#!/usr/bin/env python3
"""D-095: does the engine's ADU reform ratio match what happened where coded rules changed?

    PYTHONPATH=src python scripts/archive/adu_reform_ratio.py --out reports/adu-reform-ratio --workers 7

D-079's in-window events on the checked rule rows (`joint_refit.events`). For each, the after-years total is
forecast from the before years under P (no effect), M (the engine's ratio, config m_o and m_x) and M′ (the
ratio at m_o and m_x from the A + P fit without the event's place), with drift σ from config and, as a
sensitivity, without. Measures and reading rule: D-095 (`adu_reform_check`).

Offline from cached tables; St. Paul stays out (adu_joint_refit); nothing is unblinded or written to config.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import adu_reform_check as rc
import numpy as np
import pandas as pd

from lotline.calibrate.adu import calibrate_adu as cal
from lotline.calibrate.adu import joint_refit as jr
from lotline.calibrate.adu import score as sc
from lotline.config import load_params
from lotline.io import DataStore, offline
from lotline.model import adu_owner as ao

HERE = Path(__file__).resolve().parent
N = 20_000
SEED = 95


def _load(name: str, file: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TYP = _load("adu_types_refit", "adu_types_refit.py")
from lotline.model import adu_types as ty  # noqa: E402


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def gain(frame: pd.DataFrame, a: str, b: str) -> dict:
    g, se = sc.paired(frame[b] - frame[a])
    return {"gain": g, "se": se, "events": len(frame)}


def run(a, store) -> dict:
    places, _new, own = TYP.OWN.inputs(store)
    z_fit = dict(zip(own["geoid"], own["z_fit"], strict=True))
    fit_ids = {p.geoid for p in places}
    tt = TYP.type_table(store)
    fit_t = tt[tt["geoid"].isin(fit_ids)][["state", "geoid", "type_raw"]].rename(columns={"type_raw": "type"})
    mapping, _ = ty.merge_small(fit_t)
    tt["type"] = tt["type_raw"].map(mapping)
    types = dict(zip(tt["geoid"], tt["type"], strict=True))
    pz = TYP.attach([ao.with_z(p, z_fit[p.geoid]) for p in places], types)
    byg = {p.geoid: p for p in pz}

    ev = jr.events(pz)
    ev.to_csv(a.out / "events.csv", index=False)
    log(f"{len(ev)} events in {ev['state'].nunique()} states")

    params = load_params("adu")
    m_o, m_x = params["adu_owner_occupancy_share"].value, params["adu_partial_rule_share"].value
    sigma = params["adu_drift_sigma"].value
    log(f"engine m_o {m_o}, m_x {m_x}; drift sigma {sigma}")

    keys = sorted(set(ev["geoid"]))
    jobs = {f"without place {g}": {"A+P": [p for p in pz if p.geoid != g]} for g in keys}
    with ProcessPoolExecutor(a.workers) as pool:
        fits, _ = TYP.run_fits(pool, jobs, ("A+P",))

    rows = []
    for _, r in ev.iterrows():
        pl = byg[r.geoid]
        fit = fits[(f"without place {r.geoid}", "A+P")]
        e_m = rc.event_from(pl, int(r.year), cal._cvals(m_o, m_x))
        e_r = rc.event_from(pl, int(r.year), cal._cvals(fit.m_owner, fit.m_other))
        row = {
            "state": r.state,
            "geoid": r.geoid,
            "name": r["name"],
            "year": int(r.year),
            "dose_before": r.dose_before,
            "dose_after": r.dose_after,
            "years_before": int(r.years_before),
            "years_after": int(r.years_after),
            "y_before": e_m.y_before,
            "e_before": e_m.e_before,
            "y_after": e_m.y_after,
            "e_after": e_m.e_after,
            "ratio_engine": e_m.ratio,
            "ratio_refit": e_r.ratio,
            "refit_m_owner": fit.m_owner,
            "refit_m_other": fit.m_other,
            "observed_ratio": ((e_m.y_after + rc.PRIOR) / e_m.e_after)
            / ((e_m.y_before + rc.PRIOR) / e_m.e_before),
        }
        for tag, sg in (("", sigma), ("_nodrift", 0.0)):
            mu = rc.rate_draws(e_m, sg, N, SEED)
            for f, ratio in (("P", 1.0), ("M", e_m.ratio), ("Mr", e_r.ratio)):
                m = mu * ratio
                row[f"ls_{f}{tag}"] = rc.log_score(e_m.y_after, m)
                if not tag:
                    # count draws for the range: Poisson on the mean draws, own stream
                    cnt = np.random.default_rng([SEED, 1, len(rows)]).poisson(m)
                    p10, p50, p90 = np.percentile(cnt, [10, 50, 90])
                    row[f"{f}_p10"], row[f"{f}_p50"], row[f"{f}_p90"] = p10, p50, p90
                    row[f"{f}_inside"] = bool(p10 <= e_m.y_after <= p90)
                    row[f"{f}_within2"] = bool(p50 > 0 and 0.5 <= e_m.y_after / p50 <= 2.0)
        rows.append(row)
    pd.DataFrame(rows).to_csv(a.out / "events_scored.csv", index=False)

    # the b profiles (engine ratio and refitted ratio), with and without drift
    prof = {}
    for tag, sg in (("", sigma), ("_nodrift", 0.0)):
        for f, col in (("M", "ratio_engine"), ("Mr", "ratio_refit")):
            evs, mus = [], []
            for row in rows:
                e = rc.Event(
                    row["name"], row["y_before"], row["e_before"], row["y_after"], row["e_after"], row[col]
                )
                evs.append(e)
                mus.append(rc.rate_draws(e, sg, N, SEED))
            prof[f"{f}{tag}"] = rc.b_profile(evs, mus)
    pd.DataFrame({"b": rc.B_GRID} | prof).to_csv(a.out / "b_profile.csv", index=False)
    return {"m_owner": m_o, "m_other": m_x, "sigma": sigma, "draws": N, "seed": SEED}


def finish(out: Path, inputs: dict) -> None:
    sc_ = pd.read_csv(out / "events_scored.csv", dtype={"geoid": str})
    prof = pd.read_csv(out / "b_profile.csv")
    grid = prof["b"].to_numpy()
    res = {"inputs": inputs, "events": len(sc_), "states": int(sc_["state"].nunique())}
    for tag in ("", "_nodrift"):
        part = {}
        for f in ("M", "Mr"):
            g = gain(sc_, f"ls_P{tag}", f"ls_{f}{tag}")
            b, lo, hi = rc.b_interval(prof[f"{f}{tag}"].to_numpy(), grid)
            part[f] = {
                "gain_over_P": g,
                "b": b,
                "b_low": lo,
                "b_high": hi,
                "reading": rc.reading(g["gain"], g["se"], lo, hi),
            }
        res["drift" if not tag else "no_drift"] = part
    big = sc_[(sc_["ratio_engine"] > 1.5) | (sc_["ratio_engine"] < 1 / 1.5)]
    same = ((big["ratio_engine"] > 1) == (big["observed_ratio"] > 1)).sum()
    res["direction"] = {"events_with_big_ratio": len(big), "moved_same_way": int(same)}
    res["coverage"] = {
        f: {"inside_p10_p90": int(sc_[f"{f}_inside"].sum()), "within_x2": int(sc_[f"{f}_within2"].sum())}
        for f in ("P", "M", "Mr")
    }
    res["reading"] = res["drift"]["M"]["reading"]
    (out / "summary.json").write_text(json.dumps(res, indent=1, default=str))
    cols = [
        "name",
        "year",
        "dose_before",
        "dose_after",
        "y_before",
        "y_after",
        "ratio_engine",
        "ratio_refit",
        "observed_ratio",
        "M_p10",
        "M_p50",
        "M_p90",
        "ls_P",
        "ls_M",
        "ls_Mr",
    ]
    log("\n" + sc_[cols].round(2).to_string(index=False))
    log(json.dumps({k: res[k] for k in ("drift", "no_drift", "direction", "coverage", "reading")}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--finish", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.finish:
        inputs = json.loads((a.out / "inputs.json").read_text())
    else:
        store = DataStore()
        with offline.offline_build(store):
            inputs = run(a, store)
        (a.out / "inputs.json").write_text(json.dumps(inputs))
    finish(a.out, inputs)


if __name__ == "__main__":
    main()
