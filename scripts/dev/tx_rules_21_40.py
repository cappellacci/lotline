# ruff: noqa: E501  (coding data: long source URLs and notes)
"""ADU and missing-middle rules for Texas places 21-40 by 2020 population -> config/reforms/tx.csv.

Texas data plan S4/S5 (docs/build/tx-data-plan.md, approved by Ben 2026-10-23). Run from the repo root:
`uv run python scripts/dev/tx_rules_21_40.py`. Rows are written by `reform_id`: a new id is appended, an existing
id is replaced. Rerunning is safe.

Method: one read of each city's zoning code (index page plus the chapter that holds the residential rules) on
the zoneomics.com code mirror, whose robots.txt allows all agents. The official publishers block automated
reading (library.municode.com: Cloudflare challenge; ecode360.com: robots.txt disallows ClaudeBot;
codelibrary.amlegal.com: HTTP 403), so **every row here is flagged for a second coder** against the official
code. Places whose rules the mirror did not show go to `docs/research/ordinances/tx-adu-lookups-todo.csv` and
`tx-mm-lookups-todo.csv` instead of getting a row (D-022: unread stays blank).

Conventions are those of `scripts/dev/tx_adu_rows.py` (WS-TX, 2026-10-20), plus:
- **Missing middle "no" rows:** a place whose single-family districts allow one dwelling per lot gets an explicit
  row with `unit_cap = 1`, which D-024 reads as no missing-middle rule (dose 0), so the place counts as untreated
  on evidence rather than by default. Coded at 2010-01-01 when the one-unit rule predates the window.
- **Dates:** where only the code's history note is known, the row is dated by the latest ordinance that the
  note ties to the section, and the notes say the substance may be older (a recodification date is not an
  adoption date; a second coder should check before the row is used as a D-025 event).
"""

import csv
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "config" / "reforms" / "tx.csv"
COLS = next(csv.reader(PATH.open()))
ROWS: list[dict] = []
FLOOR = "2010-01-01"
FLAG = (
    " FLAG for second coder: read on the zoneomics mirror only (official code host blocks automated access)"
)
Z = "https://www.zoneomics.com/code/"


def row(**kw):
    base = {
        "state": "TX",
        "status": "in_force",
        "coder": "claude",
        "coder_agreement": "single_coder",
    }
    base.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
    unknown = set(base) - set(COLS)
    assert not unknown, unknown
    ROWS.append(base)


def adu_none(geoid, year, component, effective, sources, notes, coverage="Single-family districts"):
    """No rentable ADU in single-family zones: adus_per_lot = 0 (read as "none")."""
    row(
        reform_id=f"TX-{geoid}-adu-{year}",
        theme="adu",
        jurisdiction_geoid=geoid,
        component=component,
        effective_date=effective,
        by_right=False,
        adus_per_lot=0,
        coverage=coverage,
        source_url=sources,
        coding_notes="NO ADU RULE (adus_per_lot = 0): " + notes + FLAG + ".",
    )


def mm_none(geoid, year, component, effective, sources, notes, coverage="Single-family districts"):
    """One dwelling per single-family lot: unit_cap = 1 (no missing-middle rule, on evidence)."""
    row(
        reform_id=f"TX-{geoid}-missing_middle-{year}",
        theme="missing_middle",
        jurisdiction_geoid=geoid,
        component=component,
        effective_date=effective,
        unit_cap=1,
        coverage=coverage,
        source_url=sources,
        coding_notes="NO MISSING-MIDDLE RULE (unit_cap = 1): " + notes + FLAG + ".",
    )


# ---- Mesquite (4847892) ----------------------------------------------------------------------------------
adu_none(
    "4847892",
    2010,
    "ADU only by Conditional Use Permit on properties of at least 21,780 sq ft, owner on site, not rented or sold separately, up to 500 sq ft, four off-street spaces",
    FLOOR,
    Z + "mesquite-TX/chapter_3",
    "Zoning Ordinance §2-203 (use table, row C.3: 'Accessory dwelling unit', C in two columns; 'Requires minimum property area of 21,780 square feet') and §2-603.N: 'Accessory dwelling units may be approved by Conditional Use Permit'; 'The property owner must live on the property'; 'The accessory dwelling unit shall not be rented or sold separately'; 500 sq ft (1,000 on AG lots over one acre); four off-street spaces. Not by right and not rentable, so coded none. §2-603 history runs from Ord. 2592 (1989-04-03) to Ord. 4990 (2022-10-03) without tying subsection N to one ordinance: coded at 2010-01-01.",
)
mm_none(
    "4847892",
    2010,
    "One dwelling per lot in single-family districts; duplexes only in the D (duplex) district; 3- and 4-plexes require a PD district",
    FLOOR,
    Z + "mesquite-TX/chapter_3",
    "§2-203 use table: 'Other attached dwellings (3-plex, 4-plex)' 'Requires PD district'; duplexes permitted in the D district (§2-103, 'small lot single family attached/duplex housing'), a separate district. Use table history Ord. 2669 (1990) to Ord. 5152 (2025-01-21); no change found allowing 2-4 units on single-family lots.",
    coverage="Single-family districts AG, R-1, R-1A, R-2, R-2A, R-3",
)

