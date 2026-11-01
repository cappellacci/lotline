# ruff: noqa: E501  (coding data: long source URLs and notes)
"""Carrollton ADU rule from Ben's lookup (2026-11-01) -> config/reforms/tx.csv and the ADU tracker.

Run from the repo root after `tx_fee_rule_2026_10_30.py`:
`uv run python scripts/dev/tx_ben_lookups_2026_11_01.py`. Rerunning it is safe.

Ben's agent read Carrollton's Comprehensive Zoning Ordinance (April 2026 and 2020 editions) and its amendment
register. An accessory building may be a dwelling only on a lot with at least 20,000 sq ft of buildable area, in
the SF-detached, SF-attached/townhouse and D districts. The provision names no SUP, so with a building permit
it is coded by right. The rule is attributed to Ord. 3421, ratified 2011-01-11. The effective date and the rule
before 2011 are unresolved, and so is rental. The "guest house" definition (Ord. 1947) bars renting a guest
house, but the code doesn't say whether every accessory dwelling is one.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "reforms" / "tx.csv"
TRACKER = ROOT / "docs" / "research" / "ordinances" / "tx-adu-lookups-todo.csv"
DAY = "2026-11-01"
BEN = f"From Ben's lookup ({DAY}, in chat)"

ROW = {
    "reform_id": "TX-4813024-adu-2011",
    "state": "TX",
    "jurisdiction_geoid": "4813024",
    "theme": "adu",
    "component": "Comprehensive Zoning Ordinance Arts. 7-9 accessory buildings (Ord. 3421): an accessory building may be used as a dwelling unit only on a lot with at least 20,000 sq ft of buildable area (floodplain and easements excluded); no separate utility meter; number of accessory buildings limited; no SUP named",
    "status": "in_force",
    "adoption_date": "2011-01-11",
    "effective_date": "2011-01-11",
    "by_right": "True",
    "min_lot_sqft": "20000",
    "adu_detached_allowed": "True",
    "parking": "no ADU-specific rule; Article 24 directs the City Manager to use the most similar listed use (two spaces per single-family home)",
    "coverage": "SF-detached, SF-attached/townhouse and D districts, lots with at least 20,000 sq ft of buildable area",
    "source_url": "https://www.cityofcarrollton.com/home/showpublisheddocument/40713/639150626674770000; https://www.cityofcarrollton.com/home/showpublisheddocument/20997/639129044492400000; https://www.cityofcarrollton.com/home/showpublisheddocument/33615/639009729505030000",
    "source_section": "Comprehensive Zoning Ordinance Articles 7, 8 and 9 (accessory buildings); CZO amendment register (Ord. 3421)",
    "source_quote": "Accessory buildings shall not be used as a dwelling unit unless the lot or parcel contains at least 20,000 square feet of buildable area.",
    "coder": "ben",
    "coder_agreement": "single_coder",
    "coding_notes": f"{BEN}: the current CZO (April 2026) and the 2020 CZO carry the 20,000 sq ft buildable-area rule in the accessory-building provisions of Articles 7, 8 and 9; the amendment register attributes those provisions to Ord. 3421, ratified 2011-01-11 (adoption and effective date not in the register, so both are coded as the ratification date). No later amendment changes it; Ord. 3891 (2018-12-11) concerns accessory-building size and materials. By right: the provision names no SUP; a building permit is needed for buildings over 120 sq ft. min_lot_sqft = 20,000 is buildable area, so D-021's lot-size share (measured on total lot area) is an upper bound. No maximum unit size (adu_max_sqft blank); height 15 ft per city guidance. Rental and owner occupancy left blank: the guest-house definition (Ord. 1947, 1993-10-19) bars renting a guest house, and the code does not say whether every accessory dwelling is a guest house. Article 7 keeps one principal dwelling per lot of record. The rule before 2011 is unresolved, so there is no earlier row (D-022 fills 2010)."
    " FLAG for second coder: the effective date of Ord. 3421, whether a qualifying accessory dwelling may be rented, and the pre-2011 rule.",
}
TRACKER_NOTE = "Ben 2026-11-01: coded TX-4813024-adu-2011 (Ord. 3421, ratified 2011-01-11; by right on lots with 20,000 sq ft of buildable area). Open: the effective date, rental, the pre-2011 rule."


def main() -> None:
    with PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)
    assert set(ROW) <= set(cols), set(ROW) - set(cols)
    added = 0
    if ROW["reform_id"] not in {r["reform_id"] for r in rows}:
        rows.append({c: ROW.get(c, "") for c in cols})
        added = 1
    with PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with TRACKER.open(newline="") as f:
        reader = csv.DictReader(f)
        tcols, trows = reader.fieldnames, list(reader)
    for t in trows:
        if t["place"] == "Carrollton":
            t["status"] = "coded"
            if TRACKER_NOTE not in t["notes"]:
                t["notes"] = t["notes"].rstrip() + " | " + TRACKER_NOTE
    with TRACKER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=tcols, lineterminator="\n")
        w.writeheader()
        w.writerows(trows)
    print(f"{added} row added -> {PATH}")


if __name__ == "__main__":
    main()
