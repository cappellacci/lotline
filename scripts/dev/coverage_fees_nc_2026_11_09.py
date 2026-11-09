# ruff: noqa: E501  (coding data: long notes)
"""Fee coverage for the largest uncoded NC places (manual-fee-lookups.md, priority 4) -> config/fees/nc.csv.
Rerunning it is safe.

    uv run python scripts/dev/coverage_fees_nc_2026_11_09.py

Rows live in `coverage_fees_nc_2026_11_09_rows.json` next to this script (one object per fee item, schema
columns), following the pattern of #345 (permit_fees_2026_11_09.py). Prototypes: house SFD 2,150 sq ft valued
$354,750; duplex U2 2 x 1,000 sq ft valued $330,000; fourplex U3_4 4 x 1,000 sq ft valued $660,000. Water and
sewer follow #346: one meter per dwelling unit is central, the master-meter case is the low end.

Coded: Charlotte (Charlotte Water, fees only; no Charlotte permit or outcome data was opened), Cary (water/sewer,
permit, transportation development fee, multifamily recreation payment in lieu), Greenville (GUC water/sewer),
Gastonia (city water/sewer). Every source was read through a web-fetch summariser because direct downloads were
blocked by the session proxy, so every `source_quote` is blank and notes say so.

No rows for: Charlotte permits (Mecklenburg LUESA fee ordinance, mecknc.widen.net, blocked), Fayetteville (PWC
Section 11 fees and the city fee schedule not readable), High Point (no official FY27 schedule found), Greenville
and Gastonia permits (city manual of fees / Gaston County schedule not found).

Idempotent: a row is skipped when a row with the same key (state, geoid, year, fee_component, fee_type,
building_type_std) already exists. Existing rows are never changed. The file is validated with
`lotline.config.load_fees` before it is written.
"""

import csv
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEES = ROOT / "config" / "fees"
DATA = Path(__file__).with_name("coverage_fees_nc_2026_11_09_rows.json")
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
        print(f"{path.name}: +{added} coverage rows ({len(rows)} total), validated")


if __name__ == "__main__":
    main()
