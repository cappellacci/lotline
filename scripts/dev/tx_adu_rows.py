# ruff: noqa: E501  (coding data: long source URLs and notes)
"""ADU rules for the 20 largest Texas places (2020 population) -> config/reforms/tx.csv.

Run from the repo root: `uv run python scripts/dev/tx_adu_rows.py`. Rows are written by `reform_id`: a new id is
appended, an existing id is replaced, and `UPDATES` fills fields on rows coded earlier. Rerunning is safe.

Coding conventions (WS-TX, 2026-10-20; see the PR and the logbook fragment):
- A place whose code allows no rentable ADU in single-family zones gets an explicit row with `adus_per_lot = 0`
  (read as "none" by `lotline.model.scenarios.adu.current_rules`). That includes units allowed only through a
  rezoning, SUP or board case, and units that may not be rented or used as a separate home (guest, family or
  servants' quarters).
- `adu_max_sqft` is the cap every eligible lot gets; a cap that is only a share of the main house is left blank
  and described in `coding_notes`.
- A rule documented as in force before 2010 whose adoption date was not found is coded `effective_date =
  2010-01-01` (start of the study window) and says so; its `rule_age` is then a lower bound.
- Every source URL was opened. Facts read only on a third-party code mirror (zoneomics.com) or in secondary
  sources because the city site or official publisher blocked automated access are flagged for a second coder.
"""

import csv
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "config" / "reforms" / "tx.csv"
COLS = next(csv.reader(PATH.open()))
ROWS: list[dict] = []
UPDATES: dict[str, dict] = {}
FLOOR = "2010-01-01"
FLAG = " FLAG for second coder: "


def row(**kw):
    base = {
        "state": "TX",
        "theme": "adu",
        "status": "in_force",
        "coder": "claude",
        "coder_agreement": "single_coder",
    }
    base.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
    unknown = set(base) - set(COLS)
    assert not unknown, unknown
    ROWS.append(base)


def none_row(
    geoid, year, component, effective, sources, notes, adoption=None, coverage="Single-family districts"
):
    """A place whose code allows no ADU in single-family zones: coded explicitly, adus_per_lot = 0."""
    row(
        reform_id=f"TX-{geoid}-adu-{year}",
        jurisdiction_geoid=geoid,
        component=component,
        adoption_date=adoption,
        effective_date=effective,
        by_right=False,
        adus_per_lot=0,
        coverage=coverage,
        source_url=sources,
        coding_notes="NO ADU RULE (adus_per_lot = 0): " + notes,
    )


