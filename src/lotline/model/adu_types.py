"""D-088: place types shared across states (Form P), and Part 1's breakdown of the place effects.

    E[y_it | u_i] = θ · exp(β_o z_i) · exp(Σ_j β_j d_ij) · u_i · k_it,   u_i ~ Gamma(mean 1, variance α)

d_ij is 1 if place i is of type j. Suburb is the reference type, so the terms are core city and town (at most
two numbers), shared by every state. The base is Form A (β_o = 0) or Form A′ (D-084). With every β_j = 0 this
is the base exactly.

**Types, from national data only** (`assign_types`): in each metropolitan area (OMB 2023, `jurisdictions`
`cbsa_code` / `cbsa_type`), the place with the most housing units is a core city, and so is any place in
that metro with at least a third of the largest's units. Every other place in a metro is a suburb; places in
a micropolitan area or in none are towns. `merge_small` applies D-088's minimum size rule.

**Fit.** Fit 3's procedure, as `adu_owner.fit3_term`: on every (m_o, m_x) cell θ, α, (β_o) and the type terms
are maximized together (Nelder–Mead from the base's start, two passes, as `adu_trend`); the cell and the rule
shares' intervals are read as fit 3 does; θ's 90% interval is profiled over the candidate cells and α with
the place terms held at their estimates; β_o and each β_j get their own profile intervals. With the type
terms held at 0 it reproduces `adu_owner.fit3_term` (tested).

**Draws.** Each β_j ~ N(β̂_j, se_j) independently, as β_o (`type_draws`); `joint_refit.GlobalsA.type_beta`
carries them and scales a place carrying `extra["type_d"]` (`with_types`) per draw.

**Part 1** (`effects`, `variance_shares`): each place's log posterior-mean effect under the base form, and
the share of their variance (weighted by fit years) that each grouping explains.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from lotline.model import adu_owner as ao
from lotline.model import adu_screen as scr
from lotline.model import calibrate_adu as cal
from lotline.model.calibrate_shape import nelder_mead

TYPES = ("core", "suburb", "town")
REFERENCE = "suburb"
TERMS = ("core", "town")  # the non-reference types, in this order everywhere
D_KEY = "type_d"
CORE_SHARE = 1.0 / 3.0  # a second place is a core city with at least this share of the largest's units
BETA = scr.BETA


# ---------------------------------------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------------------------------------


def assign_types(juris: pd.DataFrame, core_share: float = CORE_SHARE) -> pd.Series:
    """Type per geoid. `juris` has geoid, cbsa_code, cbsa_type ('metro', 'micro' or missing) and units
    (housing units; missing counts as 0 for the ranking).

    By hand: metro M with A 300, B 120, C 90 units; micro m with D 50; E with no area ->
    A core (largest), B core (120 >= 300 / 3), C suburb (90 < 100), D town, E town."""
    j = juris.copy()
    j["units"] = pd.to_numeric(j["units"], errors="coerce").fillna(0.0)
    out = pd.Series("town", index=j["geoid"].astype(str).to_numpy(), dtype=object)
    metro = j[j["cbsa_type"] == "metro"]
    for _, m in metro.groupby("cbsa_code"):
        top = float(m["units"].max())
        for g, u in zip(m["geoid"].astype(str), m["units"], strict=True):
            out[g] = "core" if top > 0 and u >= core_share * top else "suburb"
    return out


def merge_small(
    fit_types: pd.DataFrame, min_places: int = 8, min_states: int = 3
) -> tuple[dict[str, str], list[str]]:
    """D-088's minimum size rule over the fit places (`fit_types`: state, type). A type short of `min_places`
    places in `min_states` states is merged: town into suburb, then core city into suburb. Returns
    ({type: merged type}, notes).

    By hand: core 10 places in 3 states, suburb 30 in 4, town 5 in 2 -> town merged into suburb, core kept."""
    mapping = {t: t for t in TYPES}
    notes = []

    def ok(t: str) -> bool:
        rows = fit_types[fit_types["type"].map(mapping) == t]
        return len(rows) >= min_places and rows["state"].nunique() >= min_states

    for t in ("town", "core"):
        if not ok(t):
            for k, v in mapping.items():
                if v == t:
                    mapping[k] = REFERENCE
            notes.append(
                f"{t} has fewer than {min_places} fit places in {min_states} states: merged into suburb"
            )
    return mapping, notes


UNITS_END = 2015  # D-088: the core-city ranking reads ACS 2011-15 (config adu_type_units_end_year, tested)


def units_table(store, state: str) -> pd.DataFrame:
    """Housing units per jurisdiction of `state`: ACS B25024_001 (all housing units), the latest vintage
    ending in `UNITS_END` or earlier that the holdout filter lets through, else the latest it lets through,
    else the jurisdiction's largest eligible-lot count (flagged). A county's unincorporated remainder is the
    county less its places. Columns: state, geoid, name, kind, cbsa_code, cbsa_type, units, units_vintage,
    units_source. National data and parcel counts only: no ADU outcome is read."""
    from lotline.validation import holdout

    st = state.lower()
    a = holdout.apply_acs(store.read(st, "acs_geo_year"), st)
    a = a[(a["table_id"] == "B25024") & (a["variable"].astype(str) == "B25024_001")]
    by = a.groupby(["geo", "end_year"])["estimate"].sum()
    geos = set(by.index.get_level_values("geo"))
    juris = store.read(st, "jurisdictions")
    juris = juris.assign(geoid=juris["geoid"].astype(str))
    elig = store.read(st, "eligible_parcels")
    elig = elig[elig["theme"] == "adu"].groupby("jurisdiction_geoid")["eligible_parcels"].max()
    geo_of = {"place": "place:{}", "township": "cousub:{}"}
    rows = []
    for r in juris.itertuples():
        units, vintage, source, ser = np.nan, None, "none", None
        if r.kind == "county_unincorporated":
            cg = f"county:{r.county_geoid}"
            if cg in geos:
                ser = by.xs(cg, level="geo")
                inside = juris[
                    (juris["county_geoid"].astype(str) == str(r.county_geoid)) & (juris["kind"] == "place")
                ]
                for g in inside["geoid"]:
                    if f"place:{g}" in geos:
                        ser = ser.sub(by.xs(f"place:{g}", level="geo").reindex(ser.index).fillna(0.0))
        elif r.kind in geo_of and geo_of[r.kind].format(r.geoid) in geos:
            ser = by.xs(geo_of[r.kind].format(r.geoid), level="geo")
        if ser is not None and len(ser):
            early = ser[ser.index <= UNITS_END]
            if len(early):
                vintage = int(early.index.max())
                units = float(early.loc[vintage])
                source = "acs 2011-15" if vintage == UNITS_END else "acs early"
            else:
                vintage = int(ser.index.max())
                units, source = float(ser.loc[vintage]), "acs latest let through"
        if not np.isfinite(units) and r.geoid in elig.index:
            units, source = float(elig.loc[r.geoid]), "eligible lots (flag)"
        rows.append(
            {
                "state": st.upper(),
                "geoid": r.geoid,
                "name": r.name,
                "kind": r.kind,
                "cbsa_code": r.cbsa_code,
                "cbsa_type": r.cbsa_type,
                "units": units,
                "units_vintage": vintage,
                "units_source": source,
            }
        )
    return pd.DataFrame(rows)


def raw_types(units: pd.DataFrame, core_share: float = CORE_SHARE) -> pd.Series:
    """D-088's raw type per geoid from a `units_table`: Census places by `assign_types`; townships and
    unincorporated county areas are suburbs in a metro and towns otherwise (only a place can be a core city).

    By hand: metro M with places A 300, B 90 and township T 500; micro place D -> A core, B suburb (90 < 100;
    T is not ranked), T suburb, D town."""
    u = units.assign(geoid=units["geoid"].astype(str))
    out = pd.Series(
        np.where(u["cbsa_type"] == "metro", REFERENCE, "town"), index=u["geoid"].to_numpy(), dtype=object
    )
    places = u[u["kind"] == "place"]
    t = assign_types(places, core_share)
    out.loc[t.index] = t
    return out


def jurisdiction_types(store, state: str, core_share: float = CORE_SHARE) -> pd.Series:
    """Every jurisdiction's raw type in `state` (geoid -> core, suburb or town), as D-088 and D-089 read them.
    The scenario engine uses these with D-089's town prior, so towns stay towns (no merge)."""
    return raw_types(units_table(store, state), core_share)


