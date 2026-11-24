"""Handbook ADU scenario: one ADU allowed on every eligible single-family parcel, at least 600 sq ft, by
right,
with no parking requirement (Handbook benchmark; BUILD_PLAN §5; judging finding MS-01).

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
  has not been checked within ×2 on held-out data. Places with no observed rate keep the mechanism.

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
(`scripts/dev/adu_types_refit.py`), and observed local ADUs enter as the no-reform rate with drift (D-093),
or as the additionality floor with the switch off.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.build.eligible import PARCEL_SOURCES
from lotline.config import CONFIG_DIR, load_params
from lotline.model import baseline, hazard, proforma
from lotline.model import eligible_proxy as eligible_proxy_step

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


Z_90 = 1.644854  # standard normal 95th percentile: a 90% interval spans ±Z_90 log-SDs
LOGNORMAL = ("adu_mature_hazard_ref", "adu_place_effect_variance")
SENSITIVITY = ("mortgage_rate_forecast", "adu_extrapolation_shared_share")
NOT_IN_FIT = frozenset({"adu_extrapolation_widening"})


def anchor_inputs() -> list[str]:
    """The drawn parameters the D-019 fit 3 likelihood depends on: the anchor θ and place-effect variance α
    were fitted at their central values, so each draw shifts θ and α with them (`draw_params`, D-030)."""
    skip = FIXED | set(LOGNORMAL) | set(SENSITIVITY) | set(AGGREGATE_KEYS) | NOT_IN_FIT
    return [k for k, s in specs().items() if k not in skip and s.low != s.high]


def log_sd(spec) -> float:
    """Log-SD of a lognormal whose 90% interval is (low, high): (ln high − ln low) / (2 × 1.645). The same
    convention as the fit's own predictive check (`calibrate_adu.Fit3.log_se`).

    By hand, anchor 0.000453-0.003173: (ln 0.003173 − ln 0.000453) / 3.2897 = 1.9466 / 3.2897 = 0.5917.
    """
    return (np.log(spec.high) - np.log(spec.low)) / (2 * Z_90)


def draw_params(n: int, seed: int, anchor: Mapping[str, float] | None = None) -> list[dict[str, float]]:
    """n parameter sets (D-030).

    - Judgment parameters: triangular(low, central, high); fixed ones held.
    - `SENSITIVITY` parameters (the 2015-25 mortgage-rate stress range, the shared share of extrapolation
      noise): held at central; their low and high are run as sensitivities, not mixed into the forecast range.
    - The estimated anchor θ and place-effect variance α (`LOGNORMAL`): lognormal with median at the estimate
      and log-SD from the 90% interval (`log_sd`), correlated as the fit's observed information says, then
      shifted with the judgment parameters they were fitted at:
      log θ_d = log θ̂ + sd_θ ε_θ + Σ_j g_j (p_jd − p̂_j), g_j = d log θ̂ / d p_j (config/params/adu_anchor.yaml,
      from `scripts/dev/calibrate_adu.py --draw-terms`; a parameter not listed there has slope 0); the same
      for α.
    """
    rng = np.random.default_rng(seed)
    sp = specs()
    held = FIXED | set(SENSITIVITY) | set(LOGNORMAL)
    cols = {
        k: np.full(n, s.value) if k in held or s.low == s.high else rng.triangular(s.low, s.value, s.high, n)
        for k, s in sp.items()
    }
    a = anchor_terms() if anchor is None else anchor
    corr = a["adu_anchor_info_corr"]
    e1, e2 = rng.standard_normal(n), rng.standard_normal(n)
    eps = {
        "adu_mature_hazard_ref": e1,
        "adu_place_effect_variance": corr * e1 + np.sqrt(1 - corr**2) * e2,
    }
    for key, tag in zip(LOGNORMAL, ("theta", "alpha"), strict=True):
        s = sp[key]
        shift = sum(a.get(f"anchor_slope_{tag}__{j}", 0.0) * (cols[j] - sp[j].value) for j in anchor_inputs())
        sd = log_sd(s) if s.low < s.high else 0.0
        cols[key] = np.exp(np.log(s.value) + sd * eps[key] + shift)
    return [{k: float(v[i]) for k, v in cols.items()} for i in range(n)]


NEW_RULE = "adu_new_rule_share"  # D-099
GRID_FILE = "adu_partial_share_grid.csv"
SHARE_DRAWS = (
    "adu_partial_share_draws"  # 0 fixed; 1 the grid's weights; 2 the fold maxima; 3 all at the set m_x
)
CORE_SHIFT = "adu_types_core_shift"


def partial_share_grid() -> pd.DataFrame:
    """D-097: config/params/adu_partial_share_grid.csv, A + place types refitted at each m_x on the 0.1 grid
    (m_x, θ̂, α̂, β̂_core, log-likelihood, weight, weight_fold_max)."""
    return pd.read_csv(CONFIG_DIR / "params" / GRID_FILE)


def apply_partial_share_grid(
    sets: list[dict[str, float]], grid: pd.DataFrame, mode: int, seed: int, central_mx: float
) -> list[dict[str, float]]:
    """D-097: one m_x per draw, with θ, α and the core term moved to that grid row's refit.

    The draw's own lognormal spread and judgment shifts stay: θ_d × θ̂(m) ÷ θ̂(m̂), α_d × α̂(m) ÷ α̂(m̂), and the
    core term shifted by β̂(m) − β̂(m̂) (`adu_types_core_shift`), m̂ the configured central m_x. `mode` 1 draws m
    from `weight`, 2 from `weight_fold_max`, 3 puts every draw at the set's own `adu_partial_rule_share`.
    Own stream: (seed, 97).

    By hand: grid rows m 0.4 (θ 2, α 1, β 1) and 0.7 (θ 1, α 2, β 2), central 0.7, mode 3 with a set at
    m_x 0.4 and θ 3: θ 3 × 2 / 1 = 6, α × 0.5, core shift −1."""
    g = grid.set_index("m_x")
    c = g.loc[round(central_mx, 1)]
    if mode == 3:
        ms = np.array([round(p["adu_partial_rule_share"], 1) for p in sets])
    else:
        w = g["weight" if mode == 1 else "weight_fold_max"].to_numpy(dtype=float)
        ms = np.random.default_rng([seed, 97]).choice(g.index.to_numpy(), size=len(sets), p=w / w.sum())
    out = []
    for p, m in zip(sets, ms, strict=True):
        r = g.loc[m]
        q = dict(p)
        q["adu_partial_rule_share"] = float(m)
        q["adu_mature_hazard_ref"] = p["adu_mature_hazard_ref"] * r["theta"] / c["theta"]
        q["adu_place_effect_variance"] = p["adu_place_effect_variance"] * r["alpha"] / c["alpha"]
        q[CORE_SHIFT] = float(r["core"] - c["core"])
        out.append(q)
    return out


def anchor_terms() -> dict[str, float]:
    """config/params/adu_anchor.yaml: the anchor's observed-information terms and judgment slopes (D-030),
    for the Form A + place types fit (D-088; `scripts/dev/adu_types_slopes.py`)."""
    return {k: s.value for k, s in load_params("adu_anchor").items()}


# ---------------------------------------------------------------------------------------------------------
# Place types (D-088, D-089)
# ---------------------------------------------------------------------------------------------------------

TYPE_FILE = "adu_place_types"
CORE, TOWN = "core", "town"


def type_terms(spec: Mapping[str, float] | None = None) -> dict[str, float]:
    """The core-city term's estimate and SE, and the town prior's SD, from config/params/adu_place_types.yaml
    (`spec` replaces the file: keys as there, each a value or a (value, low, high) tuple).
    se = (high − low) / (2 × 1.645). By hand: 1.199 (0.546-1.898) -> se 1.352 / 3.2897 = 0.4110."""
    if spec is None:
        p = load_params(TYPE_FILE)
        c = p["adu_types_core_log_multiplier"]
        core = (c.value, c.low, c.high)
        town = p["adu_types_town_prior_sd"].value
    else:
        core = spec["adu_types_core_log_multiplier"]
        core = tuple(core) if isinstance(core, (tuple, list)) else (core, core, core)
        town = spec["adu_types_town_prior_sd"]
    return {"core": float(core[0]), "core_se": (core[2] - core[1]) / (2 * Z_90), "town_sd": float(town)}


def central_type_log_multiplier(types, spec: Mapping[str, float] | None = None) -> np.ndarray:
    """Each place's log multiplier at central values: β̂_core for a core city, 0 otherwise (the town prior's
    centre is the suburb rate)."""
    tt = type_terms(spec)
    types = pd.Series(types, dtype=object).reset_index(drop=True)
    return np.where(types == CORE, tt["core"], 0.0)


def type_log_multipliers(types, states, n: int, seed: int, spec=None) -> np.ndarray:
    """Log hazard multiplier per draw and place (draws × places), D-088 and D-089:

    - core city: β_d ~ N(β̂_core, se), one per draw, shared by every core city;
    - town: s × z_ds, z standard normal, one per draw and state (shared by the state's towns), s the town
      prior's SD;
    - suburb, or a place with no type: 0.

    By hand with se and s at 0: a core city gets β̂ in every draw, a town 0.
    """
    tt = type_terms(spec)
    types = pd.Series(types, dtype=object).reset_index(drop=True)
    states = pd.Series(states, dtype=object).reset_index(drop=True).fillna("")
    rng = np.random.default_rng(seed)
    core = rng.normal(tt["core"], tt["core_se"], size=n)
    out = np.zeros((n, len(types)))
    is_core = (types == CORE).to_numpy()
    out[:, is_core] = core[:, None]
    is_town = (types == TOWN).to_numpy()
    if is_town.any():
        names = sorted(states[is_town].unique())
        z = rng.standard_normal((n, len(names)))
        col = states[is_town].map({st: i for i, st in enumerate(names)}).to_numpy()
        out[:, is_town] = tt["town_sd"] * z[:, col]
    return out


# ---------------------------------------------------------------------------------------------------------
# Current local rules (config/reforms/<st>.csv, rubric of protocol §5.4)
# ---------------------------------------------------------------------------------------------------------


def load_reforms(state: str, config_dir: Path | None = None) -> pd.DataFrame:
    """The state's coded reforms (config/reforms/<st>.csv) with dates parsed.

    A state outside `REFORM_STATES` with no reforms file gets an empty table (no coded rules), so a new
    state runs on borrowed priors alone (WS-SCALE task 0). A listed state must have its file.
    """
    path = (config_dir or CONFIG_DIR) / "reforms" / f"{state.lower()}.csv"
    if not path.exists() and state.upper() not in REFORM_STATES:
        from lotline.schemas import Reforms

        df = pd.DataFrame({c: pd.Series(dtype=object) for c in Reforms.to_schema().columns})
    else:
        df = pd.read_csv(path, dtype={"jurisdiction_geoid": str})
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


TYPES = ("none", "owner", "other", "both", "handbook")
P_COLS = tuple(f"p_{t}" for t in TYPES)
FIELDS = ("by_right", "owner_occ", "adu_detached_allowed", "adu_max_sqft", "parking")
OWNER = "owner_occ"
LABELS = {
    "by_right": lambda m: "not by right",
    "owner_occ": lambda m: "owner must live on site",
    "adu_detached_allowed": lambda m: "no detached ADUs",
    "adu_max_sqft": lambda m: f"size cap under {m:g} sq ft",
    "parking": lambda m: "parking required",
}


def restriction_fields(rubric: Mapping, min_sqft: float = 600) -> tuple[list[str], list[str]]:
    """(fields whose coded value fails a Handbook condition, fields left blank) for one ADU rule (D-022).

    A blank field is unknown, never "no restriction". Parking is known when `parking_min_per_unit` is coded,
    or the text says "no …" (none required) or names a requirement ("required", "space"); other text, or none,
    is unknown. `min_sqft` is the Handbook minimum (adu.yaml `adu_handbook_min_sqft`).
    """
    failed, unknown = [], []
    checks = {
        "by_right": lambda v: v is False or str(v).lower() == "false",
        "owner_occ": lambda v: v is True or str(v).lower() == "true",
        "adu_detached_allowed": lambda v: v is False or str(v).lower() == "false",
        "adu_max_sqft": lambda v: float(v) < min_sqft,
    }
    for field, fails_if in checks.items():
        if field not in rubric or pd.isna(rubric[field]):
            unknown.append(field)
        elif fails_if(rubric[field]):
            failed.append(field)
    minimum = rubric.get("parking_min_per_unit")
    text = str(rubric.get("parking", "") if pd.notna(rubric.get("parking", None)) else "").strip().lower()
    if minimum is not None and pd.notna(minimum):
        if float(minimum) > 0:
            failed.append("parking")
    elif text.startswith("no"):
        pass
    elif "requir" in text or "space" in text:
        failed.append("parking")
    else:
        unknown.append("parking")
    return failed, unknown


def rule_restrictions(rubric: Mapping, min_sqft: float = 600) -> tuple[list[str], list[str]]:
    """(labels of the Handbook conditions a rule fails, blank fields): `restriction_fields`, labelled."""
    failed, unknown = restriction_fields(rubric, min_sqft)
    return [LABELS[f](min_sqft) for f in failed], unknown


def type_of(failed) -> str:
    """Rule type from the conditions it fails: 'handbook' (none), 'owner' (owner occupancy only), 'other'
    (parking, permit by conditional use, attached only or a cap under 600 sq ft), 'both'."""
    failed = set(failed)
    owner, other = OWNER in failed, bool(failed - {OWNER})
    return "both" if owner and other else "owner" if owner else "other" if other else "handbook"


def type_distribution(failed, unknown, field_probs: Mapping[str, float]) -> np.ndarray:
    """P(rule type) over TYPES when blank fields restrict independently with `field_probs` (D-022).

    By hand: owner occupancy known to fail, parking blank with P = 0.25 -> owner 0.75, both 0.25.
    """
    v = np.zeros(len(TYPES))
    for bits in itertools.product((False, True), repeat=len(unknown)):
        pairs = list(zip(unknown, bits, strict=True))
        prob = float(np.prod([field_probs[f] if b else 1 - field_probs[f] for f, b in pairs]))
        restricted = set(failed) | {f for f, b in pairs if b}
        v[TYPES.index(type_of(restricted))] += prob
    return v


def c_values(params: Mapping[str, float]) -> np.ndarray:
    """c for each type: none 0, owner m_o, other m_x, both m_o × m_x, handbook 1 (graded partial share, D-019
    fit 3): m_o = `adu_owner_occupancy_share`, m_x = `adu_partial_rule_share`."""
    mo, mx = params["adu_owner_occupancy_share"], params["adu_partial_rule_share"]
    return np.array([0.0, mo, mx, mo * mx, 1.0])


def _combine_max(vectors: list[np.ndarray], cvals: np.ndarray) -> np.ndarray:
    """Distribution of the most permissive type (highest c) over independent rules in force together."""
    order = np.argsort(cvals, kind="stable")
    cdf = np.prod([np.cumsum(np.asarray(v)[order]) for v in vectors], axis=0)
    out = np.zeros(len(cvals))
    out[order] = np.diff(np.r_[0.0, cdf])
    return out


def _live(reforms: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(ADU rows in force on as_of and not superseded by one in force, all in-force ADU rows)."""
    adu = reforms[(reforms["theme"] == "adu") & (reforms["status"] == "in_force")]
    live = adu[(adu["effective_date"] <= as_of) & (adu["end_date"].isna() | (adu["end_date"] > as_of))]
    return live[~live["reform_id"].isin(set(live["supersedes"].dropna()))], adu


def parking_waived(reforms: pd.DataFrame, geoid: str, date: pd.Timestamp) -> bool:
    """True if a citywide 'parking' reform with a zero minimum is in force for `geoid` on `date` (D-022).

    Such a row settles a blank ADU parking field: no parking can be required for an ADU there.
    """
    r = reforms[(reforms["theme"] == "parking") & (reforms["status"] == "in_force")]
    r = r[(r["jurisdiction_geoid"] == geoid) & (r["effective_date"] <= date)]
    r = r[r["end_date"].isna() | (r["end_date"] > date)]
    zero = pd.to_numeric(r.get("parking_min_per_unit"), errors="coerce") == 0
    citywide = r["coverage"].fillna("").str.lower().str.contains("citywide") if "coverage" in r else False
    return bool((zero & citywide).any())


def with_parking(rubric: Mapping, reforms: pd.DataFrame, geoid: str, date: pd.Timestamp) -> dict:
    """The ADU rubric with a blank parking field filled from a citywide zero-minimum parking reform."""
    out = dict(rubric)
    blank = pd.isna(out.get("parking_min_per_unit", np.nan)) and pd.isna(out.get("parking", np.nan))
    if blank and parking_waived(reforms, geoid, date):
        out["parking_min_per_unit"] = 0.0
    return out


def _no_adus(rubric: Mapping) -> bool:
    v = rubric.get("adus_per_lot")
    return v is not None and pd.notna(v) and float(v) == 0


def field_restrict_counts(reforms: pd.DataFrame, as_of: pd.Timestamp, min_sqft: float = 600) -> pd.DataFrame:
    """Per field: how many coded rules in force state it (known) and how many of those restrict (D-022).

    The probability that a blank field restricts is restricting / known among coded rules (by state, with the
    pooled count as fallback: `field_probabilities`). Explicit 'no ADUs' rows are not counted.
    """
    live, adu = _live(reforms, as_of)
    rows = []
    for r in live.itertuples():
        rubric = with_parking(_resolved(adu, r.reform_id), reforms, r.jurisdiction_geoid, as_of)
        if _no_adus(rubric):
            continue
        fails, unknown = rule_restrictions(rubric, min_sqft)
        for f in FIELDS:
            if f not in unknown:
                rows.append({"state": r.state, "field": f, "restricts": LABELS[f](min_sqft) in fails})
    df = pd.DataFrame(rows, columns=["state", "field", "restricts"])
    return df.groupby(["state", "field"])["restricts"].agg(known="count", restricting="sum").reset_index()


def field_probabilities(counts: pd.DataFrame, state: str, min_count: int) -> dict[str, float]:
    """P(blank field restricts) for one state: its own coded share if it has min_count known values,
    else the pooled share over all states (D-022). A field nobody has coded gets 0.5 (no information)."""
    out = {}
    for f in FIELDS:
        own = counts[(counts["state"] == state) & (counts["field"] == f)]
        pooled = counts[counts["field"] == f]
        use = own if len(own) and own["known"].sum() >= min_count else pooled
        known = use["known"].sum()
        out[f] = float(use["restricting"].sum() / known) if known else 0.5
    return out


LIMITED_SCOPE = re.compile(
    r"\bonly (inside|within|in)\b|^within\b|\bnew subdivisions?\b|half[- ]mile|1/2 mile", re.IGNORECASE
)


def _norm_zone(z) -> str:
    return re.sub(r"[\s\-_.()]", "", str(z)).upper()


def _zone_keys(z) -> set[str]:
    """A parcel's zoning as codes to compare: normalized as written, and the acronym of a written-out name
    ('Urban Neighborhood 1' -> 'UN1')."""
    text = str(z)
    words = re.findall(r"[A-Za-z]+|\d+", text)
    acronym = "".join(w[0] if w.isalpha() else w for w in words).upper()
    return {_norm_zone(text), acronym}


def rule_coverage(
    rule: Mapping, parcels: pd.DataFrame | None, params: Mapping[str, float]
) -> tuple[float, str]:
    """Share of a place's ADU-eligible parcels a coded ADU rule covers (D-021), and how it was found.

    - zones (`coverage_zones`) and the lot minimum (`min_lot_sqft`) are measured on the place's single-family
      detached parcels (latest roll) among those whose zoning / lot size is known, where at least half of them
      have it; a zone list matching no parcel's zoning (as written or as an acronym) counts as unavailable;
    - otherwise each limit takes `adu_rule_zoned_coverage_share` (judgment);
    - with no zones or lot minimum: 1, unless the coverage text names a limited area explicitly ("only
      inside/within/in", "within …", new subdivisions, a half-mile corridor):
      `adu_rule_limited_coverage_share`.
    By hand: zones R-1 on 3 of 4 parcels; lot minimum 6,000 met by 2 of the 4 (both R-1) -> 2 / 4.
    """
    zones = [z for z in str(rule.get("coverage_zones") or "").split(";") if z.strip() and z != "nan"]
    min_lot = rule.get("min_lot_sqft")
    min_lot = float(min_lot) if min_lot is not None and pd.notna(min_lot) and float(min_lot) > 0 else None
    if not zones and min_lot is None:
        text = str(rule.get("coverage") or "")
        if LIMITED_SCOPE.search(text):
            return float(params["adu_rule_limited_coverage_share"]), "limited area (judgment)"
        return 1.0, "citywide"
    sf = parcels if parcels is not None else pd.DataFrame(columns=["zoning_raw", "lot_sqft"])
    measured = pd.Series(True, index=sf.index)  # parcels on which every measured limit is known
    covered = pd.Series(True, index=sf.index)
    share, notes = 1.0, []
    if zones:
        zoning = sf["zoning_raw"] if "zoning_raw" in sf else pd.Series(np.nan, index=sf.index)
        wanted = {_norm_zone(z) for z in zones}
        match = zoning.map(lambda z: bool(_zone_keys(z) & wanted) if pd.notna(z) else False)
        if len(sf) and zoning.notna().mean() >= 0.5 and match.any():
            measured &= zoning.notna()
            covered &= match
            notes.append("zones from parcels")
        else:
            share *= float(params["adu_rule_zoned_coverage_share"])
            notes.append("zones (judgment)")
    if min_lot is not None:
        lot = sf["lot_sqft"] if "lot_sqft" in sf else pd.Series(np.nan, index=sf.index)
        if len(sf) and lot.notna().mean() >= 0.5:
            measured &= lot.notna()
            covered &= lot.fillna(0) >= min_lot
            notes.append("lot minimum from parcels")
        else:
            share *= float(params["adu_rule_zoned_coverage_share"])
            notes.append("lot minimum (judgment)")
    if any("from parcels" in n for n in notes) and measured.any():
        share *= float(covered[measured].mean())
    return float(share), "; ".join(notes)


def apply_coverage(vector: np.ndarray, coverage: float) -> np.ndarray:
    """Parcels a rule does not cover have no ADU rule: the uncovered share of each type moves to 'none'."""
    out = coverage * np.asarray(vector, dtype=float)
    out[0] += 1 - coverage
    return out


def _class(p: np.ndarray) -> str:
    if p[0] == 1:
        return "none"
    if p[-1] == 1:
        return "handbook"
    if p[1:4].sum() == 1 and np.count_nonzero(p) == 1:
        return "partial"
    return "uncertain"


def current_rules(
    reforms: pd.DataFrame,
    geoids,
    state_fips: str,
    as_of: pd.Timestamp,
    field_probs: Mapping | None = None,
    coverage: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Per jurisdiction: P(current ADU rule type) over TYPES, the rule, its date and a note (D-021, D-022).

    - **No ADU row** (local or statewide): `rule_class` 'unknown', p_* missing (filled by `apply_priors`).
    - **A coded row:** known failed conditions fix part of the type; each blank field restricts with
      `field_probs[field]` (default 0.5), independently (`type_distribution`).
    - **Explicit 'no ADUs' row** (`adus_per_lot` = 0, #164): 'none'.
    - **Coverage** (D-021): `coverage[reform_id]` (else judged from the rule's text) moves the uncovered share
      of eligible lots to 'none'.
    Several rows in force (local and state law): the most permissive type (highest c at central values)
    counts. `rule_class` describes the rules' own conditions, before coverage: 'none', 'partial', 'handbook',
    'uncertain' (blank fields) or 'unknown'; the p_* include coverage; `p_partial` = owner + other + both.
    """
    live, adu = _live(reforms, as_of)
    scheduled = adu[adu["effective_date"] > as_of]
    central = {k: v.value for k, v in load_params("adu").items()}
    min_sqft = central["adu_handbook_min_sqft"]
    cvals = c_values(central)
    fp = {f: 0.5 for f in FIELDS} | dict(field_probs or {})

    def assess(geoid: str) -> dict:
        rows = live[live["jurisdiction_geoid"].isin([geoid, state_fips])]
        if rows.empty:
            out = {
                "rule_class": "unknown",
                "rule_id": None,
                "effective": pd.NaT,
                "note": "no ADU rule coded",
                "unknown_fields": "",
                "coverage": np.nan,
            }
            out |= {c: np.nan for c in P_COLS}
        else:
            vectors, raw, best = [], [], None
            for _, row in rows.iterrows():
                rubric = with_parking(_resolved(adu, row["reform_id"]), reforms, geoid, as_of)
                cov = 1.0
                if _no_adus(rubric):
                    v, note, unknown = np.eye(len(TYPES))[0], f"no ADUs allowed ({row['reform_id']})", []
                    v_raw = v
                else:
                    failed, unknown = restriction_fields(rubric, min_sqft)
                    v = type_distribution(failed, unknown, fp)
                    v_raw = v.copy()
                    labels = [LABELS[f](min_sqft) for f in failed]
                    note = ("partial: " + "; ".join(labels)) if failed else "Handbook-equivalent"
                    if unknown:
                        note += " (not coded: " + ", ".join(unknown) + ")"
                    cov = (coverage or {}).get(row["reform_id"])
                    if cov is None:
                        cov = rule_coverage(row, None, central)[0]
                    if cov < 1:
                        v = apply_coverage(v, cov)
                        note += f"; covers {cov:.0%} of eligible lots"
                raw.append(v_raw)
                vectors.append(v)
                rank = float(v @ cvals)
                if best is None or rank > best[0]:
                    best = (rank, row, unknown, note, cov)
            p = _combine_max(vectors, cvals)
            _, row, unknown, note, cov = best
            cls = _class(_combine_max(raw, cvals))  # the rules' own conditions; coverage is reported apart
            out = {
                "rule_class": cls,
                "rule_id": row["reform_id"],
                "effective": pd.NaT if cls == "none" else row["effective_date"],
                "note": note,
                "unknown_fields": ";".join(unknown),
                "coverage": cov,
            }
            out |= dict(zip(P_COLS, p, strict=True))
        later = scheduled[scheduled["jurisdiction_geoid"].isin([geoid, state_fips])]["reform_id"].tolist()
        if later:
            out["note"] += "; scheduled after the rules date: " + ", ".join(later)
        return out

    cols = ["geoid", "rule_class", "rule_id", "effective", "note", "unknown_fields", "coverage", *P_COLS]
    out = pd.DataFrame([{"geoid": g, **assess(g)} for g in geoids], columns=cols)
    out["effective"] = pd.to_datetime(out["effective"])
    out = out.rename(columns={"effective": "rule_effective", "note": "rule_note"})
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1, min_count=1)
    age = (as_of - out["rule_effective"]).dt.days / 365.25
    return out.assign(rule_age=age.where(out["rule_class"] != "none"))


def size_band(population, edges) -> np.ndarray:
    """Place-size band 0, 1, 2 … from 2020 population and band edges (e.g. 10,000 and 50,000)."""
    return np.searchsorted(np.asarray(edges, dtype=float), np.asarray(population, dtype=float), side="right")


REMAINDER = "county_unincorporated"  # a county remainder: unincorporated land the county itself zones
REMAINDER_BAND = -1  # the priors row county remainders read under D-102 option (b)


def remainder_priors(coded: pd.DataFrame, min_count: int) -> pd.DataFrame:
    """D-102 option (b) (Ben, 2026-11-24): for each state with at least `min_count` coded county remainders
    (`kind` == county_unincorporated), one priors row (band `REMAINDER_BAND`) with their mean probabilities.
    An uncoded remainder in that state reads it instead of its size band (`apply_priors`), since
    unincorporated land is zoned by the county, not by cities its size. Other states keep the band rule.
    By hand: 5 coded remainders, 1 Handbook-equivalent and 4 'none' -> p_handbook 0.2, p_none 0.8."""
    if "kind" not in coded:
        return pd.DataFrame(columns=["state", "band", "n_coded", "source", *P_COLS, "p_partial"])
    rem = coded[coded["kind"] == REMAINDER]
    rows = [
        {"state": st, "band": REMAINDER_BAND, "n_coded": len(g), "source": "state, coded county remainders",
         **g[list(P_COLS)].mean().to_dict()}
        for st, g in rem.groupby("state") if len(g) >= min_count
    ]  # fmt: skip
    out = pd.DataFrame(rows, columns=["state", "band", "n_coded", "source", *P_COLS])
    return out.assign(p_partial=out[["p_owner", "p_other", "p_both"]].sum(axis=1))


def rule_priors(coded: pd.DataFrame, edges, min_count: int) -> pd.DataFrame:
    """Type probabilities for places with no ADU row, from the coded places themselves (D-022).

    `coded`: state, population and p_* (over TYPES) for every place with a coded rule (fractional where blanks
    or coverage leave the type uncertain). For each state and size band: the mean of the coded places'
    probabilities if at least `min_count` places are coded there; else the state's pooled mean; else the mean
    over every state. Returns state, band, n_coded, source and p_* (and p_partial). With a `kind` column, also
    the `remainder_priors` rows (D-102 option (b)).
    By hand: 5 coded places in a band, 2 'other' and 3 Handbook-equivalent -> p_other 0.4, p_handbook 0.6.
    """
    c = coded.assign(band=size_band(coded["population"], edges))
    rows = []
    for state in sorted(c["state"].unique()):
        for band in range(len(edges) + 1):
            own = c[(c["state"] == state) & (c["band"] == band)]
            whole = c[c["state"] == state]
            if len(own) >= min_count:
                use, src = own, "state and band"
            elif len(whole) >= min_count:
                use, src = whole, "state, all bands"
            else:
                use, src = c, "all states"
            rows.append(
                {
                    "state": state,
                    "band": band,
                    "n_coded": len(own),
                    "source": src,
                    **use[list(P_COLS)].mean().to_dict(),
                }
            )
    out = pd.DataFrame(rows)
    out = out.assign(p_partial=out[["p_owner", "p_other", "p_both"]].sum(axis=1))
    rem = remainder_priors(coded, min_count)
    return pd.concat([out, rem], ignore_index=True) if len(rem) else out


def no_state_rule_priors(coded: pd.DataFrame, edges, min_count: int, law_states, state: str) -> pd.DataFrame:
    """D-068: priors for the places a state ADU law leaves out, from the coded places of the states without
    such a law (`law_states` are those whose law is coded row by row, `adu_state_law_rows_complete`).

    For each size band: the mean P(type) of those states' coded places in the band if at least `min_count`
    are coded there; else their pooled mean. Rows are labelled `state` so `apply_priors` reads them for it.
    By hand: no-law places in band 0, 3 Handbook-equivalent and 2 'none', min_count 5 -> p_handbook 0.6,
    p_none 0.4; flagged states' places never count.
    """
    pool = coded[~coded["state"].isin(set(law_states))]
    pool = pool.assign(band=size_band(pool["population"], edges))
    rows = []
    for band in range(len(edges) + 1):
        own = pool[pool["band"] == band]
        use, src = (own, "band") if len(own) >= min_count else (pool, "all bands")
        rows.append(
            {
                "state": state,
                "band": band,
                "n_coded": len(own),
                "source": f"states without a coded state ADU law, {src}",
                **use[list(P_COLS)].mean().to_dict(),
            }
        )
    out = pd.DataFrame(rows)
    return out.assign(p_partial=out[["p_owner", "p_other", "p_both"]].sum(axis=1))


def apply_priors(places: pd.DataFrame, priors: pd.DataFrame, edges) -> pd.DataFrame:
    """Fill p_* for 'unknown' places from `rule_priors` by state and size band; adds `prior_source`. A county
    remainder (`kind`) reads its state's `REMAINDER_BAND` row where there is one (D-102 option (b))."""
    out = places.assign(band=size_band(places["population"].fillna(0), edges))
    if "kind" in out:
        has_rem = set(priors.loc[priors["band"] == REMAINDER_BAND, "state"])
        rem = (out["kind"] == REMAINDER) & out["state"].isin(has_rem)
        out.loc[rem, "band"] = REMAINDER_BAND
    pr = priors.set_index(["state", "band"])
    pooled = priors.loc[priors["band"] != REMAINDER_BAND, list(P_COLS)].mean()
    src = pd.Series("coded", index=out.index, dtype=object)
    for i in out.index[out["rule_class"] == "unknown"]:
        key = (out.at[i, "state"], out.at[i, "band"])
        row = pr.loc[key] if key in pr.index else None
        for col in P_COLS:
            out.at[i, col] = row[col] if row is not None else pooled[col]
        src[i] = row["source"] if row is not None else "all states"
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1)
    return out.assign(prior_source=src)


def type_probs(places: pd.DataFrame) -> np.ndarray:
    """(places × TYPES) probabilities. Tables from before D-022 with only p_none/p_partial/p_handbook (or only
    `rule_class`) read 'partial' as 'other'."""
    if all(c in places for c in P_COLS) and places[list(P_COLS)].notna().all(axis=None):
        return places[list(P_COLS)].to_numpy(dtype=float)
    cls = places["rule_class"]
    get = lambda col, fallback: places[col] if col in places else fallback  # noqa: E731
    none = get("p_none", (cls == "none").astype(float)).fillna((cls == "none").astype(float))
    part = get("p_partial", (cls == "partial").astype(float)).fillna((cls == "partial").astype(float))
    hb = get("p_handbook", (cls == "handbook").astype(float)).fillna((cls == "handbook").astype(float))
    zero = np.zeros(len(places))
    return np.column_stack([none, zero, part, zero, hb]).astype(float)


def expected_rule_share(places: pd.DataFrame, params: Mapping[str, float]) -> np.ndarray:
    """E[c] = Σ P(type) × c(type): the central-path value of c (D-022)."""
    return type_probs(places) @ c_values(params)


def draw_rule_share(places: pd.DataFrame, params: Mapping[str, float], rng: np.random.Generator):
    """One draw of each place's rule type -> (c, drawn type index, sampled mask)."""
    p = type_probs(places)
    u = rng.random(len(p))[:, None]
    idx = (u > np.cumsum(p, axis=1)).sum(axis=1).clip(max=len(TYPES) - 1)
    return c_values(params)[idx], idx, p.max(axis=1) < 1


def rule_share(rule_class: pd.Series, partial_share: float) -> np.ndarray:
    """c for a known class (before D-022): 0 none, `partial_share` partial, 1 Handbook-equivalent."""
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


def observed_adu_counts(permits: pd.DataFrame | None, first: int, last: int, undercount=None) -> pd.DataFrame:
    """ADU permits per jurisdiction and year in [first, last], from sources that flag ADUs at all.

    Where two sources cover one jurisdiction (Met Council and Minneapolis's own permits), the larger count
    each year is kept, never the sum. Jurisdictions in a flagging source with no ADU get 0, not missing.

    With `undercount` (`model.undercount.Factors`, D-078), each source's count is first multiplied by its k
    and the larger scaled count is kept; the output then also has the kept `source`, its raw count
    (`counted`) and its table row (`k_row`, -1 for k = 1).
    """
    from lotline.model import undercount as uc

    if (
        permits is None or permits.empty
    ):  # no permit adapter for the state (WS-SCALE task 0): no observed ADUs
        cols = ["geoid", "year", "adu_permits"]
        cols += [] if undercount is None else ["source", "counted", "k_row"]
        return pd.DataFrame({c: pd.Series(dtype=object) for c in cols})
    flagging = permits.loc[_is_adu(permits), "source"].unique()
    p = permits[permits["source"].isin(flagging) & permits["jurisdiction_geoid"].notna()]
    p = p[(p["issue_year"] >= first) & (p["issue_year"] <= last)].assign(adu=_is_adu)
    by = p.groupby(["jurisdiction_geoid", "source", "issue_year"])["adu"].sum().reset_index()
    if undercount is None:
        out = by.groupby(["jurisdiction_geoid", "issue_year"])["adu"].max().reset_index()
    else:
        by = uc.scale(by.assign(adu=by["adu"].astype(float)), undercount)
        by = by.sort_values(["adu", "source"], ascending=[False, True], kind="stable")
        out = by.groupby(["jurisdiction_geoid", "issue_year"]).head(1)
        out = out[["jurisdiction_geoid", "issue_year", "adu", "source", "counted", "k_row"]]
        out = out.sort_values(["jurisdiction_geoid", "issue_year"]).reset_index(drop=True)
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


def own_rate_paths(h_own, h_cur_mech, h_hb_mech):
    """D-091 (adopted 2026-11-15): the no-reform and Handbook hazards where a place's own counts set the
    no-reform rate. `h_own` is that rate (persistence × drift; NaN: no own counts, keep the mechanism).

    - no reform: h_own;
    - Handbook: h_own × (h_hb_mech ÷ h_cur_mech), the mechanism's ratio, where h_cur_mech > 0; where it is 0
      (no rule allows ADUs and nothing was observed) the ratio is undefined and the mechanism's added hazard
      h_hb_mech − h_cur_mech is added instead.

    Both capped at 1. By hand: h_own 0.01, mechanism 0.02 → 0.05 gives 0.01 → 0.025; h_own 0.001, mechanism
    0 → 0.03 gives 0.001 → 0.031; h_own NaN gives the mechanism's 0.02 → 0.05.
    """
    own = np.asarray(h_own, dtype=float)
    cur_m, hb_m = np.asarray(h_cur_mech, dtype=float), np.asarray(h_hb_mech, dtype=float)
    use = np.isfinite(own)
    o = np.where(use, own, 0.0)
    pos = cur_m > 0
    ratio_hb = o * np.divide(hb_m, cur_m, out=np.ones_like(cur_m), where=pos)
    hb_own = np.where(pos, ratio_hb, o + (hb_m - cur_m))
    cur = np.where(use, np.minimum(o, 1.0), cur_m)
    hb = np.where(use, np.minimum(hb_own, 1.0), hb_m)
    return cur, hb


def pool_paths(
    eligible, h_mature, h_floor, rule_share, rule_age, ramp_params, horizon, enabled=True, lead=0, h_own=None
):
    """Gross ADUs per year under current and Handbook rules, depleting the pool of parcels without an ADU.

    `rule_age` is the current rule's age in years at the origin (NaN: no rule). `ramp_params` gives the ramp
    (`hazard.adu_ramp`; D-048: 1 every year). With `enabled=False` the Handbook path equals the current-rules
    path, so nothing is added. `lead` years (D-061) run first under current rules only, on one shared pool,
    and are not returned: the window's year t has rule age a + lead + t and Handbook ramp(t).
    `h_own` (D-091; None or NaN per place: off) replaces the no-reform hazard, in the lead years too, and
    scales the Handbook hazard by the mechanism's ratio (`own_rate_paths`). D-099: where today's rule share c
    is 0 (no ADUs allowed), the Handbook's new hazard is multiplied by `adu_new_rule_share` (ν; 1 = none).
    """
    e = np.asarray(eligible, dtype=float)
    hm = np.asarray(h_mature, dtype=float)
    floor = np.nan_to_num(np.asarray(h_floor, dtype=float), nan=0.0)
    c = np.asarray(rule_share, dtype=float)
    age = np.nan_to_num(np.asarray(rule_age, dtype=float), nan=0.0)
    own = np.full(len(e), np.nan) if h_own is None else np.asarray(h_own, dtype=float)
    nu = float(ramp_params.get(NEW_RULE, 1.0))  # D-099: first-years share where no ADUs are allowed today
    r = e.copy()
    for s in range(1, int(lead) + 1):  # lead years: current rules only, nothing reported (D-061)
        h_lead = np.minimum(np.maximum(c * hm * hazard.adu_ramp(age + s, ramp_params), floor), 1.0)
        h_lead, _ = own_rate_paths(own, h_lead, h_lead)
        r = r - r * h_lead
    age = age + int(lead)
    r_hb, r_cur = r.copy(), r.copy()
    hb, cur = np.zeros((len(e), horizon)), np.zeros((len(e), horizon))
    for i, t in enumerate(range(1, horizon + 1)):
        h_rule = c * hm * hazard.adu_ramp(age + t, ramp_params)
        h_cur = np.minimum(np.maximum(h_rule, floor), 1.0)
        if enabled:
            h_new = h_rule + (1.0 - c) * hm * hazard.adu_ramp(t, ramp_params) * np.where(c <= 0, nu, 1.0)
            h_hb = np.minimum(np.maximum(h_new, floor), 1.0)
        else:
            h_hb = h_cur
        h_cur, h_hb = own_rate_paths(own, h_cur, h_hb)
        hb[:, i], cur[:, i] = r_hb * h_hb, r_cur * h_cur
        r_hb, r_cur = r_hb - hb[:, i], r_cur - cur[:, i]
    return Paths(hb, cur)


def own_rate_draws(observed_rate, eligible, n_years, sigma, n, seed, mean_one: bool = False) -> np.ndarray:
    """D-091 (adopted 2026-11-15): each place's no-reform ADU rate per eligible parcel a year from its own
    counts, persistence × drift (draws × places; NaN where the place has no observed rate).

    - Persistence (D-090 F0): rate ~ Gamma(Y + 0.5, E), Y = observed_rate × eligible × n_years (the counts
      the observed rate came from, undercount-scaled as drawn), E = eligible × n_years lot-years.
    - Drift: × d = exp(σ z), z standard normal, one per place and draw for the whole window (median 1).
      With `mean_one` (`adu_drift_mean_one`, Ben 2026-11-20): × d = exp(σ z − σ² / 2), mean 1, so a place's
      expected rate stays at its persistence mean; its median falls to exp(−σ² / 2) (0.59 at σ 1.025).

    `observed_rate` is one row (places) or one row per draw (`observed_rate_draws`). Own stream: `seed`.
    By hand: rate 0.01, 100 lots, 3 years -> Y 3, E 300, posterior mean 3.5 / 300 = 0.01167 before drift;
    σ 1.025 with `mean_one`: every drift factor is the median-one factor × exp(−0.5253) = × 0.5914.
    """
    obs = np.atleast_2d(np.asarray(observed_rate, dtype=float))
    obs = np.broadcast_to(obs, (n, obs.shape[1]))
    e = np.asarray(eligible, dtype=float)
    lot_years = np.where(e > 0, e * n_years, np.nan)
    y = np.nan_to_num(obs * lot_years, nan=0.0)
    rng = np.random.default_rng(seed)
    rate = rng.standard_gamma(y + 0.5) / lot_years
    drift = np.exp(sigma * rng.standard_normal(obs.shape) - (sigma**2 / 2 if mean_one else 0.0))
    return np.where(np.isfinite(obs) & np.isfinite(lot_years), rate * drift, np.nan)


def own_rate_central(observed_rate, eligible, n_years) -> np.ndarray:
    """The persistence posterior mean (Y + 0.5) / E at drift 1 (the median, or with `adu_drift_mean_one` the
    mean, of the drift factor); NaN without an observed rate."""
    e = np.asarray(eligible, dtype=float)
    lot_years = np.where(e > 0, e * n_years, np.nan)
    obs = np.asarray(observed_rate, dtype=float)
    return (obs * lot_years + 0.5) / lot_years


def with_rule_probs(places: pd.DataFrame, params: Mapping[str, float]) -> pd.DataFrame:
    """Type probabilities for every place (`type_probs`), and a rule age of `adu_unknown_rule_age_years` where
    the type is drawn and no rule date is known (D-022)."""
    out = places.copy()
    probs = type_probs(out)
    for k, col in enumerate(P_COLS):
        out[col] = probs[:, k]
    out["p_partial"] = probs[:, 1:4].sum(axis=1)
    sampled = probs.max(axis=1) < 1
    age = out["rule_age"] if "rule_age" in out else pd.Series(np.nan, index=out.index)
    out["rule_age"] = age.where(~(sampled & age.isna()), params["adu_unknown_rule_age_years"])
    return out


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


def extrapolation_noise(n: int, n_places: int, shared: float, seed: int) -> np.ndarray:
    """Standard-normal extrapolation noise (draws × places): √shared · z_d + √(1 − shared) · e_di (D-030).

    z_d is one number per draw, common to every place; e_di is each place's own. Every entry stays standard
    normal, so `hazard.widen` keeps each place's mean and spread; only the correlation between places,
    `shared`, changes. shared = 1: one z per draw; 0: independent per place (before D-030).
    """
    rng = np.random.default_rng(seed)
    common = rng.standard_normal((n, 1))
    own = rng.standard_normal((n, n_places))
    return np.sqrt(shared) * common + np.sqrt(1.0 - shared) * own


def state_effect(spec: Mapping[str, float] | None = None) -> tuple[np.ndarray, np.ndarray, frozenset[str]]:
    """config/params/adu_state_effect.yaml (D-044): τ's grid, its probabilities, and the fitted states.

    `spec` replaces the file (tests): keys adu_state_tau_prob__<τ, _ for .> and
    adu_state_effect_fitted__<ST>.
    Probabilities are renormalised (the file rounds them to 6 significant figures).
    """
    spec = spec if spec is not None else {k: s.value for k, s in load_params("adu_state_effect").items()}
    pairs = sorted(
        (float(k.removeprefix("adu_state_tau_prob__").replace("_", ".")), v)
        for k, v in spec.items()
        if k.startswith("adu_state_tau_prob__")
    )
    grid = np.array([t for t, _ in pairs])
    probs = np.array([q for _, q in pairs], dtype=float)
    fitted = frozenset(k.removeprefix("adu_state_effect_fitted__") for k, v in spec.items()
                       if k.startswith("adu_state_effect_fitted__") and v == 1)  # fmt: skip
    return grid, probs / probs.sum(), fitted


def state_noise(states, fitted, grid, probs, n: int, seed: int) -> np.ndarray:
    """τ_d · z_ds per draw and place (draws × places), the log state multiplier (D-043, D-044).

    τ_d is drawn from the grid once per draw; z_ds is one standard normal per draw and state, shared by the
    state's places. Places in a fitted state (or with no state) get 0: their spread is in the place effects.
    """
    states = pd.Series(states, dtype=object).reset_index(drop=True)
    out = np.zeros((n, len(states)))
    unseen = states.notna() & ~states.isin(fitted)
    if not unseen.any():
        return out
    rng = np.random.default_rng(seed)
    tau = rng.choice(grid, size=n, p=probs)
    names = sorted(states[unseen].unique())
    z = rng.standard_normal((n, len(names)))
    col = states[unseen].map({st: i for i, st in enumerate(names)}).to_numpy()
    out[:, unseen.to_numpy()] = tau[:, None] * z[:, col]
    return out


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


# States whose coded rules feed field probabilities, rule priors and blank shares. Oregon joined on
# 2026-11-05 (D-053), after V9 was scored; V9 itself keeps the four states it was frozen from.
# A state not listed here borrows from these states but feeds nothing back ("borrow only", Ben 2026-11-17,
# WS-SCALE task 0): `reforms_with` adds it to the run on the fly, after the shared pools are built.
REFORM_STATES = ("MN", "NC", "OH", "TX", "OR")


def reforms_with(state: str, load=None) -> dict[str, pd.DataFrame]:
    """`{state: reforms}` for every state in `REFORM_STATES`, then `state` itself if it is not listed.

    Callers pool only the `REFORM_STATES` entries (`pooled_states`); the extra state's own rules still
    apply to its own places. `load` defaults to `load_reforms`.
    """
    load = load or load_reforms
    out = {st: load(st) for st in REFORM_STATES}
    st = state.upper()
    if st not in out:
        out[st] = load(st)
    return out


def pooled_states(reforms: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """The entries of `reforms` that feed shared pools (field probabilities, priors, blank shares)."""
    return {st: r for st, r in reforms.items() if st in REFORM_STATES}


_PARCEL_CACHE: dict[str, pd.DataFrame] = {}


def _sf_parcels(state: str, store) -> pd.DataFrame | None:
    """Single-family detached parcels of each jurisdiction's latest roll (zoning and lot size), cached. None
    for a state with no parcel table (Oregon on the ACS fallback): its zone-limited rules then take the
    judgment share, as `rule_coverage` does for any place without parcels (D-021)."""
    if state not in _PARCEL_CACHE:
        cols = ["jurisdiction_geoid", "vintage", "land_use_std", "lot_sqft", "zoning_raw"]
        p = store.read(state, "parcels")
        if p is None:
            return None
        p = p[[c for c in cols if c in p]]
        p = p[p["land_use_std"] == "SF_DETACHED"]
        latest = p.groupby("jurisdiction_geoid")["vintage"].transform("max")
        _PARCEL_CACHE[state] = p[p["vintage"] == latest]
    return _PARCEL_CACHE[state]


def coverage_map(state: str, store, reforms: pd.DataFrame, params: Mapping[str, float]) -> pd.DataFrame:
    """D-021: coverage share of every coded ADU rule in a state, measured on parcels where possible.

    Returns reform_id, geoid, coverage, how. Rules with no zone list or lot minimum need no parcels.
    """
    adu = reforms[reforms["theme"] == "adu"]
    needs = adu["coverage_zones"].notna() | (pd.to_numeric(adu["min_lot_sqft"], errors="coerce") > 0)
    parcels = _sf_parcels(state, store) if needs.any() else None
    rows = []
    for r in adu.itertuples():
        mine = parcels[parcels["jurisdiction_geoid"] == r.jurisdiction_geoid] if parcels is not None else None
        cov, how = rule_coverage(r._asdict(), mine, params)
        rows.append({"reform_id": r.reform_id, "geoid": r.jurisdiction_geoid, "coverage": cov, "how": how})
    return pd.DataFrame(rows, columns=["reform_id", "geoid", "coverage", "how"])


def rule_inputs(
    state: str, store, geoids, as_of: pd.Timestamp, prior_as_of: pd.Timestamp | None = None
) -> tuple[pd.DataFrame, dict]:
    """Rule-type probabilities for `geoids` in `state` (D-021, D-022), and the counts behind them.

    Field probabilities come from every state's coded rules in force (`field_restrict_counts`); coverage from
    each rule's zones and lot minimum on the place's parcels (`coverage_map`); priors for places with no ADU
    row from the coded places of every state, by state and size band (`rule_priors`). Reads
    config/reforms/*.csv at run time, so newly coded rules shrink the unknowns with no code change.

    Dates (D-067): each place's own rules are read on `as_of`; what a place borrows (field probabilities and
    the coded places behind the priors) on `prior_as_of` (default `as_of`). `info["coded"]` holds the coded
    places on `as_of` (their own rules, used by `county_mix`); `info["coded_prior"]` those behind the priors.

    D-068: in a state flagged `adu_state_law_rows_complete`, a place with no ADU row is outside the state law,
    so it takes `no_state_rule_priors` (coded places of the unflagged states, by size band).
    Returns (table: geoid, rule_class, p_* over TYPES, coverage, rule_age, …, prior_source; info dict).
    """
    from lotline.config import load_state

    prior_as_of = as_of if prior_as_of is None else prior_as_of
    p = load_params("adu")
    central = {k: v.value for k, v in p.items()}
    min_count = int(central["adu_rule_min_coded"])
    edges = (central["adu_rule_band_small_max_pop"], central["adu_rule_band_mid_max_pop"])
    reforms = {st: r.assign(state=st) for st, r in reforms_with(state).items()}
    pooled = pooled_states(reforms)
    counts = field_restrict_counts(pd.concat(pooled.values(), ignore_index=True), prior_as_of)
    covs = {st: coverage_map(st, store, r, central) for st, r in reforms.items()}

    def coded_on(date: pd.Timestamp) -> pd.DataFrame:
        out = []
        for st, r in pooled.items():
            local = sorted(g for g in r.loc[r["theme"] == "adu", "jurisdiction_geoid"].unique() if len(g) > 2)
            if not local:
                continue
            cm = covs[st]
            fp_st = field_probabilities(counts, st, min_count)
            cr = current_rules(
                r, local, load_state(st).fips, date, fp_st, dict(zip(cm.reform_id, cm.coverage, strict=True))
            )
            cr = cr[cr["rule_class"] != "unknown"]
            pop = store.read(st, "jurisdictions").set_index("geoid")["pop_2020"]
            j = store.read(st, "jurisdictions").set_index("geoid")
            kind = j["kind"] if "kind" in j else pd.Series(dtype=object)
            out.append(
                cr.assign(state=st, population=cr["geoid"].map(pop).astype(float), kind=cr["geoid"].map(kind))
            )
        return pd.concat(out, ignore_index=True)

    coded_prior = coded_on(prior_as_of)
    coded = coded_prior if prior_as_of == as_of else coded_on(as_of)
    priors = rule_priors(coded_prior.dropna(subset=["population"]), edges, min_count)
    law_states = {st for st in REFORM_STATES if load_state(st).adu_state_law_rows_complete}
    if state in law_states:  # D-068: an uncoded place is outside the state law
        outside = no_state_rule_priors(
            coded_prior.dropna(subset=["population"]), edges, min_count, law_states, state
        )
        keep = (priors["state"] != state) | (
            priors["band"] == REMAINDER_BAND
        )  # (b): own remainders still apply
        priors = pd.concat([priors[keep], outside], ignore_index=True)
    fp = field_probabilities(counts, state, min_count)
    cm = covs[state]
    rules = current_rules(
        reforms[state],
        geoids,
        load_state(state).fips,
        as_of,
        fp,
        dict(zip(cm.reform_id, cm.coverage, strict=True)),
    )
    juris = store.read(state, "jurisdictions").set_index("geoid")
    rules = rules.assign(
        state=state, population=rules["geoid"].map(juris["pop_2020"]).astype(float),
        kind=rules["geoid"].map(juris["kind"] if "kind" in juris else pd.Series(dtype=object)),
    )  # fmt: skip
    rules = apply_priors(rules, priors, edges).drop(columns=["state", "band", "kind"])
    info = {
        "field_counts": counts,
        "field_probs": fp,
        "priors": priors,
        "coded": coded,
        "coded_prior": coded_prior,
        "coverage": covs,
    }
    return rules, info


def county_mix(places: pd.DataFrame, state: str, store, origin: int, coded: pd.DataFrame) -> pd.DataFrame:
    """D-021: blend the rules of coded places that BPS files under a county row (no jurisdiction of their own,
    e.g. Wilmington) into that row, weighted by their share of the row's eligible parcels.

    Share = the place's ACS one-unit detached homes in the county (newest vintage <= origin; Census county
    shares for places spanning counties) / the row's eligible parcels, capped at 1. Row p_* becomes
    (1 − w)·p_row + w·p_place. The mean c is right; a draw still picks one type for the whole row.
    """
    from lotline.adapters.national import geoparts
    from lotline.config import load_state

    juris = set(store.read(state, "jurisdictions")["geoid"])
    orphans = coded[(coded["state"] == state) & ~coded["geoid"].isin(juris) & (coded["geoid"].str.len() == 7)]
    if orphans.empty:
        return places
    shares = geoparts.county_shares(load_state(state).fips, sorted(orphans["geoid"]), store)
    acs = store.read(state, "acs_geo_year")
    acs = acs[(acs["variable"] == "B25024_002") & (acs["end_year"] <= origin) & acs["estimate"].notna()]
    homes = acs.sort_values("end_year").groupby("geo")["estimate"].last()
    out = places.copy()
    rows = out.index[out["kind"] == "county_unincorporated"]
    for o in orphans.itertuples():
        h = float(homes.get(f"place:{o.geoid}", np.nan))
        for sh in shares[shares["place_geoid"] == o.geoid].itertuples():
            target = [i for i in rows if out.at[i, "county_geoid"] == sh.county_geoid]
            if not target or np.isnan(h):
                continue
            i = target[0]
            w = min(1.0, h * sh.share / max(float(out.at[i, "eligible_parcels"]), 1.0))
            for col in P_COLS:
                out.at[i, col] = (1 - w) * out.at[i, col] + w * getattr(o, col)
            out.at[i, "rule_note"] = f"{out.at[i, 'rule_note']}; mixes {o.geoid}'s rule on {w:.0%} of lots"
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1)
    return out


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


def observed_terms_by_k_row(
    counts: pd.DataFrame, origin: int, n_years: int, stops: Mapping[str, int]
) -> dict[str, dict[int, float]]:
    """The observed floor per place split by undercount row: GEOID -> {k_row: raw ADU permits a year}.

    Same window as `observed_per_year`; `counts` from `observed_adu_counts(..., undercount)` (columns
    `counted`, `k_row`). Summing raw x k over the rows gives `observed_per_year`, so `run` can redraw k.
    By hand: 4 years, raw 1, 2, 3, 6 all from row 0 -> {0: 3.0}; 2 from row 0 and 2 from row -1 -> {0: 0.5,
    -1: 0.5}.
    """
    out: dict[str, dict[int, float]] = {}
    for g, grp in counts.groupby("geoid"):
        last = min(origin, stops.get(g, stops.get("*", 9999)) - 1)
        w = grp[grp["year"].between(last - n_years + 1, last)]
        if w["year"].nunique() < n_years:  # a year with no records: not observed (`observed_per_year`)
            continue
        out[g] = {int(r): float(v) / n_years for r, v in w.groupby("k_row")["counted"].sum().items()}
    return out


def observed_rate_draws(places: pd.DataFrame, n: int, seed: int, table=None) -> np.ndarray | None:
    """Observed ADU permits per parcel a year in each draw (draws x places), with each draw's k (D-078 §5:
    one shared z for field rows, its own for each parser row), or None when `places` has no per-row split.

    A place with no observed floor (NaN) stays NaN. Rows index `undercount.resolve(table)` (the config table
    by default, as `places_from_store` used); -1 is k = 1.
    """
    from lotline.model import undercount as uc

    if "observed_adu_by_k_row" not in places:
        return None
    rows = uc.resolve(table)
    k = np.hstack([uc.draw_matrix(rows, n, np.random.default_rng(seed)), np.ones((n, 1))])  # last: k = 1
    m = np.zeros((len(places), len(rows) + 1))
    for i, terms in enumerate(places["observed_adu_by_k_row"]):
        if isinstance(terms, dict):
            for r, v in terms.items():
                m[i, r] += v  # r = -1 lands in the last column
    e = places["eligible_parcels"].to_numpy(dtype=float)
    rate = (k @ m.T) / np.where(e > 0, e, np.nan)
    return np.where(places["observed_rate"].isna().to_numpy()[None, :], np.nan, rate)


def holdout_stops(holdouts) -> dict[str, int]:
    """First year a held-out place's outcomes are missing from the store: GEOID -> year of `outcome_from`
    (for the place and every GEOID its outcomes are reported under). A statewide holdout is keyed "*". A
    released holdout (`released_on`, `validation.holdout.still_blind`) no longer hides anything: skipped."""
    out: dict[str, int] = {}
    for h in holdouts:
        if h.released_on:
            continue
        for g in ["*"] if h.statewide else h.geoids:
            out[g] = min(out.get(g, 9999), h.outcome_from.year)
    return out


def observed_per_year(counts: pd.DataFrame, origin: int, n_years: int, stops: Mapping[str, int]) -> pd.Series:
    """Mean ADU permits a year per place over the `n_years` years ending at `origin` (WS-NC-GUTCHECK).

    A held-out place's years end the year before its holdout starts (`stops`), so a partly held-out year is
    never read as a low count and no held-out outcome is used; its window keeps `n_years` years.

    Coverage (2026-11-19, Ben): `observed_adu_counts` has a row for a place and year only where a source that
    flags ADUs holds at least one record of any kind for that place that year (0 when none was an ADU). A
    place observed only if every window year has a row; otherwise it is left out (NaN after mapping) and
    the mechanism estimates it. A year with no records means the source was not recording there (a source
    that ended, such as Chapel Hill's in 2021; a county source holding a few stray rows for a town mostly in
    the next county; a list of ADU permits only), not that no ADU was built.

    By hand: origin 2025, 4 years, place A 2022-25 = 1, 2, 3, 6 -> 3.0; place B held out from 2023 with
    2019-22 = 2, 2, 4, 0 -> 2.0; place C with rows 2022, 2023, 2025 only -> left out.
    """
    rows = {}
    for g, grp in counts.groupby("geoid"):
        last = min(origin, stops.get(g, stops.get("*", 9999)) - 1)
        by_year = grp.set_index("year")["adu_permits"]
        window = range(last - n_years + 1, last + 1)
        if not all(y in by_year.index for y in window):
            continue
        rows[g] = sum(float(by_year[y]) for y in window) / n_years
    return pd.Series(rows, dtype=float, name="adu_permits_per_year")
