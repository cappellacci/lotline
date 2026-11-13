"""D-084: Form A′, the ADU model with owner-occupied share as a place term.

    E[y_it | u_i] = θ · exp(β_o z_i) · u_i · k_it,   u_i ~ Gamma(mean 1, variance α),
    z_i = (o_i − center) / scale

k_it is Form A's exposure (`calibrate_adu.PlaceData.k`: parcels × h1 × ρ × max over rules of c_r × coverage)
and o_i the place's owner-occupied share. With β_o = 0 this is Form A (D-048, D-079) exactly.

The fit is fit 3's (D-019, `calibrate_adu.fit3`): θ and α by maximum likelihood on every cell of the
(m_o, m_x) grid, the cell chosen and its interval read as fit 3 does, with β_o profiled on each cell as
well. The likelihood is `calibrate_adu.frailty_loglik`, vectorized over places (`adu_screen.place_loglik`),
which is what makes β_o's extra profile affordable.

θ's interval is profiled over the candidate cells and α with β_o held at its estimate. Because z is centered,
θ is the rate of a place at the center, and θ and β_o are close to independent. β_o has its own profile
interval, and the predictive draws carry both: θ from its interval, β_o ~ N(β̂, se) independently.

The place term rides on each `PlaceData` as `extra["place_z"]` (`with_z`). `joint_refit.globals_a` takes the
β_o draws, and `joint_refit.predict` / `place_loglik` scale each place by exp(β_o z_i) per draw.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np

from lotline.model import adu_screen as scr
from lotline.model import calibrate_adu as cal

Z_KEY = "place_z"
Z_90 = 1.6448536269514722


def owner_z(share: float, center: float, scale: float) -> float:
    """z = (o − center) / scale. By hand: o 0.52, center 0.6727, scale 0.1544 -> −0.989."""
    return (float(share) - center) / scale


def with_z(pl: cal.PlaceData, z: float) -> cal.PlaceData:
    """The place carrying its standardized owner share (read by `place_z` and `joint_refit`)."""
    return replace(pl, extra=dict(pl.extra or {}) | {Z_KEY: float(z)})


def place_z(pl: cal.PlaceData) -> float:
    """The place's z, 0 if it carries none (Form A)."""
    return float((pl.extra or {}).get(Z_KEY, 0.0))


def scaled(pl: cal.PlaceData, beta: float) -> cal.PlaceData:
    """The place with exp(β z) folded into its exposure: Form A′ at a fixed β is Form A on these places.
    By hand: base (100, 200), z 1, β log 2 -> base (200, 400)."""
    return replace(pl, base=pl.base * math.exp(beta * place_z(pl)))


@dataclass(frozen=True)
class Fit3Term(cal.Fit3):
    """A Form A′ fit: fit 3's fields at the chosen cell, plus β_o and its 90% profile interval."""

    beta: float = 0.0
    beta_low: float = 0.0
    beta_high: float = 0.0
    beta_estimated: bool = False

    @property
    def beta_se(self) -> float:
        return (self.beta_high - self.beta_low) / (2 * Z_90)


def _cell(p: scr.Prepared, z: np.ndarray, estimate_beta: bool) -> scr.ScreenFit:
    return scr.fit(p, z, within=False, beta=None if estimate_beta else 0.0)


def _loglik(p: scr.Prepared, z: np.ndarray, lt: float, la: float, beta: float) -> float:
    return float(np.sum(scr.place_loglik(p, math.exp(lt) * np.exp(beta * z), math.exp(la))))


