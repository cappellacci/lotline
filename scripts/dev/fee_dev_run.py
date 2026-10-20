#!/usr/bin/env python3
# ruff: noqa: E501  (long report lines)
"""Development run of the fee scenario on real data for the places with coded fees (not a published result).

    uv run python scripts/dev/fee_dev_run.py [--origin 2025] [--state MN NC TX] [--out results.csv]

For each state: places with rows in config/fees (St. Paul is left out: its outcomes from 2024 on are a holdout);
baseline units per year = the baseline model's mean (`baseline.baseline_forecast`) summed over the four BPS
size classes, from the holdout-filtered panel; median home value from the newest ACS 5-year vintage <= origin
(2025 dollars); parcel inputs (`scenarios.fees.parcel_inputs`) where the state has a parcel table. Runs the
scenario in `local` and `handbook` modes and prints five-year totals (P10/P50/P90 and mean of added units).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lotline.build import eligible, panels
from lotline.config import load_fees, load_params
from lotline.io import DataStore
from lotline.model import baseline, money
from lotline.model.scenarios import adu, fees

HOLDOUT_PLACES = {"2758000", "3712000"}  # St. Paul, Charlotte: never in a development run


def baseline_units(state: str, store, origin: int, geoids) -> pd.DataFrame:
    """Mean baseline units a year (all BPS size classes) for years 1..5 after the origin, per place."""
    p = load_params("baseline")
    panel = panels.load(state, store, theme="adu", rule_version=eligible.RULE_VERSION)
    panel = panel[panel["geoid"].isin(geoids)]
    reported = bool(p["use_reported_only"].value)
    parts = []
    for size in baseline.SIZE_CLASSES:
        t = baseline.baseline_forecast(panel, baseline.outcome_column(size, reported), origin, params=p)
        parts.append(t[["geoid", "horizon", "mean"]])
    t = pd.concat(parts).groupby(["geoid", "horizon"])["mean"].sum().unstack("horizon")
    t = t.reindex(columns=range(1, int(p["forecast_horizon_years"].value) + 1))
    t.columns = [f"baseline_y{h}" for h in t.columns]
    return t.rename_axis(columns=None).reset_index()


def places_for(state: str, store, origin: int) -> pd.DataFrame | None:
    coded = load_fees(state)
    if coded is None:
        return None
    local = fees.local_fees(coded)
    local = local[~local["geoid"].isin(HOLDOUT_PLACES)]
    juris = store.read(state, "jurisdictions")[["geoid", "name", "kind", "state"]]
    places = local.merge(juris, on="geoid", how="left")
    places = places.merge(baseline_units(state, store, origin, places["geoid"]), on="geoid", how="left")
    cpi = money.index_by_year(store.read(state, "market_geo_year"), "cpi_u")
    places["acs_geo"] = places["kind"].map(adu.ACS_PREFIX) + ":" + places["geoid"]
    acs = adu.acs_values(store.read(state, "acs_geo_year"), places["acs_geo"], origin, cpi)
    places = places.merge(acs[["home_value"]], left_on="acs_geo", right_index=True, how="left")
    parcels = store.read(state, "parcels")
    if parcels is not None:
        parcels = parcels[parcels["jurisdiction_geoid"].isin(places["geoid"])]
        places = places.merge(
            fees.parcel_inputs(parcels, origin, fees.central_params()), on="geoid", how="left"
        )
    return places


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", type=int, default=2025)
    ap.add_argument("--state", nargs="+", default=["MN", "NC", "TX"])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    store = DataStore()
    frames = []
    for state in a.state:
        places = places_for(state, store, a.origin)
        if places is None or places.empty:
            continue
        ok = places["home_value"].notna() & places.filter(like="baseline_y").notna().all(axis=1)
        if (~ok).any():
            print(
                f"{state}: skipped (no baseline or ACS value): {', '.join(places.loc[~ok, 'name'].astype(str))}"
            )
        places = places[ok].reset_index(drop=True)
        if places.empty:
            continue
        for mode in fees.MODES:
            _, totals, summary = fees.run(places, a.origin, mode=mode, summary_by="state")
            frames.append(totals.assign(state=state))
            five = summary.iloc[-1]
            print(
                f"\n{state}, mode {mode}: {len(places)} places; sum of draws, five years: units added "
                f"P10 {five.p10:,.0f} / P50 {five.p50:,.0f} / P90 {five.p90:,.0f} (mean {five['mean']:,.0f})"
            )
            for _, r in totals.iterrows():
                print(
                    f"- {r['name']}: fee ${r['fee_per_unit']:,.0f} ({r['fee_source']}; {r['fee_components']}), "
                    f"cut ${r['fee_cut_per_unit']:,.0f}, to builders ${r['builder_saving_central']:,.0f}; "
                    f"home value ${r['home_value']:,.0f}; new-home value "
                    f"${r.get('new_home_value', float('nan')):,.0f}; channel {r['channel_central']} "
                    f"({r['feasibility_share_of_draws']:.0%} of draws feasibility); central "
                    f"{r['pct_change_central']:+.1%}; baseline {r['baseline_five_year']:,.0f} units in 5 yrs; "
                    f"added P10 {r['units_added_p10']:,.0f} / P50 {r['units_added_p50']:,.0f} / "
                    f"P90 {r['units_added_p90']:,.0f}"
                )
    if a.out and frames:
        pd.concat(frames, ignore_index=True).to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
