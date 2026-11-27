"""Handbook ADU scenario: one ADU allowed on every eligible single-family parcel, at least 600 sq ft, by
right, with no parking requirement (Handbook benchmark; BUILD_PLAN §5; judging finding MS-01).

For each jurisdiction and each of the five years of the window, t = 1 … 5 (D-061: the window starts
`forecast_lead_years` after the data origin, so origin 2025 gives 2027-2031, and the reform takes effect at
the start of year 1; `baseline.window`):

    current rules   h_cur(t) = max(c × h_m × ramp(a + t), observed ADU rate)
    Handbook rules  h_hb(t)  = max(c × h_m × ramp(a + t) + (1 − c) × h_m × ramp(t), observed ADU rate)

- **h_m**, the place's mature ADU hazard (`model.hazard.adu_mature_hazard`), with each simulation draw widened
  where the place lies outside the calibration range (`hazard.widen`), times the place-type multiplier
  (D-088, D-089; `type_log_multipliers`): exp(β_core) for a core city, a draw from the town prior for a town,
  1 for a suburb (the type the anchor θ describes) or a place with no `place_type`.
- **c, how close current local rules already are to the Handbook** (`current_rules`): 1 when the coded ADU
  rule in force at the origin allows a detached ADU of 600+ sq ft by right with no owner-occupancy or parking
  requirement; `adu_partial_rule_share` when ADUs are allowed with any of those restrictions; 0 when no ADU
  rule is coded. a = years since that rule took effect. Since D-048 the ramp is 1 in every year a rule is in
  force (`hazard.adu_ramp`), so a, and a recent reform, no longer change the result. A blank (uncoded) rubric
  field is unknown, never "not restrictive": it restricts with the share of coded rules that restrict it,
  and a place with no coded rule draws its type from coded places like it (D-022).
- **Observed ADU rate**: where local permits flag ADUs, ADU permits per eligible parcel per year over the
  `adu_observed_years` years ending at the data origin (`observed_per_year`; a held-out place's years end
  before its holdout). It is a floor on the current-rules hazard: ADUs a place
  already builds are in its baseline and are never counted as added (additionality, MS-10).
- **Own counts with drift** (D-091, adopted 2026-11-15; D-093; `adu_own_rate_drift`, 0 turns it off): where a
  place has an observed ADU rate, its own counts set the no-reform hazard instead, in the lead years too:
  persistence, rate ~ Gamma(Y + 0.5, E) over the observed years, times a place drift exp(σ z − σ²/2) with σ
  `adu_drift_sigma` (`own_rate_draws`): mean 1 since 2026-11-20 (`adu_drift_mean_one`; 0 gives D-091's
  median-1 drift exp(σ z)). The Handbook hazard is that rate times the mechanism's ratio
  h_hb ÷ h_cur above, or plus the mechanism's added hazard where h_cur is 0 (`own_rate_paths`). The ratio
  has not been checked within ×2 on held-out data. Places with no observed rate keep the mechanism. D-099:
  where no ADUs are allowed today (c = 0), the added hazard in the first years is scaled by ν
  (`adu_new_rule_share`; `own_rate_paths`).

Each year the pool of parcels without an ADU shrinks, separately under each set of rules:
gross ADUs(t) = R(t − 1) × h(t), R(t) = R(t − 1) − gross ADUs(t), R(0) = eligible parcels. So a parcel gets at
most one ADU, and cumulative ADUs never exceed eligible parcels. In the lead years between the origin and the
window (D-061) only current rules apply: the pool shrinks by current-rules ADUs, the rule ages, and nothing is
added or reported.

    ADU permits added (t) = Handbook gross ADUs(t) − current-rules gross ADUs(t)
    additional homes (t)  = ADU permits added (t) × adu_net_new_share × (1 − adu_formalization_share)

Every result is a range: P10/P50/P90 and the mean over `adu_simulation_draws` draws (`draw_params`, D-030):
judgment parameters triangular(low, central, high); the fitted anchor and place-effect variance lognormal
around their estimates, shifted with the judgment parameters they were fitted at; the core-city term and the
town prior; one place multiplier per place; extrapolation noise shared across places (`extrapolation_noise`).
The mortgage-rate stress range is a sensitivity (`params=`), not part of the forecast range. Numerator (units)
and denominator (eligible parcels) stay in separate columns. Nothing is fitted here: the anchor, place-effect
variance, rule shares and core-city term come from D-088's Form A + place types fit
(`scripts/archive/adu_types_refit.py`), and observed local ADUs enter as the no-reform rate with drift
(D-093), or as the additionality floor with the switch off.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.build.eligible import PARCEL_SOURCES
from lotline.config import load_params
from lotline.model import baseline, hazard
from lotline.model import eligible_proxy as eligible_proxy_step

# Each method step has its own module (modularity step 3): legal lots (`adu_rules`, `adu_rule_priors`,
# `adu_rule_inputs`), parameter draws (`adu_params`), place types (`adu_place_types`), uptake and pool
# depletion (`adu_paths`), own-rate persistence and drift (`adu_own_rate`). This module adds them up (`run`,
# `central_path`) and reads a state's tables (`places_from_store`). Their names are re-exported here, so
# `scenarios.adu.<name>` still works.
from lotline.model.scenarios.adu_own_rate import (  # noqa: F401
    _is_adu,
    adu_share_of_one_unit,
    holdout_stops,
    observed_adu_counts,
    observed_per_year,
    observed_rate_draws,
    observed_terms_by_k_row,
    own_rate_central,
    own_rate_draws,
    own_rate_paths,
)
from lotline.model.scenarios.adu_params import (  # noqa: F401
    AGGREGATE_KEYS,
    CORE_SHIFT,
    FIXED,
    GRID_FILE,
    LOGNORMAL,
    NEW_RULE,
    NOT_IN_FIT,
    PARAM_FILES,
    SENSITIVITY,
    SHARE_DRAWS,
    Z_90,
    _adu_value,
    anchor_inputs,
    anchor_terms,
    apply_partial_share_grid,
    central_params,
    draw_params,
    log_sd,
    partial_share_grid,
    specs,
)
from lotline.model.scenarios.adu_paths import (  # noqa: F401
    Paths,
    extrapolation_noise,
    pool_paths,
    state_effect,
    state_noise,
    with_rule_probs,
)
from lotline.model.scenarios.adu_place_types import (  # noqa: F401
    CORE,
    TOWN,
    TYPE_FILE,
    central_type_log_multiplier,
    type_log_multipliers,
    type_terms,
)
from lotline.model.scenarios.adu_rule_inputs import (  # noqa: F401
    _PARCEL_CACHE,
    REFORM_STATES,
    _sf_parcels,
    county_mix,
    coverage_map,
    load_reforms,
    pooled_states,
    reforms_with,
    rule_inputs,
)
from lotline.model.scenarios.adu_rule_priors import (  # noqa: F401
    REMAINDER,
    REMAINDER_BAND,
    _cities,
    apply_priors,
    draw_rule_share,
    expected_rule_share,
    no_state_rule_priors,
    remainder_priors,
    rule_priors,
    rule_share,
    size_band,
    type_probs,
)
from lotline.model.scenarios.adu_rules import (  # noqa: F401
    FIELDS,
    LABELS,
    LIMITED_SCOPE,
    OWNER,
    P_COLS,
    RUBRIC,
    TYPES,
    _class,
    _combine_max,
    _live,
    _no_adus,
    _norm_zone,
    _resolved,
    _zone_keys,
    apply_coverage,
    c_values,
    current_rules,
    field_probabilities,
    field_restrict_counts,
    parking_waived,
    restriction_fields,
    rule_coverage,
    rule_restrictions,
    type_distribution,
    type_of,
    with_parking,
)

# ---------------------------------------------------------------------------------------------------------
# The scenario
# ---------------------------------------------------------------------------------------------------------


def central_path(
    places: pd.DataFrame,
    horizon: int | None = None,
    enabled: bool = True,
    params: dict | None = None,
    types_spec: Mapping[str, float] | None = None,
) -> dict[str, np.ndarray]:
    """The scenario at central parameter values, no widening: arrays (places × years) for each outcome.

    For hand checks and the worked example; `run` gives the ranges. `params` overrides central values;
    `types_spec` replaces adu_place_types.yaml (`type_terms`).
    """
    p = central_params() | (params or {})
    places = with_rule_probs(places, p)
    lead, window_years, _ = baseline.window(0)
    horizon = horizon or window_years
    given = places["mortgage_rate"] if "mortgage_rate" in places else pd.Series(np.nan, index=places.index)
    rate = given.fillna(p["mortgage_rate_forecast"]).to_numpy(dtype=float)
    hm = hazard.adu_mature_hazard(places["rent"], places["home_value"], rate, p)
    if "place_type" in places:  # D-088: core cities at exp(β̂_core); towns at the suburb rate (prior centre)
        hm = np.minimum(hm * np.exp(central_type_log_multiplier(places["place_type"], types_spec)), 1.0)
    c = expected_rule_share(places, p)  # E[c] over the rule types (D-022)
    paths = pool_paths(
        places["eligible_parcels"],
        hm,
        places["observed_rate"],
        c,
        places["rule_age"],
        p,
        horizon,
        enabled,
        lead,
        own_rate_central(places["observed_rate"], places["eligible_parcels"], p["adu_observed_years"])
        if p["adu_own_rate_drift"]
        else None,
    )
    homes = paths.added * p["adu_net_new_share"] * (1 - p["adu_formalization_share"])
    return {
        "mature_hazard": hm,
        "handbook": paths.handbook,
        "current": paths.current,
        "added": paths.added,
        "homes": homes,
    }


def run(
    places: pd.DataFrame,
    origin: int,
    *,
    draws: int | None = None,
    enabled: bool = True,
    summary_by: str | None = None,
    params: Mapping[str, float] | None = None,
    anchor: Mapping[str, float] | None = None,
    states_spec: Mapping[str, float] | None = None,
    eligible_proxy: bool = False,
    return_draws: bool = False,
    types_spec: Mapping[str, float] | None = None,
):
    """The scenario for every place: (per-year table, five-year totals), each with P10/P50/P90 and mean.

    `origin` is the last year of data; the years reported are the window `baseline.window(origin)` (D-061).

    With `summary_by` (a column, e.g. 'state'), also returns a third table: for each group, year and the
    five-year total, P10/P50/P90 and mean of the **sum of draws** over the group's places (places must be
    non-overlapping units, D-020), so shared draws (rates, costs, the anchor) add up correctly.
    Each draw multiplies each place's hazard by its own u ~ Gamma(mean 1, variance α_d), the place effects
    fitted in D-019 fit 3, with α_d that draw's place-effect variance (`draw_params`). The extrapolation
    noise is shared across places in a draw (`extrapolation_noise`). `params` holds parameters at given values
    in every draw (sensitivities, e.g. `mortgage_rate_forecast` at its low); `anchor` replaces
    config/params/adu_anchor.yaml (tests). With a `state` column, places in a state outside the fit that
    estimated τ also get a state multiplier exp(τ_d z_ds), shared by the state's places, with τ_d drawn per
    draw (`state_noise`, config/params/adu_state_effect.yaml, D-044); `states_spec` replaces that file
    (tests). With a `place_type` column (core, suburb or town; `places_from_store` adds it), each draw
    multiplies the hazard by the place-type multiplier (`type_log_multipliers`, its own random stream);
    `types_spec` replaces config/params/adu_place_types.yaml (tests). With `eligible_proxy` (D-056), a state
    whose every place has `denominator_source == "acs_sf_fallback"` has its eligible parcels multiplied in
    each draw by eligible_proxy_scale × exp(eligible_proxy_sd × z), one z per state per draw
    (`eligible_proxy.multipliers`, its own random stream); any state with a parcel-based place is untouched,
    and with the flag off nothing changes.
    With `return_draws`, a last element is added: per-draw arrays for the results bundle (`model/results.py`):
    `eligible`, `pencil` and `rule_share` (draws x places; pencil = the pro forma's feasible share F(PCR) the
    hazard uses; rule_share = c, how close that draw's current rules are to the Handbook),
    `added`, `current` (current-rules gross ADUs, the no-reform world) and `homes` (draws x places x years)
    and `params` (each draw's parameter set).

    `places` columns: geoid, eligible_parcels, rent (median gross rent, 2025 dollars), home_value (2025
    dollars), optional mortgage_rate (a backtest passes the year's actual rate; where it is missing, each draw
    uses `mortgage_rate_forecast` from market.yaml, flat over the horizon), rule_class ('none', 'partial',
    'handbook'), rule_age (years, NaN without a rule), observed_rate (ADU permits per parcel a year; NaN
    where not observed). Extra columns are carried through. With `observed_adu_by_k_row` (from
    `places_from_store`, D-078), each draw's observed rate uses that draw's flag undercount k
    (`observed_rate_draws`, its own random stream); `observed_rate` itself is the central-k rate.
    Totals are percentiles of each draw's five-year sum, not sums of percentiles.
    """
    central = central_params() | dict(params or {})
    places = with_rule_probs(places, central)
    n = int(draws or central["adu_simulation_draws"])
    seed = int(central["adu_simulation_seed"])
    sets = [p | dict(params or {}) for p in draw_params(n, seed, anchor)]
    share_mode = int(central.get(SHARE_DRAWS, 0))
    if share_mode:  # D-097: m_x drawn, θ, α and the core term refitted at it
        sets = apply_partial_share_grid(
            sets, partial_share_grid(), share_mode, seed, specs()["adu_partial_rule_share"].value
        )
    core_shift = np.array([p.get(CORE_SHIFT, 0.0) for p in sets])
    rule_rng = np.random.default_rng(seed + 2)
    drawn = np.zeros((n, len(places)))
    lead, horizon, first = baseline.window(origin)
    z = extrapolation_noise(n, len(places), central["adu_extrapolation_shared_share"], seed + 1)
    grid, probs, fitted = state_effect(states_spec)
    st = places["state"] if "state" in places else pd.Series(np.nan, index=places.index)
    z_state = state_noise(st, fitted, grid, probs, n, seed + 4)
    ptype = (
        places["place_type"] if "place_type" in places else pd.Series(None, index=places.index, dtype=object)
    )
    log_type = type_log_multipliers(ptype, st, n, seed + 7, types_spec)  # D-088, D-089: own stream
    log_type = log_type + core_shift[:, None] * (ptype == CORE).to_numpy()[None, :]  # D-097 (0 when off)
    var_u = np.array([p["adu_place_effect_variance"] for p in sets])[:, None]
    gamma = np.random.default_rng(seed + 3).standard_gamma(
        1 / np.maximum(var_u, 1e-12), size=(n, len(places))
    )
    u_all = np.where(var_u > 0, gamma * var_u, 1.0)
    obs_d = observed_rate_draws(places, n, seed + 6)  # D-078: each draw's flag undercount k, own stream
    e = places["eligible_parcels"].to_numpy(dtype=float)
    own = (  # D-091: own counts × drift as the no-reform rate, own stream
        own_rate_draws(
            places["observed_rate"].to_numpy(dtype=float)[None, :] if obs_d is None else obs_d,
            e,
            central["adu_observed_years"],
            central["adu_drift_sigma"],
            n,
            seed + 8,
            mean_one=bool(central.get("adu_drift_mean_one", 0)),
        )
        if central["adu_own_rate_drift"]
        else np.full((n, len(places)), np.nan)
    )
    e_mult = (
        eligible_proxy_step.multipliers(places, n, np.random.default_rng(seed + 5))
        if eligible_proxy
        else np.ones((n, len(places)))
    )
    keys = {
        "handbook": "handbook_adus",
        "current": "current_rules_adus",
        "added": "adu_permits_added",
        "homes": "additional_homes",
    }
    out = {k: np.zeros((n, len(places), horizon)) for k in keys}
    pencil = np.zeros((n, len(places)))
    share = np.zeros((n, len(places)))
    given = places["mortgage_rate"] if "mortgage_rate" in places else pd.Series(np.nan, index=places.index)

    def rates(
        p,
    ):  # a forward run uses mortgage_rate_forecast (market.yaml, central unless a sensitivity sets it)
        return given.fillna(p["mortgage_rate_forecast"]).to_numpy(dtype=float)

    for d, p in enumerate(sets):
        args = (places["rent"], places["home_value"], rates(p))
        hm = hazard.adu_mature_hazard(*args, p)
        dist_d = hazard.calibration_distance(*args, p)["total"]
        hm = hazard.widen_unseen_state(hm, dist_d, z[d], z_state[d], 1.0, "both", p)
        hm = np.clip(hm * np.exp(log_type[d]) * u_all[d], 0.0, 1.0)
        c, idx, sampled = draw_rule_share(places, p, rule_rng)
        drawn[d] = idx
        share[d] = c
        paths = pool_paths(
            e * e_mult[d],
            hm,
            places["observed_rate"] if obs_d is None else obs_d[d],
            c,
            places["rule_age"],
            p,
            horizon,
            enabled,
            lead,
            own[d],
        )
        out["handbook"][d], out["current"][d], out["added"][d] = paths.handbook, paths.current, paths.added
        out["homes"][d] = paths.added * p["adu_net_new_share"] * (1 - p["adu_formalization_share"])
        if return_draws:
            ptc = hazard.adu_price_to_cost(places["rent"], params=p)
            pencil[d] = hazard.feasible_share(ptc, p["adu_margin"], p["adu_feasibility_dispersion"])

    args = (places["rent"], places["home_value"], rates(central))
    dist = hazard.calibration_distance(*args, central)
    info = (
        places.drop(columns=["observed_adu_by_k_row"], errors="ignore")
        .assign(
            mortgage_rate_central=args[2],
            mature_hazard_central=np.minimum(
                hazard.adu_mature_hazard(*args, central)
                * np.exp(central_type_log_multiplier(ptype, types_spec)),
                1.0,
            ),
            price_to_cost_central=hazard.adu_price_to_cost(places["rent"], params=central),
            calibration_distance=dist["total"],
            outside_calibration=dist["total"] > 0,
            outside_fit_states=(st.notna() & ~st.isin(fitted)).to_numpy(),
            no_reform_basis=np.where(
                np.isfinite(own).any(axis=0) if n else False, "own ADU counts with drift", "model"
            ),
            draws_from_unknown_rule=np.where(sampled, 1.0, 0.0) if n else 0.0,
            drawn_none=(drawn == 0).mean(axis=0),
            drawn_partial=((drawn >= 1) & (drawn <= 3)).mean(axis=0),
            drawn_handbook=(drawn == 4).mean(axis=0),
        )
        .reset_index(drop=True)
    )
    yearly = info.loc[info.index.repeat(horizon)].reset_index(drop=True)
    yearly["horizon"] = np.tile(np.arange(1, horizon + 1), len(places))
    yearly["year"] = first - 1 + yearly["horizon"]
    totals = info.copy()
    for key, name in keys.items():
        for table, a in ((yearly, out[key].reshape(n, -1)), (totals, out[key].sum(axis=2))):
            table[f"{name}_mean"] = a.mean(axis=0)
            for q in (10, 50, 90):
                table[f"{name}_p{q}"] = np.percentile(a, q, axis=0)
    extra = (
        (
            {
                "eligible": e * e_mult,
                "pencil": pencil,
                "rule_share": share,
                "added": out["added"],
                "current": out["current"],
                "homes": out["homes"],
                "params": sets,
            },
        )
        if return_draws
        else ()
    )
    if summary_by is None:
        return (yearly, totals, *extra)
    rows = []
    for group, idx in pd.Series(range(len(places)), index=places[summary_by].to_numpy()).groupby(level=0):
        cols = idx.to_numpy()
        for key, name in keys.items():
            sums = out[key][:, cols, :].sum(axis=1)  # (draws, years)
            for h in range(horizon + 1):
                a = sums.sum(axis=1) if h == horizon else sums[:, h]
                label = f"{first}-{first + horizon - 1}" if h == horizon else str(first + h)
                p10, p50, p90 = np.percentile(a, [10, 50, 90])
                rows.append(
                    {
                        summary_by: group,
                        "period": label,
                        "outcome": name,
                        "p10": p10,
                        "p50": p50,
                        "p90": p90,
                        "mean": a.mean(),
                    }
                )
    return (yearly, totals, pd.DataFrame(rows), *extra)


# ---------------------------------------------------------------------------------------------------------
# Inputs from a state's processed tables
# ---------------------------------------------------------------------------------------------------------

ACS_PREFIX = {"place": "place", "township": "cousub", "county_unincorporated": "county"}
ACS_VARS = {"rent": "B25064_001", "home_value": "B25077_001"}


def acs_values(acs: pd.DataFrame, geos: pd.Series, year: int, cpi: pd.Series) -> pd.DataFrame:
    """Median gross rent and home value per ACS geo from the newest 5-year vintage ending <= year, 2025
    dollars."""
    from lotline.model import money

    a = acs[acs["variable"].isin(ACS_VARS.values()) & acs["geo"].isin(geos) & (acs["end_year"] <= year)]
    a = a[a["estimate"].notna()].sort_values("end_year").groupby(["geo", "variable"]).last().reset_index()
    to_year = money.base_year()
    a["real"] = money.deflate(a["estimate"], a["end_year"], cpi, to_year).astype(float).to_numpy()
    wide = a.pivot(index="geo", columns="variable", values="real").rename(
        columns={v: k for k, v in ACS_VARS.items()}
    )
    vintage = a.groupby("geo")["end_year"].max().rename("acs_end_year")
    return wide.join(vintage)


def non_overlapping(places: pd.DataFrame, jurisdictions: pd.DataFrame, county_shares: pd.DataFrame):
    """Make scenario units that never share a parcel (D-020).

    County remainders ("rest of county") keep the homes of local-only places and townships (`in_bps` False:
    BPS files their permits in the county row), so a scenario that models both counts those parcels twice.
    This happens only where the remainder's denominator is the ACS fallback (`eligible.allocate_homes`); a
    remainder counted from a parcel roll never overlaps, since every parcel belongs to one jurisdiction.
    Each local-only place stays its own unit (it carries its own rules); its eligible parcels are subtracted
    from the ACS-fallback remainder of every county it sits in, by `county_shares` (place_geoid,
    county_geoid, share; a place without shares sits wholly in its `county_geoid`). Negative results are set
    to 0 and flagged.

    Adds `eligible_parcels_reported` (before) and `overlap_removed`; `eligible_parcels` becomes the
    non-overlapping count. By hand: county C remainder 1,000 and D remainder 500; local-only L has 300
    parcels, two thirds in C -> C 800, D 400, L 300; total 1,500 instead of 1,800.
    """
    out = places.copy()
    out["eligible_parcels_reported"] = out["eligible_parcels"].astype(float)
    j = jurisdictions.set_index("geoid")
    in_bps = j["in_bps"].astype("boolean").fillna(True).astype(bool)
    local_only = [g for g in out["geoid"] if g in j.index and not in_bps[g]]
    # Only ACS-fallback remainders overlap: `eligible.allocate_homes` keeps local-only homes in them. A
    # remainder counted from a parcel roll holds only parcels assigned to the county row, never a place's;
    # so does one scaled to that roll in a year without one (`parcels_scaled_acs`, #208).
    source = out["denominator_source"] if "denominator_source" in out else pd.Series("acs", index=out.index)
    remainder = {
        r.county_geoid: i
        for i, r in out.iterrows()
        if r.get("kind") == "county_unincorporated" and source[i] not in PARCEL_SOURCES
    }
    removed = pd.Series(0.0, index=out.index)
    parcels = out.set_index("geoid")["eligible_parcels_reported"]
    for g in local_only:
        shares = county_shares[county_shares["place_geoid"] == g]
        if shares.empty:
            shares = pd.DataFrame({"county_geoid": [j.at[g, "county_geoid"]], "share": [1.0]})
        for c, sh in zip(shares["county_geoid"], shares["share"], strict=True):
            if c in remainder:
                removed[remainder[c]] += float(parcels[g]) * float(sh)
    net = out["eligible_parcels_reported"] - removed
    out["overlap_clipped"] = net < 0
    out["eligible_parcels"] = net.clip(lower=0.0)
    out["overlap_removed"] = out["eligible_parcels_reported"] - out["eligible_parcels"]
    return out


def _county_shares(state: str, store, places: pd.DataFrame) -> pd.DataFrame:
    """Census 2020 county shares of the local-only places (cached Census files via the IO layer)."""
    from lotline.adapters.national import geoparts
    from lotline.config import load_state

    local = places.loc[~places["in_bps"].fillna(True).astype(bool) & (places["kind"] == "place"), "geoid"]
    if local.empty:
        return pd.DataFrame(columns=["place_geoid", "county_geoid", "share"])
    return geoparts.county_shares(load_state(state).fips, sorted(local), store)


# the ADU columns of `place_inputs` (suffix `_adu`) that `places_from_store` reads
PLACE_INPUT_ADU = (
    "eligible_parcels",
    "eligible_parcels_reported",
    "overlap_removed",
    "parcels_year",
    "parcels_after_origin",
    "denominator_source",
    "denominator_quality",
)


def _place_input_rows(state: str, store, origin: int) -> pd.DataFrame:
    """`place_inputs` rows for a run with this origin (WS-SCALE, contract-change #455): the stored table's
    year == origin, else built for that year from the same processed tables (a synthetic or partial store)."""
    from lotline.build import place_inputs

    table = store.read(state, place_inputs.TABLE)
    rows = None if table is None else table[table["year"] == origin]
    if rows is None or rows.empty:
        rows = place_inputs.build(state, store, [origin])
    return rows.assign(geoid=rows["geoid"].astype(str))


def places_from_store(state: str, store, origin: int, undercount="table") -> pd.DataFrame:
    """One row per jurisdiction with ADU-eligible parcels: every input `run` needs, from processed tables.

    The shared per-place inputs come from `place_inputs` at year == origin (WS-SCALE): eligible parcels (theme
    'adu', current rule version) from the newest roll <= origin (else the earliest later roll, flagged
    `parcels_after_origin`), net of the D-020 overlap; ACS rent and value from the newest vintage <= origin;
    the observed ADU floor; the D-088 place type. Model-specific steps stay here: no
    mortgage rate (forward runs use `mortgage_rate_forecast`); coded ADU rules in force on
    `baseline.rules_as_of` (31 December of the window's first year, D-064); observed ADU permits per parcel
    where local permits flag ADUs, each source's count times its flag undercount k (D-078; `undercount`:
    "table" = the table's central k, None = no correction). The per-row split of the observed floor goes in
    `observed_adu_by_k_row` so `run` can redraw k in every draw.
    Reads only holdout-filtered tables (DataStore); no outcome after the origin is used.
    """
    rows = _place_input_rows(state, store, origin)
    adu_cols = {f"{c}_adu": c for c in PLACE_INPUT_ADU if f"{c}_adu" in rows}
    keep = ["geoid", "name", "kind", "county_geoid", "in_bps", "data_tier", *adu_cols, "acs_geo", *ACS_VARS]
    keep.append("acs_end_year")
    rows = rows[rows["eligible_parcels_adu"].fillna(0) > 0]
    places = rows[[c for c in keep if c in rows]].rename(columns=adu_cols)
    places = places.sort_values("geoid").reset_index(drop=True)
    place_type = rows.set_index("geoid")["place_type"]
    observed = rows.set_index("geoid")["observed_adu_per_year"]
    places["mortgage_rate"] = np.nan  # forward run: the rate path is a drawn parameter (market.yaml)

    as_of = baseline.rules_as_of(origin)  # D-064: rules already law by the end of the first window year
    # D-067: what places without their own rule borrow comes from the rules at the origin
    rules, info = rule_inputs(state, store, places["geoid"], as_of, pd.Timestamp(f"{origin}-12-31"))
    places = places.merge(rules, on="geoid", how="left")
    places = county_mix(places, state, store, origin, info["coded"])

    from lotline.config import load_state

    n_years = int(load_params("adu")["adu_observed_years"].value)
    from lotline.model import undercount as uc

    k_adj = uc.factors_arg(undercount)
    counts = observed_adu_counts(store.read(state, "permits"), 1900, origin, k_adj)
    stops = holdout_stops(load_state(state).holdouts)
    # place_inputs carries the observed floor at the table's central k (D-078); any other k is recomputed here
    if not (isinstance(undercount, str) and undercount == "table"):
        observed = pd.Series(observed_per_year(counts, origin, n_years, stops))
    places["observed_adu_per_year"] = places["geoid"].map(observed).to_numpy()
    places["observed_rate"] = places["observed_adu_per_year"] / places["eligible_parcels"]
    # D-088 place type from place_inputs (OMB metro areas, ACS 2011-15 units); a town where unknown (D-089)
    places["place_type"] = places["geoid"].map(place_type).fillna(TOWN).to_numpy()
    if k_adj is not None:
        terms = observed_terms_by_k_row(counts, origin, n_years, stops)
        places["observed_adu_by_k_row"] = places["geoid"].map(terms)
    return places
