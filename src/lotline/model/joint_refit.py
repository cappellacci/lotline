"""The five-state ADU joint refit (analysis plan D-079, with D-074, D-075, D-078, D-080, D-081).

D-079 fixed, before any fit, the two candidate forms and the rule that chooses between them:

- **Form A** is D-048 as adopted: `calibrate_adu.fit3` (θ, α and the rule shares m_o, m_x).
- **Form B** is D-047's approach 3 (`calibrate_shape.fit_empirical`) plus g d_it + g_m d̄_i: d_it is the
  D-023 dose of the strongest rule in force on 1 July (none 0, permit or conditional use 1/3, by right with
  owner occupancy 2/3, by right without it 1) and d̄_i the place's mean dose over its fit years. g is
  estimated only if the in-window events (`events`) number at least 8 in at least 3 states
  (`g_identified`); otherwise g and g_m are held at 0 and Form B is approach 3 as run in D-047.

This module holds the pieces that do not read data: the dose and events, Form B's design, the state effect
each form carries to a held-out state, the predictive draws for D-075's data tiers (tier 2 updates the state
effect from one city's counts by reweighting the shared draws), the scores (inside P10-P90, observed ÷ P50,
CRPS, log score), D-075's claim rule, the pass bars of tests A-C (D-074 §3) and D-079's decision rule. The run
itself (`scripts/dev/adu_joint_refit.py`) builds the places from the processed tables.
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from lotline.model import calibrate_adu as cal
from lotline.model import calibrate_shape as shp
from lotline.model.scenarios import adu

# ---------------------------------------------------------------------------------------------------------
# Form B: the dose, the in-window events and the identification rule
# ---------------------------------------------------------------------------------------------------------

DOSE_PERMIT, DOSE_OWNER, DOSE_FULL = 1.0 / 3.0, 2.0 / 3.0, 1.0  # D-023 grades; no rule in force is 0
MIN_EVENTS, MIN_EVENT_STATES, MIN_SIDE = 8, 3, 2  # D-079's identification rule, fixed before any fit
TYPE_DOSE = {
    "none": 0.0,
    "owner": DOSE_OWNER,
    "other": DOSE_PERMIT,
    "both": DOSE_PERMIT,
    "handbook": DOSE_FULL,
}


def rule_dose(no_by_right, owner) -> np.ndarray:
    """D-023 grade of one rule: 1/3 if not by right (permit or conditional use), else 2/3 with owner
    occupancy, else 1. By hand: (True, True) -> 1/3, (False, True) -> 2/3, (False, False) -> 1."""
    no_by_right, owner = np.asarray(no_by_right, dtype=bool), np.asarray(owner, dtype=bool)
    return np.where(no_by_right, DOSE_PERMIT, np.where(owner, DOSE_OWNER, DOSE_FULL))


def dose_path(pl: cal.PlaceData) -> np.ndarray:
    """d_it per fit year: the strongest rule in force (max over rules), averaged over the place's blank-field
    combinations by their weights. A place whose rules carry only a type (D-075 tier 0 borrows rules by
    size band) reads its dose from the type (`TYPE_DOSE`; 'other' and 'both' as 1/3).

    By hand: one combination, rules (permit, by right with owner occupancy) in force -> 2/3; two equally
    weighted combinations whose blank field makes the rule permit-only in one -> (1/3 + 1) / 2 = 2/3."""
    ex = pl.extra or {}
    w = pl.w / pl.w.sum()
    live = ~np.isnan(ex["age"]) if "age" in ex else np.ones(pl.types.shape[1:], dtype=bool)
    if "no_by_right" in ex and "owner" in ex:
        grade = rule_dose(ex["no_by_right"], ex["owner"])
    else:
        grade = np.vectorize(lambda i: TYPE_DOSE[adu.TYPES[i]])(pl.types).astype(float)
    grade = np.where(live[None], grade, 0.0).max(axis=2)  # (C, T)
    return w @ grade


def events(places: Sequence[cal.PlaceData], min_side: int = MIN_SIDE) -> pd.DataFrame:
    """D-079's in-window events, built by code from the coded rows: every place whose d_it changes between two
    consecutive fit years with at least `min_side` fit years on each side. One row per change.

    By hand: doses (1/3, 1/3, 1, 1) over 2018-2021 -> one event in 2020 (2 years each side); (1/3, 1, 1, 1)
    -> none (one year before)."""
    rows = []
    for pl in places:
        d = dose_path(pl)
        n = len(d)
        for i in range(1, n):
            if abs(d[i] - d[i - 1]) > 1e-9 and i >= min_side and n - i >= min_side:
                rows.append(
                    {
                        "state": pl.state,
                        "geoid": pl.geoid,
                        "name": pl.name,
                        "year": int(pl.years[i]),
                        "dose_before": float(d[i - 1]),
                        "dose_after": float(d[i]),
                        "years_before": i,
                        "years_after": n - i,
                    }
                )
    cols = ["state", "geoid", "name", "year", "dose_before", "dose_after", "years_before", "years_after"]
    return pd.DataFrame(rows, columns=cols)


def g_identified(ev: pd.DataFrame, min_events: int = MIN_EVENTS, min_states: int = MIN_EVENT_STATES) -> bool:
    """D-079: g is estimated only with at least 8 events in at least 3 states."""
    return len(ev) >= min_events and ev["state"].nunique() >= min_states


NAMES_B = (*shp.NAMES, "dose (g)", "mean dose (g_m)")


def design_b(pl: cal.PlaceData, with_dose: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Form B's (X, offset): approach 3's design (`calibrate_shape.design`) plus d_it and d̄_i when g is
    identified. A place whose rules are borrowed with a 'none' share (tier 0) has its offset lowered by
    log(1 - P(none)): the expected count is that of the places allowing ADUs times their share."""
    x, off = shp.design(pl)
    p_none = _p_none(pl)
    if np.any(p_none > 0):
        off = off + np.log(np.clip(1.0 - p_none, 1e-12, None))
    if not with_dose:
        return x, off
    d = dose_path(pl)
    return np.column_stack([x, d, np.full(len(d), d.mean())]), off


