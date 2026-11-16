#!/usr/bin/env python3
"""D-085: Form T (a calendar-year trend) against its base, Form A and Form A′, and test D.

    uv run python scripts/dev/adu_trend_refit.py --inputs-only --out reports/adu-time-trend
    uv run python scripts/dev/adu_trend_refit.py --out reports/adu-time-trend --workers 7

Four forms: A, A+T, A′, A′+T. The base forms use D-084's fitter (`adu_owner.fit3_term`), so their numbers are
D-084's; the T forms use `adu_trend.fit3_trend` (fit 3's procedure with γ). Then, once:

1. **Test D** (new): every form refitted on 2016-2020 place-years; each place with years on both sides of the
   split forecast for 2021-2025 from its own early counts (`adu_trend.forecast`). T is scored with γ continued
   and with γ held at 2020; `adu_trend.choose_extrapolation` picks the way. A persistence benchmark is
   reported, not used.
2. **D-075's data-tier test** and **tests A-B**, as D-084 ran them, for all four forms.
3. **D-085's decision rule** (`adu_trend.decide`) for each pair (A vs A+T, A′ vs A′+T). Which pair counts is
   D-084's open call.
4. **Sensitivities:** γ leaving out each state (the data-tier folds); a rule-age term instead of the trend
   (an outlook, its likelihood ratio only).

The whole run is inside `offline_build`: nothing is downloaded. St. Paul stays out (`adu_joint_refit`), and
ACS rows go through `holdout.apply_acs` (`adu_owner_refit`). Writes only to `--out`.
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

from lotline.config import load_params
from lotline.io import DataStore, offline
from lotline.model import adu_owner as ao
from lotline.model import adu_trend as at
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr
from lotline.model import score as sc

HERE = Path(__file__).resolve().parent
FORMS = ("A", "A+T", "A′", "A′+T")
PAIRS = (("A", "A+T"), ("A′", "A′+T"))
PT = {k: int(v.value) for k, v in load_params("adu_trend").items()}
REF, SPLIT = PT["adu_trend_ref_year"], PT["adu_trend_split_last_early_year"]
LATE = range(SPLIT + 1, 2026)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


OWN = _load("adu_owner_refit", "adu_owner_refit.py")
R = OWN.R


# ---------------------------------------------------------------------------------------------------------
# Fits
# ---------------------------------------------------------------------------------------------------------


def fit_one(form: str, places, s_of=None):
    owner = form.startswith("A′")
    if form.endswith("+T") or s_of is not None:
        return at.fit3_trend(places, estimate_beta=owner, estimate_gamma=True, ref=REF, s_of=s_of)
    return ao.fit3_term(places, estimate_beta=owner)


def fit_task(args):
    key, form, places = args
    t0 = time.time()
    return key, form, fit_one(form, places), time.time() - t0


def folded(places, fit):
    """The places with exp(β̂ z) and exp(γ̂ (t − ref)) folded in, for τ's profile."""
    out = [ao.scaled(p, fit.beta) for p in places]
    g = getattr(fit, "gamma", 0.0)
    return [at.trended(p, g, REF) for p in out] if g else out


def tau_task(args):
    key, form, places, fit = args
    return key, form, cal.tau_profile(folded(places, fit), fit.m_owner, fit.m_other)


def fit_row(variant, fold, form, f) -> dict:
    d = {k: v for k, v in dataclasses.asdict(f).items() if not isinstance(v, tuple)}
    return {"variant": variant, "fold": fold, "form": form} | d


def run_fits(pool, jobs: dict, forms=FORMS, tau_for=()) -> tuple[dict, dict]:
    futs = [pool.submit(fit_task, (k, f, v)) for k, v in jobs.items() for f in forms]
    fits = {}
    for fu in futs:
        k, f, fit, sec = fu.result()
        fits[(k, f)] = fit
        gm = getattr(fit, "gamma", 0.0)
        log(
            f"  {f} {k}: theta {fit.theta * 1000:.4f}/1,000 ({fit.low * 1000:.3f}-{fit.high * 1000:.3f}), "
            f"alpha {fit.alpha:.3f}, beta {fit.beta:+.3f}, gamma {gm:+.4f} "
            f"({getattr(fit, 'gamma_low', 0.0):+.4f}, {getattr(fit, 'gamma_high', 0.0):+.4f}), "
            f"m_o {fit.m_owner}, m_x {fit.m_other}, loglik {fit.loglik:.2f} ({sec:.0f}s)"
        )
    tf = [pool.submit(tau_task, (k, f, jobs[k], fits[(k, f)])) for k in tau_for for f in forms]
    taus = {}
    for fu in tf:
        k, f, ll = fu.result()
        taus[(k, f)] = ll
    return fits, taus


