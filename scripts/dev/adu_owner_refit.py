#!/usr/bin/env python3
"""D-084: Form A′ (Form A with owner-occupied share as a place term) against Form A, on D-079's tests.

    uv run python scripts/dev/adu_owner_refit.py --inputs-only --out reports/adu-owner-share
    uv run python scripts/dev/adu_owner_refit.py --out reports/adu-owner-share --workers 6

`--inputs-only` builds the fit set (D-079's, `adu_joint_refit.all_places`) and each place's owner share, and
writes them with the correlation between the fit vintage (2011-15) and the latest vintage (2020-24), as D-084
asks before any fit. Without it the script then runs, once:

1. **Both forms** with the same fitter (`adu_owner.fit3_term`), so they are compared on the same inputs.
   Form A is the fitter with β_o held at 0, and it is checked against D-079's Form A values.
2. **D-075's data-tier test** (leave one state out; tiers 0, 1 and 2; target 2021-2024), as D-079 ran it.
3. **Tests A and B** state by state (D-074 §3), as D-079 ran them. Test C needs the scenario engine, which has
   no place term; D-079 left C out of the decision count, so it is not run here (Form A's D-079 result
   stands).
4. **D-084's decision rule** (`adu_owner.decide`), with the tier-1 held-out log score per place.
5. **Sensitivities**, reported and not used to choose: owner share from the 2016-20 vintage; β_o within
   states; Form A′ plus D-083's pre-1960 share (an outlook).

Owner share is B25003_002 / B25003_001 from `acs_geo_year`, through `holdout.apply_acs`. A place reads its
place rows; a Minnesota township its county-subdivision rows; an unincorporated county area its county's rows
less the places whose county it is. A place with none gets z = 0 and a flag. The whole run is inside
`offline_build`: nothing is downloaded. Writes only to `--out`.
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
from lotline.model import adu_screen as scr
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr
from lotline.model import score as sc
from lotline.validation import holdout

HERE = Path(__file__).resolve().parent
LATEST = 2024  # the newest ACS 5-year vintage ending at or before the 2025 data origin
SENS_END = 2020  # D-084 sensitivity: the 2016-20 vintage
FORMS = ("A", "A′")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_refit():
    spec = importlib.util.spec_from_file_location("adu_joint_refit", HERE / "adu_joint_refit.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adu_joint_refit"] = mod
    spec.loader.exec_module(mod)
    return mod


R = load_refit()
P = {k: v.value for k, v in load_params("adu_owner").items()}
CENTER, SCALE, FIT_END = (
    P["adu_owner_share_center"],
    P["adu_owner_share_scale"],
    int(P["adu_owner_fit_end_year"]),
)


# ---------------------------------------------------------------------------------------------------------
# Owner share
# ---------------------------------------------------------------------------------------------------------


def b25003(store, st: str) -> pd.DataFrame:
    """Owner-occupied and total occupied homes per (geo, end_year), held-out rows removed."""
    a = holdout.apply_acs(store.read(st, "acs_geo_year"), st)
    a = a[a["table_id"] == "B25003"]
    v = a["variable"].astype(str)
    out = pd.DataFrame(
        {
            "owner": a[v == "B25003_002"].groupby(["geo", "end_year"])["estimate"].sum(),
            "total": a[v == "B25003_001"].groupby(["geo", "end_year"])["estimate"].sum(),
        }
    )
    return out.dropna()


def owner_rows(st: str, geoid: str, kind: str, county: str, acs: pd.DataFrame, juris: pd.DataFrame):
    """({end_year: share}, source) for one jurisdiction, by D-084's order of sources."""

    def shares(frame: pd.DataFrame) -> dict[int, float]:
        f = frame[frame["total"] > 0]
        return {int(y): float(o / t) for y, o, t in zip(f.index, f["owner"], f["total"], strict=True)}

    def at(geo: str) -> pd.DataFrame:
        return acs.xs(geo, level="geo") if geo in acs.index.get_level_values("geo") else acs.iloc[:0]

    if kind == "place" and not at(f"place:{geoid}").empty:
        return shares(at(f"place:{geoid}")), "place"
    if kind == "township" and not at(f"cousub:{geoid}").empty:
        return shares(at(f"cousub:{geoid}")), "county subdivision"
    if kind == "county_unincorporated" and not at(f"county:{county}").empty:
        inside = juris[(juris["county_geoid"].astype(str) == county) & (juris["kind"] == "place")]
        rest = at(f"county:{county}").copy()
        for g in inside["geoid"].astype(str):
            p = at(f"place:{g}")
            rest = rest.sub(p.reindex(rest.index).fillna(0.0))
        return shares(rest), "county less its places"
    return {}, "none"


