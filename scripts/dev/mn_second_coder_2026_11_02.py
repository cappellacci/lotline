#!/usr/bin/env python3
"""Apply the MN second-coder review of 2026-11-02 to config/reforms/mn.csv (append-only notes).

Reads docs/research/ordinances/mn-second-coder-2026-11-02.csv (Ben's second agent, Codex, filled the
four reviewer columns). Rows the reviewer agrees with get coder_2 and coder_agreement = agree. Every reviewed
row gets the reviewer's finding appended to coding_notes, cut to NOTE_CHARS (full text stays in the sheet).
No coded value changes here: disagreements and value changes are decided by Ben in
mn-second-coder-decisions-2026-11-02.csv, applied by a later script. Idempotent.

The reviewer also wrote into the sheet's left-hand columns (dates, coded_as, coverage, source_url); those
edits are its findings, not our coding. Our coding as sent is the sheet at commit 54e9727.

    uv run python scripts/dev/mn_second_coder_2026_11_02.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFORMS = ROOT / "config/reforms/mn.csv"
SHEET = ROOT / "docs/research/ordinances/mn-second-coder-2026-11-02.csv"
CODER = "codex-2026-11-02"
TAG = "Second coder (Codex, 2026-11-02)"
NOTE_CHARS = 400


def main() -> None:
    review = {r["reform_id"]: r for r in csv.DictReader(SHEET.open())}
    with REFORMS.open() as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    agreed = noted = 0
    for row in rows:
        r = review.get(row["reform_id"])
        if not r or not r["agrees (yes/no/partly)"] or TAG in row["coding_notes"]:
            continue
        verdict = r["agrees (yes/no/partly)"]
        finding = r["correct_value"] or r["second_coder_note"]
        if len(finding) > NOTE_CHARS:
            finding = finding[:NOTE_CHARS].rsplit(" ", 1)[0] + " [...]"
        row["coding_notes"] = f"{row['coding_notes']} {TAG}: {verdict}. {finding}".strip()
        noted += 1
        if verdict == "yes":
            row["coder_2"], row["coder_agreement"] = CODER, "agree"
            agreed += 1
    with REFORMS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{noted} rows noted, {agreed} marked agree")


if __name__ == "__main__":
    main()
