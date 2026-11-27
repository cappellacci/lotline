#!/usr/bin/env python3
"""D-094: a place-effect variance per place type (Form S), against A + P, on the checked rule rows.

    PYTHONPATH=src python scripts/archive/adu_type_spread.py --out reports/adu-type-spread --workers 7

Forms: A + P (the base, D-088's), A + P + S (core cities get their own variance α_core = α_sub e^λ) and,
reported only, A + S (a variance per type, no type terms). Fits on every year for the full set, each state
left out and each D-074 new place left out (test A), and on 2016-2020 (test D), with D-088's code
(`adu_types_refit`, `adu_trend_refit`). Then D-088's measures for the three forms (tier-1 held-out log score,
D-075's tiers, tests A-B, test D), D-088's decision rule for A + P vs A + P + S (`adu_types.decide`), and the
range coverage check's measures (`adu_range_coverage`): randomized-PIT coverage by type and the state-total
width split by source.

τ's profile (`calibrate_adu.tau_profile`) refits θ and one α at each τ, so the state multiplier's spread is
learned as under A + P for every form (D-094 changes only the place effect).

Offline from cached tables; St. Paul stays out (adu_joint_refit); nothing is unblinded or written to config.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.calibrate.adu import calibrate_adu as cal
from lotline.calibrate.adu import joint_refit as jr
from lotline.io import DataStore, offline
from lotline.model import adu_owner as ao
from lotline.model import adu_types as ty

HERE = Path(__file__).resolve().parent
FORMS = ("A+P", "A+P+S", "A+S")
BASE, CAND = "A+P", "A+P+S"


def _load(name: str, file: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


COV = _load("adu_range_coverage", "adu_range_coverage.py")
TYP = COV.TYP
R, OWN, TR = TYP.R, TYP.OWN, TYP.TR
_base_fit_one = TYP.fit_one


def fit_one(form: str, places):
    """D-088's forms, plus Form S (module docstring)."""
    if form == "A+P+S":
        return ty.fit3_types(places, estimate_beta=False, terms=ty.TERMS, spread=True)
    if form == "A+S":
        return ty.fit3_types(places, estimate_beta=False, terms=(), spread=True)
    return _base_fit_one(form, places)


TYP.fit_one = fit_one  # top level, so worker processes see it too


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def spread_row(fold: str, form: str, f) -> dict:
    return {
        "fold": fold,
        "form": form,
        "alpha_sub": f.alpha,
        "alpha_core": getattr(f, "alpha_core", None),
        "lam": getattr(f, "lam", 0.0),
        "lam_low": getattr(f, "lam_low", 0.0),
        "lam_high": getattr(f, "lam_high", 0.0),
        "core": f.type_beta[0] if getattr(f, "type_beta", ()) else 0.0,
        "core_low": f.type_low[0] if getattr(f, "type_low", ()) else 0.0,
        "core_high": f.type_high[0] if getattr(f, "type_high", ()) else 0.0,
        "theta_per_1000": f.theta * 1000,
        "m_owner": f.m_owner,
        "m_other": f.m_other,
        "loglik": f.loglik,
    }


def coverage(store, pz, fits, taus, types) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The range coverage check's place table and width split, for the three forms."""
    rows, parts = [], []
    for st in R.STATES:
        held = [p for p in pz if p.state == st]
        if not held:
            continue
        inp = R.tier_inputs(st, store, held)
        for form in FORMS:
            fit = fits[(f"without {st}", form)]
            rng = np.random.default_rng([R.SEED, 1])
            tau_draws = cal.draw_tau(
                cal.TAU_GRID, cal.tau_probabilities(taus[(f"without {st}", form)]), R.DRAWS, rng
            )
            g = TYP.globals_for(fit, tau_draws, R.SEED)
            t1 = [inp["t1"][p.geoid] for p in held]
            pred = jr.predict(t1, g, R.SEED)
            parts.append(COV.decompose(form, st, t1, fit, g, pred))
            prng = np.random.default_rng([R.SEED, 7])
            for pl in t1:
                rows.append(COV.place_row(form, st, pl, pred[pl.geoid].sum(axis=1), prng))
    places = pd.DataFrame(rows)
    places["type"] = places["geoid"].map(types)
    return places, pd.DataFrame(parts)


