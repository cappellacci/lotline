# ruff: noqa: E501  (coding data: long notes)
"""Building-permit fees for the 23 places that borrowed Minnesota's pooled median (manual-fee-lookups.md,
priority 2) -> config/fees/<st>.csv. Rerunning it is safe.

    uv run python scripts/dev/permit_fees_2026_11_09.py

Rows live in `permit_fees_2026_11_09_rows.json` next to this script (one object per fee item, schema
columns). All are `fee_component = permit`: building permit, plan review, trade permits for a new building and
surcharges collected with the permit. Prototypes (same as the fee model): house SFD 2,150 sq ft valued $354,750;
duplex U2 2 x 1,000 sq ft valued $330,000; fourplex U3_4 4 x 1,000 sq ft valued $660,000. Where a place values
buildings with its own table, notes give both valuations.

Idempotent: a row is skipped when a row with the same key (state, geoid, year, fee_component, fee_type,
building_type_std) already exists. Existing rows are never changed. Each file is validated with
`lotline.config.load_fees` after writing.

Durham's 2025 building and plumbing rows carry `in_force_through = 2026`, because its electrical schedule is a
2026 file and the engine otherwise keeps only the newest year per component. Notes say when a `source_quote` was
matched word for word against Ben's local copy and when it was not (most direct downloads were blocked to the
session). Oregon rows whose only reading was a paraphrase are left out (every OR row must carry a quote): the
12% state surcharge for Portland and Salem and Salem's mechanical and electrical permits.

No rows for: Wilson (schedule link not found), Buncombe County (site blocked to the session proxy, PDF is
an image scan), Cabarrus County and Concord (Cabarrus issues Concord's permits; adopted schedule not found).
"""

import csv
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEES = ROOT / "config" / "fees"
DATA = Path(__file__).with_name("permit_fees_2026_11_09_rows.json")
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
        print(f"{path.name}: +{added} permit rows ({len(rows)} total), validated")


if __name__ == "__main__":
    main()
