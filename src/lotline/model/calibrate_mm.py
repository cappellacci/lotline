"""Calibrate the missing-middle uptake hazard on Lotline's own post-reform places (analysis plan D-038,
pre-registered; D-037 amendment).

For place i in year t at or after its adoption year T_i, at event age a = t − T_i + 0.5:

    y_it ~ Poisson(B_it + θ u_i k_it),   u_i ~ Gamma(mean 1, variance α)
    B_it = β_i g_it                          building that would have happened anyway
    k_it = E_it d_it F_i / F_ref ramp(a)     eligible parcels × dose × feasibility relative to PCR = 1 × ramp

- y: new 2-4 unit buildings (BPS); β_i: the place's mean over T − 3 … T − 1; g_it: its growth in homes outside
  2-4 unit buildings (units_1 + units_5p, centred 3-year mean over its pre-reform mean, capped).
- F = Φ((ln PCR − ln(1 + margin)) / σ) as in `hazard.feasible_share`; the rental duplex PCR is the panel's.
- u is integrated out numerically on a grid of log u (trapezoid weights renormalized to one, plus the mass
  below the grid at u = 0). θ is estimated on the log scale with α and the ramp's half-way point profiled
  out; its 90% interval is {θ : 2(ℓ̂ − ℓ_p(θ)) <= 2.706}.

`loo_backtest` is the V4 leave-one-place-out test. Only NumPy, pandas and the standard library; tests use
hand-worked examples and simulated places (tests/model/test_calibrate_mm.py).
"""

from __future__ import annotations

import functools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from lotline.model.calibrate_adu import CHI2_90, LOG_ALPHA, Z_95, _golden_max
from lotline.model.hazard import feasible_share, ramp

HALF_GRID = tuple(np.round(np.arange(0.5, 6.0001, 0.5), 1))  # ramp half-way points profiled (D-038)
SLOPE = 0.75  # ramp steepness, fixed (D-038)
G_CAP = (0.25, 4.0)  # growth index bounds (D-038)
LOG_THETA = (-16.0, -2.0)
_V = np.linspace(-25.0, 7.0, 801)  # global log-u grid for α >= ALPHA_LOCAL
ALPHA_LOCAL = 0.04  # below it the grid is local: ±10 sd around the mode (log u has sd ≈ √α)
ALPHA_POISSON = 1e-6  # below it u ≡ 1


# ---------------------------------------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Place:
    """One place's post-reform years: y (buildings), β (pre-reform mean), g (growth index), kr (k without the
    ramp), age (years since adoption at mid-year). Baseline B = β g."""

    geoid: str
    name: str
    T: int
    beta: float
    years: np.ndarray
    y: np.ndarray
    g: np.ndarray
    kr: np.ndarray
    age: np.ndarray
    eligible: np.ndarray

    @property
    def B(self) -> np.ndarray:
        return self.beta * self.g

    def upto(self, last_year: int) -> Place:
        keep = self.years <= last_year
        arrays = ("years", "y", "g", "kr", "age", "eligible")
        return replace(self, **{a: getattr(self, a)[keep] for a in arrays})

    def k(self, half: float, slope: float = SLOPE) -> np.ndarray:
        return self.kr * ramp(self.age, half, slope)


def centred_mean(series: Mapping[int, float], t: int) -> float:
    """Mean of the values at t − 1, t, t + 1 that exist.

    By hand: {1: 2, 2: 4, 3: 9}, t = 2 -> 5; t = 3 -> 6.5."""
    vals = [series[s] for s in (t - 1, t, t + 1) if s in series and pd.notna(series[s])]
    return float(np.mean(vals)) if vals else np.nan


