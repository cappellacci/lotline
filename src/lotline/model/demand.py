"""Spec C (analysis plan D-006): two demand signals on top of the baseline's recent pace.

Spec B keeps each place at its own recent pace. Spec C multiplies that level by `exp(β_h · g + β_p · q)`:

- **g, household growth:** annualized growth of occupied housing units (ACS `B25003_001`) in the place's
  county, the 5-year estimate ending in year t against the non-overlapping one ending 5 years earlier:
  `g = (E[t] / E[t − 5])^(1/5) − 1` (`household_growth_years`).
- **q, house prices:** annualized FHFA index change over the 3 years to t on **one** geography:
  `q = (HPI[t] / HPI[t − 3])^(1/3) − 1` (`hpi_change_years`). The geography is the place's `hpi_geo` in year
  t (the first level of the panel's chain county → metro/micro area → state non-CBSA → state that has a
  value); if it lacks either year, the next level down that has both. A ratio never mixes geographies.
- **β_h, β_p:** pooled Poisson regression per state and size class on fit years only (t ≤ origin). For each
  place-year with a full trailing history, the expected count is `E_it` = the spec-B level from years
  t−5..t−1 × eligible parcels in t / 1,000, and `y_it ~ Poisson(exp(log E_it + β_0 + β_h g_it + β_p q_it))`,
  fitted by iteratively reweighted least squares (`poisson_irls`).
- **Forecast:** g and q at the origin, held over the horizon. β_0 is estimated but **not applied**: it
  absorbs the average drift between spec B's level and the next year's count so the slopes aren't biased,
  and D-006 leaves spec B's level otherwise unchanged. A place without g or q at the origin keeps
  multiplier 1 (spec B), and so does every place when the fit fails (no permits, or no convergence).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from lotline.build.panels import HPI_LEVELS
from lotline.config import Parameter, load_params
from lotline.model import baseline

HOUSEHOLDS = "B25003_001"  # ACS: occupied housing units (households), Total


@dataclass(frozen=True)
class DemandInputs:
    """The two signals' sources for one state: county households and the FHFA index by geography."""

    households: pd.Series  # (geo "county:<5-digit>", ACS end year) -> estimate
    hpi: pd.Series  # (geo, year) -> FHFA index


@dataclass(frozen=True)
class DemandFit:
    """Result of the Poisson fit for one state, size class and origin."""

    beta_0: float
    beta_h: float
    beta_p: float
    n: int  # place-years in the fit
    converged: bool


def inputs_from_tables(acs: pd.DataFrame, market: pd.DataFrame) -> DemandInputs:
    """DemandInputs from a state's processed `acs_geo_year` and `market_geo_year` tables."""
    a = acs[(acs["variable"] == HOUSEHOLDS) & acs["geo"].str.startswith("county:")]
    a = a.dropna(subset=["estimate"])
    households = a.groupby(["geo", a["end_year"].astype(int)])["estimate"].first().astype(float)
    m = market.dropna(subset=["hpi"])
    hpi = m.groupby(["geo", m["year"].astype(int)])["hpi"].first().astype(float)
    return DemandInputs(households=households, hpi=hpi)


def _lookup(series: pd.Series, geo: pd.Series, year: np.ndarray) -> np.ndarray:
    idx = pd.MultiIndex.from_arrays([geo.astype(object).to_numpy(), np.asarray(year, dtype=int)])
    return series.reindex(idx).to_numpy(dtype=float)


def _annualized(now: np.ndarray, then: np.ndarray, years: int) -> np.ndarray:
    ok = (now > 0) & (then > 0)
    ratio = np.divide(now, then, out=np.full_like(now, np.nan), where=ok)
    return np.where(ok, ratio ** (1.0 / years) - 1.0, np.nan)


def household_growth(rows: pd.DataFrame, households: pd.Series, years: int) -> np.ndarray:
    """g for each row (needs `county_geoid` and `year`): (E[t] / E[t − years])^(1/years) − 1, NaN if missing.

    By hand: 10,000 households in the estimate ending 2020 and 8,000 in the one ending 2015:
    (10000 / 8000)^(1/5) − 1 = 1.25^0.2 − 1 = 0.04564.
    """
    geo = "county:" + rows["county_geoid"].astype("string")
    t = rows["year"].to_numpy(dtype=int)
    return _annualized(_lookup(households, geo, t), _lookup(households, geo, t - years), years)