def _p_none(pl: cal.PlaceData) -> np.ndarray:
    """P(no ADUs) per year: the weight of combinations in which every rule in force is type 'none'."""
    w = pl.w / pl.w.sum()
    ex = pl.extra or {}
    live = ~np.isnan(ex["age"]) if "age" in ex else np.ones(pl.types.shape[1:], dtype=bool)
    none = np.all((pl.types == adu.TYPES.index("none")) | ~live[None], axis=2)  # (C, T)
    return w @ none


@dataclass(frozen=True)
class FormB:
    """A Form B fit: the approach-3 coefficients, with the dose terms when g was identified."""

    fit: shp.EmpFit
    with_dose: bool

    def design(self, pl: cal.PlaceData) -> tuple[np.ndarray, np.ndarray]:
        return design_b(pl, self.with_dose)


def fit_form_b(places: Sequence[cal.PlaceData], with_dose: bool, starts: int = 5, seed: int = 47) -> FormB:
    """Maximum likelihood as D-047 (Nelder-Mead, best of five starts, observed-information covariance)."""
    fn = lambda pl: design_b(pl, with_dose)  # noqa: E731
    return FormB(shp.fit_empirical(list(places), starts=starts, seed=seed, design_fn=fn), with_dose)


def state_shift(places: Sequence[cal.PlaceData], b: FormB, bound: float = 6.0) -> float:
    """The intercept shift δ that maximizes one state's places' likelihood with every other coefficient held
    at the fit (Form B's analogue of a state multiplier)."""
    d = shp.EmpData.of(list(places), b.design)
    base = np.r_[b.fit.beta, math.log(max(b.fit.alpha, 1e-12))]

    def ll(delta):
        q = base.copy()
        q[0] += delta
        v = shp.emp_loglik(q, d)
        return v if math.isfinite(v) else -1e300

    return float(cal._golden_max(ll, -bound, bound)[0])