# ---- McAllen (4845384) -----------------------------------------------------------------------------------
row(
    reform_id="TX-4845384-adu-2026",
    theme="adu",
    jurisdiction_geoid="4845384",
    component="Unified Development Code (Ord. 2026-16): ADU permitted (P) with use-specific standards, one per lot, owner occupies the main house or the ADU, 450-650 sq ft on lots under 6,500 sq ft, one parking space, detached in the rear",
    adoption_date="2026-02-09",
    effective_date="2026-02-09",
    by_right=True,
    owner_occ=True,
    adu_detached_allowed=True,
    adus_per_lot=1,
    parking="one space per dwelling unit",
    parking_min_per_unit=1,
    coverage="Districts marked P in Table 3.1.3-2 (single-family districts not confirmed)",
    source_url=Z + "mcallen-TX/chapter_3",
    coding_notes="UDC Ch. 3 §3.3.5A: 'Only one Accessory Dwelling Unit is allowed on a lot'; 'The property owner must occupy the principal dwelling or Accessory Dwelling Unit as the owner's permanent residence'; utilities connected to the main house; may not exceed the main house's height or size; Table 3.3.5-1 (detached single-family): 450 sq ft minimum, 650 sq ft maximum on lots under 6,500 sq ft, no maximum on larger lots (adu_max_sqft blank: no cap every lot gets); use table parking '1/DU'. Every section in the chapter ends '(Ordinance 2026-16 adopted 2/9/2026)', a new UDC: effective date not found, coded as adoption. The use table's columns did not survive extraction, so the districts marked P are not confirmed. The rule before 2026 was not read and is not coded (it falls outside the 2010-2025 panel either way)."
    + FLAG
    + ".",
)

# ---- Denton (4819972) ------------------------------------------------------------------------------------
row(
    reform_id="TX-4819972-adu-2023",
    theme="adu",
    jurisdiction_geoid="4819972",
    component="Denton Development Code §5.4.4A as amended (Ord. DCA22-0008a): ADU permitted with use-specific standards on lots with a single-family house, one per lot, up to 1,000 sq ft and 50% of the main house on lots under 10,000 sq ft (50% only on larger lots), detached allowed",
    adoption_date="2023-03-07",
    effective_date="2023-03-07",
    by_right=True,
    adu_max_sqft=1000,
    adu_detached_allowed=True,
    adus_per_lot=1,
    coverage="Districts marked P+ in Table 5.2-A (single-family districts RR, R1-R4 not confirmed); lots whose principal use is a detached house",
    source_url=Z + "denton-TX/chapter_7",
    coding_notes="DDC Table 5.2-A: 'Accessory Dwelling Unit' P+ (by right with standards, 5.2.1) in several columns, districts not mappable from the extraction. §5.4.4A: 'ADUs shall only be permitted on lots where the principal use is a single-family detached dwelling'; 'Only one ADU shall be allowed per lot'; 'ADUs shall not exceed 1,000 square feet per lot' (lots under 10,000 sq ft) and 'shall not exceed 50 percent of the square footage of the principal dwelling unit'; 'Detached ADUs shall be located to the side or rear'; ownership may not be severed. No owner-occupancy rule and no ADU parking rule in the text (owner_occ, parking blank). History note for §5.4.4: DCA22-0008a (2023-03-07), DCA23-0010b (2023-09-19), DCA24-0006a (2024-06-04): dated by the first, but the 2019 DDC already listed ADUs and what the 2023 amendment changed was not read, so this may be an amendment, not an adoption: CHECK before using as a D-025 event. adu_max_sqft = 1000 is the cap on lots under 10,000 sq ft."
    + FLAG
    + ".",
)