# ---- Austin (4805000) -------------------------------------------------------------------------------------
row(
    reform_id="TX-4805000-adu-2015",
    jurisdiction_geoid="4805000",
    component="Ord. 20151119-080: ADU (second dwelling unit, two-family residential use) rules eased in SF-3: "
    "minimum lot 7,000 -> 5,750 sq ft, size cap 850 -> the smaller of 1,100 sq ft or 15% of lot area, one parking "
    "space (was two) and none within 1/4 mile of an activity corridor, no separate driveway, 10 ft separation",
    adoption_date="2015-11-19",
    effective_date="2015-11-19",
    by_right=True,
    owner_occ=False,
    min_lot_sqft=5750,
    adu_max_sqft=862,
    adu_detached_allowed=True,
    adus_per_lot=1,
    parking="one off-street space required (was two); none within 1/4 mile of an activity corridor",
    parking_min_per_unit=1,
    coverage="SF-3 and less restrictive districts, lots of at least 5,750 sq ft; not SF-1 or SF-2",
    coverage_zones="SF-3",
    source_url="https://austinmonitor.com/stories/2015/11/council-loosens-rules-accessory-dwelling-units/; "
    "https://udspace.udel.edu/bitstreams/32c1ebbd-97a2-4377-b5ba-4cab72dfb073/download",
    coding_notes="Council vote 7-4 on 2015-11-19 (Austin Monitor, 2015-11-20). Ordinance number 20151119-080 and the "
    "list of changes from a University of Delaware thesis citing the ordinance; the ordinance text itself was not "
    "opened (library.municode.com returns 403 to automated access: FLAG for second coder). Effective date not found: "
    "coded as the vote date. adu_max_sqft = 862: the cap every eligible lot gets (15% of a 5,750 sq ft lot; 1,100 sq ft "
    "on lots of 7,334+ sq ft). Owner occupancy not required; ADUs built after 2015-10-01 may be short-term rentals at "
    "most 30 days a year. By right: the use is permitted in SF-3 (no conditional approval).",
    supersedes="TX-4805000-adu-2010",
)
row(
    reform_id="TX-4805000-adu-2010",
    jurisdiction_geoid="4805000",
    component="Secondary apartment / second dwelling unit in SF-3 before Ord. 20151119-080: lots of 7,000+ sq ft, "
    "up to 850 sq ft, two parking spaces, own driveway",
    effective_date=FLOOR,
    by_right=True,
    owner_occ=False,
    min_lot_sqft=7000,
    adu_max_sqft=850,
    adu_detached_allowed=True,
    adus_per_lot=1,
    parking="two off-street spaces and a separate driveway",
    parking_min_per_unit=2,
    coverage="SF-3 and less restrictive districts, lots of at least 7,000 sq ft; not SF-1 or SF-2",
    coverage_zones="SF-3",
    source_url="https://udspace.udel.edu/bitstreams/32c1ebbd-97a2-4377-b5ba-4cab72dfb073/download; "
    "https://austinmonitor.com/stories/2015/11/council-loosens-rules-accessory-dwelling-units/",
    coding_notes="Rule in force before 2015 as listed (old value -> new value) in the thesis summary of Ord. "
    "20151119-080; the thesis also says ADUs were historically permitted in SF-3 but not SF-1/SF-2. Adoption date "
    "not found: coded at the start of the study window (2010-01-01), so rule_age is a lower bound.",
)
row(
    reform_id="TX-4805000-adu-2023",
    jurisdiction_geoid="4805000",
    component="Citywide elimination of minimum parking requirements applied to ADUs (no parking space required)",
    adoption_date="2023-11-02",
    effective_date="2023-11-02",
    supersedes="TX-4805000-adu-2015",
    parking="no minimum (citywide parking minimums eliminated)",
    parking_min_per_unit=0,
    coverage="Citywide, except Hyde Park, North Hyde Park, North University and Fairview Park (kept their minimums)",
    source_url="https://communityimpact.com/north-central-austin/development/austin-eliminates-parking-requirements-for-new-developments/",
    coding_notes="ADU view of TX-4805000-parking-2023 so the ADU rule carries the parking change (blank fields inherit "
    "from TX-4805000-adu-2015). Vote 8-2 on 2023-11-02; effective date not found, coded as the vote date.",
)
row(
    reform_id="TX-4805000-adu-2024",
    jurisdiction_geoid="4805000",
    component="HOME phase 1 (Ord. 20231207-001): second and third homes on SF-1, SF-2 and SF-3 lots as two- and "
    "three-unit residential uses; the secondary-apartment use, ADU maximum size and 10 ft separation removed",
    adoption_date="2023-12-07",
    effective_date="2024-02-05",
    supersedes="TX-4805000-adu-2023",
    by_right=True,
    owner_occ=False,
    adu_max_sqft=2300,
    adu_detached_allowed=True,
    adus_per_lot=2,
    parking="no minimum",
    parking_min_per_unit=0,
    coverage="Citywide, lots zoned SF-1, SF-2 and SF-3 (minimum lot 5,750 sq ft until HOME phase 2)",
    coverage_zones="SF-1;SF-2;SF-3",
    source_url="https://aiaaustin.org/wp-content/uploads/2024/01/HOME_Summary-FAQ_20240126-1039.pdf; "
    "https://www.austintexas.gov/development-services/home-amendments",
    coding_notes="AIA Austin ordinance summary (2024-01-26): Duplex, Two-Unit and Three-Unit Residential uses allowed "
    "on SF-1/2/3 lots make 'Two-Family, Accessory Apartments' redundant; maximum ADU size and 10 ft separation "
    "removed. adu_max_sqft = 2,300: inside the Subchapter F boundary any single new unit may reach the greater of "
    "0.4 FAR or 2,300 sq ft; outside it there is no FAR limit. One unit of a duplex or two-unit use may not be a "
    "short-term rental more than 30 days a year. Same effective date convention as TX-4805000-missing_middle-2024 "
    "(applications from 2024-02-05). HOME does not override deed restrictions, HOAs or NCCDs.",
)