def owner_table(store, items: list[tuple[str, str, str]]) -> pd.DataFrame:
    """One row per (state, geoid, name): share and vintage in the fit, latest and sensitivity reads, z."""
    rows = []
    for st in sorted({s for s, _, _ in items}):
        acs = b25003(store, st)
        juris = store.read(st, "jurisdictions")
        info = juris.set_index(juris["geoid"].astype(str))
        for s, g, name in items:
            if s != st:
                continue
            kind = str(info.at[g, "kind"]) if g in info.index else "place"
            county = str(info.at[g, "county_geoid"]) if g in info.index else ""
            by_year, source = owner_rows(st, g, kind, county, acs, juris)
            row = {"state": st, "geoid": g, "name": name, "kind": kind, "source": source}
            for tag, end in (("fit", FIT_END), ("latest", LATEST), ("sens", SENS_END)):
                share, year = ao.vintage_share(by_year, end)
                row[f"share_{tag}"], row[f"vintage_{tag}"] = share, year
                row[f"z_{tag}"] = 0.0 if share is None else ao.owner_z(share, CENTER, SCALE)
            row["flag"] = "no owner share: z = 0" if row["share_fit"] is None else ""
            rows.append(row)
    return pd.DataFrame(rows)


def roll_towns() -> pd.DataFrame:
    r = pd.read_csv(R.ROLLS, dtype={"geoid": str})
    return r[~r["sets_k"]]


# ---------------------------------------------------------------------------------------------------------
# Fits
# ---------------------------------------------------------------------------------------------------------


def fit_task(args):
    key, form, places = args
    t0 = time.time()
    fit = ao.fit3_term(places, estimate_beta=(form == "A′"))
    return key, form, fit, time.time() - t0


def tau_task(args):
    key, form, places, fit = args
    return key, form, cal.tau_profile([ao.scaled(p, fit.beta) for p in places], fit.m_owner, fit.m_other)


def fit_row(variant, fold, form, f) -> dict:
    return {"variant": variant, "fold": fold, "form": form} | {
        k: v for k, v in dataclasses.asdict(f).items() if not isinstance(v, tuple)
    }


def run_fits(pool, jobs: dict, forms=FORMS, tau_for=()) -> tuple[dict, dict]:
    futs = [pool.submit(fit_task, (k, f, v)) for k, v in jobs.items() for f in forms]
    fits = {}
    for fu in futs:
        k, f, fit, sec = fu.result()
        fits[(k, f)] = fit
        log(
            f"  {f} {k}: theta {fit.theta * 1000:.4f}/1,000 ({fit.low * 1000:.3f}-{fit.high * 1000:.3f}), "
            f"alpha {fit.alpha:.3f}, beta {fit.beta:+.3f} ({fit.beta_low:+.3f}, {fit.beta_high:+.3f}), "
            f"m_o {fit.m_owner}, m_x {fit.m_other}, loglik {fit.loglik:.2f} ({sec:.0f}s)"
        )
    tf = [pool.submit(tau_task, (k, f, jobs[k], fits[(k, f)])) for k in tau_for for f in forms]
    taus = {}
    for fu in tf:
        k, f, ll = fu.result()
        taus[(k, f)] = ll
    return fits, taus


def globals_for(fit, taus, seed: int):
    return jr.globals_a(fit, taus, R.DRAWS, seed, beta=ao.beta_draws(fit, R.DRAWS, seed))


