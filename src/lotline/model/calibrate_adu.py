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


def nb_loglik_rows(y, mu, alpha: float) -> np.ndarray:
    """Per-observation NB log-likelihood (Poisson when alpha <= 1e-8); −inf where μ <= 0."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    safe = np.where(mu > 0, mu, 1.0)
    if alpha <= 1e-8:
        ll = y * np.log(safe) - safe - _lgamma(y + 1)
    else:
        r = 1.0 / alpha
        ll = (
            _lgamma(y + r)
            - math.lgamma(r)
            - _lgamma(y + 1)
            + r * np.log(r / (r + safe))
            + y * np.log(safe / (r + safe))
        )
    return np.where(mu > 0, ll, -np.inf)


def mix_loglik(y, mu_a, mu_b, q, alpha: float) -> float:
    """Σ log(q·NB(y; μ_a) + (1 − q)·NB(y; μ_b)): a rule class unknown with P(class A) = q (D-022).

    q = 0 is the plain NB likelihood at μ_b. By hand, y = 2, μ_a = 1, μ_b = 2, q = 0.5, Poisson:
    log(0.5·e^−1/2 + 0.5·4e^−2/2) = log(0.09197 + 0.13534) = −1.4814.
    """
    q = np.broadcast_to(np.asarray(q, dtype=float), np.shape(y))
    la, lb = nb_loglik_rows(y, mu_a, alpha), nb_loglik_rows(y, mu_b, alpha)
    with np.errstate(divide="ignore"):
        terms = np.logaddexp(np.log(q) + la, np.log1p(-q) + lb)
    return float(np.sum(terms))


def profile_alpha(y, mu, mu_b=None, q=None) -> tuple[float, float]:
    """max over α of the (mixture) NB log-likelihood -> (alpha, loglik); compares against Poisson (α = 0).

    Without `mu_b`/`q` it is the plain NB likelihood at `mu`."""
    if mu_b is None or q is None:

        def ll(a):
            return nb_loglik(y, mu, a)
    else:

        def ll(a):
            return mix_loglik(y, mu, mu_b, q, a)

    la, best = _golden_max(lambda la: ll(math.exp(la)), *LOG_ALPHA)
    pois = ll(0.0)
    return (0.0, pois) if pois >= best else (math.exp(la), best)


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


def fit_anchor(y, k, log_theta_range: tuple[float, float] = (-14.0, 0.0), k_b=None, q=None) -> Fit:
    """Maximum-likelihood θ for counts y ~ NB(θ k, α), α profiled; 90% profile-likelihood interval.

    With `k_b` and `q` (D-022), each count is a mixture: P(y) = q·NB(y; θ k) + (1 − q)·NB(y; θ k_b).

    `k` may be 2-D (one row per value of a nuisance parameter such as the partial-rule share s): the profile
    then also maximizes over the rows, so θ's interval accounts for not knowing s.
    """
    y = np.asarray(y, dtype=float)
    ks = np.atleast_2d(np.asarray(k, dtype=float))
    kbs = ks if k_b is None else np.atleast_2d(np.asarray(k_b, dtype=float))
    qs = np.zeros(ks.shape[1]) if q is None else np.asarray(q, dtype=float)
    mixed = q is not None
    keep = ((ks > 0) | (qs == 0)).all(axis=0) & ((kbs > 0) | (qs == 1)).all(axis=0)
    y, ks, kbs, qs = y[keep], ks[:, keep], kbs[:, keep], qs[keep]

    def best(lt: float) -> tuple[float, float]:
        t = math.exp(lt)
        fits = [
            profile_alpha(y, t * a, t * b, qs) if mixed else profile_alpha(y, t * a)
            for a, b in zip(ks, kbs, strict=True)
        ]
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


def predictive(k, fit: Fit, draws: int = 10_000, seed: int = 0, k_b=None, q=None) -> np.ndarray:
    """Parametric-bootstrap predictive counts, shape (draws, len(k)): log θ ~ N(log θ̂, se), NB(θ k, α).

    With `k_b` and `q`, each draw uses k with probability q, else k_b (a rule class left unknown, D-022)."""
    rng = np.random.default_rng(seed)
    k = np.asarray(k, dtype=float)
    theta = np.exp(rng.normal(math.log(fit.theta), fit.log_se, size=(draws, 1)))
    if k_b is not None and q is not None:
        pick = rng.random((draws, len(k))) < np.asarray(q, dtype=float)[None, :]
        k = np.where(pick, k[None, :], np.asarray(k_b, dtype=float)[None, :])
    mu = theta * k
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


def k_paths(rows, share: float) -> tuple[np.ndarray, np.ndarray]:
    """Expected counts at θ = 1 when blank-dependent rules restrict (A) or don't (B), for partial share s:
    A = parcels × h1 × max(s × max(ramp_partial, ramp_blank), ramp_handbook);
    B = parcels × h1 × max(s × ramp_partial, max(ramp_handbook, ramp_blank)). Equal where ramp_blank = 0."""
    base = np.asarray(rows["eligible_parcels"] * rows["h1"], dtype=float)
    rp, rh, rb = (np.asarray(rows[c], dtype=float) for c in ("ramp_partial", "ramp_handbook", "ramp_blank"))
    a = base * np.maximum(share * np.maximum(rp, rb), rh)
    b = base * np.maximum(share * rp, np.maximum(rh, rb))
    return a, b


def profile_share_rows(y, rows, grid) -> tuple[np.ndarray, np.ndarray, tuple[float, float]]:
    """`profile_share` for place-years whose class may depend on blank fields (mixture over `q_blank`)."""
    grid = np.asarray(grid, dtype=float)
    q = np.asarray(rows["q_blank"], dtype=float)
    ll = []
    for s in grid:
        a, b = k_paths(rows, s)
        ll.append(fit_anchor(y, a, k_b=b, q=q).loglik)
    ll = np.array(ll)
    inside = grid[2 * (ll.max() - ll) <= CHI2_90]
    return grid, ll, (float(inside.min()), float(inside.max()))


SURVEY_SOURCES = frozenset({"metc_residential_permits"})  # counts reported by cities to a survey (D-041)


def count_settings(exclude_cobuilt: bool = True, report_rate: float | None = None) -> dict:
    """D-041 count rules with `config/params/adu_counts.yaml`'s central values unless overridden."""
    from lotline.config import load_params

    p = load_params("adu_counts")
    rho = p["adu_survey_report_rate"].value if report_rate is None else report_rate
    window = int(p["adu_cobuilt_window_years"].value)
    return {"exclude_cobuilt": exclude_cobuilt, "window": window, "report_rate": float(rho)}


