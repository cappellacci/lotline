"""Estimate the ADU hazard's anchor from Lotline's own post-reform places (analysis plan D-019,
pre-registered).

The anchor θ = `adu_mature_hazard_ref` scales every place's mature ADU hazard (model/hazard.py). For a
place-year with a coded ADU rule in force, the scenario's current-rules path gives the expected ADU permits:

    μ = θ × k,   k = eligible parcels × h_m(θ = 1) × max over rules in force of c × ramp(age at mid-year)

where h_m(θ = 1) uses that year's rent, home value and actual mortgage rate. With a restricted rule c is the
partial-rule share s, so k = parcels × h_m(1) × max(s × ramp_partial, ramp_handbook).

Observed counts y are negative binomial around μ: P(y) = Γ(y + 1/α) / (Γ(1/α) y!) × (1/(1 + αμ))^(1/α) ×
(αμ/(1 + αμ))^y, Var = μ + αμ² (α → 0 is Poisson). θ is estimated on the log scale by maximum likelihood with
α profiled out; its 90% interval is the profile-likelihood interval {θ : 2(ℓ̂ − ℓ_p(θ)) <= 2.706}. Only NumPy
and the standard library are used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

CHI2_90 = 2.705543  # 90% point of chi-square with 1 degree of freedom
Z_95 = 1.644854  # standard normal 95th percentile


def nb_loglik(y, mu, alpha: float) -> float:
    """Negative-binomial log-likelihood, Var = μ + αμ²; Poisson when alpha <= 1e-8.

    By hand, y = 2, μ = 1: Poisson log(e^-1 / 2) = −1.6931; α = 1 (geometric, p = 1/2):
    log(Γ(3) / (Γ(1) 2!) × (1/2)^1 × (1/2)^2) = log(1/8) = −2.0794.
    """
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    if np.any(mu <= 0):
        return -math.inf
    if alpha <= 1e-8:
        return float(np.sum(y * np.log(mu) - mu - _lgamma(y + 1)))
    r = 1.0 / alpha
    return float(
        np.sum(
            _lgamma(y + r)
            - math.lgamma(r)
            - _lgamma(y + 1)
            + r * np.log(r / (r + mu))
            + y * np.log(mu / (r + mu))
        )
    )


def _lgamma(x):
    return np.vectorize(math.lgamma, otypes=[float])(np.asarray(x, dtype=float))


def _golden_max(f, lo: float, hi: float, tol: float = 1e-7, iters: int = 200) -> tuple[float, float]:
    """Maximize a unimodal f on [lo, hi] by golden-section search -> (argmax, max)."""
    g = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(iters):
        if abs(b - a) < tol:
            break
        if fc >= fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    x = (a + b) / 2
    return x, f(x)


LOG_ALPHA = (-12.0, 4.0)  # α from ~6e-6 (effectively Poisson) to ~55


def profile_alpha(y, mu) -> tuple[float, float]:
    """max over α of the NB log-likelihood -> (alpha, loglik); compares against Poisson (α = 0)."""
    la, ll = _golden_max(lambda la: nb_loglik(y, mu, math.exp(la)), *LOG_ALPHA)
    pois = nb_loglik(y, mu, 0.0)
    return (0.0, pois) if pois >= ll else (math.exp(la), ll)


@dataclass(frozen=True)
class Fit:
    theta: float
    low: float  # 90% profile-likelihood interval
    high: float
    alpha: float
    loglik: float
    n: int

    @property
    def log_se(self) -> float:
        """Standard error of log θ implied by the 90% interval (for the parametric bootstrap)."""
        return (math.log(self.high) - math.log(self.low)) / (2 * Z_95)


def fit_anchor(y, k, log_theta_range: tuple[float, float] = (-14.0, 0.0)) -> Fit:
    """Maximum-likelihood θ for counts y ~ NB(θ k, α), α profiled; 90% profile-likelihood interval.

    `k` may be 2-D (one row per value of a nuisance parameter such as the partial-rule share s): the profile
    then also maximizes over the rows, so θ's interval accounts for not knowing s.
    """
    y = np.asarray(y, dtype=float)
    ks = np.atleast_2d(np.asarray(k, dtype=float))
    keep = (ks > 0).all(axis=0)
    y, ks = y[keep], ks[:, keep]

    def best(lt: float) -> tuple[float, float]:
        fits = [profile_alpha(y, math.exp(lt) * row) for row in ks]
        return max(fits, key=lambda f: f[1])

    def prof(lt: float) -> float:
        return best(lt)[1]

    lt_hat, ll_hat = _golden_max(prof, *log_theta_range)
    alpha, _ = best(lt_hat)

    def edge(lo: float, hi: float) -> float:  # bisection for 2(ll_hat - prof) = CHI2_90 between lo and hi
        f_lo = 2 * (ll_hat - prof(lo)) - CHI2_90
        for _ in range(100):
            mid = (lo + hi) / 2
            f_mid = 2 * (ll_hat - prof(mid)) - CHI2_90
            if (f_mid > 0) == (f_lo > 0):
                lo, f_lo = mid, f_mid
            else:
                hi = mid
        return (lo + hi) / 2

    low = edge(log_theta_range[0], lt_hat)
    high = edge(log_theta_range[1], lt_hat)
    return Fit(math.exp(lt_hat), math.exp(low), math.exp(high), alpha, ll_hat, int(len(y)))


def predictive(k, fit: Fit, draws: int = 10_000, seed: int = 0) -> np.ndarray:
    """Parametric-bootstrap predictive counts, shape (draws, len(k)): log θ ~ N(log θ̂, se), NB(θ k, α)."""
    rng = np.random.default_rng(seed)
    k = np.asarray(k, dtype=float)
    theta = np.exp(rng.normal(math.log(fit.theta), fit.log_se, size=(draws, 1)))
    mu = theta * k[None, :]
    if fit.alpha > 0:
        mu = rng.gamma(1.0 / fit.alpha, mu * fit.alpha)
    return rng.poisson(mu)


# ---------------------------------------------------------------------------------------------------------
# The partial-rule share s: k(s) = parcels × h_m(1) × max(s × ramp_partial, ramp_handbook)
# ---------------------------------------------------------------------------------------------------------


def k_of_share(k_handbook, k_partial, share: float) -> np.ndarray:
    """Expected count at θ = 1 for a given partial-rule share: max(s × k_partial, k_handbook), elementwise."""
    return np.maximum(share * np.asarray(k_partial, dtype=float), np.asarray(k_handbook, dtype=float))


def profile_share(y, k_handbook, k_partial, grid) -> tuple[np.ndarray, np.ndarray, tuple[float, float]]:
    """Profile log-likelihood of s over a grid (θ and α maximized at each s), and s's 90% interval.

    Returns (grid, loglik per s, (low, high)); the interval is the grid range within CHI2_90 / 2 of the max.
    """
    grid = np.asarray(grid, dtype=float)
    ll = np.array([fit_anchor(y, k_of_share(k_handbook, k_partial, s)).loglik for s in grid])
    inside = grid[2 * (ll.max() - ll) <= CHI2_90]
    return grid, ll, (float(inside.min()), float(inside.max()))


# ---------------------------------------------------------------------------------------------------------
# Place-years from the processed tables (the scenario's current-rules path)
# ---------------------------------------------------------------------------------------------------------


def place_years(state: str, store, geoids, years, params=None, assume_rules=None):
    """One row per place-year that can be checked: a coded ADU rule in force by 1 July, and a permit source
    covering the place that flags ADUs that year. Columns: geoid, name, year, adu_permits (observed),
    eligible_parcels, rent, home_value, mortgage_rate (actual), h1 (mature hazard at θ = 1),
    ramp_handbook, ramp_partial (largest ramp over Handbook-equivalent / restricted rules in force),
    k_handbook, k_partial (= parcels × h1 × ramp). Reads holdout-filtered tables only.

    `assume_rules` (geoid -> [(class, effective Timestamp)]) stands in for a place with no coded ADU rule;
    only for clearly labelled exploratory runs, never for the pre-registered fit.
    """
    import pandas as pd

    from lotline.model import hazard, money
    from lotline.model.scenarios import adu

    p = dict(adu.central_params() if params is None else params)
    unit = 1e-3  # h_m is linear in θ below the cap of 1: evaluate at a small θ and rescale
    p["adu_mature_hazard_ref"] = unit
    years = list(years)
    market = store.read(state, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    rate = market[market["geo"] == money.NATIONAL].set_index("year")["mortgage_rate"]
    acs = store.read(state, "acs_geo_year")
    juris = store.read(state, "jurisdictions").set_index("geoid")
    elig = store.read(state, "eligible_parcels")
    from lotline.build import eligible as eligible_rule

    elig = elig[(elig["theme"] == "adu") & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    permits = store.read(state, "permits")
    flags = permits[adu._is_adu(permits)].groupby(["source", "issue_year"]).size()
    covered = permits.groupby(["jurisdiction_geoid", "source", "issue_year"]).size().reset_index()
    covered = covered[
        [(s, y) in flags.index for s, y in zip(covered["source"], covered["issue_year"], strict=True)]
    ]
    covered = set(zip(covered["jurisdiction_geoid"], covered["issue_year"], strict=True))
    counts = adu.observed_adu_counts(permits, min(years), max(years)).set_index(["geoid", "year"])[
        "adu_permits"
    ]
    from lotline.config import load_state

    fips = load_state(state).fips
    reforms = adu.load_reforms(state)
    reforms = reforms[(reforms["theme"] == "adu") & (reforms["status"] == "in_force")]
    rows = []
    for g in geoids:
        mine = reforms[reforms["jurisdiction_geoid"].isin([g, fips])]  # a state law applies everywhere
        rules = []
        for r in mine.itertuples():
            rubric = adu._resolved(reforms, r.reform_id)
            per_lot = rubric.get("adus_per_lot", getattr(r, "adus_per_lot", None))
            if per_lot is not None and pd.notna(per_lot) and float(per_lot) == 0:
                continue  # an explicit "no ADUs" row is not an ADU rule (#164)
            cls = "partial" if adu.rule_restrictions(rubric)[0] else "handbook"
            rules.append((cls, r.effective_date, r.end_date))
        if not rules and assume_rules and g in assume_rules:
            rules = [(c, eff, pd.NaT) for c, eff in assume_rules[g]]
        e = elig[elig["jurisdiction_geoid"] == g]
        kind = juris.loc[g, "kind"] if g in juris.index else "place"
        geo = f"{adu.ACS_PREFIX.get(kind, 'place')}:{g}"
        for y in years:
            mid = pd.Timestamp(f"{y}-07-01")
            live = [
                (c, (mid - eff).days / 365.25)
                for c, eff, end in rules
                if eff <= mid and (pd.isna(end) or end > mid)
            ]
            if not live or (g, y) not in covered or e.empty:
                continue
            ey = e.assign(after=e["year"] > y, gap=(e["year"] - y).abs()).sort_values(["after", "gap"])
            parcels = float(ey["eligible_parcels"].iloc[0])
            v = adu.acs_values(acs, pd.Series([geo]), y, cpi)
            if v.empty or v[["rent", "home_value"]].isna().any(axis=None):
                continue
            v = v.iloc[0]
            h1 = float(hazard.adu_mature_hazard(v["rent"], v["home_value"], float(rate[y]), p)) / unit
            ramp = {
                c: max(
                    (
                        float(hazard.ramp(a, p["adu_ramp_half_years"], p["adu_ramp_slope_years"]))
                        for cc, a in live
                        if cc == c
                    ),
                    default=0.0,
                )
                for c in ("handbook", "partial")
            }
            rows.append(
                {
                    "state": state,
                    "geoid": g,
                    "name": juris["name"].get(g, g),
                    "year": y,
                    "adu_permits": int(counts.get((g, y), 0)),
                    "eligible_parcels": parcels,
                    "rent": v["rent"],
                    "home_value": v["home_value"],
                    "mortgage_rate": float(rate[y]),
                    "h1": h1,
                    "ramp_handbook": ramp["handbook"],
                    "ramp_partial": ramp["partial"],
                }
            )
    out = pd.DataFrame(rows)
    if not out.empty:
        out["k_handbook"] = out["eligible_parcels"] * out["h1"] * out["ramp_handbook"]
        out["k_partial"] = out["eligible_parcels"] * out["h1"] * out["ramp_partial"]
    return out
