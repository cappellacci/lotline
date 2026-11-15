#!/usr/bin/env python3
"""D-091: D-090's forecasts with a per-place drift d = exp(σ z), σ learned leaving one state out.

    cd ~/Engineering/lotline   # .env lives here
    PYTHONPATH=<wt>/src .venv/bin/python <wt>/scripts/dev/adu_drift.py \
        --d090 <wt>/reports/adu-time-split --out <wt>/reports/adu-drift --workers 7

Reads D-090's outputs (`places.csv` for the classes, `summary.json` for F1's fit) and rebuilds D-090's places
and draws unchanged. Then, once:

1. **Log scores on a fixed-drift grid** (`adu_forecast.LOGD_GRID`) for every scored place, F0 and F1. The
   value at log d = 0 is D-090's score; the run checks it against `place_scores.csv` (the rollback check).
2. **σ leaving one state out**, per forecaster: for held-out state s, σ maximizes the other scored states'
   window likelihood with d integrated (`fit_sigma`). Sensitivity: (μ, σ) learned the same way.
3. **Draws with drift** (independent places; and one d shared by a state, the correlated bound), scores per
   place and per state, calibration, and the side-by-side evidence D-091 promised: with against without drift.

Holdouts as D-090 (St. Paul out; no `--unblind`). Runs inside `offline_build`. Writes only to `--out`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.io import DataStore, offline
from lotline.model import adu_forecast as af
from lotline.model import joint_refit as jr
from lotline.model import score as sc

HERE = Path(__file__).resolve().parent
SCORED = ("MN", "NC", "TX", "OR")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


R = _load("adu_joint_refit")


def state_fit(d: dict) -> af.StateFit:
    d = dict(d)
    for k in ("owner_interval", "other_interval", "use", "betas"):
        d[k] = tuple(d[k])
    d["cov"] = tuple(tuple(r) for r in d["cov"])
    return af.StateFit(**d)


def grid_task(args):
    """(geoid, F0 grid or None, F1 grid) for one place."""
    geoid, cls, fp, wp, fit, st, draws, seed = args
    g = af.state_globals(fit, st, draws, seed)
    if cls == "new":
        return geoid, None, af.new_log_score_grid(wp, g, af.LOGD_GRID)
    f0 = np.array([af.f0_log_score(fp, wp, ld) for ld in af.LOGD_GRID]) if cls == "history" else None
    return geoid, f0, af.own_log_score_grid(fp, wp, g, af.LOGD_GRID)


def place_draws(cls, fp, wp, g, seed, mult):
    """(F0 totals or None, F1 totals) per draw over the window."""
    if cls == "new":
        return None, af.predict_new(wp, g, seed, mult).sum(axis=1)
    f0 = af.f0_draws(fp, wp, len(g.scale), seed, mult).sum(axis=1) if cls == "history" else None
    return f0, af.predict_own(fp, wp, g, seed, mult).sum(axis=1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--d090", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--smoke", action="store_true", help="code-path check only: 500 draws")
    a = ap.parse_args()
    if a.smoke:
        R.DRAWS = 500
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        run(a, store)


def run(a, store) -> None:
    pr = pd.read_csv(a.d090 / "places.csv", dtype={"geoid": str})
    cls = dict(zip(pr["geoid"], pr["class"], strict=True))
    d090 = json.loads((a.d090 / "summary.json").read_text())
    f1 = state_fit(d090["fits"]["F1"])
    old = pd.read_csv(a.d090 / "place_scores.csv", dtype={"geoid": str}).set_index("geoid")
    places, _ = R.all_places(store)
    parts = {}
    for p in places:
        if p.state in SCORED and cls[p.geoid] in ("history", "new", "thin"):
            fp, wp = af.split(p)
            parts[p.geoid] = (p.state, cls[p.geoid], fp, wp)
    log(f"places scored: {pd.Series([v[1] for v in parts.values()]).value_counts().to_dict()}")

    # 1. log scores on the drift grid
    jobs = [(g, c, fp, wp, f1, st, R.DRAWS, R.SEED) for g, (st, c, fp, wp) in parts.items()]
    grids0, grids1 = {}, {}
    with ProcessPoolExecutor(a.workers) as pool:
        for g, f0g, f1g in pool.map(grid_task, jobs):
            grids0[g], grids1[g] = f0g, f1g
    log(f"grids: {len(grids1)} places x {len(af.LOGD_GRID)} drift values")
    i0 = int(np.argmin(np.abs(af.LOGD_GRID)))
    gap = max(
        max(abs(grids1[g][i0] - old.loc[g, "ls_F1"]) for g in grids1),
        max(abs(grids0[g][i0] - old.loc[g, "ls_F0"]) for g in grids0 if grids0[g] is not None),
    )
    log(f"rollback check: largest gap to D-090's log scores at d = 1: {gap:.2e}")
    np.savez_compressed(a.out / "logscore_grids.npz", logd=af.LOGD_GRID,
                        **{f"F1_{g}": v for g, v in grids1.items()},
                        **{f"F0_{g}": v for g, v in grids0.items() if v is not None})  # fmt: skip

    # 2. σ leaving one state out
    hist = [g for g in parts if parts[g][1] == "history"]
    sig, musig = {}, {}
    for st in SCORED:
        train = [g for g in hist if parts[g][0] != st]
        for name, grids in (("F0", grids0), ("F1", grids1)):
            sig[(name, st)] = af.fit_sigma([grids[g] for g in train])
            musig[(name, st)] = af.fit_mu_sigma([grids[g] for g in train])
            log(f"  sigma {name} without {st}: {sig[(name, st)]:.3f}; (mu, sigma) {musig[(name, st)]}")
    sig_all = {n: af.fit_sigma([gr[g] for g in hist]) for n, gr in (("F0", grids0), ("F1", grids1))}
    log(f"  sigma on all four states (reported only, not used): {sig_all}")

    # 3. draws, scores, evidence
    variants = {
        "none": lambda name, st, g: None,
        "drift": lambda name, st, g: af.drift_mult(R.DRAWS, sig[(name, st)], R.SEED, g),
        "drift, shared by state": lambda name, st, g: af.drift_mult(R.DRAWS, sig[(name, st)], R.SEED, st),
        "drift, log-mean learned": lambda name, st, g: af.drift_mult(
            R.DRAWS, musig[(name, st)][1], R.SEED, g, mu=musig[(name, st)][0]
        ),
    }
    place_rows, tot_rows = [], []
    for st in SCORED:
        g1 = af.state_globals(f1, st, R.DRAWS, R.SEED)
        mine = [g for g in parts if parts[g][0] == st]
        for var, mk in variants.items():
            draws = {}
            for g in mine:
                _, c, fp, wp = parts[g]
                d0, _ = (
                    place_draws(c, fp, wp, g1, R.SEED, mk("F0", st, g)) if c == "history" else (None, None)
                )
                _, d1 = place_draws(c, fp, wp, g1, R.SEED, mk("F1", st, g))
                draws[g] = {"F0": d0, "F1": d1}
                obs = float(wp.y.sum())
                for name, d in (("F0", d0), ("F1", d1)):
                    if d is None:
                        continue
                    s = jr.score(obs, d)
                    if var == "none":
                        ls = (grids0 if name == "F0" else grids1)[g][i0]
                    elif var == "drift":
                        ls = af.drift_loglik((grids0 if name == "F0" else grids1)[g], sig[(name, st)])
                    elif var == "drift, log-mean learned":
                        m_, s_ = musig[(name, st)]
                        ls = af.drift_loglik((grids0 if name == "F0" else grids1)[g], s_, m_)
                    else:
                        ls = math.nan  # not separable by place when d is shared
                    place_rows.append(
                        {"state": st, "geoid": g, "name": wp.name, "class": c, "variant": var,
                         "forecaster": name, "observed": obs, "p10": s["p10"], "p50": s["p50"],
                         "p90": s["p90"], "inside": s["inside"], "percentile": s["percentile"],
                         "crps": s["crps"], "log_score": ls}
                    )  # fmt: skip
            for line, keep in (
                ("history", "history"),
                ("new places in a known state", "new"),
                ("thin", "thin"),
            ):
                gs = [g for g in mine if parts[g][1] == keep]
                if not gs:
                    continue
                obs = float(sum(parts[g][3].y.sum() for g in gs))
                for name in ("F0", "F1"):
                    if any(draws[g][name] is None for g in gs):
                        continue
                    tot = sum(draws[g][name] for g in gs)
                    tot_rows.append(
                        {"state": st, "line": line, "variant": var, "forecaster": name, "places": len(gs)}
                        | jr.score(obs, tot)
                    )
    pl, tot = pd.DataFrame(place_rows), pd.DataFrame(tot_rows)
    pl.to_csv(a.out / "place_scores.csv", index=False)
    tot.to_csv(a.out / "totals.csv", index=False)

    h = pl[pl["class"] == "history"]
    th = tot[tot.line == "history"]

    def piv(var, name, col):
        return h[(h.variant == var) & (h.forecaster == name)].set_index("geoid")[col]

    evidence = {}
    for name in ("F0", "F1"):
        e = {}
        for var in ("drift", "drift, log-mean learned"):
            ls_gain = sc.paired((piv(var, name, "log_score") - piv("none", name, "log_score")).dropna())
            crps_gain = sc.paired((piv("none", name, "crps") - piv(var, name, "crps")).dropna())
            e[var] = {"log_score_gain": list(ls_gain), "crps_reduction_places": list(crps_gain)}
        for var in variants:
            r = th[(th.variant == var) & (th.forecaster == name)]
            q = h[(h.variant == var) & (h.forecaster == name)]
            share, ok = af.coverage(q["inside"])
            e.setdefault("by_variant", {})[var] = {
                "useful_states": {s_: bool(r.set_index("state").loc[s_, "useful"]) for s_ in SCORED},
                "inside_states": {s_: bool(r.set_index("state").loc[s_, "inside"]) for s_ in SCORED},
                "state_total_crps_sum": float(r["crps"].sum()),
                "place_coverage": share,
                "place_coverage_ok": ok,
                "place_log_score_sum": float(q["log_score"].sum()) if q["log_score"].notna().all() else None,
            }
        e["improves"] = e["drift"]["log_score_gain"][0] > 2 * e["drift"]["log_score_gain"][1]
        evidence[name] = e
    useful = {n: evidence[n]["by_variant"]["drift"]["useful_states"] for n in ("F0", "F1")}
    g10 = sc.paired(piv("drift", "F1", "log_score") - piv("drift", "F0", "log_score"))
    n1, n0 = sum(useful["F1"].values()), sum(useful["F0"].values())
    verdict = {
        "rule1_F1d_useful_states": n1,
        "rule1_F0d_useful_states": n0,
        "rule1_pass_F1d": n1 >= af.USEFUL_STATES,
        "rule1_pass_F0d": n0 >= af.USEFUL_STATES,
        "rule2_F1d_minus_F0d": list(g10),
        "rule2_pass": g10[0] > 2 * g10[1],
        "rule3_coverage": {n: evidence[n]["by_variant"]["drift"]["place_coverage"] for n in ("F0", "F1")},
        "rule3_pass": {n: evidence[n]["by_variant"]["drift"]["place_coverage_ok"] for n in ("F0", "F1")},
        "improves": {n: evidence[n]["improves"] for n in ("F0", "F1")},
    }
    summary = {
        "sigma_loso": {f"{n} without {s_}": v for (n, s_), v in sig.items()},
        "mu_sigma_loso": {f"{n} without {s_}": v for (n, s_), v in musig.items()},
        "sigma_all_states_reported_only": sig_all,
        "rollback_check_max_gap": gap,
        "evidence": evidence,
        "verdict": verdict,
        "draws": R.DRAWS,
        "d090_commit": "d03ec95e",
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    for name in ("F0", "F1"):
        e = evidence[name]
        bv = e["by_variant"]
        log(
            f"{name}: log-score gain with drift {e['drift']['log_score_gain'][0]:+.1f} "
            f"(2 SE {2 * e['drift']['log_score_gain'][1]:.1f}); coverage "
            f"{bv['none']['place_coverage']:.2f} -> {bv['drift']['place_coverage']:.2f}; useful states "
            f"{sum(bv['none']['useful_states'].values())} -> {sum(bv['drift']['useful_states'].values())}"
        )
    log(f"verdict: {verdict}")
    log("done")


if __name__ == "__main__":
    sys.exit(main())
