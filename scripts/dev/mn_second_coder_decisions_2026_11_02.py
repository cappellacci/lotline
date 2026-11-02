#!/usr/bin/env python3
"""Apply Ben's decisions on the MN second-coder review (2026-11-02) to config/reforms/mn.csv.

Run after scripts/dev/mn_second_coder_2026_11_02.py. Decisions are recorded in
docs/research/ordinances/mn-second-coder-decisions-2026-11-02.csv (Ben, 2026-11-02: accept all 62
recommendations). Decided rows get coder_2 = the reviewer, coder_agreement = adjudicated and the recommended
action appended to coding_notes. Two rows are deleted (not ADU rules), one is recoded and renamed (Forest
Lake). `[predates]` marks a rule in force before its coded date, first date unknown: not an in-window event
(HANDOFF 2026-11-01). `DATE UNCONFIRMED` marks a date the reviewer could not confirm from a signed ordinance;
the row still counts, and the date is on Ben's lookup list, written to LOOKUPS. Idempotent.

    uv run python scripts/dev/mn_second_coder_decisions_2026_11_02.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFORMS = ROOT / "config/reforms/mn.csv"
SHEET = ROOT / "docs/research/ordinances/mn-second-coder-decisions-2026-11-02.csv"
LOOKUPS = ROOT / "docs/research/ordinances/mn-second-coder-lookups-2026-11-02.csv"
REVIEWER = "codex-2026-11-02"
TAG = "Adjudicated by Ben 2026-11-02"
EK = (
    "[earliest-known] effective_date is the earliest date this source shows the rule in force, "
    "not a confirmed first adoption;"
)
PRE = (
    "[predates] the rule was in force before this date (second coder 2026-11-02); first date unknown: "
    "not an in-window event."
)
UNCONF = "DATE UNCONFIRMED: no signed ordinance or effective-date record found (second coder 2026-11-02);"

DELETE = {"MN-2730140-adu-2024", "MN-2725334-adu-2016-none"}
RENAME = {"MN-2721770-adu-none": "MN-2721770-adu-2023"}
ADU_YES = {"by_right": "True", "owner_occ": "True", "adus_per_lot": "1", "adu_detached_allowed": "True"}
UPDATES = {
    "MN-2744530-adu-2025": {
        "adoption_date": "2025-05-27",
        "effective_date": "2025-06-29",
        **ADU_YES,
        "adu_detached_allowed": "False",
    },
    "MN-2708794-adu-2018": {"adoption_date": "2018-05-22", "effective_date": "2018-05-22"},
    "MN-2710918-adu-2025": {"by_right": "False", "adus_per_lot": "1", "adu_max_sqft": "960"},
    "MN-2754214-adu-2015": {"adu_detached_allowed": "False"},
    "MN-2747680-adu-2025": {"by_right": "True", "adus_per_lot": "1", "adu_max_sqft": "1500"},
    "MN-2730392-adu-2011": {**ADU_YES, "by_right": "False"},
    "MN-2712700-adu-2024": {
        "adoption_date": "2024-08-26",
        "effective_date": "2024-08-26",
        **ADU_YES,
        "adu_max_sqft": "1000",
    },
    "MN-2731076-adu-2018": {**ADU_YES, "adu_max_sqft": "1000", "min_lot_sqft": "43560"},
    "MN-2701486-adu-2016": {**ADU_YES, "by_right": "False", "adu_max_sqft": "900"},
    "MN-2745430-adu-2024": {**ADU_YES, "adu_max_sqft": "1064"},
    "MN-2718662-adu-2025": dict(ADU_YES),
    "MN-2758738-adu-2026": dict(ADU_YES),
    "MN-2721770-adu-none": {
        "component": "Forest Lake: one detached accessory dwelling on A (Agriculture) lots of 5 acres "
        "or more (800 sq ft footprint, 50% of the house, one added space); "
        "internal accessory apartments in A and RR with a certificate of compliance "
        "(300 to 600 sq ft, owner-occupied)",
        "effective_date": "2023-01-23",
        "by_right": "True",
        "adus_per_lot": "1",
        "adu_max_sqft": "800",
        "adu_detached_allowed": "True",
        "coverage": "Forest Lake: A (detached, lots of 5+ acres) and RR (internal apartments only)",
        "coverage_zones": "A;RR",
        "source_section": "Forest Lake Code 153.067(C)(7), 153.068(D)(2)(a), 153.092(A)-(B)",
    },
    "MN-2707966-missing_middle-2010": {
        "coverage": "R-1 (R-2 to R-4 allow two-family dwellings, Table 152.507.1)",
        "coverage_zones": "R-1",
    },
    "MN-2743000-moratorium-2022": {"effective_date": "2022-06-15"},
    "MN-2758000-adu-2018": {"effective_date": "2018-12-01"},
    "MN-2758000-parking-2021": {"effective_date": "2021-10-01"},
    "MN-2754880-adu-2023": {"parking": "set by the Director (unlisted use)"},
}
PREDATES = {"MN-2722814-adu-2022", "MN-2721770-adu-none", "MN-2754880-missing_middle-2023"}
EARLIEST = PREDATES | {"MN-2713456-adu-2023", "MN-2716315688-adu-2022"}
UNCONFIRMED = {
    "MN-2708794-adu-2020",
    "MN-2754214-adu-2015",
    "MN-2747680-adu-2025",
    "MN-2751730-adu-2023",
    "MN-2713456-adu-2023",
    "MN-2757220-adu-2020",
    "MN-2717288-adu-2014",
    "MN-2713910450-adu-2010",
    "MN-2713928322-adu-2010",
    "MN-2713931580-adu-2010",
    "MN-2713957184-adu-2010",
    "MN-2731076-adu-2015",
    "MN-2701486-adu-2016",
    "MN-2743252-adu-2021",
    "MN-2714158-adu-2018",
    "MN-2724308-adu-2022",
    "MN-2735180-adu-2013",
    "MN-2741480-adu-2011",
    "MN-2741480-adu-2024",
    "MN-2744476-adu-2024",
    "MN-2753026-adu-2022",
    "MN-2755186-adu-2020",
    "MN-2755726-adu-2024",
    "MN-2755852-adu-2021",
    "MN-2762824-adu-2017",
    "MN-2763544-adu-2025",
    "MN-2766460-adu-2024",
    "MN-2768818-adu-2022",
    "MN-2769970-adu-2025",
    "MN-2716304132-adu-2018",
    "MN-2716315688-adu-2022",
}
# Lookups beyond the unconfirmed dates (reform_id -> what to find).
EXTRA_LOOKUPS = {
    "MN-2722814-adu-2022": "Fridley's first ADU ordinance (number and date).",
    "MN-2721770-adu-none": "When Forest Lake first allowed A-district ADUs and RR apartments "
    "(Ben's 2026-10 lookup said no ADU ordinance).",
    "MN-2754880-missing_middle-2023": "What Rochester's pre-2023 code allowed for 2-4 units in R-1 and other "
    "districts.",
    "MN-2730392-adu-2011": "Whether Ord. 2011-459 (2011-10-03) or Ord. 2011-460 (2011-11-07) adopted "
    "Hugo's ADU standards.",
    "MN-2744530-adu-2025": "Mounds View Ord. 1045 (2025-07-28, detached ADUs): a possible second row.",
}


def main() -> None:
    sheet = {r["reform_id"]: r for r in csv.DictReader(SHEET.open())}
    with REFORMS.open() as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    kept, changed = [], 0
    for row in rows:
        rid = row["reform_id"]
        if rid in DELETE:
            continue
        kept.append(row)
        if rid not in sheet or TAG in row["coding_notes"]:
            continue
        row.update(UPDATES.get(rid, {}))
        tags = [t for ids, t in ((EARLIEST, EK), (PREDATES, PRE), (UNCONFIRMED, UNCONF)) if rid in ids]
        tags = [t for t in tags if t.split(":")[0].split("]")[0] not in row["coding_notes"]]
        # The action text names tags ("tag [predates]"); strip the markers so only real tags are read as tags.
        note = sheet[rid]["recommended_action"].replace("[", "").replace("]", "")
        note = note.replace("DATE UNCONFIRMED", "date-unconfirmed")
        row["coding_notes"] = " ".join([*tags, row["coding_notes"], f"{TAG}: {note}"]).strip()
        row["reform_id"] = RENAME.get(rid, rid)
        row["coder_2"], row["coder_agreement"] = REVIEWER, "adjudicated"
        changed += 1
    with REFORMS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(kept)
    lookups = [
        (RENAME.get(rid, rid), sheet[rid]["place"], EXTRA_LOOKUPS.get(rid) or sheet[rid]["finding"])
        for rid in sheet
        if rid in UNCONFIRMED or rid in EXTRA_LOOKUPS
    ]
    if LOOKUPS.exists():  # never overwrite Ben's answers
        print(f"{changed} rows adjudicated, {len(rows) - len(kept)} deleted; {LOOKUPS.name} kept")
        return
    with LOOKUPS.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["reform_id", "place", "what_to_find", "answer", "source_url"])
        w.writerows([*r, "", ""] for r in lookups)
    print(f"{changed} rows adjudicated, {len(rows) - len(kept)} deleted, {len(lookups)} lookups")


if __name__ == "__main__":
    main()
