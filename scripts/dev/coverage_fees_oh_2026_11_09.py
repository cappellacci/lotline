# ruff: noqa: E501  (coding data: long notes)
"""Fee coverage for Ohio's six largest uncoded places (manual-fee-lookups.md, priority 4) -> config/fees/oh.csv.
Rerunning it is safe.

    uv run python scripts/dev/coverage_fees_oh_2026_11_09.py

Rows live in `coverage_fees_oh_2026_11_09_rows.json` next to this script (one object per fee item, schema
columns): Columbus, Cleveland, Cincinnati, Toledo and Dayton. Components: `water_sewer` (capacity/tap/meter
charges, one meter per dwelling unit central and the master-meter case as the low end, D-069) and `permit`
(building permit, plan review, trade permits and the Ohio surcharge of ORC 3781.102: 1% for 1-3 family
dwellings, 3% for a fourplex, which the Ohio Building Code treats as nonresidential). Every place codes SFD, U2
and U3_4 rows for every item it codes (no OTHER rows). Prototypes: house 2,150 sq ft valued $354,750; duplex
2 x 1,000 sq ft valued $330,000; fourplex 4 x 1,000 sq ft valued $660,000. Plumbing fixture counts are
assumed (house 12, 8 per 1,000-sf unit) and stated in notes.

No source could be downloaded directly (the session proxy refused the city hosts), so every row was read
through the web-fetch tool: `source_quote` is blank and notes say so.

No rows for: Akron (akronohio.gov robots.txt 403, codelibrary blocked; manual lookup), Dayton water/sewer
(no posted schedule found), Toledo system development charges (only a 2022 illustration sheet found). No Ohio
place found has impact fees.

Creates `config/fees/oh.csv` with the schema header when it does not exist. Idempotent: a row is skipped when
a row with the same key already exists. Existing rows are never changed. Validated with
`lotline.config.load_fees` before writing.
"""

import csv
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEES = ROOT / "config" / "fees"
DATA = Path(__file__).with_name("coverage_fees_oh_2026_11_09_rows.json")
KEY = ("state", "jurisdiction_geoid", "year", "fee_component", "fee_type", "building_type_std")


def cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


def main() -> None:
    from lotline.config import load_fees

    new = json.loads(DATA.read_text())
    for st in sorted({r["state"].lower() for r in new}):
        path = FEES / f"{st}.csv"
        if not path.exists():
            from lotline.schemas import TABLES

            cols, rows = list(TABLES["fees"].to_schema().columns), []
        else:
            with path.open(newline="") as f:
                reader = csv.DictReader(f)
                cols, rows = list(reader.fieldnames), list(reader)
        have = {tuple(r[k] for k in KEY) for r in rows}
        added = 0
        for r in new:
            if r["state"].lower() != st:
                continue
            out = {c: cell(r.get(c)) for c in cols}
            k = tuple(out[c] for c in KEY)
            if k in have:
                continue
            rows.append(out)
            have.add(k)
            added += 1
        with tempfile.TemporaryDirectory() as tmp:  # validate before touching the real file
            check = Path(tmp) / "fees" / path.name
            check.parent.mkdir()
            with check.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
            load_fees(st, config_dir=Path(tmp))
            shutil.copyfile(check, path)
        print(f"{path.name}: +{added} rows ({len(rows)} total), validated")


if __name__ == "__main__":
    main()
