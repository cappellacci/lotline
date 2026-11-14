"""D-090: a within-state ADU forecast test. Fit on each state's own years to 2019, forecast 2021-2025.

D-090 fixed, before any run, the split, the places scored, three forecasters and the rule that reads them:

- **The split.** Fit on 2016-2019 (`FIT_LAST`). 2020 is the lead year (D-061): it is not scored. The window is
  2021-2025 (`WINDOW_YEARS`). In this draw code the years are independent given the place effect and the
  shared draws (no stock of lots is used up), so the lead year changes no window draw; it is only left out.
- **Places with history** (`has_history`): at least 2 fit years and at least 1 window year. Places with no fit
  year and at least 1 window year are "new places in a known state". A place with exactly 1 fit year is
  neither; it stays in the fit and is reported as "thin history", not scored by the rule.
- **F0, persistence** (`f0_*`): each place's own 2016-2019 ADUs per eligible lot, rate ~ Gamma(Y + 0.5, E),
  Y the counted ADUs and E the eligible lot-years; each window year is Poisson(rate × lots). No rules, no
  state term.
- **F1** (`fit_within`, `state_globals`, `predict_own`, `own_log_score`): Form A's mechanism with α, m_o and
  m_x fitted jointly on every state's fit years and one θ per state. Each place's u is updated on its own fit
  years by the gamma-Poisson posterior (D-052), jointly with its blank-field combination, draw by draw.
- **F2**: F1 with housing age as a place term (`fit_within(use=(0,))` on places carrying z_age).
- **Sensitivity** (`fit_trend`, `with_trend`): F1 with a log-linear calendar trend per state, fitted on the
  fit years with α and the cell held at F1's. Reported, not used to choose.
- **The rule** (`decide`): own history is enough if F1 is useful in at least 3 of the 4 scored states; the
  mechanism earns its place if F1's summed per-place log score beats F0's by more than 2 paired SE; F2
  replaces F1 only if it beats F1 by more than 2 paired SE and is useful in at least as many states.

The fitter reuses D-087's (`adu_terms.ascent` with `within=True`, `adu_screen`'s vectorized likelihood) and
reads the (m_o, m_x) cell as fit 3 does. Each θ_s's 90% interval is profiled over α and the other states' θ
at the chosen cell, with any β held at its estimate. Pure functions; the run is
`scripts/dev/adu_time_split.py`.
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np

from lotline.model import adu_screen as scr
from lotline.model import adu_terms as at
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr

FIT_FIRST, FIT_LAST, LEAD_YEAR = 2016, 2019, 2020
WINDOW_YEARS = range(2021, 2026)
MIN_FIT_YEARS, MIN_WINDOW_YEARS = 2, 1
USEFUL_STATES = 3  # rule 1: useful in at least 3 of the 4 scored states (Ben confirmed 2026-11-14)
F0_PRIOR_SHAPE = 0.5  # F0: rate ~ Gamma(Y + 0.5, E)

# ---------------------------------------------------------------------------------------------------------
# The split
# ---------------------------------------------------------------------------------------------------------


def fit_years(last: int = FIT_LAST) -> range:
    return range(FIT_FIRST, last + 1)


def split(
    pl: cal.PlaceData, last: int = FIT_LAST, window=WINDOW_YEARS
) -> tuple[cal.PlaceData | None, cal.PlaceData | None]:
    """(the place on its fit years, the place on its window years); None where it has none. The lead year
    is in neither. By hand: years 2016-2025 -> fit 2016-2019 (4 years), window 2021-2025 (5 years)."""
    return jr.subset_years(pl, fit_years(last)), jr.subset_years(pl, window)


def place_class(pl: cal.PlaceData, last: int = FIT_LAST, window=WINDOW_YEARS) -> str:
    """'history' (at least 2 fit years and 1 window year), 'new' (no fit year, at least 1 window year),
    'thin' (1 fit year and at least 1 window year) or 'none' (no window year)."""
    f, w = split(pl, last, window)
    nf = 0 if f is None else len(f.years)
    nw = 0 if w is None else len(w.years)
    if nw < MIN_WINDOW_YEARS:
        return "none"
    if nf >= MIN_FIT_YEARS:
        return "history"
    return "new" if nf == 0 else "thin"


def has_history(pl: cal.PlaceData, last: int = FIT_LAST, window=WINDOW_YEARS) -> bool:
    return place_class(pl, last, window) == "history"


def rule_change_years(pl: cal.PlaceData, first: int = LEAD_YEAR, window=WINDOW_YEARS) -> list[int]:
    """Years in the window whose rules (any combination's types, or coverage) differ from the year before,
    counting from the lead year. By hand: types (owner, owner, by right) over 2020-2022 -> [2022]."""
    keep = (pl.years >= first) & (pl.years <= max(window))
    yrs = pl.years[keep]
    types, cr = pl.types[:, keep, :], pl.cr[keep]
    out = []
    for t in range(1, len(yrs)):
        if not (np.array_equal(types[:, t, :], types[:, t - 1, :]) and np.allclose(cr[t], cr[t - 1])):
            out.append(int(yrs[t]))
    return out


# ---------------------------------------------------------------------------------------------------------
# F0: persistence
# ---------------------------------------------------------------------------------------------------------


def lots(pl: cal.PlaceData) -> np.ndarray:
    return np.asarray((pl.extra or {})["parcels"], dtype=float)


def f0_posterior(fit_pl: cal.PlaceData, shape0: float = F0_PRIOR_SHAPE) -> tuple[float, float]:
    """(shape, rate) of F0's rate per eligible lot: Gamma(Y + 0.5, E). By hand: y (2, 3), lots (100, 100)
    -> (5.5, 200)."""
    return float(np.sum(fit_pl.y)) + shape0, float(np.sum(lots(fit_pl)))


def f0_draws(fit_pl: cal.PlaceData, win_pl: cal.PlaceData, n: int, seed: int) -> np.ndarray:
    """F0's predictive counts (n draws × window years), from a stream keyed by (seed, geoid)."""
    a, b = f0_posterior(fit_pl)
    rng = np.random.default_rng([seed, zlib.crc32(fit_pl.geoid.encode()), 90])
    rate = rng.gamma(a, 1.0 / b, size=n)
    return rng.poisson(rate[:, None] * lots(win_pl)[None, :])


def f0_log_score(fit_pl: cal.PlaceData, win_pl: cal.PlaceData) -> float:
    """log P(window counts | F0), the gamma rate integrated (exact):
    Σ y_t log e_t − Σ log y_t! + a log b − log Γ(a) + log Γ(a + Y) − (a + Y) log(b + Σ e_t).
    By hand: a 1, b 1 (fit y 0.5, lots 1), one window year y 0, e 1 -> log(1/2)."""
    a, b = f0_posterior(fit_pl)
    y, e = np.asarray(win_pl.y, dtype=float), lots(win_pl)
    big_y, big_e = float(y.sum()), float(e.sum())
    head = float(np.sum(np.where(y > 0, y * np.log(np.where(e > 0, e, 1.0)), 0.0)))
    head -= float(sum(math.lgamma(v + 1) for v in y))
    return (
        head + a * math.log(b) - math.lgamma(a) + math.lgamma(a + big_y) - (a + big_y) * math.log(b + big_e)
    )


# ---------------------------------------------------------------------------------------------------------
# F1 and F2: Form A with one θ per state
# ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StateFit:
    """The within-state fit at the chosen (m_o, m_x) cell. `use`/`betas`/`cov` as `adu_terms.Fit3Terms`."""

    theta: Mapping[str, float]
    low: Mapping[str, float]
    high: Mapping[str, float]
    alpha: float
    m_owner: float
    m_other: float
    owner_interval: tuple[float, float]
    other_interval: tuple[float, float]
    owner_estimated: bool
    other_estimated: bool
    loglik: float
    n_places: int
    n_years: int
    use: tuple[int, ...] = ()
    n_terms: int = 0
    betas: tuple[float, ...] = ()
    cov: tuple[tuple[float, ...], ...] = ()

    def log_se(self, state: str) -> float:
        return (math.log(self.high[state]) - math.log(self.low[state])) / (2 * cal.Z_95)

    @property
    def betas_full(self) -> np.ndarray:
        b = np.zeros(self.n_terms)
        for j, v in zip(self.use, self.betas, strict=True):
            b[j] = v
        return b

    @property
    def beta_se(self) -> tuple[float, ...]:
        return tuple(math.sqrt(max(self.cov[j][j], 0.0)) for j in range(len(self.use)))


def read_shares(
    lls: Mapping[tuple[float, float], float], judgment=(0.5, 0.3), ranges=((0.2, 1.0), (0.1, 0.6))
) -> tuple[tuple[float, float], tuple[tuple[float, float], tuple[float, float]], tuple[bool, bool]]:
    """Fit 3's reading of the (m_o, m_x) surface: each share's profile and 90% interval; a share whose
    interval is narrower than its judgment range is estimated (its profile maximum), else it takes its
    judgment value.
    Returns ((m_o, m_x), (m_o interval, m_x interval), (m_o estimated, m_x estimated))."""
    top = max(lls.values())

    def interval(axis: int):
        vals = sorted({key[axis] for key in lls})
        prof = {v: max(ll for key, ll in lls.items() if key[axis] == v) for v in vals}
        inside = [v for v in vals if 2 * (top - prof[v]) <= cal.CHI2_90]
        return max(prof, key=prof.get), (min(inside), max(inside))

    (mo_hat, mo_int), (mx_hat, mx_int) = interval(0), interval(1)
    mo_est = (mo_int[1] - mo_int[0]) < (ranges[0][1] - ranges[0][0])
    mx_est = (mx_int[1] - mx_int[0]) < (ranges[1][1] - ranges[1][0])
    m = (mo_hat if mo_est else judgment[0], mx_hat if mx_est else judgment[1])
    return m, (mo_int, mx_int), (mo_est, mx_est)


def _state_max(p: scr.Prepared, zb: np.ndarray, alpha: float) -> float:
    return scr._golden(lambda lt: float(np.sum(scr.place_loglik(p, math.exp(lt) * np.exp(zb), alpha))),
                       *scr.LOG_THETA)[1]  # fmt: skip


def theta_interval(
    p: scr.Prepared, zb: np.ndarray, state: str, lt_hat: float, ll_hat: float
) -> tuple[float, float]:
    """θ_s's 90% profile interval: for each log θ_s, α and the other states' θ are maximized (zb, the place
    terms' offsets, held). Returns (low, high)."""
    st = np.array(p.states)
    mine = st == state
    sub = p.subset(mine)
    others = [(p.subset(st == s), zb[st == s]) for s in sorted(set(p.states) - {state})]

    def prof(lt):
        def at_alpha(la):
            a = math.exp(la)
            own = float(np.sum(scr.place_loglik(sub, math.exp(lt) * np.exp(zb[mine]), a)))
            return own + sum(_state_max(q, z, a) for q, z in others)

        return scr._golden(at_alpha, *scr.LOG_ALPHA, tol=1e-4)[1]

    def edge(far):
        lo, hi = lt_hat, far
        if 2 * (ll_hat - prof(far)) - cal.CHI2_90 < 0:
            return far
        for _ in range(30):
            mid = (lo + hi) / 2
            if 2 * (ll_hat - prof(mid)) - cal.CHI2_90 < 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    return math.exp(edge(scr.LOG_THETA[0])), math.exp(edge(lt_hat + 8.0))


def _cell_fit(args):
    places, Z, key = args
    return key, at.ascent(scr.prepare(places, cal._cvals(*key)), Z, None, within=True)


def fit_within(
    places: Sequence[cal.PlaceData],
    use: tuple[int, ...] = (),
    grid=cal.GRID3,
    cell: tuple[float, float] | None = None,
    intervals: bool = True,
    mapper=map,
) -> StateFit:
    """Form A (use=()) or Form A with place terms, one θ per state, every (m_o, m_x) cell profiled over the
    θ_s, α and the β's (`adu_terms.ascent(within=True)`, each cell from β = 0); the cell is read by
    `read_shares`. `mapper` (e.g. a process pool's `map`) runs the cells; the result does not depend on it."""
    n_terms = max((len((pl.extra or {}).get(at.ZV_KEY, ())) for pl in places), default=0)
    n_terms = max(n_terms, max(use, default=-1) + 1)
    Z = np.array([at.place_zv(pl, n_terms)[list(use)] for pl in places]).reshape(len(places), len(use))
    cells = [cell] if cell is not None else [(mo, mx) for mo in grid for mx in grid]
    surface = dict(mapper(_cell_fit, [(places, Z, key) for key in cells]))
    if cell is not None:
        (m_o, m_x), ints, est = cell, ((cell[0],) * 2, (cell[1],) * 2), (False, False)
    else:
        (m_o, m_x), ints, est = read_shares({k: f.loglik for k, (_, f) in surface.items()})
    b_hat, best = surface[(m_o, m_x)]
    zb = Z @ b_hat if len(use) else np.zeros(len(places))
    p = scr.prepare(places, cal._cvals(m_o, m_x))
    low, high = {}, {}
    for s, th in best.theta.items():
        if intervals:
            low[s], high[s] = theta_interval(p, zb, s, math.log(th), best.loglik)
        else:
            low[s], high[s] = th, th
    cov = at.hessian_cov(p, Z, b_hat, within=True)
    return StateFit(
        theta=dict(best.theta),
        low=low,
        high=high,
        alpha=best.alpha,
        m_owner=m_o,
        m_other=m_x,
        owner_interval=tuple(ints[0]),
        other_interval=tuple(ints[1]),
        owner_estimated=bool(est[0]),
        other_estimated=bool(est[1]),
        loglik=best.loglik,
        n_places=len(places),
        n_years=int(sum(len(pl.y) for pl in places)),
        use=tuple(use),
        n_terms=n_terms,
        betas=tuple(float(v) for v in b_hat),
        cov=tuple(tuple(float(v) for v in row) for row in cov),
    )


def state_globals(fit: StateFit, state: str, n: int, seed: int) -> jr.GlobalsA:
    """The state's shared draws: θ_s ~ lognormal from its 90% interval; β ~ N(β̂, Σ) if the fit uses terms."""
    rng = np.random.default_rng([seed, zlib.crc32(state.encode())])
    sd = fit.log_se(state)
    theta = (
        np.exp(rng.normal(math.log(fit.theta[state]), sd, size=n)) if sd > 0 else np.full(n, fit.theta[state])
    )
    beta = None
    if fit.use:
        used = np.random.default_rng([seed, 87]).multivariate_normal(
            np.asarray(fit.betas), np.asarray(fit.cov), size=n, check_valid="ignore"
        )
        beta = np.zeros((n, fit.n_terms))
        beta[:, list(fit.use)] = used
    return jr.GlobalsA(theta, fit.alpha, cal._cvals(fit.m_owner, fit.m_other), beta)


def _combo_loglik(y: np.ndarray, mu: np.ndarray, alpha: float) -> np.ndarray:
    """log P(y | mu) per draw (rows of mu), u integrated (`joint_refit._marginal`)."""
    return jr._marginal(y, mu, alpha, float(sum(math.lgamma(v + 1) for v in y)))


def predict_own(fit_pl: cal.PlaceData, win_pl: cal.PlaceData, g: jr.GlobalsA, seed: int) -> np.ndarray:
    """F1's predictive counts (draws × window years) for a place with history. In each draw j the place's
    blank-field combination c is drawn with probability ∝ w_c P(fit counts | scale_j, c), then
    u ~ Gamma(r + Y, rate r + scale_j K_c) (r = 1/α, Y the fit counts, K_c the fit exposure; D-052), then each
    window year ~ Poisson(scale_j u k_ct). α = 0 gives u = 1."""
    n = len(g.scale)
    rng = np.random.default_rng([seed, zlib.crc32(fit_pl.geoid.encode()), 91])
    scale = g.place_scale(fit_pl)
    kf, kw = fit_pl.k(g.cvals), win_pl.k(g.cvals)  # (C, T_fit), (C, T_win)
    y = np.asarray(fit_pl.y, dtype=float)
    live = np.flatnonzero(fit_pl.w > 0)
    lw = np.stack(
        [math.log(fit_pl.w[c] / fit_pl.w.sum()) + _combo_loglik(y, scale[:, None] * kf[c][None, :], g.alpha)
         for c in live], axis=1,
    )  # fmt: skip
    top = lw.max(axis=1, keepdims=True)
    pr = np.exp(lw - np.where(np.isfinite(top), top, 0.0))
    pr = pr / pr.sum(axis=1, keepdims=True)
    combo = live[(pr.cumsum(axis=1) < rng.random(n)[:, None]).sum(axis=1).clip(max=len(live) - 1)]
    big_k = kf.sum(axis=1)[combo]
    if g.alpha > 0:
        r = 1.0 / g.alpha
        u = rng.gamma(r + y.sum(), 1.0 / (r + scale * big_k))
    else:
        u = np.ones(n)
    return rng.poisson((scale * u)[:, None] * kw[combo])


def _whole(fit_pl: cal.PlaceData, win_pl: cal.PlaceData) -> cal.PlaceData:
    """Concatenate a place's fit and window parts (same combinations and rules axis)."""

    def cat(a, b):
        if not isinstance(a, np.ndarray):
            return a
        return np.concatenate([a, b], axis=1 if a.ndim == 3 else 0)

    ex = {k: cat(v, (win_pl.extra or {})[k]) for k, v in (fit_pl.extra or {}).items()}
    return replace(
        fit_pl,
        years=np.concatenate([fit_pl.years, win_pl.years]),
        y=np.concatenate([fit_pl.y, win_pl.y]),
        base=np.concatenate([fit_pl.base, win_pl.base]),
        types=np.concatenate([fit_pl.types, win_pl.types], axis=1),
        cr=np.concatenate([fit_pl.cr, win_pl.cr]),
        detached=None
        if fit_pl.detached is None
        else np.concatenate([fit_pl.detached, win_pl.detached], axis=1),
        extra=ex,
    )


def own_log_score(fit_pl: cal.PlaceData, win_pl: cal.PlaceData, g: jr.GlobalsA) -> float:
    """D-049's held-out log score of the window counts given the place's own fit counts:
    log mean_j P(window | fit counts, draw j) = log mean_j exp(ℓ_j(fit + window) − ℓ_j(fit)), each ℓ with u
    integrated and combinations mixed (`joint_refit.place_loglik`)."""
    both = jr.place_loglik(_whole(fit_pl, win_pl), g)
    alone = jr.place_loglik(fit_pl, g)
    d = np.where(np.isfinite(alone), both - alone, -np.inf)
    return float(jr._logsumexp_rows(d[None, :], axis=1)[0] - math.log(len(d)))


# ---------------------------------------------------------------------------------------------------------
# Sensitivity: a log-linear calendar trend per state
# ---------------------------------------------------------------------------------------------------------


def with_trend(pl: cal.PlaceData, gamma: float, origin: int = FIT_LAST) -> cal.PlaceData:
    """The place with exp(γ (year − origin)) folded into its exposure. By hand: years (2018, 2019, 2020),
    base 1, γ log 2 -> base (0.5, 1, 2)."""
    return replace(pl, base=pl.base * np.exp(gamma * (pl.years - origin)))


TREND = (-1.5, 1.5)  # search range for γ (per year, log scale)


def fit_trend(
    places: Sequence[cal.PlaceData], fit: StateFit, state: str, origin: int = FIT_LAST
) -> tuple[float, float]:
    """(γ_s, θ_s at γ_s): the state's trend, maximizing over (γ, θ_s) with α and the cell held at F1's."""
    mine = [pl for pl in places if pl.state == state]
    cv = cal._cvals(fit.m_owner, fit.m_other)

    def prep(gamma):
        return scr.prepare([with_trend(pl, gamma, origin) for pl in mine], cv)

    gamma = scr._golden(lambda g: _state_max(prep(g), np.zeros(len(mine)), fit.alpha), *TREND, tol=1e-4)[0]
    p = prep(gamma)
    ones = np.ones(len(mine))
    lt = scr._golden(
        lambda lt: float(np.sum(scr.place_loglik(p, math.exp(lt) * ones, fit.alpha))), *scr.LOG_THETA
    )[0]
    return gamma, math.exp(lt)


# ---------------------------------------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    own_history_enough: bool
    useful_states_f1: int
    mechanism_beats_persistence: bool
    f2_replaces_f1: bool
    reasons: tuple[str, ...]


def decide(
    useful_f1: Mapping[str, bool],
    useful_f2: Mapping[str, bool],
    gain_f1_over_f0: float,
    se_f1_over_f0: float,
    gain_f2_over_f1: float,
    se_f2_over_f1: float,
    min_states: int = USEFUL_STATES,
) -> Verdict:
    """D-090's three rules, fixed before any run.

    1. Own history is enough if F1 is useful in at least `min_states` scored states.
    2. The mechanism earns its place if F1's summed per-place log score beats F0's by more than 2 paired SE.
    3. F2 replaces F1 if it beats F1 by more than 2 paired SE and is useful in at least as many states.

    By hand: useful F1 (T, T, T, F), F2 (T, T, T, T), F1-F0 gain 10 SE 4, F2-F1 gain 5 SE 3 ->
    (True, 3, True, False): 5 is not more than 6."""
    n1 = int(sum(bool(v) for v in useful_f1.values()))
    n2 = int(sum(bool(v) for v in useful_f2.values()))
    r1 = n1 >= min_states
    r2 = gain_f1_over_f0 > 2 * se_f1_over_f0
    r3 = gain_f2_over_f1 > 2 * se_f2_over_f1 and n2 >= n1
    reasons = (
        f"rule 1: F1 useful in {n1} of {len(useful_f1)} states (bar {min_states}) -> "
        + ("own history is enough" if r1 else "own history is not enough to forecast within ×2"),
        f"rule 2: F1 − F0 log score {gain_f1_over_f0:+.2f}, bar 2 SE = {2 * se_f1_over_f0:.2f} -> "
        + ("the mechanism beats persistence" if r2 else "F1 forecasts no better than persistence"),
        f"rule 3: F2 − F1 log score {gain_f2_over_f1:+.2f}, bar {2 * se_f2_over_f1:.2f}; "
        f"useful states F2 {n2} vs F1 {n1} -> " + ("F2 replaces F1" if r3 else "F1 stays"),
    )
    return Verdict(r1, n1, r2, r3, reasons)
