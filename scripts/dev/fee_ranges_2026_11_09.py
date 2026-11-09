# ruff: noqa: E501  (coding data: long notes)
"""Fee ranges and still-in-force rows (#247, D-066) -> config/fees/<st>.csv. Rerunning it is safe.

    uv run python scripts/dev/fee_ranges_2026_11_09.py

1. Adds the schema 1.11 columns `in_force_through`, `amount_per_unit_low_usd` and `amount_per_unit_high_usd`
   to every state's fee file (blank), in schema order.
2. **Ranges (Texas).** For each group under Ben's 2026-10-30 rule (`tx_fee_rule_2026_10_30.py`: fees that vary
   by area, basin, density tier or plat date), the central row gets low = the group's smallest and high = its
   largest schedule amount. Those amounts were already in the central row's notes. Fort Worth's collection rows
   (newest plat cohort) get the 2013-2017 cohort as their low end ($469 water, $452 wastewater) and their own
   amount as high.
3. **Still in force.** `local_fees` keeps the newest year per fee component. Two coded schedules are older than
   another row of the same component but are still current, so they get `in_force_through = 2026`:
   - Austin's water and wastewater impact fees (2023 ordinance; the 2026 rows of the same component are meter,
     tap and inspection charges);
   - Bend Park & Recreation District's park SDC (FY 2025-26, the latest on BPRD's own site; the 2026 rows of the
     same component are the city's transportation SDC).
"""

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEES = ROOT / "config" / "fees"
NEW = ("in_force_through", "amount_per_unit_low_usd", "amount_per_unit_high_usd")
TAG = " Range and in-force columns 2026-11-09 (#247, D-066):"

_spec = importlib.util.spec_from_file_location(
    "txrule", ROOT / "scripts" / "dev" / "tx_fee_rule_2026_10_30.py"
)
txrule = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(txrule)

FORT_WORTH_LOW = {  # 2013-2017 plat cohort, per home (tx_fee_rule FW note)
    "Water impact fee, 5/8 x 3/4-inch meter, collected from": 469.0,
    "Wastewater impact fee, 5/8 x 3/4-inch meter, collected from": 452.0,
}
IN_FORCE = [  # (state, geoid, year, fee_type prefix, through, why)
    (
        "tx",
        "4805000",
        "2023",
        "Water impact fee, lots platted",
        2026,
        "Austin's 2023 impact-fee schedule is still the current one",
    ),
    (
        "tx",
        "4805000",
        "2023",
        "Wastewater impact fee, lots platted",
        2026,
        "Austin's 2023 impact-fee schedule is still the current one",
    ),
    (
        "or",
        "4105800",
        "2025",
        "Park SDC (BPRD)",
        2026,
        "BPRD's FY 2025-26 schedule is the latest on its own site; the city's 2026 rows are a different agency's SDC",
    ),
]


def schema_order(cols: list[str]) -> list[str]:
    from lotline.schemas import TABLES

    order = list(TABLES["fees"].to_schema().columns)
    return [c for c in order if c in cols or c in NEW] + [c for c in cols if c not in order]


def num(x: str) -> float:
    return float(x) if x not in ("", None) else float("nan")


def money(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def main() -> None:
    from lotline.config import load_fees

    for path in sorted(FEES.glob("*.csv")):
        st = path.stem
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            cols, rows = schema_order(reader.fieldnames), list(reader)
        for r in rows:
            for c in NEW:
                r.setdefault(c, "")
        changed = 0
        if st == "tx":
            for name, (geoid, year, prefix, _kind) in txrule.GROUPS.items():
                group = [
                    r
                    for r in rows
                    if r["jurisdiction_geoid"] == geoid
                    and r["year"] == year
                    and r["fee_type"].startswith(prefix)
                ]
                central = [r for r in group if r["amount_per_unit_usd"] != ""]
                assert len(central) == 1, name
                amounts = [num(r["amount_usd"]) for r in group]
                c = central[0]
                c["amount_per_unit_low_usd"], c["amount_per_unit_high_usd"] = (
                    money(min(amounts)),
                    money(max(amounts)),
                )
                if TAG not in c["notes"]:
                    c["notes"] = (
                        c["notes"].rstrip()
                        + TAG
                        + f" low and high are the smallest and largest of the {name} rows."
                    )
                changed += 1
            for r in rows:
                low = next(
                    (
                        v
                        for k, v in FORT_WORTH_LOW.items()
                        if r["jurisdiction_geoid"] == "4827000" and r["fee_type"].startswith(k)
                    ),
                    None,
                )
                if low is not None and r["amount_per_unit_usd"] != "":
                    r["amount_per_unit_low_usd"], r["amount_per_unit_high_usd"] = (
                        money(low),
                        r["amount_per_unit_usd"],
                    )
                    if TAG not in r["notes"]:
                        r["notes"] = (
                            r["notes"].rstrip()
                            + TAG
                            + " low is the 2013-2017 plat cohort; high is this row (newest cohort)."
                        )
                    changed += 1
        for state, geoid, year, prefix, through, why in IN_FORCE:
            if state != st:
                continue
            hits = [
                r
                for r in rows
                if r["jurisdiction_geoid"] == geoid and r["year"] == year and r["fee_type"].startswith(prefix)
            ]
            assert hits, (state, geoid, prefix)
            for r in hits:
                r["in_force_through"] = str(through)
                if TAG not in r["notes"]:
                    r["notes"] = r["notes"].rstrip() + TAG + f" in force through {through}: {why}."
                changed += 1
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        load_fees(st, FEES.parent)
        print(f"{path.name}: {changed} rows set")


if __name__ == "__main__":
    main()
