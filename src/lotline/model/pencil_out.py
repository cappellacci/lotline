"""Pencil-out table: does a house, a duplex or a fourplex pay for its lot, at today's fees and after a cut?
(fee plan Phase 2; office hours 2026-11-03, A5; D-073).

For one place and one building type, the pro forma (`proforma.pro_forma`) gives every line of the project.
This module runs it for three prototypes and two tenures at four fee levels and reports, per row:

- **fee per unit** and **fee per lot** (fee per unit × units): "one tap versus four" as a number.
- **cost per unit** = (hard + soft + fees + interest while building) / units, land and profit left out, and
  the **fee's share of that cost**.
- **residual land value** per lot and per unit: what is left for the land after value, cost and profit.
- **pencils**: whether that beats the lot's value in its current use plus a margin (`proforma.is_feasible`),
  when a lot value is given; otherwise left blank.

Fee levels (D-065):

- `now`: the place's local fee per unit for that type (`fee_levels.place_fees`, 2025 dollars).
- `local_half`: that fee cut by `handbook_fee_cut_share` (half).
- `handbook_50k`: the Handbook's $50,000 per unit.
- `handbook_25k`: the Handbook's benchmark after its cut ($25,000).

The table shows the full fee change in residual land value. How much of it builders keep and how much goes
to landowners (λ, `land_capture_share`) is the fee scenario's question, not this table's.

**Market inputs** (2025 dollars). For sale: the place's median home value spread over the house prototype's
size gives a price per sq ft, used for every type. For rent: the place's median gross rent per unit spread
over the plex unit's size gives a rent per sq ft, used for every type. So the house, duplex and fourplex
differ here only in size, building code and fee per unit, which is the comparison A5 asks for.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model import proforma

# Fee building type -> pro forma prototype.
TYPES = {"SFD": "single_family", "U2": "duplex", "U3_4": "fourplex"}
CASES = ("now", "local_half", "handbook_50k", "handbook_25k")
CASE_LABELS = {
    "now": "Today's local fee",
    "local_half": "Local fee cut in half",
    "handbook_50k": "Handbook: $50,000",
    "handbook_25k": "Handbook after the cut: $25,000",
}
COLUMNS = [
    "building_type",
    "prototype",
    "tenure",
    "case",
    "units",
    "fee_per_unit",
    "fee_per_lot",
    "cost_per_unit",
    "fee_share_of_cost",
    "value_per_unit",
    "rlv_per_lot",
    "rlv_per_unit",
    "lot_value",
    "pencils",
]


def central_params() -> dict[str, float]:
    """Central values of the pro forma and fee parameters this table uses."""
    out = proforma.central_params()
    out.update({k: s.value for k, s in load_params("fees").items()})
    return out


def market(home_value: float, monthly_rent: float, params: Mapping[str, float]) -> proforma.Market:
    """Price and rent per sq ft for every prototype, from a place's median home value and gross rent.

    By hand: home value $354,750 over 2,150 sq ft -> $165 a sq ft; rent $1,500 a month over 1,000 sq ft ->
    $1.50 a sq ft a month.
    """
    return proforma.Market(
        sale_price_per_sqft=float(home_value) / params["single_family_sqft"],
        monthly_rent_per_sqft=float(monthly_rent) / params["plex_unit_sqft"],
    )


def case_fee(case: str, local_fee: float, params: Mapping[str, float]) -> float:
    """Fee per unit under one of the four cases."""
    if case == "now":
        return float(local_fee)
    if case == "local_half":
        return float(local_fee) * (1 - params["handbook_fee_cut_share"])
    if case == "handbook_50k":
        return float(params["handbook_fee_per_unit_usd"])
    if case == "handbook_25k":
        return float(params["handbook_fee_per_unit_usd"]) * (1 - params["handbook_fee_cut_share"])
    raise ValueError(f"case must be one of {CASES}, not {case!r}")


def row(
    building_type: str,
    tenure: str,
    case: str,
    mkt: proforma.Market,
    fee_per_unit: float,
    lot_value: float | None,
    params: Mapping[str, float],
) -> dict:
    """One line of the table: the pro forma of one prototype and tenure at one fee per unit."""
    pf = proforma.pro_forma(TYPES[building_type], tenure, mkt, fee_per_unit, params)
    cost = pf.hard_cost + pf.soft_cost + pf.fees + pf.financing
    rlv = pf.residual_land_value
    has_lot = lot_value is not None and np.isfinite(lot_value)
    return {
        "building_type": building_type,
        "prototype": pf.prototype,
        "tenure": tenure,
        "case": case,
        "units": pf.units,
        "fee_per_unit": fee_per_unit,
        "fee_per_lot": pf.fees,
        "cost_per_unit": cost / pf.units,
        "fee_share_of_cost": pf.fees / cost if cost else np.nan,
        "value_per_unit": pf.value / pf.units,
        "rlv_per_lot": rlv,
        "rlv_per_unit": rlv / pf.units,
        "lot_value": float(lot_value) if has_lot else np.nan,
        "pencils": bool(proforma.is_feasible(rlv, float(lot_value), params)) if has_lot else None,
    }


def table(
    home_value: float,
    monthly_rent: float,
    local_fees: Mapping[str, float],
    lot_value: float | None = None,
    params: Mapping[str, float] | None = None,
    cases: tuple[str, ...] = CASES,
) -> pd.DataFrame:
    """The pencil-out table for one place: types × tenures × cases.

    `local_fees`: fee per unit by building type ('SFD', 'U2', 'U3_4'), 2025 dollars. A type without a fee is
    left out of the local cases (`now`, `local_half`) but still shown at the Handbook's levels.
    """
    p = central_params() if params is None else params
    mkt = market(home_value, monthly_rent, p)
    rows = []
    for building_type in TYPES:
        local = local_fees.get(building_type, np.nan)
        for tenure in proforma.TENURES:
            for case in cases:
                if case in ("now", "local_half") and not np.isfinite(local):
                    continue
                rows.append(row(building_type, tenure, case, mkt, case_fee(case, local, p), lot_value, p))
    return pd.DataFrame(rows, columns=COLUMNS)