def growth_index(series: Mapping[int, float], t: int, pre_years: Sequence[int], cap=G_CAP) -> float:
    """g_t = centred 3-year mean at t / mean over the pre-reform years, capped; 1 if either is missing or 0.

    By hand: homes {2017: 100, 2018: 100, 2019: 100, 2020: 150, 2021: 200, 2022: 250}, pre 2017-19:
    t = 2021 -> mean(150, 200, 250) / 100 = 2.0; a pre mean of 10 and a mean of 100 -> capped at 4.
    """
    pre = [series[s] for s in pre_years if s in series and pd.notna(series[s])]
    m_pre, m_t = (float(np.mean(pre)) if pre else np.nan), centred_mean(series, t)
    if not (m_pre > 0) or not np.isfinite(m_t):
        return 1.0
    return float(np.clip(m_t / m_pre, *cap))


def feasibility_ratio(pcr: float, margin: float, sigma: float) -> float:
    """F(PCR) / F(1): feasible share relative to a place where a rental duplex's value equals its cost.

    By hand: margin 0.15, σ 0.5, PCR 1.15 -> F = Φ(0) = 0.5; F(1) = Φ(ln(1/1.15) / 0.5) = Φ(−0.2795) = 0.3899;
    ratio 1.2824.
    """
    f = float(feasible_share(pcr, margin, sigma))
    return f / float(feasible_share(1.0, margin, sigma))


def place_inputs(
    panel: pd.DataFrame,
    geoids: Sequence[str],
    margin: float,
    sigma: float,
    baseline_years: int = 3,
    growth: str = "own",
    shift: int = 0,
    feasibility: bool = True,
) -> list[Place]:
    """`Place` per geoid from the D-024 panel (`estimate_mm.build_panel(...).data`).

    growth: 'own' (units_1 + units_5p), 'own_5p' (units_5p), 'state' (the same state's uncoded places' 2-4
    unit buildings, summed by year) or 'none'. shift: move T that many years earlier and keep only years
    before the real T (the placebo-date check). Places with no post-reform year or no pre-reform year with
    data are left out.
    """
    d = panel
    state_series: dict[str, dict[int, float]] = {}
    if growth == "state":
        comp = d[d["status"] == "uncoded"]
        for st, g in comp.groupby("state"):
            state_series[st] = g.groupby("year")["y_buildings"].sum(min_count=1).to_dict()
    out = []
    for gid in geoids:
        rows = d[d["place"] == gid].sort_values("year")
        if rows.empty or pd.isna(rows["T"].iloc[0]):
            continue
        T_real = int(rows["T"].iloc[0])
        T = T_real - shift
        pre = list(range(T - baseline_years, T))
        yb = rows.set_index("year")["y_buildings"]
        base_vals = [yb.get(s, np.nan) for s in pre]
        base_vals = [v for v in base_vals if pd.notna(v)]
        if not base_vals:
            continue
        beta = float(np.mean(base_vals))
        if growth in ("own", "own_5p"):
            other = rows.set_index("year")["units_5p"].astype(float)
            if growth == "own":
                other = other + rows.set_index("year")["units_1"].astype(float)
            series = other.to_dict()
        elif growth == "state":
            series = state_series.get(rows["state"].iloc[0], {})
        else:
            series = {}
        post = rows[(rows["year"] >= T) & rows["y_buildings"].notna() & (rows["eligible"] > 0)]
        if shift:
            post = post[post["year"] < T_real]
            dose = np.full(len(post), float(rows.loc[rows["year"] >= T_real, "dose"].max()))
        else:
            dose = post["dose"].to_numpy(float)
        if post.empty:
            continue
        pcr = float(rows["pcr"].dropna().iloc[0]) if rows["pcr"].notna().any() else np.nan
        fr = feasibility_ratio(pcr, margin, sigma) if feasibility and np.isfinite(pcr) else 1.0
        years = post["year"].to_numpy(int)
        g = np.array([growth_index(series, int(t), pre) if series else 1.0 for t in years])
        E = post["eligible"].to_numpy(float)
        out.append(
            Place(
                geoid=gid,
                name=str(rows["name"].iloc[0]),
                T=T,
                beta=beta,
                years=years,
                y=post["y_buildings"].to_numpy(float),
                g=g,
                kr=E * dose * fr,
                age=years - T + 0.5,
                eligible=E,
            )
        )
    return out


