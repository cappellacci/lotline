"""Counts behind §1 of `reports/or/adu-coverage-and-undercount.md`: where Oregon's ADU-eligible lots sit.

    uv run python scripts/dev/or_adu_coverage.py

Descriptive counts only (data thread): no engine, scenario or calibration run. Eligible lots (theme `adu`,
current rule version) are taken the way `adu.places_from_store` takes them (newest count at or before the
origin year, 2026 here: RLIS parcels for the 27 Metro jurisdictions, the 2024 ACS fallback elsewhere) and
made non-overlapping with `adu.non_overlapping`, so county remainders don't count local-only places twice.
ADU-flagged permits per year (Portland, Bend) are read through `holdout.apply`. Prints markdown tables.
"""

from __future__ import annotations

from lotline.io import DataStore
from lotline.model.scenarios import adu
from lotline.validation import holdout

STATE = "OR"
ORIGIN = 2026
FLAGGED = {"4159000": "portland_permits", "4105800": "bend_permits"}


def main() -> None:
    store = DataStore()
    places = adu.places_from_store(STATE, store, ORIGIN)[
        [
            "geoid",
            "name",
            "kind",
            "parcels_year",
            "denominator_source",
            "eligible_parcels_reported",
            "eligible_parcels",
        ]
    ]
    total = places["eligible_parcels"].sum()
    raw = places["eligible_parcels_reported"].sum()
    places["covered"] = places["geoid"].isin(FLAGGED)
    cov = places.loc[places["covered"], "eligible_parcels"].sum()
    print(f"jurisdictions {len(places)}; eligible lots non-overlapping {total:,.0f} (raw sum {raw:,.0f})")
    print(f"covered (Portland, Bend) {cov:,.0f} = {cov / total:.1%}")
    by_src = places.groupby("denominator_source")["eligible_parcels"].agg(["size", "sum"])
    print(by_src.to_string())
    top = places.sort_values("eligible_parcels", ascending=False).head(25).reset_index(drop=True)
    top["share"] = top["eligible_parcels"] / total
    top["cum"] = top["share"].cumsum()
    print("\n| # | Place | GEOID | Eligible lots | Share | Cumulative | Lots from | ADU-flagged permits? |")
    print("|---:|---|---|---:|---:|---:|---|---|")
    for i, r in top.iterrows():
        src = f"{r.denominator_source} {r.parcels_year}"
        print(
            f"| {i + 1} | {r['name']} | {r.geoid} | {r.eligible_parcels:,.0f} | {r.share:.1%} | {r.cum:.1%} |"
            f" {src} |"
            f" {'yes' if r.covered else 'no'} |"
        )
    # ADU-flagged permits by year in the two covered places
    permits = store.read(STATE, "permits")
    permits = (
        holdout.apply(permits, STATE, geoid_col="jurisdiction_geoid", date_col="issue_date")
        if "issue_date" in permits
        else permits
    )
    flagged = permits[permits["adu_type"].notna() & permits["jurisdiction_geoid"].isin(FLAGGED)]
    counts = flagged.groupby(["jurisdiction_geoid", "issue_year"]).size().unstack(0).fillna(0).astype(int)
    lots = places.set_index("geoid")["eligible_parcels"]
    print("\n| Year | Portland | per 1,000 lots | Bend | per 1,000 lots |")
    print("|---|---:|---:|---:|---:|")
    for y, r in counts.loc[2016:].iterrows():
        p, b = r.get("4159000", 0), r.get("4105800", 0)
        print(f"| {y} | {p} | {p / lots['4159000'] * 1000:.2f} | {b} | {b / lots['4105800'] * 1000:.2f} |")


if __name__ == "__main__":
    main()
