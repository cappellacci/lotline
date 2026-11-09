#!/usr/bin/env python3
"""D-064's one-line sensitivity: current rules as of 2027-12-31 (adopted) vs 2026-12-31 (low value, 0).

Same seeds and draws in both arms, so the difference is the rules date alone. Prints, per state, the ADU
permits added and missing-middle net homes (homes permitted minus teardowns), P10 / P50 / P90 over 5 years.
A third arm, 2025-12-31, is the rule before D-064; its missing-middle numbers reproduce D-063's run.

    uv run python scripts/dev/d064_sensitivity.py [--out reports/results-run-2026-11-09/d064_sensitivity.csv]
"""

import argparse

import numpy as np
import pandas as pd

from lotline.io import DataStore
from lotline.model import baseline
from lotline.model.scenarios import adu, mm

ARMS = {
    "2027-12-31 (adopted)": "2027-12-31",
    "2026-12-31 (low)": "2026-12-31",
    "2025-12-31 (before D-064)": "2025-12-31",
}
STATES = ["MN", "NC", "OH", "OR", "TX"]
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="reports/results-run-2026-11-09/d064_sensitivity.csv")
args = ap.parse_args()
store = DataStore()
original = baseline.rules_as_of


def pct(x):
    return np.percentile(x, [10, 50, 90])


out = []
for st in STATES:
    for label, date in ARMS.items():
        baseline.rules_as_of = lambda origin, params=None, _d=date: pd.Timestamp(_d)
        try:
            places = adu.places_from_store(st, store, 2025)
            places = places[places["rent"].notna() & places["home_value"].notna()].reset_index(drop=True)
            places["state"] = st
            _, _, rd = adu.run(places, 2025, draws=1000, return_draws=True)
            a = np.asarray(rd["added"], dtype=float).sum(axis=(1, 2))
            _, res, _ = mm.run(st, store, 2025, n=4000)
            m = res.homes_gross.sum(axis=1) - res.teardowns.sum(axis=1)
        finally:
            baseline.rules_as_of = original
        out.append((st, label, *pct(a), *pct(m)))
        print(st, label, "ADU", np.round(pct(a)), "MM", np.round(pct(m)), flush=True)

cols = ["state", "rules_as_of", "adu_p10", "adu_p50", "adu_p90", "mm_p10", "mm_p50", "mm_p90"]
df = pd.DataFrame(out, columns=cols)
df.to_csv(args.out, index=False)
print(df.round(0).to_string(index=False))