# ---- Houston (4835000): no zoning; second dwelling units under Ch. 42 / Ch. 26 ---------------------------------
row(
    reform_id="TX-4835000-adu-2010",
    jurisdiction_geoid="4835000",
    component="Secondary dwelling unit (Ch. 42/26 before Livable Places): one detached unit up to 900 sq ft on a "
    "single-family lot, one parking space",
    effective_date=FLOOR,
    owner_occ=False,
    adu_max_sqft=900,
    adu_detached_allowed=True,
    adus_per_lot=1,
    parking="one parking space for a secondary dwelling unit of up to 900 sq ft",
    parking_min_per_unit=1,
    coverage="Citywide (no zoning); active deed restrictions can forbid a second unit",
    source_url="https://houstontx.gov/planning/docs_pdfs/LP_Meeting%20Notes_08.10%20Rev.pdf; "
    "https://www.houstontx.gov/planning/Commissions/docs_pdfs/Livable%20Places_Chapter%2026%20amend.%20Ord.%202023-802_Approved.pdf",
    coding_notes="Livable Places committee notes (2021-08-10): ADUs 'are already allowed today', only detached, one "
    "per lot, 900 sq ft; staff not proposing owner occupancy. Ord. 2023-802 strikes the old Ch. 26 text 'a secondary "
    "dwelling unit not larger than 900 square feet of GFA shall provide 1.0 parking space'. Ordinance that first set "
    "the 900 sq ft rule not found: coded at the start of the study window (2010-01-01), rule_age a lower bound. "
    "by_right left null: no zoning approval is needed, but deed restrictions can forbid the unit.",
)
UPDATES["TX-4835000-adu-2023"] = {
    "supersedes": "TX-4835000-adu-2010",
    "owner_occ": "False",
    "adu_detached_allowed": "True",
    "adus_per_lot": "1",
    "parking": "none for a second dwelling unit of up to 1,000 sq ft; one space for 1,001-1,500 sq ft",
    "parking_min_per_unit": "0",
    "source_url": "https://www.houstontx.gov/planning/pressrelease-20230927.html; "
    "https://www.houstontx.gov/planning/Commissions/docs_pdfs/Livable%20Places_Chapter%2026%20amend.%20Ord.%202023-802_Approved.pdf; "
    "https://www.houstontx.gov/planning/Commissions/chapter42.html",
    "coding_notes": "by_right left null: Houston has no zoning, so no zoning approval is needed, but deed "
    "restrictions can forbid ADUs. Added 2026-10-20 (WS-TX): Ord. 2023-801 (Ch. 42) and 2023-802 (Ch. 26), passed "
    "2023-09-27, effective 12:01 a.m. 2023-11-27 (Ord. 2023-802 signature page; city Ch. 42 page). Ch. 26 §26-492: "
    "no extra space for a second dwelling unit of 1,000 sq ft or less, one for 1,001-1,500 sq ft; "
    "parking_min_per_unit = 0 is what every lot gets for a unit up to 1,000 sq ft. No owner-occupancy rule found "
    "(2021 committee notes). One unit per lot, detached (garage apartment or separate structure)."
    + FLAG
    + "the Ch. 42 text (Ord. 2023-801) was not opened (PDF timed out; municode 403).",
}

# ---- San Antonio (4865000) ---------------------------------------------------------------------------------
row(
    reform_id="TX-4865000-adu-2001",
    jurisdiction_geoid="4865000",
    component="UDC §35-371 accessory dwellings (from 2001): one per lot by accessory dwelling permit, owner occupancy, "
    "up to 800 sq ft (300 sq ft minimum and 40% of the main house footprint for detached units), one bedroom",
    effective_date="2001-01-01",
    by_right=True,
    owner_occ=True,
    adu_max_sqft=800,
    adu_detached_allowed=True,
    adus_per_lot=1,
    coverage="Single-family districts other than FR (1,200 sq ft in RE)",
    source_url="https://dallascityhall.com/departments/sustainabledevelopment/planning/DCH%20Documents/ADU/ADU_ZOAC_CaseReport-10.1.2020_FINAL.pdf",
    coding_notes="Secondary source: Dallas ZOAC case report (2020-10-01, pp. 7-8) quotes San Antonio UDC §35-371 as "
    "then in force and says the city 'has allowed ADUs since 2001'. effective_date is year-only (2001-01-01); the "
    "2001 ordinance number and any 2010-2022 amendments were not found. Must connect to the main house's utilities; "
    "at most 3 occupants; the owner may not take rent for the unit they occupy. Parking: the report says parking "
    "rules exist (parking behind the front yard) but no space count, so parking is left blank."
    + FLAG
    + "sanantonio.gov refused the connection and municode returns 403; check §35-371 history notes.",
)
UPDATES["TX-4865000-adu-2023"] = {"supersedes": "TX-4865000-adu-2001"}

