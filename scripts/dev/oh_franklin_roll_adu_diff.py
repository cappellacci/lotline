#!/usr/bin/env python3
"""Counts behind `reports/oh/adu-coverage-and-undercount.md` §2: second homes added to Franklin County
single-family lots, Dec 2019 → Dec 2024, and the Columbus flag undercount k (D-074 step 1).

    uv run python scripts/dev/oh_franklin_roll_adu_diff.py [--cache DIR]

Descriptive counts only (data thread): no engine, scenario or calibration run. Downloads the Franklin County
Auditor's `Dwelling.xlsx`, `Improvement.xlsx` and `Parcel.xlsx` for the two snapshots through the IO layer
(`raw/franklin_auditor/<snapshot>/`, manifest entries under `dev.oh_franklin_roll_adu_diff`), reading only
parcel number, card, units, year built, living area, land use, acreage and improvement code (no address or
owner field), and Columbus's processed permits through `holdout.apply` (Ohio has none). The rule is in the
report's §2.1 and `lotline.adapters.states.oh.franklin_roll_diff`.

`--cache DIR` keeps the columns read as parquet in DIR (outside the repo). Writes aggregates to
`reports/oh/franklin-roll-adu-diff.json`; no parcel-level table is written.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pandas as pd

from lotline.adapters.states.oh import franklin_roll_diff as fd
from lotline.adapters.states.oh.oh_parcels import luc_code, luc_crosswalk
from lotline.io import DataStore
from lotline.io.http import fetch
from lotline.validation import holdout

STATE = "OH"
BASE_URL = "https://apps.franklincountyauditor.com/Outside_User_Files"
LICENSE = "Franklin County Auditor public records (disclaimer: 'as is'; no reuse terms stated)"
ADAPTER, VERSION = "dev.oh_franklin_roll_adu_diff", "0.1"
BEFORE, AFTER = "2019-12-18", "2024-12-30"
YEARS = (pd.Timestamp(AFTER) - pd.Timestamp(BEFORE)).days / 365.25
FIRST_NEW_YEAR, LAST_YEAR = 2020, 2024
WINDOW = ("2020-01-01", "2024-06-30")
COLUMBUS = "3918000"
COLS = {
    "Dwelling": ["PARCEL ID", "CARD", "LIVUNITS", "YRBLT", "SFLA"],
    "Improvement": ["PARCEL ID", "CARD", "CODE", "YRBLT"],
    "Parcel": ["PARCEL ID", "LUC", "ACRES"],
}
ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "reports" / "oh" / "franklin-roll-adu-diff.json"
DWELLING_NEW = ("101|", "102|", "103|", "106|")
NEW_STRUCTURE = "1,2,3 Family - New Structure"


def _history():
    spec = importlib.util.spec_from_file_location(
        "oh_franklin_history", ROOT / "scripts/dev/oh_franklin_history.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(store: DataStore, date: str, name: str, cache: Path | None) -> pd.DataFrame:
    hit = cache / f"{date}_{name}.parquet" if cache else None
    if hit is not None and hit.exists():
        df = pd.read_parquet(hit)
        df.columns = [c.strip() for c in df.columns]
        if set(COLS[name]) <= set(df.columns):
            return df[COLS[name]]
    sub = store.raw("franklin_auditor", date) / ("appraisal" if name != "Parcel" else "")
    path = fetch(
        f"{BASE_URL}/{date[:4]}/{date}%20Appraisal/{name}.xlsx",
        sub / f"{name}.xlsx",
        store=store,
        source="franklin_auditor",
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
    )
    df = pd.read_excel(path, dtype=str, usecols=lambda c: c.strip() in COLS[name])
    df.columns = [c.strip() for c in df.columns]
    if hit is not None:
        cache.mkdir(parents=True, exist_ok=True)
        df.to_parquet(hit)
    return df[COLS[name]]


def key(parcel: pd.Series) -> pd.Series:
    """Columbus permit parcel '010-012345' / '010012345' → Auditor parcel number '010-012345-00'."""
    d = parcel.astype("string").str.replace(r"\D", "", regex=True).str[:9]
    return (d.str[:3] + "-" + d.str[3:] + "-00").where(d.str.len() == 9)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", type=Path)
    args = ap.parse_args()
    store = DataStore()
    hist = _history()
    roll = store.read(STATE, "parcels")
    roll = roll.loc[roll["county_geoid"] == hist.COUNTY, ["parcel_id", "jurisdiction_geoid"]]
    roll = roll.drop_duplicates("parcel_id")  # a few IDs repeat (multi-part polygons)
    crosswalk = luc_crosswalk()

    s = {}
    for date in (BEFORE, AFTER):
        s[date] = fd.summarize(
            read(store, date, "Dwelling", args.cache), read(store, date, "Parcel", args.cache)
        )
    b = s[BEFORE]
    land_use = luc_code(b["luc"]).map(crosswalk).fillna("UNKNOWN")
    land_use.index = b.index
    ids = pd.DataFrame({"parcel_id": hist.roll_id(pd.Series(b.index, index=b.index))})
    juris = pd.Series(hist.place(ids, roll).values, index=b.index)

    diff = fd.diff_rolls(b, s[AFTER], land_use, juris, FIRST_NEW_YEAR)
    garages = fd.new_garages(
        read(store, BEFORE, "Improvement", args.cache),
        read(store, AFTER, "Improvement", args.cache),
        FIRST_NEW_YEAR,
        LAST_YEAR,
    )
    diff["new_garage"] = diff.index.isin(garages)

    g = diff.groupby(diff["jurisdiction_geoid"].fillna("unplaced"))
    by_j = pd.DataFrame(
        {
            "sf_parcels": g.size(),
            "gained": g["gained"].sum(),
            "strict": g["strict"].sum(),
            "new_garage": g["new_garage"].sum(),
            "added_area": g["added_area"].sum(),
        }
    )
    for grp in (*fd.GAINED_GROUPS, "merge"):
        by_j[grp] = g["group"].apply(lambda x, grp=grp: int((x == grp).sum()))
    names = store.read(STATE, "jurisdictions").set_index("geoid")["name"]
    by_j["name"] = by_j.index.map(names)
    by_j = by_j.sort_values("sf_parcels", ascending=False)

    # Columbus undercount
    permits = pd.read_parquet(store.processed(STATE, "permits", "columbus_permits"))
    permits = holdout.apply(permits, STATE, geoid_col="jurisdiction_geoid", date_col="issue_date")
    permits = permits.loc[permits["issue_date"].between(*WINDOW)].assign(key=lambda d: key(d["parcel_id"]))
    flagged = permits.loc[permits["adu_type"].notna()]
    raw = permits["permit_class_raw"].fillna("")
    new_struct = raw.str.endswith(NEW_STRUCTURE) & permits["adu_type"].isna()
    col = diff.loc[diff["jurisdiction_geoid"] == COLUMBUS]
    denom = set(col.index)
    R = set(col.index[col["gained"]])
    P = set(flagged["key"].dropna())
    variants = {
        "as_written": set(permits.loc[new_struct & raw.str.startswith(DWELLING_NEW), "key"].dropna()),
        "adu_only": set(
            permits.loc[
                new_struct & raw.str.startswith(DWELLING_NEW) & ~raw.str.startswith("103|"), "key"
            ].dropna()
        ),
        "with_434": set(
            permits.loc[
                new_struct & ~raw.str.startswith("103|") & raw.str.match(r"^(101|102|106|434)\|"), "key"
            ].dropna()
        ),
    }
    k = {v: fd.undercount(R, P, denom, u) for v, u in variants.items()}
    R_dup = {p for p in R if p in variants["as_written"] - variants["adu_only"]}
    k["duplex_removed_from_R"] = fd.undercount(R - R_dup, P, denom, variants["adu_only"])
    k["envelope"] = {
        "flagged_in_denominator": len(P & denom),
        "flagged_with_new_garage": len(P & denom & set(col.index[col["new_garage"]])),
        "flagged_with_added_area": len(P & denom & set(col.index[col["added_area"]])),
        "columbus_new_garage_parcels": int(col["new_garage"].sum()),
    }
    k["flagged_by_year"] = flagged["issue_date"].dt.year.value_counts().sort_index().to_dict()

    total = {
        "sf_parcels": int(len(diff)),
        "sf_dropped": diff.attrs["sf_dropped"],
        "gained": int(diff["gained"].sum()),
        "strict": int(diff["strict"].sum()),
        "groups": diff["group"].value_counts().to_dict(),
        "new_garage": int(diff["new_garage"].sum()),
        "added_area": int(diff["added_area"].sum()),
        "years": YEARS,
    }
    lo, hi = fd.wilson(total["gained"], total["sf_parcels"])
    total["rate_per_1000_yr"] = total["gained"] / total["sf_parcels"] * 1000 / YEARS
    total["rate_ci95"] = (lo * 1000 / YEARS, hi * 1000 / YEARS)
    print(json.dumps(total, indent=1, default=str))
    print(by_j.head(20).to_string())
    print(json.dumps(k, indent=1, default=str))
    OUT_JSON.write_text(
        json.dumps(
            {
                "rolls": [BEFORE, AFTER],
                "total": total,
                "by_jurisdiction": by_j.reset_index().to_dict("records"),
                "columbus": k,
            },
            indent=1,
            default=lambda o: int(o) if hasattr(o, "__int__") else str(o),
        )
    )


if __name__ == "__main__":
    main()