def hpi_chain(rows: pd.DataFrame) -> list[pd.Series]:
    """The panel's FHFA fallback geographies for each row, in chain order (see `build.panels._hpi`)."""
    state = rows["geoid"].astype(str).str[:2]
    codes = {
        "county": "county:" + rows["county_geoid"].astype("string"),
        "cbsa": "cbsa:" + rows["cbsa_code"].astype("string") if "cbsa_code" in rows else None,
        "state_noncbsa": "cbsa:000" + state,
        "state": "state:" + state,
    }
    na = pd.Series(pd.NA, index=rows.index, dtype="string")
    return [codes[level] if codes[level] is not None else na for level in HPI_LEVELS]


def price_change(rows: pd.DataFrame, hpi: pd.Series, years: int) -> np.ndarray:
    """q for each row (needs `geoid`, `county_geoid`, `year`, `hpi_geo`, optionally `cbsa_code`).

    Starts at the row's own `hpi_geo` and walks down the chain to the first geography with the index in
    both t and t − years; the ratio always uses one geography. By hand: index 200 in 2020 and 160 in 2017 on
    the county: (200 / 160)^(1/3) − 1 = 1.25^(1/3) − 1 = 0.07722.
    """
    t = rows["year"].to_numpy(dtype=int)
    chain = hpi_chain(rows)
    own = rows["hpi_geo"].astype("string") if "hpi_geo" in rows else pd.Series(pd.NA, index=rows.index)
    start = np.zeros(len(rows), dtype=int)  # no recorded hpi_geo: the whole chain
    found = np.zeros(len(rows), dtype=bool)
    for i, geo in enumerate(chain):
        hit = (own == geo).fillna(False).to_numpy(dtype=bool) & ~found
        start[hit], found = i, found | hit
    q = np.full(len(rows), np.nan)
    for i, geo in enumerate(chain):
        cand = _annualized(_lookup(hpi, geo, t), _lookup(hpi, geo, t - years), years)
        use = np.isnan(q) & (i >= start) & ~np.isnan(cand)
        q[use] = cand[use]
    return q


def signals(rows: pd.DataFrame, inputs: DemandInputs, params: dict[str, Parameter]) -> pd.DataFrame:
    """g and q for each row (place-year), as of that row's year."""
    g = household_growth(rows, inputs.households, int(params["household_growth_years"].value))
    q = price_change(rows, inputs.hpi, int(params["hpi_change_years"].value))
    return pd.DataFrame({"g": g, "q": q}, index=rows.index)


def poisson_irls(
    y: np.ndarray, x: np.ndarray, offset: np.ndarray, *, tol: float, max_iter: int
) -> tuple[np.ndarray, bool]:
    """Poisson log-link regression with an offset by iteratively reweighted least squares.

    Maximizes Σ y·η − exp(η) with η = offset + Xβ. Each step solves the weighted least squares
    (XᵀWX) β = XᵀW z with weights W = μ and working response z = η − offset + (y − μ) / μ, by least squares
    (stable when the signals are nearly collinear). Starts from the intercept-only solution, with x's first
    column taken to be the constant; a rank-deficient X (e.g. a signal that never varies) is reported as
    not converged rather than given a made-up coefficient. Converged when the relative change in deviance
    is below `tol` (|ΔD| / (|D| + 0.1) < tol, the rule R's glm uses): a coefficient-change rule never
    settles when two signals are nearly collinear, because rounding keeps the coefficients jittering.
    Returns (β, converged).
    """
    y, x, offset = (np.asarray(a, dtype=float) for a in (y, x, offset))
    beta = np.zeros(x.shape[1])
    if y.sum() <= 0:
        return beta, False
    if np.linalg.matrix_rank(x) < x.shape[1]:  # a signal that can't be identified: report it, don't invent β
        return beta, False
    beta[0] = np.log(y.sum() / np.exp(offset).sum())
    dev = _deviance(y, np.exp(offset + x @ beta))
    for _ in range(max_iter):
        eta = offset + x @ beta
        mu = np.exp(eta)
        z = eta - offset + (y - mu) / mu
        sw = np.sqrt(mu)
        new = np.linalg.lstsq(x * sw[:, None], z * sw, rcond=None)[0]
        if not np.all(np.isfinite(new)):
            return beta, False
        new_dev = _deviance(y, np.exp(offset + x @ new))
        if not np.isfinite(new_dev):
            return beta, False
        done = abs(new_dev - dev) / (abs(new_dev) + 0.1) < tol
        beta, dev = new, new_dev
        if done:
            return beta, True
    return beta, False


def _deviance(y: np.ndarray, mu: np.ndarray) -> float:
    """Poisson deviance 2 Σ [y log(y/μ) − (y − μ)], with y log(y/μ) = 0 where y = 0."""
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(y > 0, y * np.log(y / mu), 0.0)
    return float(2 * np.sum(term - (y - mu)))


