#!/usr/bin/env python3
"""Apply Ben's decisions on the NC second-coder review (2026-11-01) to config/reforms/nc.csv.

Run after scripts/dev/nc_second_coder_2026_11_01.py. Decisions are recorded in
docs/research/ordinances/nc-second-coder-decisions-2026-11-01.csv (Ben: accept the recommendations, keep Mint
Hill's duplexes by right). Decided rows get coder_2 = the reviewer and coder_agreement = adjudicated. Four
rows are renamed because their effective year moves. `[predates]` marks a rule in force before its coded date,
first date unknown: not an in-window event. Five rows are added (Goldsboro, New Bern, Concord). Idempotent.

    uv run python scripts/dev/nc_second_coder_decisions_2026_11_01.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFORMS = ROOT / "config/reforms/nc.csv"
REVIEWER = "codex-2026-11-01"
TAG = "Adjudicated by Ben 2026-11-01"
EK = (
    "[earliest-known] effective_date is the earliest date this source shows the rule in force, "
    "not a confirmed first adoption;"
)
PRE = (
    "[predates] the rule was in force before this date (second coder 2026-11-01); first date unknown: "
    "not an in-window event."
)

# reform_id -> (new reform_id or None, field changes, note)
DECISIONS = {
    "NC-3755000-adu-2019": (
        None,
        {"effective_date": "2019-05-20"},
        "reviewer's overlay distinction matches the row; effective date from TC-3-17 (2019-05-20).",
    ),
    "NC-3759280-adu-2023": (
        None,
        {},
        "DATE UNCONFIRMED: the 2023 city report says Phase 1 (with ADUs) was still being "
        "finalized; Sanford's ADU text-amendment adoption date is on Ben's lookup list.",
    ),
    "NC-3702080-adu-2021": (
        "NC-3702080-adu-2014",
        {"effective_date": "2014-11-06", "adoption_date": "2014-11-06"},
        f"{EK} council minutes show accessory-apartment amendments adopted 2014-11-06 (earlier "
        "history not researched).",
    ),
    "NC-3741960-adu-2014": (
        "NC-3741960-adu-2016",
        {"effective_date": "2016-04-11", "adoption_date": "2016-04-11"},
        f"{EK} Sec. 155.506.9 shows the rule as amended by Ord. 2141 (2016-04-11).",
    ),
    "NC-3757500-adu-2005": (
        "NC-3757500-adu-2004",
        {"effective_date": "2004-07-12", "adoption_date": "2004-07-12"},
        f"{EK} LDC adopted and effective 2004-07-12; O-05-34b (2005-05-09) is a stormwater "
        "ordinance per the reviewer.",
    ),
    "NC-3743480-missing_middle-2011": (
        None,
        {},
        "kept by_right True: use table Duplex SR (Sec. 5.1.A.2, by right "
        "with special requirements); note the dimensional table says duplexes are "
        "'Subject to the requirements of the Conditional Zoning District'.",
    ),
    "NC-3767420-adu-1982": (
        None,
        {},
        "reviewer's 2017 Sec. 22-43 ADU source is Thomasville, Georgia (thomasville.org) "
        "and a Cabarrus County agenda; rejected. Row kept as coded.",
    ),
}
PREDATES = [
    "NC-3733560-adu-2021",
    "NC-3702080-missing_middle-2021",
    "NC-3725480-adu-2022",
    "NC-3728080-adu-2026",
    "NC-3731060-missing_middle-2011",
    "NC-3732260-adu-2023",
    "NC-3735200-adu-2022",
    "NC-3744220-adu-2022",
]

GSO = "https://www.goldsboronc.gov/wp-content/uploads/UDO160D-Article-5.pdf"
NB = "https://library.municode.com/nc/new_bern/codes/code_of_ordinances?nodeId=PTIICOOR_APXALAUS_ARTXPEUS"
NEW = [
    dict(
        reform_id="NC-3726880-adu-2021",
        jurisdiction_geoid="3726880",
        theme="adu",
        effective_date="2021-06-01",
        component="Goldsboro UDO Sec. 5.5.4(A): accessory dwellings and accessory apartments only "
        "by Tier 2 special "
        "use permit (City Council) in the districts of Sec. 5.4; one per lot; lesser of 40% of the "
        "house's livable "
        "area or 1,100 sq ft; rear of the house",
        by_right="False",
        adus_per_lot="1",
        adu_max_sqft="1100",
        adu_detached_allowed="True",
        coverage="City of Goldsboro: districts marked in UDO Sec. 5.4",
        source_url=GSO,
        source_section="Goldsboro UDO (G.S. 160D version, 2021-06-01) Article 5, Secs. 5.4 and 5.5.4(A)",
        source_quote="are permitted as a special use permit Tier 2",
        coding_notes=f"{EK} current UDO version dated 2021-06-01; first appearance of the ADU "
        "provision not found.",
    ),
    dict(
        reform_id="NC-3726880-missing_middle-2021",
        jurisdiction_geoid="3726880",
        theme="missing_middle",
        effective_date="2021-06-01",
        component="Goldsboro UDO Sec. 5.4: duplexes permitted in R-12, R-9, R-6 and RM-8 (not R-40 or R-20); "
        "multifamily (3+) by Tier 2 special use in some residential districts",
        by_right="True",
        unit_cap="2",
        coverage="City of Goldsboro: R-12, R-9, R-6, RM-8",
        coverage_zones="R-12;R-9;R-6;RM-8",
        source_url=GSO,
        source_section="Goldsboro UDO (2021-06-01 version) Article 5, Sec. 5.4; June 4, 2018 Council minutes "
        "(Ord. 2018-30)",
        source_quote="Duplex (two attached units/lot or on separate lots)",
        coding_notes=f"{EK} {PRE} Ord. 2018-30 (2018-06-04) predates the 2021 version.",
    ),
    dict(
        reform_id="NC-3746340-adu-2023",
        jurisdiction_geoid="3746340",
        theme="adu",
        effective_date="2023-10-18",
        component="New Bern Land Use Ordinance (Code Appendix A) Sec. 15-146 Table of Permissible Uses: no "
        "accessory dwelling or secondary dwelling use",
        adus_per_lot="0",
        coverage="City of New Bern, all districts",
        source_url=NB,
        source_section="New Bern Code Appendix A Sec. 15-146 (Supp. 78, 2023-10-18); June 19, 2025 "
        "Planning and "
        "Zoning Commission recording (newbernnc.new.swagit.com/videos/346307)",
        source_quote="we don't have the ability for ADUs",
        coding_notes=f"{EK} 'no ADUs' (adus_per_lot = 0 convention, as Jacksonville); date is the Supp. 78 "
        "compilation the reviewer read; city staff confirmed in June 2025.",
    ),
    dict(
        reform_id="NC-3746340-missing_middle-1996",
        jurisdiction_geoid="3746340",
        theme="missing_middle",
        effective_date="1996-02-13",
        adoption_date="1996-02-13",
        component="New Bern Land Use Ordinance Sec. 15-146 use 1.200 Duplex permitted (Z) in A-5, "
        "A-5F, R-10, "
        "R-10A, R-8 and R-6 (and commercial districts); multifamily (1.300) by special use in some districts",
        by_right="True",
        unit_cap="2",
        coverage="City of New Bern: A-5, A-5F, R-10, R-10A, R-8, R-6",
        coverage_zones="A-5;A-5F;R-10;R-10A;R-8;R-6",
        source_url=NB,
        source_section="New Bern Code Appendix A Sec. 15-146 (Supp. 78); date from Ben's manual lookup "
        "(Ord. 1996-13, 1996-02-13)",
        source_quote="1.200 Duplex",
        coding_notes=f"{EK} date is Ord. 1996-13 (duplex density standards) from Ben's 2026-10-21 "
        "lookup, not "
        "the primary text.",
    ),
    dict(
        reform_id="NC-3714100-missing_middle-2024",
        jurisdiction_geoid="3714100",
        theme="missing_middle",
        effective_date="2024-11-14",
        component="Concord Development Ordinance Sec. 8.1.8 use table: Duplex/Triplex PS (permitted "
        "by right with "
        "supplemental standards) in RV and RC only; duplex lots need 1.5x the district minimum area "
        "and width",
        by_right="True",
        unit_cap="3",
        coverage="City of Concord: RV and RC",
        coverage_zones="RV;RC",
        source_url="https://www.concordnc.gov/",
        source_section="Concord Development Ordinance Article 8, use table 8.1.8 (copy postdating TA-10-24, "
        "downloaded by Ben 2026-10-21)",
        source_quote="Duplex/Triplex PS PS",
        coding_notes=f"{EK} {PRE} date is TA-10-24 (2024-11-14), the earliest date the copy is "
        "known to reflect; "
        "the reviewer agreed with the rule (second coder yes).",
    ),
]


def main() -> None:
    with REFORMS.open() as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    ids = {r["reform_id"] for r in rows}
    changed = 0
    for row in rows:
        rid = row["reform_id"]
        if TAG in row["coding_notes"]:
            continue
        if rid in DECISIONS:
            new_id, updates, note = DECISIONS[rid]
            row.update(updates)
            if new_id:
                row["reform_id"] = new_id
            row["coding_notes"] = f"{row['coding_notes']} {TAG}: {note}"
        elif rid in PREDATES:
            row["coding_notes"] = f"{PRE} {row['coding_notes']} {TAG}: rule predates the coded date."
        else:
            continue
        row["coder_2"], row["coder_agreement"] = REVIEWER, "adjudicated"
        changed += 1
    added = 0
    for n in NEW:
        if n["reform_id"] in ids:
            continue
        row = {k: "" for k in fields}
        row.update(
            state="NC",
            status="in_force",
            verified_date="2026-11-01",
            coder=REVIEWER,
            coder_2="claude",
            coder_agreement="adjudicated",
            verified_by="Ben (accepted 2026-11-01)",
        )
        row.update(n)
        row["coding_notes"] = (
            f"{row['coding_notes']} Coded by the second coder (Codex, 2026-11-01); geoid "
            f"corrected and checked by Claude; {TAG}: accepted."
        )
        rows.append(row)
        added += 1
    with REFORMS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{changed} rows adjudicated, {added} rows added")


if __name__ == "__main__":
    main()