# ---- Dallas (4819000): none ------------------------------------------------------------------------------------
none_row(
    "4819000",
    2018,
    "No by-right ADU: a rentable ADU needs a Board of Adjustment special exception (owner occupancy deed "
    "restriction) or a neighborhood ADU overlay rezoning (Ords. 30930, 30931); a non-rental 'additional dwelling "
    "unit' also needs a special exception",
    "2018-06-27",
    "https://dallascityhall.com/departments/pnv/Pages/Accessory_Dwelling_Units.aspx; "
    "https://dallascityhall.com/departments/sustainabledevelopment/planning/DCH%20Documents/ADU/ADU_ZOAC_CaseReport-10.1.2020_FINAL.pdf; "
    "https://dallascityhall.com/government/Boards-and-Commissions/Board-of-Adjustment/Documents/BOA%20Panel%20A%20Minutes%2005.19.26.pdf",
    "the city ADU page says ADUs 'are not allowed to be built by right in most cases'. Routes: §51A-4.209(b)(6)(E) "
    "board special exception (non-rental, deed-restricted; or rentable with an owner-occupancy deed restriction and "
    "possible extra parking) and the §51A-4.510(c) ADU overlay (neighborhood petition, CPC and Council). Rentable "
    "terms where granted: 700 sq ft or 25% of the main house, whichever is greater; one parking space unless within "
    "1,200 ft of a DART stop. 2 rentable ADUs granted 2018-2020. Framework adopted 2018-06-27 (Ords. 30930/30931, "
    "from the city page's file names; effective date not found, coded as the adoption date). Before 2018 only the "
    "non-rental special exception existed (adoption date not found). The 2020 by-right proposal (DCA190-007) was "
    "held by ZOAC on 2020-10-01 and suspended; no by-right ordinance found through the 2026-05-19 board minutes."
    + FLAG
    + "§51A-4.209 and §51A-4.510 on amlegal returned 403.",
    adoption="2018-06-27",
    coverage="Single-family districts (R-1ac(A) to R-5(A)); a board case or an overlay rezoning is needed",
)
# Added 2026-10-26 (WS-TX): the rule before the 2018 framework, so Dallas has a dated rule for 2010-2017 too.
none_row(
    "4819000",
    2010,
    "Before the 2018 framework: only a non-rental 'additional dwelling unit' by Board of Adjustment special "
    "exception; no rentable ADU",
    FLOOR,
    "https://dallascityhall.com/departments/pnv/Pages/Accessory_Dwelling_Units.aspx; "
    "https://dallascityhall.com/departments/sustainabledevelopment/planning/DCH%20Documents/ADU/ADU_ZOAC_CaseReport-10.1.2020_FINAL.pdf",
    "from the sources of TX-4819000-adu-2018 (read 2026-10-20): 'Before 2018 only the non-rental special exception "
    "existed'; its adoption date was not found, so the row starts at the study window (2010-01-01) and rule_age is "
    "a lower bound. Added so Dallas has a dated rule for every panel year (D-025 leaves out place-years with no "
    "dated rule)." + FLAG + "§51A-4.209 on amlegal returned 403.",
    coverage="Single-family districts; non-rental additional dwelling units by special exception only",
)
next(r for r in ROWS if r["reform_id"] == "TX-4819000-adu-2018")["supersedes"] = "TX-4819000-adu-2010"

# ---- Fort Worth (4827000): none -----------------------------------------------------------------------------
none_row(
    "4827000",
    2010,
    "Accessory dwelling allowed in one-family districts only when not rented or used as a separate residence "
    "(habitable accessory structure, Zoning Ordinance §5.301)",
    FLOOR,
    "https://www.fortworthtexas.gov/files/assets/public/v/2/communications/documents/city-council-presentations/2024/04-02-2024/presentation-on-congregate-living.pdf; "
    "https://www.fortworthtexas.gov/files/assets/public/v/4/city-secretary/documents/calendar/2025-agendas/bampc/boa/08-20-2025-revised-residential-board-of-adjustment-agenda.pdf",
    "city council presentation (2024-04-02, slide 10): in A-2.5A, A-43, A-21, A-10, A-7.5, A-5 and AR an accessory "
    "dwelling unit is allowed 'when not rented or used as a separate residence' and prohibited when rented or used "
    "as one, so it is not a rentable ADU. No ADU change found 2010-2026 (the 2023 housing strategy's ADU proposal "
    "was paused; Ord. 28525-05-2026, SB 15 small lots, does not touch ADUs). Adoption of the current §5.301 text not "
    "found: coded at 2010-01-01." + FLAG + "§5.301 on amlegal returned 403 (size cap and exact wording).",
    coverage="One-family districts A-2.5A, A-43, A-21, A-10, A-7.5, A-5, AR",
)

# ---- El Paso (4824000): partial ------------------------------------------------------------------------------
row(
    reform_id="TX-4824000-adu-2011",
    jurisdiction_geoid="4824000",
    component="Title 20 §20.10.035 accessory dwelling units: permitted accessory use in all R and A districts, one "
    "per single-family lot, up to 800 sq ft, one bedroom, owner occupancy, one parking space, 5,500 sq ft minimum lot",
    adoption_date="2011-04-19",
    effective_date="2011-04-19",
    by_right=True,
    owner_occ=True,
    min_lot_sqft=5500,
    adu_max_sqft=800,
    adu_detached_allowed=True,
    adus_per_lot=1,
    parking="one off-street space",
    parking_min_per_unit=1,
    coverage="All residential (R) and apartment (A) districts, lots with a single-family house; detailed site plan "
    "approval in special purpose districts",
    source_url="https://www2.elpasotexas.gov/municipal-clerk/agenda/03-29-11/03291105B.pdf; "
    "https://www2.elpasotexas.gov/municipal-clerk/agenda/04-19-11/04191108A.pdf; "
    "https://elpasomatters.org/2025/08/19/el-paso-city-council-casitas-accessory-dwelling-units-zoning-changes/; "
    "https://www.elpasotexas.gov/planning-and-inspections/faqs",
    coding_notes="Ordinance text from the 2011 council agendas (introduced 2011-03-29, on the 2011-04-19 agenda): "
    "'permitted accessory use (A) in all residential (R) and apartment (A) zoning districts'; owner must occupy the "
    "principal unit or the ADU. Ordinance number and adoption date not found: coded as the 2011-04-19 agenda date. "
    "Parking (one space) from El Paso Matters 2025-08-19, which also reports the council voted 5-3 that day to drop "
    "a package that would have removed owner occupancy and parking and allowed 800-1,200 sq ft; no later adoption "
    "found. A search snippet says the current code allows 1,200 sq ft on lots of 8,000+ sq ft (not verified; "
    "amendment not found). A 2019 amendment (introduced 2019-08-06, HB 2439 design rules) does not change these "
    "fields." + FLAG + "current §20.10.035 not opened (municode 403, elaws mirror timed out).",
)

