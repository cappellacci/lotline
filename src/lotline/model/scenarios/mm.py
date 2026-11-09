"""Handbook missing-middle scenario: 2-6 homes in three stories allowed by right on every single-family-zoned
parcel, setbacks and coverage not binding (Handbook benchmark; analysis plan D-063, approved 2026-11-08).

For each place i and scenario year t = 1 … 5, with the fitted D-038 model (`mm_hazard.yaml`, D-055 values):

    added buildings_it ~ Poisson(θ × ramp(t − 0.5; half) × u_i × E_i × (1 − d_i) × F(PCR_i) / F(1))
    teardowns_it       ~ Binomial(added buildings_it, s × house share_i)
    added homes_it     = added buildings_it × homes per building − teardowns_it

- **θ, half, slope:** the mature hazard per eligible parcel and its ramp. The half-way point is held at its
  fitted value; D-062 showed that θ's interval with the ramp held already carries the five-year range.
- **u_i:** the place's multiplier, Gamma(mean 1, variance α), from a stream keyed by (seed, geoid), as in the
  backtests (`calibrate_mm.predict_places`).
- **E_i:** missing-middle eligible parcels (rule 1.1, D-014) from the roll nearest the origin, made
  non-overlapping as the ADU scenario does (D-020).
- **d_i:** the dose of the rules in force at the origin (`estimate_mm.rule_dose`: units grade × approval
  grade × coverage). The Handbook rule has dose 1 (four or more units by right on every single-family zone);
  the fitted effect is per unit of dose increase (D-042), so the scenario adds 1 − d_i. A place with no
  coded rule draws d from coded places in its state and size band (D-022), per draw.
- **F(PCR)/F(1):** the rental-duplex price-to-cost at the origin's ACS rent, relative to PCR = 1, with σ
  and the developer margin of the fit. A place without a rent takes the state median.
- **Homes per building:** `mm_units_per_project`, triangular. Only 2-4 unit buildings are counted (D-063
  choice 1): BPS puts 5-6 unit buildings with apartments, so the fit says nothing about them.
- **Teardowns (D-063 choice 2):** a new building on a lot with a house replaces it. The house share is the
  share of the place's missing-middle eligible parcels in its latest roll that hold a house rather than a
  vacant lot (`house_share`); ACS-fallback places count houses only, so theirs is 1. s
  (`mm_teardown_share_scale`) allows builders to favour vacant lots. D-063 wrote net homes as homes × (1 −
  teardown share); one home is lost per teardown, so the correct form is used here (noted in D-063).
- **Three stories / FAR (choice 3):** stated, not modelled; the hazard has no floor-area term.
- **Holdouts (choice 4):** no permits are read. Places enter through rolls, rules and ACS only.

Every result is a range over `mm_scenario_draws` draws: P10/P50/P90 and the mean of the statewide sum. The
baseline cancels in the added homes and is the baseline module's. Nothing is fitted here.
"""

from __future__ import annotations

import zlib
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model.hazard import feasible_share, ramp

Z_90 = 1.644854
HORIZON = 5


def specs() -> dict:
    """Every parameter the scenario uses: mm_hazard.yaml and the scenario keys of mm.yaml."""
    return load_params("mm_hazard") | load_params("mm")


def log_sd(spec) -> float:
    """Log-SD of a lognormal whose 90% interval is (low, high). By hand, θ 0.0000325-0.001006:
    (ln 0.001006 − ln 0.0000325) / 3.2897 = 3.4326 / 3.2897 = 1.0434."""
    return float((np.log(spec.high) - np.log(spec.low)) / (2 * Z_90)) if spec.low < spec.high else 0.0


def draw_params(n: int, seed: int, sp: Mapping | None = None) -> pd.DataFrame:
    """n parameter sets: θ and α lognormal with median at the estimate and log-SD from the 90% interval (as
    V9 and the ADU scenario); homes per building and the teardown scale triangular(low, value, high)."""
    sp = specs() if sp is None else sp
    rng = np.random.default_rng(seed)
    out = {}
    for key, col in (("mm_mature_hazard_ref", "theta"), ("mm_place_effect_variance", "alpha")):
        s = sp[key]
        out[col] = np.exp(np.log(s.value) + log_sd(s) * rng.standard_normal(n))
    for key, col in (("mm_units_per_project", "units"), ("mm_teardown_share_scale", "teardown_scale")):
        s = sp[key]
        out[col] = rng.triangular(s.low, s.value, s.high, n) if s.low < s.high else np.full(n, s.value)
    return pd.DataFrame(out)