def fit_sample(
    panel: pd.DataFrame,
    value: str,
    origin: int,
    inputs: DemandInputs,
    params: dict[str, Parameter],
    *,
    group: str = "county_geoid",
    key: str = "geoid",
) -> pd.DataFrame:
    """Place-years t <= origin for the fit: y, E (spec-B expected count), g and q as of t.

    E = level from years t − level_years .. t − 1 (spec B, `baseline.level_estimates`) × eligible parcels
    in t / 1,000. Kept: y observed, parcels > 0, E > 0 (log E finite), and both g and q available.
    """
    level_years = int(params["level_years"].value)
    hist = panel[panel["year"] <= origin]
    parts = []
    for t in sorted(int(y) for y in hist["year"].unique()):
        if t - level_years < int(hist["year"].min()):
            continue
        lev = baseline.level_estimates(
            hist[hist["year"] <= t - 1],
            value,
            t - 1,
            level_years=level_years,
            min_group_places=int(params["min_group_places"].value),
            group=group,
            use_direct_variance=bool(params["use_direct_variance"].value),
            key=key,
        )
        if lev.empty:
            continue
        rows = hist[(hist["year"] == t) & hist[key].isin(lev[key])].drop_duplicates(key)
        rows = rows[rows[value].notna() & (rows[baseline.PARCELS].astype(float) > 0)]
        if rows.empty:
            continue
        level = rows[key].map(lev.set_index(key)["level"]).astype(float)
        e = level * rows[baseline.PARCELS].astype(float) / baseline.PER
        s = signals(rows, inputs, params)
        part = pd.DataFrame(
            {key: rows[key], "year": t, "y": rows[value].astype(float), "e": e, "g": s["g"], "q": s["q"]}
        )
        parts.append(part[(part["e"] > 0) & part["g"].notna() & part["q"].notna()])
    cols = [key, "year", "y", "e", "g", "q"]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)


def fit(sample: pd.DataFrame, params: dict[str, Parameter]) -> DemandFit:
    """β_0, β_h, β_p from a `fit_sample` table; a failed fit (no permits, no convergence) gives 0s."""
    if sample.empty:
        return DemandFit(0.0, 0.0, 0.0, 0, False)
    x = np.column_stack([np.ones(len(sample)), sample["g"].to_numpy(float), sample["q"].to_numpy(float)])
    beta, ok = poisson_irls(
        sample["y"].to_numpy(float),
        x,
        np.log(sample["e"].to_numpy(float)),
        tol=float(params["irls_tolerance"].value),
        max_iter=int(params["irls_max_iterations"].value),
    )
    if not ok:
        return DemandFit(0.0, 0.0, 0.0, len(sample), False)
    return DemandFit(float(beta[0]), float(beta[1]), float(beta[2]), len(sample), True)


def multipliers(
    panel: pd.DataFrame,
    value: str,
    origin: int,
    inputs: DemandInputs,
    *,
    params: dict[str, Parameter] | None = None,
    group: str = "county_geoid",
    key: str = "geoid",
) -> tuple[pd.DataFrame, dict[str, DemandFit]]:
    """Spec C's multiplier per place at the origin: exp(β_h · g + β_p · q), β fitted per state.

    Returns (table with key, state, g, q, multiplier, fallback; fits by state). fallback is True where the
    place has no g or q at the origin, or its state's fit failed: those places get multiplier 1 (spec B).
    Only rows with year <= origin are used.
    """
    p = params or load_params("baseline")
    hist = panel[panel["year"] <= origin]
    fits: dict[str, DemandFit] = {}
    tables = []
    for state, ps in hist.groupby("state", sort=True):
        f = fit(fit_sample(ps, value, origin, inputs, p, group=group, key=key), p)
        fits[str(state)] = f
        rows = ps[ps["year"] == origin].drop_duplicates(key)
        s = signals(rows, inputs, p)
        m = np.exp(f.beta_h * s["g"] + f.beta_p * s["q"])
        fallback = s["g"].isna() | s["q"].isna() | (not f.converged)
        tables.append(
            pd.DataFrame(
                {
                    key: rows[key],
                    "state": state,
                    "g": s["g"],
                    "q": s["q"],
                    "multiplier": m.where(~fallback, 1.0),
                    "fallback": fallback,
                }
            )
        )
    cols = [key, "state", "g", "q", "multiplier", "fallback"]
    table = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=cols)
    return table, fits