def globals_for(fit, taus, seed: int, cap: int | None = None):
    return jr.globals_a(
        fit,
        taus,
        R.DRAWS,
        seed,
        beta=ao.beta_draws(fit, R.DRAWS, seed),
        gamma=at.gamma_draws(fit, R.DRAWS, seed),
        trend_ref=REF,
        trend_cap=cap,
    )


# ---------------------------------------------------------------------------------------------------------
# Test D
# ---------------------------------------------------------------------------------------------------------


def split(places):
    """(early places for the 2016-2020 fit, [(early, late)] for places with years on both sides)."""
    early, pairs = [], []
    for pl in places:
        e = jr.subset_years(pl, range(2016, SPLIT + 1))
        lt = jr.subset_years(pl, LATE)
        if e is not None:
            early.append(e)
            if lt is not None:
                pairs.append((e, lt))
    return early, pairs


def variants(fits_early):
    """The forecasts test D scores: each base form, and each T form continued and held flat at the split."""
    out = {}
    for f in FORMS:
        fit = fits_early[("early", f)]
        if f.endswith("+T"):
            out[f"{f} continued"] = (f, globals_for(fit, 0.0, R.SEED, cap=None))
            out[f"{f} flat"] = (f, globals_for(fit, 0.0, R.SEED, cap=SPLIT))
        else:
            out[f] = (f, globals_for(fit, 0.0, R.SEED))
    return out


def test_d(pairs, fits_early):
    place_rows, state_rows = [], []
    vs = variants(fits_early)
    for name, (_, g) in vs.items():
        draws = {}
        for e, lt in pairs:
            d = at.forecast(e, lt, g, R.SEED + 4)
            draws[e.geoid] = d.sum(axis=1)
            obs = float(lt.y.sum())
            place_rows.append(
                {
                    "forecast": name,
                    "state": e.state,
                    "geoid": e.geoid,
                    "name": e.name,
                    "early_years": len(e.y),
                    "late_years": len(lt.y),
                    "log_score": at.forecast_log_score(e, lt, g),
                }
                | jr.score(obs, draws[e.geoid])
            )
        for st in R.STATES:
            ps = [(e, lt) for e, lt in pairs if e.state == st]
            if ps:
                obs = float(sum(lt.y.sum() for _, lt in ps))
                tot = sum(draws[e.geoid] for e, _ in ps)
                state_rows.append({"forecast": name, "state": st, "places": len(ps)} | jr.score(obs, tot))
    draws = {}
    for e, lt in pairs:
        d, ll = at.persistence(e, lt, R.DRAWS, R.SEED + 5)
        draws[e.geoid] = d.sum(axis=1)
        place_rows.append(
            {
                "forecast": "persistence",
                "state": e.state,
                "geoid": e.geoid,
                "name": e.name,
                "early_years": len(e.y),
                "late_years": len(lt.y),
                "log_score": ll,
            }
            | jr.score(float(lt.y.sum()), draws[e.geoid])
        )
    for st in R.STATES:
        ps = [(e, lt) for e, lt in pairs if e.state == st]
        if ps:
            obs = float(sum(lt.y.sum() for _, lt in ps))
            tot = sum(draws[e.geoid] for e, _ in ps)
            state_rows.append(
                {"forecast": "persistence", "state": st, "places": len(ps)} | jr.score(obs, tot)
            )
    return pd.DataFrame(place_rows), pd.DataFrame(state_rows)


def gain(places: pd.DataFrame, a: str, b: str) -> tuple[float, float, int]:
    """Σ (log score of b − log score of a) over places, its paired SE, and the number of places."""
    piv = places.pivot_table(index="geoid", columns="forecast", values="log_score")
    d = (piv[b] - piv[a]).replace([np.inf, -np.inf], np.nan).dropna()
    g, se = sc.paired(d)
    return g, se, len(d)


# ---------------------------------------------------------------------------------------------------------
# Tiers and tests A-B (D-084's, for four forms)
# ---------------------------------------------------------------------------------------------------------


