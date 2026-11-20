# ruff: noqa: E501  (plain-language strings and notes)
"""Price one fee item for one dwelling unit of Lotline's prototype homes.

Prototype sizes and the hard cost per sq ft come from config/params/proforma.yaml (central values), so the
fees agent prices fees exactly as scripts/dev/ordinance_records.py and the coverage passes did: a 2,150 sq ft
house, 1,000 sq ft duplex and fourplex units, an 800 sq ft ADU, $165/sq ft (house valuation $354,750).
`OTHER` items apply to any building type and are priced at the house. The table of rules is in
docs/build/rule-agents/fees/DESIGN.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from lotline.config import load_params
from lotline.rule_agents.fees.records import FeeItem

ASSUMPTIONS = Path(__file__).with_name("assumptions.yaml")

# schema `basis` for each basis_kind
BASIS = {
    "per_unit": "per_unit",
    "per_building": "flat",
    "per_sqft": "per_sqft",
    "per_lue": "per_lue",
    "per_meter": "per_lue",
    "valuation_table": "other",
    "pct_of_value": "pct_of_value",
    "share_of": "other",
    "per_bedroom": "other",
    "per_fixture": "other",
    "per_trip": "other",
    "per_acre": "other",
    "conditional": "other",
    "excluded": "other",
}


@lru_cache(maxsize=1)
def assumptions() -> dict:
    return {k: v["value"] for k, v in yaml.safe_load(ASSUMPTIONS.read_text()).items()}


@dataclass(frozen=True)
class Prototype:
    building_type: str
    units: int
    sqft_per_unit: float
    hard_cost_per_sqft: float
    bedrooms_per_unit: int

    @property
    def valuation(self) -> float:
        """Building valuation used by valuation tables: units x sq ft x hard cost (2025 dollars)."""
        return self.units * self.sqft_per_unit * self.hard_cost_per_sqft


def prototypes(params: dict | None = None) -> dict[str, Prototype]:
    """Building type -> prototype, from proforma.yaml central values (or `params`: name -> number, for tests)."""
    if params is None:
        params = {k: p.value for k, p in load_params("proforma").items()}
    sqft = {
        "SFD": params["single_family_sqft"],
        "U2": params["plex_unit_sqft"],
        "U3_4": params["plex_unit_sqft"],
        "ADU": params["adu_sqft"],
    }
    sqft["OTHER"] = sqft["SFD"]
    units = assumptions()["units_per_building"]
    beds = assumptions()["bedrooms_per_unit"]
    cost = params["hard_cost_per_sqft_usd"]
    return {t: Prototype(t, int(units[t]), float(sqft[t]), float(cost), int(beds[t])) for t in sqft}


@dataclass(frozen=True)
class Priced:
    """What one dwelling unit pays for an item. `amount_per_unit` None = not paid by a typical new home."""

    amount_per_unit: float | None
    low: float | None
    high: float | None
    rule: str
    how: str  # the arithmetic, for notes


def valuation_fee(item: FeeItem, value: float) -> float | None:
    """Fee from one valuation-table bracket at building valuation `value`; None if outside the bracket."""
    start, end = item.bracket_start, item.bracket_end
    if value < start or (end is not None and value > end):
        return None
    return item.bracket_base + item.rate_per_1000 * math.ceil((value - start) / 1000)


def price(item: FeeItem, proto: Prototype, parent_building_fee: float | None = None) -> Priced:
    """Price `item` for one dwelling unit of `proto`.

    `parent_building_fee` is the whole-building fee of the item a `share_of` item is a share of (e.g. plan
    review = 65% of the building permit fee).
    """
    k, a, n = item.basis_kind, item.amount, proto.units
    v = proto.valuation
    if k == "per_unit":
        return Priced(a, None, None, k, f"${a:,.2f} per unit")
    if k == "per_building":
        return Priced(a / n, None, None, k, f"${a:,.2f} per building / {n} unit(s)")
    if k == "per_sqft":
        x = a * proto.sqft_per_unit
        return Priced(x, None, None, k, f"${a:,.4g}/sq ft x {proto.sqft_per_unit:,.0f} sq ft")
    if k == "per_lue":
        if item.units_per_dwelling is None:
            return Priced(None, None, None, k, "per LUE/EDU; units per dwelling not stated, so not priced")
        x = a * item.units_per_dwelling
        return Priced(x, None, None, k, f"${a:,.2f} x {item.units_per_dwelling:g} unit(s) per dwelling")
    if k == "per_meter":
        how = f"one meter per unit (D-069): ${a:,.2f}"
        if item.master_meter_amount is not None and n > 1:
            m = item.master_meter_amount / n
            how += f"; master meter ${item.master_meter_amount:,.2f} / {n} units = ${m:,.2f} (range)"
            return Priced(a, min(a, m), max(a, m), k, how)
        return Priced(a, None, None, k, how)
    if k == "valuation_table":
        fee = valuation_fee(item, v)
        if fee is None:
            return Priced(None, None, None, k, f"prototype valuation ${v:,.0f} outside the bracket")
        return Priced(
            fee / n, None, None, k, f"fee at prototype valuation ${v:,.0f} = ${fee:,.2f}, / {n} unit(s)"
        )
    if k == "pct_of_value":
        fee = item.pct / 100 * v
        return Priced(
            fee / n, None, None, k, f"{item.pct:g}% x valuation ${v:,.0f} = ${fee:,.2f}, / {n} unit(s)"
        )
    if k == "share_of":
        if parent_building_fee is None:
            return Priced(None, None, None, k, f"{item.pct:g}% of {item.share_of}, which is not priced")
        fee = item.pct / 100 * parent_building_fee
        return Priced(
            fee / n,
            None,
            None,
            k,
            f"{item.pct:g}% x ${parent_building_fee:,.2f} = ${fee:,.2f}, / {n} unit(s)",
        )
    if k == "per_bedroom":
        x = a * proto.bedrooms_per_unit
        return Priced(x, None, None, k, f"${a:,.2f} x {proto.bedrooms_per_unit} bedrooms (assumed)")
    if k in ("per_fixture", "per_trip"):
        if item.quantity_per_unit is None:
            return Priced(None, None, None, k, f"{k}; quantity per unit not stated, so not priced")
        x = a * item.quantity_per_unit
        return Priced(
            x, None, None, k, f"${a:,.2f} x {item.quantity_per_unit:g} ({k[4:]}s per unit, assumed)"
        )
    reason = {"per_acre": "charged on land area", "conditional": "not paid by a typical new home"}
    return Priced(None, None, None, k, reason.get(k, "excluded: " + (item.applies_when or "see notes")))


def building_fee(item: FeeItem, proto: Prototype, parent_building_fee: float | None = None) -> float | None:
    """The whole-building fee of a priced item (per-unit amount x units), for share_of parents."""
    p = price(item, proto, parent_building_fee)
    return None if p.amount_per_unit is None else p.amount_per_unit * proto.units
