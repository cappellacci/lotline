#!/usr/bin/env python3
"""Coverage audit for `reports/oh/adu-coverage-and-undercount.md` §1: Ohio's eligible ADU lots in places with
ADU-flagged permits.

    uv run python scripts/dev/oh_adu_coverage.py [--origin 2024] [--json out.json]

Descriptive counts only (data thread): no engine, scenario or calibration run. Reads the processed, holdout-
filtered `eligible_parcels`, `jurisdictions` and `parcels` tables through `DataStore`.

- **Lots.** Theme `adu`, the current eligibility rule version, the newest year at or before `--origin` for
  each jurisdiction (as `lotline.model.scenarios.adu` picks it), made non-overlapping with
  `adu.non_overlapping` (a raw sum counts local-only places twice, inside their county's ACS remainder).
- **Covered** means an ADU-flagged permit source reaches the lot:
  - Columbus (`columbus_permits`, flags from the Auditor's permit descriptions) and Cincinnati
    (`cincy_permits`);
  - every other jurisdiction's **Franklin County part** (`franklin_permits`, the Auditor's permit file covers
    the whole county): a jurisdiction that reaches beyond Franklin is covered by the share of its
    single-family parcels inside Franklin (the processed `parcels` table);
  - the 12 Montgomery jurisdictions `montgomery_permits.covered_places` lists in `config/states/oh.yaml`
    (Montgomery-only places, so the whole place counts).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lotline.build import eligible as eligible_rule
from lotline.io import DataStore
from lotline.model.scenarios import adu

STATE = "OH"
FRANKLIN = "39049"
CITY_SOURCES = {"3918000": "columbus_permits", "3915000": "cincy_permits"}
# montgomery_permits.covered_places on 2026-09-30 (config/states/oh.yaml notes)
MONTGOMERY_COVERED = {
    "39113": "Montgomery County Unincorporated Area", "3921000": "Dayton", "3940040": "Kettering",
    "3913190": "Centerville", "3949434": "Miamisburg", "3977504": "Trotwood", "3978470": "Union",
    "3983090": "West Carrollton", "3979492": "Vandalia", "3952010": "Moraine", "3925396": "Englewood",
    "3909358": "Brookville",
}  # fmt: skip


def lots(store: DataStore, origin: int) -> pd.DataFrame:
    elig = store.read(STATE, "eligible_parcels")
    elig = elig[(elig["theme"] == "adu") & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    elig = elig.assign(after=elig["year"] > origin, gap=(elig["year"] - origin).abs())
    elig = elig.sort_values(["after", "gap"]).groupby("jurisdiction_geoid").first().reset_index()
    elig = elig.rename(columns={"jurisdiction_geoid": "geoid", "year": "parcels_year"})
    juris = store.read(STATE, "jurisdictions")
    places = elig.merge(juris[["geoid", "name", "kind", "county_geoid", "in_bps"]], on="geoid", how="left")
    places = places[places["eligible_parcels"].fillna(0) > 0].reset_index(drop=True)
    return adu.non_overlapping(places, juris, adu._county_shares(STATE, store, places))


def franklin_share(store: DataStore) -> pd.Series:
    """Share of each jurisdiction's SF_DETACHED parcels that lie in Franklin County (only those reaching it)."""
    p = store.read(STATE, "parcels")
    houses = p.loc[p["land_use_std"] == "SF_DETACHED", ["jurisdiction_geoid", "county_geoid"]]
    reach = houses.loc[houses["county_geoid"] == FRANKLIN, "jurisdiction_geoid"].unique()
    houses = houses[houses["jurisdiction_geoid"].isin(reach)]
    return (houses["county_geoid"] == FRANKLIN).groupby(houses["jurisdiction_geoid"]).mean()


def coverage(places: pd.DataFrame, share: pd.Series) -> pd.DataFrame:
    out = places[["geoid", "name", "kind", "county_geoid", "parcels_year", "eligible_parcels"]].copy()
    out["covered_share"] = out["geoid"].map(share).fillna(0.0)
    out.loc[out["geoid"].isin(MONTGOMERY_COVERED), "covered_share"] = 1.0
    out.loc[out["geoid"].isin(CITY_SOURCES), "covered_share"] = 1.0
    out["source"] = ""
    out.loc[out["covered_share"] > 0, "source"] = "franklin_permits"
    out.loc[out["geoid"].isin(MONTGOMERY_COVERED), "source"] = "montgomery_permits"
    for g, s in CITY_SOURCES.items():
        out.loc[out["geoid"] == g, "source"] = s
    out["covered_lots"] = out["eligible_parcels"] * out["covered_share"]
    return out.sort_values("eligible_parcels", ascending=False).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--origin", type=int, default=2024)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    store = DataStore()
    cov = coverage(lots(store, args.origin), franklin_share(store))
    total, covered = float(cov["eligible_parcels"].sum()), float(cov["covered_lots"].sum())
    by_source = cov.groupby("source")["covered_lots"].sum().drop("", errors="ignore")
    print(f"eligible ADU lots (non-overlapping): {total:,.0f}; covered {covered:,.0f} ({covered / total:.1%})")
    print(by_source.round(0).to_string())
    top = cov.head(25)
    print(top[["name", "kind", "parcels_year", "eligible_parcels", "covered_share", "source"]].to_string())
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "origin": args.origin,
                    "total_lots": round(total),
                    "covered_lots": round(covered),
                    "by_source": {k: round(v) for k, v in by_source.items()},
                    "top25": top[["geoid", "name", "eligible_parcels", "covered_share", "source"]].to_dict(
                        "records"
                    ),
                },
                indent=1,
                default=str,
            )
        )


if __name__ == "__main__":
    main()
