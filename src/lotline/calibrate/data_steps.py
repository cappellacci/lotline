"""Runners for the data-only calibration steps (phase 2): statistics read straight from the fetched tables.

Each runner takes a `RunContext` and returns {params file: {key: value or {value, low, high}}}, rounded as
config states the value, so a rerun on unchanged data reproduces config exactly. None of these draws random
numbers, so a quick run and a full run are the same.

- `baseline_adu_share` (MS-10): ADU permits over ADU + detached single-family permits, 2019-2022, in the two
  sources that flag ADUs across many places; pooled value, the two sources as the range.
- `eligible_proxy` (D-056): k, the geometric mean of real-to-ACS eligible-lot ratios over the parcel states
  (theme ADU), with k exp(-/+ sigma) as its range, and sigma.
- `adu_reference_values` (D-060): Portland's ACS 2015-2019 median rent and home value in 2025 dollars, and the
  2015-2019 mean 30-year mortgage rate.
- `mortgage_rate_forecast`: the 2025 annual mean rate, with the lowest and highest annual means 2015-2025.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from lotline.adapters.national import geoparts
from lotline.build import eligible
from lotline.config import load_params, load_state


def _r(x: float, places: int = 0) -> float | int:
    """Round half up, as config's values are written (Python's round would give 6.59 for 6.595)."""
    q = Decimal(str(float(x))).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return int(q) if places == 0 else float(q)


# ---- baseline ADU share (MS-10) ----------------------------------------------------------------------------
ADU_SHARE_SOURCES = {"MN": "metc_residential_permits", "TX": "austin_permits"}
ADU_SHARE_YEARS = (2019, 2022)  # before the 2023 rate shock and the newest reforms; outside every holdout


def baseline_adu_share(ctx) -> dict:
    from lotline.model.scenarios.adu import adu_share_of_one_unit

    shares, adu, one = [], 0, 0
    for state, source in ADU_SHARE_SOURCES.items():
        permits = ctx.store.read(state, "permits")
        a, o = adu_share_of_one_unit(permits[permits["source"] == source], *ADU_SHARE_YEARS)
        shares.append(a / o)
        adu, one = adu + a, one + o
    value = {"value": _r(adu / one, 3), "low": _r(min(shares), 4), "high": _r(max(shares), 4)}
    return {"aggregate": {"baseline_adu_share_of_one_unit": value}}


# ---- eligible proxy (D-056) --------------------------------------------------------------------------------
PROXY_STATES = ("MN", "NC", "TX", "OH", "OR")
PROXY_THEME = "adu"


def acs_rows(state: str, store) -> pd.DataFrame:
    """`from_acs` for every jurisdiction, built as `eligible.load` builds it (no network: cached inputs)."""
    juris = store.read(state, "jurisdictions")
    acs = store.read(state, "acs_geo_year")
    cfg = load_state(state)
    places = juris.loc[juris["kind"] == "place", "geoid"].tolist()
    townships = juris.loc[juris["kind"] == "township", "geoid"].tolist()
    c_shares = geoparts.county_shares(cfg.fips, places, store)
    t_shares = geoparts.township_shares(cfg.fips, places, townships, store)
    return eligible.from_acs(acs, juris, county_shares=c_shares, township_shares=t_shares)


def proxy_pairs(state: str, store, max_gap: float) -> pd.DataFrame:
    """One row per parcel-counted jurisdiction and theme: newest roll's count and the paired ACS homes."""
    elig = store.read(state, "eligible_parcels")
    rolls = elig[(elig["denominator_source"] == "parcels") & (elig["rule_version"] == eligible.RULE_VERSION)]
    newest = rolls.sort_values("year").groupby(["jurisdiction_geoid", "theme"]).tail(1)
    acs = acs_rows(state, store)
    series = {
        k: g.set_index("year")["eligible_parcels"] for k, g in acs.groupby(["jurisdiction_geoid", "theme"])
    }
    juris = store.read(state, "jurisdictions").set_index("geoid")
    out = []
    for r in newest.itertuples():
        s = series.get((r.jurisdiction_geoid, r.theme))
        years = sorted(int(y) for y in s.index) if s is not None else []
        a = eligible._nearest_acs_year(int(r.year), years, max_gap) if s is not None else None
        out.append(
            {
                "state": state,
                "jurisdiction_geoid": r.jurisdiction_geoid,
                "name": juris["name"].get(r.jurisdiction_geoid),
                "kind": juris["kind"].get(r.jurisdiction_geoid),
                "theme": r.theme,
                "roll_year": int(r.year),
                "acs_end_year": a,
                "parcels": int(r.eligible_parcels),
                "acs_homes": float(s[a]) if a is not None else float("nan"),
            }
        )
    return pd.DataFrame(out)


