"""Approaches 2 and 3 for the ADU calibration (analysis plan D-047).

Approach 2 keeps D-041's mechanism (θ × parcels × h1 × reporting rate × max over rules of c × coverage ×
ramp) and lets the data set three shape terms on a grid: the ramp's half-life (or no ramp), the equity
elasticity, and a size elasticity. Approach 3 is an empirical benchmark with no Portland transport and no
pro forma: a Poisson-gamma regression on rent, home value, mortgage rate, size, rule restrictions and rule
age. Both use `PlaceData` built by `calibrate_adu.place_data` (its `extra` inputs). NumPy only.
"""

from __future__ import annotations

import dataclasses
import math
import zlib
from dataclasses import dataclass

import numpy as np

from lotline.model import calibrate_adu as cal
from lotline.model import hazard

NO_RAMP = -1.0  # half-life code for "no ramp": ramp = 1 from the first year
RAMP_SLOPE = 0.75  # D-047 held the slope at its then-central value (hazard.PRE_D048_RAMP)
GRID_HALF = (NO_RAMP, 0.5, 1.0, 2.0, 3.5, 6.0)  # pre-registered
GRID_EQUITY = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
GRID_SIZE = (-0.6, -0.4, -0.2, 0.0, 0.2)
SIZE_REF = 10_000.0  # eligible parcels the size term is centred on
SHARES = (1.0, 0.3)  # D-041's fitted rule shares (m_o, m_x), held fixed


# ---------------------------------------------------------------------------------------------------------
# Approach 2: shape terms on the mechanism
# ---------------------------------------------------------------------------------------------------------


def shaped(pl: cal.PlaceData, half: float, equity: float, size: float, p) -> cal.PlaceData:
    """The place with the ramp's half-life `half` (NO_RAMP: ramp 1), the equity elasticity `equity` in place
    of `p`'s, and the size term (mean eligible parcels / SIZE_REF)^size.

    base × (V / V_ref)^(equity − β_e central) × (parcels / SIZE_REF)^size; cr = coverage × ramp(age).
    By hand: V = 2 V_ref, equity 0.75 with central 0.25 -> × 2^0.5 = 1.414; parcels 40,000, size −0.5 ->
    × 0.5.
    """
    ex = pl.extra
    age = ex["age"]
    live = ~np.isnan(age)
    if half == NO_RAMP:
        ramp = np.where(live, 1.0, 0.0)
    else:
        ramp = np.where(live, hazard.ramp(np.nan_to_num(age), half, RAMP_SLOPE), 0.0)
    value = (ex["home_value"] / p["adu_ref_home_value_usd"]) ** (equity - p["adu_equity_elasticity"])
    scale = (float(np.mean(ex["parcels"])) / SIZE_REF) ** size
    return dataclasses.replace(pl, base=pl.base * value * scale, cr=ex["cov"] * ramp)


def _shape_point(args) -> tuple[float, float]:
    places, half, equity, size, p, log_theta_range = args
    sp = [shaped(pl, half, equity, size, p) for pl in places]
    cv = cal._cvals(*SHARES)
    return cal._golden_max(lambda lt: cal._best_at(sp, lt, cv, 1.0)[1], *log_theta_range)


def _shape_cand(args) -> float:
    places, lt, half, equity, size, p = args
    sp = [shaped(pl, half, equity, size, p) for pl in places]
    return cal._best_at(sp, lt, cal._cvals(*SHARES), 1.0)[1]


@dataclass(frozen=True)
class ShapeFit:
    theta: float
    low: float
    high: float
    alpha: float
    half: float
    equity: float
    size: float
    half_interval: tuple[float, float]
    equity_interval: tuple[float, float]
    size_interval: tuple[float, float]
    loglik: float
    n_places: int
    n_years: int

    def as_fit3(self) -> cal.Fit3:
        """The fit in fit 3's form, for `cal.predict_places` on places made with `shaped`."""
        m_o, m_x = SHARES
        return cal.Fit3(self.theta, self.low, self.high, self.alpha, m_o, m_x, (m_o, m_o), (m_x, m_x),
                        False, False, self.loglik, self.n_places, self.n_years)  # fmt: skip

    def apply(self, places: list[cal.PlaceData], p) -> list[cal.PlaceData]:
        return [shaped(pl, self.half, self.equity, self.size, p) for pl in places]


