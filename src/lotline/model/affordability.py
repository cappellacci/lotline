"""Who the new homes serve: the income a household needs for each kind of home, as a share of area median
income (AMI). Method: docs/research/lotline-ami-method.md; parameters: config/params/affordability.yaml.

This is context beside the housing need, not a forecast and not a result of the reform scenarios: the model
predicts how many homes, not what they rent for. It only re-expresses rents and costs the engine already
assumes, in a unit a housing official reads.

**Three home types.** An ADU (1 bedroom), a unit in a duplex to fourplex (2 bedrooms, priced as the
pro forma's duplex), and a new single-family house for sale (3 bedrooms), for contrast.

**Two values per home.**

- *Market*: what the engine assumes it rents or sells for. ADU rent = place median gross rent x
  `adu_rent_to_median_ratio` (hazard.yaml, as the ADU model uses it); plex rent = median rent x
  `plex_rent_to_median_ratio` (this file; the missing-middle model needs no ratio because it cancels in its
  fit); house price = the place's median home value (as the fee scenario prices a home at the margin).
- *Break-even*: the rent (or price) at which the pro forma's value equals what it costs to build:
  construction, soft costs, fees and interest while building. Land and the builder's profit are left out for
  all three types (Ben, 2026-11-19), so break-even is a floor. Rental:
  ``R_be = cost / value of $1 a month``, i.e. ``cost x cap rate / (12 x (1 - vacancy) x (1 - operating))``
  per unit. House: ``P_be = cost / (1 - selling costs)``. It moves with fees, so it is computed for three fee
  cases: today's local fees (`current`), real local fees cut in half (`fees_local_half`) and the Handbook
  benchmark (`fees`: $50,000 cut in half), each with the builder keeping (1 - λ) of the cut as the fee
  scenario assumes. ADUs carry `adu_fee_per_unit_usd` in every case: the fee scenario does not touch them.

**Income needed.** Rent: ``Y = 12 x R / 0.30``. House: the monthly cost of owning (principal and interest
at `mortgage_rate_forecast` over `mortgage_term_years` on the price less the down payment, plus property tax
and insurance) held to the same 30%.

**Share of AMI.** ``S = Y / (MFI x f(n))``, with MFI the HUD area's 4-person median family income and f the
household-size factor for ``n = 1.5 x bedrooms`` persons (IRC 42(g)(2)): a fractional size takes the mean of
the two sizes around it (1.5 persons: mean of the 1- and 2-person factors). f comes from the HUD file's own
limits (``l50_n / l50_4``) where present, else HUD's published factors (this file's fallbacks).

**Roll-up.** Places are averaged to place type and to the state, each place weighted by the homes the
matching reform adds there (ADU: the ADU scenario's median over draws; plex unit and house: the
missing-middle scenario's mean), so the figure describes the homes the model predicts, not the average town.
Each draw redraws the pro forma, the rent ratios, λ and the owning costs (triangular over each parameter's
low, central, high); P10/P50/P90 are across draws. Nothing below place type is written (S10).
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import load_params

HOME_TYPES = ("adu", "plex_unit", "house")
PROTOTYPE = {"adu": "adu", "plex_unit": "duplex", "house": "single_family"}
BEDROOMS = {"adu": "bedrooms_adu", "plex_unit": "bedrooms_plex_unit", "house": "bedrooms_house"}
RENT_KINDS = ("market", "break_even")
FEE_CASES = ("current", "fees_local_half", "fees")  # fees = the Handbook benchmark (D-065 labels)
FEE_MODE = {"fees_local_half": "local_half", "fees": "handbook"}
PLACE_TYPES = ("core", "suburb", "town", "state")
SIZES = (1, 2, 3, 4, 5)


def params() -> dict[str, float]:
    return {k: p.value for k, p in load_params("affordability").items()}


# ---- the arithmetic (each with a hand-worked test) ---------------------------------------------------------


def rent_to_income(monthly_rent, share: float = 0.30):
    """Yearly income at which a monthly housing cost is `share` of income. By hand: $1,500 -> $60,000."""
    return 12.0 * np.asarray(monthly_rent, dtype=float) / share


def household_size(bedrooms: float, persons_per_bedroom: float = 1.5) -> float:
    """Persons assumed for a unit: 1.5 per bedroom, one for a studio (IRC 42(g)(2)(C)). By hand: 2 -> 3."""
    return 1.0 if bedrooms <= 0 else persons_per_bedroom * bedrooms


def size_factors(limits: Mapping[int, float] | None = None, p: Mapping[str, float] | None = None) -> dict:
    """Household-size factor per size 1-5 relative to 4 persons: from HUD limits (l50_n / l50_4) if given,
    else HUD's published factors. By hand: limits 46,350 and 66,150 for 1 and 4 persons -> 0.7007."""
    if limits is not None and all(pd.notna(limits.get(n)) for n in SIZES) and limits[4] > 0:
        return {n: float(limits[n]) / float(limits[4]) for n in SIZES}
    p = params() if p is None else p
    return {1: p["hud_size_factor_1"], 2: p["hud_size_factor_2"], 3: p["hud_size_factor_3"], 4: 1.0} | {
        5: p["hud_size_factor_5"]
    }


