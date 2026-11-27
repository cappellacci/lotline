"""Missing-middle D-024 inference and checks: randomization inference, added homes, the reported checks
(leads, placebo dates, outcomes, inside, leave one out) and the out-of-sample prediction.

Part of `estimate_mm`, split by method step (modularity step 3); `estimate_mm` re-exports every name.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .estimate import BIN_NAMES, LEADS, bootstrap, estimate, overall, summary, year_code
from .panel import EVENT_BINS, MODIFIERS, event_bin

# ---------------------------------------------------------------------------------------------------------
# Randomization inference (D-024): treatment packages reassigned within state and size band
# ---------------------------------------------------------------------------------------------------------

PACKAGE = ("T", "dose", "p_by_right", *MODIFIERS)


def reassign(panel: pd.DataFrame, rng: np.random.Generator, pool: set | None = None) -> pd.DataFrame:
    """One reassignment: each treated place's package (adoption year, its calendar-year dose path and its
    modifiers) moves to a place drawn without replacement from the treated and untreated places in the same
    state and size band (`pool`: the places eligible to receive one, default all). Places not drawn get no
    treatment."""
    p = panel.copy()
    places = p.drop_duplicates("place")[["place", "state", "band", "T"]]
    if pool is not None:
        places = places[places["place"].isin(pool) | places["T"].notna()]
    treated = places[places["T"].notna()]
    target: dict = {}
    for (st, band), grp in treated.groupby(["state", "band"]):
        cands = places[(places["state"] == st) & (places["band"] == band)]["place"].to_numpy()
        chosen = rng.choice(cands, size=len(grp), replace=False)
        for src, dst in zip(rng.permutation(grp["place"].to_numpy()), chosen, strict=True):
            target[dst] = src
    by_place_year = panel.set_index(["place", "year"])[list(PACKAGE)]
    for c in PACKAGE:
        p[c] = np.nan if c != "dose" else 0.0
    p["p_by_right"] = 0.0
    for dst, src in target.items():
        rows = p["place"] == dst
        vals = by_place_year.loc[src].reindex(p.loc[rows, "year"].to_numpy())
        for c in PACKAGE:
            p.loc[rows, c] = vals[c].to_numpy()
    return p


def _ri_one(args):
    panel, seed, i, pool, method, kw = args
    from lotline.calibrate.adu.estimate_adu import EstimationError

    try:
        return overall(
            estimate(reassign(panel, np.random.default_rng([seed, i]), pool=pool), method=method, **kw)
        )
    except (EstimationError, np.linalg.LinAlgError, ValueError):  # a fit that cannot be estimated
        return None


def randomization_inference(panel, permutations=999, seed=0, method="ppml", workers=1, **kw):
    """(overall effect, p, permuted effects, failed): p = share of reassignments (`reassign`; receiving places
    are those with any 2-4 unit home, so a fixed-effects fit can see them) whose |overall effect| is at least
    the observed one. Reassignment i uses its own generator (seed, i), so results don't depend on `workers`
    (processes). A reassignment the fit cannot estimate is skipped and counted in `failed`."""
    att = overall(estimate(panel, method=method, **kw))
    pos = set(panel.loc[panel["y"].fillna(0) > 0, "place"])
    jobs = [(panel, seed, i, pos, method, kw) for i in range(permutations)]
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=workers) as ex:
            res = list(ex.map(_ri_one, jobs, chunksize=max(1, permutations // (4 * workers))))
    else:
        res = [_ri_one(j) for j in jobs]
    failed = sum(r is None for r in res)
    dist = np.array([r for r in res if r is not None], dtype=float)
    dist = dist[~np.isnan(dist)]
    p = float(np.mean(np.abs(dist) >= abs(att))) if len(dist) else np.nan
    return att, p, dist, failed


def added_homes(est_, boot: pd.DataFrame | None = None, level: float = 0.90) -> pd.DataFrame:
    """Homes the rules added in the treated places' post-adoption years: fitted mean minus the mean with the
    treatment terms (β, θ, ρ) switched off, per place, and per 1,000 eligible parcels a year. Interval:
    each bootstrap draw's treatment terms applied to the untreated means, μ0 (e^(X b*) − 1), with place and
    year effects held at the estimate. Columns: place, name, years, added, low, high,
    per_1000_parcels_year."""
    fit, d, p = est_.fit, est_.design, est_.panel
    X = d.X[fit.keep][:, [d.names.index(n) for n in fit.names]]
    treat = [i for i, n in enumerate(fit.names) if n.startswith(("beta_", "theta_", "rho"))]
    kp = p[fit.keep].reset_index(drop=True)
    post = (kp["T"].notna() & (kp["year"] >= kp["T"])).to_numpy()
    lin = X[:, treat] @ fit.coef[treat]
    mu0 = fit.mu * np.exp(-lin)
    rows = []
    a = (1 - level) / 2
    draws = None
    if boot is not None:
        B = boot[[fit.names[i] for i in treat]].to_numpy()
        draws = mu0[None, :] * (np.exp(B @ X[:, treat].T) - 1.0)
    for place, g in kp[post].groupby("place"):
        on = post & (kp["place"] == place).to_numpy()
        add = float(np.sum(fit.mu[on] - mu0[on]))
        lo = hi = np.nan
        if draws is not None:
            tot = draws[:, on].sum(axis=1)
            dev_lo, dev_hi = np.quantile(tot - add, [a, 1 - a])
            lo, hi = add - dev_hi, add - dev_lo
        n = int(on.sum())
        name = g["name"].iloc[0] if "name" in g else place
        per = add / float(g["eligible"].mean()) / n * 1000
        rows.append({"place": place, "name": name, "years": n, "added": add, "low": lo, "high": hi,
                     "per_1000_parcels_year": per})  # fmt: skip
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Checks (D-024, all reported; pass rules fixed in the entry)
# ---------------------------------------------------------------------------------------------------------


def _interval(est_, draws, seed, term="att"):
    s, _ = summary(est_, draws=draws, seed=seed)
    s = s.set_index("term")
    return s.loc[term, "estimate"], s.loc[term, "low"], s.loc[term, "high"]


def _safe(name, fn):
    """Run one check; a fit that fails becomes a failed check with the reason, never a crash."""
    from lotline.calibrate.adu.estimate_adu import EstimationError

    try:
        return fn()
    except (EstimationError, np.linalg.LinAlgError, KeyError, ValueError) as err:
        return {"check": name, "pass": False, "note": f"could not be estimated: {err}"}


def check_leads(panel, draws=999, seed=0, method="ppml", **kw) -> dict:
    """1. Leads k = −3…−1 jointly 0 at the 10% level (pass: bootstrap Wald p >= 0.10)."""
    from lotline.calibrate.adu.estimate_adu import joint_wald

    def run():
        e = estimate(panel, method=method, leads=LEADS, **kw)
        W, p = joint_wald(bootstrap(e, draws=draws, seed=seed), e, [f"lead_{-k}" for k in LEADS])
        return {"check": "pre-trend leads", "statistic": W, "p": p, "pass": bool(p >= 0.10)}

    return _safe("pre-trend leads", run)


def check_placebo_dates(panel, shift=2, draws=999, seed=0, method="ppml", **kw) -> dict:
    """2. Adoption moved `shift` years early, pre-adoption years only, full dose: 90% interval contains 0."""
    name = f"placebo dates (−{shift} years)"

    def run():
        p = panel[panel["T"].isna() | (panel["year"] < panel["T"])].copy()
        p["T"] = p["T"] - shift
        p.loc[p["T"].notna(), "dose"] = 1.0
        est_, lo, hi = _interval(estimate(p, method=method, **kw), draws, seed)
        return {"check": name, "estimate": est_, "low": lo, "high": hi, "pass": bool(lo <= 0 <= hi)}

    return _safe(name, run)


def check_outcome(panel, column, name, draws=999, seed=0, rule=True, method="ppml", **kw) -> dict:
    """3./4. Another outcome (5+ unit homes: placebo, pass if the 90% interval contains 0; 1-unit homes:
    substitution, reported with no pass rule)."""

    def run():
        p = panel.assign(y=panel[column].round())
        est_, lo, hi = _interval(estimate(p, method=method, **kw), draws, seed)
        return {
            "check": name,
            "estimate": est_,
            "low": lo,
            "high": hi,
            "pass": bool(lo <= 0 <= hi) if rule else None,
        }

    return _safe(name, run)


def check_inside(panel, main: pd.DataFrame, name, terms=("att",), draws=999, seed=0, method="ppml", **kw):
    """5./7. A re-fit on `panel` (a subsample): every listed term's estimate inside the main 90% interval."""

    def run():
        s, _ = summary(estimate(panel, method=method, **kw), draws=draws, seed=seed)
        s, m = s.set_index("term"), main.set_index("term")
        got = {t: float(s.loc[t, "estimate"]) for t in terms if t in s.index}
        outside = [
            t for t, v in got.items() if t in m.index and not (m.loc[t, "low"] <= v <= m.loc[t, "high"])
        ]
        return {
            "check": name,
            **{f"estimate_{t}": v for t, v in got.items()},
            "outside": outside,
            "pass": not outside,
        }

    return _safe(name, run)


