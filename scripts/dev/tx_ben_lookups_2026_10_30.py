# ruff: noqa: E501  (coding data: long source URLs and notes)
"""Texas rule rows from Ben's own lookups (2026-10-30) -> config/reforms/tx.csv and the lookup trackers.

Run from the repo root after `tx_corrections_2026_10_30.py`:
`uv run python scripts/dev/tx_ben_lookups_2026_10_30.py`. Rerunning it is safe.

Ben answered the open items in chat on 2026-10-30. There were seven ADU and code-history questions, a table of
eight missing-middle lookups, follow-ups for Plano, Lubbock and Laredo, and fee answers for Austin, SAWS, Fort
Worth, Dallas and Houston. Ben's updated workbook (`...-updated.xlsx`, 2026-10-30) supplies the official
sources and table readings behind the missing-middle and fee answers. Facts are his unless a note says
otherwise. Two terms are read from the local PDFs: Killeen's overlay terms (`Killeen_North-Killeen-
Overlay_2026-10-20.pdf`) and Lewisville's districts (the row coded earlier).

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
WB2 = "Ben's updated research workbook (2026-10-30, lotline-data/manual/texas/Texas-Municipal-ADU-and-Missing-Middle-Research-updated.xlsx)"


def row(**kw) -> dict:
    base = {"state": "TX", "status": "in_force", "coder": "ben", "coder_agreement": "single_coder"}
    return base | {k: ("" if v is None else str(v)) for k, v in kw.items()}


def mm_no(geoid: str, place: str, coverage: str, url: str, note: str, section: str = "") -> dict:
    return row(
        reform_id=f"TX-{geoid}-missing_middle-2010",
        jurisdiction_geoid=geoid,
        theme="missing_middle",
        component=f"{place}: one dwelling per lot in the single-family districts (no duplex or 3-4 unit building)",
        effective_date=FLOOR,
        unit_cap=1,
        coverage=coverage,
        source_url=url,
        source_section=section,
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
        coding_notes=f"{BEN}: duplex no in R-1 through R-3A, permitted in R-4 and R-5; 3-4 units no in those districts (multifamily districts are separate). {WB2}: the city-published Appendix A lists the duplex as permitted in R-4 and R-5 and not in R-1, R-2, R-2A, R-3 or R-3A; apartments (3+ units) are not permitted in R-1 to R-5; the city FAQ says a residential lot may have one single-family dwelling (plus the ADU exception). R-4 and R-5 are counted as single-family districts that also allow duplexes. Dated {FLOOR} (start of the window): the start date was not researched."
        + FLAG
        + "check Appendix A's two-family row for R-4 and R-5 and that it was in force by 2010.",
    ),
    mm_no(
        "4817000",
        "Corpus Christi",
        "Standard single-family districts (FR, RE, RS-22, RS-15, RS-10, RS-6, RS-4.5); narrow exceptions in specified overlays and qualifying infill or transitional projects",
        "https://online.encodeplus.com/regs/corpuschristi-tx/doc-view.aspx?print=1&tocid=; https://www.corpuschristitx.gov/department-directory/development-services/unified-development-code-udc/",
        f"duplex no in standard single-family districts, with narrow exceptions in specified overlays or qualifying infill/transitional projects; no general permission for 3-4 units. {WB2}: UDC Table 4.3.2 (FR, RE, RS-22, RS-15, RS-10, RS-6, RS-4.5) does not permit two-family houses and §4.2.2 sets one single-family dwelling per lot; Table 4.4.2 permits them by right in RS-TF and RM; §6.14 allows alternative housing only in specified concepts, overlays and qualifying RS-6/RS-4.5 infill or transitional cases; 3+ units are apartments.",
        "UDC §4.2.2, Tables 4.3.2 and 4.4.2, §6.14",
    ),
    mm_no(
        "4803000",
        "Amarillo",
        "Single-family districts R-1 and R-2 one dwelling; duplexes in R-3, which merged the former two-family and townhouse districts (not counted as single-family)",
        "https://www.amarillo.gov/wp-content/uploads/2024/09/Zoning-Ordinance-Table-List-COA.pdf; https://downloads.amarillo.gov/Planning/Zoning%20Ordinance%20August%202014.pdf; https://www.amarillo.gov/wp-content/uploads/2025/03/March-2008-Development-Policy-Manual.pdf",
        f"duplex no in R-1/R-2, yes in R-3; 3-4 units no in R-1 to R-3. {WB2}: the city-hosted Chapter 4-10 use schedule (P permitted, S SUP, blank prohibited) has the two-family use blank in R-1 and R-2 and permitted in R-3, and the Development Policy Manual says R-3 combines the former two-family and townhouse districts; Multiple-Family Housing (3+ units, §4-10-83(4)) is blank in R-1 to R-3. R-3 is therefore a two-family district under the coding rule, so this is a one-dwelling row (an earlier draft of this PR read R-3 as single-family).",
        "Zoning Ordinance Ch. 4-10 use schedule; §4-10-83",
    ),
    mm_no(
        "4839148",
        "Killeen",
        "Single-family districts (R-1, SF-2 and others); a Zoning Board exception may allow a duplex on a qualifying R-1/SF-2 lot next to business or industrial zoning, and a four-family building in R-2 under a similar exception",
        "https://library.municode.com/TX/Killeen/codes/Code_of_Ordinances?nodeId=PTIICOOR_CH31ZO_ARTIINGE_S31-5COAUBU; https://www.killeentexas.gov/DocumentCenter/View/204/Notice-of-Appeal-to-the-Zoning-Board-of-Adjustments-and-Appeals-PDF",
        f"duplex not by right in single-family districts; a Zoning Board exception may allow one on a qualifying R-1/SF-2 lot next to business or industrial zoning; 3-4 units generally no (a narrow four-family exception may apply in R-2 next to business or industrial zoning). Coded as one dwelling because the exception is a board case limited to edge lots. {WB2}: §31-186 allows one-family dwellings in R-1; R-2 is the Two-Family district (§31-231); one principal single- or two-family structure per lot in R-1/R-2. The Board may permit a two-family dwelling on an R-1 or SF-2 lot of at least 6,000 sq ft that sides on business or industrial zoning (transitional strip at most 100 ft wide); 3-4 units belong in R-3F, apartments in R-3A.",
        "Code Ch. 31 §§31-186, 31-231 (R-1, R-2), Zoning Board transitional-use exception",
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
        source_url="https://denton-tx.legistar.com/View.ashx?GUID=D3DD0DDF-2105-4CA2-BE49-FE894142AE92&ID=11133786&M=F; https://www.cityofdenton.com/DocumentCenter/View/427/Denton-Development-Code-PDF",
        source_section="Denton Development Code Table 5.2-A",
        coding_notes=f"{BEN}: duplex no in R1-R3, Specific Use Permit in R4; 3-4 units no in R1-R4 (current rule, after the 2026-01-13 Missing Middle Housing Amendment). {WB2}: Table 5.2-A (Legistar attachment; P permitted, S SUP, blank prohibited, + use-specific standards) has the duplex blank in RR and R1-R3, S+ in R4, P+ in R6, R7, MN, MD, MR; triplex and fourplex blank through R4, P+ from R6. Dated {FLOOR} (start of the window): when the R4 SUP started (the 2019 Development Code or the 2026 amendment) was not researched."
        + FLAG
        + "find when the R4 duplex SUP started; if it came with DCA25-0001a (2026-01-13), redate this row and add a 2010 one-dwelling row.",
    ),
    mm_no(
        "4813024",
        "Carrollton",
        "Single-family districts; duplexes permitted in the D (duplex) and multifamily districts only",
        "https://www.cityofcarrollton.com/home/showpublisheddocument/40713/639150626674770000; https://www.cityofcarrollton.com/departments/departments-g-p/planning/zoning-information",
        f"duplex no in single-family districts (permitted in D and multifamily districts); 3-4 units no in single-family districts. Ord. 3331 (2009-10-06) repealed the triplex/fourplex districts (Ben's research workbook, 2026-10-29). {WB2}: the Article 5 matrix (updated April 2026) has the Duplex Dwelling cell blank in 'All SF-Detached Districts' and 'All SF-Attached Districts', permitted in D and MF; Multifamily Dwelling (3+) only in MF.",
        "Comprehensive Zoning Ordinance Article 5, p. 5-4 (use matrix, April 2026)",
    ),
    mm_no(
        "4815976",
        "College Station",
        "Ordinary single-family districts; duplexes permitted in D or MH zoning, small multiplexes in MH and MF",
        "https://library.municode.com/tx/college_station/codes/code_of_ordinances?nodeId=SPBLADEOR_APXAUNDEOR_ART6USRE; https://www.cstx.gov/business-development/unified-development-ordinance/; https://blog.cstx.gov/wp-content/uploads/2022/08/4-Middle-Housing-Zoning.pdf",
        f"duplex no in ordinary single-family districts (permitted in D or MH zoning); 3-4 units no in ordinary single-family districts (small multiplexes permitted in MH and MF). {WB2}: UDO Article 6 use table: GS, RS, R and the other one-family districts list neither duplex nor 'Multiplex Small'; MH (Middle Housing, 2022) is a separate district needing a rezoning.",
        "UDO Article 6 use table",
    ),
    mm_no(
        "4858016",
        "Plano",
        "Single-family districts SF-20, SF-9, SF-7, SF-6 (and SF-A); two-family dwellings in the 2F district",
        "https://www.plano.gov/municipal-codes-and-ordinances",
        "the 2024-2025 zoning amendments do not allow standard two-family homes (duplexes) across the single-family districts; 3-4 unit buildings are multifamily, not allowed in single-family districts (Ben's research workbook, 2026-10-29). Any narrow exception was not identified.",
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
    # Lubbock: what the 'limited use' approval requires
    "TX-4845000-missing_middle-2023": (
        {},
        f"{BEN}: 'limited use' approval is administrative, by the Director of Planning through a Use Verification Form, when the duplex meets the design, site and building standards of §39.02.018 and Division 3.2: parking behind the building, a rear alley preferred, front garages subordinate (at most 50% of the facade or 28 ft, set back 10 ft, or side-turned), service and trash off the alley, ground-floor heights. That confirms by_right = True (no hearing or board). No ADU on the same lot as a duplex. Sources: https://ecode360.com/45661592, https://ecode360.com/45660753.",
    ),
    # Laredo: Ord. 2025-O-004
    "TX-4841464-missing_middle-2010": (
        {},
        f"{BEN}: Ord. 2025-O-004, adopted 2025-01-28, amends the Land Development Code's minimum lot area for duplexes and adds a 'vertical duplex' definition. It sets standards for duplexes in the districts that allow them; it was not found to allow duplexes in RS or R-1, so this row is unchanged. FLAG for second coder: check whether 2025-O-004 changed the use table for any single-family district.",
    ),
}

FEES = ROOT / "config" / "fees" / "tx.csv"
PARKLAND = (
    f"{BEN}: newly built ADUs and duplex units on existing lots pay the parkland dedication fee unless exempted "
    "through an affordable housing program (Affordability Unlocked or another certified city program), so "
    "amount_per_unit_usd is the per-unit amount for the density tier. FLAG for second coder: check the exemption "
    "list in Land Development Code Ch. 25-1 Art. 14 and the fee table's fiscal year."
)
SERVICE_UNITS = (
    f"{BEN}: Austin Water assigns service units (living unit equivalents) by water meter size, not building type: "
    "5/8-inch 1.0, 3/4-inch 1.5, 1-inch 2.5 (REca FY2023 development fee schedule, "
    "https://www.reca.org/uploads/1/3/8/9/138900216/fy23_development_feeschedule.pdf). A home, duplex unit or "
    "ADU on a 5/8-inch meter is 1 service unit. FLAG for second coder: secondary source; check Austin Water's "
    "meter-equivalency table."
)
HOUSTON_SU = (
    f"{BEN}: a single-family home up to 3,000 sq ft is 1 service unit. {WB2}: the 2020 Cost of Service Study "
    "(https://www.houstontx.gov/citysec/HPW/impactfeereport.pdf) and the Houston Public Works memo "
    "(https://www.houstontx.gov/citysec/HPW/impactfeememo.pdf) define the unit by average single-family use."
)
# fee rows to annotate -> (jurisdiction, fee_type prefix, fill amount_per_unit_usd from amount_usd, note)
FEE_EDITS: list[tuple[str, str, bool, str]] = [
    ("4805000", "Parkland dedication fee in lieu", True, PARKLAND),
    ("4805000", "Water impact fee", False, SERVICE_UNITS),
    ("4805000", "Wastewater impact fee", False, SERVICE_UNITS),
    ("4835000", "Water impact fee, collected rate", False, HOUSTON_SU),
    ("4835000", "Wastewater impact fee, collected rate", False, HOUSTON_SU),
]

SAWS_FY2027 = "https://docsonline.sanantonio.gov/FileUploads/dsd/CurrentFeeSchedule.pdf"
SAWS_TIMING = "assessed at plat recordation; paid before recordation or at meter set/sewer connection, as elected at plat application"
HOU_TIMING = "collected when the building permit issues, or at water/wastewater connection if no permit"
HOU_2021 = "https://houston.novusagenda.com/agendapublic/CoverSheet.aspx?ItemID=23219&MeetingID=488; https://www.houstontx.gov/citysec/agenda/2021/Jun2221.pdf; https://www.houstontx.gov/citysec/HPW/impactfeememo.pdf"


def fee(**kw) -> dict:
    base = {"state": "TX", "fee_component": "water_sewer", "building_type_std": "SFD", "basis": "per_lue"}
    return base | {k: str(v) for k, v in kw.items()}


FEE_ROWS: list[dict] = [
    *(
        fee(
            jurisdiction_geoid="4865000",
            year=2026,
            fee_type=f"SAWS water impact fee (flow + system development + water supply), {area} elevation, plats on/after 2019-06-01",
            amount_usd=total,
            dollar_year=2026,
            payment_timing=SAWS_TIMING,
            source=SAWS_FY2027,
            source_section="FY2027 Development Fee Schedule (revised Oct. 2026), SAWS Water and Sewer Impact Fees",
            notes=f"{BEN} and {WB2}: per EDU for a 5/8-inch meter in the {area} elevation area: flow $1,188 + system development ${sysdev:,} + water supply $2,706 = ${total:,}; applies to plats recorded on or after 2019-06-01 (older plats: the 2014 ordinance rows). effective_date blank and amount_per_unit_usd blank, as for the low elevation row (zone- and plat-date dependent). FLAG for second coder: check against the posted schedule.",
        )
        for area, sysdev, total in (("middle", 1014, 4908), ("high", 1203, 5097))
    ),
    *(
        fee(
            jurisdiction_geoid="4835000",
            year=2021,
            effective_date="2021-07-01",
            fee_type=f"{kind} impact fee, collected rate (2021 update)",
            amount_usd=amount,
            amount_per_unit_usd=amount,
            dollar_year=2021,
            payment_timing=HOU_TIMING,
            source=HOU_2021,
            source_section="Ords. 2021-388 (adopted 2021-05-19) and 2021-512 (passed 2021-06-23, collection from 2021-07-01)",
            notes=f"{BEN} and {WB2}: Ord. 2021-388 adopted the updated land-use assumptions, capital plan and fees on 2021-05-19; Ord. 2021-512 set collection from 2021-07-01. Collected rate per service unit {share} of the maximum ${maximum}); 1 service unit per single-family home up to 3,000 sq ft, so amount_per_unit_usd = amount. The annual 2022-2025 collected rates are not coded. FLAG for second coder: secondary summary of the ordinances; check the effective clause.",
        )
        for kind, amount, share, maximum in (
            ("Water", 1618.11, "(50%", "3,236.21"),
            ("Wastewater", 1621.63, "(70%", "2,316.62"),
        )
    ),
]

# fee tracker place -> note (all stay partial)
FEE_TRACKERS = {
    "Austin": "Ben 2026-10-30: ADUs and duplex units on existing lots pay parkland (unless an affordable-housing exemption); service units follow meter size (5/8-inch 1.0, 3/4-inch 1.5, 1-inch 2.5). Still open: the parkland table's fiscal year.",
    "San Antonio (SAWS)": "Ben 2026-10-30: FY2027 5/8-inch water $4,908 middle and $5,097 high elevation (plats on/after 2019-06-01), coded. Still open: the exact charges for pre-2019 plats after 2015 (the 2014 ordinance rows cover 2014-2015).",
    "Fort Worth": "Ben 2026-10-30: the transportation fee depends on service area, plat cohort (2008, 2013, 2017, 2022 studies) and permit date; a home is one residential unit (e.g. 2022 cohort, 2026-27: $1,067.30 Area A, $2,033.20 Area B, $0 L/W). Not coded (area-dependent). Still open: the full 2015-2022 annual series.",
    "Dallas": "Ben 2026-10-30: no separate DWU impact fee in the reviewed public schedules, but no official statement that none exists. Still open pending DWU confirmation.",
    "Houston": "Ben 2026-10-30: 1 service unit per single-family home up to 3,000 sq ft; Ord. 2021-388 (2021-05-19) and 2021-512 (collection from 2021-07-01) at $1,618.11 water and $1,621.63 wastewater, coded. Still open: the annual 2015-2022 schedules.",
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
    ("mm", "Amarillo"): (
        "coded",
        "Ben 2026-10-30: duplex only in R-3, the former two-family and townhouse district (updated workbook); coded TX-4803000-missing_middle-2010 as one dwelling in R-1/R-2.",
    ),
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
    ("mm", "Plano"): (
        "coded",
        "Ben 2026-10-30: the 2024-25 amendments do not allow duplexes across the single-family districts; coded TX-4858016-missing_middle-2010.",
    ),
    ("mm", "Lubbock"): (
        "coded",
        "Ben 2026-10-30: limited use is administrative (Director, Use Verification Form) with design standards (§39.02.018, Div. 3.2); no ADU with a duplex. Still open: the matrix's amendment history and the pre-2023 Ch. 40 rule.",
    ),
    ("mm", "Laredo"): (
        "partial",
        "Ben 2026-10-30: Ord. 2025-O-004 adopted 2025-01-28 (duplex minimum lot area, vertical duplex definition). Still open: R-1A, R-1B, R-1-MH and the triplex/fourplex matrix.",
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

    fcols, frows = read(FEES)
    have = {(f["jurisdiction_geoid"], f["fee_type"]) for f in frows}
    for f in FEE_ROWS:
        assert set(f) <= set(fcols), set(f) - set(fcols)
        if (f["jurisdiction_geoid"], f["fee_type"]) not in have:
            frows.append({c: f.get(c, "") for c in fcols})
    fee_edits = 0
    for f in frows:
        for geoid, prefix, per_unit, note in FEE_EDITS:
            if (
                f["jurisdiction_geoid"] == geoid
                and f["fee_type"].startswith(prefix)
                and note not in f["notes"]
            ):
                if per_unit and not f["amount_per_unit_usd"]:
                    f["amount_per_unit_usd"] = f["amount_usd"]
                f["notes"] = f["notes"].rstrip() + f" Updated {DAY}: " + note
                fee_edits += 1
    write(FEES, fcols, frows)

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
    fdone = 0
    path = ORD / "tx-fee-lookups-todo.csv"
    tcols, trows = read(path)
    for t in trows:
        note = FEE_TRACKERS.get(t["place"])
        if note:
            if note not in t["notes"]:
                t["notes"] = t["notes"].rstrip() + " | " + note
            fdone += 1
    write(path, tcols, trows)
    print(
        f"{added} rows added, {len(EDITS)} rows updated, {done + fdone} tracker rows, {fee_edits} fee rows -> {PATH}"
    )


if __name__ == "__main__":
    main()
