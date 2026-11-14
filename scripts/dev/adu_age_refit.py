#!/usr/bin/env python3
"""D-087: Forms A, A′ (owner share) and A″ (owner share + housing age), refitted on the checked rule rows and
scored on D-084's tests.

    cd ~/Engineering/lotline   # .env lives here
    PYTHONPATH=<worktree>/src .venv/bin/python <worktree>/scripts/dev/adu_age_refit.py \
        --inputs-only --out <dir>
    PYTHONPATH=<worktree>/src .venv/bin/python <worktree>/scripts/dev/adu_age_refit.py --out <dir> --workers 7

`--inputs-only` builds the fit set, each place's owner share (D-084's reader) and housing age (the same
reader on B25034), the vintage check for age, and writes them before any fit. Without it the script then
runs, once:

1. **Three forms** with one fitter (`adu_terms.fit3_terms`): A (no term), A′ (owner), A″ (owner and age),
   on all places, leaving each state out, and leaving each new place out (test A).
2. **D-075's data-tier test**, tests A and B, the tier-1 held-out log score, as D-084 ran them; test C for
   Form A only (`adu_joint_refit.test_c_rows`; the engine has no place terms).
3. **D-087's decision**, two steps under D-084's rule (`adu_owner.decide`): A′ against A, then A″ against
   the base in use (A′ is not adopted on `main`, so the base is step 1's winner).
4. **Sensitivities**, reported, not used to choose: A″ within states; age without owner share; A″ at m_x 0.4.

Housing age is the share of units built in 1959 or earlier (ACS B25034, labels "1950 to 1959", "1940 to
1949", "1939 or earlier", as D-083), through `holdout.apply_acs`, read for each place as D-084 reads owner
share (place rows; township -> county subdivision; unincorporated -> county less its places; else z = 0 and a
flag). Everything runs inside `offline_build`. Writes only to `--out`.
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
from lotline.model import adu_terms as at
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr
from lotline.model import score as sc
from lotline.validation import holdout

HERE = Path(__file__).resolve().parent
OLD_HOMES = ("1950 to 1959", "1940 to 1949", "1939 or earlier")
FORMS = {"A": (), "A′": (0,), "A″": (0, 1)}  # terms used: 0 owner share, 1 housing age


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


OWN = _load("adu_owner_refit")  # D-084's owner-share reader (it loads adu_joint_refit as R)
R = OWN.R
PA = {k: v.value for k, v in load_params("adu_age").items()}
AGE_CENTER, AGE_SCALE = PA["adu_age_share_center"], PA["adu_age_share_scale"]


# ---------------------------------------------------------------------------------------------------------
# Housing age (D-084's reader, on B25034)
# ---------------------------------------------------------------------------------------------------------


def b25034(store, st: str) -> pd.DataFrame:
    """Units built before 1960 and all units per (geo, end_year), held-out rows removed. The columns are named
    `owner` (the part) and `total` because D-084's `owner_rows` reads those names."""
    a = holdout.apply_acs(store.read(st, "acs_geo_year"), st)
    a = a[a["table_id"] == "B25034"]
    lab = a["label"].astype(str).str.replace(":", "", regex=False).str.strip().str.lower()
    old = lab.map(lambda s: any(k in s for k in OLD_HOMES))
    tot = lab.isin(["total", "estimate!!total"])
    return pd.DataFrame(
        {
            "owner": a[old].groupby(["geo", "end_year"])["estimate"].sum(),
            "total": a[tot].groupby(["geo", "end_year"])["estimate"].sum(),
        }
    ).dropna()


def age_table(store, items: list[tuple[str, str, str]]) -> pd.DataFrame:
    rows = []
    for st in sorted({s for s, _, _ in items}):
        acs = b25034(store, st)
        juris = store.read(st, "jurisdictions")
        info = juris.set_index(juris["geoid"].astype(str))
        for s, g, name in items:
            if s != st:
                continue
            kind = str(info.at[g, "kind"]) if g in info.index else "place"
            county = str(info.at[g, "county_geoid"]) if g in info.index else ""
            by_year, source = OWN.owner_rows(st, g, kind, county, acs, juris)
            row = {"state": st, "geoid": g, "name": name, "kind": kind, "source": source}
            for tag, end in (("fit", OWN.FIT_END), ("latest", OWN.LATEST)):
                share, year = ao.vintage_share(by_year, end)
                row[f"share_{tag}"], row[f"vintage_{tag}"] = share, year
                row[f"z_{tag}"] = 0.0 if share is None else at.age_share_z(share, AGE_CENTER, AGE_SCALE)
            row["flag"] = "no housing age: z = 0" if row["share_fit"] is None else ""
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Fits
# ---------------------------------------------------------------------------------------------------------