# ---- Arlington (4804000): none ---------------------------------------------------------------------------------
none_row(
    "4804000",
    2014,
    "UDC (Ord. 14-039): 'secondary living unit' only for family members or relatives and never rented or leased; "
    "by right in RE, RS-20, RS-15 and VG, SUP in RS-7.2, RS-5 and RM-12; garage apartments not in single-family "
    "districts",
    "2014-06-24",
    "https://www.arlingtontx.gov/files/assets/city/v/8/city-secretary/documents/city-code-of-ordinances/unified-development-code-chapter.pdf",
    "UDC §12.3.5.N defines the secondary living unit as 'only for use by family members or relatives' that 'shall "
    "not be rented or leased', so it is not a rentable ADU. Table 3.3-1: P* in RE, RS-20, RS-15, VG; S* (SUP) in "
    "RS-7.2, RS-5, RM-12. §3.3.6.L: one bedroom, kitchen and bath, exempt from parking; detached accessory "
    "structures up to 50% of the main house (§3.3.6.A). STR permits possible inside the entertainment-district STR "
    "zone (§3.4.5, Ord. 19-014). Read in the UDC as amended by Ord. 25-059 (2025-08-26); the history list shows no "
    "amendment naming secondary living units. effective_date = UDC adoption (2014-06-24); the 1987 zoning chapter's "
    "rule was not found.",
    adoption="2014-06-24",
    coverage="Single-family districts RE, RS-20, RS-15 (by right) and RS-7.2, RS-5 (SUP); family members only",
)

# ---- Plano (4858016): partial ------------------------------------------------------------------------------
row(
    reform_id="TX-4858016-adu-2019",
    jurisdiction_geoid="4858016",
    component="Backyard cottages (Zoning Ordinance §15.1800) extended from the Estate Development district to most "
    "residential districts: owner occupancy, one extra parking space, 6,000 sq ft minimum lot",
    adoption_date="2019-02-25",
    effective_date="2019-02-25",
    by_right=True,
    owner_occ=True,
    min_lot_sqft=6000,
    adu_detached_allowed=True,
    adus_per_lot=1,
    parking="at least one additional off-street space",
    parking_min_per_unit=1,
    coverage="Most residential districts (district list not confirmed); before 2019 only the Estate Development "
    "district (141 homes)",
    source_url="https://communityimpact.com/dallas-fort-worth/city-county/2019/04/19/thousands-of-plano-homes-now-eligible-to-add-backyard-cottage/; "
    "https://www.planocompplan.org/DocumentCenter/View/5220/Plano-Zoning-and-Subdivision-Ordinance-Rewrite-Diagnostic-Report; "
    "https://plano.novusagenda.com/agendapublic/AttachmentViewer.ashx?AttachmentID=19006&ItemID=9200",
    coding_notes="Council approved 2019-02-25 (Community Impact; ordinance 2019-2-10 / ZC 2018-033 per a search "
    "snippet, not opened); effective date not found, coded as the vote date. One unit must be owner-occupied, either "
    "may be rented long term; 6,000 sq ft minimum lot; one extra parking space. The 2024 diagnostic report calls "
    "cottages 'by-right in most residential districts'. Size: search snippets of the city fact sheet say 1,100 sq ft "
    "or 50% of the main house, whichever is smaller, minimum 400 sq ft (not opened: left blank). ZC 2024-008 "
    "(2024-04-22) counts cottage and house as one short-term rental. The ED-only rule before 2019 is not coded "
    "(adoption date not found)."
    + FLAG
    + "plano.gov and the civicplus fact sheet returned 403 (§15.1800 text).",
)