def size_factor(persons: float, factors: Mapping[int, float]) -> float:
    """Factor for a household of `persons`: a fractional size takes the mean of the two around it (the
    tax-credit rule: 1.5 persons = mean of the 1- and 2-person limits). By hand: 1.5 at 0.70 and 0.80
    -> 0.75."""
    lo, hi = int(np.floor(persons)), int(np.ceil(persons))
    if lo == hi:
        return float(factors[lo])
    return float((factors[lo] + factors[hi]) / 2.0)


def ami_share(income, mfi_4person, factor):
    """Income as a share of AMI for the household size: Y / (MFI x f). By hand: $60,000 on MFI $132,300 at
    f 0.75 -> 0.6047 (60%); at f 0.90 -> 0.5039 (50%)."""
    return np.asarray(income, dtype=float) / (np.asarray(mfi_4person, dtype=float) * np.asarray(factor))


def _cost_lines(home_type: str, fee_per_unit, pf_params: Mapping[str, float]):
    """(whole-project cost to build at the fee, value of $1 a month per unit or of a $1 price, units)."""
    from lotline.model import proforma

    proto = PROTOTYPE[home_type]
    units_spec, size_key, _ = proforma.PROTOTYPES[proto]
    tenure = "for_sale" if home_type == "house" else "rental"
    sqft_unit = pf_params[size_key]
    market = (
        proforma.Market(sale_price_per_sqft=1.0 / sqft_unit, monthly_rent_per_sqft=0.0)
        if tenure == "for_sale"
        else proforma.Market(sale_price_per_sqft=0.0, monthly_rent_per_sqft=1.0 / sqft_unit)
    )
    at0 = proforma.pro_forma(proto, tenure, market, 0.0, pf_params)
    at1 = proforma.pro_forma(proto, tenure, market, 1.0, pf_params)
    per_fee_dollar = (at1.fees + at1.financing) - (at0.fees + at0.financing)  # cost is linear in the fee
    cost0 = at0.hard_cost + at0.soft_cost + at0.fees + at0.financing
    cost = cost0 + per_fee_dollar * np.asarray(fee_per_unit, dtype=float)
    return cost, at0.value / at0.units, at0.units