def indicators(type_: str, terms: Sequence[str] = TERMS) -> np.ndarray:
    """d for one place. By hand: 'core' -> (1, 0); 'suburb' -> (0, 0); 'town' -> (0, 1)."""
    return np.array([1.0 if type_ == t else 0.0 for t in terms])


def with_types(pl: cal.PlaceData, d: np.ndarray) -> cal.PlaceData:
    """The place carrying its type indicators (read by `type_d` and `joint_refit.GlobalsA`)."""
    return replace(pl, extra=dict(pl.extra or {}) | {D_KEY: tuple(float(v) for v in d)})


def type_d(pl: cal.PlaceData, m: int = len(TERMS)) -> np.ndarray:
    """The place's indicators; zeros (the reference type) if it carries none."""
    d = (pl.extra or {}).get(D_KEY)
    return np.zeros(m) if d is None else np.asarray(d, dtype=float)


def typed_scaled(pl: cal.PlaceData, beta_o: float, betas: np.ndarray) -> cal.PlaceData:
    """The place with exp(β_o z + Σ β_j d_j) folded into its exposure: Form P at fixed terms is Form A
    on these.
    By hand: base (100,), z 0, d (1, 0), β (log 2, 0) -> (200,)."""
    f = math.exp(beta_o * ao.place_z(pl) + float(np.dot(betas, type_d(pl, len(betas)))))
    return replace(pl, base=pl.base * f)


