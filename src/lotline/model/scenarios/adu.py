"""Handbook ADU scenario: one ADU allowed on every eligible single-family parcel, at least 600 sq ft, by
right,
with no parking requirement (Handbook benchmark; BUILD_PLAN §5; judging finding MS-01).

For each jurisdiction and each of the five years after the origin, t = 1 … 5:

    current rules   h_cur(t) = max(c × h_m × ramp(a + t), observed ADU rate)
    Handbook rules  h_hb(t)  = max(c × h_m × ramp(a + t) + (1 − c) × h_m × ramp(t), observed ADU rate)

- **h_m**, the place's mature ADU hazard (`model.hazard.adu_mature_hazard`), with each simulation draw widened
  where the place lies outside the calibration range (`hazard.widen`).
- **c, how close current local rules already are to the Handbook** (`current_rules`): 1 when the coded ADU
  rule in force at the origin allows a detached ADU of 600+ sq ft by right with no owner-occupancy or parking
  requirement; `adu_partial_rule_share` when ADUs are allowed with any of those restrictions; 0 when no ADU
  rule is coded. a = years since that rule took effect, so a recent reform is still ramping up under current
  rules. Unknown (uncoded) rubric fields count as not restrictive and are listed, so a coding gap never
  creates a Handbook gain.
- **Observed ADU rate**: where local permits flag ADUs, ADU permits per eligible parcel per year over
  `adu_observed_first_year`–`adu_observed_last_year`. It is a floor on the current-rules hazard: ADUs a place
  already builds are in its baseline and are never counted as added (additionality, MS-10).

Each year the pool of parcels without an ADU shrinks, separately under each set of rules:
gross ADUs(t) = R(t − 1) × h(t), R(t) = R(t − 1) − gross ADUs(t), R(0) = eligible parcels. So a parcel gets at
most one ADU, and cumulative ADUs never exceed eligible parcels.

    ADU permits added (t) = Handbook gross ADUs(t) − current-rules gross ADUs(t)
    additional homes (t)  = ADU permits added (t) × adu_net_new_share × (1 − adu_formalization_share)

Every result is a range: P10/P50/P90 and the mean over `adu_simulation_draws` draws of every uncertain
parameter (pro forma, hazard, net-new and formalization shares, partial-rule share). Numerator (units) and
denominator (eligible parcels) stay in separate columns. Nothing is fitted here: the hazard's anchor comes
from
the evidence band (D-018) and observed local ADUs enter only as the additionality floor.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lotline.config import CONFIG_DIR, load_params
from lotline.model import hazard, proforma

PARAM_FILES = ("proforma", "hazard", "adu", "market")
AGGREGATE_KEYS = ("adu_net_new_share", "adu_formalization_share")
FIXED = proforma.NOT_SAMPLED | {"adu_simulation_draws", "adu_simulation_seed"}
RUBRIC = (
    "by_right",
    "owner_occ",
    "adu_detached_allowed",
    "adu_max_sqft",
    "parking",
    "parking_min_per_unit",
    "adus_per_lot",
)


def specs() -> dict:
    """Every parameter the scenario uses: pro forma, hazard, adu.yaml and the two ADU shares in
    aggregate.yaml."""
    out = {}
    for name in PARAM_FILES:
        out |= load_params(name)
    agg = load_params("aggregate")
    return out | {k: agg[k] for k in AGGREGATE_KEYS}


def central_params() -> dict[str, float]:
    return {k: s.value for k, s in specs().items()}


def draw_params(n: int, seed: int) -> list[dict[str, float]]:
    """n parameter sets: each uncertain parameter triangular(low, central, high); fixed ones held."""
    rng = np.random.default_rng(seed)
    cols = {
        k: np.full(n, s.value) if k in FIXED or s.low == s.high else rng.triangular(s.low, s.value, s.high, n)
        for k, s in specs().items()
    }
    return [{k: float(v[i]) for k, v in cols.items()} for i in range(n)]


# ---------------------------------------------------------------------------------------------------------
# Current local rules (config/reforms/<st>.csv, rubric of protocol §5.4)
# ---------------------------------------------------------------------------------------------------------


def load_reforms(state: str) -> pd.DataFrame:
    """The state's coded reforms (config/reforms/<st>.csv) with dates parsed."""
    df = pd.read_csv(CONFIG_DIR / "reforms" / f"{state.lower()}.csv", dtype={"jurisdiction_geoid": str})
    for col in ("announced_date", "adoption_date", "effective_date", "end_date"):
        if col in df:
            df[col] = pd.to_datetime(df[col])
    return df