# ---------------------------------------------------------------------------------------------------------
# Tiers and tests (D-079's, with A′ in place of Form B)
# ---------------------------------------------------------------------------------------------------------


def tiers_for_state(held, inputs, places_held, fits, taus, seed):
    city = inputs["city"]
    targets = [pl for pl in places_held if pl.geoid != city and R.target_cols(pl).any()]
    if not targets:
        return [
            {
                "held_out": held,
                "form": f,
                "tier": t,
                "targets": 0,
                "tier2_city": city,
                "useful": False,
                "note": "no place to score besides the tier-2 city",
            }
            for f in FORMS
            for t in (0, 1, 2)
        ], []
    obs = float(sum(pl.y[R.target_cols(pl)].sum() for pl in targets))
    rows, ls_rows = [], []
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
        for pl in targets:
            t1 = jr.subset_years(inputs["t1"][pl.geoid], R.TARGET_YEARS)
            ls_rows.append(
                {
                    "held_out": held,
                    "form": form,
                    "geoid": pl.geoid,
                    "name": pl.name,
                    "log_score_tier1": jr.held_out_log_score(t1, g),
                }
            )
    return rows, ls_rows


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
                {
                    "form": form,
                    "state": pl.state,
                    "geoid": pl.geoid,
                    "name": pl.name,
                    "years": int(cols.sum()),
                    "z": ao.place_z(pl),
                }
                | jr.score(obs, d)
            )
    return rows


def test_b_rows(store, fits, z_of: dict, seed) -> tuple[list[dict], list[dict]]:
    rolls = roll_towns()
    per, tot = [], []
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
            for pl in pls:
                per.append(
                    {"form": form, "state": st, "geoid": pl.geoid, "name": pl.name, "z": ao.place_z(pl)}
                    | jr.score(float(gained[pl.geoid]), d[pl.geoid].sum(axis=1))
                )
    return tot, per


def verdicts(tiers: pd.DataFrame, ls: pd.DataFrame, ta: pd.DataFrame, tb: pd.DataFrame) -> dict:
    claim = {f: jr.claim_tier(tiers[tiers["form"] == f]) for f in FORMS}
    passes = {}
    for f in FORMS:
        a, b = ta[ta["form"] == f], tb[tb["form"] == f]
        passes[f] = {
            "A": {st: jr.test_a_pass(a[a["state"] == st]) for st in R.STATES},
            "B": {
                st: (bool(b.loc[b["state"] == st, "pass"].iloc[0]) if (b["state"] == st).any() else None)
                for st in R.STATES
            },
        }
    piv = ls.pivot_table(index="geoid", columns="form", values="log_score_tier1")
    gain, se = sc.paired((piv["A′"] - piv["A"]).dropna())
    n_tests = {f: jr.tests_passed(passes[f]) for f in FORMS}
    dec = ao.decide(claim["A"], claim["A′"], gain, se, n_tests["A"], n_tests["A′"])
    useful = {
        f: {
            int(t): int(tiers[(tiers["form"] == f) & (tiers["tier"] == t)]["useful"].sum()) for t in (0, 1, 2)
        }
        for f in FORMS
    }
    return {
        "claim_tier": claim,
        "useful_states_by_tier": useful,
        "tests": passes,
        "tests_passed": n_tests,
        "log_gain_a_prime_over_a": gain,
        "log_gain_se": se,
        "places_scored": int(piv.dropna().shape[0]),
        "decision": dataclasses.asdict(dec),
    }


# ---------------------------------------------------------------------------------------------------------
# Sensitivities
# ---------------------------------------------------------------------------------------------------------