def shift_spread(shifts: Sequence[float]) -> float:
    """s, the spread of the fitted states' intercept shifts: their standard deviation (ddof 1). By hand:
    shifts (-1, 0, 1, 2) -> s = sd = 1.291."""
    return float(np.std(np.asarray(shifts, dtype=float), ddof=1))


# ---------------------------------------------------------------------------------------------------------
# Predictive draws for a held-out state (D-075 tiers): shared global draws, per-place u
# ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GlobalsA:
    """Form A's shared draws: scale = θ × v (θ from its interval, v = exp(τ z) the state multiplier)."""

    scale: np.ndarray
    alpha: float
    cvals: np.ndarray


@dataclass(frozen=True)
class GlobalsB:
    """Form B's shared draws: coefficient vectors β and a state intercept δ."""

    betas: np.ndarray
    delta: np.ndarray
    alpha: float
    form: FormB


def globals_a(fit: cal.Fit3, taus, n: int, seed: int) -> GlobalsA:
    """θ ~ lognormal from its profile interval; τ per draw (`taus`: scalar or n values; 0 = no state effect);
    z ~ N(0, 1)."""
    rng = np.random.default_rng(seed)
    theta = np.exp(rng.normal(math.log(fit.theta), fit.log_se, size=n))
    tau = np.broadcast_to(np.asarray(taus, dtype=float), (n,))
    v = np.exp(tau * rng.standard_normal(n))
    return GlobalsA(theta * v, fit.alpha, cal._cvals(fit.m_owner, fit.m_other))


def globals_b(b: FormB, s: float, n: int, seed: int) -> GlobalsB:
    """β ~ N(β̂, Σ); δ ~ N(0, s²) (s = 0: no state effect)."""
    rng = np.random.default_rng(seed)
    k = len(b.fit.beta)
    betas = rng.multivariate_normal(b.fit.beta, b.fit.cov[:k, :k], size=n, check_valid="ignore")
    delta = rng.normal(0.0, s, size=n) if s > 0 else np.zeros(n)
    return GlobalsB(betas, delta, b.fit.alpha, b)


def _n(g) -> int:
    return len(g.scale) if isinstance(g, GlobalsA) else len(g.delta)


def _take(g, idx: np.ndarray):
    if isinstance(g, GlobalsA):
        return replace(g, scale=g.scale[idx])
    return replace(g, betas=g.betas[idx], delta=g.delta[idx])


def _marginal(y: np.ndarray, mu: np.ndarray, alpha: float, log_fact: float) -> np.ndarray:
    """log P(y_1..T) per row of mu (draws × T), the gamma place effect integrated (`frailty_loglik_place`).
    A zero mean with a positive count gives -inf."""
    bad = ((mu <= 0) & (y[None, :] > 0)).any(axis=1)
    big_y = float(y.sum())
    head = (y[None, :] * np.log(np.maximum(mu, 1e-300))).sum(axis=1) - log_fact
    big_m = mu.sum(axis=1)
    if alpha <= 1e-8:
        out = head - big_m
    else:
        r = 1.0 / alpha
        out = (
            head + math.lgamma(big_y + r) - math.lgamma(r) + r * math.log(r) - (big_y + r) * np.log(r + big_m)
        )
    return np.where(bad, -np.inf, out)


def _logsumexp_rows(a: np.ndarray, axis: int) -> np.ndarray:
    m = np.max(a, axis=axis, keepdims=True)
    m = np.where(np.isfinite(m), m, 0.0)
    return np.squeeze(m, axis=axis) + np.log(np.exp(a - m).sum(axis=axis))