def tiers_for_state(held, inputs, places_held, fits, taus, seed):
    city = inputs["city"]
    targets = [pl for pl in places_held if pl.geoid != city and R.target_cols(pl).any()]
    if not targets:
        return [
            {"held_out": held, "form": f, "tier": t, "targets": 0, "tier2_city": city, "useful": False}
            for f in FORMS
            for t in (0, 1, 2)
        ]
    obs = float(sum(pl.y[R.target_cols(pl)].sum() for pl in targets))
    rows = []
    for form in FORMS:
        fit = fits[(f"without {held}", form)]
        rng = np.random.default_rng([seed, 1])
        tau_draws = cal.draw_tau(
            cal.TAU_GRID, cal.tau_probabilities(taus[(f"without {held}", form)]), R.DRAWS, rng
        )
        g = globals_for(fit, tau_draws, seed)
        city_t1 = jr.subset_years(inputs["t1"][city], range(min(R.WINDOW), R.TIER2_LAST + 1))
        g2, ess = jr.update(g, city_t1, seed + 2)
        for tier, (key, gg) in enumerate([("t0", g), ("t1", g), ("t1", g2)]):
            pls = [inputs[key][pl.geoid] for pl in targets]
            d = jr.predict(pls, gg, seed + 3)
            tot = sum(d[pl.geoid][:, R.target_cols(pl)].sum(axis=1) for pl in pls)
            rows.append(
                {
                    "held_out": held,
                    "form": form,
                    "tier": tier,
                    "targets": len(pls),
                    "tier2_city": city,
                    "ess": ess if tier == 2 else np.nan,
                }
                | jr.score(obs, tot)
            )
    return rows


def test_a_rows(new_places, fits, seed) -> list[dict]:
    rows = []
    for pl in new_places:
        cols = R.target_cols(pl)
        if not cols.any():
            continue
        obs = float(pl.y[cols].sum())
        for form in FORMS:
            g = globals_for(fits[(f"without place {pl.geoid}", form)], 0.0, seed)
            d = jr.predict([pl], g, seed + 1)[pl.geoid][:, cols].sum(axis=1)
            rows.append(
                {"form": form, "state": pl.state, "geoid": pl.geoid, "name": pl.name} | jr.score(obs, d)
            )
    return rows


def test_b_rows(store, fits, z_of: dict, seed) -> list[dict]:
    rolls = OWN.roll_towns()
    tot = []
    for st, r in rolls.groupby("state"):
        y0, y1 = int(r["first_year"].min()), int(r["last_year"].max())
        pls = cal.place_data(
            st, store, list(r["geoid"]), range(y0, y1 + 1), counts=cal.count_settings(), require_counts=False
        )
        pls = [ao.with_z(pl, z_of.get(pl.geoid, 0.0)) for pl in pls]
        if not pls:
            continue
        gained = r.set_index("geoid")["gained"]
        for form in FORMS:
            d = jr.predict(pls, globals_for(fits[("all", form)], 0.0, seed), seed + 1)
            total = sum(d[pl.geoid].sum(axis=1) for pl in pls)
            obs = float(sum(gained[pl.geoid] for pl in pls))
            tot.append(
                {"form": form, "state": st, "towns": len(pls), "years": f"{y0}-{y1}"}
                | jr.score(obs, total)
                | {"pass": jr.test_b_pass(obs, total)}
            )
    return tot


def tests_by_form(ta: pd.DataFrame, tb: pd.DataFrame) -> dict:
    out = {}
    for f in FORMS:
        a, b = ta[ta["form"] == f], tb[tb["form"] == f]
        out[f] = {
            "A": {st: jr.test_a_pass(a[a["state"] == st]) for st in R.STATES},
            "B": {
                st: (bool(b.loc[b["state"] == st, "pass"].iloc[0]) if (b["state"] == st).any() else None)
                for st in R.STATES
            },
        }
    return out


# ---------------------------------------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--inputs-only", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        run(a, store)