# ---------------------------------------------------------------------------------------------------------
# Likelihood
# ---------------------------------------------------------------------------------------------------------


@functools.lru_cache(maxsize=4096)
def _u_grid(alpha: float) -> tuple[np.ndarray, np.ndarray, float]:
    """(u values, weights summing to 1 − lump, lump mass at u = 0) for u ~ Gamma(mean 1, variance α)."""
    r = 1.0 / alpha
    if alpha < ALPHA_LOCAL:
        s = math.sqrt(alpha)
        v = np.linspace(-10 * s, 10 * s, 401)
        lump = 0.0
    else:
        v = _V
        # P(u < e^v0) ≈ (r x)^r / (r Γ(r)), the leading term of the lower incomplete gamma
        lump = min(1.0, math.exp(r * (math.log(r) + v[0]) - math.log(r) - math.lgamma(r)))
    ld = r * math.log(r) - math.lgamma(r) + r * v - r * np.exp(v)
    w = np.exp(ld - ld.max())
    w[0] *= 0.5
    w[-1] *= 0.5
    w = w / w.sum() * (1.0 - lump)
    return np.exp(v), w, lump


def _log_pois(y, mu):
    with np.errstate(divide="ignore"):
        return np.where(mu > 0, y * np.log(np.where(mu > 0, mu, 1.0)) - mu, np.where(y > 0, -np.inf, 0.0))


def place_loglik(y, B, k, theta: float, alpha: float) -> float:
    """log ∫ Π_t Poisson(y_t; B_t + θ u k_t) dGamma(u; mean 1, var α), dropping Σ log y_t! (a constant).

    Poisson (α -> 0) at u = 1. With B = 0 and one year it is the negative binomial with mean θk and
    Var = μ + αμ² (`calibrate_adu.nb_loglik`, plus log y!).
    """
    y, B, k = (np.asarray(a, dtype=float) for a in (y, B, k))
    if alpha < ALPHA_POISSON:
        return float(np.sum(_log_pois(y, B + theta * k)))
    u, w, lump = _u_grid(alpha)
    ll = _log_pois(y[None, :], B[None, :] + theta * u[:, None] * k[None, :]).sum(axis=1)
    with np.errstate(divide="ignore"):
        terms = np.log(w) + ll
        if lump > 0:
            terms = np.append(terms, math.log(lump) + float(np.sum(_log_pois(y, B))))
    return float(np.logaddexp.reduce(terms))


@dataclass(frozen=True)
class Stack:
    """Every place's years laid end to end, so the likelihood is computed in one array (`starts` marks where
    each place begins)."""

    y: np.ndarray
    B: np.ndarray
    kr: np.ndarray
    age: np.ndarray
    starts: np.ndarray
    n_places: int

    @classmethod
    def of(cls, places: Sequence[Place]) -> Stack:
        if isinstance(places, Stack):
            return places
        lens = [len(p.years) for p in places]
        return cls(
            y=np.concatenate([p.y for p in places]),
            B=np.concatenate([p.B for p in places]),
            kr=np.concatenate([p.kr for p in places]),
            age=np.concatenate([p.age for p in places]),
            starts=np.concatenate([[0], np.cumsum(lens)[:-1]]).astype(int),
            n_places=len(places),
        )


def loglik(places, theta: float, alpha: float, half: float, slope: float = SLOPE) -> float:
    """Σ over places of `place_loglik`, computed on the stacked years."""
    st = Stack.of(places)
    k = st.kr * ramp(st.age, half, slope)
    if alpha < ALPHA_POISSON:
        return float(np.sum(_log_pois(st.y, st.B + theta * k)))
    u, w, lump = _u_grid(alpha)
    ll = np.add.reduceat(
        _log_pois(st.y[None, :], st.B[None, :] + theta * u[:, None] * k[None, :]), st.starts, axis=1
    )  # (grid, places)
    with np.errstate(divide="ignore"):
        terms = np.log(w)[:, None] + ll
        if lump > 0:
            base = np.add.reduceat(_log_pois(st.y, st.B), st.starts)
            terms = np.vstack([terms, math.log(lump) + base[None, :]])
    return float(np.logaddexp.reduce(terms, axis=0).sum())


