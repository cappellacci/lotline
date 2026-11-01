"""Counting permitted units, with repeated project totals counted once (analysis plan D-008 and D-036).

City permit files often put a multi-building project's **total** unit count on every building's permit
(Columbus 2023: nine permits on one parcel each say 198 units; Austin 2022: nine permits each say 280).
Summing them counts the project nine times. The adapters keep the numbers as reported; this build step
decides what to count.

**The rule, in plain words:** if at least `repeated_total_min_permits` (3) new-construction permits on the
same parcel, in the same jurisdiction and year, all report the same large unit count (at least
`repeated_total_min_units`, 50), that count is the project's total. It is counted once, on the permit with the
lowest `permit_id`; the others are flagged and count 0 units. All parameters are in
`config/params/permits.yaml`.

**Permits with no parcel number (D-036):** some cities (Fort Worth, Dallas) publish no parcel. Their permits
are grouped by jurisdiction, year, **day** (`issue_date`, else `application_date`) and the same unit count of
at least 50, again with at least 3 permits. Within such a group only permits whose floor area per unit is
below `repeated_total_max_sqft_per_unit` (300 sq ft, under any real home) or whose floor area is missing are
read as repeating the total: their count goes once on the lowest `permit_id` among them. Permits with a
plausible floor area per unit are real buildings and stay as reported. Permits with no date are never grouped.

- Demolition permits are never grouped.
- Different years, parcels, days or unit counts are different groups.
- Runs of duplexes or fourplexes are never touched: they are below the 50-unit floor.
- The rule can be switched off (`dedupe=False`) to show the as-reported count as a sensitivity.
"""

from __future__ import annotations

import pandas as pd

from lotline.config import load_params

GROUP = ["jurisdiction_geoid", "parcel_id", "issue_year", "units_new"]
DAY_GROUP = ["jurisdiction_geoid", "issue_year", "day", "units_new"]  # permits with no parcel (D-036)
SIZE_CLASSES = ["1", "2", "3_4", "5p"]  # same classes as the Census BPS (build/panels.py)


def _params(params: dict | None) -> dict:
    return params if params is not None else load_params("permits")


def _thresholds(params: dict | None) -> tuple[int, int]:
    p = _params(params)
    return int(p["repeated_total_min_units"].value), int(p["repeated_total_min_permits"].value)


def _column(permits: pd.DataFrame, name: str) -> pd.Series:
    """An optional column, all null when the source doesn't have it."""
    return permits[name] if name in permits else pd.Series(pd.NA, index=permits.index, dtype="object")


def _flag_no_parcel_repeats(permits: pd.DataFrame, candidate: pd.Series, params: dict | None) -> pd.Series:
    """D-036: repeated totals among large permits with no parcel, grouped by day; implausible areas only."""
    day = pd.to_datetime(_column(permits, "issue_date")).fillna(
        pd.to_datetime(_column(permits, "application_date"))
    )
    c = permits.loc[candidate & day.notna(), DAY_GROUP[:2] + ["units_new", "permit_id"]]
    c = c.assign(day=day[c.index].dt.normalize())
    if c.empty:
        return pd.Series(False, index=permits.index)
    _, min_permits = _thresholds(params)
    max_sqft = float(_params(params)["repeated_total_max_sqft_per_unit"].value)
    area = pd.to_numeric(_column(permits, "floor_area_sqft")[c.index], errors="coerce").astype("Float64")
    # Missing floor area counts as implausible: nothing shows the permit is a real building.
    implausible = (area / c["units_new"].astype("Float64")).lt(max_sqft).fillna(True)
    size = c.groupby(DAY_GROUP)["permit_id"].transform("size")
    c = c[(size >= min_permits) & implausible.astype(bool)].sort_values("permit_id")
    flagged = c.groupby(DAY_GROUP).cumcount() > 0
    return flagged.reindex(permits.index, fill_value=False).astype(bool)


def flag_repeated_totals(permits: pd.DataFrame, params: dict | None = None) -> pd.Series:
    """True for each permit whose `units_new` repeats a project total already counted on another permit."""
    min_units, min_permits = _thresholds(params)
    parcel = permits["parcel_id"].astype("string").str.strip()
    has_parcel = parcel.fillna("").ne("").astype(bool)
    large = (
        permits["units_new"].fillna(0).ge(min_units) & ~permits["is_demolition"].fillna(False).astype(bool)
    ).astype(bool)
    candidate = large & has_parcel
    c = permits.loc[candidate, GROUP[:1] + GROUP[2:] + ["permit_id"]].assign(parcel_id=parcel[candidate])
    c = c.sort_values("permit_id")
    size = c.groupby(GROUP)["permit_id"].transform("size")
    order = c.groupby(GROUP).cumcount()
    flagged = ((size >= min_permits) & (order > 0)).reindex(permits.index, fill_value=False).astype(bool)
    flagged |= _flag_no_parcel_repeats(permits, large & ~has_parcel, params)
    return flagged.rename("repeated_total")


def size_class(units: pd.Series) -> pd.Series:
    """BPS size class from the units a permit reports: 1, 2, 3-4 or 5+ (null if 0 or unknown)."""
    bins = pd.cut(units.astype("Float64"), [0.5, 1.5, 2.5, 4.5, float("inf")], labels=SIZE_CLASSES)
    return bins.astype("string")


def count_units(permits: pd.DataFrame, *, dedupe: bool = True, params: dict | None = None) -> pd.DataFrame:
    """New units by jurisdiction × year × size class (`units`, `n_permits`).

    With `dedupe` (the default, primary count) repeated project totals count once; without it, units are
    summed as reported (sensitivity). The size class comes from each permit's own reported units.
    """
    p = permits[permits["units_new"].fillna(0) > 0]
    units = p["units_new"].astype("Int64")
    if dedupe:
        units = units.mask(flag_repeated_totals(p, params), 0)
    out = pd.DataFrame(
        {
            "jurisdiction_geoid": p["jurisdiction_geoid"],
            "issue_year": p["issue_year"],
            "size_class": size_class(p["units_new"]),
            "units": units,
        }
    )
    keys = ["jurisdiction_geoid", "issue_year", "size_class"]
    return (
        out.groupby(keys, as_index=False)
        .agg(units=("units", "sum"), n_permits=("units", "size"))
        .astype({"units": "Int64", "n_permits": "Int64"})
    )
