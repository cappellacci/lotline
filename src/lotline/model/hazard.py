"""The ADU hazard: the yearly chance that an eligible single-family parcel adds an ADU (BUILD_PLAN §5;
two-prong design; statistical protocol §5.5-5.8; causal diagram C22).

The anchor h_ref is the mature hazard of a typical place at the reference place's (Portland, 2015-19) rent,
home value and mortgage rate, estimated from Lotline's own post-reform places (D-019 fit 3,
`scripts/dev/calibrate_adu.py`: about 1.0 per 1,000 eligible parcels a year, 90% interval 0.45-3.2; the
research band's Portland figure of about 4 per 1,000 is the comparison, not the anchor). The hazard
**transports** it to another place through the things that make an ADU worth building there, then phases it
in after adoption:

    h(t) = ramp(t) × h_mature

    h_mature = u × F(PCR) × (V / V_ref)^β_equity × exp(−β_rate × (r − r_ref)),   u = h_ref / F(PCR_ref)

- **PCR, price-to-cost ratio, from the pro forma** (`proforma.pro_forma`, ADU rented out): what the ADU is
  worth (a year's rent after vacancy and operating costs, divided by the cap rate) over what it costs to build
  (hard + soft + fees + interest while building). Rent is the place's median gross rent (ACS B25064) times
  `adu_rent_to_median_ratio`. Construction costs are national unless a local value replaces them, so with
  national costs PCR moves one-for-one with rent.
- **F, share of lots where an ADU pencils**: lots differ (garage to convert, slope, the owner's plans), so
  each lot's own ratio is taken to be lognormal around the place's PCR with spread σ
  (`adu_feasibility_dispersion`). A lot pencils when its ratio beats 1 + the owner's margin (`adu_margin`):
  F(PCR) = Φ((ln PCR − ln(1 + margin)) / σ). F rises with PCR, so more profit never lowers uptake.
- **u, uptake among lots that pencil**, is set so the reference place (Portland, 2015-19) gets h_ref:
  u = h_ref / F(PCR_ref). The reference's PCR is recomputed with the same parameters as the target's, so a
  change in costs or cap rates moves both and only the local difference (rent) transports.
- **Owner financing (C22).** ADUs are mostly paid for by owners (Portland 62% cash; about 40% used home
  equity, E045), so home equity and interest rates matter beyond the pro forma's construction loan. Equity:
  the median home value V (ACS B25077) relative to the reference's, to the power β_equity. Rates: the 30-year
  mortgage rate r relative to the reference years' mean, with semi-elasticity β_rate. Both are judgment with
  ranges that include 0 (no effect).
- **ramp(t)**, years since adoption t = 1, 2, …: a logistic with half-way point `adu_ramp_half_years` and
  steepness `adu_ramp_slope_years`: ramp(t) = 1 / (1 + exp(−(t − half) / slope)). Detached ADUs took about
  3 years to plateau in Seattle and kept rising about 6 years in Portland (adu-study-design.md).

**Outside the calibration range.** The reference cities (Portland, Seattle, Los Angeles) are high-rent; most
places Lotline covers are not. `calibration_distance` measures how far a place's rent, home value and mortgage
rate lie outside the range the reference cities span (in logs, 0 inside). The model still uses the formula
there, but `widen` multiplies each draw's hazard by exp(w·d·z − (w·d)²/2), z standard normal, which keeps
the mean and widens the range the further out the place is (`adu_extrapolation_widening` = w). z is a
transport (model) error, so the scenario shares it across places in a draw
(`scenarios.adu.extrapolation_noise`, `adu_extrapolation_shared_share`, D-027). Places outside
are flagged in the output: no silent extrapolation (protocol §5.5 step 3).

Every number comes from config/params/hazard.yaml and proforma.yaml; scripts/dev/adu_reference.py recomputes
the reference and calibration values from ACS and FRED.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np

from lotline.config import load_params
from lotline.model import proforma

FILES = ("proforma", "hazard")


def central_params(files: tuple[str, ...] = FILES) -> dict[str, float]:
    """Central values of the pro forma and hazard parameters, merged into one dict."""
    out: dict[str, float] = {}
    for name in files:
        out |= {key: p.value for key, p in load_params(name).items()}
    return out


def normal_cdf(x):
    """Standard normal CDF Φ(x), elementwise (no SciPy: Φ(x) = (1 + erf(x / √2)) / 2)."""
    erf = np.vectorize(math.erf, otypes=[float])
    return 0.5 * (1.0 + erf(np.asarray(x, dtype=float) / math.sqrt(2.0)))


def ramp(t, half_years: float, slope_years: float):
    """Share of the mature hazard reached t years after adoption: 1 / (1 + exp(−(t − half) / slope)).

    By hand, half 2, slope 0.75: t = 1 -> 1 / (1 + e^1.333) = 0.2086; t = 2 -> 0.5; t = 5 -> 0.9817.
    """
    t = np.asarray(t, dtype=float)
    return 1.0 / (1.0 + np.exp(-(t - half_years) / slope_years))


def feasible_share(price_to_cost, margin: float, dispersion: float):
    """Share of lots where an ADU pencils: Φ((ln PCR − ln(1 + margin)) / σ). 0 where PCR <= 0.

    By hand: PCR 1.1, margin 0.10 -> exactly half (Φ(0) = 0.5); PCR 1.1·e^0.5, σ 0.5 -> Φ(1) = 0.8413.
    """
    pcr = np.asarray(price_to_cost, dtype=float)
    z = (np.log(np.where(pcr > 0, pcr, 1.0)) - math.log(1.0 + margin)) / dispersion
    return np.where(pcr > 0, normal_cdf(z), 0.0)


def adu_price_to_cost(
    monthly_rent,
    fee_per_unit: float | None = None,
    params: Mapping[str, float] | None = None,
    cost_index: float = 1.0,
):
    """ADU value over its cost from the pro forma (rental), for a place's median gross rent (2025 dollars).

    value = 12 × rent × ratio × (1 − vacancy) × (1 − operating costs) / cap rate;
    cost = hard + soft + fees + interest while building (profit left out: the margin enters `feasible_share`).
    Value is linear in rent, so the pro forma runs once at $1 a month and scales. `cost_index` scales the
    hard cost per sq ft (2025 level) by a year's real construction cost relative to 2025
    (`cost_index_by_year`).
    """
    p = central_params() if params is None else dict(params)
    if cost_index != 1.0:
        p = dict(p, hard_cost_per_sqft_usd=p["hard_cost_per_sqft_usd"] * cost_index)
    fee = p["adu_fee_per_unit_usd"] if fee_per_unit is None else fee_per_unit
    unit_rent = proforma.Market(sale_price_per_sqft=0.0, monthly_rent_per_sqft=1.0 / p["adu_sqft"])
    pf = proforma.pro_forma("adu", "rental", unit_rent, fee, p)
    cost = pf.hard_cost + pf.soft_cost + pf.fees + pf.financing
    rent = np.asarray(monthly_rent, dtype=float) * p["adu_rent_to_median_ratio"]
    return rent * pf.value / cost


def adu_mature_hazard(
    monthly_rent,
    home_value,
    mortgage_rate,
    params: Mapping[str, float] | None = None,
    cost_index: float = 1.0,
):
    """Yearly chance that an eligible parcel adds an ADU once a strong reform has matured (0 to 1).

    h = u × F(PCR) × (V / V_ref)^β_equity × exp(−β_rate × (r − r_ref)), u = h_ref / F(PCR_ref), capped at 1.
    At the reference place's own rent, value, rate and cost era it returns exactly h_ref. `cost_index` is the
    target year's real construction cost relative to 2025 (1 for forward runs); the reference uses
    `adu_ref_cost_index` if a parameter set gives one (default 1: the reference priced at 2025 costs, as in
    every fit so far).
    """
    p = central_params() if params is None else params
    margin, sigma = p["adu_margin"], p["adu_feasibility_dispersion"]
    f = feasible_share(adu_price_to_cost(monthly_rent, params=p, cost_index=cost_index), margin, sigma)
    ref_index = p.get("adu_ref_cost_index", 1.0)
    f_ref = float(
        feasible_share(
            adu_price_to_cost(p["adu_ref_rent_usd"], params=p, cost_index=ref_index), margin, sigma
        )
    )
    u = p["adu_mature_hazard_ref"] / f_ref
    value = np.asarray(home_value, dtype=float)
    equity = (np.where(value > 0, value, 0.0) / p["adu_ref_home_value_usd"]) ** p["adu_equity_elasticity"]
    rate = np.exp(
        -p["adu_rate_semi_elasticity"] * (np.asarray(mortgage_rate, dtype=float) - p["adu_ref_mortgage_rate"])
    )
    return np.clip(u * f * equity * rate, 0.0, 1.0)


def cost_index_by_year(market) -> dict[int, float]:
    """Real construction cost relative to 2025: (PPI residential construction inputs / CPI-U) in year t over
    the same ratio in the base year (money.yaml), from `market_geo_year` (national)."""
    from lotline.model import money

    ppi = money.index_by_year(market, "ppi_resid_inputs")
    cpi = money.index_by_year(market, "cpi_u")
    real = (ppi / cpi).dropna()
    base = money.base_year()
    return {int(y): float(v / real.loc[base]) for y, v in real.items()}


def _outside(x, low: float, high: float):
    """How far x lies outside [low, high] in logs: log(low / x) below, log(x / high) above, 0 inside."""
    x = np.asarray(x, dtype=float)
    return np.where(x < low, np.log(low / x), np.where(x > high, np.log(x / high), 0.0))


def calibration_distance(monthly_rent, home_value, mortgage_rate, params: Mapping[str, float] | None = None):
    """Log distance outside the reference cities' range, per modifier and in total (0 = inside on all three).

    By hand, rent range 1,500-2,000: rent 1,000 -> log(1,500 / 1,000) = 0.405; rent 1,800 -> 0.
    """
    p = central_params() if params is None else params
    monthly_rent, home_value, mortgage_rate = np.broadcast_arrays(
        np.asarray(monthly_rent, dtype=float),
        np.asarray(home_value, dtype=float),
        np.asarray(mortgage_rate, dtype=float),
    )
    d = {
        "rent": _outside(monthly_rent, p["adu_calibration_rent_low_usd"], p["adu_calibration_rent_high_usd"]),
        "home_value": _outside(
            home_value, p["adu_calibration_value_low_usd"], p["adu_calibration_value_high_usd"]
        ),
        "mortgage_rate": _outside(
            mortgage_rate, p["adu_calibration_rate_low"], p["adu_calibration_rate_high"]
        ),
    }
    d["total"] = d["rent"] + d["home_value"] + d["mortgage_rate"]
    return d


def widen(hazard, distance, z, params: Mapping[str, float] | None = None):
    """Spread a hazard further the further a place lies outside the calibration range, keeping its mean.

    hazard × exp(s·z − s²/2), s = w × distance, z standard normal (one per draw and place, correlated across
    places by `scenarios.adu.extrapolation_noise`); capped at 1. Inside the range (distance 0) it returns the
    hazard unchanged.
    """
    p = central_params() if params is None else params
    s = p["adu_extrapolation_widening"] * np.asarray(distance, dtype=float)
    return np.clip(np.asarray(hazard, dtype=float) * np.exp(s * np.asarray(z) - s**2 / 2), 0.0, 1.0)
