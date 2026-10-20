#!/usr/bin/env python3
"""Development run of the Handbook ADU scenario on real data (not a published result).

    uv run python scripts/dev/adu_dev_run.py [--origin 2025] [--state MN NC OH TX] [--out results.csv]

For each state: inputs from the processed, holdout-filtered tables (`scenarios.adu.places_from_store`), then
`scenarios.adu.run`. Prints five-year totals (P10/P50/P90 of each draw's sum) for named places and, per state,
how many places fall outside the calibration range and the sum of the places' mean additional homes, then
state totals (P10/P50/P90 of draws summed over places). Sensitivities (D-027), unless `--no-sensitivities`:
the state five-year totals with the mortgage rate at the low and high of its 2015-25 stress range, and with
half of the extrapolation noise shared instead of all of it. Places below the publishing minimum (D-015) and
places missing ACS rent or value are counted, not shown.
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
    ap.add_argument("--no-sensitivities", action="store_true")
    a = ap.parse_args()
    store = DataStore()
    minimum = load_params("aggregate")["min_eligible_parcels_publish"].value
    frames, summaries, yearlies, inputs = [], [], [], {}
    for state in a.state:
        places = adu.places_from_store(state, store, a.origin)
        missing = places[["rent", "home_value"]].isna().any(axis=1)
        inputs[state] = places[~missing].reset_index(drop=True)
        yearly, totals, summary = adu.run(inputs[state], a.origin, summary_by="state")
        summaries.append(summary)
        yearlies.append(yearly.assign(state=state))
        totals["state"] = state
        frames.append(totals)
        shown = totals[totals["eligible_parcels"] >= minimum]
        print(
            f"\n{state}: {len(places)} places, {int(missing.sum())} missing ACS rent/value, "
            f"{int((totals['eligible_parcels'] < minimum).sum())} below {minimum:g} eligible parcels; "
            f"outside calibration range {int(shown['outside_calibration'].sum())} of {len(shown)}; "
            f"rules: {shown['rule_class'].value_counts().to_dict()}"
        )
        sampled = shown["draws_from_unknown_rule"] > 0
        share = shown.loc[sampled, "eligible_parcels"].sum() / shown["eligible_parcels"].sum()
        print(
            f"  rule drawn (D-022) for {int(sampled.sum())} of {len(shown)} places "
            f"({share:.0%} of eligible "
            f"parcels); drawn classes over those places: none {shown.loc[sampled, 'drawn_none'].mean():.2f}, "
            f"partial {shown.loc[sampled, 'drawn_partial'].mean():.2f}, "
            f"handbook {shown.loc[sampled, 'drawn_handbook'].mean():.2f}"
        )
        print(
            f"  sum of place means, 5 years: Handbook ADU permits {shown['handbook_adus_mean'].sum():,.0f}, "
            f"added {shown['adu_permits_added_mean'].sum():,.0f}, additional homes "
            f"{shown['additional_homes_mean'].sum():,.0f} on {shown['eligible_parcels'].sum():,.0f} parcels"
        )
    allp = pd.concat(frames, ignore_index=True)
    summ = pd.concat(summaries, ignore_index=True)
    print("\nState totals: sum of draws over non-overlapping places (P10 / P50 / P90, mean)")
    for outcome in ("adu_permits_added", "additional_homes"):
        print(f"  {outcome}")
        for state, g in summ[summ["outcome"] == outcome].groupby("state"):
            cells = "; ".join(
                f"{r.period} {r.p10:,.0f}/{r.p50:,.0f}/{r.p90:,.0f} ({r['mean']:,.0f})"
                for _, r in g.iterrows()
            )
            print(f"    {state}: {cells}")
    if not a.no_sensitivities:
        print_sensitivities(inputs, a.origin, summ)
    named = allp[allp["geoid"].isin(NAMED)]
    print("\nNamed places, five-year totals (development run, origin", a.origin, ")")
    for _, r in named.iterrows():
        print(
            f"- {r['name']} ({r['state']}): {r['eligible_parcels']:,.0f} parcels; rent ${r['rent']:,.0f}; "
            f"PCR {r['price_to_cost_central']:.2f}; "
            f"mature hazard {r['mature_hazard_central'] * 1000:.2f}/1,000; "
            f"outside range by {r['calibration_distance']:.2f}; rule {r['rule_class']} ({r['rule_note']}); "
            f"P(none/partial/handbook) {r['p_none']:.2f}/{r['p_partial']:.2f}/{r['p_handbook']:.2f}; "
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
        summ.to_csv(a.out.with_name(a.out.stem + "_state.csv"), index=False)
        pd.concat(yearlies, ignore_index=True).to_csv(
            a.out.with_name(a.out.stem + "_yearly.csv"), index=False
        )


def print_sensitivities(inputs: dict, origin: int, central: pd.DataFrame) -> None:
    """Five-year state totals (P10/P50/P90) under each sensitivity, next to the forecast run (D-027)."""
    specs = adu.specs()
    rate, shared = specs["mortgage_rate_forecast"], specs["adu_extrapolation_shared_share"]
    cases = {
        "forecast (central)": None,
        f"mortgage rate {rate.low:g}% (2015-25 low)": {"mortgage_rate_forecast": rate.low},
        f"mortgage rate {rate.high:g}% (2015-25 high)": {"mortgage_rate_forecast": rate.high},
        f"extrapolation noise {shared.low:g} shared": {"adu_extrapolation_shared_share": shared.low},
    }
    period = f"{origin + 1}-{origin + 5}"
    print(f"\nSensitivities, state five-year totals {period} (P10 / P50 / P90, mean)")
    for outcome in ("adu_permits_added", "additional_homes"):
        print(f"  {outcome}")
        for label, fixed in cases.items():
            cells = []
            for state, places in inputs.items():
                if fixed is None:
                    summ = central[central["state"] == state]
                else:
                    summ = adu.run(places, origin, summary_by="state", params=fixed)[2]
                r = summ[(summ["outcome"] == outcome) & (summ["period"] == period)].iloc[0]
                cells.append(f"{state} {r.p10:,.0f}/{r.p50:,.0f}/{r.p90:,.0f} ({r['mean']:,.0f})")
            print(f"    {label:34s} " + "; ".join(cells))


if __name__ == "__main__":
    main()