# ---- Waco (4876000) --------------------------------------------------------------------------------------
row(
    reform_id="TX-4876000-adu-2023",
    theme="adu",
    jurisdiction_geoid="4876000",
    component="Ord. 2023-969: accessory dwelling units on platted single-family lots, one per lot with one bedroom, owner occupies the main house or the ADU, up to 500 sq ft or 30% of the main house (whichever is greater), one extra parking space",
    adoption_date="2023-11-07",
    effective_date="2023-11-07",
    owner_occ=True,
    adu_max_sqft=500,
    adu_detached_allowed=True,
    adus_per_lot=1,
    parking="one space in addition to the two required for the main house",
    parking_min_per_unit=1,
    coverage="Legally platted single-family lots",
    source_url=Z + "waco-TX/chapter_5",
    coding_notes="Zoning Ordinance §§28-970.5.1 to 28-970.5.3 (history: Ord. No. 2023-969, § 1, 11-7-23): 'All accessory dwelling units must conform to the following standards'; one ADU and one bedroom per lot; owner's recorded affidavit that the owner occupies the main or accessory unit, and leasing both units is prohibited in single-family residence districts; size the greater of 500 sq ft or 30% of the main house (adu_max_sqft = 500, the floor every lot gets); detached allowed (10 ft separation, 5 ft side and 10 ft rear setbacks); height no more than the main house; one extra space. by_right left blank: the text does not say whether a permit beyond the building permit is needed. Effective date not found: coded as adoption. No ADU rule before 2023 was found in the text (§28-902: one principal residential structure per lot in R-E, R-1, R-2); the earlier status is not coded."
    + FLAG
    + ".",
)
mm_none(
    "4876000",
    2010,
    "One principal residential structure per zoning lot in the R-E, R-1 and R-2 single-family districts",
    FLOOR,
    Z + "waco-TX/chapter_5",
    "§28-902(a): 'not more than one principal residential structure shall be located on a zoning lot' in R-E, R-1 or R-2 (Ord. 1986-49, 1987-3, 2008-037, 2016-174). Whether a two-family structure is a permitted principal use in these districts was not read (Ch. 4 use lists).",
    coverage="Single-family districts R-E, R-1, R-2",
)

# ---- Midland (4848072) -----------------------------------------------------------------------------------
adu_none(
    "4848072",
    2019,
    "Development Code §11-1-4.09: one accessory dwelling unit per tract, up to 1,000 sq ft or 30% of the main house, but it may not be leased or rented",
    "2019-05-28",
    Z + "midland-TX/chapter_5",
    "§11-1-4.09(C)(1)(a): 'Accessory Dwelling Units shall not be leased or rented'; (D)(9): not sold or leased separately; (C)(1)(b) living area the lesser of 1,000 sq ft or 30% of the main house; (C)(1)(c) one per tract. The use chart marks ADUs 'S-1' in five residential columns (the marker is not defined in the text read). Not rentable, so coded none. History: Ordinance 9920 (Exh. A), adopted 2019-05-28 (the Development Code); the rule before 2019 was not read.",
)

# ---- College Station (4815976) ---------------------------------------------------------------------------
row(
    reform_id="TX-4815976-adu-2023",
    theme="adu",
    jurisdiction_geoid="4815976",
    component="UDO §6.5.B.7: accessory living quarters allowed with single-family use, owner lives on site, one per building plot, at most two unrelated people, one extra parking space; accessory uses together up to 25% of the main house's habitable area or 400 sq ft",
    adoption_date="2023-08-10",
    effective_date="2023-08-10",
    owner_occ=True,
    adu_max_sqft=400,
    adus_per_lot=1,
    parking="one additional off-street space",
    parking_min_per_unit=1,
    coverage="Areas zoned and used for single-family residential use",
    source_url=Z + "college-station-TX/chapter_6",
    coding_notes="UDO Art. 6 §6.5.B.7 ('Living Quarters'): 'In areas zoned and used for single-family residential use, accessory living quarters are allowed subject to the following': (a) 'The property owner resides on-site and uses the subject property as their primary residence'; (b) one per building plot; (c) 'No more than two (2) unrelated persons'; (d) one additional off-street space. §6.5.B.1 caps all accessory uses together at 25% of the main house's habitable area or 400 sq ft, whichever is greater (adu_max_sqft = 400, the floor). Not in the use table; allowed as an accessory use (§6.5.A), so by_right left blank. Rental of the quarters not addressed. Dated by the history note (Ord. No. 2023-4453, 2023-08-10), which looks like a recodification of the whole article: the provision may be older. CHECK before using as a D-025 event."
    + FLAG
    + ".",
)