def year_shape(half: float, slope: float, horizon: int = HORIZON) -> np.ndarray:
    """Share of the mature hazard in each scenario year: ramp at mid-year ages 0.5, 1.5, …"""
    return ramp(np.arange(horizon) + 0.5, half, slope)


def dose_pools(places: pd.DataFrame, min_coded: int) -> dict:
    """Doses of coded places by size band, for places with no coded rule (D-022): the band's coded doses if
    it has at least `min_coded`, else every coded place in the state; empty if none is coded (then d = 0)."""
    coded = places[places["dose"].notna()]
    every = coded["dose"].to_numpy(float)
    return {
        b: (g["dose"].to_numpy(float) if len(g) >= min_coded else every) for b, g in coded.groupby("band")
    } | {"all": every}


def _place_stream(seed: int, geoid: str) -> np.random.Generator:
    return np.random.default_rng([seed, zlib.crc32(str(geoid).encode())])


@dataclass(frozen=True)
class Result:
    buildings: np.ndarray  # draws × years, statewide added 2-4 unit buildings
    homes_gross: np.ndarray  # draws × years, homes in them
    teardowns: np.ndarray  # draws × years, houses replaced
    places: pd.DataFrame  # per place: mean added buildings and net homes over the five years, inputs
    legal: np.ndarray | None = None  # draws × 3: newly legal parcels E × (1 − d), by data tier 1, 2, 3
    pencils: np.ndarray | None = None  # draws: newly legal parcels × the lot's feasible share F(PCR)

    @property
    def homes_net(self) -> np.ndarray:
        return self.homes_gross - self.teardowns


def simulate(
    places: pd.DataFrame,
    draws: pd.DataFrame,
    half: float,
    slope: float,
    seed: int,
    min_coded: int = 5,
    horizon: int = HORIZON,
) -> Result:
    """Joint draws of the added buildings, homes and teardowns (module docstring).

    `places`: geoid, eligible, dose (NaN = no coded rule), band, f_ratio, house_share; optional data_tier
    (default 3) and f_share (F(PCR), for the funnel's pencil-out stage; default f_ratio). `draws`: one row per
    draw (theta, alpha, units, teardown_scale; `draw_params`). Every place shares a draw's parameters; its u,
    its drawn dose (if uncoded) and its counts come from its own keyed stream, so a place draws alike
    whichever places it is run with.
    """
    n = len(draws)
    shape = year_shape(half, slope, horizon)
    th, al = draws["theta"].to_numpy(), draws["alpha"].to_numpy()
    units, scale = draws["units"].to_numpy(), draws["teardown_scale"].to_numpy()
    pools = dose_pools(places, min_coded)
    bld, hom, tdn = (np.zeros((n, horizon)) for _ in range(3))
    legal, pencils = np.zeros((n, 3)), np.zeros(n)
    has_share = "f_share" in places
    rows = []
    for p in places.itertuples(index=False):
        r = _place_stream(seed, p.geoid)
        u = r.gamma(1 / al, al)
        if pd.isna(p.dose):
            pool = pools.get(p.band, pools["all"])
            d = r.choice(pool, size=n) if len(pool) else np.zeros(n)
        else:
            d = np.full(n, float(p.dose))
        gap = np.clip(1.0 - d, 0.0, 1.0)
        mu = (th * u * float(p.eligible) * gap * float(p.f_ratio))[:, None] * shape[None, :]
        b = r.poisson(mu).astype(float)
        share = np.clip(scale * float(p.house_share), 0.0, 1.0)
        t = r.binomial(b.astype(np.int64), share[:, None]).astype(float)
        h = b * units[:, None]
        bld += b
        newly = float(p.eligible) * gap
        tier = int(getattr(p, "data_tier", 3)) if pd.notna(getattr(p, "data_tier", 3)) else 3
        legal[:, min(max(tier, 1), 3) - 1] += newly
        pencils += newly * float(p.f_share if has_share else p.f_ratio)
        hom += h
        tdn += t
        rows.append(
            {"geoid": p.geoid, "added_buildings_mean": b.sum(1).mean(),
             "added_homes_net_mean": (h - t).sum(1).mean(), "dose_gap_mean": gap.mean()}
        )  # fmt: skip
    per_place = places.merge(pd.DataFrame(rows), on="geoid", how="left") if rows else places.copy()
    return Result(bld, hom, tdn, per_place, legal, pencils)


