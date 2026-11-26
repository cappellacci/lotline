#!/usr/bin/env python3
"""Fast-ramp sensitivity for the Handbook missing-middle scenario (D-100, pre-registered 2026-11-17).

    uv run python scripts/archive/mm_fast_ramp_run.py --out reports/mm-d100/fast-ramp

Runs each state three times with C4's values, draws and seed, changing only the ramp's half-way point: 4.0
(C4, the main result), 1.0 (C4's low end) and 0.5 (`mm_ramp_half_years_fast`, D-100's locally adopted ramp).
Origin 2025. Reads rolls, rules, ACS and market series only; no permits, no holdouts. Writes summary.csv,
compare.json and params.json.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.model.scenarios import mm

STATES = ("MN", "NC", "OH", "TX", "OR")
ORIGIN = 2025


def main(out: Path) -> None:
    t0 = time.time()
    store = DataStore()
    sp = mm.specs()
    halves = {"main": mm.ramp_half(sp), "fast_high": mm.ramp_half(sp, "fast", "high"),
              "fast": mm.ramp_half(sp, "fast")}  # fmt: skip
    n, seed = int(sp["mm_scenario_draws"].value), int(sp["mm_scenario_seed"].value)
    draws = mm.draw_params(n, seed, sp)
    out.mkdir(parents=True, exist_ok=True)
    summ, compare = [], {}
    for st in STATES:
        places = mm.places_from_store(st, store, ORIGIN)
        compare[st] = {}
        for label, half in halves.items():
            res = mm.simulate(
                places, draws, half, sp["mm_ramp_slope_years"].value, seed,
                int(sp["mm_rule_min_coded"].value), phi=sp["mm_year_spread_phi"].value,
            )  # fmt: skip
            s = mm.summarize(res).assign(state=st, variant=label, half=half)
            summ.append(s)
            five = s[s["period"] == "five_years"].set_index("measure")
            hg = res.homes_gross
            compare[st][label] = {
                "half": half,
                **{m: [round(float(five.loc[m, k])) for k in ("p10", "p50", "p90", "mean")]
                   for m in ("buildings", "homes_net")},
                "year5_share": round(float(hg[:, -1].sum() / hg.sum()), 3),
            }  # fmt: skip
        m0 = compare[st]["main"]["homes_net"][3]
        for label in ("fast_high", "fast"):
            compare[st][label]["mean_ratio_to_main"] = round(compare[st][label]["homes_net"][3] / m0, 3)
        med = " | ".join(f"{k} {v['homes_net'][1]:,}" for k, v in compare[st].items())
        print(f"[{time.time() - t0:5.0f}s] {st}: {len(places)} places {med}", flush=True)
    pd.concat(summ).round(2).to_csv(out / "summary.csv", index=False)
    (out / "compare.json").write_text(json.dumps(compare, indent=1))
    params = {"draws": n, "seed": seed, "origin": ORIGIN, "halves": halves,
              "slope": sp["mm_ramp_slope_years"].value, "theta": sp["mm_mature_hazard_ref"].value,
              "phi": sp["mm_year_spread_phi"].value, "seconds": round(time.time() - t0)}  # fmt: skip
    (out / "params.json").write_text(json.dumps(params, indent=2))
    print(json.dumps(compare, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=Path("reports/mm-d100/fast-ramp"))
    main(ap.parse_args().out)