def _resolved(rows: pd.DataFrame, rid: str) -> dict:
    """A reform's rubric with fields it leaves blank taken from the reform it supersedes (amendments)."""
    by_id = rows.set_index("reform_id")
    out: dict = {}
    while isinstance(rid, str) and rid in by_id.index:
        row = by_id.loc[rid]
        for f in RUBRIC:
            if f not in out and f in row and pd.notna(row[f]):
                out[f] = row[f]
        rid = row.get("supersedes")
    return out


def rule_restrictions(rubric: Mapping, min_sqft: float = 600) -> tuple[list[str], list[str]]:
    """Which Handbook conditions a coded ADU rule fails, and which rubric fields are not coded.

    `min_sqft` is the Handbook minimum (adu.yaml `adu_handbook_min_sqft`)."""
    fails, unknown = [], []
    checks = {
        "by_right": lambda v: v is False or str(v).lower() == "false",
        "owner_occ": lambda v: v is True or str(v).lower() == "true",
        "adu_detached_allowed": lambda v: v is False or str(v).lower() == "false",
        "adu_max_sqft": lambda v: float(v) < min_sqft,
    }
    labels = {
        "by_right": "not by right",
        "owner_occ": "owner must live on site",
        "adu_detached_allowed": "no detached ADUs",
        "adu_max_sqft": f"size cap under {min_sqft:g} sq ft",
    }
    for field, fails_if in checks.items():
        if field not in rubric:
            unknown.append(field)
        elif fails_if(rubric[field]):
            fails.append(labels[field])
    minimum = rubric.get("parking_min_per_unit")
    text = str(rubric.get("parking", "")).lower()
    if minimum is not None and float(minimum) > 0:
        fails.append("parking required")
    elif minimum is None and text and not text.startswith("no") and ("requir" in text or "space" in text):
        fails.append("parking required")
    elif minimum is None and not text:
        unknown.append("parking")
    return fails, unknown


def current_rules(reforms: pd.DataFrame, geoids, state_fips: str, as_of: pd.Timestamp) -> pd.DataFrame:
    """Per jurisdiction: rule class ('none', 'partial', 'handbook'), the rule's effective date and a note.

    Uses ADU reforms in force on `as_of` (effective, not ended, not superseded by a newer one in force); a
    state law (2-digit GEOID) applies everywhere, and the more permissive of state and local rule counts.
    """
    adu = reforms[(reforms["theme"] == "adu") & (reforms["status"] == "in_force")]
    live = adu[(adu["effective_date"] <= as_of) & (adu["end_date"].isna() | (adu["end_date"] > as_of))]
    superseded = set(live["supersedes"].dropna())
    live = live[~live["reform_id"].isin(superseded)]
    scheduled = adu[adu["effective_date"] > as_of]
    min_sqft = load_params("adu")["adu_handbook_min_sqft"].value

    def assess(geoid: str) -> dict:
        rank = {"none": 0, "partial": 1, "handbook": 2}
        best = {"rule_class": "none", "rule_id": None, "effective": pd.NaT, "note": "no ADU rule coded"}
        for _, row in live[live["jurisdiction_geoid"].isin([geoid, state_fips])].iterrows():
            rubric = _resolved(adu, row["reform_id"])
            if pd.notna(rubric.get("adus_per_lot")) and float(rubric["adus_per_lot"]) == 0:
                # an explicit "no ADUs" row: the place has a rule, and it allows none
                if best["rule_id"] is None:
                    best = {
                        **best,
                        "rule_id": row["reform_id"],
                        "note": f"no ADUs allowed ({row['reform_id']})",
                    }
                continue
            fails, unknown = rule_restrictions(rubric, min_sqft)
            cls = "partial" if fails else "handbook"
            note = ("partial: " + "; ".join(fails)) if fails else "Handbook-equivalent"
            if unknown:
                note += " (not coded: " + ", ".join(unknown) + ")"
            if rank[cls] > rank[best["rule_class"]]:
                best = {
                    "rule_class": cls,
                    "rule_id": row["reform_id"],
                    "effective": row["effective_date"],
                    "note": note,
                }
        later = scheduled[scheduled["jurisdiction_geoid"].isin([geoid, state_fips])]["reform_id"].tolist()
        if later:
            best["note"] += "; scheduled after origin: " + ", ".join(later)
        return best

    out = pd.DataFrame([{"geoid": g, **assess(g)} for g in geoids])
    out = out.rename(columns={"effective": "rule_effective", "note": "rule_note"})
    age = (as_of - out["rule_effective"]).dt.days / 365.25
    return out.assign(rule_age=age.where(out["rule_class"] != "none"))