def eligible_proxy(ctx) -> dict:
    from lotline.model.eligible_proxy import proxy_test

    max_gap = load_params("eligibility")["scale_max_year_gap"].value
    allp = pd.concat([proxy_pairs(s, ctx.store, max_gap) for s in PROXY_STATES], ignore_index=True)
    g = allp.dropna(subset=["acs_end_year"])
    g = g[g["theme"] == PROXY_THEME]
    totals = (
        g.groupby("state", sort=False)[["parcels", "acs_homes"]].sum().reindex(PROXY_STATES).reset_index()
    )
    res = proxy_test(totals)
    k, s = res.k, res.sigma
    return {
        "eligible_proxy": {
            "eligible_proxy_scale": {
                "value": _r(k, 3),
                "low": _r(k * math.exp(-s), 3),
                "high": _r(k * math.exp(s), 3),
            },
            "eligible_proxy_sd": {"value": _r(s, 3), "low": _r(s, 3), "high": _r(s, 3)},
        }
    }


# ---- ADU reference values (D-060) --------------------------------------------------------------------------
REFERENCE_VINTAGE = 2019  # ACS 2015-2019: Portland's mature years before COVID (E046, E047)
REFERENCE_PLACE = ("41", "59000")  # Portland, OR
REFERENCE_VARIABLES = {"rent": "B25064_001", "value": "B25077_001"}


def adu_reference_values(ctx) -> dict:
    from lotline.adapters.national import acs
    from lotline.model import money

    market = ctx.store.read("MN", "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    state, place = REFERENCE_PLACE
    get = ",".join(f"{v}E" for v in REFERENCE_VARIABLES.values())
    url = f"{acs.BASE_URL}/{REFERENCE_VINTAGE}/acs/acs5?get={get}&for=place:{place}&in=state:{state}"
    dest = ctx.store.raw(acs.SOURCE, REFERENCE_VINTAGE) / f"adu_reference_{state}_{place}.json"
    try:
        key = acs.api_key()
    except acs.CensusKeyError:
        key = None  # the cached file needs no key; a first download does
    header, row = acs._fetch_json(url, dest, ctx.store, refresh=False, key=key)
    rec = dict(zip(header, row, strict=True))
    real = {
        n: float(money.deflate(float(rec[f"{v}E"]), REFERENCE_VINTAGE, cpi, money.base_year()).iloc[0])
        for n, v in REFERENCE_VARIABLES.items()
    }
    nat = market[market["geo"] == money.NATIONAL].set_index("year")["mortgage_rate"].dropna()
    rate = _r(float(nat.loc[2015:2019].mean()), 2)

    def flat(v):
        return {"value": v, "low": v, "high": v}

    return {
        "hazard": {
            "adu_ref_rent_usd": flat(_r(real["rent"])),
            "adu_ref_home_value_usd": flat(_r(real["value"])),
            "adu_ref_mortgage_rate": flat(rate),
        }
    }


# ---- mortgage rate held over the forecast ------------------------------------------------------------------
def mortgage_rate_forecast(ctx) -> dict:
    from lotline.model import money

    market = ctx.store.read("MN", "market_geo_year")
    nat = market[market["geo"] == money.NATIONAL].set_index("year")["mortgage_rate"].dropna()
    window = nat.loc[2015:2025]
    value = {"value": _r(float(nat.loc[2025]), 2), "low": _r(float(window.min()), 2),
             "high": _r(float(window.max()), 2)}  # fmt: skip
    return {"market": {"mortgage_rate_forecast": value}}


def adu_rule_priors(ctx) -> dict:
    """D-022, D-067, saved for borrowing states (Ben 2026-11-27): what a state outside `REFORM_STATES`
    borrows, the pooled field-restriction counts and the rule priors by state and size band, as of
    31 December of each origin in `PRIOR_YEARS`. Two whole tables (CSV text), compared row by row."""
    from lotline.model.scenarios import adu_rule_inputs as ri

    return ri.borrowed_pools(ctx.store)
