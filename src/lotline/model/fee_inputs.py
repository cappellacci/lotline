"""Inputs for the fee scenario from the data store: every place the baseline forecasts, with its baseline by
BPS size class, local fees per building type (D-065 fill, 2025 dollars), ACS home value and parcel inputs.

Moved from `scripts/dev/fee_dev_run.py` (D-076) so the results bundle can run the fee scenarios statewide.
"""

from __future__ import annotations

import pandas as pd

from lotline.build import eligible, panels
from lotline.config import CONFIG_DIR, load_fees, load_params
from lotline.model import baseline, fee_levels, money
from lotline.model.scenarios import adu, fees


def baseline_units(state: str, store, origin: int, geoids) -> pd.DataFrame:
    """Mean baseline units a year for each year of the forecast window (D-061), per place: each BPS size
    class (`baseline_y<h>_<class>`) and their sum (`baseline_y<h>`)."""
    p = load_params("baseline")
    panel = panels.load(state, store, theme="adu", rule_version=eligible.RULE_VERSION)
    if geoids is not None:
        panel = panel[panel["geoid"].isin(geoids)]
    reported = bool(p["use_reported_only"].value)
    horizons = range(1, int(p["forecast_horizon_years"].value) + 1)
    parts = []
    for size in baseline.SIZE_CLASSES:
        t = baseline.baseline_forecast(panel, baseline.outcome_column(size, reported), origin, params=p)
        parts.append(t[["geoid", "horizon", "mean"]].assign(size=size))
    long = pd.concat(parts)
    total = long.groupby(["geoid", "horizon"])["mean"].sum().unstack("horizon").reindex(columns=horizons)
    total.columns = [f"baseline_y{h}" for h in total.columns]
    by = long.set_index(["geoid", "size", "horizon"])["mean"].unstack(["horizon", "size"])
    by.columns = [f"baseline_y{h}_{s}" for h, s in by.columns]
    return total.join(by).rename_axis(columns=None).reset_index()


def type_fees(geoids: pd.DataFrame, coded: pd.DataFrame, cpi) -> pd.DataFrame:
    """Fee per unit for houses (unsuffixed columns) and duplexes and fourplexes (`_U2`, `_U3_4`), D-073."""
    keep = ["local_fee_per_unit", "local_fee_low", "local_fee_high", "fee_source"]
    out = fee_levels.place_fees(geoids, coded, "SFD", index=cpi)
    for t in ("U2", "U3_4"):
        f = fee_levels.place_fees(geoids, coded, t, index=cpi)[["geoid", *keep]]
        out = out.merge(f.rename(columns={k: f"{k}_{t}" for k in keep}), on="geoid", how="left")
    return out


def all_coded_fees() -> pd.DataFrame:
    """Every state's coded fees, so the D-065 fill can fall back to pooled medians."""
    states = sorted(p.stem for p in (CONFIG_DIR / "fees").glob("*.csv"))
    return pd.concat([load_fees(s) for s in states], ignore_index=True)


def statewide_places(state: str, store, origin: int) -> pd.DataFrame:
    """Every place the baseline forecasts in the state (the BPS units `results.baseline_table` sums), with
    fees per type (coded, or the D-065 fill: the state's or the pooled median), ACS home value (places without
    one take the state's median, flagged `home_value_filled`) and parcel inputs where the state has a roll.
    Holdout places are included as inputs: the panel's outcomes are holdout-filtered, and no outcome after the
    origin is read (D-076)."""
    cpi = money.index_by_year(store.read(state, "market_geo_year"), "cpi_u")
    base = baseline_units(state, store, origin, None)
    juris = store.read(state, "jurisdictions")[["geoid", "name", "kind", "state"]]
    places = base.merge(juris, on="geoid", how="left")
    places["state"] = state.upper()
    local = type_fees(places[["geoid", "state"]], all_coded_fees(), cpi).drop(columns="state")
    places = places.merge(local, on="geoid", how="left")
    places["acs_geo"] = places["kind"].map(adu.ACS_PREFIX) + ":" + places["geoid"]
    acs = adu.acs_values(store.read(state, "acs_geo_year"), places["acs_geo"], origin, cpi)
    places = places.merge(acs[["home_value", "rent"]], left_on="acs_geo", right_index=True, how="left")
    places["home_value_filled"] = places["home_value"].isna()
    places["home_value"] = places["home_value"].fillna(places["home_value"].median())
    parcels = store.read(state, "parcels")
    if parcels is not None:
        parcels = parcels[parcels["jurisdiction_geoid"].isin(places["geoid"])]
        places = places.merge(
            fees.parcel_inputs(parcels, origin, fees.central_params()), on="geoid", how="left"
        )
    return places
