# ruff: noqa: E501  (coding data: long notes)
"""Ben's rule for fees that vary by area or plat date (2026-10-30) -> config/fees/tx.csv.

Run from the repo root after `tx_ben_lookups_2026_10_30b.py`:
`uv run python scripts/dev/tx_fee_rule_2026_10_30.py`. Rerunning it is safe.

The rule (Ben, 2026-10-30; `config/fees/README.md`): when a fee's amount depends on the area, basin, density
tier or plat date of the lot, only one row of the group stands for a typical new home. Only that row carries
`amount_per_unit_usd`. The other rows keep their schedule amount with `amount_per_unit_usd` blank, and the
group's low and high are written in the central row's notes as the range.
- **Areas, basins and tiers:** the central row is the median one. With an even count, the central value is
  the median of the amounts, carried by the row nearest it; on a tie, the lower one.
- **Plat-date groups:** the central row is the newest group, because most new homes go on recently platted
  lots. The older groups are the low end.

`lotline.model.scenarios.fees.local_fees` sums `amount_per_unit_usd`, so this sets the central fee per home.
Using the range needs an engine change, raised with WS-CORE as a contract-change issue.
"""

import csv
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEES = ROOT / "config" / "fees" / "tx.csv"
DAY = "2026-10-30"
TAG = f" Fee rule {DAY} (Ben: median area / newest plat cohort is central, the rest is the range):"

# group name -> (jurisdiction, year, fee_type prefix, kind); kind "median" or "newest"
GROUPS = {
    "SAWS water, FY2027, by elevation area": (
        "4865000",
        "2026",
        "SAWS water impact fee (flow + system development + water supply)",
        "median",
    ),
    "SAWS wastewater, FY2027, by service basin": (
        "4865000",
        "2026",
        "SAWS wastewater impact fee (collection + treatment)",
        "median",
    ),
    "Austin parkland fee in lieu, by density tier": (
        "4805000",
        "2026",
        "Parkland dedication fee in lieu, single-family",
        "median",
    ),
    "Austin water impact fee, by plat date": ("4805000", "2023", "Water impact fee, lots platted", "newest"),
    "Austin wastewater impact fee, by plat date": (
        "4805000",
        "2023",
        "Wastewater impact fee, lots platted",
        "newest",
    ),
}
# plat-date groups: fee_type substring of the newest cohort
NEWEST = {
    "Austin water impact fee, by plat date": "lots platted after 2023-10-01",
    "Austin wastewater impact fee, by plat date": "lots platted after 2023-10-01",
}
# Fort Worth: the 2025 and 2026 collection rows are the newest plat cohort (plats on/after 2017-04-01); the
# 2009-2012 and 2013-2017 tables are the older cohorts (lots platted before 2017-04-01 pay the fee set at
# recordation), so the low end is the 2013-2017 total
FW = {
    "rows": (
        "Water impact fee, 5/8 x 3/4-inch meter, collected from",
        "Wastewater impact fee, 5/8 x 3/4-inch meter, collected from",
    ),
    "note": "Central: the newest plat cohort (plats recorded on or after 2017-04-01 pay the collection-date rate), 1 service unit for a 5/8 x 3/4-inch meter, so amount_per_unit_usd = amount. Range: the low end is the older cohort, lots platted 2013-2017 ($469 water + $452 wastewater = $921 a home; 2009-2012: $1,052); the high end is this row.",
}


def num(x: str) -> float:
    return float(x) if x not in ("", None) else float("nan")


def main() -> None:
    with FEES.open(newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)
    changed = 0
    for name, (geoid, year, prefix, kind) in GROUPS.items():
        group = [
            r
            for r in rows
            if r["jurisdiction_geoid"] == geoid and r["year"] == year and r["fee_type"].startswith(prefix)
        ]
        assert len(group) >= 2, name
        amounts = [num(r["amount_usd"]) for r in group]
        if kind == "median":
            mid = statistics.median(amounts)
            central = min(group, key=lambda r: (abs(num(r["amount_usd"]) - mid), num(r["amount_usd"])))
            why = f"the median of {len(group)} rows (${mid:,.2f})" + (
                "" if mid == num(central["amount_usd"]) else ", carried by the nearest row"
            )
        else:
            central = next(r for r in group if NEWEST[name] in r["fee_type"])
            why = "the newest plat cohort"
        lo, hi = min(amounts), max(amounts)
        for r in group:
            if TAG in r["notes"]:
                continue
            is_central = r is central
            r["amount_per_unit_usd"] = r["amount_usd"] if is_central else ""
            role = (
                f"this row is central ({why}); range ${lo:,.2f} to ${hi:,.2f} across the {name} rows."
                if is_central
                else f"not central ({name}: the central row is '{central['fee_type']}'), so amount_per_unit_usd is blank; this amount is part of the range ${lo:,.2f} to ${hi:,.2f}."
            )
            r["notes"] = r["notes"].rstrip() + TAG + " " + role
            changed += 1
    for r in rows:
        if (
            r["jurisdiction_geoid"] == "4827000"
            and r["fee_type"].startswith(FW["rows"])
            and TAG not in r["notes"]
        ):
            r["amount_per_unit_usd"] = r["amount_usd"]
            r["notes"] = r["notes"].rstrip() + TAG + " " + FW["note"]
            changed += 1
    with FEES.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{changed} fee rows set by the rule -> {FEES}")


if __name__ == "__main__":
    main()