def fit_shape(
    places: list[cal.PlaceData],
    p,
    grids=(GRID_HALF, GRID_EQUITY, GRID_SIZE),
    log_theta_range=(-14.0, 2.0),
    map_fn=map,
) -> ShapeFit:
    """D-047 approach 2: profile the shape grid (θ, α by maximum likelihood at each point), choose the
    maximum, intervals per shape term from its profile (2Δℓ <= 2.706), and θ's interval profiled over the
    points inside the joint 90% region (2Δℓ <= 6.251)."""
    pts = [(a, b, c) for a in grids[0] for b in grids[1] for c in grids[2]]
    res = list(map_fn(_shape_point, [(places, *pt, p, log_theta_range) for pt in pts]))
    lls = {pt: r[1] for pt, r in zip(pts, res, strict=True)}
    lts = {pt: r[0] for pt, r in zip(pts, res, strict=True)}
    top = max(lls.values())
    best = max(lls, key=lls.get)
    ints = []
    for i in range(3):
        prof = {v: max(ll for pt, ll in lls.items() if pt[i] == v) for v in grids[i]}
        inside = [v for v in grids[i] if 2 * (top - prof[v]) <= cal.CHI2_90]
        ints.append((min(inside), max(inside)))
    cands = [pt for pt, ll in lls.items() if 2 * (top - ll) <= cal.CHI2_90_3]
    lt_hat = lts[best]

    def prof(lt):
        return max(map_fn(_shape_cand, [(places, lt, *pt, p) for pt in cands]))

    ll_hat = prof(lt_hat)
    sp = [shaped(pl, *best, p) for pl in places]
    la, _ = cal._best_at(sp, lt_hat, cal._cvals(*SHARES), 1.0)

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
    alpha = math.exp(la) if math.isfinite(la) else 0.0
    n_years = int(sum(len(pl.y) for pl in places))
    return ShapeFit(math.exp(lt_hat), math.exp(low), math.exp(high), alpha, *best, *ints, ll_hat, len(places),
                    n_years)  # fmt: skip


# ---------------------------------------------------------------------------------------------------------
# Approach 3: an empirical benchmark
# ---------------------------------------------------------------------------------------------------------

NAMES = ("intercept", "log rent / 1500", "log value / 300k", "rate - 5", "log parcels / 10k", "restricted",
         "attached only", "log(1 + rule age)")  # fmt: skip
HANDBOOK = 4  # index of 'handbook' in scenarios.adu.TYPES


def design(pl: cal.PlaceData) -> tuple[np.ndarray, np.ndarray]:
    """(X: years × 8 in NAMES order, offset: log(parcels × reporting rate)).

    restricted_t = Σ_c w_c [no rule in force in combination c is Handbook-equivalent]; attached only_t =
    Σ_c w_c [every rule in force forbids detached ADUs]; rule age = years since the oldest rule in force.
    """
    ex = pl.extra
    w = pl.w / pl.w.sum()
    live = ~np.isnan(ex["age"])  # (T, R)
    restricted = np.all((pl.types != HANDBOOK) | ~live[None], axis=2)  # (C, T)
    attached = np.all(ex["no_detached"] | ~live[None], axis=2)
    age = np.nanmax(ex["age"], axis=1)
    x = np.column_stack([
        np.ones(len(pl.y)),
        np.log(ex["rent"] / 1500.0),
        np.log(ex["home_value"] / 300_000.0),
        ex["rate"] - 5.0,
        np.log(ex["parcels"] / SIZE_REF),
        w @ restricted,
        w @ attached,
        np.log1p(np.maximum(age, 0.0)),
    ])  # fmt: skip
    return x, np.log(ex["parcels"] * ex["report"])


@dataclass
class EmpData:
    y: np.ndarray
    x: np.ndarray
    off: np.ndarray
    starts: np.ndarray
    lfact: float

    @classmethod
    def of(cls, places: list[cal.PlaceData]) -> EmpData:
        xs, offs = zip(*(design(pl) for pl in places), strict=True)
        y = np.concatenate([pl.y for pl in places])
        starts = np.cumsum([0] + [len(pl.y) for pl in places[:-1]])
        return cls(y, np.vstack(xs), np.concatenate(offs), starts, float(cal._lgamma(y + 1).sum()))


def emp_loglik(params: np.ndarray, d: EmpData) -> float:
    """Poisson-gamma panel log-likelihood: params = (b0..b7, log α). Per place, as `frailty_loglik_place`:
    Σ_t [y log μ − log y!] + log Γ(Y + r) − log Γ(r) + r log r − (Y + r) log(r + M), r = 1/α, M = Σ μ."""
    beta, alpha = params[:-1], math.exp(params[-1])
    eta = d.off + d.x @ beta
    if np.any(eta > 30):
        return -math.inf
    mu = np.exp(eta)
    y_sum = np.add.reduceat(d.y, d.starts)
    m_sum = np.add.reduceat(mu, d.starts)
    r = 1.0 / alpha
    out = float((d.y * eta).sum()) - d.lfact
    out += float(
        (cal._lgamma(y_sum + r) - math.lgamma(r) + r * math.log(r) - (y_sum + r) * np.log(r + m_sum)).sum()
    )
    return out


