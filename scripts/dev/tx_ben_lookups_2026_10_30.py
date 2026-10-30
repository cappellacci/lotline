# ruff: noqa: E501  (coding data: long source URLs and notes)
"""Texas rule rows from Ben's own lookups (2026-10-30) -> config/reforms/tx.csv and the lookup trackers.

Run from the repo root after `tx_corrections_2026_10_30.py`:
`uv run python scripts/dev/tx_ben_lookups_2026_10_30.py`. Rerunning it is safe.

Ben answered the open items in chat on 2026-10-30. There were seven ADU and code-history questions and a table
of eight missing-middle lookups. Facts are his unless a note says otherwise. Two terms are read from the local
PDFs: Killeen's overlay terms (`Killeen_North-Killeen-Overlay_2026-10-20.pdf`) and Lewisville's districts (the
row coded earlier).

Conventions follow `tx_adu_rows.py` and `tx_rules_21_40.py`:
- New rows have new ids.
- `EDITS` change rows coded earlier field by field, each with a dated note.
- A missing-middle rule whose start date wasn't researched is dated 2010-01-01 (the start of the window) and
  flagged for a second coder.

Two judgement calls:
- **Killeen's overlay** row leaves `min_lot_sqft` blank and names the overlay in `coverage`. A lot minimum would
  make D-021 measure coverage on every Killeen parcel. Leaving it blank means the "only inside" area rule
  applies instead.
- **McKinney's 2022 row** stays a rentable ADU. Ben: the 2022 UDC "did not explicitly ban renting", though it
  framed the unit for family, multigenerational or guest use.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "reforms" / "tx.csv"
ORD = ROOT / "docs" / "research" / "ordinances"
DAY = "2026-10-30"
BEN = f"From Ben's own lookup ({DAY}, in chat)"
FLOOR = "2010-01-01"
FLAG = " FLAG for second coder: "


def row(**kw) -> dict:
    base = {"state": "TX", "status": "in_force", "coder": "ben", "coder_agreement": "single_coder"}
    return base | {k: ("" if v is None else str(v)) for k, v in kw.items()}


def mm_no(geoid: str, place: str, coverage: str, url: str, note: str) -> dict:
    return row(
        reform_id=f"TX-{geoid}-missing_middle-2010",
        jurisdiction_geoid=geoid,
        theme="missing_middle",
        component=f"{place}: one dwelling per lot in the single-family districts (no duplex or 3-4 unit building)",
        effective_date=FLOOR,
        unit_cap=1,
        coverage=coverage,
        source_url=url,
        coding_notes=f"{BEN}: {note} Dated {FLOOR} (start of the window): when the rule was adopted was not researched."
        + FLAG
        + "check the use table section and that the rule was in force by 2010.",
    )


ROWS: list[dict] = [
    # 1. Killeen: North Killeen Overlay District ordinance passed (4-1 vote, reported by the Killeen Daily Herald)
    row(
        reform_id="TX-4839148-adu-2026",
        jurisdiction_geoid="4839148",
        theme="adu",
        component="North Killeen Overlay District (Ord. 26-046): ADUs, tiny homes and THOWs allowed in every residential district inside the overlay that allows single-family dwellings, with a building permit and site plan; one ADU per lot, attached or detached; lots of at least 6,000 sq ft; up to the lesser of 800 sq ft or 50% of the main house; short-term rental allowed with a registration permit",
        adoption_date="2026-10-20",
        effective_date="2026-10-20",
        by_right=True,
        adu_detached_allowed=True,
        adus_per_lot=1,
        coverage="Only inside the North Killeen Overlay District (about 1,842 acres of north Killeen); single-family-zoned lots of at least 6,000 sq ft",
        source_url="https://www.killeentexas.gov/DocumentCenter/View/14388/2026-north-killeen-overlay-district-ordinance-updated; https://www.killeentexas.gov/731/North-Killeen-Overlay-District; https://www.facebook.com/kdhnews/posts/the-killeen-city-council-in-a-4-1-vote-this-week-approved-the-north-killeen-over/1696140302460117/",
        source_section="Code of Ordinances Ch. 31, North Killeen Overlay District, §5 (ADUs)",
        source_quote="ADUs, Tiny Homes and THOWs shall be allowed in all residential zoning districts within the NKOD that allow single-family dwellings",
        coding_notes=f"{BEN}: the council approved the overlay 4-1 (Killeen Daily Herald post). Terms read from Killeen_North-Killeen-Overlay_2026-10-20.pdf pp. 11-12 (city-hosted copy, text layer; quote repaired from the OCR): building permit and site plan only (by right); minimum lot 6,000 sq ft; size the lesser of 800 sq ft or 50% of the primary dwelling (a share-of-house cap, so adu_max_sqft is blank); STR allowed under §31-950. min_lot_sqft is left blank on purpose so D-021 reads the overlay-only coverage text, not a citywide lot-size share. Owner occupancy and parking not read (OCR gaps). The ordinance is effective 'after passage and publication'; adoption and effective are both coded as the 2026-10-20 public-hearing meeting (PH-26-037). The city copy's signature block reads '8th day of October 2026' and 'Ord. #26---', conflicting with that. Does not supersede TX-4839148-adu-2010, which still governs the rest of the city."
        + FLAG
        + "confirm the adoption date (2026-10-20 vs. the copy's 2026-10-08), the publication date, the ordinance number (26-046) and owner occupancy and parking in the signed ordinance.",
    ),
    # 3. Denton: Missing Middle Housing Amendment (DCA25-0001a), council vote 6-1 on 2026-01-13
    row(
        reform_id="TX-4819972-adu-2026",
        jurisdiction_geoid="4819972",
        theme="adu",
        component="Missing Middle Housing Amendment (DCA25-0001a): one ADU by right on a lot whose principal use is a detached house; up to two accessory units with a Specific Use Permit; up to the greater of 800 sq ft or 75% of the main house; no parking minimum",
        adoption_date="2026-01-13",
        effective_date="2026-01-13",
        supersedes="TX-4819972-adu-2023",
        by_right=True,
        adu_max_sqft=800,
        adu_detached_allowed=True,
        adus_per_lot=1,
        parking="no ADU parking minimum (city ADU page)",
        coverage="Lots whose principal use is a detached single-family house",
        source_url="https://www.cityofdenton.com/1064/Accessory-Dwelling-Unit-ADU; https://www.cityofdenton.com/DocumentCenter/View/427/Denton-Development-Code-PDF",
        source_section="Denton Development Code §5.3 (ADU), as amended by DCA25-0001a",
        coding_notes=f"{BEN}: council passed the Missing Middle Housing Amendment (Case DCA25-0001a) 6-1 on 2026-01-13. It lets homeowners build ADUs by right and allows up to two secondary units with a Specific Use Permit. adus_per_lot = 1 (the by-right number). adu_max_sqft = 800: the cap is the greater of 800 sq ft or 75% of the house, so every lot gets at least 800. Size, detached and parking terms are from the city ADU page as summarized in Ben's research workbook (2026-10-29). Effective date not found, so it is the vote date. Supersedes TX-4819972-adu-2023, whose 2023-03-07 date is unsupported."
        + FLAG
        + "find the ordinance number and effective date and check the size and parking terms in the amended §5.3.",
    ),
    # 5. College Station: Ord. 2023-4454 parking for accessory living quarters
    row(
        reform_id="TX-4815976-adu-2023",
        jurisdiction_geoid="4815976",
        theme="adu",
        component="Ord. 2023-4454: off-street parking for accessory living quarters set at one space per bedroom",
        adoption_date="2023-08-10",
        effective_date="2023-08-10",
        supersedes="TX-4815976-adu-2018",
        parking="one off-street space per bedroom of the accessory living quarters",
        coverage="Areas zoned and used for single-family residential (as TX-4815976-adu-2018)",
        source_url="https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/15047/1233343/pdf; https://opendoc.cstx.gov/DocArc/edoc/1828115/2023-4454%20-%20Ordinance%20-%2008102023.pdf?dbid=0&repo=DOCUMENT-SERVER",
        source_section="UDO §7.3(H) (parking), as amended by Ord. 2023-4454",
        coding_notes=f"{BEN}: Ord. 2023-4454 sets the minimum off-street parking for accessory living quarters at one space per bedroom. Only the parking changes; the other terms stay as in TX-4815976-adu-2018 (blank here, the Austin 2023 convention). parking_min_per_unit is blank because the rule is per bedroom, not per unit. Effective date not found, so it is the adoption date. This id belonged to the 2018 rule until it was renamed TX-4815976-adu-2018 on {DAY}."
        + FLAG
        + "the ordinance's effective clause.",
    ),
    # 7. Pearland: UDC adopted 2006-02-27, ADU by CUP only, duplex by CUP in R-4 only
    row(
        reform_id="TX-4856348-adu-2006",
        jurisdiction_geoid="4856348",
        theme="adu",
        component="Unified Development Code (2006): an ADU needs a Conditional Use Permit (Planning and Zoning Commission and City Council) in every residential district except SD, plus two extra parking spaces",
        adoption_date="2006-02-27",
        effective_date="2006-02-27",
        by_right=False,
        adus_per_lot=0,
        parking="two additional spaces",
        coverage="All residential districts except SD (by CUP)",
        source_url="https://www.pearlandtx.gov/departments/community-development/planning/unified-development-code-udc; https://www.pearlandtx.gov/departments/community-development/planning/conditional-use-permit",
        source_section="UDC Land Use Matrix (accessory dwelling)",
        coding_notes=f"NO ADU RULE (adus_per_lot = 0): an ADU is allowed only with a Conditional Use Permit decided by the council. {BEN}: the CUP rule was adopted with the UDC on 2006-02-27. CUP terms are from Ben's research workbook (2026-10-29). Effective date coded as the adoption date."
        + FLAG
        + "check the 2006 UDC's effective clause and whether the ADU row of the matrix has changed since.",
    ),
    row(
        reform_id="TX-4856348-missing_middle-2006",
        jurisdiction_geoid="4856348",
        theme="missing_middle",
        component="Unified Development Code (2006): two-family dwelling by Conditional Use Permit in R-4; no duplex or 3-4 unit building in R-E, R-1, R-2, R-3",
        adoption_date="2006-02-27",
        effective_date="2006-02-27",
        by_right=False,
        unit_cap=2,
        coverage="R-4 only (by CUP); R-E, R-1, R-2, R-3 one dwelling",
        coverage_zones="R-4",
        source_url="https://www.pearlandtx.gov/departments/community-development/planning/unified-development-code-udc",
        source_section="UDC Land Use Matrix (two-family dwelling)",
        coding_notes=f"{BEN}: the duplex rules were adopted with the UDC on 2006-02-27. The matrix (Ben's research workbook, 2026-10-29) has two-family conditional in R-4, permitted in TH, MF and OT-R, and four-family in TH, MF and MH, none of which is a single-family district. Effective date coded as the adoption date."
        + FLAG
        + "check the 2006 UDC's effective clause and whether the two-family row of the matrix has changed since.",
    ),
    # Missing-middle table (Ben, 2026-10-30)
    row(
        reform_id="TX-4824000-missing_middle-2010",
        jurisdiction_geoid="4824000",
        theme="missing_middle",
        component="Title 20: duplex permitted in R-4 and R-5; not allowed in R-1 to R-3A; no 3-4 unit building in the residential (R) districts",
        effective_date=FLOOR,
        by_right=True,
        unit_cap=2,
        coverage="R-4 and R-5 (duplex by right); R-1, R-2, R-2A, R-3, R-3A one dwelling",
        coverage_zones="R-4;R-5",
        source_url="https://www.elpasotx.com/assets/pdf/Appendix%2BA%2B-%2BTitle%2B20%2BZoning; https://www.elpasotexas.gov/planning-and-inspections/faqs",
        source_section="Title 20 Appendix A (table of permissible uses)",
        coding_notes=f"{BEN}: duplex no in R-1 through R-3A, permitted in R-4 and R-5; 3-4 units no in those districts (multifamily districts are separate). Dated {FLOOR} (start of the window): the start date was not researched."
        + FLAG
        + "check Appendix A's two-family row for R-4 and R-5 and that it was in force by 2010.",
    ),
    mm_no(
        "4817000",
        "Corpus Christi",
        "Standard single-family districts (FR, RE, RS-22, RS-15, RS-10, RS-6, RS-4.5); narrow exceptions in specified overlays and qualifying infill or transitional projects",
        "https://www.corpuschristitx.gov/department-directory/development-services/unified-development-code-udc/",
        "duplex no in standard single-family districts, with narrow exceptions in specified overlays or qualifying infill/transitional projects; no general permission for 3-4 units.",
    ),
    row(
        reform_id="TX-4803000-missing_middle-2010",
        jurisdiction_geoid="4803000",
        theme="missing_middle",
        component="Zoning ordinance: duplex allowed in R-3; not in R-1 or R-2; no 3-4 unit building in R-1 to R-3",
        effective_date=FLOOR,
        by_right=True,
        unit_cap=2,
        coverage="R-3 (duplex); R-1, R-2 one dwelling",
        coverage_zones="R-3",
        source_url="https://downloads.amarillo.gov/Planning/Zoning%20Ordinance%20August%202014.pdf; https://www.amarillo.gov/planning/codes-ordinances/",
        source_section="Zoning ordinance use table (two-family dwelling)",
        coding_notes=f"{BEN}: duplex no in R-1/R-2, yes in R-3; 3-4 units no in R-1 to R-3 (multifamily in denser districts). R-3 counted as a single-family district (Amarillo's R-1 to R-3 are its single-family districts); by_right True read from 'yes'. Dated {FLOOR} (start of the window): the start date was not researched."
        + FLAG
        + "check that the R-3 duplex is by right (not by SUP) and in force by 2010.",
    ),
    mm_no(
        "4839148",
        "Killeen",
        "Single-family districts (R-1, SF-2 and others); a Zoning Board exception may allow a duplex on a qualifying R-1/SF-2 lot next to business or industrial zoning, and a four-family building in R-2 under a similar exception",
        "https://www.killeentexas.gov/",
        "duplex not by right in single-family districts; a Zoning Board exception may allow one on a qualifying R-1/SF-2 lot next to business or industrial zoning; 3-4 units generally no (a narrow four-family exception may apply in R-2 next to business or industrial zoning). Coded as one dwelling because the exception is a board case limited to edge lots.",
    ),
    row(
        reform_id="TX-4819972-missing_middle-2010",
        jurisdiction_geoid="4819972",
        theme="missing_middle",
        component="Denton Development Code Table 5.2-A: duplex by Specific Use Permit in R4; no duplex in R1-R3; no 3-4 unit building in R1-R4",
        effective_date=FLOOR,
        by_right=False,
        unit_cap=2,
        coverage="R4 only (by SUP); R1, R2, R3 one dwelling",
        coverage_zones="R4",
        source_url="https://www.cityofdenton.com/DocumentCenter/View/427/Denton-Development-Code-PDF",
        source_section="Denton Development Code Table 5.2-A",
        coding_notes=f"{BEN}: duplex no in R1-R3, Specific Use Permit in R4; 3-4 units no in R1-R4 (current rule, after the 2026-01-13 Missing Middle Housing Amendment). Dated {FLOOR} (start of the window): when the R4 SUP started (the 2019 Development Code or the 2026 amendment) was not researched."
        + FLAG
        + "find when the R4 duplex SUP started; if it came with DCA25-0001a (2026-01-13), redate this row and add a 2010 one-dwelling row.",
    ),
    mm_no(
        "4813024",
        "Carrollton",
        "Single-family districts; duplexes permitted in the D (duplex) and multifamily districts only",
        "https://www.cityofcarrollton.com/departments/departments-g-p/planning/zoning-information/zoning-ordinance",
        "duplex no in single-family districts (permitted in D and multifamily districts); 3-4 units no in single-family districts. Ord. 3331 (2009-10-06) repealed the triplex/fourplex districts (Ben's research workbook, 2026-10-29).",
    ),
    mm_no(
        "4815976",
        "College Station",
        "Ordinary single-family districts; duplexes permitted in D or MH zoning, small multiplexes in MH and MF",
        "https://www.cstx.gov/business-development/unified-development-ordinance/",
        "duplex no in ordinary single-family districts (permitted in D or MH zoning); 3-4 units no in ordinary single-family districts (small multiplexes permitted in MH and MF).",
    ),
]

# reform_id -> (field values, note)
EDITS: dict[str, tuple[dict, str]] = {
    # 2. Lewisville: council adopted the UDC updates, backyard cottages included, on 2026-09-21
    "TX-4842508-adu-2026": (
        {"status": "in_force"},
        f"{BEN}: the city council officially adopted the broad UDC updates, including the backyard cottage amendments, on 2026-09-21 (https://citizenportal.ai/articles/10167883/texas/denton-county/lewisville/council-adopts-broad-unified-development-code-updates-covering-drones-backyard-cottages-and-ev-chargers), so the row is in force, not pending. FLAG for second coder: confirm in the official minutes and find the ordinance number and effective date.",
    ),
    # 4. McKinney: the 2022 UDC did not explicitly ban renting
    "TX-4845744-adu-2022": (
        {},
        f"{BEN}: the 2022 UDC did not explicitly ban renting, but it framed the unit for family, multigenerational or guest use and so limited the use case (https://mckinney.legistar.com/LegislationDetail.aspx?ID=6478853&GUID=B04E970F-373D-4892-AEE0-82D80AFCC7B5, the 2024-01-16 council work session on supporting ADUs in East McKinney). The row stays a rentable ADU from 2022. A news report of that session says the ordinance then allowed ADUs only on lots of at least 12,000 sq ft (not checked). FLAG for second coder: check whether a minimum lot size applied in 2022-2026, and whether a later amendment widened the rule (a new row).",
    ),
    # 6. League City: duplexes are neither permitted nor SUP in RSF-5
    "TX-4841980-missing_middle-2020": (
        {"coverage": "RSF-2 duplex permitted (P); RSF-20, RSF-10, RSF-7, RSF-5 one dwelling"},
        f"{BEN}: duplexes are neither permitted nor allowed by SUP in RSF-5 (Chapter 125 Article 3, https://www.leaguecitytx.gov/DocumentCenter/View/45962/Chap-125-Article-3); RSF-5 allows zero-lot-line and attached single-family units, and mobile homes by SUP. The RSF-5 'S' reading of 2026-10-30 (#32) was a column misalignment in the PDF's text layer and is withdrawn.",
    ),
}

# tracker (table, place) -> (status, note)
TRACKERS: dict[tuple[str, str], tuple[str, str]] = {
    ("adu", "Killeen"): (
        "coded",
        "Ben 2026-10-30: overlay passed 4-1; coded TX-4839148-adu-2026 (overlay only). Open: the signed ordinance's number and dates, owner occupancy, parking.",
    ),
    ("adu", "Lewisville"): (
        "coded",
        "Ben 2026-10-30: adopted 2026-09-21; TX-4842508-adu-2026 now in force. Open: ordinance number, effective date, the 2022 baseline.",
    ),
    ("adu", "McKinney"): (
        "partial",
        "Ben 2026-10-30: 2022 UDC did not explicitly ban renting (family/guest framing). Open: 12,000 sq ft lot minimum before 2026, and any amendment that widened the rule.",
    ),
    ("adu", "Pearland"): (
        "coded",
        "Ben 2026-10-30: CUP rule adopted with the UDC 2006-02-27; coded TX-4856348-adu-2006 (none).",
    ),
    ("adu", "League City"): (
        "partial",
        "Ben 2026-10-30: no duplex in RSF-5. Still open: SUP-versus-administrative ADU approval, Art. 4 parking, pre-2026 baseline.",
    ),
    ("mm", "El Paso"): (
        "coded",
        "Ben 2026-10-30: duplex by right in R-4, R-5; coded TX-4824000-missing_middle-2010 (start date not researched).",
    ),
    ("mm", "Corpus Christi"): (
        "coded",
        "Ben 2026-10-30: no in single-family districts; coded TX-4817000-missing_middle-2010.",
    ),
    ("mm", "Amarillo"): ("coded", "Ben 2026-10-30: duplex in R-3; coded TX-4803000-missing_middle-2010."),
    ("mm", "Killeen"): (
        "coded",
        "Ben 2026-10-30: not by right (narrow board exception); coded TX-4839148-missing_middle-2010 as one dwelling.",
    ),
    ("mm", "Denton"): (
        "coded",
        "Ben 2026-10-30: duplex by SUP in R4; coded TX-4819972-missing_middle-2010. Open: when the R4 SUP started.",
    ),
    ("mm", "Carrollton"): (
        "coded",
        "Ben 2026-10-30: no in single-family districts; coded TX-4813024-missing_middle-2010.",
    ),
    ("mm", "College Station"): (
        "coded",
        "Ben 2026-10-30: no in ordinary single-family districts; coded TX-4815976-missing_middle-2010.",
    ),
    ("mm", "Pasadena"): (
        "open",
        "Ben 2026-10-30: stays pending; no zoning does not establish that a duplex can go on any lot.",
    ),
    ("mm", "Pearland"): (
        "coded",
        "Ben 2026-10-30: duplex rules adopted 2006-02-27; coded TX-4856348-missing_middle-2006 (CUP in R-4).",
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
    added = 0
    for r in ROWS:
        assert set(r) <= set(cols), set(r) - set(cols)
        if r["reform_id"] not in by_id:
            rows.append({c: r.get(c, "") for c in cols})
            added += 1
    for rid, (fields, note) in EDITS.items():
        r = by_id[rid]
        if note not in r["coding_notes"]:
            r.update(fields)
            r["coding_notes"] = r["coding_notes"].rstrip() + f" Updated {DAY}: " + note
    write(PATH, cols, rows)
    flagged = sum("FLAG for second coder" in r["coding_notes"] for r in rows)

    done = 0
    for table in ("adu", "mm"):
        path = ORD / f"tx-{table}-lookups-todo.csv"
        tcols, trows = read(path)
        for t in trows:
            key = (table, t["place"])
            if key in TRACKERS:
                status, note = TRACKERS[key]
                t["status"] = status
                if note not in t["notes"]:
                    t["notes"] = t["notes"].rstrip() + " | " + note
                done += 1
            if table == "adu" and t["place"] == "(all flagged rows)":
                count = f"{DAY}: {flagged} of {len(rows)} rows carry 'FLAG for second coder'; the 2026-10-29 corrections are decided (tx-corrections-2026-10-29.csv)"
                if count not in t["notes"]:
                    t["notes"] = t["notes"].rstrip() + " | " + count
        write(path, tcols, trows)
    print(f"{added} rows added, {len(EDITS)} rows updated, {done} tracker rows -> {PATH}")


if __name__ == "__main__":
    main()
