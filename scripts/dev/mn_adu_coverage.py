"""Coverage audit behind `reports/mn/adu-coverage-and-undercount.md` §1: what share of Minnesota's
ADU-eligible lots sit in places whose permits carry an ADU flag.

    uv run python scripts/dev/mn_adu_coverage.py [--year 2024]

Descriptive counts only (data thread): no engine, scenario or calibration run. Reads the processed
`eligible_parcels` (theme `adu`, current rule version), `jurisdictions` and `permits` tables. Eligible lots
are summed over non-overlapping units with `lotline.model.scenarios.adu.non_overlapping` (a raw sum counts the
local-only places twice, once on their own and once in their county's ACS-fallback remainder), using each
jurisdiction's newest roll at or before `--year` (the earliest later one where none is earlier), as the ADU
scenario does. Permits are read through `holdout.apply`; a jurisdiction is **covered** when a permit source
that flags ADUs (Met Council's `ADU` housing type, Minneapolis CCS's scope-text parser) holds record-level
permits for it. Writes aggregates to `reports/mn/adu-coverage.json`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lotline.build import eligible as eligible_rule
from lotline.io import DataStore
from lotline.model.scenarios import adu
from lotline.validation import holdout

STATE = "MN"
OUT_JSON = Path(__file__).resolve().parents[2] / "reports" / "mn" / "adu-coverage.json"
# Sources whose permit rows can carry building_type_std == "ADU" (a field or a parser).
FLAG_SOURCES = {
    "metc_residential_permits": "Met Council (field)",
    "mpls_ccs_permits": "Minneapolis CCS (parser)",
}


def eligible_units(store: DataStore, year: int) -> pd.DataFrame:
    elig = store.read(STATE, "eligible_parcels")
    elig = elig[(elig["theme"] == "adu") & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    elig = elig.assign(after=elig["year"] > year, gap=(elig["year"] - year).abs())
    elig = elig.sort_values(["after", "gap"]).groupby("jurisdiction_geoid").first().reset_index()
    elig = elig.rename(columns={"jurisdiction_geoid": "geoid", "year": "parcels_year"}).drop(columns="gap")
    juris = store.read(STATE, "jurisdictions")
    places = elig.merge(juris[["geoid", "name", "kind", "county_geoid", "in_bps"]], on="geoid", how="left")
    places = places[places["eligible_parcels"].fillna(0) > 0].reset_index(drop=True)
    return adu.non_overlapping(places, juris, adu._county_shares(STATE, store, places))


def coverage(store: DataStore) -> pd.DataFrame:
    """Per jurisdiction: which flagging sources hold its permits, ADU-flagged permits and years."""
    p = store.read(STATE, "permits")
    p = holdout.apply(p, STATE, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year")
    p = p[p["source"].isin(FLAG_SOURCES)]
    p = p.assign(is_adu=p["building_type_std"] == "ADU")
    g = p.groupby("jurisdiction_geoid")
    return pd.DataFrame(
        {
            "sources": g["source"].agg(lambda s: "; ".join(sorted(FLAG_SOURCES[x] for x in set(s)))),
            "permits": g.size(),
            "adu_permits": g["is_adu"].sum(),
            "first_year": g["issue_year"].min(),
            "last_year": g["issue_year"].max(),
        }
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024)
    args = ap.parse_args()
    store = DataStore()
    units = eligible_units(store, args.year)
    cov = coverage(store)
    units = units.merge(cov, left_on="geoid", right_index=True, how="left")
    units["covered"] = units["sources"].notna()
    total = float(units["eligible_parcels"].sum())
    raw = float(units["eligible_parcels_reported"].sum())
    covered = float(units.loc[units["covered"], "eligible_parcels"].sum())
    with_adu = float(units.loc[units["adu_permits"].fillna(0) > 0, "eligible_parcels"].sum())
    top = units.sort_values("eligible_parcels", ascending=False).head(25)
    by_kind = units.groupby(["kind", "covered"])["eligible_parcels"].sum().unstack(fill_value=0)
    out = {
        "year": args.year,
        "rule_version": eligible_rule.RULE_VERSION,
        "units": int(len(units)),
        "eligible_lots_non_overlapping": total,
        "eligible_lots_raw_sum": raw,
        "covered_lots": covered,
        "covered_share": covered / total,
        "covered_units": int(units["covered"].sum()),
        "lots_in_places_with_an_adu_permit": with_adu,
        "share_in_places_with_an_adu_permit": with_adu / total,
        "places_with_an_adu_permit": int((units["adu_permits"].fillna(0) > 0).sum()),
        "by_kind": {k: {str(c): float(v) for c, v in r.items()} for k, r in by_kind.iterrows()},
        "top25": [
            {
                "geoid": r.geoid,
                "name": r["name"],
                "kind": r.kind,
                "eligible_lots": float(r.eligible_parcels),
                "parcels_year": int(r.parcels_year),
                "denominator_source": r.denominator_source,
                "covered": bool(r.covered),
                "sources": r.sources if r.covered else None,
                "adu_permits": int(r.adu_permits) if r.covered else None,
                "years": f"{int(r.first_year)}-{int(r.last_year)}" if r.covered else None,
            }
            for _, r in top.iterrows()
        ],
        "top_uncovered": [
            {"geoid": r.geoid, "name": r["name"], "eligible_lots": float(r.eligible_parcels)}
            for _, r in units[~units["covered"]]
            .sort_values("eligible_parcels", ascending=False)
            .head(15)
            .iterrows()
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
