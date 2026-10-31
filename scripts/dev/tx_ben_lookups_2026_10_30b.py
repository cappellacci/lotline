# ruff: noqa: E501  (coding data: long source URLs and notes)
"""Ben's second batch of lookups (2026-10-30, evening) -> config/reforms/tx.csv and the lookup trackers.

Run from the repo root after `tx_second_coder_2026_10_30.py`:
`uv run python scripts/dev/tx_ben_lookups_2026_10_30b.py`. Rerunning it is safe.

Ben's agent answered the ten questions of 2026-10-30, with an updated workbook. Edits are field by field, each
with a dated note. Two change rows:
- **League City** `TX-4841980-adu-2026` goes back to `in_force` and becomes by right. Ord. 2026-10 was
  approved 2026-05-26 and takes effect on passage. The Planning Director approves an ADU that shares the main
  home's address and meters, with no SUP. This supersedes the review's "first reading only" reading, which set
  it to pending earlier the same day.
- **Tyler** `TX-4874144-adu-2011` is renamed `TX-4874144-adu-2010` and dated 2010-01-01. The R-1C purpose clause
  names garage apartments by 2010, so the rule was in force at the start of the window, and its first date is
  unknown. Owner occupancy: none found.

The other findings add notes only, or update the trackers. Fees (same batch): the SAWS 2014-schedule
component rows get a note confirming the totals they sum to for plats of June 2015 to May 2019. That is a note,
not total rows, which would double-count. Houston gets a row for the pre-2021 indexed water rate ($790.55).
Fort Worth, Dallas and Austin go in the fee tracker.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "reforms" / "tx.csv"
ORD = ROOT / "docs" / "research" / "ordinances"
DAY = "2026-10-30"
BEN = f"Ben's lookup ({DAY}, second batch)"
RENAMES = {"TX-4874144-adu-2011": "TX-4874144-adu-2010"}

# reform_id (name before any rename) -> (fields, note)
EDITS: dict[str, tuple[dict, str]] = {
    "TX-4841980-adu-2026": (
        {"status": "in_force", "by_right": "True"},
        f"{BEN}: under Ord. 2026-10 the Planning Director may approve an ADU in a single-family district if it shares the primary home's address and utility meters; that route needs no SUP, so by_right = True. Approved 2026-05-26, effective upon passage; removed the former family-occupancy requirement (https://leaguecity.legistar.com/LegislationDetail.aspx?GUID=D0E8785A-A445-4A88-BC81-D52BB20EBBDD&ID=8033447&Options=&Search=). Back to in_force from the review's pending. When the earlier family-only rule first took effect is unresolved (it is in the 2023 UDC).",
    ),
    "TX-4874144-adu-2011": (
        {"adoption_date": "", "effective_date": "2010-01-01", "owner_occ": "False"},
        f"{BEN}: garage apartments are allowed in R-1C and R-1D in the 2017-printed historical and 2024 code tables, and the R-1C purpose clause names garage apartments by 2010, so the rule is dated 2010-01-01 (in force at the start of the window; whether it came with the 2008 code or a later ordinance is unresolved). No owner-on-site condition and no rental ban found; general parking rules apply (https://www.cityoftyler.org/home/showpublisheddocument/14161/638633748097600000; https://www.cityoftyler.org/home/showpublisheddocument/2276/637112939022400000). Renamed from TX-4874144-adu-2011 (2011-06-08 was a later ordinance date).",
    ),
    "TX-4841464-missing_middle-2010": (
        {
            "coverage": "Single-family districts RS, R-1, R-1A, R-1B and R-1-MH (duplex, three-family and four-family homes prohibited in each); duplex lot standards apply in R-2, R-O, AE, B-1, B-3, CBD"
        },
        f"{BEN}: LDC §24.63.2 leaves duplex, three-family and four-family blank (prohibited, not SUP) in R-1A, R-1B and R-1-MH; Ord. 2025-O-004 changed the duplex definition and dimensional standards, not those cells (code history: 2025-01-28; effective date unverified). Sources: https://www.cityoflaredo.com/home/showpublisheddocument/17795/638721250398470000, https://www.cityoflaredo.com/home/showpublisheddocument/18303/638771903294200000.",
    ),
    "TX-4819972-missing_middle-2010": (
        {},
        f"{BEN}: the R4 duplex SUP was already in the 2019 Development Code's Table 5.2-A, so DCA25-0001a (2026-01-13, a case ID; ordinance number and effective date not found) did not create it. Whether it predates the 2019 code is still unresolved.",
    ),
    "TX-4845744-adu-2022": (
        {},
        f"{BEN}: the 2022 and 2026-03 code editions require a conforming lot, not a universal 12,000 sq ft minimum (12,000 is one district's lot size), so min_lot_sqft stays blank. No broader district expansion found in those editions; the city guide supports renting; no ordinance number found for a rental authorization.",
    ),
    "TX-4839148-adu-2026": (
        {},
        f"{BEN}: a final ordinance number, adoption and effective date could not be confirmed: the city page still calls the overlay proposed, and the city-hosted signed copy has no number and conflicting effective-date language. The row stays in_force on the reported 4-1 vote. No owner-occupancy rule or ADU parking count in the draft text.",
    ),
    "TX-4842508-adu-2026": (
        {},
        f"{BEN}: the 2026-09-21 meeting record and recap report approval, but 26-4739 is the agenda-item number, not an ordinance number; no signed ordinance or effective date found, and the code compilation does not include it yet. The 2022 UDC is the prior baseline.",
    ),
    "TX-4822660-adu-2022": (
        {},
        f"{BEN}: the 2022 baseline §2.206(E) is confirmed: one ADU in residential districts accessory to a single-family detached home, owner in either unit, shared meter and driveway, one parking space. The 2026-10-06 amendments are not posted; the pre-2022 rule is unresolved.",
    ),
}

FEES = ROOT / "config" / "fees" / "tx.csv"
SAWS_TOTALS = (
    f"{BEN}: for plats recorded June 2015 through May 2019 the 5/8-inch water totals per EDU (flow + system "
    "development + water supply) were $4,597 low, $4,777 middle and $4,861 high elevation, the sums of this "
    "schedule's components; wastewater varies by service basin. The 2019 transition and any schedule changes in "
    "between still need confirmation."
)
# (jurisdiction, fee_type prefix) -> note
FEE_NOTES: dict[tuple[str, str], str] = {
    ("4865000", "SAWS water flow fee (2014 schedule)"): SAWS_TOTALS,
    ("4865000", "SAWS water system development fee"): SAWS_TOTALS,
    ("4865000", "SAWS water supply fee (2014 schedule, step 2)"): SAWS_TOTALS,
}
FEE_ROWS: list[dict] = [
    {
        "state": "TX",
        "jurisdiction_geoid": "4835000",
        "year": "2020",
        "fee_component": "water_sewer",
        "fee_type": "Water impact fee, indexed rate before the 2021 update",
        "building_type_std": "SFD",
        "basis": "per_lue",
        "amount_usd": "790.55",
        "amount_per_unit_usd": "790.55",
        "dollar_year": "2020",
        "payment_timing": "collected when the building permit issues, or at water/wastewater connection if no permit",
        "source": "https://www.houstontx.gov/citysec/HPW/impactfeereport.pdf",
        "source_section": "2020 Cost of Service Study, history of adopted fees",
        "notes": f"{BEN}: the verified rate before the 2021 change was $790.55 water per service unit (wastewater $1,199.11, already coded at its 2010 adoption). 1 service unit per single-family home up to 3,000 sq ft, so amount_per_unit_usd = amount. Coded as year 2020, the last full year before collection of the 2021 rates began on 2021-07-01; when indexing reached $790.55 is not known, so effective_date is blank and the exact annual indexed rates for 2011-2020 remain unresolved. FLAG for second coder: the year the indexed rate took effect.",
    },
]
FEE_TRACKERS = {
    "Dallas": "Ben 2026-10-30 (second batch): official schedules list connection and inspection charges, no impact fee; no official statement that none applies. Still unresolved.",
    "San Antonio (SAWS)": "Ben 2026-10-30 (second batch): plats of June 2015 to May 2019 paid $4,597 / $4,777 / $4,861 (low / middle / high) per EDU for water, the sums of the coded 2014-schedule components. Open: the 2019 transition and changes in between.",
    "Fort Worth": "Ben 2026-10-30 (second batch): rates change by plat and permit date, so a single fee per fiscal year would mislead; the historical schedule is incomplete.",
    "Houston": "Ben 2026-10-30 (second batch): $790.55 water / $1,199.11 wastewater before the 2021 change (water row added); then $1,618.11 / $1,621.63 from 2021-07-01. Open: the annual indexed rates in between.",
    "Austin": "Ben 2026-10-30 (second batch): the city's page lists the single-family parkland fees without a fiscal year. Still unresolved.",
}

TRACKERS: dict[tuple[str, str], tuple[str, str]] = {
    ("adu", "Pasadena"): (
        "open",
        "Ben 2026-10-30 (second batch): no general ADU provision found; whether a detached second home is allowed stays unresolved (parcel-specific).",
    ),
    ("mm", "Pasadena"): (
        "open",
        "Ben 2026-10-30 (second batch): §9-76 recognizes a duplex as a residential building (Ord. 1833, 1966-07-05; amended 1972, 1974, 1996, 1997), but no zoning does not establish it can go on any lot; 3+ units need multifamily site-plan review. Stays pending.",
    ),
    ("mm", "Laredo"): (
        "coded",
        "Ben 2026-10-30 (second batch): R-1A, R-1B, R-1-MH prohibit duplex, three- and four-family (§24.63.2); TX-4841464-missing_middle-2010 now covers them.",
    ),
    ("adu", "McKinney"): (
        "coded",
        "Ben 2026-10-30 (second batch): no universal 12,000 sq ft minimum (conforming lot); rental supported by the city guide. Open: an ordinance number for any widening.",
    ),
    ("adu", "League City"): (
        "coded",
        "Ben 2026-10-30 (second batch): Ord. 2026-10 (2026-05-26, effective on passage) lets the Planning Director approve; coded by right and in force. Open: when the family-only rule began.",
    ),
    ("adu", "Carrollton"): (
        "partial",
        "Ben 2026-10-30 (second batch): the 20,000 sq ft buildable-area rule applies in SF-detached, SF-attached/townhouse and D districts; separate meter prohibited; no rental or owner-occupancy rule, no size cap found. Not coded: the enacting ordinance and date are unresolved (Ord. 3891, 2018-12-11, covers a different subsection).",
    ),
    ("adu", "Tyler"): (
        "coded",
        "Ben 2026-10-30 (second batch): garage apartments in R-1C, R-1D by 2010, no owner-occupancy rule or rental ban; row renamed TX-4874144-adu-2010.",
    ),
    ("adu", "Edinburg"): (
        "partial",
        "Ben 2026-10-30 (second batch): 2022 baseline confirmed. Open: the 2026-10-06 amendments (not posted) and the pre-2022 rule.",
    ),
    ("adu", "Killeen"): (
        "coded",
        "Ben 2026-10-30 (second batch): ordinance number and dates still unconfirmed (city page says proposed); row kept on the reported vote.",
    ),
    ("adu", "Lewisville"): (
        "coded",
        "Ben 2026-10-30 (second batch): approval meeting-reported only (26-4739 is an agenda number); ordinance number and effective date unresolved.",
    ),
}


def read(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames), list(r)


def write(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    cols, rows = read(PATH)
    by_id = {r["reform_id"]: r for r in rows}
    changed = 0
    for rid, (fields, note) in EDITS.items():
        r = by_id[RENAMES[rid]] if RENAMES.get(rid) in by_id else by_id[rid]
        if note in r["coding_notes"]:
            continue
        r.update(fields)
        r["coding_notes"] = r["coding_notes"].rstrip() + f" Updated {DAY}: " + note
        changed += 1
    present = {r["reform_id"] for r in rows}
    renames = {a: b for a, b in RENAMES.items() if b not in present}  # done once; a reused id stays
    for r in rows:
        r["reform_id"] = renames.get(r["reform_id"], r["reform_id"])
        r["supersedes"] = renames.get(r["supersedes"], r["supersedes"])
    write(PATH, cols, rows)
    done = 0
    for table in ("adu", "mm"):
        path = ORD / f"tx-{table}-lookups-todo.csv"
        tcols, trows = read(path)
        for t in trows:
            if (table, t["place"]) in TRACKERS:
                status, note = TRACKERS[(table, t["place"])]
                t["status"] = status
                if note not in t["notes"]:
                    t["notes"] = t["notes"].rstrip() + " | " + note
                done += 1
        write(path, tcols, trows)
    fcols, frows = read(FEES)
    have = {(f["jurisdiction_geoid"], f["fee_type"]) for f in frows}
    for f in FEE_ROWS:
        assert set(f) <= set(fcols), set(f) - set(fcols)
        if (f["jurisdiction_geoid"], f["fee_type"]) not in have:
            frows.append({c: f.get(c, "") for c in fcols})
    for f in frows:
        for (geoid, prefix), note in FEE_NOTES.items():
            if (
                f["jurisdiction_geoid"] == geoid
                and f["fee_type"].startswith(prefix)
                and note not in f["notes"]
            ):
                f["notes"] = f["notes"].rstrip() + f" Updated {DAY}: " + note
    write(FEES, fcols, frows)
    path = ORD / "tx-fee-lookups-todo.csv"
    tcols, trows = read(path)
    for t in trows:
        note = FEE_TRACKERS.get(t["place"])
        if note and note not in t["notes"]:
            t["notes"] = t["notes"].rstrip() + " | " + note
    write(path, tcols, trows)
    print(f"{changed} rows updated, {len(RENAMES)} renamed, {done} tracker rows -> {PATH}")


if __name__ == "__main__":
    main()