def check_leave_one_out(panel, main: pd.DataFrame, groups: Mapping[str, Sequence[str]], method="ppml", **kw):
    """6. Leaving out each treated place (and each named group): the overall effect stays inside the main
    90% interval."""
    m = main.set_index("term").loc["att"]
    moved, rows = [], []
    for label, places in groups.items():
        try:
            att = overall(estimate(panel[~panel["place"].isin(places)], method=method, **kw))
        except Exception as err:  # noqa: BLE001 (reported, not raised)
            att = np.nan
            rows.append({"left_out": label, "att": np.nan, "note": str(err)})
            moved.append(label)
            continue
        rows.append({"left_out": label, "att": att})
        if not (m["low"] <= att <= m["high"]):
            moved.append(label)
    return {"check": "leave one treated place out", "moved": moved, "pass": not moved}, pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Out-of-sample tests (D-024 A and B)
# ---------------------------------------------------------------------------------------------------------


def transport_predict(est_, boot, target: pd.DataFrame, draws=4000, seed=0, widening=1.0) -> pd.DataFrame:
    """Predicted 2-4 unit homes per post-adoption year for treated places left out of the fit.

    Per target place and draw: η_t = α + γ_{s,t} + log(eligible) + β_b(t) × dose + Σ θ_m z_m + ρ (r − r̄) +
    δ adu, with coefficient draws from the bootstrap, γ from the fit (the target's state keeps its year
    effects from its comparison places), z_m on the fit's treated-place scale, and α from the place's own
    pre-adoption years given γ and the offset, with its sampling error (variance ≈ (1 + κ·mean) / pre-period
    homes); a place with none draws α from the fitted places. Places outside the fitted modifier range get
    log-normal noise with sd = `widening` × summed log distance outside the range. Counts are Poisson-gamma
    with the fit's overdispersion κ. Returns place, name, year, observed, mean, p05, p10, p90, p95,
    outside_range, with a 'total' row per place.
    """
    from lotline.calibrate.adu.estimate_adu import (
        MAX_YEARLY_RATE,
        EstimationError,
        modifier_scale,
        overdispersion,
    )

    rng = np.random.default_rng(seed)
    f, fp = est_.fit, est_.panel
    gam = dict(zip(f.years, f.gamma, strict=True))
    kappa = overdispersion(est_)
    treated = fp[fp["T"].notna()].drop_duplicates("place")
    mods = [n.replace("theta_", "") for n in f.names if n.startswith("theta_")]
    scale = {m: modifier_scale(treated, m) for m in mods}
    span = {m: (float(treated[m].min()), float(treated[m].max())) for m in mods}
    rate_ref = float(fp["rate"].mean())
    coefs = {n: boot[n].to_numpy() for n in boot.columns}
    idx = rng.integers(0, len(boot), size=draws)
    out = []
    for place, d in target[target["y"].notna()].groupby("place", sort=False):
        d = d.sort_values("year").reset_index(drop=True)
        T = d["T"].iloc[0]
        e = d["year"].to_numpy() - T
        post = e >= 0
        g = np.array([gam.get(c, np.nan) for c in year_code(d)])
        if np.isnan(g).any():
            raise EstimationError(f"transport for {place}: no year effect for some of its state-years")
        off = np.log(d["eligible"].to_numpy(dtype=float))
        dist = 0.0
        for m in mods:
            x, (lo, hi) = d[m].iloc[0], span[m]
            if np.isnan(x):
                continue
            xv, lov, hiv = (
                (x, lo, hi)
                if m == "log_value"
                else (np.log(max(x, 1e-12)), np.log(max(lo, 1e-12)), np.log(max(hi, 1e-12)))
            )
            dist += max(0.0, lov - xv, xv - hiv)
        pre = ~post
        y_pre = float(d.loc[pre, "y"].sum())
        if y_pre > 0:
            a_hat = np.log(y_pre / np.sum(np.exp(off[pre] + g[pre] + _delta(coefs, None, d.loc[pre, "adu"]))))
            a_draw = a_hat + rng.normal(0.0, np.sqrt((1 + kappa * y_pre / pre.sum()) / y_pre), size=draws)
        else:
            a_draw = rng.choice(np.asarray(f.alpha), size=draws)
        eta = a_draw[:, None] + g[None, :] + off[None, :]
        for (lo, hi), name in zip(EVENT_BINS, BIN_NAMES, strict=True):
            on = post & (e >= lo) & (e <= (np.inf if hi is None else hi))
            if name in coefs:
                eta[:, on] += coefs[name][idx][:, None] * d.loc[on, "dose"].to_numpy()[None, :]
        for m in mods:
            c, sd = scale[m]
            z = 0.0 if np.isnan(d[m].iloc[0]) else (d[m].iloc[0] - c) / sd
            eta[:, post] += coefs[f"theta_{m}"][idx][:, None] * z
        if "rho" in coefs:
            eta[:, post] += coefs["rho"][idx][:, None] * (d.loc[post, "rate"].to_numpy() - rate_ref)[None, :]
        eta += _delta(coefs, idx, d["adu"])
        if not np.all(np.isfinite(eta)) or np.max(eta - off[None, :]) > np.log(MAX_YEARLY_RATE):
            raise EstimationError(
                f"transport for {place}: predicted rate beyond {MAX_YEARLY_RATE:.0%} a year"
            )
        s = widening * dist
        mu = np.exp(eta + s * rng.standard_normal((draws, 1)) - s**2 / 2)
        lam = rng.gamma(1 / kappa, mu * kappa) if kappa > 0 else mu
        sims = rng.poisson(lam)[:, post]
        dpost = d[post]
        for t, r in enumerate(dpost.itertuples()):
            col = sims[:, t]
            out.append(_pred_row(place, r.name, int(r.year), float(r.y), col, dist))
        out.append(
            _pred_row(place, d["name"].iloc[0], "total", float(dpost["y"].sum()), sims.sum(axis=1), dist)
        )
    return pd.DataFrame(out)