GRID = cal.GRID3  # --smoke replaces it with a 2 x 2 grid to check the code path end to end


def fit_task(args):
    key, form, places, use, cell, grid = args
    t0 = time.time()
    return key, form, at.fit3_terms(places, use=use, cell=cell, grid=grid), time.time() - t0


def tau_task(args):
    key, form, places, fit = args
    b = fit.betas_full
    return key, form, cal.tau_profile([at.scaled(p, b) for p in places], fit.m_owner, fit.m_other)


def describe(f) -> str:
    bs = ", ".join(
        f"{b:+.3f} ({lo:+.3f}, {hi:+.3f})" for b, (lo, hi) in zip(f.betas, f.beta_interval, strict=True)
    )
    return (
        f"theta {f.theta * 1000:.4f}/1,000 ({f.low * 1000:.3f}-{f.high * 1000:.3f}), alpha {f.alpha:.3f}, "
        f"betas [{bs}], m_o {f.m_owner}, m_x {f.m_other}, loglik {f.loglik:.2f}"
    )


def fit_row(variant, fold, form, f) -> dict:
    d = {k: v for k, v in dataclasses.asdict(f).items() if not isinstance(v, tuple)}
    names = ("beta_owner", "beta_age")
    for j, b, (lo, hi), se in zip(f.use, f.betas, f.beta_interval, f.beta_se, strict=True):
        d |= {names[j]: b, f"{names[j]}_low": lo, f"{names[j]}_high": hi, f"{names[j]}_se": se}
    if len(f.use) == 2:
        d["beta_corr"] = f.cov[0][1] / (f.beta_se[0] * f.beta_se[1])
    return {"variant": variant, "fold": fold, "form": form} | d


def run_fits(pool, jobs: dict, forms: dict, tau_for=(), cell=None) -> tuple[dict, dict]:
    futs = [
        pool.submit(fit_task, (k, f, v, use, cell, GRID)) for k, v in jobs.items() for f, use in forms.items()
    ]
    fits = {}
    for fu in futs:
        k, f, fit, sec = fu.result()
        fits[(k, f)] = fit
        log(f"  {f} {k}: {describe(fit)} ({sec:.0f}s)")
    tf = [pool.submit(tau_task, (k, f, jobs[k], fits[(k, f)])) for k in tau_for for f in forms]
    taus = {}
    for fu in tf:
        k, f, ll = fu.result()
        taus[(k, f)] = ll
    return fits, taus


def globals_for(fit, taus, seed: int):
    return jr.globals_a(fit, taus, R.DRAWS, seed, beta=at.beta_draws(fit, R.DRAWS, seed))


# ---------------------------------------------------------------------------------------------------------
# Tiers and tests (D-084's, three forms)
# ---------------------------------------------------------------------------------------------------------


def tiers_for_state(held, inputs, places_held, fits, taus, seed):
    city = inputs["city"]
    targets = [pl for pl in places_held if pl.geoid != city and R.target_cols(pl).any()]
    if not targets:
        return [
            {"held_out": held, "form": f, "tier": t, "targets": 0, "tier2_city": city, "useful": False,
             "note": "no place to score besides the tier-2 city"}
            for f in FORMS for t in (0, 1, 2)
        ], []  # fmt: skip
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
                {"held_out": held, "form": form, "tier": tier, "targets": len(pls), "tier2_city": city,
                 "ess": ess if tier == 2 else np.nan}
                | jr.score(obs, tot)
            )  # fmt: skip
        for pl in targets:
            t1 = jr.subset_years(inputs["t1"][pl.geoid], R.TARGET_YEARS)
            ls_rows.append(
                {"held_out": held, "form": form, "geoid": pl.geoid, "name": pl.name,
                 "log_score_tier1": jr.held_out_log_score(t1, g)}
            )  # fmt: skip
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
                }
                | jr.score(obs, d)
            )
    return rows


def test_b_rows(store, fits, zv_of: dict, seed) -> tuple[list[dict], list[dict]]:
    rolls = OWN.roll_towns()
    per, tot = [], []
    for st, r in rolls.groupby("state"):
        y0, y1 = int(r["first_year"].min()), int(r["last_year"].max())
        pls = cal.place_data(
            st, store, list(r["geoid"]), range(y0, y1 + 1), counts=cal.count_settings(), require_counts=False
        )
        pls = [at.with_zv(pl, zv_of.get(pl.geoid, (0.0, 0.0))) for pl in pls]
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
                    {"form": form, "state": st, "geoid": pl.geoid, "name": pl.name}
                    | jr.score(float(gained[pl.geoid]), d[pl.geoid].sum(axis=1))
                )
    return tot, per


