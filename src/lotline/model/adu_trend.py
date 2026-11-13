"""D-085: Form T, the ADU model with a calendar-year trend, and test D (forecast 2021-2025 from 2016-2020).

    E[y_it | u_i] = θ · exp(β_o z_i) · exp(γ (t − ref)) · u_i · k_it,   u_i ~ Gamma(mean 1, variance α)

The base is Form A (β_o = 0) or Form A′ (D-084). With γ = 0 this is the base exactly. `ref` is 2020
(`config/params/adu_trend.yaml`), so θ is the rate in that year. A `cap` year holds the trend flat after it:
exp(γ (min(t, cap) − ref)). The scenario and test D's "held flat" forecast use it.

**Fit.** Fit 3's procedure (`adu_owner.fit3_term`): on every (m_o, m_x) cell θ, α, γ (and β_o for A′) are
maximized; the cell and the rule shares' intervals are read as fit 3 does; θ's 90% interval is profiled over
the candidate cells and α with β_o and γ held at their estimates; γ (and β_o) get their own profile intervals.
With the trend, a cell's likelihood needs each year's exposure, so the per-cell arrays keep years
(`TrendPrep`), and the maximum over the 3-4 numbers is found by Nelder–Mead (`calibrate_shape.nelder_mead`)
from two starts, not by nested golden sections. With γ held at 0 it reproduces `fit3_term` (tested).

**Test D** (`forecast`, `forecast_log_score`): each place's 2021-2025 counts given its own 2016-2020 counts.
Per global draw, the blank-field combination and the place effect u come from their posterior given the early
counts (Gamma(r + Y_e, r + M_e), r = 1/α), then the late counts are Poisson. The global draws come from the
2016-2020 fit, which already used every early count, so they are not reweighted per place.
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np

from lotline.model import adu_owner as ao
from lotline.model import adu_screen as scr
from lotline.model import calibrate_adu as cal
from lotline.model.calibrate_shape import nelder_mead

GAMMA = (-2.0, 2.0)  # γ's search bounds per year (exp(±2) a year is far outside anything plausible)
BETA = scr.BETA


def trend_factor(years, gamma, ref: int, cap: int | None = None) -> np.ndarray:
    """exp(γ (min(t, cap) − ref)) per year. By hand: years (2019, 2020, 2022), γ log 2, ref 2020 ->
    (0.5, 1, 4); with cap 2020 -> (0.5, 1, 1)."""
    t = np.asarray(years, dtype=float)
    if cap is not None:
        t = np.minimum(t, cap)
    return np.exp(gamma * (t - ref))


def trended(pl: cal.PlaceData, gamma: float, ref: int, cap: int | None = None) -> cal.PlaceData:
    """The place with the trend folded into its exposure: Form T at a fixed γ is the base form on these."""
    return replace(pl, base=pl.base * trend_factor(pl.years, gamma, ref, cap))


@dataclass(frozen=True)
class TrendPrep:
    """One cell's arrays with years kept: per place (rows), combination (padded) and year (padded):
    exposure Kt (n, C, T); s = t − ref (n, T); H0 the head at γ = 0 (n, C); YS = Σ_t y_t s_t; Y the total."""

    geoids: tuple[str, ...]
    states: tuple[str, ...]
    log_w: np.ndarray
    Kt: np.ndarray
    s: np.ndarray
    H0: np.ndarray
    YS: np.ndarray
    Y: np.ndarray

    def at(self, gamma: float) -> scr.Prepared:
        """`adu_screen.Prepared` at γ: K = Σ_t k_t e^{γ s_t}, H = H0 + γ Σ_t y_t s_t."""
        f = np.exp(gamma * self.s)[:, None, :]
        big_k = (self.Kt * f).sum(axis=2)
        head = np.where(np.isfinite(self.H0), self.H0 + gamma * self.YS[:, None], -np.inf)
        return scr.Prepared(self.geoids, self.states, self.log_w, big_k, head, self.Y)


def trend_prep(places: Sequence[cal.PlaceData], cvals: np.ndarray, ref: int, s_of=None) -> TrendPrep:
    """`s_of(pl)` replaces t − ref by another per-year covariate (D-085's rule-age outlook)."""
    base = scr.prepare(places, cvals)
    n, c_max = base.K.shape
    t_max = max(len(pl.years) for pl in places)
    kt = np.zeros((n, c_max, t_max))
    s = np.zeros((n, t_max))
    ys = np.zeros(n)
    for i, pl in enumerate(places):
        k = pl.k(cvals)
        tt = len(pl.years)
        kt[i, : k.shape[0], :tt] = np.where(np.asarray(pl.w)[:, None] > 0, k, 0.0)
        s[i, :tt] = (
            np.asarray(pl.years, dtype=float) - ref if s_of is None else np.asarray(s_of(pl), dtype=float)
        )
        ys[i] = float(np.sum(np.asarray(pl.y, dtype=float) * s[i, :tt]))
    return TrendPrep(base.geoids, base.states, base.log_w, kt, s, base.H, ys, base.Y)


def _ll(tp: TrendPrep, z: np.ndarray, lt: float, la: float, beta: float, gamma: float) -> float:
    p = tp.at(gamma)
    return float(np.sum(scr.place_loglik(p, math.exp(lt) * np.exp(beta * z), math.exp(la))))


@dataclass(frozen=True)
class CellFit:
    lt: float
    la: float
    beta: float
    gamma: float
    loglik: float


def _maximize(tp, z, est_beta: bool, est_gamma: bool, fixed=None, start=None) -> CellFit:
    """Maximize over (log θ, log α, [β], [γ]); `fixed` holds β or γ at a value ({'beta': b} or
    {'gamma': g})."""
    fixed = dict(fixed or {})
    names = (
        ["lt", "la"]
        + (["beta"] if est_beta and "beta" not in fixed else [])
        + (["gamma"] if est_gamma and "gamma" not in fixed else [])
    )
    base = {"lt": math.log(7e-4), "la": math.log(1.5), "beta": 0.0, "gamma": 0.0} | (start or {})

    def unpack(x):
        v = {"beta": fixed.get("beta", 0.0), "gamma": fixed.get("gamma", 0.0)} | dict(
            zip(names, x, strict=True)
        )
        v["la"] = float(np.clip(v["la"], *scr.LOG_ALPHA))
        v["beta"] = float(np.clip(v["beta"], *BETA))
        v["gamma"] = float(np.clip(v["gamma"], *GAMMA))
        return v

    def neg(x):
        v = unpack(x)
        ll = _ll(tp, z, v["lt"], v["la"], v["beta"], v["gamma"])
        return -ll if np.isfinite(ll) else 1e300

    x0 = np.array([base[k] for k in names], dtype=float)
    x, val = nelder_mead(neg, x0, step=0.5, iters=4000, tol=1e-9)
    x, val = nelder_mead(neg, x, step=0.05, iters=4000, tol=1e-11)  # restart: Nelder-Mead can stall
    v = unpack(x)
    return CellFit(v["lt"], v["la"], v["beta"], v["gamma"], -val)


@dataclass(frozen=True)
class Fit3Trend(ao.Fit3Term):
    """A Form T fit: Form A′'s fields (β_o 0 and not estimated on an A base), plus γ and its 90% interval."""

    gamma: float = 0.0
    gamma_low: float = 0.0
    gamma_high: float = 0.0
    gamma_estimated: bool = False
    ref: int = 2020

    @property
    def gamma_se(self) -> float:
        return (self.gamma_high - self.gamma_low) / (2 * ao.Z_90)


def _interval(tp, z, best: CellFit, est_beta, est_gamma, name: str, bounds) -> tuple[float, float]:
    """90% profile interval on β or γ (an edge at the search bound means it is open there)."""

    def gap(v):
        f = _maximize(tp, z, est_beta, est_gamma, fixed={name: v}, start=best.__dict__)
        return 2 * (best.loglik - f.loglik) - cal.CHI2_90

    def edge(far):
        lo, hi = getattr(best, name), far
        if gap(far) < 0:
            return far
        for _ in range(30):
            mid = (lo + hi) / 2
            if gap(mid) < 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    return edge(bounds[0]), edge(bounds[1])


def fit3_trend(
    places: Sequence[cal.PlaceData],
    estimate_beta: bool,
    estimate_gamma: bool = True,
    ref: int = 2020,
    grid=cal.GRID3,
    judgment=(0.5, 0.3),
    ranges=((0.2, 1.0), (0.1, 0.6)),
    log_theta_range=(-14.0, 0.0),
    s_of=None,
) -> Fit3Trend:
    """Form T (or, with `estimate_gamma=False`, its base) by fit 3's procedure; see the module docstring."""
    z = np.array([ao.place_z(pl) for pl in places])
    tps = {(mo, mx): trend_prep(places, cal._cvals(mo, mx), ref, s_of) for mo in grid for mx in grid}
    surface = {key: _maximize(tp, z, estimate_beta, estimate_gamma) for key, tp in tps.items()}
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
    beta, gamma = best.beta, best.gamma
    cands = [tps[(a, b)].at(gamma) for a in mos for b in mxs]
    scale = np.exp(beta * z)

    def prof(lt):
        def f(la, p):
            return float(np.sum(scr.place_loglik(p, math.exp(lt) * scale, math.exp(la))))

        return max(scr._golden(lambda la, p=p: f(la, p), *scr.LOG_ALPHA)[1] for p in cands)

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
    tp = tps[(m_o, m_x)]
    b_lo, b_hi = (
        _interval(tp, z, best, estimate_beta, estimate_gamma, "beta", BETA) if estimate_beta else (0.0, 0.0)
    )
    g_lo, g_hi = (
        _interval(tp, z, best, estimate_beta, estimate_gamma, "gamma", GAMMA)
        if estimate_gamma
        else (0.0, 0.0)
    )
    return Fit3Trend(
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
        n_years=int(sum(len(p.y) for p in places)),
        beta=beta,
        beta_low=b_lo,
        beta_high=b_hi,
        beta_estimated=estimate_beta,
        gamma=gamma,
        gamma_low=g_lo,
        gamma_high=g_hi,
        gamma_estimated=estimate_gamma,
        ref=ref,
    )


def rule_age(pl: cal.PlaceData, cap: float = 10.0) -> np.ndarray:
    """min(age of the oldest rule in force, cap) per year, from `extra["age"]` (years × rules, NaN = not in
    force). By hand: ages ((1, NaN), (2, 0.5), (12, 1)) -> (1, 2, 10)."""
    age = np.asarray((pl.extra or {})["age"], dtype=float)
    return np.minimum(np.nanmax(np.where(np.isnan(age), -np.inf, age), axis=1), cap)


def gamma_draws(fit, n: int, seed: int) -> np.ndarray | None:
    """γ per predictive draw, N(γ̂, se) from its profile interval; None when γ is not estimated."""
    if not getattr(fit, "gamma_estimated", False):
        return None
    return np.random.default_rng([seed, 85]).normal(fit.gamma, fit.gamma_se, size=n)


# ---------------------------------------------------------------------------------------------------------
# Test D: forecast the late years from the early ones
# ---------------------------------------------------------------------------------------------------------


def _early_late(pl_early: cal.PlaceData, pl_late: cal.PlaceData, g):
    """Per draw: the late means at u = 1 per combination (n, C, T_l), the early totals M_e (n, C), and the
    log weight of each combination given the early counts (n, C)."""
    me = g.year_scale(pl_early)  # (n, T_e)
    ml = g.year_scale(pl_late)  # (n, T_l)
    ke, kl = pl_early.k(g.cvals), pl_late.k(g.cvals)  # (C, T)
    ye = np.asarray(pl_early.y, dtype=float)
    lf = float(sum(math.lgamma(v + 1) for v in ye))
    share = np.asarray(pl_early.w, dtype=float) / np.sum(pl_early.w)
    n, c = me.shape[0], ke.shape[0]
    big_me = np.zeros((n, c))
    lw = np.full((n, c), -np.inf)
    from lotline.model import joint_refit as jr

    for j in range(c):
        if share[j] <= 0:
            continue
        mu = me * ke[j][None, :]
        big_me[:, j] = mu.sum(axis=1)
        lw[:, j] = math.log(share[j]) + jr._marginal(ye, mu, g.alpha, lf)
    late = ml[:, None, :] * kl[None, :, :]
    return late, big_me, lw


def forecast(pl_early: cal.PlaceData, pl_late: cal.PlaceData, g, seed: int) -> np.ndarray:
    """Draws × late years: the late counts given the early ones (module docstring). The place's two
    `PlaceData` are the same place cut at the split (`joint_refit.subset_years`), so their combinations
    match."""
    late, big_me, lw = _early_late(pl_early, pl_late, g)
    n = late.shape[0]
    rng = np.random.default_rng([seed, zlib.crc32(pl_early.geoid.encode())])
    w = np.exp(lw - np.max(lw, axis=1, keepdims=True))
    w = w / w.sum(axis=1, keepdims=True)
    combo = (rng.random(n)[:, None] > np.cumsum(w, axis=1)).sum(axis=1)
    combo = np.minimum(combo, w.shape[1] - 1)
    ye = float(np.sum(pl_early.y))
    if g.alpha > 0:
        r = 1.0 / g.alpha
        u = rng.gamma(r + ye, 1.0 / (r + big_me[np.arange(n), combo]))
    else:
        u = np.ones(n)
    mu = u[:, None] * late[np.arange(n), combo]
    return rng.poisson(mu)


def forecast_log_score(pl_early: cal.PlaceData, pl_late: cal.PlaceData, g) -> float:
    """log mean_j P(late counts | early counts, draw j): per draw, Σ_c P(c | early) P(late | early, c), with
    P(late | early, c) = P(early and late | c) / P(early | c) (place effect integrated)."""
    from lotline.model import joint_refit as jr

    late, big_me, lw = _early_late(pl_early, pl_late, g)
    ye = np.asarray(pl_early.y, dtype=float)
    yl = np.asarray(pl_late.y, dtype=float)
    lf_e = float(sum(math.lgamma(v + 1) for v in ye))
    lf_all = lf_e + float(sum(math.lgamma(v + 1) for v in yl))
    me = g.year_scale(pl_early)
    ke = pl_early.k(g.cvals)
    y_all = np.concatenate([ye, yl])
    n, c = big_me.shape
    per = np.full((n, c), -np.inf)
    for j in range(c):
        if not np.isfinite(lw[:, j]).any():
            continue
        mu_all = np.concatenate([me * ke[j][None, :], late[:, j, :]], axis=1)
        joint = jr._marginal(y_all, mu_all, g.alpha, lf_all)
        early = jr._marginal(ye, me * ke[j][None, :], g.alpha, lf_e)
        post = lw[:, j] - jr._logsumexp_rows(lw, axis=1)  # log P(c | early, draw)
        per[:, j] = post + joint - early
    lp = jr._logsumexp_rows(per, axis=1)
    return float(jr._logsumexp_rows(lp[None, :], axis=1)[0] - math.log(n))


def persistence(pl_early: cal.PlaceData, pl_late: cal.PlaceData, n: int, seed: int, prior: float = 0.5):
    """D-085's benchmark: the place's own early rate per eligible lot (× report rate) carried forward.
    λ ~ Gamma(Y_e + prior, L_e), late y_t ~ Poisson(λ m_t), m_t = lots_t × ρ_t. Returns (draws × late years,
    log score of the late counts). By hand: Y_e 2, L_e 4, prior 0, one late year with m 2 and y 0 ->
    P = (4 / 6)^2 = 4/9."""
    me, ml = exposure_lots(pl_early), exposure_lots(pl_late)
    a, b = float(np.sum(pl_early.y)) + prior, float(me.sum())
    rng = np.random.default_rng([seed, zlib.crc32(pl_early.geoid.encode()), 2])
    lam = rng.gamma(a, 1.0 / b, size=n)
    draws = rng.poisson(lam[:, None] * ml[None, :])
    yl = np.asarray(pl_late.y, dtype=float)
    big_y, big_m = float(yl.sum()), float(ml.sum())
    ll = (
        math.lgamma(a + big_y)
        - math.lgamma(a)
        + a * math.log(b)
        - (a + big_y) * math.log(b + big_m)
        + float(np.sum(yl * np.log(np.where(ml > 0, ml, 1.0))))
        - float(sum(math.lgamma(v + 1) for v in yl))
    )
    return draws, ll


def exposure_lots(pl: cal.PlaceData) -> np.ndarray:
    """Eligible lots × report rate per year, from the place's per-year inputs (`extra`)."""
    ex = pl.extra or {}
    lots = np.asarray(ex["parcels"], dtype=float)
    rho = np.asarray(ex.get("report", np.ones_like(lots)), dtype=float)
    return lots * rho


# ---------------------------------------------------------------------------------------------------------
# D-085's rules, fixed before any fit
# ---------------------------------------------------------------------------------------------------------


def choose_extrapolation(gain_continue: float, se: float) -> str:
    """'continue' if continuing γ past the fit years beats holding it flat on test D by more than 2 paired SE,
    else 'flat' (a tie goes to the smaller assumption). By hand: (5, 2) -> continue; (3, 2) -> flat."""
    return "continue" if gain_continue > 2 * se else "flat"


@dataclass(frozen=True)
class Decision:
    trend: bool
    reason: str


def decide(
    gain_d: float,
    se_d: float,
    gamma_low: float,
    gamma_high: float,
    useful_base: dict,
    useful_t: dict,
    tests_base: int,
    tests_t: int,
) -> Decision:
    """D-085: Form T replaces its base only if (1) its test D log score beats the base's by more than 2
    paired SE, (2) γ's 90% interval on the full fit excludes 0, and (3) on the D-075 data-tier test it has at
    least as many useful states at every tier, and passes at least as many of tests A-B.

    By hand: (10, 3, -0.3, -0.1, {0:1,1:1,2:1}, {0:1,1:2,2:1}, 1, 1) -> trend; the same with gain 5 -> no;
    with interval (-0.2, 0.1) -> no; with useful_t tier 2 = 0 -> no; with tests 1 vs 0 -> no."""
    fails = []
    if not gain_d > 2 * se_d:
        fails.append(f"test D gain {gain_d:.1f} is not above 2 SE ({2 * se_d:.1f})")
    if gamma_low <= 0 <= gamma_high:
        fails.append(f"γ's 90% interval ({gamma_low:+.3f}, {gamma_high:+.3f}) holds 0")
    lost = [t for t in useful_base if useful_t.get(t, 0) < useful_base[t]]
    if lost:
        fails.append(f"fewer useful states at tier(s) {lost}")
    if tests_t < tests_base:
        fails.append(f"fewer of tests A-B passed ({tests_t} vs {tests_base})")
    if fails:
        return Decision(False, "; ".join(fails))
    return Decision(
        True,
        f"test D gain {gain_d:.1f} > 2 SE ({2 * se_d:.1f}), γ's interval excludes 0, "
        "no useful state or test lost",
    )
