"""D-087: Form A with several place terms (Form A″ = owner share and housing age).

    E[y_it | u_i] = θ · exp(Σ_j β_j z_ij) · u_i · k_it,   u_i ~ Gamma(mean 1, variance α)

k_it is Form A's exposure (`calibrate_adu.PlaceData.k`). Each place carries its full vector of standardized
terms (`with_zv`, `extra["place_zv"]`); a form picks which terms it uses (`use`): Form A uses none, Form A′
(D-084) the owner term, Form A″ (D-087) owner and age. With `use=()` this is Form A; with one term it is
`adu_owner.fit3_term`'s Form A′ (the tests check both).

The fit is fit 3's procedure (`adu_owner.fit3_term`): every (m_o, m_x) cell is profiled over θ, α and the β's,
the cell and the shares' intervals are read as fit 3 reads them, and θ's 90% interval is profiled over the
candidate cells and α with the β's held at their estimates. The β's are found by coordinate ascent (a golden
search on each in turn, the others fixed, until no β moves by more than 1e-3), on the vectorized likelihood
`adu_screen.place_loglik`. No new dependency.

Uncertainty: Σ, the β's covariance, is the inverse of minus the Hessian of the profile log-likelihood (θ and α
maximized) at the chosen cell, by central differences. The predictive draws take β ~ N(β̂, Σ) jointly, so two
correlated terms are not given independent spreads (D-087). The β intervals reported are Wald 90% intervals
from Σ.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np

from lotline.calibrate.adu import calibrate_adu as cal
from lotline.model import adu_screen as scr

ZV_KEY = "place_zv"
Z_90 = 1.6448536269514722
STEP = 0.05  # Hessian step on β (per SD of the factor)
MOVE_TOL = 1e-3
WINDOW = 0.5  # after the first sweep, each golden search looks within ±WINDOW of the current β


def age_share_z(share: float, center: float, scale: float) -> float:
    """z = (a − center) / scale. By hand: a 0.40, center 0.2045, scale 0.1669 -> 1.1714."""
    return (float(share) - center) / scale


def with_zv(pl: cal.PlaceData, zv: Sequence[float]) -> cal.PlaceData:
    """The place carrying its vector of standardized place terms."""
    return replace(pl, extra=dict(pl.extra or {}) | {ZV_KEY: tuple(float(v) for v in zv)})


def place_zv(pl: cal.PlaceData, k: int) -> np.ndarray:
    """The place's term vector (zeros if it carries none)."""
    zv = (pl.extra or {}).get(ZV_KEY)
    return np.zeros(k) if zv is None else np.asarray(zv, dtype=float)[:k]


def offset(pl: cal.PlaceData, betas_full: np.ndarray) -> float:
    """Σ_j β_j z_ij for one place, β over the full term vector (0 for unused terms)."""
    b = np.asarray(betas_full, dtype=float)
    return float(place_zv(pl, len(b)) @ b) if len(b) else 0.0


def scaled(pl: cal.PlaceData, betas_full: np.ndarray) -> cal.PlaceData:
    """The place with exp(Σ β z) folded into its exposure. By hand: base (100, 200), z (1, 2), β (log 2, 0)
    -> base (200, 400)."""
    return replace(pl, base=pl.base * math.exp(offset(pl, betas_full)))


@dataclass(frozen=True)
class Fit3Terms(cal.Fit3):
    """fit 3's fields at the chosen cell, plus the β's of the terms used, their covariance and the total
    number of terms on the places (so draws can be padded with zeros for unused terms)."""

    use: tuple[int, ...] = ()
    n_terms: int = 0
    betas: tuple[float, ...] = ()
    cov: tuple[tuple[float, ...], ...] = ()

    @property
    def betas_full(self) -> np.ndarray:
        b = np.zeros(self.n_terms)
        for j, v in zip(self.use, self.betas, strict=True):
            b[j] = v
        return b

    @property
    def beta_se(self) -> tuple[float, ...]:
        return tuple(math.sqrt(max(self.cov[j][j], 0.0)) for j in range(len(self.use)))

    @property
    def beta_interval(self) -> tuple[tuple[float, float], ...]:
        return tuple((b - Z_90 * s, b + Z_90 * s) for b, s in zip(self.betas, self.beta_se, strict=True))


