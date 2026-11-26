#!/usr/bin/env python3
"""Write D-100 run 1's summary.json from the files the run saved (the run stopped at the summary step on a
JSON key bug, fixed since in `mm_ramp_d100.py`; its fits and scores were already written).

    uv run python scripts/archive/mm_ramp_d100_summary.py reports/mm-d100/run1

Reads fits.csv, place_scores.csv, routes.csv and the R2 half-way points from run-log.txt. Fits nothing.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

from lotline.model import calibrate_mm as cal


def main(run: Path) -> None:
    fits = pd.read_csv(run / "fits.csv").set_index("fit")
    scores = pd.read_csv(run / "place_scores.csv")
    routes = pd.read_csv(run / "routes.csv", dtype={"geoid": str})
    log = (run / "run-log.txt").read_text()
    m = re.search(r"R2 [\d.]+/1,000 half state ([\d.]+), local ([\d.]+) \(([\d.]+)-([\d.]+)\)", log)
    hs, hl, lo, hi = (float(x) for x in m.groups())
    folds = {
        s: [float(a), float(b)] for s, a, b in re.findall(r"fold (\w\w): .*R2 halves ([\d.]+)/([\d.]+)", log)
    }
    fs = scores[~scores["test_place"]]
    full = {k: fits.loc[f"{k}_full"].to_dict() for k in ("R0", "R1", "R2")}
    r5 = {k: f["per_1000"] * cal.ramp_mean(f["half"]) for k, f in full.items()}
    r5["R2_local"] = full["R2"]["per_1000"] * cal.ramp_mean(hl)
    pairs = {"R1_vs_R0": ("ls_R1", "ls_R0"), "R2_vs_R1": ("ls_R2", "ls_R1"), "R2_vs_R0": ("ls_R2", "ls_R0"),
             "R0_vs_none": ("ls_R0", "ls_none"), "R1_vs_none": ("ls_R1", "ls_none"),
             "R2_vs_none": ("ls_R2", "ls_none")}  # fmt: skip
    paired = {k: cal.paired_delta(fs, a, b) for k, (a, b) in pairs.items()}
    margin = 2.0  # D-092 §5 (mm_challenger_se_margin)
    beats = {
        k: paired[k]["delta"] > margin * paired[k]["paired_se"] for k in ("R1_vs_R0", "R2_vs_R1", "R2_vs_R0")
    }
    chosen = "R2" if beats["R2_vs_R0"] and beats["R2_vs_R1"] else ("R1" if beats["R1_vs_R0"] else "R0")
    summary = {
        "status": "D-100 run 1 (Ben's go-ahead 2026-11-16); summary rebuilt from the saved files",
        "full": full,
        "R2_halves": {"state": hs, "local": hl, "local_low": lo, "local_high": hi},
        "R2_fold_halves": folds,
        "R2_theta_interval_note": "R2's θ interval is conditional on its best pair of half-way points "
        "(fit with the pair held), so it is narrower than R0's and R1's, which profile over the ramp",
        "r5_per_1000": r5,
        "route_counts": {
            f"{r}/{t}": int(n) for (r, t), n in routes.groupby(["role", "route"]).size().items()
        },
        "paired": paired,
        "beats_by_2se": beats,
        "chosen_by_scores": chosen,
        "section7_rerun": "not triggered: no candidate beats the one before it by 2 paired SE",
    }
    (run / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