# ---------------------------------------------------------------------------------------------------------
# Fit
# ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CellFit:
    lt: float
    la: float
    b: tuple[float, ...]  # (β_o if estimated, then one per estimated type term)
    loglik: float
    lam: float = 0.0  # D-094: log(α_core ÷ α_sub); 0 without a spread by type


LAMBDA = (-8.0, 8.0)  # D-094: search bounds on λ = log(α_core ÷ α_sub)


def alphas(la: float, lam: float, core: np.ndarray | None):
    """α per place: exp(la) (one value) without a spread by type; exp(la + λ core_i) with one (D-094).
    By hand: la 0, λ log 0.5, core (1, 0) -> (0.5, 1)."""
    if core is None:
        return math.exp(la)
    return np.exp(np.clip(la + lam * core, *scr.LOG_ALPHA))


def _ll(p: scr.Prepared, zm: np.ndarray, lt: float, la: float, b, core=None, lam: float = 0.0) -> float:
    if zm.shape[1]:
        rate = math.exp(lt) * np.exp(zm @ np.asarray(b, dtype=float))
    else:
        rate = np.full(len(p.Y), math.exp(lt))
    return float(np.sum(scr.place_loglik(p, rate, alphas(la, lam, core))))


def _maximize(
    p, zm, fixed: Mapping[int, float] | None = None, start: CellFit | None = None, core=None, lam_fixed=None
) -> CellFit:
    """Maximize over (log θ, log α, b), with the b's in `fixed` (index -> value) held. With `core` (D-094),
    also over λ = log(α_core ÷ α_sub) unless `lam_fixed` holds it; α is then α_sub."""
    fixed = dict(fixed or {})
    m = zm.shape[1]
    free = [i for i in range(m) if i not in fixed]
    free_lam = core is not None and lam_fixed is None
    x0 = [math.log(7e-4), math.log(1.5)] + [0.0] * len(free)
    if start is not None:
        x0 = [start.lt, start.la] + [start.b[i] for i in free]
    if free_lam:
        x0 = x0 + [start.lam if start is not None else 0.0]

    def unpack(x):
        b = np.zeros(m)
        for i, v in fixed.items():
            b[i] = v
        for i, v in zip(free, x[2 : 2 + len(free)], strict=True):
            b[i] = float(np.clip(v, *BETA))
        if free_lam:
            lam = float(np.clip(x[-1], *LAMBDA))
        else:
            lam = 0.0 if lam_fixed is None else float(lam_fixed)
        return float(x[0]), float(np.clip(x[1], *scr.LOG_ALPHA)), b, lam

    def neg(x):
        lt, la, b, lam = unpack(x)
        ll = _ll(p, zm, lt, la, b, core, lam)
        return -ll if np.isfinite(ll) else 1e300

    x, _ = nelder_mead(neg, np.array(x0, dtype=float), step=0.5, iters=4000, tol=1e-9)
    x, val = nelder_mead(neg, x, step=0.05, iters=4000, tol=1e-11)  # restart: Nelder-Mead can stall
    lt, la, b, lam = unpack(x)
    return CellFit(lt, la, tuple(float(v) for v in b), -val, lam)


