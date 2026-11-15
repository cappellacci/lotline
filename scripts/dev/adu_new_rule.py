#!/usr/bin/env python3
"""D-098: profile of the first-years share ν, and its held-out check, on the D-096 rows.

    PYTHONPATH=<checkout with the D-096 rows>/src python scripts/dev/adu_refit_fixed_rows.py \
        adu_new_rule.py --out reports/adu-new-rule --workers 7

Run only after D-098 is accepted. Steps (D-098):
1. All-data profile over `adu_new_rule.NU_GRID`: each place's base scaled by ν in its first K years after f_i,
   A + P's θ, α and core term refit at D-096's m_o and m_x (`adu_types._maximize`); ν̂ and its 90% interval.
2. Held-out: for each newly allowing fit place j, the profile without j, then j's new-rule years scored from
   its rules and type alone (negative binomial at the refit α) under ν̂(−j) and under ν = 1.
3. Sensitivities: K = 3; only places with an explicit no-ADU row before f_i; Raleigh left out.
Tests A-B and D with ν (decision rule part 3) run afterwards through D-088's script with the inputs scaled.
Offline; St. Paul out; nothing goes to config.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore, offline
from lotline.model import adu_new_rule as nr
from lotline.model import adu_screen as scr
from lotline.model import adu_types as ty
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr
from lotline.model import score as sc
from lotline.model.scenarios import adu

HERE = Path(__file__).resolve().parent
RALEIGH = "3755000"


def _load(name: str, file: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


GRID = _load("adu_mx_grid", "adu_mx_grid.py")  # its `places` builds the D-096 inputs with types


def _cv():
    p = load_params("adu")
    return cal._cvals(p["adu_owner_occupancy_share"].value, p["adu_partial_rule_share"].value)


def _zm(pz):
    d = np.array([ty.type_d(p) for p in pz])
    return d[:, [j for j in range(d.shape[1]) if d[:, j].any()]]


def profile(pz, first, k=nr.K) -> pd.DataFrame:
    cv, zm = _cv(), _zm(pz)
    rows = []
    for nu in nr.NU_GRID:
        f = ty._maximize(scr.prepare(nr.scaled_all(pz, nu, first, k), cv), zm)
        rows.append({"nu": nu, "theta": math.exp(f.lt), "alpha": math.exp(f.la), "core": float(f.b[0]),
                     "loglik": f.loglik})  # fmt: skip
    return pd.DataFrame(rows)


def interval(prof: pd.DataFrame) -> dict:
    top = prof["loglik"].max()
    inside = prof[2 * (top - prof["loglik"]) <= cal.CHI2_90]["nu"]
    return {
        "nu": float(prof.loc[prof["loglik"].idxmax(), "nu"]),
        "low": float(inside.min()),
        "high": float(inside.max()),
    }


def held_out_one(args) -> dict:
    j, pz, first, k = args
    rest = [p for p in pz if p.geoid != j.geoid]
    prof = profile(rest, first, k)
    nu_hat = interval(prof)["nu"]
    flags = nr.new_rule_flags(j.years, first[j.geoid], k)
    sub = jr.subset_years(j, [y for y, fl in zip(j.years, flags, strict=True) if fl])
    out = {"geoid": j.geoid, "name": j.name, "state": j.state, "nu_minus_j": nu_hat}
    out |= {"years": int(flags.sum()), "observed": float(sub.y.sum())}
    core = float(ty.type_d(j)[0])
    for tag, nu in (("hat", nu_hat), ("one", 1.0)):
        r = prof[prof["nu"] == nu].iloc[0]
        rate = r["theta"] * math.exp(r["core"] * core)
        p = scr.prepare([nr.scaled(sub, nu, np.ones(len(sub.y), dtype=bool))], _cv())
        out[f"ls_{tag}"] = float(scr.place_loglik(p, np.array([rate]), r["alpha"])[0])
    return out


def run_all(pz, first, k, workers, label) -> dict:
    prof = profile(pz, first, k)
    iv = interval(prof)
    targets = [p for p in pz if p.geoid in first and nr.new_rule_flags(p.years, first[p.geoid], k).any()]
    with ProcessPoolExecutor(workers) as pool:
        ho = pd.DataFrame(list(pool.map(held_out_one, [(j, pz, first, k) for j in targets])))
    g, se = sc.paired(ho["ls_hat"] - ho["ls_one"]) if len(ho) > 1 else (float("nan"), float("nan"))
    return {
        "label": label,
        "profile": prof,
        "interval": iv,
        "held_out": ho,
        "gain": g,
        "se": se,
        "places": len(ho),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        pz = GRID.places(store)
    rows = pd.concat([adu.load_reforms(st) for st in ("MN", "NC", "OH", "TX", "OR")], ignore_index=True)
    first = nr.first_allowing_year(rows)
    first = {g: f for g, f in first.items() if g in {p.geoid for p in pz}}
    no_before = {
        g
        for g in first
        if (
            (rows["jurisdiction_geoid"] == g) & (pd.to_numeric(rows["adus_per_lot"], errors="coerce") == 0)
        ).any()
    }
    variants = {
        "main": (first, nr.K, pz),
        "K = 3": (first, 3, pz),
        "explicit no-ADU before": ({g: f for g, f in first.items() if g in no_before}, nr.K, pz),
        "without Raleigh": (
            {g: f for g, f in first.items() if g != RALEIGH},
            nr.K,
            [p for p in pz if p.geoid != RALEIGH],
        ),
    }
    summary = {"first_allowing": first, "variants": {}}
    for label, (fst, k, pls) in variants.items():
        res = run_all(pls, fst, k, a.workers, label)
        tag = label.replace(" ", "_").replace("=", "").replace("-", "")
        res["profile"].to_csv(a.out / f"profile_{tag}.csv", index=False)
        res["held_out"].to_csv(a.out / f"held_out_{tag}.csv", index=False)
        summary["variants"][label] = {
            "interval": res["interval"],
            "gain": res["gain"],
            "se": res["se"],
            "places": res["places"],
        }
        print(label, summary["variants"][label], flush=True)
    m = summary["variants"]["main"]
    summary["parts_1_2"] = bool(
        not (m["interval"]["low"] <= 1.0 <= m["interval"]["high"]) and m["gain"] > 2 * m["se"]
    )
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
