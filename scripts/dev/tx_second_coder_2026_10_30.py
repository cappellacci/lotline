# ruff: noqa: E501  (coding data: long notes)
"""Ben's second-coder review (2026-10-30) -> config/reforms/tx.csv.

Run from the repo root after `tx_ben_lookups_2026_10_30.py`:
`uv run python scripts/dev/tx_second_coder_2026_10_30.py`. Rerunning it is safe.

The review is the four second-coder columns of `docs/research/ordinances/tx-second-coder-2026-10-30.csv`, filled
by Ben's review pass (an agentic review run by Ben; file `tx-second-coder-reviewed.csv` in
`~/lotline-data/manual/texas`). Of 80 rows:
- 2 are "yes". They get `coder_2 = ben-review` and `coder_agreement = agree`.
- 74 carry the same note: the reviewer "could not independently confirm" the rule from the source text. They
  stay `single_coder` and keep their FLAG. A second-coder pass that could not read the source is not
  agreement.
- 4 are "partly" with a finding. Each finding goes into the row's notes, and the row stays single-coder.
  League City's 2026 ADU row becomes `pending`: the reviewer found a public hearing and first reading, not final
  passage, so the row should not serve as a dated D-025 event until passage is confirmed.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "reforms" / "tx.csv"
SHEET = ROOT / "docs" / "research" / "ordinances" / "tx-second-coder-2026-10-30.csv"
AGREE = "agrees (yes/no/partly)"
CODER_2 = "ben-review"
TAG = " Second-coder review 2026-10-30 (ben-review, tx-second-coder-2026-10-30.csv):"
UNREAD = "The supplied reference(s)"  # the reviewer's note for rows it could not check

# reform_id -> fields to change on a "partly" row with a finding
PARTLY_FIELDS: dict[str, dict] = {
    "TX-4841980-adu-2026": {"status": "pending"},
}


def main() -> None:
    with SHEET.open(newline="") as f:
        review = {r["reform_id"]: r for r in csv.DictReader(f)}
    with PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)
    agreed = noted = 0
    for r in rows:
        v = review.get(r["reform_id"])
        if v is None or v["second_coder_note"].startswith(UNREAD) or TAG in r["coding_notes"]:
            continue
        answer = v[AGREE].strip().lower()
        note = f"{TAG} {answer}: {v['second_coder_note'].strip()}"
        if v["correct_value"].strip() and v["correct_value"].strip().lower() != "confirmed":
            note += f" Reviewer's value: {v['correct_value'].strip()}."
        if answer == "yes":
            r["coder_2"], r["coder_agreement"] = CODER_2, "agree"
            agreed += 1
        else:
            r.update(PARTLY_FIELDS.get(r["reform_id"], {}))
            noted += 1
        r["coding_notes"] = r["coding_notes"].rstrip() + note
    with PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{agreed} rows agreed, {noted} rows noted -> {PATH}")


if __name__ == "__main__":
    main()