@dataclass(frozen=True)
class Fit:
    theta: float
    low: float  # 90% profile-likelihood interval
    high: float
    alpha: float
    alpha_low: float
    alpha_high: float
    half: float
    half_low: float
    half_high: float
    loglik: float
    n_places: int
    n_years: int
    profile_half: dict  # half -> max log-likelihood

    @property
    def log_se(self) -> float:
        return (math.log(self.high) - math.log(self.low)) / (2 * Z_95)


def _best_alpha(places, theta, half, tol=1e-4):
    la, ll = _golden_max(lambda la: loglik(places, theta, math.exp(la), half), *LOG_ALPHA, tol=tol)
    return math.exp(la), ll


def _best_at_half(places, half, log_theta=LOG_THETA, tol=1e-4):
    lt, ll = _golden_max(lambda lt: _best_alpha(places, math.exp(lt), half)[1], *log_theta, tol=tol)
    return math.exp(lt), _best_alpha(places, math.exp(lt), half)[0], ll


def _best_theta(places, alpha, half, tol=1e-4) -> float:
    return _golden_max(lambda lt: loglik(places, math.exp(lt), alpha, half), *LOG_THETA, tol=tol)[1]


def profile_theta(places, theta: float, halves=HALF_GRID) -> float:
    """ℓ_p(θ) = max over the half-way grid and α."""
    return max(_best_alpha(places, theta, h)[1] for h in halves)


def _interval(f, x_hat: float, f_hat: float, lo: float, hi: float, iters: int = 25) -> tuple[float, float]:
    """{x : 2(f̂ − f(x)) <= CHI2_90} by bisection on each side of x̂ (returns the bound if never crossed)."""
    cut = f_hat - CHI2_90 / 2

    def side(a, b):  # a inside, b the outer bound
        if f(b) >= cut:
            return b
        for _ in range(iters):
            m = (a + b) / 2
            a, b = (m, b) if f(m) >= cut else (a, m)
        return (a + b) / 2

    return side(x_hat, lo), side(x_hat, hi)


def fit(places: Sequence[Place], halves=HALF_GRID) -> Fit:
    """Maximum likelihood (θ, α, half) with profile-likelihood 90% intervals (D-038)."""
    n_years = int(sum(len(p.years) for p in places))
    places = Stack.of(places)
    by_half = {h: _best_at_half(places, h) for h in halves}
    half = max(by_half, key=lambda h: by_half[h][2])
    theta, alpha, ll = by_half[half]
    lt_lo, lt_hi = _interval(
        lambda lt: profile_theta(places, math.exp(lt), halves), math.log(theta), ll, *LOG_THETA
    )

    def profile_alpha(la):
        return max(_best_theta(places, math.exp(la), h) for h in halves)

    la_lo, la_hi = _interval(
        profile_alpha,
        math.log(alpha),
        ll,
        *LOG_ALPHA,
    )
    inside = [h for h in halves if 2 * (ll - by_half[h][2]) <= CHI2_90]
    return Fit(
        theta=theta,
        low=math.exp(lt_lo),
        high=math.exp(lt_hi),
        alpha=alpha,
        alpha_low=math.exp(la_lo),
        alpha_high=math.exp(la_hi),
        half=float(half),
        half_low=float(min(inside)),
        half_high=float(max(inside)),
        loglik=ll,
        n_places=places.n_places,
        n_years=n_years,
        profile_half={float(h): v[2] for h, v in by_half.items()},
    )


# ---------------------------------------------------------------------------------------------------------
# Prediction and the V4 backtest
# ---------------------------------------------------------------------------------------------------------