def cobuilt(permits, window: int):
    """True for an ADU permit whose source also issued a new single-family house permit (SFD, units_new ≥ 1,
    not a conversion) on the same parcel within `window` calendar years either side (D-041). False where the
    parcel is unknown."""
    import pandas as pd

    from lotline.model.scenarios import adu

    new = permits[
        (permits["building_type_std"] == "SFD")
        & (permits["units_new"].fillna(0) >= 1)
        & ~permits["is_conversion"].fillna(False).astype(bool)
    ][["source", "parcel_id", "issue_year"]].dropna()
    keys = pd.concat(
        [new.assign(issue_year=new["issue_year"] + d) for d in range(-window, window + 1)]
    ).drop_duplicates()
    keys = set(zip(keys["source"], keys["parcel_id"], keys["issue_year"], strict=True))
    hit = [
        (s, q, y) in keys
        for s, q, y in zip(permits["source"], permits["parcel_id"], permits["issue_year"], strict=True)
    ]
    return adu._is_adu(permits) & pd.Series(hit, index=permits.index) & permits["parcel_id"].notna()


def adu_counts(permits, first: int, last: int, settings: dict):
    """As `scenarios.adu.observed_adu_counts` (the larger source each year, never the sum), with D-041's
    rules: co-built ADUs dropped if `settings['exclude_cobuilt']`, and a `survey` flag where the count kept
    comes from a survey source (ties go to the city's own records)."""
    from lotline.model.scenarios import adu

    flagging = permits.loc[adu._is_adu(permits), "source"].unique()
    p = permits[permits["source"].isin(flagging) & permits["jurisdiction_geoid"].notna()]
    p = p[(p["issue_year"] >= first) & (p["issue_year"] <= last)]
    keep = adu._is_adu(p)
    if settings["exclude_cobuilt"]:
        keep = keep & ~cobuilt(p, settings["window"])
    p = p.assign(adu=keep, survey=p["source"].isin(SURVEY_SOURCES))
    by = p.groupby(["jurisdiction_geoid", "issue_year", "source", "survey"])["adu"].sum().reset_index()
    by = by.sort_values(["adu", "survey"], ascending=[False, True])  # the larger; on a tie, the city's own
    out = by.groupby(["jurisdiction_geoid", "issue_year"]).head(1)
    return out.rename(columns={"jurisdiction_geoid": "geoid", "issue_year": "year", "adu": "adu_permits"})[
        ["geoid", "year", "adu_permits", "survey"]
    ]