def place_loglik(pl: cal.PlaceData, g) -> np.ndarray:
    """log P(the place's observed counts | each global draw): place effect integrated, blank-field
    combinations summed by weight (Form A). Used for tier 2's update and the held-out log score."""
    y = np.asarray(pl.y, dtype=float)
    lf = float(sum(math.lgamma(v + 1) for v in y))
    if isinstance(g, GlobalsA):
        ks = pl.k(g.cvals)  # (C, T)
        share = pl.w / pl.w.sum()
        lw = np.log(np.where(share > 0, share, 1.0))  # zero-weight combinations are skipped below
        per = np.stack(
            [
                lw[c] + _marginal(y, g.scale[:, None] * ks[c][None, :], g.alpha, lf)
                for c in range(len(ks))
                if pl.w[c] > 0
            ],
            axis=1,
        )
        return _logsumexp_rows(per, axis=1)
    x, off = g.form.design(pl)
    mu = np.exp(np.clip(off[None, :] + g.betas @ x.T + g.delta[:, None], None, 30))
    return _marginal(y, mu, g.alpha, lf)


def update(g, pl: cal.PlaceData, seed: int):
    """D-075 tier 2: the shared draws given one city's counts. Each draw is weighted by
    P(city counts | draw) (`place_loglik`), then the draws are resampled by weight (multinomial), so the
    state effect (and θ or β) carry what the city's counts say. Returns (resampled draws, effective sample
    size)."""
    lw = place_loglik(pl, g)
    if not np.isfinite(lw).any():
        raise ValueError(f"{pl.name}: no draw can produce its counts")
    w = np.exp(lw - lw[np.isfinite(lw)].max())
    w = np.where(np.isfinite(w), w, 0.0)
    w = w / w.sum()
    ess = float(1.0 / (w**2).sum())
    idx = np.random.default_rng(seed).choice(len(w), size=len(w), p=w)
    return _take(g, idx), ess


def predict(places: Sequence[cal.PlaceData], g, seed: int) -> dict[str, np.ndarray]:
    """Joint predictive counts {geoid: draws × years}: the shared draws, then each place's own new place
    effect u ~ Gamma(mean 1, variance α) and (Form A) blank-field combination, from a stream keyed by
    (seed, geoid), so a place draws alike whichever places it is predicted with."""
    n = _n(g)
    out = {}
    for pl in places:
        rng = np.random.default_rng([seed, zlib.crc32(pl.geoid.encode())])
        u = rng.gamma(1 / g.alpha, g.alpha, size=n) if g.alpha > 0 else np.ones(n)
        if isinstance(g, GlobalsA):
            combo = rng.choice(len(pl.w), size=n, p=pl.w / pl.w.sum())
            mu = (g.scale * u)[:, None] * pl.k(g.cvals)[combo]
        else:
            x, off = g.form.design(pl)
            mu = u[:, None] * np.exp(np.clip(off[None, :] + g.betas @ x.T + g.delta[:, None], None, 30))
        out[pl.geoid] = rng.poisson(mu)
    return out


def held_out_log_score(pl: cal.PlaceData, g) -> float:
    """D-049's held-out log score of one place under the draws: log mean_j P(y | draw j)."""
    lw = place_loglik(pl, g)
    return float(_logsumexp_rows(lw[None, :], axis=1)[0] - math.log(len(lw)))


# ---------------------------------------------------------------------------------------------------------
# Building a tier's places: lots from ACS, rules borrowed by size band
# ---------------------------------------------------------------------------------------------------------


def _cut(v, keep: np.ndarray):
    """An `extra` input restricted to the kept years: (T,), (T, R) or (C, T, R) arrays."""
    if not isinstance(v, np.ndarray):
        return v
    return v[:, keep] if v.ndim == 3 else v[keep]