def _lam_interval(p, zm, best: CellFit, core) -> tuple[float, float]:
    """D-094: 90% profile interval on λ (an edge at the search bound means it is open there)."""

    def gap(v):
        f = _maximize(p, zm, start=best, core=core, lam_fixed=v)
        return 2 * (best.loglik - f.loglik) - cal.CHI2_90

    def edge(far):
        lo, hi = best.lam, far
        if gap(far) < 0:
            return far
        for _ in range(30):
            mid = (lo + hi) / 2
            if gap(mid) < 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    return edge(LAMBDA[0]), edge(LAMBDA[1])


def _interval(p, zm, best: CellFit, i: int, core=None) -> tuple[float, float]:
    """90% profile interval on b_i (an edge at the search bound means it is open there)."""

    def gap(v):
        f = _maximize(p, zm, fixed={i: v}, start=best, core=core)
        return 2 * (best.loglik - f.loglik) - cal.CHI2_90

    def edge(far):
        lo, hi = best.b[i], far
        if gap(far) < 0:
            return far
        for _ in range(30):
            mid = (lo + hi) / 2
            if gap(mid) < 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    return edge(BETA[0]), edge(BETA[1])


@dataclass(frozen=True)
class Fit3Types(ao.Fit3Term):
    """A Form P fit: Form A′'s fields (β_o 0 and not estimated on an A base), plus one term per type in
    `terms` (estimated where `type_estimated`; a type with no place in the fit is held at 0)."""

    terms: tuple[str, ...] = ()
    type_beta: tuple[float, ...] = ()
    type_low: tuple[float, ...] = ()
    type_high: tuple[float, ...] = ()
    type_estimated: tuple[bool, ...] = ()
    # D-094, Form S: α (above) is then the suburbs' (and towns') variance and alpha_core the core cities'
    alpha_core: float | None = None
    lam: float = 0.0
    lam_low: float = 0.0
    lam_high: float = 0.0

    def type_se(self) -> np.ndarray:
        return (np.asarray(self.type_high) - np.asarray(self.type_low)) / (2 * ao.Z_90)