def place_years(state: str, store, geoids, years, params=None, assume_rules=None, counts=None):
    """One row per place-year that can be checked: a coded ADU rule in force by 1 July, and a permit source
    covering the place that flags ADUs that year. Columns: geoid, name, year, adu_permits (observed),
    eligible_parcels, rent, home_value, mortgage_rate (actual), h1 (mature hazard at θ = 1),
    ramp_handbook, ramp_partial (largest ramp over Handbook-equivalent / restricted rules in force),
    k_handbook, k_partial (= parcels × h1 × ramp). Reads holdout-filtered tables only.

    `assume_rules` (geoid -> [(class, effective Timestamp)]) stands in for a place with no coded ADU rule;
    only for clearly labelled exploratory runs, never for the pre-registered fit.

    `counts` (`count_settings()`, D-041) applies the count rules; `report_rate` is then ρ for a survey-counted
    place-year and 1 otherwise, and k is multiplied by it. Without it, counts are as D-039 and the rate is 1.
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
    if counts is None:
        rho, counts = 1.0, adu.observed_adu_counts(permits, min(years), max(years)).assign(survey=False)
    else:
        rho, counts = counts["report_rate"], adu_counts(permits, min(years), max(years), counts)
    survey = counts.set_index(["geoid", "year"])["survey"]
    counts = counts.set_index(["geoid", "year"])["adu_permits"]
    from lotline.config import load_params, load_state

    fips = load_state(state).fips
    all_reforms = adu.load_reforms(state)
    reforms = all_reforms[(all_reforms["theme"] == "adu") & (all_reforms["status"] == "in_force")]
    every = pd.concat([adu.load_reforms(st).assign(state=st) for st in adu.REFORM_STATES], ignore_index=True)
    min_count = int(load_params("adu")["adu_rule_min_coded"].value)
    field_counts = adu.field_restrict_counts(every, pd.Timestamp.today().normalize())  # pre-registered
    fp = adu.field_probabilities(field_counts, state, min_count)
    rows = []
    for g in geoids:
        mine = reforms[reforms["jurisdiction_geoid"].isin([g, fips])]  # a state law applies everywhere
        e = elig[elig["jurisdiction_geoid"] == g]
        kind = juris.loc[g, "kind"] if g in juris.index else "place"
        geo = f"{adu.ACS_PREFIX.get(kind, 'place')}:{g}"
        for y in years:
            mid = pd.Timestamp(f"{y}-07-01")
            live = []  # (class, age, q): class partial / handbook / blank (Handbook unless a blank restricts)
            for r in mine.itertuples():
                if not (r.effective_date <= mid and (pd.isna(r.end_date) or r.end_date > mid)):
                    continue
                rubric = adu.with_parking(adu._resolved(reforms, r.reform_id), all_reforms, g, mid)
                if adu._no_adus(rubric):
                    continue  # an explicit "no ADUs" row is not an ADU rule (#164)
                fails, unknown = adu.rule_restrictions(rubric)
                q = 1 - float(np.prod([1 - fp[f] for f in unknown])) if unknown and not fails else 0.0
                cls = "partial" if fails else ("blank" if q > 0 else "handbook")
                live.append((cls, (mid - r.effective_date).days / 365.25, q))
            if not live and assume_rules and g in assume_rules:
                live = [(c, (mid - eff).days / 365.25, 0.0) for c, eff in assume_rules[g] if eff <= mid]
            if not live or (g, y) not in covered or e.empty:
                continue
            ey = e.assign(after=e["year"] > y, gap=(e["year"] - y).abs()).sort_values(["after", "gap"])
            parcels = float(ey["eligible_parcels"].iloc[0])
            v = adu.acs_values(acs, pd.Series([geo]), y, cpi)
            if v.empty or v[["rent", "home_value"]].isna().any(axis=None):
                continue
            v = v.iloc[0]
            h1 = float(hazard.adu_mature_hazard(v["rent"], v["home_value"], float(rate[y]), p)) / unit

            def ramp_of(c, live=live):
                return max(
                    (
                        float(hazard.ramp(a, p["adu_ramp_half_years"], p["adu_ramp_slope_years"]))
                        for cc, a, _ in live
                        if cc == c
                    ),
                    default=0.0,
                )

            ramp = {c: ramp_of(c) for c in ("handbook", "partial", "blank")}
            q_blank = max((q for c, _, q in live if c == "blank"), default=0.0)
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
                    "ramp_blank": ramp["blank"],
                    "q_blank": q_blank,
                    "report_rate": rho if bool(survey.get((g, y), False)) else 1.0,
                }
            )
    out = pd.DataFrame(rows)
    if not out.empty:
        k = out["eligible_parcels"] * out["h1"] * out["report_rate"]
        out["k_handbook"] = k * out["ramp_handbook"]
        out["k_partial"] = k * out["ramp_partial"]
    return out


# ---------------------------------------------------------------------------------------------------------
# Fit 3 (D-019, pre-registered): graded shares, gamma place effects, blank fields per place, coverage
# ---------------------------------------------------------------------------------------------------------


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

    @property
    def log_fact(self) -> float:
        return float(sum(math.lgamma(v + 1) for v in self.y))

    def k(self, cvals: np.ndarray) -> np.ndarray:
        """Expected counts at θ = 1 and u = 1 for each combination: (C, T) = base × max_r c(type) × cr."""
        return self.base[None, :] * (cvals[self.types] * self.cr[None, :, :]).max(axis=2)


def frailty_loglik_place(y, k, theta: float, alpha: float, log_fact: float | None = None) -> float:
    """log P(y_1..T) for one place with u ~ Gamma(mean 1, variance α), y_t | u ~ Poisson(θ u k_t).

    = Σ_t [y_t log(θ k_t) − log y_t!] + log Γ(Y + r) − log Γ(r) + r log r − (Y + r) log(r + θ K), r = 1/α,
    Y = Σ y_t, K = Σ k_t; α -> 0 gives the Poisson likelihood. By hand, one year y = 2, θk = 1, α = 1:
    log(1/2) + log Γ(3) − log Γ(1) + 0 − 3 log 2 = log(1/8), the geometric case of `nb_loglik`.
    """
    y = np.asarray(y, dtype=float)
    mu = theta * np.asarray(k, dtype=float)
    if np.any((mu <= 0) & (y > 0)):
        return -math.inf
    safe = np.where(mu > 0, mu, 1.0)
    log_fact = float(sum(math.lgamma(v + 1) for v in y)) if log_fact is None else log_fact
    head = float(np.sum(np.where(mu > 0, y * np.log(safe), 0.0))) - log_fact
    big_y, big_k = float(y.sum()), float(mu.sum())
    if alpha <= 1e-8:
        return head - big_k
    r = 1.0 / alpha
    return (
        head + math.lgamma(big_y + r) - math.lgamma(r) + r * math.log(r) - (big_y + r) * math.log(r + big_k)
    )


def frailty_loglik(places: list[PlaceData], theta: float, alpha: float, cvals: np.ndarray) -> float:
    """Σ over places of log Σ_c w_c P(y | combination c): blank fields integrated per place (D-022)."""
    total = 0.0
    for pl in places:
        ks = pl.k(cvals)
        lf = pl.log_fact
        terms = [
            math.log(w) + frailty_loglik_place(pl.y, k, theta, alpha, lf)
            for w, k in zip(pl.w, ks, strict=True)
            if w > 0
        ]
        total += float(np.logaddexp.reduce(terms))
    return total


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


def fit3(
    places: list[PlaceData],
    grid=GRID3,
    judgment=(0.5, 0.3),
    ranges=((0.2, 1.0), (0.1, 0.6)),
    log_theta_range=(-14.0, 0.0),
) -> Fit3:
    """Profile-likelihood fit of θ, α, m_o and m_x as pre-registered (D-019 fit 3)."""

    def best_alpha(lt, cv):
        return _golden_max(lambda la: frailty_loglik(places, math.exp(lt), math.exp(la), cv), *LOG_ALPHA)

    def prof_theta(cv):
        lt, ll = _golden_max(
            lambda lt: max(best_alpha(lt, cv)[1], frailty_loglik(places, math.exp(lt), 0.0, cv)),
            *log_theta_range,
        )
        return lt, ll

    surface = {(mo, mx): prof_theta(_cvals(mo, mx)) for mo in grid for mx in grid}
    lls = {key: v[1] for key, v in surface.items()}
    top = max(lls.values())

    def interval(axis: int):
        vals = sorted({key[axis] for key in lls})
        prof = {v: max(ll for key, ll in lls.items() if key[axis] == v) for v in vals}
        inside = [v for v in vals if 2 * (top - prof[v]) <= CHI2_90]
        hat = max(prof, key=prof.get)
        return hat, (min(inside), max(inside))

    (mo_hat, mo_int), (mx_hat, mx_int) = interval(0), interval(1)
    mo_est = (mo_int[1] - mo_int[0]) < (ranges[0][1] - ranges[0][0])
    mx_est = (mx_int[1] - mx_int[0]) < (ranges[1][1] - ranges[1][0])
    mos = [mo_hat] if mo_est else [judgment[0]]
    mxs = [mx_hat] if mx_est else [judgment[1]]
    if mo_est and mx_est:
        mos, mxs = list(grid), list(grid)  # θ's interval profiles over both shares
    elif mo_est:
        mos = list(grid)
    elif mx_est:
        mxs = list(grid)
    cands = [_cvals(a, b) for a in mos for b in mxs]

    def prof(lt):
        out = -math.inf
        for cv in cands:
            out = max(out, best_alpha(lt, cv)[1], frailty_loglik(places, math.exp(lt), 0.0, cv))
        return out

    m_o = mo_hat if mo_est else judgment[0]
    m_x = mx_hat if mx_est else judgment[1]
    lt_hat, _ = prof_theta(_cvals(m_o, m_x))
    ll_hat = prof(lt_hat)
    la, ll_a = best_alpha(lt_hat, _cvals(m_o, m_x))
    alpha = math.exp(la) if ll_a > frailty_loglik(places, math.exp(lt_hat), 0.0, _cvals(m_o, m_x)) else 0.0

    def edge(lo, hi):
        f_lo = 2 * (ll_hat - prof(lo)) - CHI2_90
        for _ in range(40):
            mid = (lo + hi) / 2
            f_mid = 2 * (ll_hat - prof(mid)) - CHI2_90
            if (f_mid > 0) == (f_lo > 0):
                lo, f_lo = mid, f_mid
            else:
                hi = mid
        return (lo + hi) / 2

    low, high = edge(log_theta_range[0], lt_hat), edge(log_theta_range[1], lt_hat)
    return Fit3(
        math.exp(lt_hat),
        math.exp(low),
        math.exp(high),
        alpha,
        m_o,
        m_x,
        mo_int,
        mx_int,
        mo_est,
        mx_est,
        ll_hat,
        len(places),
        int(sum(len(p.y) for p in places)),
    )


def fit_theta_alpha(places: list[PlaceData], cvals: np.ndarray, log_theta_range=(-14.0, 0.0)):
    """Maximum likelihood (θ, α) at fixed rule shares: log θ by golden section with α profiled out."""

    def best_alpha(lt):
        return _golden_max(lambda la: frailty_loglik(places, math.exp(lt), math.exp(la), cvals), *LOG_ALPHA)

    lt, _ = _golden_max(lambda lt: best_alpha(lt)[1], *log_theta_range)
    return math.exp(lt), math.exp(best_alpha(lt)[0])


def loglik_hessian(places: list[PlaceData], theta: float, alpha: float, cvals: np.ndarray, step=1e-3):
    """Hessian of `frailty_loglik` in (log θ, log α), by central differences.

    By hand, one place, one rule combination: ∂²/∂(log θ)² = −(Y + r) r θK / (r + θK)², r = 1/α, Y = Σ y,
    K = Σ k (the y log θ term is linear in log θ).
    """
    lt0, la0 = math.log(theta), math.log(alpha)

    def f(lt, la):
        return frailty_loglik(places, math.exp(lt), math.exp(la), cvals)

    h = step
    out = np.zeros((2, 2))
    out[0, 0] = (f(lt0 + h, la0) - 2 * f(lt0, la0) + f(lt0 - h, la0)) / h**2
    out[1, 1] = (f(lt0, la0 + h) - 2 * f(lt0, la0) + f(lt0, la0 - h)) / h**2
    out[0, 1] = out[1, 0] = (
        f(lt0 + h, la0 + h) - f(lt0 + h, la0 - h) - f(lt0 - h, la0 + h) + f(lt0 - h, la0 - h)
    ) / (4 * h * h)
    return out


def information_se(places: list[PlaceData], theta: float, alpha: float, cvals: np.ndarray):
    """(log-SE of θ, log-SE of α, their correlation) from the observed information at (θ, α): the inverse of
    minus `loglik_hessian`. At the maximum this is the usual large-sample covariance of (log θ̂, log α̂)."""
    cov = np.linalg.inv(-loglik_hessian(places, theta, alpha, cvals))
    se = np.sqrt(np.diag(cov))
    return float(se[0]), float(se[1]), float(cov[0, 1] / (se[0] * se[1]))


def predict_place(pl: PlaceData, fit: Fit3, draws: int = 20_000, seed: int = 0) -> np.ndarray:
    """Predictive counts (draws × years) for a place not in the fit: log θ normal from the interval, a new
    u ~ Gamma(mean 1, variance α), one blank-field combination, Poisson counts per year."""
    rng = np.random.default_rng(seed)
    theta = np.exp(rng.normal(math.log(fit.theta), fit.log_se, size=draws))
    u = rng.gamma(1 / fit.alpha, fit.alpha, size=draws) if fit.alpha > 0 else np.ones(draws)
    ks = pl.k(_cvals(fit.m_owner, fit.m_other))
    combo = rng.choice(len(pl.w), size=draws, p=pl.w / pl.w.sum())
    return rng.poisson((theta * u)[:, None] * ks[combo])


def predict_places(places: list[PlaceData], fit: Fit3, draws: int = 20_000, seed: int = 0) -> dict:
    """Joint predictive counts for places summed together (D-040): {geoid: draws × years}. One θ per draw,
    shared by every place (drawn first, as in `predict_place`, so a seed gives the same θ draws in every
    refit); an independent u and blank-field combination per place, from a stream keyed by (seed, geoid), so a
    place draws alike whichever places it is predicted with."""
    import zlib

    rng = np.random.default_rng(seed)
    theta = np.exp(rng.normal(math.log(fit.theta), fit.log_se, size=draws))
    cv = _cvals(fit.m_owner, fit.m_other)
    out = {}
    for pl in places:
        rng = np.random.default_rng([seed, zlib.crc32(pl.geoid.encode())])
        u = rng.gamma(1 / fit.alpha, fit.alpha, size=draws) if fit.alpha > 0 else np.ones(draws)
        combo = rng.choice(len(pl.w), size=draws, p=pl.w / pl.w.sum())
        out[pl.geoid] = rng.poisson((theta * u)[:, None] * pl.k(cv)[combo])
    return out


# ---------------------------------------------------------------------------------------------------------
# D-043: a state multiplier v_s, log v_s ~ N(0, τ²), for the range of θ in a state outside the fit set
# ---------------------------------------------------------------------------------------------------------

GH_NODES = 40  # Gauss-Hermite nodes for the state multiplier (pre-registered)
TAU_RANGE = (0.0, 2.5)  # τ's search range; an interval reaching 2.5 is "not estimable"


def gh_log_nodes(tau: float, n: int = GH_NODES) -> tuple[np.ndarray, np.ndarray]:
    """Nodes x_j for log v and log weights, Σ exp(logw) = 1, so Σ_j w_j f(x_j) ≈ E f(X), X ~ N(0, τ²).

    By hand, n = 2: Hermite nodes ±1/√2 with weights √π/2 each, so x = ±τ, w = 1/2: E X² = τ², exact."""
    if tau <= 0:
        return np.zeros(1), np.zeros(1)
    z, w = np.polynomial.hermite.hermgauss(n)
    return math.sqrt(2.0) * tau * z, np.log(w / math.sqrt(math.pi))


@dataclass(frozen=True)
class StateTerms:
    """Every place's blank-field combinations as flat rows, sorted by state then place, with what the frailty
    likelihood needs at any scale t = θ v: a = Σ_t y log k − log y! (−inf where k = 0 and y > 0), K = Σ_t k,
    Y = Σ_t y, and the combination's log weight. `place_start` / `state_start` index the first row of each
    place and the first place of each state (for reduceat)."""

    states: tuple[str, ...]
    a: np.ndarray
    big_k: np.ndarray
    big_y: np.ndarray
    log_w: np.ndarray
    place_start: np.ndarray
    state_start: np.ndarray
    place_y: np.ndarray


def state_terms(places: list[PlaceData], cvals: np.ndarray) -> StateTerms:
    order = sorted(range(len(places)), key=lambda i: places[i].state)  # stable: places keep their order
    a, big_k, big_y, log_w, place_start, state_start, place_y, states = [], [], [], [], [], [], [], []
    for i in order:
        pl = places[i]
        if not states or states[-1] != pl.state:
            states.append(pl.state)
            state_start.append(len(place_start))
        place_start.append(len(a))
        place_y.append(float(pl.y.sum()))
        lf = pl.log_fact
        for w, k in zip(pl.w, pl.k(cvals), strict=True):
            if w <= 0:
                continue
            bad = np.any((k <= 0) & (pl.y > 0))
            safe = np.where(k > 0, k, 1.0)
            a.append(-math.inf if bad else float(np.sum(np.where(k > 0, pl.y * np.log(safe), 0.0))) - lf)
            big_k.append(float(k.sum()))
            big_y.append(float(pl.y.sum()))
            log_w.append(math.log(w))
    f = np.asarray
    return StateTerms(tuple(states), f(a), f(big_k), f(big_y), f(log_w), f(place_start), f(state_start),
                      f(place_y))  # fmt: skip


def _reduce_logsumexp(x: np.ndarray, starts: np.ndarray) -> np.ndarray:
    """log Σ exp over row groups (rows sorted, groups beginning at `starts`), for every column of x."""
    top = np.maximum.reduceat(x, starts, axis=0)
    safe = np.where(np.isfinite(top), top, 0.0)
    idx = np.repeat(np.arange(len(starts)), np.diff(np.append(starts, len(x))))
    with np.errstate(divide="ignore"):
        return safe + np.log(np.add.reduceat(np.exp(x - safe[idx]), starts, axis=0))


def state_loglik_curves(terms: StateTerms, scales: np.ndarray, alpha: float) -> np.ndarray:
    """log P(state s's counts | θ v = scale_j), shape (states, len(scales)): place effects u ~ Gamma(1, α)
    and blank-field combinations integrated as in `frailty_loglik`, places independent given the scale."""
    t = np.asarray(scales, dtype=float)[None, :]
    k, y = terms.big_k[:, None], terms.big_y[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        head = terms.a[:, None] + np.where(y > 0, y * np.log(t), 0.0)
        if alpha <= 1e-8:
            ll = head - t * k
        else:
            r = 1.0 / alpha
            lg = _lgamma(terms.big_y + r)[:, None] - math.lgamma(r)
            ll = head + lg + r * math.log(r) - (y + r) * np.log(r + t * k)
    ll = np.where(np.isfinite(terms.a)[:, None], ll, -np.inf)
    per_place = _reduce_logsumexp(ll + terms.log_w[:, None], terms.place_start)
    return np.add.reduceat(per_place, terms.state_start, axis=0)


def state_loglik(terms: StateTerms, theta: float, alpha: float, tau: float) -> float:
    """Σ_s log ∫ P(y_s | θ v) φ(log v; 0, τ) d log v, Gauss-Hermite (D-043); τ = 0 is `frailty_loglik`."""
    x, logw = gh_log_nodes(tau)
    curves = state_loglik_curves(terms, theta * np.exp(x), alpha)
    return float(np.sum(np.logaddexp.reduce(curves + logw[None, :], axis=1)))


@dataclass(frozen=True)
class StateFit:
    theta: float  # the median state's rate
    low: float
    high: float
    alpha: float
    tau: float
    tau_low: float
    tau_high: float
    loglik: float
    m_owner: float
    m_other: float
    states: tuple[str, ...]
    n_places: int
    n_years: int

    @property
    def log_se(self) -> float:
        return (math.log(self.high) - math.log(self.low)) / (2 * Z_95)

    @property
    def tau_estimable(self) -> bool:
        return self.tau_high < TAU_RANGE[1] - 0.01


def _best_alpha(f) -> tuple[float, float]:
    """max over α of f(α), α = 0 (Poisson) included -> (alpha, value)."""
    la, best = _golden_max(lambda la: f(math.exp(la)), *LOG_ALPHA, tol=1e-5)
    pois = f(0.0)
    return (0.0, pois) if pois >= best else (math.exp(la), best)


def _at_tau(terms: StateTerms, tau: float, log_theta_range=(-14.0, 0.0)) -> tuple[float, float, float]:
    """max over θ and α at a given τ -> (log θ, α, loglik)."""

    def f(lt):
        return _best_alpha(lambda a: state_loglik(terms, math.exp(lt), a, tau))

    lt, ll = _golden_max(lambda lt: f(lt)[1], *log_theta_range, tol=1e-5)
    return lt, f(lt)[0], ll


def fit_state_effect(
    places: list[PlaceData], m_owner: float, m_other: float, log_theta_range=(-14.0, 0.0)
) -> StateFit:
    """Maximum likelihood (θ, α, τ) with the rule shares held at (m_owner, m_other) (D-043); 90% profile
    intervals for θ (α, τ maximized) and τ (θ, α maximized), χ² 1 df."""
    terms = state_terms(places, _cvals(m_owner, m_other))

    def at_tau(tau: float) -> tuple[float, float, float]:
        return _at_tau(terms, tau, log_theta_range)

    def at_theta(lt: float) -> float:
        return _golden_max(
            lambda tau: _best_alpha(lambda a: state_loglik(terms, math.exp(lt), a, tau))[1],
            *TAU_RANGE,
            tol=1e-4,
        )[1]

    tau_hat, _ = _golden_max(lambda tau: at_tau(tau)[2], *TAU_RANGE, tol=1e-4)
    if at_tau(0.0)[2] >= at_tau(tau_hat)[2]:
        tau_hat = 0.0
    lt_hat, alpha, ll_hat = at_tau(tau_hat)

    def edge(f, inside: float, outside: float, iters: int = 30) -> float:
        """Bisection for 2(ll_hat − f) = χ² between `inside` (the estimate) and `outside` (a bound); returns
        the bound if the profile never drops that far."""
        if 2 * (ll_hat - f(outside)) <= CHI2_90:
            return outside
        lo, hi = inside, outside
        for _ in range(iters):
            mid = (lo + hi) / 2
            if 2 * (ll_hat - f(mid)) > CHI2_90:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    def tau_prof(tau):
        return at_tau(tau)[2]

    tau_low = 0.0 if tau_hat == 0 else edge(tau_prof, tau_hat, TAU_RANGE[0])
    tau_high = edge(tau_prof, tau_hat, TAU_RANGE[1])
    low = edge(at_theta, lt_hat, log_theta_range[0])
    high = edge(at_theta, lt_hat, log_theta_range[1])
    n_years = int(sum(len(p.y) for p in places))
    return StateFit(math.exp(lt_hat), math.exp(low), math.exp(high), alpha, tau_hat, tau_low, tau_high,
                    ll_hat, m_owner, m_other, terms.states, len(places), n_years)  # fmt: skip


def state_multipliers(places: list[PlaceData], fit: StateFit, grid: int = 801) -> dict[str, tuple]:
    """Each fitted state's v_s given the fit (D-043 check K3): posterior median and 90% interval of v_s on a
    fine grid of log v, prior N(0, τ̂²). With τ̂ = 0 every v_s is 1."""
    terms = state_terms(places, _cvals(fit.m_owner, fit.m_other))
    if fit.tau <= 0:
        return {s: (1.0, 1.0, 1.0) for s in terms.states}
    x = np.linspace(-5 * fit.tau, 5 * fit.tau, grid)
    curves = state_loglik_curves(terms, fit.theta * np.exp(x), fit.alpha) - 0.5 * (x / fit.tau) ** 2
    out = {}
    for s, c in zip(terms.states, curves, strict=True):
        p = np.exp(c - c.max())
        cdf = np.cumsum(p) / p.sum()
        out[s] = tuple(float(np.exp(np.interp(q, cdf, x))) for q in (0.5, 0.05, 0.95))
    return out


TAU_GRID = tuple(round(0.05 * i, 2) for i in range(51))  # D-044: τ = 0, 0.05, ..., 2.5


def tau_profile(places: list[PlaceData], m_owner: float, m_other: float, grid=TAU_GRID) -> np.ndarray:
    """τ's profile log-likelihood on `grid` (θ and α maximized at each τ, rule shares held), D-044."""
    terms = state_terms(places, _cvals(m_owner, m_other))
    return np.array([_at_tau(terms, float(t))[2] for t in grid])


def tau_probabilities(loglik) -> np.ndarray:
    """Grid probabilities ∝ exp(profile log-likelihood): a flat prior over the grid (D-044).

    By hand, log-likelihoods (0, −log 2, −log 4): probabilities (4, 2, 1) / 7."""
    ll = np.asarray(loglik, dtype=float)
    w = np.exp(ll - ll.max())
    return w / w.sum()


def draw_tau(grid, probs, n: int, rng) -> np.ndarray:
    """n values of τ from the grid distribution (D-044 main)."""
    return rng.choice(np.asarray(grid, dtype=float), size=n, p=np.asarray(probs, dtype=float))


def draw_tau_half_normal(tau_high: float, n: int, rng) -> np.ndarray:
    """D-044 sensitivity T1: |N(0, σ²)| with its 90th percentile at τ's upper bound, σ = upper / 1.645."""
    return np.abs(rng.normal(0.0, tau_high / Z_95, size=n))


def predict_unseen_state(
    places: list[PlaceData], fit: StateFit, draws: int = 20_000, seed: int = 0, taus=None
) -> dict:
    """Joint predictive counts for a state outside the fit set (D-043): {geoid: draws × years}. Per draw, θ
    from its interval and one state multiplier exp(τ z), z ~ N(0, 1), shared by every place (median kept at
    θ); then each place's own u and blank-field combination as in `predict_places`. `taus`, one per draw
    (D-044), replaces the fixed τ̂."""
    import zlib

    rng = np.random.default_rng(seed)
    theta = np.exp(rng.normal(math.log(fit.theta), fit.log_se, size=draws))
    tau = fit.tau if taus is None else np.asarray(taus, dtype=float)
    v = np.exp(tau * rng.standard_normal(draws))
    cv = _cvals(fit.m_owner, fit.m_other)
    out = {}
    for pl in places:
        rng = np.random.default_rng([seed, zlib.crc32(pl.geoid.encode())])
        u = rng.gamma(1 / fit.alpha, fit.alpha, size=draws) if fit.alpha > 0 else np.ones(draws)
        combo = rng.choice(len(pl.w), size=draws, p=pl.w / pl.w.sum())
        out[pl.geoid] = rng.poisson((theta * v * u)[:, None] * pl.k(cv)[combo])
    return out


def place_data(state: str, store, geoids, years, params=None, counts=None) -> list[PlaceData]:
    """`PlaceData` per place with checkable years (a coded rule in force by 1 July, ADU-flagging permits).

    Uses the scenario's rule reading: `restriction_fields` with citywide parking reforms filling a blank
    parking field (`with_parking`), coverage from `scenarios.adu.coverage_map`, field probabilities from every
    state's coded rules (`field_probabilities`). Holdout-filtered tables only.
    """
    import itertools

    import pandas as pd

    from lotline.config import load_params, load_state
    from lotline.model.scenarios import adu

    rows = place_years(state, store, geoids, years, params, counts=counts)
    if rows.empty:
        return []
    central = {k: v.value for k, v in load_params("adu").items()}
    every = pd.concat([adu.load_reforms(st).assign(state=st) for st in adu.REFORM_STATES], ignore_index=True)
    fcounts = adu.field_restrict_counts(every, pd.Timestamp.today().normalize())
    fp = adu.field_probabilities(fcounts, state, int(central["adu_rule_min_coded"]))
    all_reforms = adu.load_reforms(state)
    reforms = all_reforms[(all_reforms["theme"] == "adu") & (all_reforms["status"] == "in_force")]
    cov = adu.coverage_map(state, store, reforms, central).set_index("reform_id")["coverage"].to_dict()
    p = adu.central_params() if params is None else params
    fips = load_state(state).fips
    out = []
    for (g, name), d in rows.groupby(["geoid", "name"], sort=False):
        d = d.sort_values("year")
        mine = reforms[reforms["jurisdiction_geoid"].isin([g, fips])]  # local rules and state laws
        per_year = []
        unknown_all: list[str] = []
        for y in d["year"]:
            mid = pd.Timestamp(f"{int(y)}-07-01")
            live = []
            for r in mine.itertuples():
                if not (r.effective_date <= mid and (pd.isna(r.end_date) or r.end_date > mid)):
                    continue
                rubric = adu.with_parking(adu._resolved(reforms, r.reform_id), all_reforms, g, mid)
                if adu._no_adus(rubric):
                    continue
                failed, unknown = adu.restriction_fields(rubric)
                ramp = float(hazard_ramp((mid - r.effective_date).days / 365.25, p))
                live.append((set(failed), list(unknown), cov.get(r.reform_id, 1.0) * ramp))
                unknown_all += [u for u in unknown if u not in unknown_all]
            per_year.append(live)
        combos = list(itertools.product((False, True), repeat=len(unknown_all)))
        w = np.array(
            [
                np.prod([fp[f] if b else 1 - fp[f] for f, b in zip(unknown_all, c, strict=True)])
                for c in combos
            ]
        )
        n_r = max(len(lv) for lv in per_year)
        types = np.zeros((len(combos), len(per_year), n_r), dtype=int)
        cr = np.zeros((len(per_year), n_r))
        for t, live in enumerate(per_year):
            for r_i, (failed, unknown, a) in enumerate(live):
                cr[t, r_i] = a
                for c_i, c in enumerate(combos):
                    hit = {f for f, b in zip(unknown_all, c, strict=True) if b and f in unknown}
                    types[c_i, t, r_i] = adu.TYPES.index(adu.type_of(failed | hit))
        out.append(
            PlaceData(
                state,
                g,
                name,
                d["year"].to_numpy(),
                d["adu_permits"].to_numpy(dtype=float),
                (d["eligible_parcels"] * d["h1"] * d["report_rate"]).to_numpy(dtype=float),
                types,
                cr,
                w,
            )
        )
    return out


def hazard_ramp(age: float, params) -> float:
    from lotline.model import hazard

    return float(hazard.ramp(age, params["adu_ramp_half_years"], params["adu_ramp_slope_years"]))