def run(a, store) -> dict:
    places, new, own = OWN.inputs(store)
    z_fit = dict(zip(own["geoid"], own["z_fit"], strict=True))
    fit_ids = {p.geoid for p in places}
    tt = TYP.type_table(store)
    fit_t = tt[tt["geoid"].isin(fit_ids)][["state", "geoid", "type_raw"]].rename(columns={"type_raw": "type"})
    mapping, notes = ty.merge_small(fit_t)
    tt["type"] = tt["type_raw"].map(mapping)
    types = dict(zip(tt["geoid"], tt["type"], strict=True))
    pz = TYP.attach([ao.with_z(p, z_fit[p.geoid]) for p in places], types)
    n_core = int(sum(ty.is_core(pz)))
    log(f"{len(pz)} places, {sum(len(p.y) for p in pz)} place-years, {n_core} core cities; merge {notes}")

    keys = ["all"] + [f"without {st}" for st in R.STATES] + [f"without place {g}" for g in sorted(new)]

    def sel(k, p):
        if k == "all":
            return True
        if k.startswith("without place "):
            return p.geoid != k.removeprefix("without place ")
        return p.state != k.removeprefix("without ")

    jobs = {k: {f: [p for p in pz if sel(k, p)] for f in FORMS} for k in keys}
    loso = [f"without {st}" for st in R.STATES]
    early, pairs = TR.split(pz)
    with ProcessPoolExecutor(a.workers) as pool:
        log("fits on 2016-2020 (test D)")
        fits_early, _ = TYP.run_fits(pool, {"early": {f: early for f in FORMS}}, FORMS)
        log("fits on every year, all folds")
        fits, taus = TYP.run_fits(pool, jobs, FORMS, tau_for=loso)
    rows = [TYP.fit_row("early", k, f, v) for (k, f), v in fits_early.items()]
    rows += [TYP.fit_row("central", k, f, v) for (k, f), v in fits.items()]
    pd.DataFrame(rows).to_csv(a.out / "fits.csv", index=False)
    sp = [spread_row(k, f, v) for (k, f), v in list(fits.items()) + list(fits_early.items())]
    spreads = pd.DataFrame(sp)
    spreads.to_csv(a.out / "spreads.csv", index=False)
    for (k, f), v in fits.items():
        if f != "A+P" and not k.startswith("without place"):
            log(
                f"  {f} {k}: alpha_sub {v.alpha:.3f}, alpha_core {v.alpha_core:.3f}, lambda {v.lam:+.2f} "
                f"({v.lam_low:+.2f}, {v.lam_high:+.2f})"
            )

    TYP.FORMS = FORMS
    TR.FORMS = FORMS
    TR.globals_for = TYP.globals_for
    log("test D")
    d_places, d_states = TR.test_d(pairs, fits_early)
    d_places.to_csv(a.out / "test_d_places_scores.csv", index=False)
    d_states.to_csv(a.out / "test_d_states.csv", index=False)
    log("data tiers")
    tier_rows = []
    for st in R.STATES:
        held = [p for p in pz if p.state == st]
        inp = R.tier_inputs(st, store, held)
        tier_rows += TR.tiers_for_state(st, inp, held, fits, taus, R.SEED)
    tiers = pd.DataFrame(tier_rows)
    tiers.to_csv(a.out / "tiers.csv", index=False)
    log("held-out log scores (tier 1)")
    ls = TYP.heldout_log_scores(store, pz, fits, taus)
    ls.to_csv(a.out / "heldout_log_scores.csv", index=False)
    log("tests A and B")
    ta = pd.DataFrame(TR.test_a_rows([p for p in pz if p.geoid in new], fits, R.SEED))
    ta.to_csv(a.out / "test_a.csv", index=False)
    tb = pd.DataFrame(TYP.test_b_rows(store, fits, z_fit, types, R.SEED, FORMS))
    tb.to_csv(a.out / "test_b.csv", index=False)
    log("range coverage")
    cov_places, parts = coverage(store, pz, fits, taus, types)
    cov_places.to_csv(a.out / "heldout_places.csv", index=False)
    parts.to_csv(a.out / "state_width_parts.csv", index=False)
    return {"places": len(pz), "place_years": int(sum(len(p.y) for p in pz)), "core_cities": n_core}