def _relabel(dec: ao.Decision, base: str, challenger: str) -> dict:
    """`adu_owner.decide` names its forms A (the base) and A′ (the challenger); report the forms by name."""
    return {
        "form": challenger if dec.form == "A′" else base,
        "reason": f"{dec.reason} [in this reason, A = {base}, A′ = {challenger}]",
    }


def verdicts(tiers: pd.DataFrame, ls: pd.DataFrame, ta: pd.DataFrame, tb: pd.DataFrame) -> dict:
    claim = {f: jr.claim_tier(tiers[tiers["form"] == f]) for f in FORMS}
    passes, n_tests = {}, {}
    for f in FORMS:
        a, b = ta[ta["form"] == f], tb[tb["form"] == f]
        passes[f] = {
            "A": {st: jr.test_a_pass(a[a["state"] == st]) for st in R.STATES},
            "B": {st: (bool(b.loc[b["state"] == st, "pass"].iloc[0]) if (b["state"] == st).any() else None)
                  for st in R.STATES},
        }  # fmt: skip
        n_tests[f] = jr.tests_passed(passes[f])
    piv = ls.pivot_table(index="geoid", columns="form", values="log_score_tier1")

    def gain(new, old):
        return sc.paired((piv[new] - piv[old]).dropna())

    g1, s1 = gain("A′", "A")
    step1 = _relabel(ao.decide(claim["A"], claim["A′"], g1, s1, n_tests["A"], n_tests["A′"]), "A", "A′")
    base = step1["form"]  # A′ is not adopted on main (#418 open), so the base is step 1's winner
    g2, s2 = gain("A″", base)
    step2 = _relabel(ao.decide(claim[base], claim["A″"], g2, s2, n_tests[base], n_tests["A″"]), base, "A″")
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
        "step1": step1 | {"log_gain": g1, "log_gain_se": s1},
        "base_for_step2": base,
        "step2": step2 | {"log_gain": g2, "log_gain_se": s2},
        "log_gain_a2_over_a": list(gain("A″", "A")),
        "places_scored": int(piv.dropna().shape[0]),
    }


# ---------------------------------------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--inputs-only", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="code-path check only: 2 x 2 grid, 500 draws")
    a = ap.parse_args()
    if a.smoke:
        global GRID
        GRID = (0.4, 1.0)
        R.DRAWS = 500
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        run(a, store)