def fit3_types(
    places: Sequence[cal.PlaceData],
    estimate_beta: bool,
    terms: Sequence[str] = TERMS,
    grid=cal.GRID3,
    judgment=(0.5, 0.3),
    ranges=((0.2, 1.0), (0.1, 0.6)),
    log_theta_range=(-14.0, 0.0),
    spread: bool = False,
) -> Fit3Types:
    """Form P by fit 3's procedure (module docstring). `terms=()` fits the base form by the same optimizer.
    `spread` (D-094, Form S): core cities get their own place-effect variance, α_core = α_sub e^λ."""
    m = len(terms)
    core = is_core(places) if spread else None
    dmat = np.array([type_d(pl, m)[:m] for pl in places]).reshape(len(places), m)
    est_t = [bool(dmat[:, j].any()) for j in range(m)]
    cols = ([np.array([ao.place_z(pl) for pl in places])] if estimate_beta else []) + [
        dmat[:, j] for j in range(m) if est_t[j]
    ]
    zm = np.column_stack(cols) if cols else np.zeros((len(places), 0))
    preps = {(mo, mx): scr.prepare(places, cal._cvals(mo, mx)) for mo in grid for mx in grid}
    surface = {key: _maximize(p, zm, core=core) for key, p in preps.items()}
    lls = {key: f.loglik for key, f in surface.items()}
    top = max(lls.values())

    def interval(axis: int):
        vals = sorted({key[axis] for key in lls})
        prof = {v: max(ll for key, ll in lls.items() if key[axis] == v) for v in vals}
        inside = [v for v in vals if 2 * (top - prof[v]) <= cal.CHI2_90]
        return max(prof, key=prof.get), (min(inside), max(inside))

    (mo_hat, mo_int), (mx_hat, mx_int) = interval(0), interval(1)
    mo_est = (mo_int[1] - mo_int[0]) < (ranges[0][1] - ranges[0][0])
    mx_est = (mx_int[1] - mx_int[0]) < (ranges[1][1] - ranges[1][0])
    m_o = mo_hat if mo_est else judgment[0]
    m_x = mx_hat if mx_est else judgment[1]
    mos = list(grid) if mo_est else [judgment[0]]
    mxs = list(grid) if mx_est else [judgment[1]]
    best = surface[(m_o, m_x)]
    cands = [preps[(a, b)] for a in mos for b in mxs]

    def prof(lt):
        return max(
            scr._golden(lambda la, p=p: _ll(p, zm, lt, la, best.b, core, best.lam), *scr.LOG_ALPHA)[1]
            for p in cands
        )

    ll_hat = max(prof(best.lt), best.loglik)

    def edge(lo, hi):
        f_lo = 2 * (ll_hat - prof(lo)) - cal.CHI2_90
        for _ in range(40):
            mid = (lo + hi) / 2
            f_mid = 2 * (ll_hat - prof(mid)) - cal.CHI2_90
            if (f_mid > 0) == (f_lo > 0):
                lo, f_lo = mid, f_mid
            else:
                hi = mid
        return (lo + hi) / 2

    low, high = edge(log_theta_range[0], best.lt), edge(log_theta_range[1], best.lt)
    p = preps[(m_o, m_x)]
    ints = [_interval(p, zm, best, i, core) for i in range(zm.shape[1])]
    lam_low, lam_high = _lam_interval(p, zm, best, core) if spread else (0.0, 0.0)
    k = 1 if estimate_beta else 0
    beta, b_lo, b_hi = (best.b[0], *ints[0]) if estimate_beta else (0.0, 0.0, 0.0)
    tb, tl, th = [], [], []
    for j in range(m):
        if est_t[j]:
            tb.append(best.b[k])
            tl.append(ints[k][0])
            th.append(ints[k][1])
            k += 1
        else:
            tb.append(0.0)
            tl.append(0.0)
            th.append(0.0)
    return Fit3Types(
        theta=math.exp(best.lt),
        low=math.exp(low),
        high=math.exp(high),
        alpha=math.exp(best.la),
        m_owner=m_o,
        m_other=m_x,
        owner_interval=mo_int,
        other_interval=mx_int,
        owner_estimated=mo_est,
        other_estimated=mx_est,
        loglik=best.loglik,
        n_places=len(places),
        n_years=int(sum(len(pl.y) for pl in places)),
        beta=beta,
        beta_low=b_lo,
        beta_high=b_hi,
        beta_estimated=estimate_beta,
        terms=tuple(terms),
        type_beta=tuple(tb),
        type_low=tuple(tl),
        type_high=tuple(th),
        type_estimated=tuple(est_t),
        alpha_core=float(alphas(best.la, best.lam, np.ones(1))[0]) if spread else None,
        lam=best.lam if spread else 0.0,
        lam_low=lam_low,
        lam_high=lam_high,
    )


def is_core(places: Sequence[cal.PlaceData]) -> np.ndarray:
    """1 for a core city (its `core` indicator), else 0: D-094's spread groups. Read from the places' full
    `TERMS` indicators, whatever terms the form fits. By hand: d (1, 0) -> 1; (0, 1) -> 0; none -> 0."""
    return np.array([type_d(pl)[0] if len(type_d(pl)) else 0.0 for pl in places], dtype=float)


def type_draws(fit, n: int, seed: int) -> np.ndarray | None:
    """Draws × terms: β_j ~ N(β̂_j, se_j) independently (0 where not estimated); None without type terms."""
    if not getattr(fit, "terms", ()):
        return None
    rng = np.random.default_rng([seed, 88])
    se = fit.type_se()
    out = rng.normal(
        np.asarray(fit.type_beta), np.where(fit.type_estimated, se, 0.0), size=(n, len(fit.terms))
    )
    return out


# ---------------------------------------------------------------------------------------------------------
# Part 1: where the differences sit
# ---------------------------------------------------------------------------------------------------------