def _delta(coefs, idx, adu: pd.Series):
    if "delta" not in coefs:
        return 0.0
    v = adu.to_numpy(dtype=float)
    if idx is None:
        return float(np.median(coefs["delta"])) * v
    return coefs["delta"][idx][:, None] * v[None, :]


def _pred_row(place, name, year, observed, col, dist) -> dict:
    q = np.quantile(col, [0.05, 0.10, 0.90, 0.95])
    return {"place": place, "name": name, "year": year, "observed": observed, "mean": float(col.mean()),
            "p05": q[0], "p10": q[1], "p90": q[2], "p95": q[3], "outside_range": dist}  # fmt: skip


# ---------------------------------------------------------------------------------------------------------
# Robustness: the Borusyak imputation estimator
# ---------------------------------------------------------------------------------------------------------


def imputation_effects(panel: pd.DataFrame) -> dict[str, float]:
    """Borusyak, Jaravel & Spiess (2024) imputation, in Poisson form: fit place and state × year effects (and
    δ) on untreated place-years only (never treated, or before adoption), impute each treated place-year's
    untreated mean μ0, and report log(Σ y / Σ μ0) per event-time bin and overall (same scale as β and att;
    the dose is not used). Treated places without untreated years with homes are left out."""
    from lotline.calibrate.adu.estimate_adu import ppml

    p = panel[panel["y"].notna()].reset_index(drop=True)
    e = p["year"] - p["T"]
    untreated = (p["T"].isna() | (e < 0)).to_numpy()
    codes = year_code(p)
    adu_x = p[["adu"]].to_numpy(dtype=float)
    off = np.log(p["eligible"].to_numpy(dtype=float))
    fit = ppml(p.loc[untreated, "y"], adu_x[untreated], off[untreated], p.loc[untreated, "place"],
               codes[untreated], ["delta"])  # fmt: skip
    alpha = dict(zip(np.unique(p.loc[untreated, "place"][fit.keep]), fit.alpha, strict=True))
    gam = dict(zip(fit.years, fit.gamma, strict=True))
    d = fit.coef_of("delta") if "delta" in fit.names else 0.0
    tr = p[~untreated].copy()
    tr["a"] = tr["place"].map(alpha)
    tr["g"] = [gam.get(c, np.nan) for c in codes[~untreated]]
    tr = tr.dropna(subset=["a", "g"])
    tr["mu0"] = np.exp(np.log(tr["eligible"]) + tr["a"] + tr["g"] + d * tr["adu"])
    tr["bin"] = (tr["year"] - tr["T"]).map(event_bin)
    bin_name = dict(zip(("k0_1", "k2_3", "k4p"), BIN_NAMES, strict=True))
    out = {bin_name[b]: float(np.log(g["y"].sum() / g["mu0"].sum())) for b, g in tr.groupby("bin")}
    out["att"] = float(np.log(tr["y"].sum() / tr["mu0"].sum())) if len(tr) else np.nan
    out["places"] = int(tr["place"].nunique())
    return out
