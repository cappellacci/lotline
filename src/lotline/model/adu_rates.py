"""The ADU forecast's shared fit structures, kept apart from the fitting code (modularity plan step 2).

Moved unchanged from `calibrate.adu.calibrate_adu` (D-019's place data, rule-share vector and grid, D-020's
fit record, the interval constants) and `calibrate.adu.calibrate_shape` (`nelder_mead`). The forecast modules
`adu_owner`, `adu_screen` and `adu_types` read them, and the fitting code imports them from here, so the
forecast never imports fitting code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

CHI2_90 = 2.705543  # 90% point of chi-square with 1 degree of freedom
Z_95 = 1.644854  # standard normal 95th percentile


@dataclass
class PlaceData:
    """One place's fit inputs. base[t] = parcels × h_m(θ = 1); for each blank-field combination c (weight
    w[c]) and rule r in force in year t, the rule's type index types[c, t, r] and coverage × ramp cr[t, r]."""

    state: str
    geoid: str
    name: str
    years: np.ndarray
    y: np.ndarray
    base: np.ndarray
    types: np.ndarray
    cr: np.ndarray
    w: np.ndarray
    detached: np.ndarray | None = None  # D-046: (C, T, R) True where the rule forbids detached ADUs
    extra: dict | None = None  # D-047: per-year inputs (rent, value, rate, parcels, report, cov, age)

    @property
    def log_fact(self) -> float:
        return float(sum(math.lgamma(v + 1) for v in self.y))

    def k(self, cvals: np.ndarray, m_d: float = 1.0) -> np.ndarray:
        """Expected counts at θ = 1 and u = 1 for each combination: (C, T) = base × max_r c(type) × cr.

        With `detached` set (D-046), c also carries m_d where the rule forbids detached ADUs; `types` then
        leave that restriction out."""
        c = cvals[self.types]
        if self.detached is not None:
            c = c * np.where(self.detached, m_d, 1.0)
        return self.base[None, :] * (c * self.cr[None, :, :]).max(axis=2)


GRID3 = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)  # m_o and m_x grid, pre-registered


@dataclass(frozen=True)
class Fit3:
    theta: float
    low: float
    high: float
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

    @property
    def log_se(self) -> float:
        return (math.log(self.high) - math.log(self.low)) / (2 * Z_95)


def _cvals(m_owner: float, m_other: float) -> np.ndarray:
    return np.array([0.0, m_owner, m_other, m_owner * m_other, 1.0])


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