def break_even(home_type: str, fee_per_unit, pf_params: Mapping[str, float] | None = None):
    """Break-even monthly rent per unit (ADU, plex unit) or sale price (house), 2025 dollars: the value at
    which the pro forma's value equals hard + soft + fees + interest (no land, no profit).

    Rental, by hand at the central pro forma, ADU, no fee: hard 165 x 1.15 x 800 = $151,800; soft 20% =
    $30,360; interest 8.5% x 0.75 yr x 0.5 x $182,160 = $5,806.35; cost $187,966.35. $1 a month is worth
    12 x 0.95 x 0.65 / 0.055 = $134.73, so R_be = $1,395.16 a month.
    """
    from lotline.model import proforma

    p = proforma.central_params() if pf_params is None else pf_params
    cost, value_per_dollar, units = _cost_lines(home_type, fee_per_unit, p)
    return cost / units / value_per_dollar


def monthly_payment(principal, annual_rate_pct, years: float = 30):
    """Fixed-rate mortgage payment a month. By hand: $300,000 at 6% over 30 years -> $1,798.65."""
    r = np.asarray(annual_rate_pct, dtype=float) / 100.0 / 12.0
    n = years * 12.0
    principal = np.asarray(principal, dtype=float)
    return np.where(r > 0, principal * r / (1 - (1 + r) ** -n), principal / n)


def owner_monthly_cost(price, annual_rate_pct, p: Mapping[str, float]):
    """Monthly cost of owning: mortgage on the price less the down payment, plus property tax and insurance.
    By hand: $400,000, 10% down, 6%, 30 years, tax 1%, insurance 0.4% -> 2,158.38 + 333.33
    + 133.33 = $2,625.05.
    """
    price = np.asarray(price, dtype=float)
    loan = price * (1 - p["down_payment_share"])
    pay = monthly_payment(loan, annual_rate_pct, p["mortgage_term_years"])
    return pay + price * (p["property_tax_rate"] + p["home_insurance_rate"]) / 12.0


def weighted_mean(x, w):
    """Mean of x (... x places) weighted by w (places). By hand: x 1, 3 with weights 3, 1 -> 1.5."""
    w = np.asarray(w, dtype=float)
    return np.asarray(x, dtype=float) @ w / w.sum()


# ---- the table ---------------------------------------------------------------------------------------------


def draw_sets(n: int, seed: int) -> list[dict[str, float]]:
    """n parameter sets: the pro forma and fee parameters as the fee scenario draws them, plus the rent ratios
    and owning costs here, each triangular(low, central, high)."""
    from lotline.model.scenarios import fees

    rng = np.random.default_rng(seed)
    base = fees.draw_params(n, seed)
    specs = {k: s for k, s in load_params("affordability").items()} | {
        "adu_rent_to_median_ratio": load_params("hazard")["adu_rent_to_median_ratio"]
    }
    cols = {
        k: (np.full(n, s.value) if s.low == s.high else rng.triangular(s.low, s.value, s.high, n))
        for k, s in specs.items()
    }
    return [b | {k: float(v[i]) for k, v in cols.items()} for i, b in enumerate(base)]


def fee_for_case(home_type: str, fee_case: str, places: pd.DataFrame, p: Mapping[str, float]) -> np.ndarray:
    """Fee per unit (2025 dollars) each place's home pays in a fee case, after the builder's share
    of any cut."""
    from lotline.model.scenarios import fees

    n = len(places)
    if home_type == "adu":
        return np.full(n, p.get("adu_fee_per_unit_usd", load_params("hazard")["adu_fee_per_unit_usd"].value))
    col = "fee_plex" if home_type == "plex_unit" else "fee_house"
    if fee_case == "fees":
        f = np.full(n, p["handbook_fee_per_unit_usd"])
    else:
        f = places[col].to_numpy(dtype=float)
    if fee_case == "current":
        return f
    return f - fees.builder_saving(f, p, FEE_MODE[fee_case])