def subset_years(pl: cal.PlaceData, years) -> cal.PlaceData | None:
    """The place restricted to `years` (None if none of them are fit years)."""
    keep = np.isin(pl.years, list(years))
    if not keep.any():
        return None
    return replace(
        pl,
        years=pl.years[keep],
        y=pl.y[keep],
        base=pl.base[keep],
        types=pl.types[:, keep, :],
        cr=pl.cr[keep],
        detached=None if pl.detached is None else pl.detached[:, keep, :],
        extra={k: _cut(v, keep) for k, v in (pl.extra or {}).items()},
    )


def with_lots(pl: cal.PlaceData, lots: np.ndarray) -> cal.PlaceData:
    """The place on other eligible lots (tier 0: ACS one-unit detached homes): base and the parcel input
    scale by lots / the roll's lots; rent, value, rate and the pro forma hazard are unchanged."""
    lots = np.asarray(lots, dtype=float)
    ex = dict(pl.extra or {})
    ratio = lots / ex["parcels"]
    ex["parcels"] = lots
    return replace(pl, base=pl.base * ratio, extra=ex)


QUANTILE_COMBOS = 40  # equally weighted combinations that carry a borrowed rule's per-year type mix


def quantile_types(p: np.ndarray, m: int = QUANTILE_COMBOS) -> np.ndarray:
    """(m, T) type indices whose share in each year matches the year's probabilities `p` (T × types) to
    1 / m: combination j takes the type at cumulative probability (j + 0.5) / m. The same j sits at the same
    rank every year, so a place keeps its place in the band's distribution over time. By hand, m = 4 and
    p = (0.5 none, 0.5 Handbook): types (none, none, Handbook, Handbook)."""
    p = np.asarray(p, dtype=float)
    u = (np.arange(m) + 0.5) / m
    cdf = np.cumsum(p, axis=1) / p.sum(axis=1, keepdims=True)
    return (u[:, None, None] > cdf[None, :, :] + 1e-12).sum(axis=2).clip(max=p.shape[1] - 1)


def with_borrowed_rules(
    pl: cal.PlaceData, p_local: np.ndarray, age: np.ndarray, law=None, law_age=None, m: int = QUANTILE_COMBOS
) -> cal.PlaceData:
    """The place with its local rule borrowed (D-075 tier 0, as D-068).

    `p_local` (T × TYPES): the size band's type probabilities each year; `age` (T,): the band's mean rule age.
    `law` (T × TYPES, NaN rows where no state ADU law is in force) and `law_age` (T,): the state law's own
    type probabilities and age; the stronger rule counts, as in `PlaceData.k`. The local mix enters as `m`
    equally weighted combinations (`quantile_types`), each crossed with the law's types (weighted by the
    law's probabilities in the years it is in force). Coverage and the ramp are 1 (D-048: no ramp; coverage
    is already in the 'none' share). Detached ADUs are taken as allowed, and Form B reads the dose from the
    type (`TYPE_DOSE`).

    By hand: p_local (0.5 none, 0.5 Handbook) in every year, no law -> E[k] = base × c(Handbook) / 2."""
    p_local = np.asarray(p_local, dtype=float)
    n_t = p_local.shape[0]
    local = quantile_types(p_local, m)  # (m, T)
    law = None if law is None else np.asarray(law, dtype=float)
    on = np.zeros(n_t, dtype=bool) if law is None else np.isfinite(law).all(axis=1)
    if on.any():
        p_law = law[on].mean(axis=0)
        laws = [b for b in range(len(p_law)) if p_law[b] > 0]
        types = np.zeros((m * len(laws), n_t, 2), dtype=int)
        w = np.zeros(m * len(laws))
        for j in range(m):
            for i, b in enumerate(laws):
                c = j * len(laws) + i
                types[c, :, 0], types[c, :, 1], w[c] = local[j], b, p_law[b] / m
        la = np.where(on, np.asarray(law_age, dtype=float), np.nan)
        ages = np.column_stack([np.asarray(age, dtype=float), la])
        cr = np.column_stack([np.ones(n_t), on.astype(float)])
    else:
        types, w = local[:, :, None], np.full(m, 1.0 / m)
        ages, cr = np.asarray(age, dtype=float)[:, None], np.ones((n_t, 1))
    ex = {k: v for k, v in (pl.extra or {}).items() if k not in ("no_by_right", "owner")}
    ex |= {"age": ages, "cov": cr.copy(), "no_detached": np.zeros(types.shape, dtype=bool)}
    return replace(pl, types=types, cr=cr, w=w, detached=None, extra=ex)


