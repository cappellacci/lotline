"""Pro forma: is building this housing type on this lot worth it? (methods review §2a; register C40-C48, C54).

A developer can pay for a lot only what is left after building. That leftover is the **residual land value**:

    residual land value = value of the finished building
                          − construction (hard) cost − soft cost − fees − financing − profit

- **Value.** For sale: price per sq ft × sq ft, less selling costs. For rent: a year's rent after vacancy and
  operating costs (net operating income), divided by the cap rate (what investors pay per dollar of income).
- **Hard cost** = cost per sq ft × sq ft. Buildings of 3+ attached units usually fall under the commercial
  building code (IBC), which costs more per sq ft (C43, `code_step_premium`); townhouses, duplexes and smaller
  stay under the residential code (IRC). A switch lets triplexes stay under the IRC where a place allows it.
- **Soft cost** = a share of hard cost (design, engineering, insurance, permits other than fees).
- **Fees** = fee per unit × units, so a fee cut of $25,000 per unit moves residual land value by
  $25,000 × units (plus the interest saved when fees are paid at permit, C54).
- **Financing** = interest on the money borrowed while building: rate × years × (average share of hard + soft
  cost outstanding + fees paid at permit).
- **Profit** = a margin on the finished value (the builder's hurdle, C48).

A project is **feasible** when its residual land value covers what the lot is worth in its current use, plus a
margin (C46). For an ADU the house stays, so the caller passes an existing-use value of 0.

Every number comes from config/params/proforma.yaml (2025 dollars). Market prices and rents, and fee levels,
are arguments, so a place can use its own data.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from lotline.config import load_params

# Prototype -> (units: a number or the parameter holding it, parameter for sq ft per unit, building code).
# Code "IRC" = residential, "IBC" = commercial, "IBC3" = commercial unless `triplex_under_irc` is on.
PROTOTYPES: dict[str, tuple[int | str, str, str]] = {
    "adu": (1, "adu_sqft", "IRC"),
    "single_family": (1, "single_family_sqft", "IRC"),
    "duplex": (2, "plex_unit_sqft", "IRC"),
    "triplex": (3, "plex_unit_sqft", "IBC3"),
    "fourplex": (4, "plex_unit_sqft", "IBC"),
    "townhouse": ("townhouse_units", "townhouse_sqft", "IRC"),
    "small_multifamily": ("small_multifamily_units", "plex_unit_sqft", "IBC"),
}
TENURES = ("for_sale", "rental")
# Prototype definitions and policy switches: held at their value in uncertainty runs.
NOT_SAMPLED = frozenset({"townhouse_units", "small_multifamily_units", "triplex_under_irc"})


@dataclass(frozen=True)
class Market:
    """Local market inputs, in 2025 dollars (deflate first with lotline.model.money.deflate)."""

    sale_price_per_sqft: float  # what a new home sells for, per sq ft
    monthly_rent_per_sqft: float  # what a new rental unit rents for, per sq ft per month


@dataclass(frozen=True)
class ProForma:
    """Every line of one calculation, so a reader can check it. Dollar amounts are for the whole project."""

    prototype: str
    tenure: str
    code: str  # "IRC" (residential) or "IBC" (commercial)
    units: int
    sqft: float
    value: float
    hard_cost: float
    soft_cost: float
    fees: float
    financing: float
    profit: float

    @property
    def residual_land_value(self) -> float:
        return self.value - self.hard_cost - self.soft_cost - self.fees - self.financing - self.profit

    @property
    def residual_land_value_per_unit(self) -> float:
        return self.residual_land_value / self.units


def central_params() -> dict[str, float]:
    """The central value of every pro forma parameter (config/params/proforma.yaml)."""
    return {key: p.value for key, p in load_params("proforma").items()}


def building_code(prototype: str, params: Mapping[str, float]) -> str:
    """Which building code applies: 'IRC' (residential) or 'IBC' (commercial, costs more per sq ft)."""
    code = PROTOTYPES[prototype][2]
    if code == "IBC3":
        return "IRC" if params["triplex_under_irc"] >= 0.5 else "IBC"
    return code


def pro_forma(
    prototype: str,
    tenure: str,
    market: Market,
    fee_per_unit: float,
    params: Mapping[str, float] | None = None,
) -> ProForma:
    """Run the pro forma for one prototype and tenure ('for_sale' or 'rental') in one market."""
    if prototype not in PROTOTYPES or tenure not in TENURES:
        raise ValueError(f"unknown prototype {prototype!r} or tenure {tenure!r}")
    p = central_params() if params is None else params
    units_spec, size_key, _ = PROTOTYPES[prototype]
    units = int(p[units_spec]) if isinstance(units_spec, str) else units_spec
    sqft = units * p[size_key]
    code = building_code(prototype, p)

    # Construction cost per sq ft, with the commercial-code step and the small-building (ADU) premium.
    cost_per_sqft = p["hard_cost_per_sqft_usd"]
    if code == "IBC":
        cost_per_sqft *= 1 + p["code_step_premium"]
    if prototype == "adu":
        cost_per_sqft *= 1 + p["adu_hard_cost_premium"]
    hard = cost_per_sqft * sqft
    soft = p["soft_cost_share"] * hard
    fees = fee_per_unit * units

    # Interest while building: on the average loan balance, and on fees paid up front at permit.
    years = p["construction_years_ibc"] if code == "IBC" else p["construction_years_irc"]
    borrowed = p["average_draw_share"] * (hard + soft) + p["fee_paid_at_permit"] * fees
    financing = p["construction_loan_rate"] * years * borrowed

    if tenure == "for_sale":
        value = market.sale_price_per_sqft * sqft * (1 - p["sale_cost_share"])
    else:
        rent_collected = market.monthly_rent_per_sqft * 12 * sqft * (1 - p["rental_vacancy_rate"])
        net_operating_income = rent_collected * (1 - p["operating_expense_share"])
        value = net_operating_income / p["cap_rate"]
    margin = p["adu_margin"] if prototype == "adu" else p["developer_margin"]

    return ProForma(prototype, tenure, code, units, sqft, value, hard, soft, fees, financing, margin * value)


def residual_land_value(
    prototype: str,
    tenure: str,
    market: Market,
    fee_per_unit: float,
    params: Mapping[str, float] | None = None,
) -> float:
    """What a builder could pay for the lot and still make its profit (whole project, 2025 dollars)."""
    return pro_forma(prototype, tenure, market, fee_per_unit, params).residual_land_value


def is_feasible(rlv: float, existing_use_value: float, params: Mapping[str, float] | None = None) -> bool:
    """Feasible when the residual land value beats the lot's current-use value plus a margin (C46)."""
    p = central_params() if params is None else params
    return rlv >= existing_use_value * (1 + p["existing_use_margin"])