def rule_share(rule_class: pd.Series, partial_share: float) -> np.ndarray:
    """c: 0 with no rule, `adu_partial_rule_share` for a restricted rule, 1 for a Handbook-equivalent one."""
    return rule_class.map({"none": 0.0, "partial": partial_share, "handbook": 1.0}).to_numpy(dtype=float)


# ---------------------------------------------------------------------------------------------------------
# Observed ADUs (additionality)
# ---------------------------------------------------------------------------------------------------------


def _is_adu(permits: pd.DataFrame) -> pd.Series:
    return (permits["building_type_std"] == "ADU") | permits["adu_type"].notna()


def adu_share_of_one_unit(permits: pd.DataFrame, first: int, last: int) -> tuple[int, int]:
    """(ADU permits, ADU + detached single-family permits) issued in [first, last]."""
    w = permits[(permits["issue_year"] >= first) & (permits["issue_year"] <= last)]
    adu = int(_is_adu(w).sum())
    return adu, adu + int((w["building_type_std"] == "SFD").sum())


def observed_adu_counts(permits: pd.DataFrame, first: int, last: int) -> pd.DataFrame:
    """ADU permits per jurisdiction and year in [first, last], from sources that flag ADUs at all.

    Where two sources cover one jurisdiction (Met Council and Minneapolis's own permits), the larger count
    each year is kept, never the sum. Jurisdictions in a flagging source with no ADU get 0, not missing.
    """
    flagging = permits.loc[_is_adu(permits), "source"].unique()
    p = permits[permits["source"].isin(flagging) & permits["jurisdiction_geoid"].notna()]
    p = p[(p["issue_year"] >= first) & (p["issue_year"] <= last)].assign(adu=_is_adu)
    by = p.groupby(["jurisdiction_geoid", "source", "issue_year"])["adu"].sum().reset_index()
    out = by.groupby(["jurisdiction_geoid", "issue_year"])["adu"].max().reset_index()
    return out.rename(columns={"jurisdiction_geoid": "geoid", "issue_year": "year", "adu": "adu_permits"})


# ---------------------------------------------------------------------------------------------------------
# The scenario
# ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Paths:
    """Gross ADU permits per place (rows) and year (columns) under each set of rules, for one parameter
    set."""

    handbook: np.ndarray
    current: np.ndarray

    @property
    def added(self) -> np.ndarray:
        return self.handbook - self.current


