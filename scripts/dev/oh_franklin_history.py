#!/usr/bin/env python3
"""Check D-035's scaled eligible-lot history against Franklin County's real year-end parcel rolls (OH S6a).

    uv run python scripts/dev/oh_franklin_history.py            # downloads once, then reads the cache
    uv run python scripts/dev/oh_franklin_history.py --csv out.csv

Ohio has one parcel roll per jurisdiction (Franklin County: the statewide snapshot of 2023-11-13), so
`eligible_parcels` holds a real count only for 2023; every other year is the jurisdiction's ACS series scaled
to that roll (`parcels_scaled_acs`, D-035, `build.eligible.scale_history`). The Franklin County Auditor
publishes a `Parcel.xlsx` (parcel ID and DTE land-use code) in every appraisal snapshot since 2016. This
script reads the last snapshot of each year 2016-2025, counts the parcels the eligibility rule would count,
and compares them with the processed `eligible_parcels` rows for the same jurisdiction and year:

- **adu**: land use SF_DETACHED (the `oh_parcels` crosswalk, `config/crosswalks/oh_dte_luc.csv`), as in
  `build.eligible.classify`; the lot floor is 0 and units, exclusions and zoning are unknown in Ohio, so
  nothing else filters.
- **missing_middle**: SF_DETACHED or VACANT_RESIDENTIAL (zoning unknown counts as single-family-only).

Each archive parcel takes the jurisdiction of the same parcel in the processed `parcels` table. A parcel no
longer in the roll (split, combined or renumbered by 2023) takes its taxing district's jurisdiction where at
least `DISTRICT_SHARE` of the district's matched parcels lie in one jurisdiction; otherwise it is left out and
counted in the "unplaced" line. Only jurisdictions with at least `MIN_ELIGIBLE` eligible lots are reported.

The archive holds Franklin County parcels only, while `eligible_parcels` counts a jurisdiction in every county
it reaches (Dublin, Westerville, Reynoldsburg …). So the summary uses only jurisdictions with at
least `MIN_COUNTY_SHARE` of their single-family houses in Franklin County (the 2023 roll); the others are
listed with an approximate gap that divides the archive count by that share (it assumes the share did not
change).

It is a check, not an input: nothing here feeds a processed table. It downloads through the IO layer (the
files land in `raw/franklin_auditor/<snapshot>/` with a manifest entry) and reads only processed,
holdout-filtered tables (Ohio has no holdouts).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lotline.adapters.states.oh.oh_parcels import luc_code, luc_crosswalk
from lotline.io import DataStore
from lotline.io.http import fetch

BASE_URL = "https://apps.franklincountyauditor.com/Outside_User_Files"
LICENSE = "Franklin County Auditor public records (disclaimer: 'as is'; no reuse terms stated)"
ADAPTER, VERSION = "dev.oh_franklin_history", "0.1"
# The last appraisal snapshot of each year (directory listings read 2026-10-27; 2015 has none).
SNAPSHOTS = {
    2016: "2016-12-22",
    2017: "2017-12-19",
    2018: "2018-12-17",
    2019: "2019-12-18",
    2020: "2020-12-25",
    2021: "2021-12-22",
    2022: "2022-12-20",
    2023: "2023-12-26",
    2024: "2024-12-30",
    2025: "2025-12-31",
}
COUNTY = "39049"
DISTRICT_SHARE = 0.95
MIN_ELIGIBLE = 1000
MIN_COUNTY_SHARE = 0.99  # share of a jurisdiction's houses in Franklin County to compare it directly
THEMES = {"adu": {"SF_DETACHED"}, "missing_middle": {"SF_DETACHED", "VACANT_RESIDENTIAL"}}


def roll_id(auditor_id: pd.Series) -> pd.Series:
    """Auditor parcel number "010-023573-00" → statewide roll ID "39049010-023573"."""
    m = auditor_id.astype(str).str.strip().str.extract(r"^(\d{3})-(\d{6})")
    return COUNTY + m[0] + "-" + m[1]


def snapshot(store: DataStore, date: str) -> pd.DataFrame:
    year = date[:4]
    url = f"{BASE_URL}/{year}/{date}%20Appraisal/Parcel.xlsx"
    path = fetch(
        url,
        store.raw("franklin_auditor", date) / "Parcel.xlsx",
        store=store,
        source="franklin_auditor",
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
    )
    raw = pd.read_excel(path, usecols=["PARCEL ID", "LUC"], dtype=str)
    return pd.DataFrame({"parcel_id": roll_id(raw["PARCEL ID"]), "luc": raw["LUC"].str.strip()}).dropna(
        subset=["parcel_id"]
    )


def place(archive: pd.DataFrame, roll: pd.DataFrame) -> pd.Series:
    """Jurisdiction of each archive parcel: the roll's, else its taxing district's (if one dominates)."""
    by_parcel = roll.set_index("parcel_id")["jurisdiction_geoid"]
    j = archive["parcel_id"].map(by_parcel)
    district = roll["parcel_id"].str[5:8]
    share = roll.groupby(district)["jurisdiction_geoid"].agg(lambda s: s.value_counts(normalize=True).iloc[0])
    top = roll.groupby(district)["jurisdiction_geoid"].agg(lambda s: s.value_counts().index[0])
    fallback = top[share >= DISTRICT_SHARE]
    return j.fillna(archive["parcel_id"].str[5:8].map(fallback))


def county_share(parcels: pd.DataFrame) -> pd.Series:
    """Per jurisdiction reaching Franklin County: the share of its SF_DETACHED parcels inside it."""
    houses = parcels[parcels["land_use_std"] == "SF_DETACHED"]
    reach = houses.loc[houses["county_geoid"] == COUNTY, "jurisdiction_geoid"].unique()
    houses = houses[houses["jurisdiction_geoid"].isin(reach)]
    return (houses["county_geoid"] == COUNTY).groupby(houses["jurisdiction_geoid"]).mean()


def real_counts(store: DataStore, parcels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    roll = parcels[parcels["county_geoid"] == COUNTY][["parcel_id", "jurisdiction_geoid"]]
    crosswalk = luc_crosswalk()
    rows, unplaced = [], []
    for year, date in SNAPSHOTS.items():
        a = snapshot(store, date)
        a["land_use_std"] = luc_code(a["luc"]).map(crosswalk).fillna("UNKNOWN")
        a["jurisdiction_geoid"] = place(a, roll)
        for theme, uses in THEMES.items():
            hit = a[a["land_use_std"].isin(uses)]
            unplaced.append(
                {"year": year, "theme": theme, "unplaced": int(hit["jurisdiction_geoid"].isna().sum())}
            )
            n = hit.dropna(subset=["jurisdiction_geoid"]).groupby("jurisdiction_geoid").size()
            rows += [
                {"jurisdiction_geoid": g, "year": year, "theme": theme, "real": int(c)} for g, c in n.items()
            ]
    return pd.DataFrame(rows), pd.DataFrame(unplaced)


def compare(real: pd.DataFrame, eligible: pd.DataFrame, names: pd.Series, share: pd.Series) -> pd.DataFrame:
    e = eligible[eligible["jurisdiction_geoid"].isin(real["jurisdiction_geoid"].unique())]
    e = e[["jurisdiction_geoid", "year", "theme", "eligible_parcels", "denominator_source"]]
    out = real.merge(e, on=["jurisdiction_geoid", "year", "theme"], how="inner")
    out["gap_pct"] = 100 * (out["eligible_parcels"] - out["real"]) / out["real"]
    out.insert(1, "name", out["jurisdiction_geoid"].map(names))
    out["county_share"] = out["jurisdiction_geoid"].map(share)
    whole = out["real"] / out["county_share"]  # approximate count across all its counties
    out["gap_adj_pct"] = 100 * (out["eligible_parcels"] - whole) / whole
    big = out[(out["year"] == 2023) & (out["real"] >= MIN_ELIGIBLE)][["jurisdiction_geoid", "theme"]]
    return out.merge(big, on=["jurisdiction_geoid", "theme"]).sort_values(
        ["theme", "jurisdiction_geoid", "year"]
    )


def growth(table: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Change start → end in the real and the scaled series, per jurisdiction and theme."""
    w = table.pivot_table(index=["theme", "name"], columns="year", values=["real", "eligible_parcels"])
    out = pd.DataFrame(
        {
            "real_growth_pct": 100 * (w[("real", end)] / w[("real", start)] - 1),
            "scaled_growth_pct": 100 * (w[("eligible_parcels", end)] / w[("eligible_parcels", start)] - 1),
        }
    )
    return out.round(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, help="write the per-year comparison here")
    args = ap.parse_args()
    store = DataStore()
    parcels = store.read("OH", "parcels")
    real, unplaced = real_counts(store, parcels)
    jur = store.read("OH", "jurisdictions").set_index("geoid")["name"]
    table = compare(real, store.read("OH", "eligible_parcels"), jur, county_share(parcels))
    if args.csv:
        table.to_csv(args.csv, index=False)
    pd.set_option("display.width", 160)
    print("Archive parcels with no jurisdiction (eligible land use):")
    print(unplaced.pivot(index="year", columns="theme", values="unplaced").to_string(), "\n")
    for theme, both in table.groupby("theme"):
        t = both[both["county_share"] >= MIN_COUNTY_SHARE]
        scaled = t[t["denominator_source"] == "parcels_scaled_acs"]
        roll = t[t["denominator_source"] == "parcels"]
        n = t["jurisdiction_geoid"].nunique()
        print(f"== {theme}: {n} jurisdictions with {MIN_ELIGIBLE}+ eligible lots, all in Franklin County")
        print(f"   roll year (2023) vs December 2023 archive: median gap {roll['gap_pct'].median():+.1f}%")
        by_year = scaled.groupby("year")["gap_pct"].describe()[["count", "50%", "min", "max"]]
        print("   scaled history minus real count, % of real, by year:")
        print(by_year.round(1).to_string(), "\n")
        print(growth(t, 2016, 2023).loc[theme].sort_values("real_growth_pct").to_string(), "\n")
        multi = both[both["county_share"] < MIN_COUNTY_SHARE]
        print("   jurisdictions partly outside Franklin County: approximate gap (archive count / share), %:")
        w = multi.pivot_table(index=["name", "county_share"], columns="year", values="gap_adj_pct")
        print(w.round(1).to_string(), "\n")


if __name__ == "__main__":
    main()
