"""Texas rule and fee rows from Ben's second research workbook (2026-10-29) -> config/.

Run from the repo root: `uv run python scripts/dev/tx_research_2026_10_29.py`. The coded results live in
`docs/research/ordinances/tx-workbook-2026-10-29.json`. They were coded by five Claude subagents from the
workbook (`~/lotline-data/manual/texas/Texas-Municipal-ADU-and-Missing-Middle-Research.xlsx`) and the official
PDFs Ben downloaded beside it (`Official-PDFs/`). Neither the workbook nor the PDFs are in the repo. Like
`tx_research_2026_10_27.py`, this script only appends, and rerunning it is safe:

- `rows` with a new `reform_id` go to `config/reforms/tx.csv`;
- `notes` add a sentence to the `coding_notes` of rows coded earlier (once);
- `fee_rows` not already present go to `config/fees/tx.csv`;
- `trackers` set `status` and add a note in `docs/research/ordinances/tx-{adu,mm,fee}-lookups-todo.csv`;
- `corrections` (changes to rows coded earlier) are **not applied**. They are written to
  `tx-corrections-2026-10-29.csv` for Ben to decide, so nothing coded earlier is replaced.

A fact checked against a local official PDF names the file and page in the notes. Every other fact carries
"FLAG for second coder".
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORD = ROOT / "docs" / "research" / "ordinances"
DATA = json.loads((ORD / "tx-workbook-2026-10-29.json").read_text())
REFORMS = ROOT / "config" / "reforms" / "tx.csv"
FEES = ROOT / "config" / "fees" / "tx.csv"
TRACKERS = {t: ORD / f"tx-{t}-lookups-todo.csv" for t in ("adu", "mm", "fee")}
CORRECTIONS = ORD / "tx-corrections-2026-10-29.csv"


def read(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames), list(r)


def write(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def reforms() -> int:
    cols, rows = read(REFORMS)
    by_id = {r["reform_id"]: r for r in rows}
    for rid, note in DATA["notes"].items():
        assert rid in by_id, rid
        if note.strip() not in by_id[rid]["coding_notes"]:
            by_id[rid]["coding_notes"] = by_id[rid]["coding_notes"].rstrip() + " " + note.strip()
    added = 0
    for r in DATA["rows"]:
        assert set(r) <= set(cols), set(r) - set(cols)
        if r["reform_id"] not in by_id:
            rows.append({c: r.get(c, "") for c in cols})
            added += 1
    write(REFORMS, cols, rows)
    return added


def fees() -> int:
    cols, rows = read(FEES)
    have = {tuple(r[c] for c in cols) for r in rows}
    added = 0
    for r in DATA["fee_rows"]:
        assert set(r) <= set(cols), set(r) - set(cols)
        new = {c: str(r.get(c, "") if r.get(c) is not None else "") for c in cols}
        if tuple(new.values()) not in have:
            rows.append(new)
            have.add(tuple(new.values()))
            added += 1
    write(FEES, cols, rows)
    return added


def trackers() -> int:
    done = 0
    for table, path in TRACKERS.items():
        cols, rows = read(path)
        by_place = {r["place"]: r for r in rows}
        for t in DATA["trackers"]:
            if t["table"] != table:
                continue
            r = by_place[t["place"]]
            r["status"] = t["status"]
            if t["note"].strip() not in r["notes"]:
                r["notes"] = r["notes"].rstrip() + " | " + t["note"].strip()
            done += 1
        write(path, cols, rows)
    return done


def corrections() -> int:
    cols = ["reform_id", "field", "current", "proposed", "evidence", "decision"]
    rows = [{c: str(x.get(c, "")) for c in cols} for x in DATA["corrections"]]
    write(CORRECTIONS, cols, rows)
    return len(rows)


if __name__ == "__main__":
    print(
        f"{reforms()} rule rows, {fees()} fee rows added; {trackers()} tracker rows updated; "
        f"{corrections()} proposed corrections -> {CORRECTIONS.name}"
    )