def effects(places: Sequence[cal.PlaceData], fit) -> pd.DataFrame:
    """Per place: log posterior-mean effect log((1 + α Y) / (1 + α rate K̄)) at the fit's cell, rate =
    θ exp(β_o z), and its fit years."""
    p = scr.prepare(places, cal._cvals(fit.m_owner, fit.m_other))
    z = np.array([ao.place_z(pl) for pl in places])
    rate = fit.theta * np.exp(fit.beta * z)
    a = (
        fit.alpha
        if getattr(fit, "alpha_core", None) is None
        else alphas(math.log(fit.alpha), fit.lam, is_core(places))
    )
    u = scr.posterior_mean(p, rate, a)
    return pd.DataFrame(
        {
            "geoid": [pl.geoid for pl in places],
            "state": [pl.state for pl in places],
            "name": [pl.name for pl in places],
            "years": [len(pl.y) for pl in places],
            "log_effect": np.log(u),
        }
    )


def variance_share(y, w, groups: pd.DataFrame) -> float:
    """Weighted R² of y on the group dummies (one or more columns of labels): the share of the weighted
    variance the groups explain. One column is the weighted between-group share (η²).

    By hand: y (1, 3, 5, 7), w 1, groups (a, a, b, b) -> means 2 and 6, between SS 16, total 20 -> 0.8."""
    y = np.asarray(y, dtype=float)
    w = np.asarray(w, dtype=float)
    x = pd.get_dummies(groups.astype(str), drop_first=True).to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(y)), x])
    sw = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(x * sw[:, None], y * sw, rcond=None)
    fitted = x @ coef
    mean = np.sum(w * y) / np.sum(w)
    tot = float(np.sum(w * (y - mean) ** 2))
    return float(np.sum(w * (fitted - mean) ** 2) / tot) if tot > 0 else 0.0


def reading(shares: Mapping[str, float], type_holds: bool) -> str:
    """D-088 Part 1's reading rule. "types matter" if type explains more than state and its pattern holds with
    each state left out; "counting matters" if source explains more than both; "states differ" if state
    explains the most and neither other grouping comes close (within a quarter of state's share); else
    "mixed". By hand: {state .3, type .4, source .1}, holds -> types matter; {state .3, type .1, source .4} ->
    counting matters; {state .4, type .1, source .1} -> states differ; {state .4, type .35, source .1}, not
    holding -> mixed."""
    s, t, c = shares["state"], shares["type"], shares["source"]
    if c > s and c > t:
        return "counting matters"
    if t > s and type_holds:
        return "types matter"
    if s >= t and s >= c and max(t, c) < 0.75 * s:
        return "states differ"
    return "mixed"


@dataclass(frozen=True)
class Decision:
    types: bool
    reason: str


def decide(
    tier_base: int | None,
    tier_p: int | None,
    log_gain: float,
    log_gain_se: float,
    tests_base: int,
    tests_p: int,
    d_gain: float,
    d_se: float,
) -> Decision:
    """D-088: P replaces its base only if (1) it passes D-075's claim rule at a lower tier, or both pass at
    the same tier (or neither) and its tier-1 held-out log score beats the base's by more than 2 paired SE;
    (2) it passes at least as many of tests A-B; (3) its test D log score is not worse by more than 2 paired
    SE.

    By hand: (None, None, 10, 4, 1, 1, -3, 2) -> P; gain 7 -> base; tests 1 vs 0 -> base; test D -5, SE 2 ->
    base; (2, 1, -50, 1, 1, 1, 0, 1) -> P (lower tier)."""
    fails = []
    lower = tier_p is not None and (tier_base is None or tier_p < tier_base)
    level = tier_base == tier_p
    if not (lower or (level and log_gain > 2 * log_gain_se)):
        fails.append(
            f"no lower tier, and the tier-1 log score gain {log_gain:.1f} is not above 2 SE "
            f"({2 * log_gain_se:.1f})"
        )
    if tests_p < tests_base:
        fails.append(f"fewer of tests A-B passed ({tests_p} vs {tests_base})")
    if d_gain < -2 * d_se:
        fails.append(f"test D worse by {-d_gain:.1f}, more than 2 SE ({2 * d_se:.1f})")
    if fails:
        return Decision(False, "; ".join(fails))
    why = "a lower tier" if lower else f"tier-1 log score gain {log_gain:.1f} > 2 SE ({2 * log_gain_se:.1f})"
    return Decision(True, f"{why}; tests A-B {tests_p} vs {tests_base}; test D {d_gain:+.1f} (SE {d_se:.1f})")