def place_values(home_type: str, rent_kind: str, fee_case: str, places: pd.DataFrame, draws, rate_pct):
    """(value, income, AMI share), each draws x places: monthly rent (or price for the house), income needed
    and its share of AMI, for one home type, rent kind and fee case."""
    a = params()
    persons = household_size(a[BEDROOMS[home_type]], a["persons_per_bedroom"])
    factor = np.array(
        [
            size_factor(persons, size_factors({n: row[f"l50_{n}"] for n in SIZES}, a))
            for _, row in places.iterrows()
        ]
    )
    value, income = [], []
    for p in draws:
        if rent_kind == "market":
            if home_type == "house":
                v = places["home_value"].to_numpy(dtype=float)
            else:
                ratio = p["adu_rent_to_median_ratio" if home_type == "adu" else "plex_rent_to_median_ratio"]
                v = places["rent"].to_numpy(dtype=float) * ratio
        else:
            v = break_even(home_type, fee_for_case(home_type, fee_case, places, p), p)
            v = np.broadcast_to(np.asarray(v, dtype=float), (len(places),))
        monthly = owner_monthly_cost(v, rate_pct, p) if home_type == "house" else v
        value.append(v)
        income.append(rent_to_income(monthly, p["rent_share_of_income"]))
    value, income = np.array(value), np.array(income)
    share = ami_share(income, places["mfi"].to_numpy(dtype=float)[None, :], factor[None, :])
    return value, income, share


def _p(a) -> tuple[float, float, float]:
    p10, p50, p90 = np.percentile(np.asarray(a, dtype=float), [10, 50, 90])
    return float(p10), float(p50), float(p90)


def table(state: str, places: pd.DataFrame, n: int | None = None, seed: int | None = None, rate_pct=None):
    """`results_affordability` rows for one state.

    `places` has one row per place: geoid, place_type, rent and home_value (2025 dollars), mfi (the HUD area's
    4-person MFI, 2025 dollars), l50_1 ... l50_5 (HUD limits, any dollar year: only their ratios are used),
    fee_house and fee_plex (local fee per unit, 2025 dollars), weight_adu and weight_mm (homes the ADU and
    missing-middle reforms add there). Places without an MFI, rent or value are left out. A home type whose
    weights sum to zero in a group is averaged with equal weights and says so in `weighting`.
    """
    a = params()
    n = int(a["affordability_draws"]) if n is None else n
    seed = int(a["affordability_seed"]) if seed is None else seed
    if rate_pct is None:
        rate_pct = load_params("market")["mortgage_rate_forecast"].value  # held flat at its central (D-030)
    places = places.dropna(subset=["mfi", "rent", "home_value"]).reset_index(drop=True)
    if places.empty:
        return pd.DataFrame(columns=COLUMNS)
    places = places.assign(place_type=places["place_type"].fillna("suburb"))
    draws = draw_sets(n, seed)
    rows = []
    for home_type in HOME_TYPES:
        weight = places["weight_adu" if home_type == "adu" else "weight_mm"].fillna(0).clip(lower=0)
        cases = [("market", "current")] + [("break_even", c) for c in FEE_CASES]
        for rent_kind, fee_case in cases:
            value, income, share = place_values(home_type, rent_kind, fee_case, places, draws, rate_pct)
            for place_type in PLACE_TYPES:
                on = (places["place_type"] == place_type).to_numpy() if place_type != "state" else None
                on = np.ones(len(places), bool) if on is None else on
                if not on.any():
                    continue
                w = weight.to_numpy()[on]
                weighting = "homes_added" if w.sum() > 0 else "places_equal"
                w = w if w.sum() > 0 else np.ones(on.sum())
                v10, v50, v90 = _p(weighted_mean(value[:, on], w))
                i10, i50, i90 = _p(weighted_mean(income[:, on], w))
                s10, s50, s90 = _p(weighted_mean(share[:, on], w))
                rows.append(
                    {
                        "state": state,
                        "home_type": home_type,
                        "place_type": place_type,
                        "rent_kind": rent_kind,
                        "fee_case": fee_case,
                        "places": int(on.sum()),
                        "weighting": weighting,
                        "mfi": float(weighted_mean(places["mfi"].to_numpy()[on], w)),
                        "value_p10": v10,
                        "value": v50,
                        "value_p90": v90,
                        "income_p10": i10,
                        "income": i50,
                        "income_p90": i90,
                        "ami_share_p10": s10,
                        "ami_share": s50,
                        "ami_share_p90": s90,
                    }
                )
    return pd.DataFrame(rows, columns=COLUMNS)


