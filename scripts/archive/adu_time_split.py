#!/usr/bin/env python3
"""D-090: the within-state ADU forecast test. Fit on 2016-2019, forecast 2021-2025, state by state.

    cd ~/Engineering/lotline   # .env lives here
    PYTHONPATH=<wt>/src .venv/bin/python <wt>/scripts/archive/adu_time_split.py --inputs-only --out <dir>
    PYTHONPATH=<wt>/src .venv/bin/python <wt>/scripts/archive/adu_time_split.py --out <dir> --workers 3

`--inputs-only` builds D-087's fit set, classifies each place (history, new, thin, none), lists the rule
changes inside 2020-2025 by code, reads housing age (D-087's reader), and writes `places.csv` before any fit.
Without it the script then runs, once:

1. **Fits on the fit years only** (`adu_forecast.fit_within`): F1 (Form A, one θ per state) and F2 (F1 plus
   housing age), every (m_o, m_x) cell; then each state's trend (the sensitivity) at F1's α and cell.
2. **Forecasts** for 2021-2025: F0 (persistence), F1 and F2 (own-history u), the trend sensitivity. New places
   in a known state draw u from the prior (F1, F2).
3. **Scores** per state and line (places with history; places with a rule change; new places; thin): the
   window total against summed draws (`joint_refit.score`) and the per-place held-out log score.
4. **D-090's rule** (`adu_forecast.decide`).

Holdouts: St. Paul is out of the fit set (`adu_joint_refit.fit_set`); ACS rows pass `holdout.apply_acs`. No
`--unblind`. Runs inside `offline_build`. Writes only to `--out`; nothing to config.
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

from lotline.calibrate.adu import adu_forecast as af
from lotline.calibrate.adu import adu_terms as at
from lotline.calibrate.adu import joint_refit as jr
from lotline.calibrate.adu import score as sc
from lotline.io import DataStore, offline

HERE = Path(__file__).resolve().parent
SCORED = ("MN", "NC", "TX", "OR")  # D-090: Ohio has no counts before 2024
FORECASTERS = ("F0", "F1", "F2", "F1 + trend")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


AGE = _load("adu_age_refit")  # D-087's housing-age reader (loads adu_owner_refit and adu_joint_refit)
R = AGE.R
GRID = af.cal.GRID3


# ---------------------------------------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------------------------------------


def place_rows(places, z_age: dict) -> pd.DataFrame:
    rows = []
    for pl in places:
        f, w = af.split(pl)
        rows.append(
            {
                "state": pl.state,
                "geoid": pl.geoid,
                "name": pl.name,
                "class": af.place_class(pl),
                "fit_years": "" if f is None else f"{f.years.min()}-{f.years.max()}",
                "n_fit_years": 0 if f is None else len(f.years),
                "window_years": "" if w is None else f"{w.years.min()}-{w.years.max()}",
                "n_window_years": 0 if w is None else len(w.years),
                "rule_change_years": " ".join(str(y) for y in af.rule_change_years(pl)),
                "z_age": z_age.get(pl.geoid, 0.0),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Fits
# ---------------------------------------------------------------------------------------------------------


def describe(f: af.StateFit) -> str:
    th = ", ".join(
        f"{s} {f.theta[s] * 1000:.3f} ({f.low[s] * 1000:.3f}-{f.high[s] * 1000:.3f})" for s in sorted(f.theta)
    )
    b = ", ".join(f"{v:+.3f} (SE {s:.3f})" for v, s in zip(f.betas, f.beta_se, strict=True))
    return (
        f"theta per 1,000 [{th}], alpha {f.alpha:.3f}, m_o {f.m_owner}, m_x {f.m_other}, "
        f"betas [{b}], loglik {f.loglik:.2f}"
    )


def fit_rows(fits: dict, trends: dict) -> list[dict]:
    rows = []
    for name, f in fits.items():
        for s in sorted(f.theta):
            rows.append(
                {"forecaster": name, "state": s, "theta": f.theta[s], "theta_low": f.low[s],
                 "theta_high": f.high[s], "alpha": f.alpha, "m_owner": f.m_owner, "m_other": f.m_other,
                 "owner_estimated": f.owner_estimated, "other_estimated": f.other_estimated,
                 "beta_age": f.betas[0] if f.betas else 0.0, "beta_age_se": f.beta_se[0] if f.betas else 0.0,
                 "loglik": f.loglik, "n_places": f.n_places, "n_years": f.n_years}
            )  # fmt: skip
    for s, (gamma, theta) in trends.items():
        rows.append({"forecaster": "F1 + trend", "state": s, "theta": theta, "trend_per_year": gamma})
    return rows


# ---------------------------------------------------------------------------------------------------------
# Forecasts and scores
# ---------------------------------------------------------------------------------------------------------


def forecast_state(st, parts: dict, cls: dict, fits: dict, trends: dict, seed: int):
    """Draws and per-place scores for one state. parts: geoid -> (fit part, window part), on F1's places
    (F2's places carry z_age)."""
    f1, f2 = fits["F1"], fits["F2"]
    g1 = af.state_globals(f1, st, R.DRAWS, seed)
    g2 = af.state_globals(f2, st, R.DRAWS, seed)
    gamma, theta_t = trends[st]
    ft = dataclasses.replace(f1, theta={**f1.theta, st: theta_t},
                             low={**f1.low, st: theta_t * f1.low[st] / f1.theta[st]},
                             high={**f1.high, st: theta_t * f1.high[st] / f1.theta[st]})  # fmt: skip
    gt = af.state_globals(ft, st, R.DRAWS, seed)
    draws, scores = {}, []
    for g, (fp, wp, fp2, wp2) in parts.items():
        c = cls[g]
        obs = float(wp.y.sum())
        row = {"state": st, "geoid": g, "name": wp.name, "class": c, "observed": obs,
               "window_years": len(wp.years)}  # fmt: skip
        d = {}
        if c in ("history", "thin"):
            if c == "history":
                d["F0"] = af.f0_draws(fp, wp, R.DRAWS, seed).sum(axis=1)
                row["ls_F0"] = af.f0_log_score(fp, wp)
            d["F1"] = af.predict_own(fp, wp, g1, seed).sum(axis=1)
            row["ls_F1"] = af.own_log_score(fp, wp, g1)
            d["F2"] = af.predict_own(fp2, wp2, g2, seed).sum(axis=1)
            row["ls_F2"] = af.own_log_score(fp2, wp2, g2)
            fpt, wpt = af.with_trend(fp, gamma), af.with_trend(wp, gamma)
            d["F1 + trend"] = af.predict_own(fpt, wpt, gt, seed).sum(axis=1)
            row["ls_F1 + trend"] = af.own_log_score(fpt, wpt, gt)
        else:  # new: u from the prior
            d["F1"] = jr.predict([wp], g1, seed)[g].sum(axis=1)
            row["ls_F1"] = jr.held_out_log_score(wp, g1)
            d["F2"] = jr.predict([wp2], g2, seed)[g].sum(axis=1)
            row["ls_F2"] = jr.held_out_log_score(wp2, g2)
        for k, v in d.items():
            s = jr.score(obs, v)
            row |= {f"p10_{k}": s["p10"], f"p50_{k}": s["p50"], f"p90_{k}": s["p90"]}
        draws[g] = d
        scores.append(row)
    return draws, scores


def totals(st, line, geoids, draws, places_obs) -> list[dict]:
    if not geoids:
        return []
    obs = float(sum(places_obs[g] for g in geoids))
    out = []
    for k in FORECASTERS:
        if not all(k in draws[g] for g in geoids):
            continue
        tot = sum(draws[g][k] for g in geoids)
        out.append({"state": st, "line": line, "forecaster": k, "places": len(geoids)} | jr.score(obs, tot))
    return out


def verdict(tot: pd.DataFrame, ps: pd.DataFrame) -> dict:
    hist = tot[tot["line"] == "history"]

    def useful(k):
        r = hist[hist["forecaster"] == k].set_index("state")["useful"]
        return {st: bool(r.get(st, False)) for st in SCORED}

    h = ps[ps["class"] == "history"]
    g10, s10 = sc.paired(h["ls_F1"] - h["ls_F0"])
    g21, s21 = sc.paired(h["ls_F2"] - h["ls_F1"])
    v = af.decide(useful("F1"), useful("F2"), g10, s10, g21, s21)
    by_state = {}
    for st in SCORED:
        hs = h[h["state"] == st]
        if len(hs) > 1:
            by_state[st] = {"F1 - F0": list(sc.paired(hs["ls_F1"] - hs["ls_F0"])), "places": len(hs)}
        elif len(hs) == 1:
            by_state[st] = {"F1 - F0": [float((hs["ls_F1"] - hs["ls_F0"]).iloc[0]), None], "places": 1}
    return {
        "useful_F0": useful("F0"),
        "useful_F1": useful("F1"),
        "useful_F2": useful("F2"),
        "useful_trend": useful("F1 + trend"),
        "log_gain_F1_over_F0": [g10, s10],
        "log_gain_F2_over_F1": [g21, s21],
        "log_gain_trend_over_F1": list(sc.paired(h["ls_F1 + trend"] - h["ls_F1"])),
        "log_gain_by_state": by_state,
        "places_scored": int(len(h)),
        "verdict": dataclasses.asdict(v),
    }


# ---------------------------------------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=3)
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
    places, _ = R.all_places(store)
    items = [(p.state, p.geoid, p.name) for p in places]
    age = AGE.age_table(store, items)
    age.to_csv(a.out / "housing_age.csv", index=False)
    z_age = dict(zip(age["geoid"], age["z_fit"], strict=True))
    pr = place_rows(places, z_age)
    pr.to_csv(a.out / "places.csv", index=False)
    summary = {
        "split": {"fit": [af.FIT_FIRST, af.FIT_LAST], "lead": af.LEAD_YEAR,
                  "window": [min(af.WINDOW_YEARS), max(af.WINDOW_YEARS)]},
        "places_by_state_and_class": {
            st: pr[pr["state"] == st]["class"].value_counts().to_dict() for st in R.STATES
        },
        "rule_change_places": pr.loc[pr["rule_change_years"] != "", ["state", "name", "class",
                                                                      "rule_change_years"]].to_dict("records"),
    }  # fmt: skip
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    for st in R.STATES:
        log(f"{st}: {summary['places_by_state_and_class'][st]}")
    log(f"rule changes in 2021-2025: {len(summary['rule_change_places'])} places")
    if a.inputs_only:
        return

    fit_parts = [f for f in (af.split(p)[0] for p in places) if f is not None]
    fit_parts2 = [at.with_zv(f, (z_age.get(f.geoid, 0.0),)) for f in fit_parts]
    log(f"fit: {len(fit_parts)} places, {sum(len(f.y) for f in fit_parts)} place-years, 2016-2019")
    fits = {}
    with ProcessPoolExecutor(a.workers) as pool:
        for name, pls, use in (("F1", fit_parts, ()), ("F2", fit_parts2, (0,))):
            t0 = time.time()
            fits[name] = af.fit_within(pls, use=use, grid=GRID, mapper=lambda f, xs: pool.map(f, xs))
            log(f"  {name}: {describe(fits[name])} ({time.time() - t0:.0f}s)")
    trends = {st: af.fit_trend(fit_parts, fits["F1"], st) for st in SCORED}
    for st, (gm, th) in trends.items():
        log(f"  trend {st}: {gm:+.3f} a year (×{np.exp(gm):.2f}), theta at 2019 {th * 1000:.3f}/1,000")
    pd.DataFrame(fit_rows(fits, trends)).to_csv(a.out / "fits.csv", index=False)

    cls = dict(zip(pr["geoid"], pr["class"], strict=True))
    tot_rows, score_rows = [], []
    for st in SCORED:
        parts = {}
        for p in places:
            if p.state != st or cls[p.geoid] == "none":
                continue
            fp, wp = af.split(p)
            p2 = at.with_zv(p, (z_age.get(p.geoid, 0.0),))
            fp2, wp2 = af.split(p2)
            parts[p.geoid] = (fp, wp, fp2, wp2)
        draws, scores = forecast_state(st, parts, cls, fits, trends, R.SEED)
        score_rows += scores
        obs = {r["geoid"]: r["observed"] for r in scores}
        rc = set(pr.loc[(pr["state"] == st) & (pr["rule_change_years"] != ""), "geoid"])
        for line, keep in (
            ("history", lambda g: cls[g] == "history"),
            ("history, rule change in window", lambda g, rc=rc: cls[g] == "history" and g in rc),
            ("history, no rule change", lambda g, rc=rc: cls[g] == "history" and g not in rc),
            ("new places in a known state", lambda g: cls[g] == "new"),
            ("thin history (1 fit year)", lambda g: cls[g] == "thin"),
        ):
            tot_rows += totals(st, line, [g for g in parts if keep(g)], draws, obs)
        for r in [t for t in tot_rows if t["state"] == st and t["line"] == "history"]:
            log(
                f"  {st} history {r['forecaster']}: obs {r['observed']:.0f}, P50 {r['p50']:.0f} "
                f"({r['p10']:.0f}-{r['p90']:.0f}), obs/P50 {r['obs_over_p50']:.2f}, useful {r['useful']}"
            )
    tot, ps = pd.DataFrame(tot_rows), pd.DataFrame(score_rows)
    tot.to_csv(a.out / "totals.csv", index=False)
    ps.to_csv(a.out / "place_scores.csv", index=False)
    summary["fits"] = {k: dataclasses.asdict(v) for k, v in fits.items()}
    summary["trends"] = {st: {"per_year": g, "theta_2019": t} for st, (g, t) in trends.items()}
    summary["central"] = verdict(tot, ps)
    summary["rows"] = "D-087's fit set and rule rows (PR #419 head ef37063f via ws/adu-age-term)"
    for line in summary["central"]["verdict"]["reasons"]:
        log(line)
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    sys.exit(main())
