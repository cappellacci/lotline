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


def main() -> None:
    with REFORMS.open() as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    ids = {r["reform_id"] for r in rows}
    kept, changed = [], 0
    for row in rows:
        rid = row["reform_id"]
        if rid in DELETE:
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
    added = 0
    if NEW["reform_id"] not in ids:
        row = {k: "" for k in fields}
        row.update(state="MN", status="in_force", coder="ben", coder_agreement="single_coder")
        row.update(NEW)
        row["coding_notes"] = f"{row['coding_notes']} {TAG}."
        kept.append(row)
        added = 1
    with REFORMS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(kept)
    print(f"{changed} rows changed, {len(rows) + added - len(kept)} deleted, {added} added")


if __name__ == "__main__":
    main()