def pool_paths(
    eligible, h_mature, h_floor, rule_share, rule_age, ramp_half, ramp_slope, horizon, enabled=True
):
    """Gross ADUs per year under current and Handbook rules, depleting the pool of parcels without an ADU.

    `rule_age` is the current rule's age in years at the origin (NaN: no rule). With `enabled=False` the
    Handbook path equals the current-rules path, so nothing is added.
    """
    e = np.asarray(eligible, dtype=float)
    hm = np.asarray(h_mature, dtype=float)
    floor = np.nan_to_num(np.asarray(h_floor, dtype=float), nan=0.0)
    c = np.asarray(rule_share, dtype=float)
    age = np.nan_to_num(np.asarray(rule_age, dtype=float), nan=0.0)
    r_hb, r_cur = e.copy(), e.copy()
    hb, cur = np.zeros((len(e), horizon)), np.zeros((len(e), horizon))
    for i, t in enumerate(range(1, horizon + 1)):
        h_rule = c * hm * hazard.ramp(age + t, ramp_half, ramp_slope)
        h_cur = np.minimum(np.maximum(h_rule, floor), 1.0)
        if enabled:
            h_new = h_rule + (1.0 - c) * hm * hazard.ramp(t, ramp_half, ramp_slope)
            h_hb = np.minimum(np.maximum(h_new, floor), 1.0)
        else:
            h_hb = h_cur
        hb[:, i], cur[:, i] = r_hb * h_hb, r_cur * h_cur
        r_hb, r_cur = r_hb - hb[:, i], r_cur - cur[:, i]
    return Paths(hb, cur)