def builder_fee_saving(fee_cut_per_unit: float, land_capture_share: float | None = None) -> float:
    """The part of a fee cut that reaches builders; the rest ends up in land prices (λ, register C18).

    Use it as the fee change in the pro forma: new fee = old fee − builder_fee_saving(cut). λ defaults to
    `land_capture_share` in config/params/fees.yaml.
    """
    lam = (
        load_params("fees")["land_capture_share"].value if land_capture_share is None else land_capture_share
    )
    return (1 - lam) * fee_cut_per_unit


def rlv_range(
    prototype: str,
    tenure: str,
    market: Market,
    fee_per_unit: float,
    draws: int = 1000,
    seed: int = 20261019,
) -> dict[str, float]:
    """Residual land value as a range: P10, P50, P90 over the parameters' plausible ranges.

    Each draw picks every parameter from a triangular distribution (low, central, high) from proforma.yaml,
    except prototype definitions and policy switches. A fixed seed makes the result reproducible.
    """
    specs = load_params("proforma")
    rng = np.random.default_rng(seed)
    columns = {
        k: (
            np.full(draws, s.value)
            if k in NOT_SAMPLED or s.low == s.high
            else rng.triangular(s.low, s.value, s.high, draws)
        )
        for k, s in specs.items()
    }
    values = [
        residual_land_value(
            prototype, tenure, market, fee_per_unit, {k: float(v[i]) for k, v in columns.items()}
        )
        for i in range(draws)
    ]
    p10, p50, p90 = np.percentile(values, [10, 50, 90])
    return {"p10": float(p10), "p50": float(p50), "p90": float(p90)}
