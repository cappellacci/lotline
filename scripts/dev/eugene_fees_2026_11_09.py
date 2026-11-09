# ruff: noqa: E501  (coding data: long notes)
"""Eugene, OR: price the known SDCs per house (D-066, Ben's option (a), 2026-11-09) -> config/fees/or.csv.
Rerunning it is safe.

    uv run python scripts/dev/eugene_fees_2026_11_09.py

Until now every Eugene row had a blank `amount_per_unit_usd`, so the fee model gave Eugene the pooled median
($6,981 per house), below its known partial bill. Option (a): code the components that are known for a
2,000 sq ft house (the WS-OR prototype, as for Portland, Bend and Salem) and carry the open question,
stormwater, in the range:

- water_sewer: EWEB water SDC, <1-inch meter, $2,276 (base) to $3,063 (upper pressure zones); local
  wastewater $546.97 + $0.1325 x 2,000 sq ft = $811.97; MWMC regional wastewater $1,990.00. The two FY26
  city rows (dollar year 2025) are in force through 2026, next to EWEB's 2026 schedule.
- impact: parks (1,501-3,000 sq ft) $7,880.61; transportation $3,759.31 (one single-family trip).
- stormwater: general capacity, medium residential, $789.99 central. Whether the LID capacity charge
  ($7,070.29) is added or is an alternative is unchecked, so the high end is both ($7,860.28).

House: central and low $17,507.88, high $25,365.17. Duplex, fourplex and ADU rows stay blank: their
category rules are open (see each row's notes), so those types take the model's fallbacks.
"""

import csv
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "fees" / "or.csv"
EUGENE = "4123850"
TAG = "Priced per unit 2026-11-09 (D-066 option (a))"

# (fee_type prefix, building type) -> (central, low, high, in_force_through, note)
SET = {
    ("Water SDC (EWEB), meter under 1 inch, base level", "SFD"): (
        "2276",
        "2276",
        "3063",
        "",
        "central the base level; high the upper-level pressure zones ($3,063).",
    ),
    ("Local wastewater SDC, per residential dwelling unit", "OTHER"): (
        "811.97",
        "",
        "",
        "2026",
        "$546.97 + $0.1325 x 2,000 sq ft = $811.97 (the per-sq-ft row stays blank, folded in here); FY26 rates in force through June 2026.",
    ),
    ("Regional wastewater SDC (MWMC), single-family/duplex", "SFD"): (
        "1990",
        "",
        "",
        "2026",
        "FY26 rates in force through June 2026.",
    ),
    ("Parks SDC, single-family 1,501-3,000 sq ft living area", "SFD"): (
        "7880.61",
        "",
        "",
        "",
        "2,000 sq ft house.",
    ),
    ("Transportation SDC, single family dwelling / duplex", "SFD"): (
        "3759.31",
        "",
        "",
        "",
        "one trip per house.",
    ),
    ("Stormwater SDC, general capacity, medium residential", "SFD"): (
        "789.99",
        "789.99",
        "7860.28",
        "",
        "central general capacity only; high adds the LID capacity charge ($7,070.29), since whether both apply is unchecked.",
    ),
}


def main() -> None:
    from lotline.config import load_fees

    with PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = list(reader.fieldnames), list(reader)
    hit = set()
    for r in rows:
        if r["jurisdiction_geoid"] != EUGENE:
            continue
        for (prefix, btype), (mid, low, high, through, note) in SET.items():
            if r["fee_type"].startswith(prefix) and r["building_type_std"] == btype:
                hit.add((prefix, btype))
                r["amount_per_unit_usd"], r["amount_per_unit_low_usd"], r["amount_per_unit_high_usd"] = (
                    mid,
                    low,
                    high,
                )
                r["in_force_through"] = through
                if TAG not in r["notes"]:
                    r["notes"] = f"{r['notes'].rstrip()} {TAG}: {note}"
    missing = set(SET) - hit
    if missing:
        raise SystemExit(f"rows not found: {sorted(missing)}")
    with tempfile.TemporaryDirectory() as tmp:  # validate before touching the real file
        check = Path(tmp) / "fees" / PATH.name
        check.parent.mkdir()
        with check.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        load_fees("or", config_dir=Path(tmp))
        shutil.copyfile(check, PATH)
    print(f"{PATH.name}: {len(hit)} Eugene rows priced, validated")


if __name__ == "__main__":
    main()
