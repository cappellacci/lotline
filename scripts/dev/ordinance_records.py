# ruff: noqa: E501  (coding data: long notes)
"""City-ordinance pipeline records -> config/fees/<st>.csv (the `fees` schema, docs/schemas.md 1.7).

Run from the repo root:

    uv run python scripts/dev/ordinance_records.py                      # write config/fees/*.csv, print coverage
    uv run python scripts/dev/ordinance_records.py --dry-run            # print coverage only

Input: `docs/research/ordinances/batch1-2026-10-20.json` (one record per city; fee items live under
`record.fee_schedules[].items[]`). Every output row is one fee item copied from a city fee schedule.

Rules (thread 02 brief, docs/build/handoffs/02-fee-table-and-scenario.md):

- **Kept:** items whose schedule link was read (`link.read`) and that carry a verbatim quote. Everything else is
  counted in the coverage report with the reason it was dropped.
- **Dropped as not a fee:** rows that total other rows ("Estimated total"), refundable escrows, and minimum
  fees (a floor under a valuation fee, not an extra charge).
- **Building type:** single_family -> SFD; adu -> ADU; per_unit_any -> OTHER ("applies to any building type");
  duplex_to_fourplex -> U2 and/or U3_4 as the item states (a "3+ units" rate is U3_4 only; a "duplex" rate is U2
  only; "multi-family", "2-4 units" or "multiple" is both). A single-family rate whose text says a duplex pays the
  same is also written as a U2 row.
- **Basis** (schema FEE_BASIS) and **`amount_per_unit_usd`**, the cost for one dwelling unit of a typical new
  project, are set by the first rule that matches the item's text (the rule is named in `notes`):
  1. *valuation table*: "$A for the first $L plus $r per additional $1,000" -> basis `other`; amount = A + r x
     ceil((V - L) / 1000) when the prototype's valuation V falls in the bracket, else blank.
  2. *ratio*: "65% of the building permit fee" -> basis `other`; amount = ratio x the converted building permit
     fee of the same schedule and building type (blank when there is none).
  3. *pct_of_value*: the Minnesota state surcharge, 0.0005 x valuation -> `pct_of_value` = 0.05.
  4. *land-based* (per acre, per sq ft of land or plat, per front foot, land value per acre) -> blank: Lotline
     has no lot-size assumption to convert them.
  5. *conditional* (checked before 4; escrow, rezoning, variance, CUP, site plan, annexation, plat, subdivision-only, lots never
     assessed, city-installed taps) -> blank: not paid by a typical infill project.
  6. *per_lue* (per SAC/WAC/CAF unit, per tap or meter, per residential connection) -> amount, one unit per home.
  7. *per_unit* (per unit, per dwelling, per lot, per new home) -> amount.
  8. *flat* (flat, per permit, per application, per project) -> amount, one permit per home.
- **Size bands:** a fee for homes of a stated size ("single family 1,000-1,999 sq ft") counts only when the
  prototype's size per unit is inside the band.
- **Prototype valuation** (rules 1 and 3): V = units x sq ft per unit x hard cost per sq ft, central values from
  config/params/proforma.yaml (single-family 2,150 sq ft; plex units 1,000 sq ft; ADU 800 sq ft; $165/sq ft,
  2025 dollars). U3_4 uses the fourplex. OTHER rows use the single-family prototype. Per-unit = fee / units.
  Building departments value work from their own tables (often ICC), so V is an approximation; noted per row.
- **Year:** the leading year of the schedule label ("2026", "2023-current"); for fiscal-year and undated
  "current" schedules, the year the schedule took effect, else the latest year named in the label, else 2026
  (the year the record was read). `dollar_year` = `year` (the schedule's own dollars).
- **Citation:** `source` = schedule link; `source_quote` = the item's quote (at most 300 characters).
  `verified_by` stays blank: the checker's verdicts are not stored in the batch-1 JSON (noted on every row).
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RECORDS = ROOT / "docs" / "research" / "ordinances" / "batch1-2026-10-20.json"
OUT_DIR = ROOT / "config" / "fees"
READ_YEAR = 2026  # the pipeline read the records in October 2026
CHECKER_NOTE = "checker verdict not stored in batch-1 JSON"

# City name in the records -> (state, Census place GEOID), from processed jurisdictions tables.
CITY_GEOIDS: dict[str, tuple[str, str]] = {
    "Apple Valley": ("MN", "2701900"),
    "Blaine": ("MN", "2706382"),
    "Bloomington": ("MN", "2706616"),
    "Brooklyn Park": ("MN", "2707966"),
    "Burnsville": ("MN", "2708794"),
    "Coon Rapids": ("MN", "2713114"),
    "Duluth": ("MN", "2717000"),
    "Eagan": ("MN", "2717288"),
    "Eden Prairie": ("MN", "2718116"),
    "Edina": ("MN", "2718188"),
    "Lakeville": ("MN", "2735180"),
    "Maple Grove": ("MN", "2740166"),
    "Minneapolis": ("MN", "2743000"),
    "Minnetonka": ("MN", "2743252"),
    "Plymouth": ("MN", "2751730"),
    "Rochester": ("MN", "2754880"),
    "St. Cloud": ("MN", "2756896"),
    "St. Louis Park": ("MN", "2757220"),
    "St. Paul": ("MN", "2758000"),
    "Woodbury": ("MN", "2771428"),
    "Austin": ("TX", "4805000"),
    "Durham": ("NC", "3719000"),
    "Raleigh": ("NC", "3755000"),
}

# Items whose text the rules below cannot read correctly: (city, fee_type prefix) -> fields to force.
OVERRIDES: dict[tuple[str, str], dict] = {
    # "2 CAF units x $940": the amount is for the whole two-family building.
    ("Duluth", "CAF, two-family dwelling"): {"units_in_amount": 2},
    # Only lots never assessed for sewer and water pay this; most infill lots were assessed long ago.
    ("Rochester", "Maximum sewer and water connection fee"): {"rule": "conditional"},
    ("Rochester", "Sewer and water connection fee (lot"): {"rule": "conditional"},
    # Charged per unit over 2: nothing for a duplex; 2 x $ for a fourplex, i.e. half the amount per unit.
    ("Austin", "Plan review surcharge per additional dwelling unit over 2"): {
        "building_types": ["U3_4"],
        "units_in_amount": 2,
    },
}

_NUM = r"\$?\s*([\d,]+(?:\.\d+)?)"
RATIO = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:%|percent)\)?\s*(?:\(0\.\d+\)\s*)?(?:x\s*)?(?:of\s+)?(?:the\s+)?(?:building\s+)?(?:permit|inspection)\s+fee"
)
SURCHARGE = re.compile(r"0\.0005\s*x\s*valuation|x\s*0\.0005|fraction of job value")
VAL_RATE = re.compile(r"plus\s+" + _NUM + r"\s+(?:for\s+each|per|each)\s+(?:add'?l|additional)\s+\$?1,000")
VAL_FIRST = re.compile(r"(?:for\s+(?:the\s+)?first|first)\s+" + _NUM)
VAL_ABOVE = re.compile(r"above\s+" + _NUM)
VAL_RANGE = re.compile(_NUM + r"\s*(?:-|to)\s*" + _NUM)
VAL_UPTO = re.compile(r"up to(?: and including)?\s+" + _NUM)
LAND = re.compile(
    r"per (?:developable )?acre|/acre|acre land value|per sq(?:uare)?\.? ?f(?:oo)?t of (?:land|plat)|sq ?ft of plat|per front foot"
)
CONDITIONAL = re.compile(
    r"escrow|rezoning|variance|conditional use|annexation|site plan|preliminary plat|waiver of platting|"
    r"subdivision \(park\)|charged on subdivisions|only where|only if|not previously assessed|never assessed|when the city installs"
)
NOT_A_FEE = re.compile(r"\btotal\b|refundable|\bminimum\b")
LUE = re.compile(
    r"per [\w ]{0,20}?(?:sac|wac|caf)(?:/sef)? unit|/sac unit|caf unit|per tap|meter|per residential connection|1 caf unit"
)
LEADING_PER_UNIT = re.compile(
    r"\s*per (?:dwelling )?unit\b"
)  # "per unit: 2.75 persons x ... acre": per unit first
PER_UNIT = re.compile(
    r"per (?:\w+ )?(?:dwelling )?unit|per dwelling|per address|per lot|per new home|per additional dwelling|max rate per unit"
)
FLAT = re.compile(r"\bflat\b|per permit|per application|per project|lump sum|fixed charge")

# "Thoroughfare fee, single family 1,000-1,999 sq ft": counted only when the prototype's size is in the band.
SIZE_BAND = re.compile(r"(?:under|less than)\s+([\d,]+)\s*sq|([\d,]+)\s*-\s*([\d,]+)\s*sq\.? ?ft")
U3_4_ONLY = re.compile(r"3\+|three units or more|>\s*2 units|3-4 unit buildings|multiple \(80%")
U2_ONLY = re.compile(r"\bduplex\b|two-family")
U2_TOO = re.compile(r"duplex|two-family")  # a single-family rate that names duplexes as paying the same


def _money(s: str) -> float:
    return float(s.replace(",", ""))


def schedule_year(fiscal_year: str, effective: str | None) -> tuple[int, str]:
    """The year a schedule applies to, and how it was read (for `notes`)."""
    m = re.match(r"\s*(\d{4})\b", fiscal_year)
    if m:
        return int(m.group(1)), "year from schedule label"
    m = re.match(r"\s*(\d{4})", effective or "")
    if m:
        return int(m.group(1)), "year the schedule took effect"
    years = [int(y) for y in re.findall(r"\b(20\d\d)\b", fiscal_year)]
    if years:
        return max(years), "latest year named in the schedule label"
    return READ_YEAR, f"undated current schedule; coded as {READ_YEAR}, the year it was read"


def effective_date(effective: str | None) -> str | None:
    m = re.match(r"\s*(\d{4})-(\d{2})(?:-(\d{2}))?", effective or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3) or '01'}" if m else None


def building_types(applies_to: str, text: str) -> list[str]:
    if applies_to == "single_family":
        return ["SFD", "U2"] if U2_TOO.search(text) and not U3_4_ONLY.search(text) else ["SFD"]
    if applies_to == "adu":
        return ["ADU"]
    if applies_to == "per_unit_any":
        return ["OTHER"]
    if applies_to == "duplex_to_fourplex":
        if U3_4_ONLY.search(text):
            return ["U3_4"]
        if U2_ONLY.search(text) and not re.search(r"multi|triplex|fourplex|2-4|three|3 units", text):
            return ["U2"]
        return ["U2", "U3_4"]
    raise ValueError(f"unknown applies_to {applies_to!r}")


def prototypes(params: Mapping[str, float]) -> dict[str, tuple[int, float, float]]:
    """Building type -> (units, sq ft per unit, building valuation in 2025 dollars)."""
    cost = params["hard_cost_per_sqft_usd"]
    sizes = {
        "SFD": (1, params["single_family_sqft"]),
        "OTHER": (1, params["single_family_sqft"]),
        "ADU": (1, params["adu_sqft"]),
        "U2": (2, params["plex_unit_sqft"]),
        "U3_4": (4, params["plex_unit_sqft"]),
    }
    return {b: (n, sqft, n * sqft * cost) for b, (n, sqft) in sizes.items()}


def size_band(fee_type: str) -> tuple[float, float] | None:
    """(low, high) sq ft per unit when a fee applies only to homes of a size band, else None."""
    m = SIZE_BAND.search(fee_type.lower())
    if not m:
        return None
    if m.group(1):
        return 0.0, _money(m.group(1))
    return _money(m.group(2)), _money(m.group(3)) + 1


def valuation_bracket(item: Mapping) -> tuple[float, float, float, float] | None:
    """(base fee, bracket start L, bracket end U, $ per additional $1,000), or None if not a valuation table."""
    text = " ".join(str(item.get(k) or "") for k in ("basis", "quote", "fee_type"))
    rate = VAL_RATE.search(text)
    if not rate:
        return None
    first = VAL_FIRST.search(text) or VAL_ABOVE.search(text)
    rng = VAL_RANGE.search(str(item.get("fee_type") or ""))
    upto = VAL_UPTO.search(text)
    if first:
        lower = _money(first.group(1))
    elif rng:
        lower = math.floor(_money(rng.group(1)) / 1000) * 1000  # "$100,001" -> 100,000
    else:
        return None
    upper = _money(rng.group(2)) if rng else (_money(upto.group(1)) if upto else None)
    if upper is None or upper <= lower:
        return None
    return float(item["amount_usd"]), lower, upper, _money(rate.group(1))


def classify(city: str, item: Mapping) -> str:
    """Name of the first rule that matches the item (see module docstring)."""
    for (c, prefix), fields in OVERRIDES.items():
        if c == city and item["fee_type"].startswith(prefix) and "rule" in fields:
            return fields["rule"]
    text = f"{item['fee_type']} | {item['basis']}".lower()
    if NOT_A_FEE.search(item["fee_type"].lower()) or "refundable" in text:
        return "not_a_fee"
    if valuation_bracket(item):  # before ratio: a bracket's text may also mention the plan-review share
        return "valuation_table"
    if RATIO.search(text):
        return "ratio"
    if SURCHARGE.search(text):
        return "pct_of_value"
    if CONDITIONAL.search(text):
        return "conditional"
    if LEADING_PER_UNIT.match(item["basis"].lower()):
        return "per_unit"
    if LAND.search(text):
        return "land_based"
    if LUE.search(text):
        return "per_lue"
    if PER_UNIT.search(text):
        return "per_unit"
    if FLAT.search(text):
        return "flat"
    return "unrecognised"


BASIS = {
    "ratio": "other",
    "pct_of_value": "pct_of_value",
    "valuation_table": "other",
    "land_based": "other",
    "conditional": "other",
    "per_lue": "per_lue",
    "per_unit": "per_unit",
    "flat": "flat",
    "unrecognised": "other",
}


def convert(records: Iterable[Mapping], params: Mapping[str, float]) -> tuple[pd.DataFrame, list[dict]]:
    """Records -> (fee rows in the `fees` schema, dropped items with reasons)."""
    protos = prototypes(params)
    rows: list[dict] = []
    dropped: list[dict] = []
    for rec in records:
        city = rec["city"]
        state, geoid = CITY_GEOIDS[city]
        for sched in rec["record"].get("fee_schedules") or []:
            year, year_how = schedule_year(sched["fiscal_year"], sched.get("effective"))
            sched_rows: list[dict] = []
            for item in sched["items"]:
                base = {"city": city, "year": year, "fee_type": item["fee_type"]}
                if not sched["link"].get("read"):
                    dropped.append({**base, "reason": "schedule link not read"})
                    continue
                if not (item.get("quote") or "").strip():
                    dropped.append({**base, "reason": "no quote"})
                    continue
                rule = classify(city, item)
                if rule == "not_a_fee":
                    dropped.append({**base, "reason": "not a fee (total, refundable escrow or minimum)"})
                    continue
                text = f"{item['fee_type']} | {item['basis']}".lower()
                override = next(
                    (f for (c, p), f in OVERRIDES.items() if c == city and item["fee_type"].startswith(p)), {}
                )
                btypes = override.get("building_types") or building_types(item["applies_to"], text)
                band = size_band(item["fee_type"])
                for btype in btypes:
                    units, sqft, value = protos[btype]
                    amount: float | None = float(item["amount_usd"])
                    per_unit: float | None = None
                    pct: float | None = None
                    how = rule
                    if rule == "valuation_table":
                        fee0, lower, upper, rate = valuation_bracket(item)
                        if lower < value <= upper:
                            fee = fee0 + rate * math.ceil((value - lower) / 1000)
                            per_unit = fee / units
                            how += (
                                f": fee at prototype valuation ${value:,.0f} = ${fee:,.2f}, / {units} unit(s)"
                            )
                        else:
                            how += f": prototype valuation ${value:,.0f} outside ${lower:,.0f}-${upper:,.0f}"
                    elif rule == "pct_of_value":
                        amount, pct = None, 0.05
                        per_unit = 0.0005 * value / units
                        how += f": 0.0005 x prototype valuation ${value:,.0f}, / {units} unit(s)"
                    elif rule == "ratio":
                        amount = None
                        how += f": {RATIO.search(text).group(1)}% of the building permit fee"
                    elif rule in ("per_lue", "per_unit", "flat") and band and not band[0] <= sqft < band[1]:
                        how += f": for homes of {band[0]:,.0f}-{band[1]:,.0f} sq ft; prototype is {sqft:,.0f} sq ft, so not in per-unit total"
                    elif rule in ("per_lue", "per_unit", "flat"):
                        per_unit = float(item["amount_usd"]) / override.get("units_in_amount", 1)
                        how += {
                            "per_lue": ": one SAC/WAC/meter unit per home",
                            "per_unit": "",
                            "flat": ": one permit per home",
                        }[rule]
                        if "units_in_amount" in override:
                            how += f"; amount covers {override['units_in_amount']} units"
                    elif rule == "land_based":
                        how += ": charged on land area or frontage; not converted (no lot-size assumption)"
                    elif rule == "conditional":
                        how += ": not paid by a typical infill project; not in per-unit total"
                    else:
                        how += ": basis not recognised; not converted"
                    if btype == "OTHER":
                        how += "; applies to any building type"
                    if rule in ("valuation_table", "pct_of_value"):
                        how += " (valuation = units x sq ft x $/sq ft, proforma.yaml central; city valuation tables differ)"
                    sched_rows.append(
                        {
                            "state": state,
                            "jurisdiction_geoid": geoid,
                            "year": year,
                            "effective_date": effective_date(sched.get("effective")),
                            "fee_component": item["component"],
                            "fee_type": item["fee_type"],
                            "building_type_std": btype,
                            "basis": BASIS[rule],
                            "amount_usd": amount,
                            "amount_per_unit_usd": None if per_unit is None else round(per_unit, 2),
                            "pct_of_value": pct,
                            "dollar_year": year,
                            "payment_timing": None,
                            "source": sched["link"]["url"],
                            "source_section": None,
                            "source_quote": item["quote"].strip()[:300],
                            "verified_by": None,
                            "verified_date": None,
                            "notes": f"{city}; schedule '{sched['fiscal_year']}' ({year_how}); "
                            f"record basis: {item['basis']}; rule {how}; {CHECKER_NOTE}",
                            "_rule": rule,
                            "_ratio": float(RATIO.search(text).group(1)) / 100 if rule == "ratio" else None,
                        }
                    )
            _fill_ratios(sched_rows)
            rows.extend(sched_rows)
    df = pd.DataFrame(rows)
    return df, dropped


def _fill_ratios(rows: list[dict]) -> None:
    """Plan review etc.: ratio x the same schedule's converted building permit fee for that building type."""
    permit = defaultdict(list)
    for r in rows:
        if r["_rule"] == "valuation_table" and r["amount_per_unit_usd"] is not None:
            permit[r["building_type_std"]].append(r["amount_per_unit_usd"])
    for r in rows:
        if r["_rule"] != "ratio":
            continue
        # A ratio row coded OTHER applies to the single-family permit fee too (and vice versa).
        found = permit.get(r["building_type_std"]) or permit.get(
            "OTHER" if r["building_type_std"] == "SFD" else "SFD" if r["building_type_std"] == "OTHER" else ""
        )
        if found and len(found) == 1:
            r["amount_per_unit_usd"] = round(r["_ratio"] * found[0], 2)
            r["notes"] += f"; x converted building permit fee ${found[0]:,.2f}"
        else:
            r["notes"] += "; no single converted building permit fee in this schedule, so not converted"


