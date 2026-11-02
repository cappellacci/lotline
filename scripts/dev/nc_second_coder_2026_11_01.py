#!/usr/bin/env python3
"""Apply the NC second-coder review of 2026-11-01 to config/reforms/nc.csv (append-only notes).

Reads docs/research/ordinances/nc-second-coder-2026-11-01.csv (Ben's second agent, Codex, filled the
four reviewer columns). Rows the reviewer agrees with get coder_2 and coder_agreement = agree. Every reviewed
row gets the reviewer's finding appended to coding_notes. No coded value changes here: disagreements and value
changes are decided by Ben in nc-second-coder-decisions-2026-11-01.csv, applied by a later script. Idempotent.

    uv run python scripts/dev/nc_second_coder_2026_11_01.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFORMS = ROOT / "config/reforms/nc.csv"
SHEET = ROOT / "docs/research/ordinances/nc-second-coder-2026-11-01.csv"
CODER = "codex-2026-11-01"
TAG = "Second coder (Codex, 2026-11-01)"


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
