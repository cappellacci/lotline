"""V9 Oregon transfer prediction (analysis plan D-046; validation plan V9).

Predicts Oregon's 2018-2025 outcomes from the four-state calibration, before any Oregon outcome after 2017 is
seen (holdout `V9-OR-TRANSFER`). Two kinds of target:

- **ADU permits** per year for named places (Portland, Bend). For place i, year t and draw d:

      mu_it = R_i,t-1 × h_m(rent_t, value_t, rate_t; p_d) × widen(z_d) × u_i × s_d
              × max_r c_r × cov_r × ramp(age_rt)
      y_it ~ Poisson(mu_it),  R_it = R_i,t-1 − mu_it,  R_i0 = eligible parcels

  c_r is 1 for a rule at the Handbook standard, `adu_partial_rule_share` for a restricted one, and for a rule
  whose blank fields may restrict (D-022) partial with probability q_r, drawn once per draw and place. u_i is
  the place multiplier (gamma, mean 1, variance α_d) and s_d the unseen-state multiplier (D-043:
  `adu_state_effect_sd`, 0 if absent). Parameters p_d come from `scenarios.adu.draw_params` (D-030). This is
  `calibrate_adu.place_years` without its permit-coverage filter and observed-rate floor, which need the
  blind Oregon permits.

  **Own-history variant (D-049).** Each place's published ADU permits before 2018 update u_i, draw by draw:
  with M_i the expected pre-2018 permits at u_i = 1 under the same draw (same p_d, z_d, s_d and rule reading)
  and Y_i the counts, u_i | history ~ Gamma(shape 1/α_d + Y_i, rate 1/α_d + M_i), the gamma-Poisson
  posterior. Both variants are frozen.

- **New 2-4 unit buildings** (BPS) per year for every jurisdiction a missing-middle rule reaches in
  2018-2025, and their sum. As D-038, y_it ~ Poisson(B_i + θ_d u_i k_it), with:
  - B_i: the mean of 2015-2017, held flat;
  - k_it = eligible × (dose_t − dose_2017) × F(PCR)/F(1) × ramp(t − T + 0.5), T the first year a rule
    raises the dose above 2017's (B already holds what 2017's rules produce).

  θ and α are lognormal from `mm_hazard.yaml`'s intervals. The ramp's half-way point and σ stay at their
  values (D-038 fitted them with θ).

Inputs come only from holdout-filtered tables (DataStore) and `config/`. Nothing here reads an outcome after
2017 for Oregon.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

YEARS = tuple(range(2018, 2026))
SUBTOTAL_LAST = 2022  # D-046: also scored on 2018-2022
BASELINE_YEARS = (2015, 2016, 2017)
ADU_TARGETS = {"4159000": "Portland", "4105800": "Bend"}
TEST_ID = "V9-OR-TRANSFER"
ROLL_LAST_YEAR = 2017  # newest eligible-parcel roll the freeze may use
CLASS_CODE = {"handbook": 0, "partial": 1, "blank": 2}
HISTORY_FILE = Path("config/validation/or_adu_history.csv")  # D-049, repo-relative


# ---------------------------------------------------------------------------------------------------------
# ADU
# ---------------------------------------------------------------------------------------------------------


@dataclass
class AduInputs:
    """Place-by-year inputs. Rule arrays are (places, years, rules), padded with cov = 0 (no rule)."""

    geoids: list[str]
    names: list[str]
    years: np.ndarray
    eligible: np.ndarray  # (places,)
    rent: np.ndarray  # (places, years), 2025 dollars
    value: np.ndarray
    rate: np.ndarray  # (years,) actual 30-year mortgage rate
    cls: np.ndarray  # (places, years, rules) CLASS_CODE
    age: np.ndarray  # years since the rule took effect, at 1 July
    q: np.ndarray  # P(a blank field restricts), class 'blank' only
    cov: np.ndarray  # coverage share, 0 = no rule


def adu_rules_in_force(reforms, all_reforms, geoid: str, fips: str, year: int, fp, params) -> list[tuple]:
    """(class, age, q, coverage) of each ADU rule in force on 1 July of `year`, as `place_years` reads them;
    an explicit "no ADUs" row is not a rule."""
    from lotline.model.scenarios import adu

    mid = pd.Timestamp(f"{year}-07-01")
    mine = reforms[reforms["jurisdiction_geoid"].isin([geoid, fips])]
    out = []
    for r in mine.itertuples():
        if not (r.effective_date <= mid and (pd.isna(r.end_date) or r.end_date > mid)):
            continue
        rubric = adu.with_parking(adu._resolved(reforms, r.reform_id), all_reforms, geoid, mid)
        if adu._no_adus(rubric):
            continue
        fails, unknown = adu.rule_restrictions(rubric)
        q = 1 - float(np.prod([1 - fp[f] for f in unknown])) if unknown and not fails else 0.0
        cls = "partial" if fails else ("blank" if q > 0 else "handbook")
        cov = adu.rule_coverage(r._asdict(), None, params)[0]
        out.append((cls, (mid - r.effective_date).days / 365.25, q, cov))
    return out


def adu_inputs(state: str, store, geoids: Sequence[str], years: Sequence[int] = YEARS) -> AduInputs:
    """Inputs for `adu_draws` from processed tables: eligible parcels from the newest roll <= 2017, ACS rent
    and value from the newest vintage <= each year, the year's actual mortgage rate, coded rules in force."""
    from lotline.build import eligible as eligible_rule
    from lotline.config import load_params, load_state
    from lotline.model import money
    from lotline.model.scenarios import adu

    years = np.array(list(years))
    p = adu.central_params()
    market = store.read(state, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    rates = market[market["geo"] == money.NATIONAL].set_index("year")["mortgage_rate"]
    acs = store.read(state, "acs_geo_year")
    juris = store.read(state, "jurisdictions").set_index("geoid")
    elig = store.read(state, "eligible_parcels")
    elig = elig[
        (elig["theme"] == "adu")
        & (elig["rule_version"] == eligible_rule.RULE_VERSION)
        & (elig["year"] <= ROLL_LAST_YEAR)
    ]
    fips = load_state(state).fips
    all_reforms = adu.load_reforms(state)
    reforms = all_reforms[(all_reforms["theme"] == "adu") & (all_reforms["status"] == "in_force")]
    every = pd.concat([adu.load_reforms(st).assign(state=st) for st in adu.REFORM_STATES], ignore_index=True)
    fcounts = adu.field_restrict_counts(every, pd.Timestamp.today().normalize())
    fp = adu.field_probabilities(fcounts, state, int(load_params("adu")["adu_rule_min_coded"].value))

    n_p, n_y = len(geoids), len(years)
    rules = [
        [adu_rules_in_force(reforms, all_reforms, g, fips, int(y), fp, p) for y in years] for g in geoids
    ]
    width = max([len(r) for row in rules for r in row] + [1])
    cls = np.zeros((n_p, n_y, width), dtype=int)
    age, q, cov = (np.zeros((n_p, n_y, width)) for _ in range(3))
    rent, value = np.full((n_p, n_y), np.nan), np.full((n_p, n_y), np.nan)
    eligible = np.zeros(n_p)
    for i, g in enumerate(geoids):
        e = elig[elig["jurisdiction_geoid"] == g].sort_values("year")
        if e.empty:
            raise ValueError(f"{g}: no eligible-parcel roll <= {ROLL_LAST_YEAR}")
        eligible[i] = float(e["eligible_parcels"].iloc[-1])
        kind = juris.loc[g, "kind"] if g in juris.index else "place"
        geo = f"{adu.ACS_PREFIX.get(kind, 'place')}:{g}"
        for j, y in enumerate(years):
            v = adu.acs_values(acs, pd.Series([geo]), int(y), cpi)
            if not v.empty:
                rent[i, j], value[i, j] = v.iloc[0]["rent"], v.iloc[0]["home_value"]
            for r, (c, a, qq, cv) in enumerate(rules[i][j]):
                cls[i, j, r], age[i, j, r], q[i, j, r], cov[i, j, r] = CLASS_CODE[c], a, qq, cv
    if np.isnan(rent).any() or np.isnan(value).any():
        raise ValueError("missing ACS rent or home value for an ADU target")
    names = [str(juris["name"].get(g, g)) for g in geoids]
    rate = np.array([float(rates[int(y)]) for y in years])
    return AduInputs(list(geoids), names, years, eligible, rent, value, rate, cls, age, q, cov)


def rule_factor(inp: AduInputs, partial_share: float, blank_partial: np.ndarray, half: float, slope: float):
    """max over rules of c × coverage × ramp(age): (places, years). `blank_partial` (places,) is True where
    this draw reads a blank-field rule as restricted."""
    from lotline.model import hazard

    c = np.where(inp.cls == CLASS_CODE["partial"], partial_share, 1.0)
    blank = inp.cls == CLASS_CODE["blank"]
    c = np.where(blank & blank_partial[:, None, None], partial_share, c)
    f = c * inp.cov * hazard.ramp(inp.age, half, slope)
    return np.where(inp.cov > 0, f, 0.0).max(axis=2)


@dataclass
class AduHistory:
    """Pre-2018 ADU permits for the ADU targets (D-049). `inputs` covers the history years, in the same place
    order as the prediction's inputs; `eligible` (places, years) is the newest roll at or before each year;
    `counts` (places, years) is NaN where no count was published."""

    inputs: AduInputs
    eligible: np.ndarray
    counts: np.ndarray


def load_history(path: Path) -> pd.DataFrame:
    """The coded counts: geoid, year, adu_permits, source_url, source_section, quote. Refuses any year in the
    V9 window, so a blind outcome can't enter this way."""
    h = pd.read_csv(path, dtype={"geoid": str})
    need = {"geoid", "year", "adu_permits", "source_url", "source_section", "quote"}
    if missing := need - set(h.columns):
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    if (h["year"] >= min(YEARS)).any():
        raise ValueError(f"{path}: a count for {min(YEARS)} or later is a V9 outcome and must not be used")
    if h["source_url"].isna().any() or (h["adu_permits"] < 0).any():
        raise ValueError(f"{path}: every count needs a source and must be >= 0")
    return h


def adu_history(state: str, store, geoids: Sequence[str], counts: pd.DataFrame) -> AduHistory:
    """History inputs for the years that have a count for some target and ACS inputs (the ACS series starts
    in 2010, so an earlier count is not used)."""
    from lotline.build import eligible as eligible_rule

    first = int(store.read(state, "acs_geo_year")["end_year"].min())
    c = counts[counts["geoid"].isin(geoids) & (counts["year"] >= first)]
    years = sorted(int(y) for y in c["year"].unique())
    if not years:
        raise ValueError("no usable pre-2018 ADU counts for the targets")
    inp = adu_inputs(state, store, geoids, years)
    elig = store.read(state, "eligible_parcels")
    elig = elig[(elig["theme"] == "adu") & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    eligible = np.zeros((len(geoids), len(years)))
    y_obs = np.full((len(geoids), len(years)), np.nan)
    for i, g in enumerate(geoids):
        e = elig[elig["jurisdiction_geoid"] == g].sort_values("year")
        for j, y in enumerate(years):
            before = e[e["year"] <= y]
            if before.empty:
                raise ValueError(f"{g}: no eligible-parcel count at or before {y}")
            eligible[i, j] = float(before["eligible_parcels"].iloc[-1])
            hit = c[(c["geoid"] == g) & (c["year"] == y)]
            if not hit.empty:
                y_obs[i, j] = float(hit["adu_permits"].iloc[0])
    return AduHistory(inp, eligible, y_obs)


def posterior_u(a: float, observed: np.ndarray, expected: np.ndarray, rng) -> np.ndarray:
    """One draw of u_i | history: Gamma(shape 1/a + Y_i, rate 1/a + M_i), summing over years with a count.
    With a = 0 (no place variation) u_i = 1 whatever the history."""
    have = ~np.isnan(observed)
    y = np.where(have, observed, 0.0).sum(axis=1)
    m = np.where(have, expected, 0.0).sum(axis=1)
    if a <= 0:
        return np.ones(len(y))
    return rng.gamma(1 / a + y, 1 / (1 / a + m))


def adu_draws(
    inp: AduInputs,
    draws: int | None = None,
    seed: int | None = None,
    params=None,
    history: AduHistory | None = None,
) -> np.ndarray:
    """Predictive ADU permits, (draws, places, years). With `history`, u_i is drawn from its posterior given
    the pre-2018 counts (D-049); otherwise from the prior. The random streams are the same either way, so the
    two variants differ only through u_i."""
    from lotline.model import hazard
    from lotline.model.scenarios import adu

    central = adu.central_params() | dict(params or {})
    n = int(draws or central["adu_simulation_draws"])
    seed = int(central["adu_simulation_seed"] if seed is None else seed)
    sets = [p | dict(params or {}) for p in adu.draw_params(n, seed)]
    n_p, n_y = len(inp.geoids), len(inp.years)
    z = adu.extrapolation_noise(n, n_p, central["adu_extrapolation_shared_share"], seed + 1)
    rng = np.random.default_rng(seed + 5)
    tau = float(central.get("adu_state_effect_sd", 0.0))
    state = np.exp(tau * rng.standard_normal(n) - tau**2 / 2)
    out = np.zeros((n, n_p, n_y))
    hist_rng = [np.random.default_rng([seed + 7, d]) for d in range(n)] if history is not None else None
    # Poisson noise has one stream per place, so a change in one place's mean never moves another's draws
    noise = [np.random.default_rng([seed + 9, i]) for i in range(n_p)]
    for d, p in enumerate(sets):
        a = p["adu_place_effect_variance"]
        u = rng.gamma(1 / a, a, size=n_p) if a > 0 else np.ones(n_p)
        q = inp.q.max(axis=(1, 2))
        if history is not None:
            q = np.maximum(q, history.inputs.q.max(axis=(1, 2)))
        blank_partial = rng.random(n_p) < q
        if history is not None:
            expected = history_expected(history, p, z[d], state[d], blank_partial)
            known = ~np.isnan(history.counts).all(axis=1)  # a place with no count keeps its prior draw
            u = np.where(known, posterior_u(a, history.counts, expected, hist_rng[d]), u)
        fac = rule_factor(
            inp,
            p["adu_partial_rule_share"],
            blank_partial,
            p["adu_ramp_half_years"],
            p["adu_ramp_slope_years"],
        )
        pool = inp.eligible.copy()
        for j in range(n_y):
            rate = np.full(n_p, inp.rate[j])
            hm = hazard.adu_mature_hazard(inp.rent[:, j], inp.value[:, j], rate, p)
            dist = hazard.calibration_distance(inp.rent[:, j], inp.value[:, j], rate, p)["total"]
            hm = np.clip(hazard.widen(hm, dist, z[d], p) * u * state[d], 0.0, 1.0)
            mu = pool * hm * fac[:, j]
            out[d, :, j] = [g.poisson(m) for g, m in zip(noise, mu, strict=True)]
            pool = np.maximum(pool - mu, 0.0)
    return out


def history_expected(h: AduHistory, p: Mapping, z, s: float, blank_partial: np.ndarray) -> np.ndarray:
    """Expected pre-2018 permits at u_i = 1 under one draw: eligible_t × widened hazard × s × rule factor,
    (places, years). No pool depletion: each year uses that year's roll."""
    from lotline.model import hazard

    inp = h.inputs
    fac = rule_factor(
        inp, p["adu_partial_rule_share"], blank_partial, p["adu_ramp_half_years"], p["adu_ramp_slope_years"]
    )
    out = np.zeros_like(h.eligible)
    for j in range(len(inp.years)):
        rate = np.full(len(inp.geoids), inp.rate[j])
        hm = hazard.adu_mature_hazard(inp.rent[:, j], inp.value[:, j], rate, p)
        dist = hazard.calibration_distance(inp.rent[:, j], inp.value[:, j], rate, p)["total"]
        out[:, j] = h.eligible[:, j] * hazard.widen(hm, dist, z, p) * s * fac[:, j]
    return out


# ---------------------------------------------------------------------------------------------------------
# Missing middle
# ---------------------------------------------------------------------------------------------------------


@dataclass
class MmInputs:
    geoids: list[str]
    names: list[str]
    years: np.ndarray
    T: np.ndarray  # (places,) adoption year
    B: np.ndarray  # (places,) baseline buildings a year
    kr: np.ndarray  # (places, years) eligible × dose × F(PCR)/F(1)


def mm_k(inp: MmInputs, half: float, slope: float) -> np.ndarray:
    """k = kr × ramp(t − T + 0.5), 0 before T."""
    from lotline.model.hazard import ramp

    age = inp.years[None, :] - inp.T[:, None] + 0.5
    return np.where(age > 0, inp.kr * ramp(age, half, slope), 0.0)


def mm_inputs(state: str, store, years: Sequence[int] = YEARS) -> MmInputs:
    """Every jurisdiction in the BPS universe where a by-right rule raises the missing-middle dose above
    2017's in a year of the window, with D-038's inputs as fixed by D-046."""
    from lotline.build import eligible as eligible_rule
    from lotline.config import load_params
    from lotline.model import estimate_mm as mm
    from lotline.model import hazard, money, rule_tags
    from lotline.model.calibrate_mm import feasibility_ratio
    from lotline.model.scenarios import adu

    years = np.array(list(years))
    pm = {k: v.value for k, v in load_params("mm").items()}
    margin = load_params("proforma")["developer_margin"].value
    sigma = load_params("mm_hazard")["mm_feasibility_dispersion"].value
    four = {st: rule_tags.apply(adu.load_reforms(st)) for st in adu.REFORM_STATES}
    every = pd.concat([r.assign(state=st) for st, r in four.items()], ignore_index=True)
    blanks = mm.blank_shares(every[every["status"] == "in_force"])  # D-038: from the four fitted states
    rows = rule_tags.apply(adu.load_reforms(state))
    rows = rows[(rows["theme"] == "missing_middle") & (rows["status"] == "in_force")]
    p = adu.central_params()
    coverage = {r["reform_id"]: adu.rule_coverage(r, None, p)[0] for r in rows.to_dict("records")}

    juris = store.read(state, "jurisdictions").set_index("geoid")
    bps = mm.bps_counts(store.read(state, "bps_place_year"))["y_buildings"]
    elig = store.read(state, "eligible_parcels")
    elig = elig[
        (elig["theme"] == "missing_middle")
        & (elig["rule_version"] == eligible_rule.RULE_VERSION)
        & (elig["year"] <= ROLL_LAST_YEAR)
    ]
    market = store.read(state, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    cost = hazard.cost_index_by_year(market)
    acs = store.read(state, "acs_geo_year")
    out = {k: [] for k in ("geoids", "names", "T", "B", "kr")}
    for g in sorted(set(rows["jurisdiction_geoid"]) & set(juris.index[juris["in_bps"].astype(bool)])):
        mine = rows[rows["jurisdiction_geoid"] == g]
        grade = pm["mm_dose_grade_permit"]
        (d0, _), *_ = mm.rules_by_year(mine, [ROLL_LAST_YEAR], coverage, blanks, grade)
        per_year = mm.rules_by_year(mine, years, coverage, blanks, grade)
        rise = [(int(y), d - d0) for y, (d, br) in zip(years, per_year, strict=True) if br >= 0.5 and d > d0]
        if not rise:
            continue  # no rule in the window raises the dose above 2017's: B already holds its building
        T = rise[0][0]
        e = elig[elig["jurisdiction_geoid"] == g].sort_values("year")
        if e.empty:
            continue
        kind = juris.loc[g, "kind"]
        geo = f"{adu.ACS_PREFIX.get(kind, 'place')}:{g}"
        y0 = int(T) - 1
        v = adu.acs_values(acs, pd.Series([geo]), max(y0, 2010), cpi)
        if v.empty or pd.isna(v.iloc[0]["rent"]):
            continue
        ci = cost.get(max(y0, min(cost)), 1.0)
        pcr = float(mm.plex_price_to_cost(v.iloc[0]["rent"], cost_index=ci))
        fr = feasibility_ratio(pcr, margin, sigma)
        base = [bps.get((g, y), np.nan) for y in BASELINE_YEARS]
        base = [b for b in base if pd.notna(b)]
        dose = np.array([max(d - d0, 0.0) for d, _ in per_year])  # only what the window newly allows
        out["geoids"].append(g)
        out["names"].append(str(juris.loc[g, "name"]))
        out["T"].append(float(T))
        out["B"].append(float(np.mean(base)) if base else 0.0)
        out["kr"].append(float(e["eligible_parcels"].iloc[-1]) * dose * fr)
    return MmInputs(
        out["geoids"],
        out["names"],
        years,
        np.array(out["T"]),
        np.array(out["B"]),
        np.array(out["kr"]).reshape(len(out["geoids"]), len(years)),
    )


def _lognormal(spec, n: int, rng) -> np.ndarray:
    """Median at the value, log-SD from the 90% interval (D-030)."""
    sd = (math.log(spec.high) - math.log(spec.low)) / 3.29 if spec.low < spec.high else 0.0
    return np.exp(math.log(spec.value) + sd * rng.standard_normal(n))


def mm_draws(inp: MmInputs, draws: int, seed: int, params: Mapping | None = None) -> np.ndarray:
    """Predictive 2-4 unit buildings, (draws, places, years)."""
    from lotline.config import load_params

    spec = load_params("mm_hazard")
    over = dict(params or {})
    rng = np.random.default_rng(seed + 7)
    theta = over.get("theta", None)
    theta = (
        np.full(draws, theta) if theta is not None else _lognormal(spec["mm_mature_hazard_ref"], draws, rng)
    )
    alpha = over.get("alpha", None)
    alpha = (
        np.full(draws, alpha)
        if alpha is not None
        else _lognormal(spec["mm_place_effect_variance"], draws, rng)
    )
    k = mm_k(inp, spec["mm_ramp_half_years"].value, spec["mm_ramp_slope_years"].value)
    n_p = len(inp.geoids)
    out = np.zeros((draws, n_p, len(inp.years)))
    for d in range(draws):
        a = alpha[d]
        u = rng.gamma(1 / a, a, size=n_p) if a > 1e-9 else np.ones(n_p)
        out[d] = rng.poisson(inp.B[:, None] + theta[d] * u[:, None] * k)
    return out


# ---------------------------------------------------------------------------------------------------------
# Summaries and the freeze file
# ---------------------------------------------------------------------------------------------------------


def summarize(draws: np.ndarray, years: np.ndarray, label: str) -> dict:
    """{year: stats, "2018-2025": stats, "2018-2022": stats} for (draws, years) totals; stats are P10/P50/P90
    and the mean of the draws (sums are taken draw by draw)."""

    def stats(a):
        p10, p50, p90 = np.percentile(a, [10, 50, 90])
        return {"p10": float(p10), "p50": float(p50), "p90": float(p90), "mean": float(a.mean())}

    out = {str(int(y)): stats(draws[:, j]) for j, y in enumerate(years)}
    out[f"{years.min()}-{years.max()}"] = stats(draws.sum(axis=1))
    sub = years <= SUBTOTAL_LAST
    out[f"{years.min()}-{SUBTOTAL_LAST}"] = stats(draws[:, sub].sum(axis=1))
    return {"target": label, "by_period": out}


def prediction(
    adu_in: AduInputs,
    adu_d: np.ndarray,
    mm_in: MmInputs,
    mm_d: np.ndarray,
    adu_hist_d: np.ndarray | None = None,
) -> dict:
    """Every V9 target's summary. ADU targets come in variant "transfer" and, with `adu_hist_d`, "own_history"
    (D-049)."""
    targets = []
    variants = [("transfer", adu_d, "")] + (
        [("own_history", adu_hist_d, ", own pre-2018 history")] if adu_hist_d is not None else []
    )
    for variant, d_, tag in variants:
        for i, g in enumerate(adu_in.geoids):
            targets.append(
                {"geoid": g, "name": adu_in.names[i], "outcome": "adu_permits", "variant": variant}
                | summarize(d_[:, i, :], adu_in.years, f"ADU permits, {adu_in.names[i]}{tag}")
            )
    for i, g in enumerate(mm_in.geoids):
        targets.append(
            {
                "geoid": g,
                "name": mm_in.names[i],
                "outcome": "bps_2_4_unit_buildings",
                "adoption_year": mm_in.T[i],
                "baseline_per_year": mm_in.B[i],
            }
            | summarize(mm_d[:, i, :], mm_in.years, f"2-4 unit buildings, {mm_in.names[i]}")
        )
    early = mm_in.T < max(mm_in.years)
    totals = [
        {"geoid": "41", "name": "Oregon, places reached before 2025", "outcome": "bps_2_4_unit_buildings"}
        | summarize(mm_d[:, early, :].sum(axis=1), mm_in.years, "2-4 unit buildings, Oregon (headline)"),
        {"geoid": "41", "name": "Oregon, all places reached by 2025", "outcome": "bps_2_4_unit_buildings"}
        | summarize(mm_d.sum(axis=1), mm_in.years, "2-4 unit buildings, Oregon incl. 2025 tier"),
    ]
    return {
        "targets": targets,
        "totals": totals,
        "n_mm_places": len(mm_in.geoids),
        "n_mm_places_before_2025": int(early.sum()),
    }


def table_hashes(
    state: str,
    store,
    tables=("jurisdictions", "eligible_parcels", "acs_geo_year", "market_geo_year", "bps_place_year"),
) -> dict:
    """sha256 of each processed input table's parquet files, so the freeze names exactly what it read."""
    out = {}
    for t in tables:
        root = Path(store.processed(state, t, "x")).parent
        h = hashlib.sha256()
        for f in sorted(root.rglob("*.parquet")):
            h.update(f.name.encode())
            h.update(f.read_bytes())
        out[t] = h.hexdigest()
    return out


def freeze_payload(pred: dict, hashes: dict, draws: int, seed: int, repo: Path) -> dict:
    """The JSON written to results/frozen/V9-OR-TRANSFER.json (D-046)."""
    from lotline.config import load_params

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    params = {
        f: {k: v.value for k, v in load_params(f).items()}
        for f in ("hazard", "adu", "mm_hazard", "proforma", "market")
    }
    return {
        "test_id": TEST_ID,
        "method": "analysis plan D-046",
        "commit": commit,
        "draws": draws,
        "seed": seed,
        "years": list(YEARS),
        "input_table_sha256": hashes,
        "params": params,
    } | pred


def write_freeze(payload: dict, repo: Path) -> Path:
    """Write the freeze file; refuses to overwrite (a freeze is made once)."""
    from lotline.validation.holdout import frozen_path

    path = frozen_path(TEST_ID, repo)
    if path.exists():
        raise FileExistsError(f"{path} exists: a frozen prediction is never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    return path
