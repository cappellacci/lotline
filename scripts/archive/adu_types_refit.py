#!/usr/bin/env python3
"""D-088: where the ADU place effects' differences sit (Part 1), and Form P, place types shared across states
(Part 2), against its base, Form A and Form A′.

    uv run python scripts/archive/adu_types_refit.py --inputs-only --out reports/adu-place-types
    uv run python scripts/archive/adu_types_refit.py --out reports/adu-place-types --workers 7

Forms: A, A+P, A′, A′+P. The base forms use D-084's fitter (`adu_owner.fit3_term`), so their numbers are
D-084's; the P forms use `adu_types.fit3_types`. Then:

1. **Part 1**: each fit place's log posterior-mean effect under A and under A′ (full fit), and the weighted
   share of their variance explained by state, place type and counting source, alone and together, with each
   state left out; D-088's reading rule (`adu_types.reading`).
2. **Part 2**: D-075's data-tier test, tests A-B, the tier-1 held-out log score per place (D-049) and D-085's
   test D (no trend), for all four forms; D-088's decision rule per pair (`adu_types.decide`).
3. **Sensitivity** (reported, not used): a fourth type splitting suburbs at the median pre-1960 share
   (D-083's X2), on the full fit and the data-tier folds.

The whole run is inside `offline_build`: nothing is downloaded. St. Paul stays out of every fit and score
(`adu_joint_refit`); ACS rows go through `holdout.apply_acs`. Writes only to `--out`.
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

from lotline.config import load_undercount
from lotline.io import DataStore, offline
from lotline.model import adu_fit_set as fs
from lotline.model import adu_owner as ao
from lotline.model import adu_types as ty
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr
from lotline.model.scenarios import adu

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FORMS = ("A", "A+P", "A′", "A′+P")
PAIRS = (("A", "A+P"), ("A′", "A′+P"))
SENS_FORMS = ("A+P4", "A′+P4")
TERMS4 = ("core", "suburb_old", "town")
UNITS_END = 2015  # ACS 2011-15
MIN_YEARS = 3  # Part 1 leaves out places with fewer fit years


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TR = _load("adu_trend_refit", "adu_trend_refit.py")
OWN = TR.OWN
R = TR.R


# ---------------------------------------------------------------------------------------------------------
# Inputs: types and counting sources
# ---------------------------------------------------------------------------------------------------------


def units_table(store, st: str) -> pd.DataFrame:
    """Housing units per jurisdiction (now `adu_types.units_table`, which the engine also reads)."""
    return ty.units_table(store, st)


type_table = fs.type_table  # D-088's raw types (now library code)
attach = fs.attach


def source_table(store, places) -> pd.DataFrame:
    """Each fit place's main counting source: among the sources that flag ADUs, the one with the most permit
    rows (of any kind) for the place in its fit years, and its kind from the undercount table (survey, field,
    parser, none). Coverage, not ADU counts, so a place with no ADUs counted still gets the source that
    covers it."""
    kinds = {}
    for r in load_undercount().rows:
        kinds.setdefault(r.source, []).append((r.kind, r.first_year, r.last_year))

    def kind(source: str, year: int) -> str:
        if source in cal.SURVEY_SOURCES:
            return "survey"
        for k, a, b in kinds.get(source, []):
            if (a is None or year >= a) and (b is None or year <= b):
                return "none" if k in ("none", "floor") else k
        return "none"

    rows = []
    by_state = {}
    for pl in places:
        st = pl.state.lower()
        if st not in by_state:
            p = store.read(st, "permits")
            flagging = p.loc[adu._is_adu(p), "source"].unique()
            by_state[st] = p[p["source"].isin(flagging)][["jurisdiction_geoid", "issue_year", "source"]]
        p = by_state[st]
        p = p[(p["jurisdiction_geoid"].astype(str) == pl.geoid) & p["issue_year"].isin(pl.years)]
        if p.empty:
            rows.append({"geoid": pl.geoid, "main_source": None, "source_kind": "none"})
            continue
        top = p["source"].value_counts().index[0]
        yrs = p.loc[p["source"] == top, "issue_year"]
        rows.append({"geoid": pl.geoid, "main_source": top, "source_kind": kind(top, int(yrs.median()))})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Fits (top level, for worker processes)
# ---------------------------------------------------------------------------------------------------------


def fit_one(form: str, places):
    owner = form.startswith("A′")
    if form.endswith("+P4"):
        return ty.fit3_types(places, estimate_beta=owner, terms=TERMS4)
    if form.endswith("+P"):
        return ty.fit3_types(places, estimate_beta=owner, terms=ty.TERMS)
    return ao.fit3_term(places, estimate_beta=owner)


def fit_task(args):
    key, form, places = args
    t0 = time.time()
    return key, form, fit_one(form, places), time.time() - t0


def folded(places, fit):
    tb = np.asarray(getattr(fit, "type_beta", ()), dtype=float)
    if tb.size:
        return [ty.typed_scaled(p, fit.beta, tb) for p in places]
    return [ao.scaled(p, fit.beta) for p in places]


def tau_task(args):
    key, form, places, fit = args
    return key, form, cal.tau_profile(folded(places, fit), fit.m_owner, fit.m_other)


def run_fits(pool, jobs: dict, forms, tau_for=()) -> tuple[dict, dict]:
    futs = [pool.submit(fit_task, (k, f, v[f])) for k, v in jobs.items() for f in forms]
    fits = {}
    for fu in futs:
        k, f, fit, sec = fu.result()
        fits[(k, f)] = fit
        tb = ", ".join(
            f"{t} {b:+.3f} ({lo:+.3f}, {hi:+.3f})"
            for t, b, lo, hi in zip(
                getattr(fit, "terms", ()),
                getattr(fit, "type_beta", ()),
                getattr(fit, "type_low", ()),
                getattr(fit, "type_high", ()),
                strict=True,
            )
        )
        log(
            f"  {f} {k}: theta {fit.theta * 1000:.4f}/1,000 ({fit.low * 1000:.3f}-{fit.high * 1000:.3f}), "
            f"alpha {fit.alpha:.3f}, beta {fit.beta:+.3f}, {tb or 'no types'}, "
            f"m_o {fit.m_owner}, m_x {fit.m_other}, loglik {fit.loglik:.2f} ({sec:.0f}s)"
        )
    tf = [pool.submit(tau_task, (k, f, jobs[k][f], fits[(k, f)])) for k in tau_for for f in forms]
    taus = {}
    for fu in tf:
        k, f, ll = fu.result()
        taus[(k, f)] = ll
    return fits, taus


def globals_for(fit, taus, seed: int, cap=None):
    return jr.globals_a(
        fit,
        taus,
        R.DRAWS,
        seed,
        beta=ao.beta_draws(fit, R.DRAWS, seed),
        type_beta=ty.type_draws(fit, R.DRAWS, seed),
    )


def fit_row(variant, fold, form, f) -> dict:
    d = {k: v for k, v in dataclasses.asdict(f).items() if not isinstance(v, tuple)}
    for i, t in enumerate(getattr(f, "terms", ())):
        d[f"b_{t}"], d[f"b_{t}_low"], d[f"b_{t}_high"] = f.type_beta[i], f.type_low[i], f.type_high[i]
    return {"variant": variant, "fold": fold, "form": form} | d


# ---------------------------------------------------------------------------------------------------------
# Part 1
# ---------------------------------------------------------------------------------------------------------


def part1(places, fit, info: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    e = ty.effects(places, fit).merge(info, on="geoid")
    e = e[e["years"] >= MIN_YEARS].reset_index(drop=True)
    return e, part1_summary(e)


def part1_summary(e: pd.DataFrame) -> dict:
    """Part 1's shares, leave-one-state-out reads, group means and reading, from the effects table."""
    w = e["years"].to_numpy(dtype=float)
    y = e["log_effect"].to_numpy()

    def share(cols, frame=e):
        return ty.variance_share(frame["log_effect"], frame["years"], frame[list(cols)])

    shares = {"state": share(["state"]), "type": share(["type"]), "source": share(["source_kind"])}
    shares["all three"] = share(["state", "type", "source_kind"])
    shares["state + type"] = share(["state", "type"])
    shares["state + source"] = share(["state", "source_kind"])
    loso, order_full = {}, _order(e)
    holds = True
    for st in sorted(e["state"].unique()):
        sub = e[e["state"] != st]
        loso[st] = {
            "places": len(sub),
            "state": share(["state"], sub),
            "type": share(["type"], sub),
            "source": share(["source_kind"], sub),
            "type_order": _order(sub),
        }
        holds = holds and loso[st]["type_order"] == order_full
    means = {}
    for col in ("state", "type", "source_kind"):
        g = e.groupby(col)
        means[col] = {
            str(k): {
                "places": len(v),
                "mean_log_effect": float(np.average(v["log_effect"], weights=v["years"])),
                "x_mean": float(np.exp(np.average(v["log_effect"], weights=v["years"]))),
            }
            for k, v in g
        }
    xt = pd.crosstab(e["state"], e["type"]).to_dict()
    xs = pd.crosstab(e["state"], e["source_kind"]).to_dict()
    total_var = float(np.average((y - np.average(y, weights=w)) ** 2, weights=w))
    out = {
        "places": len(e),
        "weighted_variance": total_var,
        "shares": shares,
        "type_order": order_full,
        "type_order_holds_without_each_state": holds,
        "without_state": loso,
        "group_means": means,
        "state_by_type": xt,
        "state_by_source": xs,
        "reading": ty.reading(shares, holds),
    }
    return out


