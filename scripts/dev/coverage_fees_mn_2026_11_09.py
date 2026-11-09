# ruff: noqa: E501  (coding data: long notes)
"""Fee coverage for the six largest uncoded Minnesota places (manual-fee-lookups.md, priority 4) ->
config/fees/mn.csv. Rerunning it is safe.

    uv run python scripts/dev/coverage_fees_mn_2026_11_09.py

Rows live in `coverage_fees_mn_2026_11_09_rows.json` next to this script (schema columns). Places: Plymouth
(2751730), Woodbury (2771428), Blaine (2706382), Eagan (2717288), Eden Prairie (2718116), Minnetonka (2743252).
Every place gets Met Council SAC ($2,485 per SAC unit, 2026 SAC Procedure Manual) as one OTHER water_sewer row.
Permit rows are SFD/U2/U3_4 at the model prototypes (house 2,150 sq ft $354,750; duplex 2 x 1,000 sq ft
$330,000; fourplex 4 x 1,000 sq ft $660,000); water/sewer and park rows are OTHER, priced for the house.

Eagan's fee schedules are disallowed by robots.txt and Eden Prairie publishes no adopted fee schedule online,
so both have only the SAC row. All sources were read through a web-fetch tool (direct downloads blocked by the
session proxy), so `source_quote` is blank and notes say so.

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
DATA = Path(__file__).with_name("coverage_fees_mn_2026_11_09_rows.json")
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