# ---- Round Rock (4863500) --------------------------------------------------------------------------------
row(
    reform_id="TX-4863500-adu-2020",
    theme="adu",
    jurisdiction_geoid="4863500",
    component="Zoning use table (Sec. 2-25): 'Accessory Dwelling Unit, Connected' permitted only in SF-3; not in SF-R, SF-1, SF-2 or SF-D; no detached ADU use",
    adoption_date="2020-10-22",
    effective_date="2020-10-22",
    by_right=True,
    adu_detached_allowed=False,
    coverage="SF-3 only (connected ADU); none in SF-R, SF-1, SF-2, SF-D",
    coverage_zones="SF-3",
    source_url=Z + "round-rock-TX/chapter_2",
    coding_notes="Sec. 2-25 use table: 'Accessory Dwelling Unit, Connected' P in SF-3 and '-' in AG, SF-R, SF-1, SF-2, SF-D; Sec. 2-4(a)(5): 'Any use, structure, or improvement not specifically permitted is not allowed'. Standards (Sec. 2-91) not in the text read: size, owner occupancy and parking blank. Dated by the use table's history note (Ord. No. O-2020-0288, 2020-10-22); when SF-3 first allowed connected ADUs was not read."
    + FLAG
    + ".",
)
mm_none(
    "4863500",
    2010,
    "No duplex, triplex or fourplex use in the single-family districts (SF-R, SF-1, SF-2, SF-3, SF-D); two-unit buildings only in the TF district",
    FLOOR,
    Z + "round-rock-TX/chapter_2",
    "Sec. 2-25 use table: no two- to four-unit use in the single-family columns; 'Single-Family, Attached' P only in TH; Sec. 2-19 TF (two-family) is a separate district. Single-family district history Ord. O-2019-0203/0204/0463/0464 (2019), use table O-2020-0288 (2020-10-22).",
    coverage="Single-family districts SF-R, SF-1, SF-2, SF-3, SF-D",
)

# ---- Wichita Falls (4879000) -----------------------------------------------------------------------------
row(
    reform_id="TX-4879000-adu-2003",
    theme="adu",
    jurisdiction_geoid="4879000",
    component="Zoning §6515(E): one accessory dwelling unit as a residential accessory use where the principal use is single-family, on lots of 10,000 sq ft or more",
    adoption_date="2003-04-01",
    effective_date="2003-04-01",
    min_lot_sqft=10000,
    adus_per_lot=1,
    coverage="Lots of 10,000 sq ft or more with a single-family house",
    source_url=Z + "wichita-falls-TX/chapter_35",
    coding_notes="§6515: accessory uses 'shall be allowed on the same lot or site containing a residential use', including (E) 'A single accessory dwelling unit when the principal use is single-family residential on a lot over 10,000 square feet or greater'. History: Ordinance 24-2003, sec. 1, adopted 2003-04-01. No conditional permit named, but by_right left blank (district chapters not read). Size cap, rental, owner occupancy and parking not in the text. Rule predates the window (rule_age from 2003)."
    + FLAG
    + ".",
)

# ---- Sugar Land (4870808) --------------------------------------------------------------------------------
adu_none(
    "4870808",
    2010,
    "Development Code §2-193: a dwelling may not be leased in part, house more than one family, or have more than one kitchen or meter; no ADU use",
    FLOOR,
    Z + "sugar-land-TX/chapter_4",
    "§2-193(C)(3): 'The family occupying the Dwelling Unit may not lease or rent any portion of the Dwelling to another person'; (A)(2) one family per dwelling unit; (B)(1) one interior kitchen; (B)(3) one water or electric meter; (A)(1) one single-family detached dwelling per platted lot. No ADU, guest house or garage apartment use in the text read (§2-192 accessory structures; history Ord. 2149 (2019-02-19) to Ord. 2339 (2024-06-06)). The use table (§2-71) was not in the text. §2-193 has no history note: coded at 2010-01-01.",
)