def predict_total(place: Place, theta: float, log_se: float, alpha: float, half: float, draws=20_000, seed=0):
    """Predictive draws of the place's total buildings over its years: log θ normal, a new u, Poisson."""
    rng = np.random.default_rng(seed)
    th = np.exp(rng.normal(math.log(theta), log_se, size=draws)) if log_se > 0 else np.full(draws, theta)
    u = rng.gamma(1 / alpha, alpha, size=draws) if alpha >= ALPHA_POISSON else np.ones(draws)
    mu = place.B[None, :] + (th * u)[:, None] * place.k(half)[None, :]
    return rng.poisson(mu).sum(axis=1)


def benchmark_total(place: Place, rate: float, half: float, draws=20_000, seed=0):
    """Poisson draws of the total under a fixed hazard `rate` (0 = no effect), with no place effect."""
    rng = np.random.default_rng(seed)
    mu = place.B + rate * place.k(half)
    return rng.poisson(np.broadcast_to(mu, (draws, len(mu)))).sum(axis=1)


def score(place: Place, draws: np.ndarray) -> dict:
    """P10/P50/P90 of the total, whether the observed total is inside P10-P90, and the error of the median
    per 1,000 eligible parcels a year. By hand: observed 10 over 2 years on 1,000 parcels a year, median 14
    -> error (14 − 10) / 2 / 1,000 × 1,000 = 2.0."""
    p10, p50, p90 = np.percentile(draws, [10, 50, 90])
    obs = float(place.y.sum())
    per = float(np.mean(place.eligible)) * len(place.years) / 1000
    return {
        "observed": obs,
        "p10": float(p10),
        "p50": float(p50),
        "p90": float(p90),
        "covered": bool(p10 <= obs <= p90),
        "error_per_1000": float((p50 - obs) / per),
    }


def loo_backtest(
    places: Sequence[Place],
    outside_rate: float,
    outside_half: float,
    min_year: int = 2015,
    horizon: int = 5,
    halves=HALF_GRID,
    fit_fn=fit,
    hold_growth: bool = False,
) -> pd.DataFrame:
    """V4: for each place with T >= min_year, refit on the other places' years <= T − 1, predict its years
    T … T + horizon − 1, and score the fit against no effect and the outside rate (D-038)."""
    rows = []
    for j, target in enumerate(places):
        if target.T < min_year:
            continue
        t = target.upto(target.T + horizon - 1)
        if hold_growth:  # a true forecast: the baseline stays at its pre-reform level
            t = replace(t, g=np.ones(len(t.g)))
        others = [p.upto(target.T - 1) for i, p in enumerate(places) if i != j]
        others = [p for p in others if len(p.years)]
        row = {"geoid": t.geoid, "name": t.name, "T": t.T, "years": len(t.years), "refit_places": len(others)}
        if len(others) >= 2:
            f = fit_fn(others, halves)
            s = score(t, predict_total(t, f.theta, f.log_se, f.alpha, f.half))
            row |= {"theta": f.theta, "half": f.half} | {f"fit_{k}": v for k, v in s.items()}
        for name, rate in (("none", 0.0), ("outside", outside_rate)):
            s = score(t, benchmark_total(t, rate, outside_half))
            row |= {f"{name}_{k}": v for k, v in s.items() if k != "observed"}
        rows.append(row)
    return pd.DataFrame(rows)


def realized_hazard(places: Sequence[Place]) -> dict:
    """Exposure-weighted mean of (y − B) / (E × dose × F/F_ref) over the observed years, and the
    exposure-weighted distribution of event ages: what the data pin down without the ramp."""
    excess = sum(float((p.y - p.B).sum()) for p in places)
    expo = sum(float(p.kr.sum()) for p in places)
    ages = np.concatenate([p.age for p in places])
    w = np.concatenate([p.kr for p in places])
    order = np.argsort(ages)
    cw = np.cumsum(w[order]) / w.sum()
    pct = {q: float(ages[order][np.searchsorted(cw, q / 100)]) for q in (10, 50, 90)}
    return {
        "mean_hazard": excess / expo if expo else np.nan,
        "age_p10": pct[10],
        "age_p50": pct[50],
        "age_p90": pct[90],
    }
