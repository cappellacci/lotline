"""Inputs for the D-082 (proposed) missing-middle counts (`lotline.model.mm_counts`): structure check only.

    uv run python scripts/dev/mm_counts_d082.py --dry

`--dry` reads each candidate permit source, parcel roll and BPS table through `mm_counts.blind` (St. Paul and
Ramsey County dropped outright, then `holdout.apply`) and prints **structure only**: source, rows, issue-year
or vintage span, which columns are present and the parcel-ID fill. It prints no 2–4 unit count, no building
count, no ratio and no breakdown by building type or land use.

Without `--dry` the script stops: D-082 is proposed, not approved, and every count needs Ben's go-ahead after
the code is reviewed. The counting run will be added here once he gives it.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from lotline.io import DataStore
from lotline.model import mm_counts as mc

# D-082 §2: the strong permit candidates (review §2), by state and processed file name
# (processed/<st>/permits/<name>.parquet).
PERMIT_SOURCES = {
    "MN": [("Minneapolis", "mpls_permits")],
    "NC": [("Mecklenburg", "meck_permits"), ("Raleigh", "raleigh_permits"), ("Durham", "durham_permits")],
    "OH": [("Columbus", "columbus_permits"), ("Cincinnati", "cincy_permits")],
    "TX": [("Austin", "austin_permits"), ("College Station", "cstx_permits")],
    "OR": [("Portland", "portland_permits"), ("Bend", "bend_permits"), ("Medford", "medford_permits")],
}
# D-082 §2 test B rolls (Wake 2019→2023, Franklin 2016→2025, Minneapolis 2017→2026, Met Council 2021→2025).
ROLL_SOURCES = {
    "NC": [("Wake", "wake_realestate")],
    "OH": [("Franklin", "oh_parcels")],
    "MN": [("Minneapolis", "mpls_assessor_parcels"), ("Met Council", "metc_parcels")],
}
PERMIT_COLUMNS = ("parcel_id", "units_new", "building_type_std", "is_conversion", "is_demolition", "address",
                  "issue_date", "n_buildings")  # fmt: skip
ROLL_COLUMNS = (
    "parcel_id",
    "units",
    "lot_sqft",
    "land_use_std",
    "sf_only_zoned",
    "year_built",
    "vintage_date",
)
BPS_COLUMNS = ("geoid", "year", "bldgs_2", "bldgs_3_4")


def _read(store: DataStore, state: str, table: str, source: str) -> pd.DataFrame | None:
    path = store.processed(state, table, source)
    return pd.read_parquet(path) if path.exists() else None


def _fill(s: pd.Series) -> float:
    t = s.astype("string").str.strip()
    return float((t.notna() & (t != "")).mean()) if len(s) else float("nan")


def _present(df: pd.DataFrame, cols: tuple[str, ...]) -> str:
    return " ".join(f"{c}={'y' if c in df else 'n'}" for c in cols)


def dry(store: DataStore) -> None:
    print("D-082 inputs, structure only (no counts of 2-4 unit buildings, no ratios)\n")
    print("Permit sources")
    for state, sources in PERMIT_SOURCES.items():
        for place, source in sources:
            raw = _read(store, state, "permits", source)
            if raw is None:
                print(f"  {state} {place:16} {source:22} not built")
                continue
            df = mc.blind(raw, state, date_col="issue_date", year_col="issue_year")
            years = pd.to_numeric(df["issue_year"])
            fill = _fill(df["parcel_id"]) if "parcel_id" in df else float("nan")
            print(
                f"  {state} {place:16} {source:22} rows={len(df):>8,} (blinded {len(raw) - len(df):,}) "
                f"years={int(years.min())}-{int(years.max())} parcel_fill={fill:.3f}"
            )
            print(f"      {_present(df, PERMIT_COLUMNS)}")
    print("\nParcel rolls")
    for state, sources in ROLL_SOURCES.items():
        for place, source in sources:
            raw = _read(store, state, "parcels", source)
            if raw is None:
                print(f"  {state} {place:16} {source:22} not built")
                continue
            date_col = "vintage_date" if "vintage_date" in raw else None
            df = mc.blind(raw, state, date_col=date_col, year_col="vintage", snapshot=True)
            vint = sorted(pd.to_numeric(df["vintage"]).dropna().astype(int).unique().tolist())
            print(
                f"  {state} {place:16} {source:22} rows={len(df):>9,} (blinded {len(raw) - len(df):,}) "
                f"vintages={vint} parcel_fill={_fill(df['parcel_id']):.3f}"
            )
            print(f"      {_present(df, ROLL_COLUMNS)}")
    print("\nBPS place-year tables")
    for state in PERMIT_SOURCES:
        raw = store.read(state, "bps_place_year")
        if raw is None:
            print(f"  {state} not built")
            continue
        df = mc.blind(raw, state, geoid_col="geoid", year_col="year")
        years = pd.to_numeric(df["year"])
        span = f"{int(years.min())}-{int(years.max())}"
        print(f"  {state} rows={len(df):>7,} years={span} {_present(df, BPS_COLUMNS)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true", help="print input structure only (no counts)")
    args = ap.parse_args()
    if not args.dry:
        print("D-082 is proposed, not approved: counts need Ben's go-ahead. Only --dry is available.")
        return 2
    dry(DataStore())
    return 0


if __name__ == "__main__":
    sys.exit(main())
