#!/usr/bin/env python3
"""Apply Ben's decisions on the MN second-coder lookups (2026-11-02) to config/reforms/mn.csv.

Run after scripts/dev/mn_second_coder_decisions_2026_11_02.py. Ben's agent filled
docs/research/ordinances/mn-second-coder-lookups-2026-11-02.csv; 33 of its 36 answers repeat the
second coder's findings, so those rows keep their DATE UNCONFIRMED tags. Ben accepted four changes:

- Forest Lake: Ord. 719 (adopted 2023-01-23, council minutes and ordinance) added ADUs in the A district,
  so the 2023 row is an in-window event: its [predates] and [earliest-known] tags come off.
- Fridley: the city says Council approved an ADU ordinance in 2022, so 2022 is not a recodification:
  [predates] comes off; the day stays DATE UNCONFIRMED.
- Mounds View: Ord. 1045 (adopted 2025-08-11, effective 2025-09-11) added detached ADUs. The Ord. 1042 row
  becomes -2025a and a -2025b row is added (the a/b convention of OH and TX).
- Burnsville 2020: no 2020 adoption found, so the row is deleted (the accepted decision);
  the 2018 rule stands.
- Hugo (Ben's own lookup, later the same day): Ord. 2011-459 §1, dated 2011-10-03, adopted the ADU rules
  (Hugo Code §90-277 attributes them to it), not Ord. 2011-460 (2011-11-07). No separate effective or
  publication date was found, so the effective date is coded as adoption.
- Round 3 (Ben, same day): Medina 2024 deleted (Ord. 733 is a height rule); Roseville Ord. 1418 (2011-10-10)
  added as an event.
- Rochester missing middle (Ben's own lookup, same day): a 1998 city planning record says an amendment
  removed duplexes and Performance Residential Developments from R-1 (R-1x kept the former R-1 uses), so
  R-1 was one home per lot before the 2023 UDC. The R-1 row stays `[predates]` and is a control on evidence.

Idempotent.

    uv run python scripts/dev/mn_lookups_2026_11_02.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFORMS = ROOT / "config/reforms/mn.csv"
TAG = "Lookup (Ben's agent, 2026-11-02), accepted by Ben"
EK = (
    "[earliest-known] effective_date is the earliest date this source shows the rule in force, "
    "not a confirmed first adoption; "
)
PRE = (
    "[predates] the rule was in force before this date (second coder 2026-11-02); first date unknown: "
    "not an in-window event. "
)
UNCONF = "DATE UNCONFIRMED: no signed ordinance or effective-date record found (second coder 2026-11-02);"
FOREST_LAKE = "https://ci.forest-lake.mn.us/AgendaCenter/ViewFile/Minutes/_01232023-141"
MOUNDS_VIEW = (
    "https://cms6.revize.com/revize/moundsview/document_center/City%20Council%20Meetings/2025/Packets/"
    "07-28-2025%20CC.pdf"
)

DELETE = {"MN-2708794-adu-2020"}
UNCONFIRMED = {"MN-2722814-adu-2022"}  # Fridley: year known, day not
RENAME = {"MN-2744530-adu-2025": "MN-2744530-adu-2025a"}
# reform_id -> (tags to remove, field changes, note)
CHANGES = {
    "MN-2721770-adu-2023": (
        [EK, PRE],
        {
            "adoption_date": "2023-01-23",
            "source_url": f"{FOREST_LAKE};https://ci.forest-lake.mn.us/DocumentCenter/View/2840",
            "source_section": "Ord. 719; Forest Lake Code 153.092(B)",
        },
        "Ord. 719 adopted unanimously 2023-01-23 (council minutes; ordinance text) added accessory dwellings "
        "as an accessory use in the A district; effective on publication, date not found "
        "(coded as adoption). "
        "Internal apartments in A and RR are older (first date unknown; district sections trace to Ord. 537, "
        "2004): the event is the detached A-district ADU.",
    ),
    "MN-2730392-adu-2011": (
        [],
        {
            "adoption_date": "2011-10-03",
            "effective_date": "2011-10-03",
            "source_section": "Ord. 2011-459 §1; Hugo Code §90-277",
        },
        "Ben's lookup: Hugo Code §90-277 attributes the ADU provisions to Ord. 2011-459 §1 (2011-10-03), not "
        "Ord. 2011-460 (2011-11-07, Ben's earlier lookup). No effective or publication date found: effective "
        "coded as adoption. The official code record's link was not recorded here.",
    ),
    "MN-2754880-missing_middle-2023": (
        [],
        {},
        "Ben's lookup: the city's archived 1998 planning record says an amendment removed duplexes and "
        "Performance Residential Developments from R-1; R-1x kept the former R-1 uses (including PRDs). So "
        "ordinary R-1 lots allowed one home before the 2023 UDC too: no change in R-1 in 2023, "
        "the predates tag stands and the row is a control. 3- and 4-unit rules across every legacy "
        "district are unresolved "
        "(full archived use table not verified). The record's link was not recorded here.",
    ),
    "MN-2722814-adu-2022": (
        [PRE],
        {},
        "the city ADU page says Council approved an ADU ordinance in 2022, so 2022 is the adoption year, not "
        "a recodification; the day (coded 2022-01-01) and ordinance number are still unknown.",
    ),
}
NEW = dict(
    reform_id="MN-2744530-adu-2025b",
    jurisdiction_geoid="2744530",
    theme="adu",
    component="Mounds View Ord. 1045: one detached ADU allowed on a single-family lot "
    "(instead of an internal ADU, not as well); owner occupancy with a recorded covenant; "
    "300 sq ft minimum, 50% of the house "
    "maximum; one added stall; rental license; no short-term rental",
    adoption_date="2025-08-11",
    effective_date="2025-09-11",
    supersedes="MN-2744530-adu-2025a",
    owner_occ="True",
    adus_per_lot="1",
    adu_detached_allowed="True",
    parking="one additional space",
    coverage="Mounds View: single-family lots",
    source_url=MOUNDS_VIEW,
    source_section="Ord. 1045",
    coding_notes=f"{UNCONF} adopted 2025-08-11, published 2025-08-12, effective 30 days later "
    "(2025-09-11) per Ben's agent; the cited source is the 2025-07-28 council packet, "
    "which predates adoption. by_right "
    "not stated (D-022 draws it).",
)

# Round 2 (Ben's agent, later on 2026-11-02): official records for adoption dates. A row whose adoption is now
# shown by an official record (code history, council packet, minutes) loses DATE UNCONFIRMED; the effective
# date stays coded as adoption where no publication date was found, as elsewhere.
TAG2 = "Lookup round 2 (Ben's agent, 2026-11-02)"
ROUND2 = {
    "MN-2735180-adu-2013": (
        True,
        {"source_url": "https://codelibrary.amlegal.com/codes/lakevillemn/latest/lakeville_mn/0-0-0-9769"},
        "Lakeville Code 11-59-13 history: Ord. 903 passed 2013-03-04 with the ADU rules.",
    ),
    "MN-2741480-adu-2011": (
        True,
        {"source_url": "https://www.medinamn.us/wp-content/uploads/2020/12/826.pdf"},
        "Medina Code 826.98(2)(p) history: Ord. 514 (2011-11-15) amended the ADU provisions.",
    ),
    "MN-2743252-adu-2021": (
        True,
        {"source_url": "https://www.minnetonkamn.gov/home/showpublisheddocument/9654/637686109292800000"},
        "council packet records adoption 2021-10-04; publication field blank.",
    ),
    "MN-2766460-adu-2024": (
        True,
        {"source_section": "Ord. 774"},
        "the 2024-07-16 council packet has the signed resolution adopting Ord. 774 that day; effective "
        "after publication, date not found.",
    ),
    "MN-2747680-adu-2025": (
        True,
        {
            "source_section": "Ord. 948 (Chapter 25, Zoning)",
            "source_url": "https://www.oakdalemn.gov/515/Proposed-and-Adopted-Ordinances;"
            "https://www.oakdalemn.gov/DocumentCenter/View/8307",
        },
        "the city's ordinance list shows Ord. 948 replacing Chapter 25, adopted 2025-07-08.",
    ),
    "MN-2713456-adu-2023": (
        True,
        {
            "adoption_date": "2022-12-21",
            "effective_date": "2023-01-01",
            "source_url": "https://cottagegrovemn.gov/202/Zoning;"
            "https://codelibrary.amlegal.com/codes/cottagegrovemn/latest/cottagegrove_mn/0-0-0-5016",
        },
        "the city says the zoning-code revision was approved 2022-12-21, effective 2023-01-01 (Ord. 1068, "
        "2023-08-16, is a later amendment). Whether accessory apartments predate the revision is unknown, so "
        "the row stays earliest-known.",
    ),
    "MN-2730392-adu-2011": (
        False,
        {"source_url": "https://hugomn.granicus.com/MetaViewer.php?clip_id=171&meta_id=13721&view_id=2"},
        "official code-history record for Ord. 2011-459 (2011-10-03) added as the source.",
    ),
    "MN-2754880-missing_middle-2023": (
        False,
        {
            "source_url": "https://lf.rochestermn.gov/WebLink/DocView.aspx?dbid=0&id=3872480&repo=ROCHESTER;"
            "https://www.rochestermn.gov/media/poageesh/unified-development-code.pdf"
        },
        "the 1998 staff report and Planning Commission minutes added as the source for pre-UDC R-1.",
    ),
    "MN-2724308-adu-2022": (
        False,
        {},
        "the city page confirms the Council vote in November 2022 only: the month is confirmed, the day is "
        "not (2022-11-01 kept as the coded day).",
    ),
}

# Round 3 (Ben, 2026-11-02): Medina 2024 is a height rule (Ord. 733), not an ADU change, so it is deleted;
# Roseville Ord. 1418 (2011-10-10) is added as an in-window event between the 2010 (2006 code) and 2021 rows.
DELETE3 = {"MN-2741480-adu-2024"}
ROSEVILLE_2011 = dict(
    reform_id="MN-2755852-adu-2011",
    jurisdiction_geoid="2755852",
    theme="adu",
    component="Roseville Ord. 1418: ADUs made a permitted use (previously conditional) on one-family lots; "
    "one ADU, attached or detached (above a garage or in an accessory building); "
    "owner occupancy; 650 sq ft cap",
    adoption_date="2011-10-10",
    effective_date="2011-10-10",
    supersedes="MN-2755852-adu-2010",
    by_right="True",
    owner_occ="True",
    adus_per_lot="1",
    adu_max_sqft="650",
    adu_detached_allowed="True",
    coverage="LDR-1 (per the council summary)",
    coverage_zones="LDR-1",
    source_url="https://www.cityofroseville.com/Archive.aspx?ADID=1186;"
    "https://cityofroseville.com/DocumentView.aspx?DID=4968",
    source_section="Ord. 1418",
    coding_notes="Council record 2011-10-10: Council adopted Ord. 1418; the report says earlier city action "
    "first allowed ADUs as conditional uses and this amendment made them permitted (the 2006 code in the "
    "2010 row shows the conditional use). One second-coder note instead says Ord. 1418 allowed ADUs by "
    "conditional use; by_right=True follows the council record. Effective on publication, date not found: "
    "coded as adoption. 650 sq ft and owner occupancy from the second coder's reading of the ordinance; "
    "a later 2011 amendment limited occupancy to 2.",
)

# Notes only (Ben's lookups, 2026-11-02): leads for dates still unconfirmed, and context for older rows.
TAG4 = "Ben's lookup lead (2026-11-02)"
NOTES4 = {
    "MN-2751730-adu-2002": "the 2023 ordinance history cites Ord. 2002-24 (2002-06-25) as the earlier ADU "
    "amendment, matching this row's date (original not located). The city says the pre-2023 rule allowed ADUs"
    " only above attached or detached garages "
    "(https://www.plymouthmn.gov/Home/Components/News/News/7970/542).",
    "MN-2757220-adu-2020": "the 2020-09-16 Planning Commission packet (draft, number and dates blank) says "
    "Council would likely consider the ordinance on 2020-10-05, probably the first reading; adoption would "
    "follow at a later meeting, consistent with the coded 2020-11-13. Next: Council minutes or video for "
    "Oct-Nov 2020, the Sun Sailor legal notice, or the city clerk (Laserfiche search did not load).",
}

# Ben's Richfield lookup (2026-11-02): the 2015-01-01 placeholder goes. The city's ADU handout is dated
# 7/2015, the earliest date a source shows the rule in force, so the row is re-dated to 2015-07-01 as
# [earliest-known]; Bill No. 2015-4's passage date stays unknown (DATE UNCONFIRMED kept).
RICHFIELD = "MN-2754214-adu-2015"
RICHFIELD_TAG = "Ben's Richfield lookup (2026-11-02)"
RICHFIELD_NOTE = (
    "Bill No. 2015-4's passage, publication and effective dates not found in official records; the city ADU "
    "handout is dated 7/2015, so effective_date is 2015-07-01 (earliest known in force), replacing the "
    "2015-01-01 placeholder. Bill No. 2015-9 (text and date not found) and Bill No. 2023-2 (signed, passed "
    "2023-01-24; carries the ADU provisions forward, allows two-family uses and changes low-density district "
    "standards) amend it; publication and effective dates for 2023-2 not found."
)
RICHFIELD_URLS = (
    "https://cms9files.revize.com/richfieldmn/Document_Center/Department/Community%20Development/"
    "Permits%2C%20Inspections%20%26%20Licenses/Zoning%20Handouts%20and%20Applications/"
    "AccessoryDwellingUnitsHand.pdf;"
    "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/15207/1201593/pdf"
)

# Ben's lookups (2026-11-02): Richfield missing middle (new row) and Eagan's ordinance number (note).
RICHFIELD_MM = dict(
    reform_id="MN-2754214-missing_middle-2023",
    jurisdiction_geoid="2754214",
    theme="missing_middle",
    component="Richfield Bill No. 2023-2: two-family dwellings by right in R (Low Density Residential); MR-1 "
    "eliminated and its properties rezoned to R; still prohibited in R-1; three or more units stay "
    "multifamily uses, not allowed in R or R-1",
    adoption_date="2023-01-24",
    effective_date="2023-01-24",
    by_right="True",
    unit_cap="2",
    coverage="R (Low Density Residential), including the former MR-1 properties",
    coverage_zones="R",
    source_url="https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/15207/1201593/pdf;"
    "https://cms9files.revize.com/richfieldmn/01-24-2023%20City%20Council%20Agenda.pdf;"
    "https://cms9files.revize.com/richfieldmn/01-24-2023%20Regular.pdf",
    source_section="Bill No. 2023-2",
    source_quote="by-right in the R District",
    coding_notes="Ben's lookup (2026-11-02): signed Bill No. 2023-2 passed 2023-01-24 (council minutes); the "
    "council-approved summary says two-family homes are allowed by right in R. Effective per Charter 3.09, "
    "generally 30 days after publication; publication date not found, so effective coded as adoption (the "
    "true date is about a month or more later). Treated as a change: the summary presents by-right duplexes "
    "in R as new; R's earlier two-family rule was not read.",
)
EAGAN = "MN-2717288-adu-2014"
EAGAN_TAG = "Ben's Eagan lookup (2026-11-02)"
EAGAN_NOTE = (
    "the ADU ordinance is almost certainly Ord. 528, 2nd Series: the draft's Sections 1-3 add ADUs to the"
    " R-1 and Estate use lists and the ADU standards, and the code history attributes the same sections "
    "to No. 528 (No. 529 is a separate amendment). The draft is unsigned with the number and dates blank,"
    " so 528 is a strong identification, not signed-copy confirmation. 2014-05-05 is the code history's "
    "effective date, not confirmed as the adoption date; publication date unknown. Eagan's online code is"
    " unofficial (the City Clerk's printed copy is official)."
)

# Ben's confirmations (2026-11-02): official records confirm the coded dates, so DATE UNCONFIRMED comes off.
BEN_TAG = "Ben's confirmation (2026-11-02)"
BEN_CONFIRM = {
    "MN-2751730-adu-2023": (
        {
            "source_section": "Ord. 2023-12; Resolution 2023-239 (summary publication)",
            "source_url": "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/15701/1237282/p"
            "df;https://d3n9y02raazwpg.cloudfront.net/nwsccc-plymouth/43307831-7282-11ed-9024-0050569183fa-5"
            "5f46114-8d12-454f-8f94-e6b3225c3f97-1695907803.pdf;https://www.plymouthmn.gov/home/showpublishe"
            "ddocument/29065/639069420947600000",
        },
        "Ord. 2023-12 adopted 2023-09-12 and effective on passage (ordinance text); council minutes confirm "
        "adoption and Resolution 2023-239 for summary publication (newspaper date not found). It expanded "
        "the earlier rule (ADUs only above attached or detached garages, Ord. 2002-24) to internal, attached"
        " and standalone detached units with an administrative ADU permit.",
    ),
    "MN-2768818-adu-2022": (
        {
            "component": "Wayzata Ord. 811: ADUs a permitted accessory use in all six single-family "
            "districts; detached allowed (11,000 sq ft lot in R-3A and R-3); 300 sq ft minimum, 33% size "
            "cap, 960 sq ft cap in R-2A, R-2, R-3A and R-3; one added parking space; owner lives in the "
            "house or the ADU; one ADU per lot",
            "effective_date": "2022-06-30",
            "by_right": "True",
            "owner_occ": "True",
            "adus_per_lot": "1",
            "adu_max_sqft": "960",
            "adu_detached_allowed": "True",
            "parking": "one additional space",
            "coverage": "R-1A, R-1, R-2A, R-2, R-3A, R-3 (all single-family districts)",
            "coverage_zones": "R-1A;R-1;R-2A;R-2;R-3A;R-3",
            "source_section": "Ord. 811; City Code Ch. 937",
        },
        "Ord. 811 adopted 2022-06-21 at second reading on the 4-0 consent agenda (official meeting summary); "
        "effective on passage and publication, and the Ch. 937 code history gives 2022-06-30 (no dated "
        "publication notice found). adu_max_sqft=960 is the cap in R-2A to R-3; R-1A and R-1 have the 33% "
        "cap only. The 11,000 sq ft lot minimum applies only to detached ADUs in R-3A and R-3 (min_lot_sqft "
        "left blank).",
    ),
    "MN-2714158-adu-2018": (
        {
            "source_section": "Ord. 2017-07 (Unified Development Code); City Code 500.09, Table 4, 515.23",
            "source_url": "https://www.crystalmn.gov/UserFiles/Servers/Server_10879634/File/Government/"
            "City%20Code/CityCode.pdf;"
            "https://nwsccc-crystal.granicus.com/GeneratedAgendaViewer.php?clip_id=563&view_id=4",
        },
        "Ord. 2017-07 enacted the Unified Development Code, which authorized ADUs; the official City Code "
        "(500.09) gives adoption 2018-01-02 and effective 2018-02-10, and the 2018-01-02 Council agenda "
        "(item 6.19) lists the second reading and adoption. The March 2018 Planning Commission 'update' "
        "came later. No signed copy or publication date found.",
    ),
    "MN-2755726-adu-2024": (
        {
            "component": "Rosemount Ord. 2024-04 (zoning code update): internal or attached ADUs allowed with"
            " standards in A-2, RR, R-1 and R-2; lesser of 75% of the house's living area or 800 sq ft; one "
            "additional parking space; exterior-material and deck/balcony standards",
            "by_right": "True",
            "adu_max_sqft": "800",
            "adu_detached_allowed": "False",
            "parking": "one additional space",
            "coverage": "A-2, RR, R-1, R-2",
            "coverage_zones": "A-2;RR;R-1;R-2",
            "source_section": "Ord. 2024-04",
            "source_url": "https://codelibrary.amlegal.com/codes/rosemountmn/latest/rosemount_mn/0-0-0-15485;"
            "https://www.co.dakota.mn.us/Government/publiccommittees/CFL/Documents/"
            "AccessoryDwellingUnitGuide.pdf",
        },
        "the official code gives Ord. 2024-04, adopted and effective 2024-06-04 (publication date not found)."
        " New authorization: Dakota County's 2016 Rosemount profile says the city had no ADU policy, and its"
        " guide (updated 2023-12-20) lists Rosemount among cities not allowing ADUs. Detached ADUs and owner"
        " occupancy are not in the reviewed provisions (adu_detached_allowed=False; owner_occ left blank, "
        "D-022 draws it); by_right=True reads 'allowed with standards' as no discretionary permit.",
    ),
}


def main() -> None:
    with REFORMS.open() as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    ids = {r["reform_id"] for r in rows}
    kept, changed = [], 0
    for row in rows:
        rid = row["reform_id"]
        if rid in DELETE or rid in DELETE3:
            continue
        kept.append(row)
        if TAG in row["coding_notes"]:
            continue
        if rid in CHANGES:
            remove, updates, note = CHANGES[rid]
            for t in remove:
                row["coding_notes"] = row["coding_notes"].replace(t, "")
            if rid in UNCONFIRMED and UNCONF not in row["coding_notes"]:
                row["coding_notes"] = f"{UNCONF} {row['coding_notes']}"
            row.update(updates)
        elif rid in RENAME:
            row["reform_id"] = RENAME[rid]
            note = "renamed from -2025 (Ord. 1042); Ord. 1045 is MN-2744530-adu-2025b."
        else:
            continue
        row["coding_notes"] = f"{row['coding_notes'].strip()} {TAG}: {note}"
        changed += 1
    for row in kept:
        rid = row["reform_id"]
        if rid not in ROUND2 or TAG2 in row["coding_notes"]:
            continue
        confirm, updates, note = ROUND2[rid]
        if confirm:
            row["coding_notes"] = row["coding_notes"].replace(UNCONF, "").strip()
        row.update(updates)
        row["coding_notes"] = f"{row['coding_notes']} {TAG2}: {note}"
        changed += 1
    for row in kept:
        rid = row["reform_id"]
        if rid in NOTES4 and TAG4 not in row["coding_notes"]:
            row["coding_notes"] = f"{row['coding_notes']} {TAG4}: {NOTES4[rid]}"
            changed += 1
    for row in kept:
        if row["reform_id"] == RICHFIELD and RICHFIELD_TAG not in row["coding_notes"]:
            row["effective_date"] = "2015-07-01"
            row["source_url"] = f"{row['source_url']};{RICHFIELD_URLS}"
            ek = "" if EK.strip() in row["coding_notes"] else EK
            row["coding_notes"] = f"{ek}{row['coding_notes']} {RICHFIELD_TAG}: {RICHFIELD_NOTE}"
            changed += 1
    for row in kept:
        if row["reform_id"] == EAGAN and EAGAN_TAG not in row["coding_notes"]:
            row["source_section"] = "Ord. 528, 2nd Series (strong identification, unsigned draft)"
            row["coding_notes"] = f"{row['coding_notes']} {EAGAN_TAG}: {EAGAN_NOTE}"
            changed += 1
    for row in kept:
        rid = row["reform_id"]
        if rid in BEN_CONFIRM and BEN_TAG not in row["coding_notes"]:
            updates, note = BEN_CONFIRM[rid]
            row.update(updates)
            row["coding_notes"] = row["coding_notes"].replace(UNCONF, "").strip()
            row["coding_notes"] = f"{row['coding_notes']} {BEN_TAG}: {note}"
            changed += 1
    added = 0
    if RICHFIELD_MM["reform_id"] not in ids:
        row = {k: "" for k in fields}
        row.update(state="MN", status="in_force", coder="ben", coder_agreement="single_coder")
        row.update(RICHFIELD_MM)
        kept.append(row)
        added += 1
    if ROSEVILLE_2011["reform_id"] not in ids:
        for row in kept:
            if row["reform_id"] == "MN-2755852-adu-2021":
                row["supersedes"] = ROSEVILLE_2011["reform_id"]
        row = {k: "" for k in fields}
        row.update(state="MN", status="in_force", coder="ben", coder_agreement="single_coder")
        row.update(ROSEVILLE_2011)
        row["coding_notes"] = f"{row['coding_notes']} Lookup round 3 (Ben, 2026-11-02)."
        kept.append(row)
        added += 1
    if NEW["reform_id"] not in ids:
        row = {k: "" for k in fields}
        row.update(state="MN", status="in_force", coder="ben", coder_agreement="single_coder")
        row.update(NEW)
        row["coding_notes"] = f"{row['coding_notes']} {TAG}."
        kept.append(row)
        added += 1
    with REFORMS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(kept)
    print(f"{changed} rows changed, {len(rows) + added - len(kept)} deleted, {added} added")


if __name__ == "__main__":
    main()