def nelder_mead(f, x0, step=0.5, iters: int = 5000, tol: float = 1e-10) -> tuple[np.ndarray, float]:
    """Minimize f from x0 (standard Nelder-Mead: reflection 1, expansion 2, contraction 0.5, shrink 0.5)."""
    n = len(x0)
    pts = [np.asarray(x0, dtype=float)] + [
        np.asarray(x0, dtype=float) + step * np.eye(n)[i] for i in range(n)
    ]
    vals = [f(q) for q in pts]
    for _ in range(iters):
        order = np.argsort(vals)
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        c = np.mean(pts[:-1], axis=0)
        xr = c + (c - pts[-1])
        fr = f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - pts[-1])
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c)
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [pts[0] + 0.5 * (q - pts[0]) for q in pts[1:]]
                vals = [vals[0]] + [f(q) for q in pts[1:]]
    i = int(np.argmin(vals))
    return pts[i], vals[i]


def hessian(f, x, step: float = 1e-3) -> np.ndarray:
    """Central-difference Hessian of f at x."""
    n = len(x)
    h = np.zeros((n, n))
    e = np.eye(n) * step
    for i in range(n):
        for j in range(i, n):
            v = (f(x + e[i] + e[j]) - f(x + e[i] - e[j]) - f(x - e[i] + e[j]) + f(x - e[i] - e[j])) / (
                4 * step**2
            )
            h[i, j] = h[j, i] = v
    return h


@dataclass(frozen=True)
class EmpFit:
    beta: np.ndarray
    alpha: float
    cov: np.ndarray
    loglik: float
    n_places: int


def fit_empirical(places: list[cal.PlaceData], starts: int = 5, seed: int = 47) -> EmpFit:
    """Maximum likelihood by Nelder-Mead, best of `starts` starts (the first at the overall rate, α = 1; the
    rest perturbed, sd 0.5), each run three times from its own end; covariance from the observed information.

    A covariate with no variation in `places` (other than the intercept) is not identified: it is held at 0
    with no variance (D-047 amendment, before the run)."""
    d = EmpData.of(places)
    k = d.x.shape[1]
    free = np.r_[True, d.x[:, 1:].std(axis=0) > 1e-9, True]  # coefficients, then log α
    rate = math.log(d.y.sum() / np.exp(d.off).sum())
    full0 = np.r_[rate, np.zeros(k - 1), 0.0]
    rng = np.random.default_rng(seed)

    def expand(q):
        z = full0 * 0
        z[free] = q
        return z

    def neg(q):
        v = emp_loglik(expand(q), d)
        return -v if math.isfinite(v) else 1e12

    x0 = full0[free]
    best = None
    for s in range(starts):
        q = x0 if s == 0 else x0 + rng.normal(0, 0.5, size=len(x0))
        for _ in range(3):
            q, v = nelder_mead(neg, q)
        if best is None or v < best[1]:
            best = (q, v)
    q, v = best
    info = -hessian(lambda z: emp_loglik(expand(z), d), q)
    w, vecs = np.linalg.eigh((info + info.T) / 2)
    sub = (vecs / np.maximum(w, 1e-8)) @ vecs.T
    cov = np.zeros((k + 1, k + 1))
    cov[np.ix_(free, free)] = (sub + sub.T) / 2
    z = expand(q)
    return EmpFit(z[:-1], math.exp(z[-1]), cov, -v, len(places))


def predict_empirical(places: list[cal.PlaceData], fit: EmpFit, draws: int = 20_000, seed: int = 0) -> dict:
    """Joint predictive counts {geoid: draws × years}: coefficients drawn once per draw from N(β̂, cov) and
    shared by every place; a gamma place effect per place from a stream keyed by (seed, geoid), as
    `cal.predict_places`."""
    rng = np.random.default_rng(seed)
    k = len(fit.beta)
    betas = rng.multivariate_normal(fit.beta, fit.cov[:k, :k], size=draws)
    out = {}
    for pl in places:
        x, off = design(pl)
        r = np.random.default_rng([seed, zlib.crc32(pl.geoid.encode())])
        u = r.gamma(1 / fit.alpha, fit.alpha, size=draws) if fit.alpha > 0 else np.ones(draws)
        eta = np.clip(off[None, :] + betas @ x.T, None, 30)
        out[pl.geoid] = r.poisson(u[:, None] * np.exp(eta))
    return out
