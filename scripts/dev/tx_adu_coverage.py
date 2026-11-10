#!/usr/bin/env python3
"""TX ADU coverage audit (D-075 step 1, `reports/tx/adu-coverage-and-undercount.md` §1). Read-only.

    uv run python scripts/dev/tx_adu_coverage.py [--year 2024] [--covered 4805000,...]

Share of Texas's ADU-eligible lots (theme `adu`, current rule version) that sits in places whose permits flag
ADUs, summed over **non-overlapping units** with `lotline.model.scenarios.adu.non_overlapping` (a county
remainder counted from the ACS fallback still holds its local-only places' homes; a raw sum counts them
twice). Each jurisdiction takes its newest eligible-lot year <= `--year` (else its earliest later roll, as
`adu.places_from_store` does). Prints the totals and the 25 largest units by eligible lots.

Processed tables are read through `DataStore.read`; they are written after `holdout.apply` (TX has no
holdouts today). No model,
scenario or calibration is run.
"""

from __future__ import annotations

import argparse

import pandas as pd

from lotline.build import eligible as eligible_rule
from lotline.io import DataStore
from lotline.model.scenarios import adu

STATE = "TX"
# Places with a record-level permit source that flags ADUs (config/states/tx.yaml): Austin, San Antonio,
# Dallas, Fort Worth. Houston's summary file (checks.houston_permits) has no ADU field, so it is not covered.
FLAGGED = {
    "4805000": "austin_permits (R-102 class)",
    "4865000": "sa_permits (permit type)",
    "4819000": "dallas_permits (parser)",
    "4827000": "fw_permits (parser)",
}


def units(store: DataStore, year: int) -> pd.DataFrame:
    """Non-overlapping ADU scenario units with eligible lots from the newest year <= `year`."""
    e = store.read(STATE, "eligible_parcels")
    e = e[(e["theme"] == "adu") & (e["rule_version"] == eligible_rule.RULE_VERSION)]
    e = e.assign(after=e["year"] > year, gap=(e["year"] - year).abs())
    e = e.sort_values(["after", "gap"]).groupby("jurisdiction_geoid").first().reset_index()
    e = e.rename(columns={"jurisdiction_geoid": "geoid", "year": "parcels_year"})
    j = store.read(STATE, "jurisdictions")
    places = e.merge(
        j[["geoid", "name", "kind", "county_geoid", "in_bps", "pop_2020"]], on="geoid", how="left"
    )
    places = places[places["eligible_parcels"].fillna(0) > 0].reset_index(drop=True)
    return adu.non_overlapping(places, j, adu._county_shares(STATE, store, places))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--covered", default="", help="extra covered GEOIDs, comma-separated (new adapters)")
    a = ap.parse_args()
    covered = dict(FLAGGED)
    for g in filter(None, a.covered.split(",")):
        covered.setdefault(g, "new adapter")
    u = units(DataStore(), a.year)
    u["covered"] = u["geoid"].isin(covered)
    tot = u["eligible_parcels"].sum()
    raw = u["eligible_parcels_reported"].sum()
    cov = u.loc[u["covered"], "eligible_parcels"].sum()
    print(
        f"units {len(u)}; eligible lots non-overlapping {tot:,.0f} (raw sum {raw:,.0f}, "
        f"overlap removed {raw - tot:,.0f})"
    )
    print(f"covered {cov:,.0f} = {cov / tot:.1%}")
    for g, src in covered.items():
        r = u[u["geoid"] == g]
        if len(r):
            print(f"  {g} {r['name'].iat[0]}: {r['eligible_parcels'].iat[0]:,.0f} ({src})")
    print("\nsource mix (share of non-overlapping lots):")
    print((u.groupby("denominator_source")["eligible_parcels"].sum() / tot).round(3).to_string())
    top = u.sort_values("eligible_parcels", ascending=False).head(25)
    print("\n| # | Place | GEOID | Kind | Eligible lots | Year | Denominator | Covered |")
    print("|---:|---|---|---|---:|---:|---|---|")
    for i, r in enumerate(top.itertuples(), 1):
        print(
            f"| {i} | {r.name} | {r.geoid} | {r.kind} | {r.eligible_parcels:,.0f} | {r.parcels_year} | "
            f"{r.denominator_source} | {'yes: ' + covered[r.geoid] if r.covered else 'no'} |"
        )
    t25 = top["eligible_parcels"].sum()
    print(
        f"\ntop 25: {t25:,.0f} = {t25 / tot:.1%} of the state; covered among them "
        f"{top.loc[top['covered'], 'eligible_parcels'].sum() / t25:.1%}"
    )


if __name__ == "__main__":
    main()