def _loglik_at(p: scr.Prepared, Z: np.ndarray, b: np.ndarray, within: bool) -> scr.ScreenFit:
    return scr._profile(p, Z @ b if Z.shape[1] else np.zeros(Z.shape[0]), 1.0, within)


def ascent(
    p: scr.Prepared, Z: np.ndarray, start: np.ndarray | None = None, within: bool = False, rounds: int = 12
) -> tuple[np.ndarray, scr.ScreenFit]:
    """Maximum likelihood over the β's (coordinate ascent), θ and α. The first sweep searches each β over
    `adu_screen.BETA` unless a start is given; later sweeps search ±WINDOW around the current value, and
    widen to
    the full range if a search ends on its window's edge."""
    k = Z.shape[1]
    b = np.zeros(k) if start is None else np.asarray(start, dtype=float).copy()
    if k == 0:
        return b, _loglik_at(p, Z, b, within)
    for r in range(rounds):
        old = b.copy()
        for j in range(k):

            def f(x, j=j):
                bb = b.copy()
                bb[j] = x
                return _loglik_at(p, Z, bb, within).loglik

            if r == 0 and start is None:
                lo, hi = scr.BETA
            else:
                lo, hi = max(scr.BETA[0], b[j] - WINDOW), min(scr.BETA[1], b[j] + WINDOW)
            x, _ = scr._golden(f, lo, hi, tol=1e-4)
            on_edge = (x - lo < 1e-3 and lo > scr.BETA[0]) or (hi - x < 1e-3 and hi < scr.BETA[1])
            if on_edge:
                x, _ = scr._golden(f, *scr.BETA, tol=1e-4)
            b[j] = x
        if np.max(np.abs(b - old)) < MOVE_TOL and r > 0:
            break
    return b, _loglik_at(p, Z, b, within)


def hessian_cov(
    p: scr.Prepared, Z: np.ndarray, b: np.ndarray, within: bool = False, h: float = STEP
) -> np.ndarray:
    """Σ = (−H)⁻¹, H the Hessian of the profile log-likelihood in the β's, by central differences."""
    k = len(b)
    if k == 0:
        return np.zeros((0, 0))

    def ll(v):
        return _loglik_at(p, Z, v, within).loglik

    f0 = ll(b)
    H = np.zeros((k, k))
    e = np.eye(k) * h
    for i in range(k):
        H[i, i] = (ll(b + e[i]) - 2 * f0 + ll(b - e[i])) / h**2
        for j in range(i + 1, k):
            H[i, j] = H[j, i] = (
                ll(b + e[i] + e[j]) - ll(b + e[i] - e[j]) - ll(b - e[i] + e[j]) + ll(b - e[i] - e[j])
            ) / (4 * h**2)
    return np.linalg.inv(-H)


