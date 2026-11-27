"""Missing-middle hazard fit, inputs (D-038, D-058): one `Place` per post-reform place, its baseline
and growth index, the dispersion test that picks the long baseline, and `place_inputs` that builds it.

Part of `calibrate_mm`, split by method step (modularity step 3); `calibrate_mm` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

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
    z: float = 0.0  # D-042: centred log builder capacity (0 = no modifier)
    unstable: bool = False  # D-058: the pre-reform pace failed the dispersion test (baseline window widened)
    kappa: float = 0.0  # D-092 deviation 2026-11-15: variance of the place-level rate multiplier w (0 = none)
    phi: float = 0.0  # D-092 deviation (b): per-year NB overdispersion, Var = μ + φμ² (0 = Poisson)

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


LONG_YEARS = 6  # D-058: the stability test's window and the replacement baseline's


DISPERSION_P = 0.05  # D-058: unstable if the dispersion test's p-value is below this


ZERO_FLOOR = 0.5  # D-058: buildings spread over a baseline window that had none


def _gamma_q(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x): the series for P below x = a + 1, else Lentz's continued
    fraction for Q (standard library only)."""
    if x <= 0:
        return 1.0
    lg = math.lgamma(a)
    if x < a + 1:
        term = total = 1.0 / a
        n = a
        for _ in range(500):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return max(0.0, 1.0 - total * math.exp(-x + a * math.log(x) - lg))
    tiny = 1e-300
    b = x + 1 - a
    c, d = 1 / tiny, 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        h *= d * c
        if abs(d * c - 1) < 1e-15:
            break
    return min(1.0, math.exp(-x + a * math.log(x) - lg) * h)


def chi2_sf(x: float, df: int) -> float:
    """P(χ²(df) >= x). By hand: 3.841 on 1 df, 5.991 on 2 and 11.070 on 5 each give 0.05; x = 0 gives 1."""
    return _gamma_q(df / 2, x / 2)


def dispersion_test(counts: Sequence[float], p_cut: float = DISPERSION_P) -> dict:
    """Poisson index-of-dispersion test (D-058): D = Σ (y − ȳ)² / ȳ ~ χ²(n − 1) for a stable pace.
    Not testable (stable) with fewer than 3 years or ȳ = 0.

    By hand: (10, 10, 10) -> D 0, p 1, stable; (0, 0, 30) -> ȳ 10, D = (100 + 100 + 400) / 10 = 60 on 2 df,
    p = e^-30, unstable; (4, 6) -> not testable."""
    y = np.asarray(counts, float)
    if len(y) < 3 or not y.mean() > 0:
        return {"n": len(y), "stat": np.nan, "p": np.nan, "testable": False, "unstable": False}
    stat = float(((y - y.mean()) ** 2).sum() / y.mean())
    p = chi2_sf(stat, len(y) - 1)
    return {"n": len(y), "stat": stat, "p": p, "testable": True, "unstable": bool(p < p_cut)}


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
    series_by_place: Mapping[str, Mapping[int, float]] | None = None,
    baseline_rule: str = "fixed",
    zero_floor: bool = False,
) -> list[Place]:
    """`Place` per geoid from the D-024 panel (`estimate_mm.build_panel(...).data`).

    growth: 'own' (units_1 + units_5p), 'own_5p' (units_5p), 'state' (the same state's uncoded places' 2-4
    unit buildings, summed by year), 'given' (`series_by_place[geoid]`, D-042's comparison index) or
    'none'. shift: move T that many years earlier and keep only years before the real T (the placebo-date
    check). Places with no post-reform year or no pre-reform year with
    data are left out.

    D-058: baseline_rule 'fixed' (the `baseline_years` window), 'stability' (the six-year window T − 6 … T − 1
    when `dispersion_test` flags the place's counts there), or 'long' (six years always); the growth index's
    reference moves with the window. zero_floor: a baseline with no outcome becomes 0.5 / n_pre.
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
        long_pre = list(range(T - LONG_YEARS, T))
        long_vals = [float(yb[s]) for s in long_pre if s in yb.index and pd.notna(yb[s])]
        flagged = baseline_rule == "stability" and dispersion_test(long_vals)["unstable"]
        if baseline_rule == "long" or flagged:
            pre = long_pre
        base_vals = [yb.get(s, np.nan) for s in pre]
        base_vals = [v for v in base_vals if pd.notna(v)]
        if not base_vals:
            continue
        beta = float(np.mean(base_vals))
        if zero_floor and beta == 0:
            beta = ZERO_FLOOR / len(base_vals)
        if growth in ("own", "own_5p"):
            other = rows.set_index("year")["units_5p"].astype(float)
            if growth == "own":
                other = other + rows.set_index("year")["units_1"].astype(float)
            series = other.to_dict()
        elif growth == "state":
            series = state_series.get(rows["state"].iloc[0], {})
        elif growth == "given":
            series = dict((series_by_place or {}).get(gid, {}))
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
                unstable=bool(flagged),
            )
        )
    return out
