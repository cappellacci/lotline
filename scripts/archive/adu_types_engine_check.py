#!/usr/bin/env python3
"""Statewide ADU scenario totals from the engine as it stands (development check, not a published result).

    uv run python scripts/archive/adu_types_engine_check.py --out <csv> [--draws 1000]

For MN, NC, OH, TX and OR: `scenarios.adu.places_from_store` (origin 2025, holdout-filtered tables, offline),
then `scenarios.adu.run` with state sums. St. Paul (V5, blind) is left out. Run once before and once after the
engine reads Form A + place types (D-088/D-089) to compare the two. Writes the state table (P10/P50/P90 and
mean of current-rules ADUs, ADU permits added and additional homes, 2027-2031) and, where places carry a type,
the mean five-year totals by state and type.
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
    ap.add_argument("--mx", type=float, help="hold m_x (adu_partial_rule_share) at this value")
    a = ap.parse_args()
    store = DataStore()
    rows, by_type = [], []
    with offline.offline_build(store):
        for st in STATES:
            places = adu.places_from_store(st, store, 2025)
            places = places[places["geoid"].astype(str) != ST_PAUL].reset_index(drop=True)
            places["state"] = st
            held = {} if a.mx is None else {"adu_partial_rule_share": a.mx}
            _, totals, summ = adu.run(places, 2025, draws=a.draws, summary_by="state", params=held)
            rows.append(summ[summ["period"].str.contains("-")])
            if "place_type" in totals:
                g = totals.groupby("place_type")[
                    ["eligible_parcels", "current_rules_adus_mean", "adu_permits_added_mean"]
                ].sum()
                by_type.append(g.assign(state=st).reset_index())
            print(st, len(places), "places", flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(a.out, index=False)
    print(out.round(0).to_string(index=False))
    if by_type:
        t = pd.concat(by_type, ignore_index=True)
        t.to_csv(a.out.with_name(a.out.stem + "_by_type.csv"), index=False)
        print(t.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