def coverage(df: pd.DataFrame, dropped: list[dict]) -> str:
    """Markdown coverage report: cities x years x components, plus what was dropped and why."""
    lines = [
        "| City | Year | " + " | ".join(COMPONENTS) + " | Rows | Per-unit $ (SFD+OTHER) |",
        "|---|---|" + "---|" * (len(COMPONENTS) + 2),
    ]
    names = {g: c for c, (_, g) in CITY_GEOIDS.items()}
    if len(df):
        for (geoid, year), g in df.groupby(["jurisdiction_geoid", "year"]):
            counts = g["fee_component"].value_counts()
            sfd = g[g["building_type_std"].isin(["SFD", "OTHER"])]["amount_per_unit_usd"].sum()
            cells = [str(counts.get(c, "")) for c in COMPONENTS]
            lines.append(f"| {names[geoid]} | {year} | " + " | ".join(cells) + f" | {len(g)} | {sfd:,.0f} |")
    have = set(df["jurisdiction_geoid"]) if len(df) else set()
    none = sorted(c for c, (_, g) in CITY_GEOIDS.items() if g not in have)
    lines += [
        "",
        f"Cities with no usable fee rows: {', '.join(none) or 'none'}.",
        "",
        "| Dropped because | Items |",
        "|---|---|",
    ]
    for reason, n in Counter(d["reason"] for d in dropped).most_common():
        lines.append(f"| {reason} | {n} |")
    if len(df):
        lines += ["", "| Rule | Rows | With per-unit $ |", "|---|---|---|"]
        for rule, g in df.groupby("_rule"):
            lines.append(f"| {rule} | {len(g)} | {g['amount_per_unit_usd'].notna().sum()} |")
    return "\n".join(lines)


COMPONENTS = ["permit", "planning", "water_sewer", "impact", "other"]


def write(df: pd.DataFrame, out_dir: Path = OUT_DIR) -> list[Path]:
    """One CSV per state, columns in schema order, sorted; validated with lotline.config.load_fees."""
    from lotline.config import load_fees
    from lotline.schemas import TABLES

    cols = list(TABLES["fees"].to_schema().columns)
    paths = []
    for state, g in df.groupby("state"):
        g = g.sort_values(["jurisdiction_geoid", "year", "fee_component", "fee_type", "building_type_std"])
        path = out_dir / f"{state.lower()}.csv"
        g[cols].to_csv(path, index=False)
        load_fees(state, out_dir.parent)
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> None:
    from lotline.model.proforma import central_params

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--records", type=Path, default=RECORDS)
    ap.add_argument("--dry-run", action="store_true", help="print the coverage report only")
    args = ap.parse_args(argv)
    df, dropped = convert(json.loads(args.records.read_text()), central_params())
    print(coverage(df, dropped))
    if not args.dry_run:
        for p in write(df):
            print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
