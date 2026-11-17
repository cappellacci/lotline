"""Compare a run's rows with the rows already coded in config/fees/<st>.csv (dry runs, LESSONS §0).

Per (place, building type, component): the sum of `amount_per_unit_usd` over the newest schedule year in each
table. Reads only the config CSVs and the run's rows; runs no model.
"""

from __future__ import annotations

import pandas as pd


def totals(df: pd.DataFrame) -> pd.DataFrame:
    """Per place, building type and component: newest year and the summed per-unit amount of that year."""
    if df.empty:
        return pd.DataFrame(
            columns=["jurisdiction_geoid", "building_type_std", "fee_component", "year", "per_unit", "rows"]
        )
    d = df.copy()
    d["year"] = d["year"].astype(int)
    newest = d.groupby(["jurisdiction_geoid", "building_type_std", "fee_component"])["year"].transform("max")
    d = d[d["year"] == newest]
    g = d.groupby(["jurisdiction_geoid", "building_type_std", "fee_component"])
    return g.agg(
        year=("year", "max"), per_unit=("amount_per_unit_usd", "sum"), rows=("fee_type", "size")
    ).reset_index()


def compare(run: pd.DataFrame, existing: pd.DataFrame, places: list[str] | None = None) -> pd.DataFrame:
    """Side-by-side totals; `status` is match (within 2% or $25), differ, run_only or existing_only."""
    if places is not None:
        existing = existing[existing["jurisdiction_geoid"].isin(places)]
        run = run[run["jurisdiction_geoid"].isin(places)] if not run.empty else run
    keys = ["jurisdiction_geoid", "building_type_std", "fee_component"]
    m = totals(run).merge(totals(existing), on=keys, how="outer", suffixes=("_run", "_existing"))

    def status(r) -> str:
        if pd.isna(r["per_unit_run"]):
            return "existing_only"
        if pd.isna(r["per_unit_existing"]):
            return "run_only"
        a, b = r["per_unit_run"], r["per_unit_existing"]
        return "match" if abs(a - b) <= max(25.0, 0.02 * max(a, b)) else "differ"

    m["status"] = m.apply(status, axis=1) if not m.empty else []
    return m.sort_values(keys).reset_index(drop=True)