# ---- Richardson (4861796) --------------------------------------------------------------------------------
adu_none(
    "4861796",
    2010,
    "R-1500-M district: servants' quarters permitted as a detached accessory building; no ADU or guest house use",
    FLOOR,
    Z + "richardson-TX/chapter_4",
    "Zoning Ordinance Art. IV (R-1500-M) Sec. 1(k): 'Servants' quarters' among the permitted uses (Sec. 2(b)(2): 'detached garages or servants' quarters'); Sec. 1(j) rental rooms inside the house for at most two renters. Servants' quarters are housing for household employees, not a rentable ADU (the convention of tx_adu_rows.py). Only R-1500-M was read; the other single-family districts are assumed to follow the same pattern. Sec. 1 history from Ord. 871-A (1973) to Ord. 4590 (2026-06-15): what the 2026 amendment changed was not read.",
    coverage="Single-family district R-1500-M (others assumed the same)",
)
mm_none(
    "4861796",
    2010,
    "R-1500-M district: single-family detached dwellings only",
    FLOOR,
    Z + "richardson-TX/chapter_4",
    "Art. IV Sec. 1 permits 'Single-family detached dwellings' as the only dwelling use in R-1500-M. Other single-family districts not read.",
    coverage="Single-family district R-1500-M (others not read)",
)

# ---- Abilene (4801000) -----------------------------------------------------------------------------------
mm_none(
    "4801000",
    2010,
    "Land Development Code: one dwelling unit per lot in RS-12, RS-8, RS-6, PH, RR and AO, except accessory dwelling units",
    "2010-04-22",
    Z + "abilene-TX/chapter_2",
    "§2.3.2.3(d), 2.3.2.4(d), 2.3.2.5(d), 2.3.2.6(e): 'There shall be a maximum of one (1) dwelling unit per lot, with the exception of accessory dwelling units'; up to four units only in the MD district (§2.3.2.8). History: Ord. No. 8-2010 (Exh. A), 2010-04-22 (the LDC). The ADU exception's standards (Land Use Matrix and Art. 4 Div. 4) were not in the text read: no ADU row (todo).",
    coverage="Single-family districts RS-12, RS-8, RS-6, PH, RR, AO",
)

# ---- Edinburg (4822660) ----------------------------------------------------------------------------------
mm_none(
    "4822660",
    2022,
    "UDC Table 2.202-1: duplex and multiplex prohibited in the RS, RP and RU single-family districts (permitted only in RM and UU)",
    "2022-08-09",
    Z + "edinburg-TX/chapter_3",
    "Table 2.202-1 (Residential and Agricultural Uses): Duplex/Multiplex '--' (prohibited) in RS, RP, RU; P in RM and UU; L in DT. 'Twin House' is P in RU (not defined in the text read; may be two attached single-family houses on separate lots, so not coded as 2 units). Sections show 'Effective on: 8/9/2022' (the UDC); the earlier code was not read.",
    coverage="Single-family districts RS, RP, RU",
)

# ---- League City (4841980) -------------------------------------------------------------------------------
row(
    reform_id="TX-4841980-missing_middle-2020",
    theme="missing_middle",
    jurisdiction_geoid="4841980",
    component="UDC Sec. 125-3.3.3(a): duplexes (with zero-lot-line houses and townhouses) permitted in the RSF-2 small-lot single-family district only",
    adoption_date="2020-09-29",
    effective_date="2020-09-29",
    unit_cap=2,
    coverage="RSF-2 only (2,000 sq ft lots); RSF-20, RSF-10, RSF-7, RSF-5 one dwelling",
    coverage_zones="RSF-2",
    source_url=Z + "league-city-TX/chapter_3",
    coding_notes="Sec. 125-3.3.3(a): 'Zero-lot line, duplexes and townhouses are permitted in the RSF-2 districts'; no other single-family district lists duplexes; Sec. 125-3.3.1: development 'must remain single family residential in nature'. by_right blank: 'permitted' is not tied to an approval type in the text read. History: Ord. No. 2020-25 (Exh. A), 2020-09-29 (the UDC); whether RSF-2 allowed duplexes before was not read, so this may not be an adoption: CHECK before using as a D-024 event. ADU rules (Sec. 125-3.14) not in the text read (todo)."
    + FLAG
    + ".",
)


def main() -> None:
    with PATH.open(newline="") as f:
        existing = list(csv.DictReader(f))
    by_id = {r["reform_id"]: r for r in existing}
    for r in ROWS:
        full = {c: r.get(c, "") for c in COLS}
        if r["reform_id"] in by_id:
            by_id[r["reform_id"]].update(full)
        else:
            existing.append(full)
            by_id[r["reform_id"]] = full
    with PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(existing)
    print(f"{len(ROWS)} rows written -> {PATH}")


if __name__ == "__main__":
    main()