def fit3_terms(
    places: Sequence[cal.PlaceData],
    use: tuple[int, ...] = (),
    grid=cal.GRID3,
    judgment=(0.5, 0.3),
    ranges=((0.2, 1.0), (0.1, 0.6)),
    log_theta_range=(-14.0, 0.0),
    cell: tuple[float, float] | None = None,
) -> Fit3Terms:
    """Form A (use=()), A′ (use=(0,)) or A″ (use=(0, 1)) by fit 3's procedure (`adu_owner.fit3_term`).

    `cell`: fit at this (m_o, m_x) only (a sensitivity; shares then reported as not estimated)."""
    n_terms = max((len((pl.extra or {}).get(ZV_KEY, ())) for pl in places), default=0)
    n_terms = max(n_terms, max(use, default=-1) + 1)
    Z = np.array([place_zv(pl, n_terms)[list(use)] for pl in places]).reshape(len(places), len(use))
    cells = [cell] if cell is not None else [(mo, mx) for mo in grid for mx in grid]
    preps = {key: scr.prepare(places, cal._cvals(*key)) for key in cells}
    surface, start = {}, None
    for key in cells:
        b, f = ascent(preps[key], Z, start)
        surface[key] = (b, f)
        start = b  # warm start for the next cell
    lls = {key: f.loglik for key, (_, f) in surface.items()}
    top = max(lls.values())

    def interval(axis: int):
        vals = sorted({key[axis] for key in lls})
        prof = {v: max(ll for key, ll in lls.items() if key[axis] == v) for v in vals}
        inside = [v for v in vals if 2 * (top - prof[v]) <= cal.CHI2_90]
        return max(prof, key=prof.get), (min(inside), max(inside))

    (mo_hat, mo_int), (mx_hat, mx_int) = interval(0), interval(1)
    if cell is not None:
        mo_est = mx_est = False
        m_o, m_x = cell
        mos, mxs = [m_o], [m_x]
    else:
        mo_est = (mo_int[1] - mo_int[0]) < (ranges[0][1] - ranges[0][0])
        mx_est = (mx_int[1] - mx_int[0]) < (ranges[1][1] - ranges[1][0])
        m_o = mo_hat if mo_est else judgment[0]
        m_x = mx_hat if mx_est else judgment[1]
        mos = list(grid) if mo_est else [judgment[0]]
        mxs = list(grid) if mx_est else [judgment[1]]
    b_hat, best = surface[(m_o, m_x)]
    lt_hat = math.log(best.theta["all"])
    zb = Z @ b_hat if len(use) else np.zeros(len(places))
    cands = [preps[(a, c)] for a in mos for c in mxs]

    def prof(lt):
        return max(
            scr._golden(
                lambda la, p=p: float(np.sum(scr.place_loglik(p, math.exp(lt) * np.exp(zb), math.exp(la)))),
                *scr.LOG_ALPHA,
            )[1]
            for p in cands
        )

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
    cov = hessian_cov(preps[(m_o, m_x)], Z, b_hat)
    return Fit3Terms(
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
        use=tuple(use),
        n_terms=n_terms,
        betas=tuple(float(v) for v in b_hat),
        cov=tuple(tuple(float(v) for v in row) for row in cov),
    )


def beta_draws(fit: Fit3Terms, n: int, seed: int) -> np.ndarray | None:
    """β per predictive draw over the full term vector, (n, n_terms): the used terms ~ N(β̂, Σ) jointly, the
    unused ones 0. None for Form A."""
    if not fit.use:
        return None
    rng = np.random.default_rng([seed, 87])
    used = rng.multivariate_normal(np.asarray(fit.betas), np.asarray(fit.cov), size=n, check_valid="ignore")
    out = np.zeros((n, fit.n_terms))
    out[:, list(fit.use)] = used
    return out


def within_state(places: Sequence[cal.PlaceData], fit: Fit3Terms) -> dict:
    """The fit's terms with one θ per state (D-083's main read), at the fit's cell, and with the β's at 0."""
    p = scr.prepare(places, cal._cvals(fit.m_owner, fit.m_other))
    Z = np.array([place_zv(pl, fit.n_terms)[list(fit.use)] for pl in places]).reshape(
        len(places), len(fit.use)
    )
    b, best = ascent(p, Z, np.asarray(fit.betas), within=True)
    null = _loglik_at(p, Z, np.zeros(len(fit.use)), True)
    cov = hessian_cov(p, Z, b, within=True)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    return {
        "betas": b.tolist(),
        "beta_se": se.tolist(),
        "alpha": best.alpha,
        "alpha_betas0": null.alpha,
        "loglik": best.loglik,
        "theta_by_state": best.theta,
    }