def fit3_term(
    places: Sequence[cal.PlaceData],
    estimate_beta: bool = True,
    grid=cal.GRID3,
    judgment=(0.5, 0.3),
    ranges=((0.2, 1.0), (0.1, 0.6)),
    log_theta_range=(-14.0, 0.0),
) -> Fit3Term:
    """Form A′ (or, with `estimate_beta=False`, Form A) by fit 3's procedure.

    Each (m_o, m_x) cell is profiled over θ, α and β_o. A share whose 90% profile interval is narrower than
    its range is estimated, else held at the judgment value (fit 3's rule). θ's 90% interval is profiled over
    the candidate cells and α at β̂; β_o's is profiled over θ and α at the chosen cell."""
    z = np.array([place_z(pl) for pl in places])
    preps = {(mo, mx): scr.prepare(places, cal._cvals(mo, mx)) for mo in grid for mx in grid}
    surface = {key: _cell(p, z, estimate_beta) for key, p in preps.items()}
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
    beta = best.beta
    lt_hat = math.log(best.theta["all"])
    cands = [preps[(a, b)] for a in mos for b in mxs]

    def prof(lt):
        return max(scr._golden(lambda la, p=p: _loglik(p, z, lt, la, beta), *scr.LOG_ALPHA)[1] for p in cands)

    ll_hat = max(prof(lt_hat), best.loglik)

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

    low, high = edge(log_theta_range[0], lt_hat), edge(log_theta_range[1], lt_hat)
    b_lo, b_hi = scr.beta_interval(preps[(m_o, m_x)], z, best, within=False) if estimate_beta else (0.0, 0.0)
    return Fit3Term(
        theta=math.exp(lt_hat),
        low=math.exp(low),
        high=math.exp(high),
        alpha=best.alpha,
        m_owner=m_o,
        m_other=m_x,
        owner_interval=mo_int,
        other_interval=mx_int,
        owner_estimated=mo_est,
        other_estimated=mx_est,
        loglik=best.loglik,
        n_places=len(places),
        n_years=int(sum(len(p.y) for p in places)),
        beta=beta,
        beta_low=b_lo,
        beta_high=b_hi,
        beta_estimated=estimate_beta,
    )


def beta_draws(fit: Fit3Term, n: int, seed: int) -> np.ndarray | None:
    """β_o per predictive draw, N(β̂, se) from its profile interval; None for Form A (β not estimated)."""
    if not fit.beta_estimated:
        return None
    return np.random.default_rng([seed, 84]).normal(fit.beta, fit.beta_se, size=n)


@dataclass(frozen=True)
class Decision:
    form: str
    reason: str


def decide(
    tier_a: int | None,
    tier_p: int | None,
    log_gain: float,
    log_gain_se: float,
    tests_a: int,
    tests_p: int,
) -> Decision:
    """D-084's decision rule, fixed before any fit: D-079's rule with Form A′ as the challenger, except that
    the log-score comparison also applies when neither form passes any tier.

    A′ replaces A if it passes D-075's claim rule at a lower tier than A, or both pass at the same tier (or
    neither passes) and A′'s tier-1 held-out log score beats A's by more than 2 paired SE; in both cases only
    if A′ passes at least as many of tests A-C (state by state). By hand: (none, none, gain 10, SE 4, tests
    1 vs 1) -> A′; same with gain 7 -> A; (none, none, gain 10, SE 4, tests 1 vs 0) -> A; (2, 1, any, tests
    1 vs 1) -> A′; (1, none, gain 50, SE 1) -> A."""
    tests_ok = tests_p >= tests_a
    lower = tier_p is not None and (tier_a is None or tier_p < tier_a)
    level = tier_a == tier_p  # the same tier, or neither passes
    beats = level and log_gain > 2 * log_gain_se
    gap = f"tier-1 log score gain {log_gain:.1f}, 2 SE {2 * log_gain_se:.1f}"
    if (lower or beats) and tests_ok:
        why = "A′ passes at a lower tier" if lower else f"A′'s held-out log score beats A's by > 2 SE ({gap})"
        return Decision("A′", f"{why}, and A′ passes at least as many of tests A-C ({tests_p} vs {tests_a})")
    if lower or beats:
        return Decision("A", f"A′ scores better but passes fewer of tests A-C ({tests_p} vs {tests_a})")
    return Decision(
        "A", f"A′ does not pass at a lower tier, nor beat A's log score by more than 2 SE ({gap})"
    )


def vintage_share(rows: Mapping[int, float], end_year: int) -> tuple[float | None, int | None]:
    """The latest vintage ending at or before `end_year` that the holdout filter let through: (share, year).
    By hand: {2015: 0.6, 2020: 0.55, 2024: 0.5}, end 2022 -> (0.55, 2020); end 2010 -> (None, None)."""
    ok = [y for y in rows if y <= end_year and rows[y] is not None and math.isfinite(rows[y])]
    if not ok:
        return None, None
    y = max(ok)
    return float(rows[y]), int(y)