# ---- Lubbock (4845000): partial ---------------------------------------------------------------------------------
row(
    reform_id="TX-4845000-adu-2023",
    jurisdiction_geoid="4845000",
    component="Unified Development Code (Ch. 39): accessory dwelling units as a limited use in RE, SF-1, SF-2 and MDR "
    "with owner occupancy, one extra parking space, outbuildings up to 750 sq ft of habitable space",
    adoption_date="2023-05-09",
    effective_date="2023-10-01",
    by_right=True,
    owner_occ=True,
    adu_max_sqft=750,
    adu_detached_allowed=True,
    parking="one space in addition to the spaces required for the residential use",
    parking_min_per_unit=1,
    coverage="RE, SF-1, SF-2 and MDR districts; mixed-use districts with house, duplex or multiplex building types",
    coverage_zones="RE;SF-1;SF-2;MDR",
    source_url="https://www.zoneomics.com/code/lubbock-TX/chapter_3",
    coding_notes="Read on the zoneomics mirror of Ch. 39 Art. 39.03: the House type 'may share an accessory dwelling "
    "unit in the backyard'; outbuildings of House, Duplex and Multiplex types up to two stories and 750 sq ft of "
    "habitable space; Table 39.03.009-2 requires 1 space for an ADU in addition to the residential use. Section "
    "history: Ord. 2023-O0054 (adopted 2023-05-09), amended Ord. 2025-O0095 (2025-08-18). Districts and owner "
    "occupancy (§39.02.020(c): 'permitted on a parcel where the owner of the property lives in either the primary or "
    "accessory unit') are from search snippets only. UDC effective 2023-10-01 per a secondary aggregator (not "
    "verified). The pre-UDC garage-apartment rule was not found and is not coded."
    + FLAG
    + "ecode360 and mylubbock.us returned 403; check §39.02.020(c) and the use table.",
)

# ---- Irving (4837000): none ----------------------------------------------------------------------------------
none_row(
    "4837000",
    2010,
    "Guest and servants' quarters in R-40 to R-6 and R-ZLa only through an S-P-1 site plan rezoning, not for rent",
    FLOOR,
    "https://www.zoneomics.com/code/irving-TX/chapter_2; https://www.zoneomics.com/code/irving-TX/chapter_9; "
    "https://www.zoneomics.com/code/irving-TX/chapter_1",
    "UDC §2.4.4-2.4.8(b)(2) and §2.4.9(b)(3): guest and servants' quarters 'may be permitted as an accessory use... "
    "upon such accessory use being approved as an S-P-1 site plan district' (a rezoning), and in R-40 to R-6 only if "
    "not 'a source of income'. Definitions (§9.3): guest quarters 'not for rent or permanent occupancy'; servants' "
    "quarters for persons employed on the premises, not for rent, no separate meter. The UDC replaced Ord. 1144 "
    "(1964) around 2020 (adopting ordinance not found); the older text was not read, so 2010-01-01 is a floor."
    + FLAG
    + "ecode360 (official publisher), irvingtx.gov and municode returned 403; read on the zoneomics mirror.",
    coverage="Single-family districts R-40, R-15, R-10, R-7.5, R-6, R-ZLa",
)

# ---- Laredo (4841464): none ----------------------------------------------------------------------------------
none_row(
    "4841464",
    1992,
    "One dwelling per lot in R-1 (Ord. 92-0-75), R-1B and R-1-MH; RS allows only attached servants' quarters or "
    "guest quarters",
    "1992-04-06",
    "https://www.zoneomics.com/code/laredo-TX/chapter_6; https://www.zoneomics.com/code/laredo-TX/chapter_9",
    "Land Development Code §24-65.3 (R-1): 'Only one (1) dwelling per lot' (as amended by Ord. 92-0-75, "
    "1992-04-06); §24-65.9 (R-1B, Ord. 2023-O-055): one single-family dwelling per lot; §24-65.6 (R-1-MH): one unit "
    "per lot. RS (§24-65.2) allows servants' quarters as part of the main structure and detached guest quarters "
    "(rental and size rules not found); R-3 allows a second dwelling only for a relative and not for rental income. "
    "The use chart marks by district did not survive extraction. ReCode Laredo (rewrite) status not verified."
    + FLAG
    + "cityoflaredo.com and municode returned 403; read on the zoneomics mirror.",
    adoption="1992-04-06",
    coverage="Single-family districts R-1, R-1A, R-1B, R-1-MH (RS: guest quarters only)",
)

# ---- Garland (4829000): none ---------------------------------------------------------------------------------
none_row(
    "4829000",
    2015,
    "Garland Development Code (Ord. 6773): guest houses only by SUP (AG, SF-E, SF-10, SF-7) and not for rent; "
    "rental units only by SUP in AG and SF-E",
    "2015-05-19",
    "https://www.zoneomics.com/code/garland-TX/chapter_5; https://garlandtx.new.swagit.com/videos/113514",
    "Staff at the 2021-03-01 council work session (item 4E): 'guest houses are permitted by SUP only in the AG, SF "
    "Estate, SF Ten and SF7 zoning districts, while rental units are permitted by SUP only in the AG and single "
    "family estate zoning districts'; the committee recommended no change. GDC §2.58 (Ord. 6773, 2015-05-19; "
    "amended Ords. 7079 and 7107, 2019): accessory dwellings may not be sold separately or sublet; accessory "
    "buildings together up to 30% of the main building (never less than 600 sq ft). effective_date = GDC adoption "
    "(2015-05-19); the earlier zoning ordinance was not read. No 2022-2026 ADU amendment found."
    + FLAG
    + "ecode360 returned 403 and garlandtx.gov refused the connection; GDC read on the zoneomics mirror.",
    adoption="2015-05-19",
    coverage="Single-family districts (SUP case by case)",
)