def _order(frame: pd.DataFrame) -> list[str]:
    """Types ordered by weighted mean effect, high to low."""
    m = {t: np.average(v["log_effect"], weights=v["years"]) for t, v in frame.groupby("type")}
    return sorted(m, key=m.get, reverse=True)


# ---------------------------------------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--inputs-only", action="store_true")
    ap.add_argument(
        "--finish",
        action="store_true",
        help="only the decision and summary, from the tables already in --out",
    )
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        run(a, store)


def test_b_rows(store, fits, z_of: dict, types: dict, seed, forms) -> list[dict]:
    rolls = OWN.roll_towns()
    tot = []
    for st, r in rolls.groupby("state"):
        y0, y1 = int(r["first_year"].min()), int(r["last_year"].max())
        pls = cal.place_data(
            st, store, list(r["geoid"]), range(y0, y1 + 1), counts=cal.count_settings(), require_counts=False
        )
        pls = attach([ao.with_z(pl, z_of.get(pl.geoid, 0.0)) for pl in pls], types)
        if not pls:
            continue
        gained = r.set_index("geoid")["gained"]
        for form in forms:
            d = jr.predict(pls, globals_for(fits[("all", form)], 0.0, seed), seed + 1)
            total = sum(d[pl.geoid].sum(axis=1) for pl in pls)
            obs = float(sum(gained[pl.geoid] for pl in pls))
            tot.append(
                {"form": form, "state": st, "towns": len(pls), "years": f"{y0}-{y1}"}
                | jr.score(obs, total)
                | {"pass": jr.test_b_pass(obs, total)}
            )
    return tot


