#!/usr/bin/env python3
"""D-099: profile of the first-years share ν, and its held-out check, on the D-096 rows.

    uv run python scripts/dev/adu_new_rule.py --out reports/adu-new-rule --workers 7
    uv run lotline calibrate --run --step adu_new_rule   # the main variant, from the registry

Run only after D-099 is accepted. Steps (D-099):
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
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.calibrate import adu_steps as steps
from lotline.io import DataStore, offline
from lotline.model import adu_fit_set as fs
from lotline.model import adu_new_rule as nr
from lotline.model import adu_screen as scr
from lotline.model import adu_types as ty
from lotline.model import joint_refit as jr
from lotline.model import score as sc
from lotline.model.scenarios import adu

RALEIGH = "3755000"


def _cv():
    return steps._cv()


def profile(pz, first, k=nr.K) -> pd.DataFrame:
    return steps.nu_profile(pz, first, nr.NU_GRID, k)


interval = steps.nu_interval


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
        pz = fs.d096_places(store)
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
