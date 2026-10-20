#!/usr/bin/env python3
"""Development run of the Handbook ADU scenario on real data (not a published result).

    uv run python scripts/dev/adu_dev_run.py [--origin 2025] [--state MN NC OH TX] [--out results.csv]

For each state: inputs from the processed, holdout-filtered tables (`scenarios.adu.places_from_store`), then
`scenarios.adu.run`. Prints five-year totals (P10/P50/P90 of each draw's sum) for named places and, per state,
how many places fall outside the calibration range and the sum of the places' mean additional homes (a sum of
means: the statewide range needs the aggregation step, a later round). Places below the publishing minimum
(D-015) and places missing ACS rent or value are counted, not shown.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore
from lotline.model.scenarios import adu

NAMED = {"2743000", "2758000", "2706616", "3918000", "3915000", "3755000", "3712000", "4805000", "4865000"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", type=int, default=2025)
    ap.add_argument("--state", nargs="+", default=["MN", "NC", "OH", "TX"])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    store = DataStore()
    minimum = load_params("aggregate")["min_eligible_parcels_publish"].value
    frames = []
    for state in a.state:
        places = adu.places_from_store(state, store, a.origin)
        missing = places[["rent", "home_value"]].isna().any(axis=1)
        _, totals = adu.run(places[~missing].reset_index(drop=True), a.origin)
        totals["state"] = state
        frames.append(totals)
        shown = totals[totals["eligible_parcels"] >= minimum]
        print(
            f"\n{state}: {len(places)} places, {int(missing.sum())} missing ACS rent/value, "
            f"{int((totals['eligible_parcels'] < minimum).sum())} below {minimum:g} eligible parcels; "
            f"outside calibration range {int(shown['outside_calibration'].sum())} of {len(shown)}; "
            f"rules: {shown['rule_class'].value_counts().to_dict()}"
        )
        print(
            f"  sum of place means, 5 years: Handbook ADU permits {shown['handbook_adus_mean'].sum():,.0f}, "
            f"added {shown['adu_permits_added_mean'].sum():,.0f}, additional homes "
            f"{shown['additional_homes_mean'].sum():,.0f} on {shown['eligible_parcels'].sum():,.0f} parcels"
        )
    allp = pd.concat(frames, ignore_index=True)
    named = allp[allp["geoid"].isin(NAMED)]
    print("\nNamed places, five-year totals (development run, origin", a.origin, ")")
    for _, r in named.iterrows():
        print(
            f"- {r['name']} ({r['state']}): {r['eligible_parcels']:,.0f} parcels; rent ${r['rent']:,.0f}; "
            f"PCR {r['price_to_cost_central']:.2f}; "
            f"mature hazard {r['mature_hazard_central'] * 1000:.2f}/1,000; "
            f"outside range by {r['calibration_distance']:.2f}; rule {r['rule_class']} ({r['rule_note']}); "
            f"observed {r['observed_adu_per_year']:.1f}/yr"
        )
        for key, label in (
            ("handbook_adus", "Handbook ADU permits"),
            ("current_rules_adus", "current rules"),
            ("adu_permits_added", "permits added"),
            ("additional_homes", "additional homes"),
        ):
            print(
                f"    {label:22s} P10 {r[key + '_p10']:>8,.0f}  P50 {r[key + '_p50']:>8,.0f}  "
                f"P90 {r[key + '_p90']:>8,.0f}  mean {r[key + '_mean']:>8,.0f}"
            )
    if a.out:
        allp.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
