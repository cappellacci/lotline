"""Compare a run's rows with the rows already coded in config/fees/<st>.csv (dry runs, LESSONS §0).

Per (place, building type, component): the sum of `amount_per_unit_usd` over the newest schedule year in each
table. Reads only the config CSVs and the run's rows; runs no model.
"""

from __future__ import annotations

import pandas as pd

TYPES = ("SFD", "U2", "U3_4", "ADU")


def totals(df: pd.DataFrame) -> pd.DataFrame:
    """Per place, building type (SFD, U2, U3_4, ADU) and component: the summed per-unit amount of the newest
    schedule year. A house sums its SFD and OTHER rows; other types use their own rows if any, else the
    place's OTHER rows (as fee_levels does, D-066, without its "from SFD" step, so a gap stays visible)."""
    cols = ["jurisdiction_geoid", "building_type_std", "fee_component", "year", "per_unit", "rows"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    d = df.copy()
    d["year"] = d["year"].astype(int)
    out = []
    for (g, comp), sub in d.groupby(["jurisdiction_geoid", "fee_component"]):
        for t in TYPES:
            if t == "SFD":  # a house pays its SFD rows and the OTHER rows (fee_levels.py)
                rows = sub[sub["building_type_std"].isin(["SFD", "OTHER"])]
            else:
                rows = sub[sub["building_type_std"] == t]
            if rows.empty:
                rows = sub[sub["building_type_std"] == "OTHER"]
            if rows.empty:
                continue
            rows = rows[rows["year"] == rows["year"].max()]
            out.append(
                (g, t, comp, int(rows["year"].max()), float(rows["amount_per_unit_usd"].sum()), len(rows))
            )
    return pd.DataFrame(out, columns=cols)


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