def two_term(places, fit, z2: np.ndarray) -> dict:
    """Form A′ plus a second place term at the chosen cell: (β_o, β_2) by nested golden search."""
    prep = scr.prepare(places, cal._cvals(fit.m_owner, fit.m_other))
    z1 = np.array([ao.place_z(p) for p in places])

    def inner(b2):
        return scr._golden(
            lambda b1: scr._profile(prep, b1 * z1 + b2 * z2, 1.0, False).loglik, *scr.BETA, tol=1e-3
        )

    b2, _ = scr._golden(lambda b2: inner(b2)[1], *scr.BETA, tol=1e-3)
    b1, _ = inner(b2)
    best = scr._profile(prep, b1 * z1 + b2 * z2, 1.0, False)
    one = scr._profile(prep, z1, fit.beta, False)
    stat = max(0.0, 2 * (best.loglik - one.loglik))
    return {
        "beta_owner": b1,
        "beta_pre1960": b2,
        "alpha": best.alpha,
        "theta": best.theta["all"],
        "loglik": best.loglik,
        "lr_vs_a_prime": stat,
        "p": scr.lr_p(stat),
    }


def within_state(places, fit) -> dict:
    prep = scr.prepare(places, cal._cvals(fit.m_owner, fit.m_other))
    z = np.array([ao.place_z(p) for p in places])
    best = scr.fit(prep, z, within=True)
    lo, hi = scr.beta_interval(prep, z, best, within=True)
    null = scr.fit(prep, z, within=True, beta=0.0)
    return {
        "beta": best.beta,
        "beta_low": lo,
        "beta_high": hi,
        "alpha": best.alpha,
        "alpha_beta0": null.alpha,
        "theta_by_state": best.theta,
    }


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


def inputs(store):
    places, new = R.all_places(store)
    items = [(p.state, p.geoid, p.name) for p in places] + [
        (r.state, r.geoid, r.name) for r in roll_towns().itertuples()
    ]
    own = owner_table(store, list(dict.fromkeys(items)))
    return places, new, own


def vintage_check(own: pd.DataFrame, fit_geoids: set[str]) -> dict:
    f = own[own["geoid"].isin(fit_geoids) & own["share_fit"].notna() & own["share_latest"].notna()]
    return {
        "places": len(f),
        "pearson": float(f["share_fit"].corr(f["share_latest"])),
        "spearman": float(f["share_fit"].rank().corr(f["share_latest"].rank())),
        "mean_change_points": float((f["share_latest"] - f["share_fit"]).mean() * 100),
        "max_abs_change_points": float((f["share_latest"] - f["share_fit"]).abs().max() * 100),
        "by_source": own[own["geoid"].isin(fit_geoids)]["source"].value_counts().to_dict(),
        "flagged": own[own["geoid"].isin(fit_geoids) & (own["flag"] != "")]["name"].tolist(),
    }


