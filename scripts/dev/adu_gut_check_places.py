#!/usr/bin/env python3
"""Per-place ADU engine results for the gut-check page: where each state's predicted ADUs come from.

    PYTHONPATH=src python scripts/dev/adu_gut_check_places.py --out reports/adu-gut-check [--draws 1000]

`scenarios.adu.run` per state (origin 2025, own counts with drift on, m_x drawn from the D-097 grid; St. Paul
left out; offline). Writes `places.csv`: each place's eligible lots, type, rule class, its recent observed ADU
rate as a count a year, and the mean and P10/P50/P90 of its five-year current-rules ADUs and ADUs added.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, offline
from lotline.model.scenarios import adu

STATES = ("MN", "NC", "OH", "TX", "OR")
ST_PAUL = "2758000"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--draws", type=int, default=1000)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    out = []
    with offline.offline_build(store):
        for st in STATES:
            places = adu.places_from_store(st, store, 2025)
            places = places[places["geoid"].astype(str) != ST_PAUL].reset_index(drop=True)
            places["state"] = st
            _, totals = adu.run(
                places, 2025, draws=a.draws, params={"adu_own_rate_drift": 1, adu.SHARE_DRAWS: 1}
            )
            keep = [
                c
                for c in totals.columns
                if c.startswith(("current_rules_adus", "adu_permits_added", "handbook_adus"))
            ]
            t = totals[["geoid", *keep]].copy()
            t["state"] = st
            for c in ("name", "eligible_parcels", "place_type", "rule_class", "observed_rate"):
                if c in places:
                    t[c] = places[c].to_numpy()
            t["observed_per_year"] = t["observed_rate"] * t["eligible_parcels"]
            out.append(t)
            print(st, flush=True)
    pd.concat(out, ignore_index=True).to_csv(a.out / "places.csv", index=False)


if __name__ == "__main__":
    main()