def finish(out: Path, inputs: dict) -> None:
    tiers = pd.read_csv(out / "tiers.csv")
    ls = pd.read_csv(out / "heldout_log_scores.csv", dtype={"geoid": str})
    d_places = pd.read_csv(out / "test_d_places_scores.csv", dtype={"geoid": str})
    ta = pd.read_csv(out / "test_a.csv", dtype={"geoid": str})
    tb = pd.read_csv(out / "test_b.csv")
    spreads = pd.read_csv(out / "spreads.csv")
    cov = pd.read_csv(out / "heldout_places.csv", dtype={"geoid": str})
    parts = pd.read_csv(out / "state_width_parts.csv")

    TR.FORMS = FORMS
    passes = TR.tests_by_form(ta, tb)
    n_tests = {f: jr.tests_passed(passes[f]) for f in FORMS}
    claim = {f: jr.claim_tier(tiers[tiers["form"] == f]) for f in FORMS}
    useful = {
        f: {
            int(t): int(tiers[(tiers["form"] == f) & (tiers["tier"] == t)]["useful"].sum()) for t in (0, 1, 2)
        }
        for f in FORMS
    }
    lsf = ls.rename(columns={"form": "forecast"})
    comparisons = {}
    for b, p in ((BASE, CAND), (BASE, "A+S")):
        gl, sel_, nl = TR.gain(lsf, b, p)
        gd, sed, nd = TR.gain(d_places, b, p)
        comparisons[f"{b} vs {p}"] = {
            "tier1_log_score_gain": {"gain": gl, "se": sel_, "places": nl},
            "test_d_gain": {"gain": gd, "se": sed, "places": nd},
        }
    c = comparisons[f"{BASE} vs {CAND}"]
    dec = ty.decide(
        claim[BASE],
        claim[CAND],
        c["tier1_log_score_gain"]["gain"],
        c["tier1_log_score_gain"]["se"],
        n_tests[BASE],
        n_tests[CAND],
        c["test_d_gain"]["gain"],
        c["test_d_gain"]["se"],
    )
    full = spreads[spreads["fold"] == "all"].set_index("form")
    cand_full = full.loc[CAND]
    stopped = bool(cand_full["lam"] >= 0)
    cov_sum = pd.concat(
        [
            COV.summarize(cov, ["form"]).assign(group="all"),
            COV.summarize(cov, ["form", "type"]).rename(columns={"type": "group"}),
            COV.summarize(cov, ["form", "state"]).rename(columns={"state": "group"}),
        ]
    )
    cov_sum.to_csv(out / "heldout_coverage.csv", index=False)
    ratio_cols = [c for c in parts.columns if c.endswith("_ratio")]
    summary = {
        "inputs": inputs,
        "full_fit": full.reset_index().to_dict(orient="records"),
        "lambda_below_zero": not stopped,
        "claim_tier": claim,
        "useful": useful,
        "tests": passes,
        "tests_passed": n_tests,
        "comparisons": comparisons,
        "decision": dataclasses.asdict(dec),
        "coverage": cov_sum.round(4).to_dict(orient="records"),
        "state_width": parts[["form", "state", "places", *ratio_cols]].round(3).to_dict(orient="records"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(
        json.dumps({k: summary[k] for k in ("claim_tier", "useful", "tests_passed", "comparisons")}, indent=1)
    )
    log(
        f"lambda {cand_full['lam']:+.3f} ({cand_full['lam_low']:+.3f}, {cand_full['lam_high']:+.3f}); "
        f"alpha_core {cand_full['alpha_core']:.3f}, alpha_sub {cand_full['alpha_sub']:.3f}"
    )
    log(f"decision: {summary['decision']}")
    log("\n" + cov_sum.round(3).to_string(index=False))
    log("\n" + parts[["form", "state", *ratio_cols]].round(1).to_string(index=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--finish", action="store_true", help="only the decision and summary, from saved tables")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    inputs = {}
    if not a.finish:
        store = DataStore()
        with offline.offline_build(store):
            inputs = run(a, store)
        (a.out / "inputs.json").write_text(json.dumps(inputs))
    else:
        inputs = json.loads((a.out / "inputs.json").read_text())
    finish(a.out, inputs)


if __name__ == "__main__":
    main()