def borrowed_by_band(donors: pd.DataFrame, edges, min_count: int) -> pd.DataFrame:
    """Band means of the donor places' type probabilities and rule age (D-068's pooled band mean): for each
    size band, the donors in it if at least `min_count`, else every donor. `donors`: population, p_* and
    rule_age. By hand: band 0 with 2 'none' and 3 Handbook donors (min 5) -> p_none 0.4, p_handbook 0.6."""
    d = donors.assign(band=adu.size_band(donors["population"].fillna(0), edges))
    rows = []
    for band in range(len(edges) + 1):
        own = d[d["band"] == band]
        use, src = (own, "band") if len(own) >= min_count else (d, "all bands")
        age = use["rule_age"].dropna()
        rows.append(
            {
                "band": band,
                "n_donors": len(own),
                "source": src,
                **use[list(adu.P_COLS)].mean().to_dict(),
                "rule_age": float(age.mean()) if len(age) else 0.0,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Scores, D-075's claim rule, tests A-C and D-079's decision rule
# ---------------------------------------------------------------------------------------------------------

P_BANDS = (10, 50, 90)


def crps(draws, observed: float) -> float:
    """CRPS of the sample: E|X - y| - E|X - X'| / 2 (the sorted-sample formula). By hand: draws (0, 2),
    y = 1 -> 1 - 0.5 = 0.5."""
    x = np.sort(np.asarray(draws, dtype=float))
    n = len(x)
    term1 = np.abs(x - observed).mean()
    i = np.arange(1, n + 1)
    term2 = (2 * i - n - 1) @ x / (n * n)  # E|X - X'| / 2 = Σ (2i - n - 1) x_(i) / n²
    return float(term1 - term2)


def log_score(draws, observed: float) -> float:
    """log P(total = round(observed)) from the sample's frequencies, add-one smoothed so a miss is finite:
    log((#{X = y} + 1) / (n + 1)). Counts scaled by k are not whole numbers; they are rounded first. By hand:
    draws (3, 3, 4), y = 3 -> log(3 / 4)."""
    x = np.asarray(draws)
    y = round(float(observed))
    return float(math.log(((x == y).sum() + 1) / (len(x) + 1)))


def score(observed: float, draws) -> dict:
    """D-075's per-state, per-tier scores of an observed total against summed predictive draws."""
    d = np.asarray(draws, dtype=float)
    lo, mid, hi = np.percentile(d, P_BANDS)
    ratio = observed / mid if mid > 0 else (math.inf if observed > 0 else 1.0)
    inside = bool(lo <= observed <= hi)
    within2 = bool(0.5 <= ratio <= 2.0)
    pct = float((d < observed).mean() + 0.5 * (d == observed).mean())
    return {
        "observed": float(observed),
        "p10": float(lo),
        "p50": float(mid),
        "p90": float(hi),
        "inside": inside,
        "obs_over_p50": float(ratio),
        "within_2x": within2,
        "useful": inside and within2,
        "percentile": pct,
        "crps": crps(d, observed),
        "log_score": log_score(d, observed),
    }


def claim_tier(results: pd.DataFrame, min_states: int = 4) -> int | None:
    """D-075's claim rule: the lowest tier at which, in at least `min_states` held-out states, the observed
    total lies within P10-P90 and observed ÷ P50 is within ×2. `results`: columns state, tier, useful. None if
    no tier passes. By hand: tier 0 useful in 3 states and tier 1 in 4 -> 1."""
    for tier in sorted(results["tier"].unique()):
        r = results[results["tier"] == tier]
        if int(r["useful"].sum()) >= min_states:
            return int(tier)
    return None


def test_a_pass(rows: pd.DataFrame) -> bool | None:
    """D-074 test A in one state: at least 60% of the new places inside P10-P90 and the median of observed ÷
    P50 within ×2. None if the state has no new place. By hand: inside (T, T, F), ratios (0.8, 1.5, 3.0) ->
    67% inside, median 1.5 -> pass."""
    if rows.empty:
        return None
    return bool(rows["inside"].mean() >= 0.6 and 0.5 <= float(rows["obs_over_p50"].median()) <= 2.0)


def test_b_pass(observed_total: float, draws) -> bool:
    """D-074 test B: the roll total (the k-setting city left out) lies within P10-P90 of the summed model."""
    lo, hi = np.percentile(np.asarray(draws, dtype=float), (10, 90))
    return bool(lo <= observed_total <= hi)


def test_c_pass(ratios: Sequence[float]) -> bool | None:
    """D-074 test C: the no-reform median a year is at least the counted ADUs a year (k applied) in every
    counted place: every ratio (median / counted) >= 1. None with no counted place."""
    r = [float(v) for v in ratios if v is not None and math.isfinite(float(v))]
    return None if not r else bool(min(r) >= 1.0)


def tests_passed(passes: Mapping[str, Mapping[str, bool | None]]) -> int:
    """Tests A-C passed, counted state by state ({test: {state: pass or None}}; None = does not apply)."""
    return int(sum(bool(v) for by_state in passes.values() for v in by_state.values() if v is not None))


@dataclass(frozen=True)
class Decision:
    form: str
    reason: str


def decide(
    tier_a: int | None,
    tier_b: int | None,
    log_gain_b: float,
    log_gain_se: float,
    tests_a: int,
    tests_b: int,
) -> Decision:
    """D-079's decision rule, fixed before any fit.

    Form A is kept unless Form B passes at a lower tier than A (a form that passes no tier counts as never
    passing), or both pass at the same tier and B's tier-1 held-out log score beats A's by more than 2 paired
    SE, while B passes at least as many of tests A-C (state by state) as A. If neither passes any tier, A is
    kept. By hand: (A none, B 1, tests 3 vs 3) -> B; (1, 1, gain 10, SE 4, tests 3 vs 3) -> B; same with
    tests 3 vs 2 -> A; (1, 1, gain 7, SE 4) -> A; (none, none) -> A."""
    if tier_a is None and tier_b is None:
        return Decision("A", "neither form passes any tier: Form A is kept and the tool shows tier-2 ranges")
    tests_ok = tests_b >= tests_a
    lower = tier_b is not None and (tier_a is None or tier_b < tier_a)
    same = tier_a is not None and tier_b == tier_a
    beats = same and log_gain_b > 2 * log_gain_se
    if (lower or beats) and tests_ok:
        why = (
            "B passes at a lower tier" if lower else "same tier and B's tier-1 log score beats A's by > 2 SE"
        )
        return Decision("B", f"{why}, and B passes at least as many of tests A-C ({tests_b} vs {tests_a})")
    if (lower or beats) and not tests_ok:
        return Decision(
            "A", f"B scores better on the tiers but passes fewer of tests A-C ({tests_b} vs {tests_a})"
        )
    return Decision("A", "B does not pass at a lower tier, nor beat A's tier-1 log score by more than 2 SE")


def sum_draws(draws: Mapping[str, np.ndarray], geoids: Sequence[str]) -> np.ndarray:
    """Per-draw totals over places and years."""
    return sum(draws[g].sum(axis=1) for g in geoids)


FitFn = Callable[[Sequence[cal.PlaceData]], object]