def summarize(res: Result) -> pd.DataFrame:
    """P10/P50/P90 and mean of the statewide five-year totals and of each year."""
    out = []
    for name, arr in (("buildings", res.buildings), ("homes_gross", res.homes_gross),
                      ("teardowns", res.teardowns), ("homes_net", res.homes_net)):  # fmt: skip
        cols = {"five_years": arr.sum(1)} | {f"year_{j + 1}": arr[:, j] for j in range(arr.shape[1])}
        for period, x in cols.items():
            p10, p50, p90 = np.percentile(x, [10, 50, 90])
            out.append({"measure": name, "period": period, "p10": p10, "p50": p50, "p90": p90,
                        "mean": float(x.mean())})  # fmt: skip
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------------------------------------
# Inputs from the data store
# ---------------------------------------------------------------------------------------------------------


def current_dose(rows: pd.DataFrame, as_of: pd.Timestamp, coverage, blanks, permit_grade) -> float:
    """Dose of the strongest of one place's in-force missing-middle rules on `as_of` (0 if none is live)."""
    from lotline.model.estimate_mm import rule_dose

    live = rows[(rows["effective_date"] <= as_of) & (rows["end_date"].isna() | (rows["end_date"] > as_of))]
    return max((rule_dose(r, coverage.get(r["reform_id"], 1.0), blanks, permit_grade)[0]
                for r in live.to_dict("records")), default=0.0)  # fmt: skip


