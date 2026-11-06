"""The ADU hazard: the yearly chance that an eligible single-family parcel adds an ADU (BUILD_PLAN §5;
two-prong design; statistical protocol §5.5-5.8; causal diagram C22).

The anchor h_ref is the mature hazard of a typical place at the reference place's (Portland, 2015-19) rent,
home value and mortgage rate, estimated from Lotline's own post-reform places (D-019 fit 3,
`scripts/dev/calibrate_adu.py`: about 1.0 per 1,000 eligible parcels a year, 90% interval 0.45-3.2; the
research band's Portland figure of about 4 per 1,000 is the comparison, not the anchor). The hazard
**transports** it to another place through the things that make an ADU worth building there. A rule is at
full strength from its first year (D-048, no ramp-in):

    h(t) = ramp(t) × h_mature,   ramp(t) = adu_ramp_share = 1

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
- **ramp(t)** (`adu_ramp`), years since adoption t: 1 in every year a rule is in force (D-048, adopted
  2026-11-05). Before D-048 it was a logistic with half-way point 2 years and steepness 0.75
  (`PRE_D048_RAMP`; ramp(t) = 1 / (1 + exp(−(t − half) / slope)), from Seattle's ~3 years to plateau and
  Portland's ~6). Lotline's own counts were flat or falling after reforms, not rising 3-5×, and every fit
  that could choose dropped the ramp (D-045, D-047, D-048, D-049).

**Outside the calibration range.** Since D-060 the range is where the ADU anchor's fit places sit: the
eligible-parcel-weighted 5th to 95th percentiles of rent and home value over its 316 place-years (MN, NC, OH,
TX, OR) and the mortgage rates of those years; before, it was the West Coast reference cities' range
(`PRE_D060_CALIBRATION`). `calibration_distance` measures how far a place's rent, home value and mortgage
rate lie outside that range (in logs, 0 inside). The model still uses the formula
there, but `widen` multiplies each draw's hazard by exp(w·d·z − (w·d)²/2), z standard normal, which keeps
the mean and widens the range the further out the place is (`adu_extrapolation_widening` = w). z is a
transport (model) error, so the scenario shares it across places in a draw
(`scenarios.adu.extrapolation_noise`, `adu_extrapolation_shared_share`, D-030). Places outside
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


PRE_D048_RAMP = {"adu_ramp_half_years": 2.0, "adu_ramp_slope_years": 0.75}
"""The ADU ramp before D-048 (hazard.yaml until 2026-11-05), only to reproduce D-041 and earlier fits."""

PRE_D060_CALIBRATION = {
    "adu_calibration_rent_low_usd": 1573.0,
    "adu_calibration_rent_high_usd": 2034.0,
    "adu_calibration_value_low_usd": 519222.0,
    "adu_calibration_value_high_usd": 835671.0,
    "adu_calibration_rate_low": 2.96,
    "adu_calibration_rate_high": 6.81,
}
"""The calibration range before D-060: Portland, Seattle and Los Angeles (ACS 2015-19, 2025 dollars) and
the 2015-23 mortgage rate. Kept so predictions frozen with it (V9 Oregon) regenerate whatever hazard.yaml
holds."""


def adu_ramp(t, params: Mapping[str, float]):
    """Share of the mature ADU hazard a rule has reached t years after it took effect.

    D-048: `adu_ramp_share` (1.0) in every year. A `params` carrying `adu_ramp_half_years` and
    `adu_ramp_slope_years` (`PRE_D048_RAMP`) gets the old logistic `ramp` instead, to reproduce earlier fits.
    By hand: share 1 -> t = 1, 2, 5 all give 1; with PRE_D048_RAMP, t = 1 -> 0.2086 (as `ramp`).
    """
    t = np.asarray(t, dtype=float)
    if "adu_ramp_half_years" in params:
        return ramp(t, params["adu_ramp_half_years"], params["adu_ramp_slope_years"])
    return np.full(t.shape, float(params["adu_ramp_share"]))


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
    """Log distance outside the calibration range (D-060: the fit places'), per modifier and in total
    (0 = inside on all three).

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


def widen_unseen_state(hazard, distance, z, z_state, tau: float, rule: str = "both", params=None):
    """`widen` for a place in a state outside the calibration's fit set (analysis plan D-043).

    The state multiplier exp(τ z_state), z_state one standard normal per draw shared by the state's places,
    keeps the median at the hazard. rule "both" (main) applies it on top of the widening, so the log-sds add
    in quadrature: hazard × exp(s·z − s²/2 + τ·z_state), s = w × distance. rule "larger" (sensitivity C1)
    uses whichever is bigger, τ or s, and not both. Capped at 1; τ = 0 gives `widen`.
    """
    p = central_params() if params is None else params
    s = p["adu_extrapolation_widening"] * np.asarray(distance, dtype=float)
    spread = s * np.asarray(z) - s**2 / 2
    state = tau * np.asarray(z_state)
    if rule == "both":
        log = spread + state
    elif rule == "larger":
        log = np.where(tau >= s, state, spread)
    else:
        raise ValueError(f"rule must be 'both' or 'larger', not {rule!r}")
    return np.clip(np.asarray(hazard, dtype=float) * np.exp(log), 0.0, 1.0)
