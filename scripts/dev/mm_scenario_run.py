#!/usr/bin/env python3
"""First run of the Handbook missing-middle scenario (D-063), five states, approved by Ben 2026-11-08..

    uv run python scripts/dev/mm_scenario_run.py --out reports/mm-scenario-2026-11-08

Origin 2025; config values as on the branch (D-055 hazard, D-063 scenario keys). Also a sensitivity with homes
per building held at the pooled 2.08 (D-063 finding on the triangular draw). Reads rolls, rules, ACS and
market series only; no permits.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.io import DataStore
from lotline.model.scenarios import mm

STATES = ("MN", "NC", "OH", "TX", "OR")
ORIGIN = 2025


def main(out: Path) -> None:
    t0 = time.time()
    store = DataStore()
    sp = mm.specs()
    n, seed = int(sp["mm_scenario_draws"].value), int(sp["mm_scenario_seed"].value)
    half, slope = sp["mm_ramp_half_years"].value, sp["mm_ramp_slope_years"].value
    draws = mm.draw_params(n, seed, sp)
    held = draws.assign(units=sp["mm_units_per_project"].value)
    out.mkdir(parents=True, exist_ok=True)
    summ, place_rows, inputs = [], [], []
    for st in STATES:
        places = mm.places_from_store(st, store, ORIGIN)
        for label, d in (("main", draws), ("units_held_2.08", held)):
            res = mm.simulate(places, d, half, slope, seed, int(sp["mm_rule_min_coded"].value))
            s = mm.summarize(res).assign(state=st, variant=label)
            summ.append(s)
            if label == "main":
                np.savez_compressed(out / f"draws_{st.lower()}.npz", buildings=res.buildings,
                                    homes_gross=res.homes_gross, teardowns=res.teardowns)  # fmt: skip
                pr = res.places
                place_rows.append(
                    pr[["geoid", "name", "kind", "eligible", "dose", "band", "house_share",
                        "house_share_source", "pcr", "f_ratio", "dose_gap_mean", "added_buildings_mean",
                        "added_homes_net_mean"]]
                    .assign(state=st)
                )  # fmt: skip
        inputs.append({
            "state": st, "places": len(places), "eligible": float(places["eligible"].sum()),
            "coded": int(places["dose"].notna().sum()), "coded_dose_gt0": int((places["dose"] > 0).sum()),
            "eligible_weighted_gap_if_coded": float(
                ((1 - places["dose"].fillna(0)) * places["eligible"]).sum() / places["eligible"].sum()),
            "house_share_weighted": float((places["house_share"] * places["eligible"]).sum()
                                          / places["eligible"].sum()),
            "f_ratio_weighted": float((places["f_ratio"] * places["eligible"]).sum()
                                      / places["eligible"].sum()),
            "denominator_sources": places["denominator_source"].value_counts().to_dict(),
        })  # fmt: skip
        print(f"[{time.time() - t0:5.0f}s] {st}: {len(places)} places", flush=True)
    s = pd.concat(summ)
    s.round(2).to_csv(out / "summary.csv", index=False)
    pd.concat(place_rows).round(5).to_csv(out / "places.csv", index=False)
    (out / "inputs.json").write_text(json.dumps(inputs, indent=2))
    params = {"draws": n, "seed": seed, "half": half, "slope": slope, "origin": ORIGIN,
              "theta": sp["mm_mature_hazard_ref"].value,
              "alpha": sp["mm_place_effect_variance"].value}  # fmt: skip
    (out / "params.json").write_text(json.dumps(params, indent=2))
    five = s[s["period"] == "five_years"]
    print(five.pivot_table(index=["state", "variant"], columns="measure", values="p50").round(0).to_string())
    print(five[five["measure"] == "homes_net"][["state", "variant", "p10", "p50", "p90", "mean"]].round(0)
          .to_string(index=False))  # fmt: skip
    print(json.dumps(inputs, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("reports/mm-scenario-2026-11-08"))
    main(ap.parse_args().out)