def run(a, store) -> None:
    places, new, own = inputs(store)
    own.to_csv(a.out / "owner_share.csv", index=False)
    vc = vintage_check(own, {p.geoid for p in places})
    log(f"fit set: {len(places)} places, {sum(len(p.y) for p in places)} place-years, {len(new)} new")
    log(f"owner share sources: {vc['by_source']}; flagged: {vc['flagged']}")
    log(
        f"vintage check (2011-15 vs 2020-24, {vc['places']} places): pearson {vc['pearson']:.3f}, "
        f"spearman {vc['spearman']:.3f}, mean change {vc['mean_change_points']:+.1f} points"
    )
    summary = {
        "fit_set": {"places": len(places), "new": sorted(new)},
        "vintage_check": vc,
        "z": {"center": CENTER, "scale": SCALE, "fit_end_year": FIT_END},
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    if a.inputs_only:
        return
    z_fit = dict(zip(own["geoid"], own["z_fit"], strict=True))
    pz = [ao.with_z(p, z_fit[p.geoid]) for p in places]
    jobs = {"all": pz} | {f"without {st}": [p for p in pz if p.state != st] for st in R.STATES}
    jobs |= {f"without place {g}": [p for p in pz if p.geoid != g] for g in sorted(new)}
    loso = [f"without {st}" for st in R.STATES]
    with ProcessPoolExecutor(a.workers) as pool:
        log("fits: Form A (β_o = 0) and Form A′, all folds")
        fits, taus = run_fits(pool, jobs, tau_for=loso)
        z_s = dict(zip(own["geoid"], own["z_sens"], strict=True))
        ps = [ao.with_z(p, z_s[p.geoid]) for p in places]
        log("sensitivity: owner share from 2016-20")
        sjobs = {"all": ps} | {f"without {st}": [p for p in ps if p.state != st] for st in R.STATES}
        sfits, staus = run_fits(pool, sjobs, forms=("A′",), tau_for=loso)
    fit_rows = [fit_row("central", k, f, v) for (k, f), v in fits.items()]
    fit_rows += [fit_row("2016-20 vintage", k, f, v) for (k, f), v in sfits.items()]
    pd.DataFrame(fit_rows).to_csv(a.out / "fits.csv", index=False)

    tier_rows, ls_rows, s_rows = [], [], []
    for st in R.STATES:
        held = [p for p in pz if p.state == st]
        inp = R.tier_inputs(st, store, held)
        log(f"  {st}: tier-2 city {inp['city']}")
        r, ls = tiers_for_state(st, inp, held, fits, taus, R.SEED)
        tier_rows += r
        ls_rows += ls
        held_s = [p for p in ps if p.state == st]
        inp_s = R.tier_inputs(st, store, held_s)
        sf = {(k, "A"): fits[(k, "A")] for k in jobs if k in sjobs} | sfits
        st_ = {(k, "A"): taus[(k, "A")] for k in loso} | staus
        r2, _ = tiers_for_state(st, inp_s, held_s, sf, st_, R.SEED)
        s_rows += [x for x in r2 if x["form"] == "A′"]
    tiers = pd.DataFrame(tier_rows)
    ls = pd.DataFrame(ls_rows)
    tiers.to_csv(a.out / "tiers.csv", index=False)
    ls.to_csv(a.out / "logscores_tier1.csv", index=False)
    pd.DataFrame(s_rows).to_csv(a.out / "tiers_2016_20.csv", index=False)

    ta = pd.DataFrame(test_a_rows([p for p in pz if p.geoid in new], fits, R.SEED))
    ta.to_csv(a.out / "test_a.csv", index=False)
    tb, tbp = test_b_rows(store, fits, z_fit, R.SEED)
    tb, tbp = pd.DataFrame(tb), pd.DataFrame(tbp)
    tb.to_csv(a.out / "test_b.csv", index=False)
    tbp.to_csv(a.out / "test_b_towns.csv", index=False)

    summary["central"] = verdicts(tiers, ls, ta, tb)
    log(f"decision: {summary['central']['decision']}")
    s_t = pd.DataFrame(s_rows)
    summary["sensitivity_2016_20"] = {
        "fit": fit_row("2016-20 vintage", "all", "A′", sfits[("all", "A′")]),
        "claim_tier": jr.claim_tier(s_t) if len(s_t) else None,
        "useful_states_by_tier": {int(t): int(s_t[s_t["tier"] == t]["useful"].sum()) for t in (0, 1, 2)},
    }
    fa = fits[("all", "A′")]
    log("sensitivity: β_o within states")
    summary["sensitivity_within_state"] = within_state(pz, fa)
    fac = pd.read_csv(
        HERE.parents[1] / "reports" / "adu-covariate-screen" / "factors.csv", dtype={"geoid": str}
    )
    x2 = fac.set_index("geoid")["X2"]
    m, s = float(x2.mean()), float(x2.std(ddof=0))
    z2 = np.array([0.0 if pd.isna(x2.get(p.geoid)) else (x2[p.geoid] - m) / s for p in pz])
    log("outlook: A′ plus pre-1960 share")
    summary["outlook_pre1960"] = two_term(pz, fa, z2) | {
        "x2_center": m,
        "x2_scale": s,
        "places_without_x2": int((x2.reindex([p.geoid for p in pz]).isna()).sum()),
    }
    summary["form_a_check_vs_d079"] = {
        "d079": {
            "theta": 0.000756299362297198,
            "alpha": 1.918380315170198,
            "m_owner": 1.0,
            "m_other": 0.4,
            "loglik": -1347.7126927902486,
        },
        "here": {
            k: getattr(fits[("all", "A")], k) for k in ("theta", "alpha", "m_owner", "m_other", "loglik")
        },
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    sys.exit(main())