def run(a, store) -> None:
    places, new = R.all_places(store)
    items = list(dict.fromkeys(
        [(p.state, p.geoid, p.name) for p in places]
        + [(r.state, r.geoid, r.name) for r in OWN.roll_towns().itertuples()]
    ))  # fmt: skip
    own = OWN.owner_table(store, items)
    age = age_table(store, items)
    own.to_csv(a.out / "owner_share.csv", index=False)
    age.to_csv(a.out / "housing_age.csv", index=False)
    fit_ids = {p.geoid for p in places}
    vc_own = OWN.vintage_check(own, fit_ids)
    vc_age = OWN.vintage_check(age, fit_ids)
    zf = age[age["geoid"].isin(fit_ids)]
    log(f"fit set: {len(places)} places, {sum(len(p.y) for p in places)} place-years, {len(new)} new")
    log(f"owner share sources {vc_own['by_source']}; flagged {vc_own['flagged']}")
    log(f"housing age sources {vc_age['by_source']}; flagged {vc_age['flagged']}")
    log(
        f"age vintage check (2011-15 vs 2020-24, {vc_age['places']} places): "
        f"pearson {vc_age['pearson']:.3f}, "
        f"spearman {vc_age['spearman']:.3f}, mean change {vc_age['mean_change_points']:+.1f} points"
    )
    z_own = dict(zip(own["geoid"], own["z_fit"], strict=True))
    z_age = dict(zip(age["geoid"], age["z_fit"], strict=True))
    corr = float(np.corrcoef([z_own[g] for g in zf["geoid"]], [z_age[g] for g in zf["geoid"]])[0, 1])
    summary = {
        "fit_set": {
            "places": len(places),
            "place_years": int(sum(len(p.y) for p in places)),
            "new": sorted(new),
        },
        "vintage_check_owner": vc_own,
        "vintage_check_age": vc_age,
        "z": {"owner": {"center": OWN.CENTER, "scale": OWN.SCALE},
              "age": {"center": AGE_CENTER, "scale": AGE_SCALE},
              "fit_end_year": OWN.FIT_END, "corr_owner_age_fit_places": corr},
    }  # fmt: skip
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log(f"owner-age correlation over the fit places: {corr:+.3f}")
    if a.inputs_only:
        return

    pz = [at.with_zv(p, (z_own[p.geoid], z_age[p.geoid])) for p in places]
    jobs = {"all": pz} | {f"without {st}": [p for p in pz if p.state != st] for st in R.STATES}
    jobs |= {f"without place {g}": [p for p in pz if p.geoid != g] for g in sorted(new)}
    loso = [f"without {st}" for st in R.STATES]
    with ProcessPoolExecutor(a.workers) as pool:
        log("fits: Forms A, A′ and A″, all folds")
        fits, taus = run_fits(pool, jobs, FORMS, tau_for=loso)
        fa2 = fits[("all", "A″")]
        log("sensitivity: age without owner share (Form A × exp(β_a z_a)), all places")
        age_only, _ = run_fits(pool, {"all": pz}, {"A + age": (1,)})
        log(f"sensitivity: A″ at m_x 0.4 (m_o {fa2.m_owner})")
        mx04, _ = run_fits(pool, {"all": pz}, {"A″ at m_x 0.4": (0, 1), "A′ at m_x 0.4": (0,)},
                           cell=(fa2.m_owner, 0.4))  # fmt: skip
    rows = [fit_row("central", k, f, v) for (k, f), v in fits.items()]
    rows += [fit_row("sensitivity", k, f, v) for (k, f), v in (age_only | mx04).items()]
    pd.DataFrame(rows).to_csv(a.out / "fits.csv", index=False)

    tier_rows, ls_rows = [], []
    for st in R.STATES:
        held = [p for p in pz if p.state == st]
        inp = R.tier_inputs(st, store, held)
        log(f"  {st}: tier-2 city {inp['city']}")
        r, ls = tiers_for_state(st, inp, held, fits, taus, R.SEED)
        tier_rows += r
        ls_rows += ls
    tiers, ls = pd.DataFrame(tier_rows), pd.DataFrame(ls_rows)
    tiers.to_csv(a.out / "tiers.csv", index=False)
    ls.to_csv(a.out / "logscores_tier1.csv", index=False)
    ta = pd.DataFrame(test_a_rows([p for p in pz if p.geoid in new], fits, R.SEED))
    ta.to_csv(a.out / "test_a.csv", index=False)
    zv_of = {g: (z_own.get(g, 0.0), z_age.get(g, 0.0)) for g in set(z_own) | set(z_age)}
    tb, tbp = test_b_rows(store, fits, zv_of, R.SEED)
    tb, tbp = pd.DataFrame(tb), pd.DataFrame(tbp)
    tb.to_csv(a.out / "test_b.csv", index=False)
    tbp.to_csv(a.out / "test_b_towns.csv", index=False)
    summary["central"] = verdicts(tiers, ls, ta, tb)
    log(f"step 1: {summary['central']['step1']}")
    log(f"step 2: {summary['central']['step2']}")

    log("test C for Form A (the scenario engine with Form A's values)")
    tc = pd.DataFrame(R.test_c_rows(store, fits[("all", "A")]))
    tc.to_csv(a.out / "test_c_form_a.csv", index=False)
    summary["test_c_form_a"] = {st: jr.test_c_pass(tc.loc[tc["state"] == st, "ratio"]) for st in R.STATES}

    log("sensitivity: A″ within states")
    summary["sensitivity_within_state"] = at.within_state(pz, fa2)
    fa = fits[("all", "A")]
    ao_ = age_only[("all", "A + age")]
    summary["sensitivity_age_only"] = fit_row("sensitivity", "all", "A + age", ao_) | {
        "lr_vs_a": max(0.0, 2 * (ao_.loglik - fa.loglik))
    }
    summary["sensitivity_mx_0_4"] = {f: fit_row("sensitivity", "all", f, v) for (_, f), v in mx04.items()}
    summary["lr"] = {
        "A′ vs A": max(0.0, 2 * (fits[("all", "A′")].loglik - fa.loglik)),
        "A″ vs A′": max(0.0, 2 * (fa2.loglik - fits[("all", "A′")].loglik)),
    }
    summary["rows"] = "PR #419 head ef37063f merged into ws/adu-age-term (not yet on main)"
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    sys.exit(main())
