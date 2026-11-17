"""D-095: does the engine's ADU reform ratio match what happened where coded rules changed?

For a place whose rules changed in year t0 (D-079's events, `joint_refit.events`), its total count over the
after years is forecast from its before years only:

- P, no effect: rate ~ Gamma(Y_before + 0.5, E_before) × exp(σ z), count ~ Poisson(rate × E_after), E the base
  exposure (eligible lots summed over the years);
- M, the engine's ratio: the same with exposure base_t × s_t, s_t the Form A rule share in year t, so the
  after mean is P's × (mean share after ÷ mean share before) ("the ratio", r).

A pooled exponent b scales the ratio: the after mean is P's × r^b (b = 1 the engine's ratio, b = 0 no effect).
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from lotline.model import calibrate_adu as cal

PRIOR = 0.5  # the half-count prior on the before rate (D-090's F0, D-091, `own_rate_draws`)
B_GRID = np.round(np.arange(-2.0, 3.0 + 1e-9, 0.05), 2)


def share_path(pl: cal.PlaceData, cvals: np.ndarray) -> np.ndarray:
    """s_t: Form A's rule share per year, k_t ÷ base_t weight-averaged over blank-field combinations (zoned
    coverage included). By hand: one combination with a full rule (share 1) then a partial one at m_x 0.4 ->
    (1, 0.4)."""
    k = pl.k(cvals)  # (C, T)
    w = np.asarray(pl.w, dtype=float) / np.sum(pl.w)
    base = np.asarray(pl.base, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        s = np.where(base[None, :] > 0, k / base[None, :], 0.0)
    return w @ s


@dataclass(frozen=True)
class Event:
    """One rule change: counts and base exposure before and after, and the ratio of mean shares."""

    name: str
    y_before: float
    e_before: float
    y_after: float
    e_after: float
    ratio: float


def event_from(pl: cal.PlaceData, year: int, cvals: np.ndarray) -> Event:
    """The place cut at `year` (the first year under the new rule). The ratio is the base-weighted mean share
    after ÷ before, so E_after × ratio is Σ k_after ÷ (Σ k_before ÷ E_before).

    By hand: base (10, 10, 10, 10), shares (0.5, 0.5, 1, 1), y (1, 2, 3, 4), year index 2 -> Y_b 3, E_b 20,
    Y_a 7, E_a 20, ratio 2."""
    years = list(pl.years)
    i = years.index(year)
    s = share_path(pl, cvals)
    base = np.asarray(pl.base, dtype=float)
    y = np.asarray(pl.y, dtype=float)
    kb, ka = float(np.sum(base[:i] * s[:i])), float(np.sum(base[i:] * s[i:]))
    eb, ea = float(base[:i].sum()), float(base[i:].sum())
    ratio = (ka / ea) / (kb / eb) if kb > 0 else math.inf
    return Event(pl.name, float(y[:i].sum()), eb, float(y[i:].sum()), ea, ratio)


def rate_draws(ev: Event, sigma: float, n: int, seed: int) -> np.ndarray:
    """The no-effect after mean per draw: Gamma(Y_b + 0.5, E_b) × exp(σ z) × E_after. Own stream per place."""
    rng = np.random.default_rng([seed, zlib.crc32(ev.name.encode())])
    rate = rng.gamma(ev.y_before + PRIOR, 1.0 / ev.e_before, size=n)
    drift = np.exp(sigma * rng.standard_normal(n)) if sigma > 0 else np.ones(n)
    return rate * drift * ev.e_after


def log_score(y: float, means: np.ndarray) -> float:
    """log mean_j Poisson(y; μ_j). By hand: y 2, μ (1, 1) -> log(e^-1 / 2)."""
    mu = np.maximum(np.asarray(means, dtype=float), 1e-300)
    lp = y * np.log(mu) - mu - math.lgamma(y + 1)
    m = lp.max()
    return float(m + math.log(np.mean(np.exp(lp - m))))


def b_profile(events: Sequence[Event], means: Sequence[np.ndarray], grid=B_GRID) -> np.ndarray:
    """Σ_e log score of y_after,e under means × ratio_e^b, for each b in `grid`. Events with an infinite or
    zero ratio are left out (b is not defined for them)."""
    out = np.zeros(len(grid))
    for ev, mu in zip(events, means, strict=True):
        if not (0 < ev.ratio < math.inf):
            continue
        for j, b in enumerate(grid):
            out[j] += log_score(ev.y_after, mu * ev.ratio**b)
    return out


def b_interval(profile: np.ndarray, grid=B_GRID) -> tuple[float, float, float]:
    """(b̂, low, high): the grid maximum and the 90% profile interval (2 × drop ≤ χ²₁ 90%); an edge at the grid
    end means the interval is open there."""
    j = int(np.argmax(profile))
    inside = grid[2 * (profile[j] - profile) <= cal.CHI2_90]
    return float(grid[j]), float(inside.min()), float(inside.max())


def reading(gain: float, se: float, b_low: float, b_high: float) -> str:
    """D-095's reading rule. By hand: (5, 1, 0.5, 1.5) -> supported; (-3, 1, 0, 2) -> contradicted;
    (1, 1, -0.5, 2) -> not shown; (1, 1, 1.2, 2) -> contradicted (excludes 1)."""
    if gain < -2 * se or not (b_low <= 1.0 <= b_high):
        return "contradicted"
    if gain > 2 * se and b_low > 0.0:
        return "supported"
    return "not shown either way"
