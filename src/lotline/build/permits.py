"""Counting permitted units, with repeated project totals counted once (analysis plan D-008).

City permit files often put a multi-building project's **total** unit count on every building's permit
(Columbus 2023: nine permits on one parcel each say 198 units; Austin 2022: nine permits each say 280).
Summing them counts the project nine times. The adapters keep the numbers as reported; this build step
decides what to count.

**The rule, in plain words:** if at least `repeated_total_min_permits` (3) new-construction permits on the
same parcel, in the same jurisdiction and year, all report the same large unit count (at least
`repeated_total_min_units`, 50), that count is the project's total. It is counted once, on the permit with the
lowest `permit_id`; the others are flagged and count 0 units. Both parameters are in
`config/params/permits.yaml`.

- Demolition permits are never grouped.
- Permits without a `parcel_id` are never grouped: without a parcel we can't tell one project from two.
- Different years, parcels or unit counts are different groups.
- The rule can be switched off (`dedupe=False`) to show the as-reported count as a sensitivity.
"""

from __future__ import annotations

import pandas as pd

from lotline.config import load_params

GROUP = ["jurisdiction_geoid", "parcel_id", "issue_year", "units_new"]
SIZE_CLASSES = ["1", "2", "3_4", "5p"]  # same classes as the Census BPS (build/panels.py)


def _thresholds(params: dict | None) -> tuple[int, int]:
    p = params if params is not None else load_params("permits")
    return int(p["repeated_total_min_units"].value), int(p["repeated_total_min_permits"].value)


def flag_repeated_totals(permits: pd.DataFrame, params: dict | None = None) -> pd.Series:
    """True for each permit whose `units_new` repeats a project total already counted on another permit."""
    min_units, min_permits = _thresholds(params)
    parcel = permits["parcel_id"].astype("string").str.strip()
    candidate = (
        permits["units_new"].fillna(0).ge(min_units)
        & ~permits["is_demolition"].fillna(False).astype(bool)
        & parcel.fillna("").ne("")
    ).astype(bool)
    c = permits.loc[candidate, GROUP[:1] + GROUP[2:] + ["permit_id"]].assign(parcel_id=parcel[candidate])
    c = c.sort_values("permit_id")
    size = c.groupby(GROUP)["permit_id"].transform("size")
    order = c.groupby(GROUP).cumcount()
    flagged = (size >= min_permits) & (order > 0)
    return flagged.reindex(permits.index, fill_value=False).astype(bool).rename("repeated_total")


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