COLUMNS = [
    "state",
    "home_type",
    "place_type",
    "rent_kind",
    "fee_case",
    "places",
    "weighting",
    "mfi",
    "value_p10",
    "value",
    "value_p90",
    "income_p10",
    "income",
    "income_p90",
    "ami_share_p10",
    "ami_share",
    "ami_share_p90",
]


# ---- inputs from the engine's own places ------------------------------------------------------------------


def hud_county(market: pd.DataFrame | None) -> pd.DataFrame:
    """county_geoid -> HUD MFI and 50% limits (nominal, latest fiscal year) from `market_geo_year`."""
    cols = ["hud_mfi", *(f"hud_l50_{n}" for n in SIZES)]
    if market is None or "hud_mfi" not in market:
        return pd.DataFrame(columns=["county_geoid", "hud_year", *cols])
    m = market[market["geo"].str.startswith("county:") & market["hud_mfi"].notna()]
    m = m.sort_values("year").groupby("geo").last().reset_index()
    return pd.DataFrame(
        {"county_geoid": m["geo"].str[7:], "hud_year": m["year"].astype(int), **{c: m[c] for c in cols}}
    )


def inputs(places_adu: pd.DataFrame, run_draws: Mapping, mm_places: pd.DataFrame | None, fee_places, market):
    """The `places` frame `table` needs, from what `results.build_bundle` already has: the ADU places (rent,
    value, county, place type), the ADU draws (weights), the missing-middle per-place adds (weights), the fee
    scenario's places (local fees) and `market_geo_year` (HUD rows and CPI, to put MFI in 2025 dollars)."""
    from lotline.model import money

    p = places_adu[["geoid", "county_geoid", "rent", "home_value"]].copy()
    p["place_type"] = places_adu["place_type"] if "place_type" in places_adu else "suburb"
    added = np.asarray(run_draws["added"], dtype=float).sum(axis=2)  # draws x places
    p["weight_adu"] = np.median(added, axis=0)
    mm = (
        mm_places[["geoid", "added_homes_net_mean"]].rename(columns={"added_homes_net_mean": "weight_mm"})
        if mm_places is not None and "added_homes_net_mean" in mm_places
        else pd.DataFrame(columns=["geoid", "weight_mm"])
    )
    p = p.merge(mm, on="geoid", how="left")
    fee_cols = {"local_fee_per_unit": "fee_house", "local_fee_per_unit_U2": "fee_plex"}
    if fee_places is not None and set(fee_cols) <= set(fee_places):
        p = p.merge(fee_places[["geoid", *fee_cols]].rename(columns=fee_cols), on="geoid", how="left")
    else:
        p["fee_house"], p["fee_plex"] = np.nan, np.nan
    for c in ("fee_house", "fee_plex"):  # a place outside the fee scenario takes the state median
        p[c] = p[c].fillna(p[c].median())
    hud = hud_county(market)
    p = p.merge(hud, on="county_geoid", how="left")
    if hud.empty or p["hud_mfi"].isna().all():
        p["mfi"] = np.nan
    else:
        cpi = money.index_by_year(market, "cpi_u")
        year = p["hud_year"].clip(upper=int(cpi.index.max()))  # newest CPI year when the fiscal year has none
        p["mfi"] = money.deflate(p["hud_mfi"], year, cpi, money.base_year()).astype(float)
    return p.rename(columns={f"hud_l50_{n}": f"l50_{n}" for n in SIZES})
