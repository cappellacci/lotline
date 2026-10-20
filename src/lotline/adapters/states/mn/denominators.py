"""Minnesota parcel denominators vs the ACS fallback (round 3, task 4).

The one-source-per-jurisdiction choice is the state config's `parcel_sources` (config/states/mn.yaml),
applied by `lotline.build.eligible.single_source` inside `eligible.load` (#147). This helper only reproduces
the PR's check: eligible parcels from the rolls against the ACS one-unit-detached fallback, side by side.
"""

from __future__ import annotations

import pandas as pd


def compare_with_acs(
    parcel_rows: pd.DataFrame,
    acs_rows: pd.DataFrame,
    jurisdictions: pd.DataFrame,
    *,
    year: int,
    theme: str = "adu",
    largest: int = 20,
    counties: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Eligible parcels from rolls vs the ACS fallback for the `largest` places by 2020 population."""
    j = jurisdictions[jurisdictions["kind"] == "place"]
    if counties is not None:
        j = j[j["county_geoid"].isin(counties)]
    top = j.sort_values("pop_2020", ascending=False).head(largest)[["geoid", "name", "pop_2020"]]

    def pick(rows: pd.DataFrame, label: str) -> pd.Series:
        r = rows[(rows["theme"] == theme) & (rows["year"] == year)]
        return r.set_index("jurisdiction_geoid")["eligible_parcels"].rename(label)

    out = top.set_index("geoid").join(pick(parcel_rows, "parcels")).join(pick(acs_rows, "acs"))
    q = parcel_rows[(parcel_rows["theme"] == theme) & (parcel_rows["year"] == year)]
    out = out.join(q.set_index("jurisdiction_geoid")["denominator_quality"].rename("quality"))
    out["ratio"] = (out["parcels"] / out["acs"]).round(2)
    return out.reset_index().rename(columns={"index": "geoid"})