# ---- Frisco (4827684): partial --------------------------------------------------------------------------------
row(
    reform_id="TX-4827684-adu-2021",
    jurisdiction_geoid="4827684",
    component="Zoning Ordinance §4.20.03 garage apartment or guest house: incidental use on a lot with the main "
    "dwelling, not sold separately, may be rented only if the main dwelling is owner-occupied",
    adoption_date="2021-07-06",
    effective_date="2021-07-06",
    owner_occ=True,
    adu_detached_allowed=True,
    coverage="Single-family districts SF-16 to SF-7 (use-chart status by district not verified)",
    source_url="https://www.zoneomics.com/code/frisco-TX/chapter_4; https://www.zoneomics.com/code/frisco-TX/chapter_7; "
    "https://www.zoneomics.com/code/frisco-TX/chapter_2; https://www.zoneomics.com/code/frisco-TX/chapter_3",
    coding_notes="§4.20.03 (Ords. 19-10-83, 2019-10-01, and 2021-07-47, 2021-07-06): 'shall be allowed as an "
    "incidental use'; 'may be rented or offered for rent provided that the main dwelling unit is owner-occupied'. "
    "Definitions §7.51.01: garage apartment requires an owner-occupied main structure. Coded at the latest section "
    "amendment (2021-07-06) because what each amendment changed was not found; the base zoning ordinance (Ord. "
    "11-04-09, 2011) and earlier text were not read. by_right left null: the §3.02 use chart (P/SUP by district) "
    "could not be read. Size cap, units per lot and parking not found."
    + FLAG
    + "ecode360 and friscotexas.gov returned 403; read on the zoneomics mirror.",
)

# ---- Amarillo (4803000): none --------------------------------------------------------------------------------
none_row(
    "4803000",
    2010,
    "No ADU use: only detached servants' or caretakers' quarters for people employed on the premises, not for rent",
    FLOOR,
    "https://www.zoneomics.com/code/amarillo-TX/chapter_4; https://www.zoneomics.com/code/amarillo-TX/chapter_1",
    "Sec. 4-10-83(a)(16): servants or caretakers quarters 'used as living quarters for persons employed on the "
    "Premises only and not for rent or use as a separate Housing Unit'; no accessory dwelling, guest house or garage "
    "apartment use in the Sec. 4-10-82 accessory use schedule (last amended Ord. 8217, 2025-09-23; Sec. 4-10-83 "
    "Ord. 8115, 2024-02-13). Adoption of the quarters rule not found: coded at 2010-01-01."
    + FLAG
    + "district marks in the use schedule did not survive extraction; check on municode (403 to automated access).",
)

# ---- Grand Prairie (4830464): none ---------------------------------------------------------------------------
none_row(
    "4830464",
    2010,
    "UDC: accessory structures may not be used as a separate dwelling; no ADU use in single-family districts "
    "(accessory apartments only where duplexes are allowed)",
    FLOOR,
    "https://www.gptx.org/Departments/Planning-and-Development/Planning-Division/Unified-Development-Code; "
    "https://www.gptx.org/files/sharedassets/public/v/1/departments/planning/documents/article-04-09.01.26.pdf; "
    "https://www.gptx.org/files/sharedassets/public/v/1/departments/planning/documents/article-30-09.01.26.pdf; "
    "https://www.gptx.org/files/sharedassets/public/v/5/departments/planning/documents/article-06-09.02.25.pdf",
    "UDC Art. 4 §4.2.3: 'Accessory structures shall be prohibited from being used as a separate dwelling unit on a "
    "lot or tract of land that has or will have a dwelling unit situated on it'; the use chart has no ADU row; "
    "'Accessory Apartment' (Art. 30: 400 sq ft minimum, 35% of the house, owner occupancy, one space per adult) "
    "points to 2-Family/Duplex uses, allowed only in SF-A and 2F. Current texts: Ord. 11939-2026 (Art. 4, 30), Ord. "
    "11756-2025 (Art. 6). When §4.2.3 was adopted was not found: coded at 2010-01-01 (UDC dates from 1990).",
    coverage="Single-family districts SF-E, SF-1 to SF-6, SF-ZLL",
)