def _nearest(elig: pd.DataFrame, theme: str, origin: int) -> pd.DataFrame:
    """Per jurisdiction, the newest roll <= origin, else the earliest later one (as
    `adu.places_from_store`)."""
    from lotline.build import eligible as eligible_rule

    e = elig[(elig["theme"] == theme) & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    e = e.assign(after=e["year"] > origin, gap=(e["year"] - origin).abs())
    return e.sort_values(["after", "gap"]).groupby("jurisdiction_geoid").first().reset_index()


def house_share(parcels: pd.DataFrame) -> float:
    """Share of missing-middle eligible parcels (rule 1.1) that hold a house rather than a vacant lot.
    By hand: 3 eligible houses and 1 eligible vacant lot -> 0.75; NaN if nothing is eligible."""
    from lotline.build import eligible as eligible_rule

    ok = eligible_rule.classify(parcels, "missing_middle")["eligible"].to_numpy()
    if not ok.any():
        return float("nan")
    return float((parcels["land_use_std"].to_numpy()[ok] == "SF_DETACHED").mean())


def house_shares(state: str, store) -> pd.Series:
    """`house_share` per jurisdiction from its latest parcel roll (empty if the state has no parcels)."""
    p = store.read(state, "parcels")
    if p is None or p.empty:
        return pd.Series(dtype=float)
    latest = p.groupby("jurisdiction_geoid")["vintage"].transform("max")
    p = p[p["vintage"] == latest]
    return p.groupby("jurisdiction_geoid").apply(house_share, include_groups=False).dropna()


def places_from_store(state: str, store, origin: int) -> pd.DataFrame:
    """One row per jurisdiction with missing-middle eligible parcels: every input `simulate` needs.

    Reads processed, holdout-filtered tables only: eligible parcels, jurisdictions, coded reforms, ACS rent
    and the market series. No permits are read (D-063 choice 4).
    """
    from lotline.config import load_state
    from lotline.model import estimate_mm as emm
    from lotline.model import hazard, money, rule_tags
    from lotline.model.scenarios import adu

    sp = specs()
    pa = {k: v.value for k, v in load_params("adu").items()}
    margin = load_params("proforma")["developer_margin"].value
    sigma = sp["mm_feasibility_dispersion"].value
    permit_grade = sp["mm_dose_grade_permit"].value
    elig = store.read(state, "eligible_parcels")
    mm_e = _nearest(elig, "missing_middle", origin).rename(
        columns={"jurisdiction_geoid": "geoid", "year": "parcels_year", "after": "parcels_after_origin"}
    )
    juris = store.read(state, "jurisdictions")
    places = mm_e.drop(columns="gap").merge(
        juris[["geoid", "name", "kind", "county_geoid", "in_bps", "pop_2020"]], on="geoid", how="left"
    )
    places = places[places["eligible_parcels"].fillna(0) > 0].reset_index(drop=True)
    places = adu.non_overlapping(places, juris, adu._county_shares(state, store, places))
    places["eligible"] = places["eligible_parcels"].astype(float)
    hs = places["geoid"].map(house_shares(state, store))
    # ACS-fallback denominators count houses only (no vacant lots), so their house share is 1
    acs_only = ~places["denominator_source"].isin(adu.PARCEL_SOURCES) & hs.isna()
    places["house_share_source"] = np.where(
        hs.notna(), "roll", np.where(acs_only, "acs_houses_only", "median")
    )
    places["house_share"] = hs.where(~acs_only, 1.0).fillna(hs.median()).fillna(1.0)

    reforms = {st: rule_tags.apply(adu.load_reforms(st)) for st in adu.REFORM_STATES}
    every = pd.concat([r.assign(state=st) for st, r in reforms.items()], ignore_index=True)
    blanks = emm.blank_shares(every[every["status"] == "in_force"])
    ref = reforms[state.upper()]
    mm_rows = ref[(ref["theme"] == "missing_middle") & (ref["status"] == "in_force")]
    cov = emm._mm_coverage(state.upper(), store, mm_rows, pa)
    as_of = pd.Timestamp(f"{origin}-12-31")
    coded = set(mm_rows["jurisdiction_geoid"])
    places["dose"] = [
        current_dose(mm_rows[mm_rows["jurisdiction_geoid"] == g], as_of, cov, blanks, permit_grade)
        if g in coded else np.nan
        for g in places["geoid"]
    ]  # fmt: skip
    pop = pd.to_numeric(places["pop_2020"], errors="coerce").fillna(0)
    places["band"] = adu.size_band(pop, (pa["adu_rule_band_small_max_pop"], pa["adu_rule_band_mid_max_pop"]))

    market = store.read(state, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    ci = hazard.cost_index_by_year(market)
    places["acs_geo"] = places["kind"].map(adu.ACS_PREFIX) + ":" + places["geoid"]
    acs = adu.acs_values(store.read(state, "acs_geo_year"), places["acs_geo"], origin, cpi)
    places = places.merge(acs[["rent"]], left_on="acs_geo", right_index=True, how="left")
    pcr = emm.plex_price_to_cost(places["rent"], cost_index=ci.get(origin, ci[max(ci)]))
    places["pcr"] = pcr
    f = pd.Series(np.where(np.isfinite(pcr), feasible_share(np.nan_to_num(pcr), margin, sigma), np.nan))
    f1 = float(feasible_share(1.0, margin, sigma))
    places["f_share"] = f.fillna(f.median()).fillna(f1).to_numpy()  # F(PCR): share of lots that pencil
    places["f_ratio"] = places["f_share"] / f1  # F(PCR) / F(1), the fit's feasibility term
    _ = load_state(state)  # validates the state code
    return places


def run(state: str, store, origin: int = 2025, n: int | None = None, seed: int | None = None):
    """(places, Result, summary) for one state at the scenario's parameter values."""
    sp = specs()
    n = int(sp["mm_scenario_draws"].value) if n is None else n
    seed = int(sp["mm_scenario_seed"].value) if seed is None else seed
    places = places_from_store(state, store, origin)
    res = simulate(
        places, draw_params(n, seed, sp), sp["mm_ramp_half_years"].value, sp["mm_ramp_slope_years"].value,
        seed, int(sp["mm_rule_min_coded"].value),
    )  # fmt: skip
    return places, res, summarize(res)