def heldout_log_scores(store, pz, fits, taus) -> pd.DataFrame:
    """The tier-1 held-out log score per place (D-049), as D-084: each held-out state's places at tier 1."""
    rows = []
    for st in R.STATES:
        held = [p for p in pz if p.state == st]
        inp = R.tier_inputs(st, store, held)
        for form in FORMS:
            fit = fits[(f"without {st}", form)]
            rng = np.random.default_rng([R.SEED, 1])
            tau_draws = cal.draw_tau(
                cal.TAU_GRID, cal.tau_probabilities(taus[(f"without {st}", form)]), R.DRAWS, rng
            )
            g = globals_for(fit, tau_draws, R.SEED)
            for pl in held:
                p1 = inp["t1"][pl.geoid]
                rows.append(
                    {
                        "form": form,
                        "state": st,
                        "geoid": pl.geoid,
                        "name": pl.name,
                        "log_score": jr.held_out_log_score(p1, g),
                    }
                )
    return pd.DataFrame(rows)


def run(a, store) -> None:
    places, new, own = OWN.inputs(store)
    z_fit = dict(zip(own["geoid"], own["z_fit"], strict=True))
    fit_ids = {p.geoid for p in places}
    roll_ids = set(OWN.roll_towns()["geoid"].astype(str))

    tt = type_table(store)
    fit_t = tt[tt["geoid"].isin(fit_ids)][["state", "geoid", "type_raw"]].rename(columns={"type_raw": "type"})
    mapping, notes = ty.merge_small(fit_t)
    tt["type"] = tt["type_raw"].map(mapping)
    types = dict(zip(tt["geoid"], tt["type"], strict=True))
    src = source_table(store, places)
    info = (
        tt[tt["geoid"].isin(fit_ids)][
            ["geoid", "type", "type_raw", "cbsa_code", "cbsa_type", "units", "units_source"]
        ]
        .merge(src, on="geoid", how="left")
        .rename(columns={})
    )
    info["source_kind"] = info["source_kind"].fillna("none")
    fit_info = pd.DataFrame(
        [{"state": p.state, "geoid": p.geoid, "name": p.name, "years": len(p.y)} for p in places]
    )
    fit_info = fit_info.merge(info, on="geoid", how="left")
    fit_info.to_csv(a.out / "place_types.csv", index=False)
    # the 4-type sensitivity: suburbs split at the median pre-1960 share (D-083's X2) over the fit suburbs
    x2 = pd.read_csv(REPO / "reports/adu-covariate-screen/factors.csv", dtype={"geoid": str})
    x2 = dict(zip(x2["geoid"], x2["X2"], strict=True))
    sub = fit_info[fit_info["type"] == "suburb"]
    med = float(np.nanmedian([x2.get(g, np.nan) for g in sub["geoid"]]))
    types4 = {
        g: ("suburb_old" if t == "suburb" and np.isfinite(x2.get(g, np.nan)) and x2[g] > med else t)
        for g, t in types.items()
    }
    summary = {
        "fit_set": {"places": len(places), "place_years": int(sum(len(p.y) for p in places))},
        "types": {
            "merge": mapping,
            "merge_notes": notes,
            "fit_places_by_type": fit_info.groupby("type").size().to_dict(),
            "fit_places_by_raw_type": fit_info.groupby("type_raw").size().to_dict(),
            "fit_states_by_type": fit_info.groupby("type")["state"].nunique().to_dict(),
            "state_by_type": pd.crosstab(fit_info["state"], fit_info["type"]).to_dict(),
            "units_sources": fit_info["units_source"].value_counts().to_dict(),
            "roll_towns_by_type": pd.Series([types.get(g, "missing") for g in roll_ids])
            .value_counts()
            .to_dict(),
            "core_cities": fit_info.loc[fit_info["type"] == "core", "name"].tolist(),
            "sens_suburb_split_x2_median": med,
            "sens_fit_places_by_type4": pd.Series([types4.get(g) for g in fit_ids]).value_counts().to_dict(),
        },
        "sources": {
            "fit_places_by_kind": fit_info["source_kind"].value_counts().to_dict(),
            "state_by_kind": pd.crosstab(fit_info["state"], fit_info["source_kind"]).to_dict(),
        },
    }
    log(json.dumps(summary, indent=1, default=str))
    if a.inputs_only:
        (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        return

    base = [ao.with_z(p, z_fit[p.geoid]) for p in places]
    pz = attach(base, types)
    if a.finish:
        finish(a.out, summary, pz)
        return
    pz4 = attach(base, types4, TERMS4)
    by_form = {f: pz for f in FORMS} | {f: pz4 for f in SENS_FORMS}
    early, pairs = TR.split(pz)

    def jobs_of(sel):
        return {k: {f: [p for p in by_form[f] if sel(k, p)] for f in FORMS + SENS_FORMS} for k in KEYS}

    KEYS = ["all"] + [f"without {st}" for st in R.STATES] + [f"without place {g}" for g in sorted(new)]

    def sel(k, p):
        if k == "all":
            return True
        if k.startswith("without place "):
            return p.geoid != k.removeprefix("without place ")
        return p.state != k.removeprefix("without ")

    jobs = jobs_of(sel)
    loso = [f"without {st}" for st in R.STATES]
    with ProcessPoolExecutor(a.workers) as pool:
        log("fits on 2016-2020 (test D), four forms")
        fits_early, _ = run_fits(pool, {"early": {f: early for f in FORMS}}, FORMS)
        log("fits on every year, four forms, all folds")
        fits, taus = run_fits(pool, jobs, FORMS, tau_for=loso)
        log("sensitivity: four types, full fit and the data-tier folds")
        sens_jobs = {k: jobs[k] for k in ["all"] + loso}
        fits4, taus4 = run_fits(pool, sens_jobs, SENS_FORMS, tau_for=loso)
    rows = [fit_row("early", k, f, v) for (k, f), v in fits_early.items()]
    rows += [fit_row("central", k, f, v) for (k, f), v in fits.items()]
    rows += [fit_row("sensitivity", k, f, v) for (k, f), v in fits4.items()]
    pd.DataFrame(rows).to_csv(a.out / "fits.csv", index=False)

    log("part 1")
    p1 = {}
    eff = []
    for f in ("A", "A′"):
        e, out = part1(pz, fits[("all", f)], info)
        eff.append(e.assign(form=f))
        p1[f] = out
        log(f"  {f}: {out['shares']} -> {out['reading']}")
    pd.concat(eff).to_csv(a.out / "part1_effects.csv", index=False)
    summary["part1"] = p1

    # Part 2 uses D-085's code for the shared steps, with this run's forms and draws
    TR.FORMS = FORMS
    TR.globals_for = globals_for
    log("test D")
    d_places, d_states = TR.test_d(pairs, fits_early)
    d_places.to_csv(a.out / "test_d_places_scores.csv", index=False)
    d_states.to_csv(a.out / "test_d_states.csv", index=False)
    log("data tiers")
    tier_rows, tier4 = [], []
    for st in R.STATES:
        held = [p for p in pz if p.state == st]
        inp = R.tier_inputs(st, store, held)
        tier_rows += TR.tiers_for_state(st, inp, held, fits, taus, R.SEED)
        held4 = [p for p in pz4 if p.state == st]
        inp4 = R.tier_inputs(st, store, held4)
        TR.FORMS = SENS_FORMS
        tier4 += TR.tiers_for_state(st, inp4, held4, fits4, taus4, R.SEED)
        TR.FORMS = FORMS
    tiers = pd.DataFrame(tier_rows)
    tiers.to_csv(a.out / "tiers.csv", index=False)
    tiers4 = pd.DataFrame(tier4)
    tiers4.to_csv(a.out / "tiers_sensitivity.csv", index=False)
    log("held-out log scores (tier 1)")
    ls = heldout_log_scores(store, pz, fits, taus)
    ls.to_csv(a.out / "heldout_log_scores.csv", index=False)
    log("tests A and B")
    ta = pd.DataFrame(TR.test_a_rows([p for p in pz if p.geoid in new], fits, R.SEED))
    ta.to_csv(a.out / "test_a.csv", index=False)
    tb = pd.DataFrame(test_b_rows(store, fits, z_fit, types, R.SEED, FORMS))
    tb.to_csv(a.out / "test_b.csv", index=False)
    finish(a.out, summary, pz)


# ---------------------------------------------------------------------------------------------------------
# Decision and summary, from the saved tables only (so a failure here never needs a refit)
# ---------------------------------------------------------------------------------------------------------


def _fit(fits: pd.DataFrame, variant: str, fold: str, form: str) -> pd.Series:
    r = fits[(fits["variant"] == variant) & (fits["fold"] == fold) & (fits["form"] == form)]
    return r.iloc[0]


def _terms(row: pd.Series, terms) -> dict:
    return {t: [row[f"b_{t}"], row[f"b_{t}_low"], row[f"b_{t}_high"]] for t in terms}


def finish(out: Path, summary: dict, pz) -> None:
    fits = pd.read_csv(out / "fits.csv")
    tiers = pd.read_csv(out / "tiers.csv")
    tiers4 = pd.read_csv(out / "tiers_sensitivity.csv")
    ls = pd.read_csv(out / "heldout_log_scores.csv", dtype={"geoid": str})
    d_places = pd.read_csv(out / "test_d_places_scores.csv", dtype={"geoid": str})
    ta = pd.read_csv(out / "test_a.csv", dtype={"geoid": str})
    tb = pd.read_csv(out / "test_b.csv")
    eff = pd.read_csv(out / "part1_effects.csv", dtype={"geoid": str})

    summary["part1"] = {f: part1_summary(eff[eff["form"] == f].reset_index(drop=True)) for f in ("A", "A′")}
    for f, p1 in summary["part1"].items():
        log(f"  part 1 {f}: {p1['shares']} -> {p1['reading']}")

    TR.FORMS = FORMS
    passes = TR.tests_by_form(ta, tb)
    n_tests = {f: jr.tests_passed(passes[f]) for f in FORMS}
    claim = {f: jr.claim_tier(tiers[tiers["form"] == f]) for f in FORMS}

    def useful_of(frame: pd.DataFrame, f: str) -> dict:
        return {
            int(t): int(frame[(frame["form"] == f) & (frame["tier"] == t)]["useful"].sum()) for t in (0, 1, 2)
        }

    useful = {f: useful_of(tiers, f) for f in FORMS} | {f: useful_of(tiers4, f) for f in SENS_FORMS}

    decisions = {}
    for b, p in PAIRS:
        gl, sel_, nl = TR.gain(ls.rename(columns={"form": "forecast"}), b, p)
        gd, sed, nd = TR.gain(d_places, b, p)
        gp, sep, _ = TR.gain(d_places, "persistence", p)
        dec = ty.decide(claim[b], claim[p], gl, sel_, n_tests[b], n_tests[p], gd, sed)
        full, base = _fit(fits, "central", "all", p), _fit(fits, "central", "all", b)
        decisions[f"{b} vs {p}"] = {
            "claim_tier": {"base": claim[b], "P": claim[p]},
            "tier1_log_score_gain": {"gain": gl, "se": sel_, "places": nl},
            "test_d_gain": {"gain": gd, "se": sed, "places": nd},
            "p_over_persistence_test_d": {"gain": gp, "se": sep},
            "useful_states_by_tier": {"base": useful[b], "P": useful[p]},
            "tests_passed": {"base": n_tests[b], "P": n_tests[p]},
            "type_terms_full": _terms(full, ty.TERMS),
            "lr_full": 2 * (full["loglik"] - base["loglik"]),
            "decision": dataclasses.asdict(dec),
        }
        log(f"{b} vs {p}: {decisions[f'{b} vs {p}']['decision']}")
    summary["decisions"] = decisions
    summary["claim_tier"] = claim
    summary["useful"] = useful
    summary["tests"] = passes
    summary["type_terms_without_state"] = {
        f: {st: _terms(_fit(fits, "central", f"without {st}", f), ("core",)) for st in R.STATES}
        for f in ("A+P", "A′+P")
    }
    summary["sensitivity_four_types"] = {
        f: {
            "terms": _terms(_fit(fits, "sensitivity", "all", f), TERMS4),
            "loglik": float(_fit(fits, "sensitivity", "all", f)["loglik"]),
            "useful": useful[f],
            "claim_tier": jr.claim_tier(tiers4[tiers4["form"] == f]),
        }
        for f in SENS_FORMS
    }
    owner = np.array([ao.place_z(p) for p in pz])
    core = np.array([ty.type_d(p)[0] for p in pz])
    summary["owner_vs_core_correlation"] = float(np.corrcoef(owner, core)[0, 1]) if core.std() > 0 else None
    summary["base_check_vs_d084"] = {
        f: {k: float(_fit(fits, "central", "all", f)[k]) for k in ("theta", "alpha", "beta", "loglik")}
        for f in ("A", "A′")
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    sys.exit(main())