def central_path(
    places: pd.DataFrame, horizon: int | None = None, enabled: bool = True
) -> dict[str, np.ndarray]:
    """The scenario at central parameter values, no widening: arrays (places × years) for each outcome.

    For hand checks and the worked example; `run` gives the ranges.
    """
    p = central_params()
    horizon = horizon or int(load_params("baseline")["forecast_horizon_years"].value)
    given = places["mortgage_rate"] if "mortgage_rate" in places else pd.Series(np.nan, index=places.index)
    rate = given.fillna(p["mortgage_rate_forecast"]).to_numpy(dtype=float)
    hm = hazard.adu_mature_hazard(places["rent"], places["home_value"], rate, p)
    c = rule_share(places["rule_class"], p["adu_partial_rule_share"])
    paths = pool_paths(
        places["eligible_parcels"],
        hm,
        places["observed_rate"],
        c,
        places["rule_age"],
        p["adu_ramp_half_years"],
        p["adu_ramp_slope_years"],
        horizon,
        enabled,
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
    places: pd.DataFrame, origin: int, *, draws: int | None = None, enabled: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The scenario for every place: (per-year table, five-year totals), each with P10/P50/P90 and mean.

    `places` columns: geoid, eligible_parcels, rent (median gross rent, 2025 dollars), home_value (2025
    dollars), optional mortgage_rate (a backtest passes the year's actual rate; where it is missing, each draw
    uses `mortgage_rate_forecast` from market.yaml, flat over the horizon), rule_class ('none', 'partial',
    'handbook'), rule_age (years, NaN without a rule), observed_rate (ADU permits per parcel a year; NaN
    where not observed). Extra columns are carried through.
    Totals are percentiles of each draw's five-year sum, not sums of percentiles.
    """
    central = central_params()
    n = int(draws or central["adu_simulation_draws"])
    seed = int(central["adu_simulation_seed"])
    sets = draw_params(n, seed)
    horizon = int(load_params("baseline")["forecast_horizon_years"].value)
    z = np.random.default_rng(seed + 1).standard_normal((n, len(places)))
    e = places["eligible_parcels"].to_numpy(dtype=float)
    keys = {
        "handbook": "handbook_adus",
        "current": "current_rules_adus",
        "added": "adu_permits_added",
        "homes": "additional_homes",
    }
    out = {k: np.zeros((n, len(places), horizon)) for k in keys}
    given = places["mortgage_rate"] if "mortgage_rate" in places else pd.Series(np.nan, index=places.index)

    def rates(
        p,
    ):  # a forward run draws the rate path (market.yaml); a backtest passes each year's actual rate
        return given.fillna(p["mortgage_rate_forecast"]).to_numpy(dtype=float)

    for d, p in enumerate(sets):
        args = (places["rent"], places["home_value"], rates(p))
        hm = hazard.adu_mature_hazard(*args, p)
        hm = hazard.widen(hm, hazard.calibration_distance(*args, p)["total"], z[d], p)
        c = rule_share(places["rule_class"], p["adu_partial_rule_share"])
        paths = pool_paths(
            e,
            hm,
            places["observed_rate"],
            c,
            places["rule_age"],
            p["adu_ramp_half_years"],
            p["adu_ramp_slope_years"],
            horizon,
            enabled,
        )
        out["handbook"][d], out["current"][d], out["added"][d] = paths.handbook, paths.current, paths.added
        out["homes"][d] = paths.added * p["adu_net_new_share"] * (1 - p["adu_formalization_share"])

    args = (places["rent"], places["home_value"], rates(central))
    dist = hazard.calibration_distance(*args, central)
    info = places.assign(
        mortgage_rate_central=args[2],
        mature_hazard_central=hazard.adu_mature_hazard(*args, central),
        price_to_cost_central=hazard.adu_price_to_cost(places["rent"], params=central),
        calibration_distance=dist["total"],
        outside_calibration=dist["total"] > 0,
    ).reset_index(drop=True)
    yearly = info.loc[info.index.repeat(horizon)].reset_index(drop=True)
    yearly["horizon"] = np.tile(np.arange(1, horizon + 1), len(places))
    yearly["year"] = origin + yearly["horizon"]
    totals = info.copy()
    for key, name in keys.items():
        for table, a in ((yearly, out[key].reshape(n, -1)), (totals, out[key].sum(axis=2))):
            table[f"{name}_mean"] = a.mean(axis=0)
            for q in (10, 50, 90):
                table[f"{name}_p{q}"] = np.percentile(a, q, axis=0)
    return yearly, totals


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


def places_from_store(state: str, store, origin: int) -> pd.DataFrame:
    """One row per jurisdiction with ADU-eligible parcels: every input `run` needs, from processed tables.

    Eligible parcels (theme 'adu', current rule version) from the newest year <= origin (else the earliest
    later roll, flagged `parcels_after_origin`); ACS rent and value from the newest vintage <= origin; no
    mortgage rate (forward runs draw `mortgage_rate_forecast`); coded ADU rules in force on 31 December of the
    origin year; observed ADU permits per parcel where local permits flag ADUs.
    Reads only holdout-filtered tables (DataStore); no outcome after the origin is used.
    """
    from lotline.build import eligible as eligible_rule
    from lotline.config import load_state
    from lotline.model import money

    elig = store.read(state, "eligible_parcels")
    elig = elig[(elig["theme"] == "adu") & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    # newest roll <= origin; where a place has only later rolls (e.g. Austin's 2026 TCAD roll), the earliest
    # of those, flagged: a parcel count is a denominator, not an outcome, so no holdout is touched
    elig = elig.assign(after=elig["year"] > origin, gap=(elig["year"] - origin).abs())
    elig = elig.sort_values(["after", "gap"]).groupby("jurisdiction_geoid").first().reset_index()
    elig = elig.rename(
        columns={"jurisdiction_geoid": "geoid", "year": "parcels_year", "after": "parcels_after_origin"}
    )
    elig = elig.drop(columns="gap")
    juris = store.read(state, "jurisdictions")[["geoid", "name", "kind", "county_geoid"]]
    places = elig.merge(juris, on="geoid", how="left")
    places = places[places["eligible_parcels"].fillna(0) > 0].reset_index(drop=True)

    market = store.read(state, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    places["acs_geo"] = places["kind"].map(ACS_PREFIX) + ":" + places["geoid"]
    acs = acs_values(store.read(state, "acs_geo_year"), places["acs_geo"], origin, cpi)
    places = places.merge(acs, left_on="acs_geo", right_index=True, how="left")
    places["mortgage_rate"] = np.nan  # forward run: the rate path is a drawn parameter (market.yaml)

    fips = load_state(state).fips
    as_of = pd.Timestamp(f"{origin}-12-31")
    rules = current_rules(load_reforms(state), places["geoid"], fips, as_of)
    places = places.merge(rules, on="geoid", how="left")

    p = load_params("adu")
    first, last = int(p["adu_observed_first_year"].value), int(p["adu_observed_last_year"].value)
    last = min(last, origin)
    counts = observed_adu_counts(store.read(state, "permits"), first, last)
    per_year = counts.groupby("geoid")["adu_permits"].sum() / (last - first + 1)
    places["observed_adu_per_year"] = places["geoid"].map(per_year)
    places["observed_rate"] = places["observed_adu_per_year"] / places["eligible_parcels"]
    return places
