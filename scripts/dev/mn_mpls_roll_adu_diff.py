"""Counts behind `reports/mn/adu-coverage-and-undercount.md` §3: ADUs added to Minneapolis single-family lots
between assessor rolls, matched to ADU-typed CCS permits (D-074 step 1, k).

    uv run python scripts/dev/mn_mpls_roll_adu_diff.py

Descriptive counts only (data thread): no engine, scenario or calibration run. Reads the registered assessor
tables through the adapter's cached download (non-personal fields only), the processed `parcels` (2017 land
use) and `permits` tables, all through `holdout.apply`. The rule is the report's §2 and
`lotline.adapters.states.mn.mpls_roll_diff`. Writes aggregates to `reports/mn/mpls-roll-adu-diff.json`; no
parcel-level table is written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from lotline.adapters.states.mn import mpls_assessor_parcels as ma
from lotline.adapters.states.mn import mpls_roll_diff as md
from lotline.io import DataStore
from lotline.validation import holdout

STATE = "MN"
OUT_JSON = Path(__file__).resolve().parents[2] / "reports" / "mn" / "mpls-roll-adu-diff.json"
PAIRS = {"main": (2017, 2026, "2025-06-30"), "short": (2017, 2024, "2023-06-30")}
START = "2017-01-01"


def read_roll(store: DataStore, year: int) -> pd.DataFrame:
    roll = ma.Roll(year)
    raw = ma.download(roll, store)
    raw = raw.drop(columns=[c for c in raw.columns if c in ma.PERSONAL])
    df = raw.rename(columns={v: k for k, v in roll.fields.items()})[md_cols()]
    df = df.assign(
        jurisdiction_geoid=ma.MINNEAPOLIS, vintage=year, vintage_date=pd.Timestamp(f"{year}-01-02")
    )
    df = holdout.apply(
        df, STATE, geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage", snapshot=True
    )
    return md.summarize_roll(df)


def md_cols() -> list[str]:
    return ["pin", "building_use", "units", "year_built", "area_sqft"]


def land_use_2017(store: DataStore) -> pd.Series:
    p = store.read(STATE, "parcels")
    p = p[(p["source"] == ma.SOURCE) & (p["vintage"] == 2017)]
    p = holdout.apply(p, STATE, geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage",
                      snapshot=True)  # fmt: skip
    return p.set_index("parcel_id")["land_use_std"]


def permits(store: DataStore) -> pd.DataFrame:
    p = store.read(STATE, "permits")
    p = holdout.apply(p, STATE, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year")
    return p


def _ints(s: pd.Series) -> dict[str, int]:
    return {str(int(k)): int(v) for k, v in s.items()}


def main() -> None:
    store = DataStore()
    land = land_use_2017(store)
    rolls = {y: read_roll(store, y) for y in range(2017, 2027)}
    allp = permits(store)
    ccs = allp[allp["source"] == "mpls_ccs_permits"]
    out: dict = {"rule_commit": "9e4b5390", "pairs": {}}
    for name, (y0, y1, end) in PAIRS.items():
        diff = md.diff_rolls(rolls[y0], rolls[y1], land)
        denom = set(diff.index)
        r_all = set(diff.index[diff["in_r"]])
        r_nodup = set(diff.index[diff["in_r"] & (diff["group"] != "duplex_adu")])
        r_strict = set(diff.index[diff["strict"]])
        sets = md.permit_parcels(ccs, START, end)
        versions = {
            "as_written": md.undercount(r_all, sets["P"], sets["a_written"], denom),
            "duplexes_removed": md.undercount(r_nodup, sets["P"], sets["a_noduplex"], denom),
            "wide": md.undercount(r_nodup, sets["P"], sets["a_wide"], denom),
            "strict_r": md.undercount(r_strict, sets["P"], sets["a_noduplex"], denom),
        }
        rest = r_nodup - sets["P"]
        years = (pd.Timestamp(f"{y1}-01-02") - pd.Timestamp(f"{y0}-01-02")).days / 365.25
        out["pairs"][name] = {
            "rolls": [y0, y1],
            "permit_window": [START, end],
            "years": years,
            "sf_before": diff.attrs["sf_before"],
            "sf_before_dropped": diff.attrs["sf_before_dropped"],
            "compared": len(diff),
            "groups": diff["group"].value_counts().to_dict(),
            "rate_per_1000_yr_R": len(r_nodup) / len(diff) * 1000 / years,
            "versions": versions,
            "checks": {
                "R_not_P_seen_by_parser": len(rest & sets["seen_by_parser"]),
                "R_not_P_with_adu_permit_outside_window": len(rest & sets["P_outside"]),
                "P_live": len(sets["P_live"]),
                "P_not_R_live": len(sets["P_live"] - r_nodup),
                "P_outside_window": len(sets["P_outside"]),
            },
        }
    # check 3: first ADU label by roll year (2017 denominator), CCS ADU-typed and Met Council ADU rows by year
    base = md.diff_rolls(rolls[2017], rolls[2026], land)
    first: dict[int, int] = {}
    seen: set[str] = set()
    for y in range(2018, 2027):
        d = md.diff_rolls(rolls[2017], rolls[y], land)
        now = set(d.index[d["in_r"]]) - seen
        first[y] = len(now)
        seen |= now
    metc = allp[
        (allp["source"] == "metc_residential_permits") & (allp["jurisdiction_geoid"] == ma.MINNEAPOLIS)
    ]
    out["by_year"] = {
        "roll_first_adu_label": first,
        "ccs_adu_typed_parcels": ccs[ccs["building_type_std"] == "ADU"]
        .groupby("issue_year")["parcel_id"]
        .nunique()
        .pipe(_ints),
        "metc_adu_units": metc[metc["building_type_std"] == "ADU"]
        .groupby("issue_year")["units_new"]
        .sum()
        .pipe(_ints),
    }
    out["base_compared"] = len(base)
    OUT_JSON.write_text(
        json.dumps(out, indent=2, default=lambda x: int(x) if hasattr(x, "__int__") else str(x)) + "\n"
    )
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