def run(a, store) -> None:
    places, new, own = OWN.inputs(store)
    z_fit = dict(zip(own["geoid"], own["z_fit"], strict=True))
    pz = [ao.with_z(p, z_fit[p.geoid]) for p in places]
    early, pairs = split(pz)
    split_tab = pd.DataFrame(
        [
            {"state": e.state, "geoid": e.geoid, "name": e.name, "early": len(e.y), "late": len(lt.y)}
            for e, lt in pairs
        ]
    )
    split_tab.to_csv(a.out / "test_d_places.csv", index=False)
    summary = {
        "fit_set": {"places": len(pz), "place_years": int(sum(len(p.y) for p in pz))},
        "test_d_set": {
            "early_fit_places": len(early),
            "early_fit_place_years": int(sum(len(p.y) for p in early)),
            "forecast_places": len(pairs),
            "by_state": split_tab.groupby("state").size().to_dict(),
            "late_place_years": int(split_tab["late"].sum()),
        },
        "ref_year": REF,
        "split_last_early_year": SPLIT,
    }
    log(f"fit set {summary['fit_set']}; test D {summary['test_d_set']}")
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    if a.inputs_only:
        return

    jobs = {"all": pz} | {f"without {st}": [p for p in pz if p.state != st] for st in R.STATES}
    jobs |= {f"without place {g}": [p for p in pz if p.geoid != g] for g in sorted(new)}
    loso = [f"without {st}" for st in R.STATES]
    with ProcessPoolExecutor(a.workers) as pool:
        log("fits on 2016-2020 (test D), four forms")
        fits_early, _ = run_fits(pool, {"early": early})
        log("fits on every year, four forms, all folds")
        fits, taus = run_fits(pool, jobs, tau_for=loso)
        log("outlook: rule age instead of the trend (A′ base)")
        fa_age = pool.submit(at.fit3_trend, pz, True, True, REF, s_of=at.rule_age).result()
    rows = [fit_row("early", k, f, v) for (k, f), v in fits_early.items()]
    rows += [fit_row("central", k, f, v) for (k, f), v in fits.items()]
    rows.append(fit_row("rule-age outlook", "all", "A′+age", fa_age))
    pd.DataFrame(rows).to_csv(a.out / "fits.csv", index=False)

    log("test D")
    d_places, d_states = test_d(pairs, fits_early)
    d_places.to_csv(a.out / "test_d_places_scores.csv", index=False)
    d_states.to_csv(a.out / "test_d_states.csv", index=False)

    log("data tiers")
    tier_rows = []
    for st in R.STATES:
        held = [p for p in pz if p.state == st]
        inp = R.tier_inputs(st, store, held)
        tier_rows += tiers_for_state(st, inp, held, fits, taus, R.SEED)
    tiers = pd.DataFrame(tier_rows)
    tiers.to_csv(a.out / "tiers.csv", index=False)
    log("tests A and B")
    ta = pd.DataFrame(test_a_rows([p for p in pz if p.geoid in new], fits, R.SEED))
    ta.to_csv(a.out / "test_a.csv", index=False)
    tb = pd.DataFrame(test_b_rows(store, fits, z_fit, R.SEED))
    tb.to_csv(a.out / "test_b.csv", index=False)
    passes = tests_by_form(ta, tb)
    n_tests = {f: jr.tests_passed(passes[f]) for f in FORMS}
    useful = {
        f: {
            int(t): int(tiers[(tiers["form"] == f) & (tiers["tier"] == t)]["useful"].sum()) for t in (0, 1, 2)
        }
        for f in FORMS
    }

    decisions = {}
    for base, tf in PAIRS:
        gc, sec, nc = gain(d_places, f"{tf} flat", f"{tf} continued")
        way = at.choose_extrapolation(gc, sec)
        gd, sed, nd = gain(d_places, base, f"{tf} {'continued' if way == 'continue' else 'flat'}")
        full = fits[("all", tf)]
        dec = at.decide(
            gd, sed, full.gamma_low, full.gamma_high, useful[base], useful[tf], n_tests[base], n_tests[tf]
        )
        gp, sep, _ = gain(d_places, "persistence", base)
        decisions[f"{base} vs {tf}"] = {
            "extrapolation": way,
            "continue_over_flat": {"gain": gc, "se": sec, "places": nc},
            "test_d_gain_t_over_base": {"gain": gd, "se": sed, "places": nd},
            "base_over_persistence": {"gain": gp, "se": sep},
            "gamma_full": {"gamma": full.gamma, "low": full.gamma_low, "high": full.gamma_high},
            "useful_states_by_tier": {"base": useful[base], "T": useful[tf]},
            "tests_passed": {"base": n_tests[base], "T": n_tests[tf]},
            "decision": dataclasses.asdict(dec),
        }
        log(f"{base} vs {tf}: {decisions[f'{base} vs {tf}']['decision']}")
    summary["decisions"] = decisions
    summary["claim_tier"] = {f: jr.claim_tier(tiers[tiers["form"] == f]) for f in FORMS}
    summary["tests"] = passes
    summary["gamma_without_state"] = {
        f: {
            st: [
                fits[(f"without {st}", f)].gamma,
                fits[(f"without {st}", f)].gamma_low,
                fits[(f"without {st}", f)].gamma_high,
            ]
            for st in R.STATES
        }
        for f in ("A+T", "A′+T")
    }
    fa = fits[("all", "A′")]
    summary["outlook_rule_age"] = {
        "delta": fa_age.gamma,
        "delta_interval": [fa_age.gamma_low, fa_age.gamma_high],
        "loglik": fa_age.loglik,
        "lr_vs_a_prime": 2 * (fa_age.loglik - fa.loglik),
        "lr_vs_a_prime_t": 2 * (fa_age.loglik - fits[("all", "A′+T")].loglik),
    }
    summary["base_check_vs_d084"] = {
        f: {k: getattr(fits[("all", f)], k) for k in ("theta", "alpha", "beta", "loglik")}
        for f in ("A", "A′")
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    sys.exit(main())