# ---- McKinney (4845744): none ----------------------------------------------------------------------------------
none_row(
    "4845744",
    2022,
    "UDC §205G(b) accessory dwelling unit: allowed in R43 to R3, TR1.8 and AP but may not be rented or leased "
    "separately from the main house",
    "2022-11-15",
    "https://zoningverdict.com/q/can-i-add-an-adu-mckinney-tx; "
    "https://mckinney.legistar.com/LegislationDetail.aspx?ID=6478853&GUID=B04E970F-373D-4892-AEE0-82D80AFCC7B5",
    "third-party summary of UDC §205G(b) and Table 2-26: permitted in R43, R12, R8, R6, R5, R3, TR1.8 and AP; up to "
    "50% of the main house (75% if the house is 1,200 sq ft or less); same ownership; 'cannot be rented or leased "
    "separately from the primary home'; no separate electric meter. The separate-rental ban makes it not a "
    "rentable ADU, so coded none; if the second coder reads the UDC as allowing rental, recode as partial "
    "(by right, detached, 50% cap, possibly one parking space). UDC adoption 2022-11-15 from a search snippet; "
    "ordinance number and effective date not found; a 2023 revision that widened eligibility (918 -> ~4,626 lots) "
    "was not found; the 2024-01-16 council work session (Legistar 24-1110) was a discussion only. The pre-UDC "
    "(Ch. 146) rule was not found."
    + FLAG
    + "all mckinneytexas.org pages and municode returned 403; nothing here is "
    "from primary code text.",
    adoption="2022-11-15",
    coverage="R43, R12, R8, R6, R5, R3, TR1.8, AP",
)

# ---- Brownsville (4810768): partial ------------------------------------------------------------------------
row(
    reform_id="TX-4810768-adu-2021",
    jurisdiction_geoid="4810768",
    component="UDC §4.4.4 accessory dwelling: by right in eleven residential and neighborhood districts, one per lot, "
    "may be rented, up to 50% of the main house's living area, one parking space",
    effective_date="2021-03-31",
    by_right=True,
    owner_occ=False,
    adu_detached_allowed=True,
    adus_per_lot=1,
    parking="one space per dwelling unit",
    parking_min_per_unit=1,
    coverage="AG, RE, R-1, R-2, R-3, TN, TN-MU, TN-C, DE, DG, DC (district list from a third-party summary)",
    source_url="https://www.zoneomics.com/code/brownsville-TX/chapter_4; https://www.vanplex.ca/texas-multiplex/brownsville/",
    coding_notes="UDC permitted-use chart (§4.4.3.F 'Dwelling, Accessory', P = by right; 'attached or detached') and "
    "§4.4.4 standards: one ADU per lot, one household, 'may be rented or occupied by a guest', setbacks of the main "
    "house, 'not more than 50% of the total floor area of the principal dwelling's living space' (no fixed cap: "
    "adu_max_sqft blank), separate meter allowed. Parking column '1 : Dwelling unit'. UDC (Ord. 2020-235.95) "
    "effective 2021-03-31 per search snippets and vanplex (not verified); 2026 amendments (Ords. 2025-235.119 to "
    ".125, 2026-235.127 to .130) not checked for ADU changes. The pre-2021 Chapter 348 rule was not found and is not "
    "coded."
    + FLAG
    + "brownsvilletx.gov DocumentCenter and municode returned 403; code read on the zoneomics mirror.",
)

# ---- Killeen (4839148): none ------------------------------------------------------------------------------
none_row(
    "4839148",
    2010,
    "No ADU in R-1; detached guest houses only in A-R1 and SR-2, up to 25% of the main house, rental prohibited",
    FLOOR,
    "https://www.zoneomics.com/code/killeen-TX/chapter_4; https://www.killeentexas.gov/731/North-Killeen-Overlay-District",
    "Ch. 31 §31-186 (R-1) lists no accessory dwelling, garage apartment or guest house; servants' quarters only as "
    "part of the main building (§31-188). Guest houses in A-R1 (§31-172(b)(1); Ord. 88-114, amended 12-072, "
    "2012-09-25) and SR-2 (§31-185.2(b)(1); Ord. 13-017, 2013-03-12): one per lot, up to 25% of the main house, one "
    "extra space, and 'the rental or lease of a guest house shall be prohibited'. Coded at 2010-01-01 (R-1 text "
    "predates the window; adoption not found). Pending: a North Killeen overlay allowing ADUs and tiny homes by "
    "right in one area was set for a council vote on 2026-10-20; outcome and terms not found, not coded."
    + FLAG
    + "municode returned 403; Ch. 31 read on the zoneomics mirror.",
    coverage="Single-family districts R-1 (none); A-R1 and SR-2 (non-rental guest houses)",
)


def main() -> None:
    with PATH.open(newline="") as f:
        existing = list(csv.DictReader(f))
    by_id = {r["reform_id"]: r for r in existing}
    for rid, fields in UPDATES.items():
        assert rid in by_id, rid
        by_id[rid].update(fields)
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
    print(f"{len(ROWS)} rows written, {len(UPDATES)} updated -> {PATH}")


if __name__ == "__main__":
    main()
