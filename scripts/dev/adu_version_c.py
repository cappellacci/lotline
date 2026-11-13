#!/usr/bin/env python3
"""ADU version C (exploratory, not adopted): separate rule-detail effects, scored as D-079 scores Form A.

The test is fixed in `reports/adu-version-c-2026-11/PLAN.md`, written before any fit. It runs on the branch
`ws/adu-version-c`, where `apply_adu_rules_proposed_2026_11.py` has put PR #417's proposed rule rows in
config/reforms/*.csv. Three runs, one process:

1. **A′**: Form A (fit3) and Form B on the new rows, scored exactly as `adu_joint_refit` (tiers, tests A-C).
2. **C**: Form A's likelihood with c = exp(β_br·[not by right] + β_p1·[1 space] + β_p2·[2+ spaces] +
   β_x·[other restriction]) × (lots / median lots)^β_s; rule slopes ≤ 0, size free. Scored the same way
   (test C not run: the scenario engine has no version C). Form B's fits are reused from run 1.
3. **C, sensitivity**: rows tagged `[detached-conditional]` read as not by right.

Version C rides on the scoring code unchanged: its parameters travel in the `cvals` vector (`_cvals` returns
it when handed a tuple) and `PlaceData.k` reads the vector when it is longer than Form A's five values.

    cd ~/Engineering/lotline   # .env lives here
    PYTHONPATH=<worktree>/src .venv/bin/python <worktree>/scripts/dev/adu_version_c.py --out <dir> --workers 7
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adu_joint_refit as ajr  # noqa: E402

from lotline.io import DataStore, offline  # noqa: E402
from lotline.model import calibrate_adu as cal  # noqa: E402
from lotline.model import calibrate_shape as shp  # noqa: E402
from lotline.model import joint_refit as jr  # noqa: E402
from lotline.model.scenarios import adu  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROPOSED = ROOT / "docs/research/ordinances/adu-fit-rules-proposed-2026-11.csv"
OTHER = {cal.DETACHED, "adu_max_sqft"}  # "any other restriction"
NAMES = ("not by right", "1 parking space", "2+ parking spaces", "other restriction", "size (log lots)")
log = ajr.log

# ---------------------------------------------------------------------------------------------------------
# The parameter vector and PlaceData.k
# ---------------------------------------------------------------------------------------------------------
# V = [0, 1, 1, 1, 1, b_br, b_p1, b_p2, b_x, b_s, c_part, log_ref]: Form A's five type values (owner: no
# effect, so every allowed type is 1 for borrowed tier-0 rules except other/both, which take c_part), then C.

_orig_cvals = cal._cvals
_orig_k = cal.PlaceData.k


def _cvals(m_owner, m_other):
    if isinstance(m_owner, tuple):
        return np.asarray(m_owner, dtype=float)
    return _orig_cvals(m_owner, m_other)


def _size(pl, v) -> float:
    lots = float(np.nanmean(pl.extra["parcels"]))
    return math.exp(v[9] * (math.log(lots) - v[11]))


def rule_c(pl, v) -> np.ndarray:
    """(C, T, R) c per rule under version C's slopes."""
    ex = pl.extra
    eta = (
        v[5] * ex["no_by_right"]
        + v[6] * (ex["park"] == 1)
        + v[7] * (ex["park"] >= 2)
        + v[8] * ex["rest"]
    )
    return np.exp(eta)


def _k(self, cvals, m_d: float = 1.0):
    cvals = np.asarray(cvals, dtype=float)
    if len(cvals) <= 5:
        return _orig_k(self, cvals, m_d)
    ex = self.extra or {}
    if "park" in ex and "no_by_right" in ex and ex["park"].shape == self.types.shape:
        c = rule_c(self, cvals)
    else:  # tier 0: borrowed types only
        c = np.array([0.0, 1.0, cvals[10], cvals[10], 1.0])[self.types]
    return _size(self, cvals) * self.base[None, :] * (c * self.cr[None, :, :]).max(axis=2)


cal._cvals = _cvals
cal.PlaceData.k = _k

_orig_frailty_loglik = cal.frailty_loglik


def frailty_loglik(places, theta: float, alpha: float, cvals, m_d: float = 1.0) -> float:
    """`cal.frailty_loglik` with the blank-field combinations done in one numpy call per place
    (`joint_refit._marginal`, the same formula): the new rows give 305 combinations, too slow one by one.
    Checked equal to the original on the fit set before the run (`--check`)."""
    total = 0.0
    for pl in places:
        ks = pl.k(cvals, m_d)
        keep = pl.w > 0
        per = np.log(pl.w[keep]) + jr._marginal(pl.y, theta * ks[keep], alpha, pl.log_fact)
        total += float(np.logaddexp.reduce(per))
    return total


cal.frailty_loglik = frailty_loglik


def fit3(places, grid=cal.GRID3, judgment=(0.5, 0.3), ranges=((0.2, 1.0), (0.1, 0.6)),
         log_theta_range=(-14.0, 0.0)):  # fmt: skip
    """`cal.fit3`, line for line, with one exact shortcut in θ's interval: the profile there is the max over
    candidate shares, and only the crossing of ℓ̂ − χ²/2 matters, so a candidate whose own maximum (its
    surface value) lies below that line can never move the crossing and is skipped. Same θ̂, α, m_o, m_x
    and interval as `cal.fit3` (checked against it with `--check`)."""
    gm, fl, lam = cal._golden_max, frailty_loglik, cal.LOG_ALPHA

    def best_alpha(lt, cv):
        return gm(lambda la: fl(places, math.exp(lt), math.exp(la), cv), *lam)

    def prof_theta(cv):
        return gm(lambda lt: max(best_alpha(lt, cv)[1], fl(places, math.exp(lt), 0.0, cv)), *log_theta_range)

    surface = {(mo, mx): prof_theta(cal._cvals(mo, mx)) for mo in grid for mx in grid}
    lls = {key: v[1] for key, v in surface.items()}
    top = max(lls.values())

    def interval(axis: int):
        vals = sorted({key[axis] for key in lls})
        prof = {v: max(ll for key, ll in lls.items() if key[axis] == v) for v in vals}
        inside = [v for v in vals if 2 * (top - prof[v]) <= cal.CHI2_90]
        hat = max(prof, key=prof.get)
        return hat, (min(inside), max(inside))

    (mo_hat, mo_int), (mx_hat, mx_int) = interval(0), interval(1)
    mo_est = (mo_int[1] - mo_int[0]) < (ranges[0][1] - ranges[0][0])
    mx_est = (mx_int[1] - mx_int[0]) < (ranges[1][1] - ranges[1][0])
    mos = [mo_hat] if mo_est else [judgment[0]]
    mxs = [mx_hat] if mx_est else [judgment[1]]
    if mo_est and mx_est:
        mos, mxs = list(grid), list(grid)
    elif mo_est:
        mos = list(grid)
    elif mx_est:
        mxs = list(grid)
    m_o = mo_hat if mo_est else judgment[0]
    m_x = mx_hat if mx_est else judgment[1]
    lt_hat, _ = prof_theta(cal._cvals(m_o, m_x))
    cand_keys = [(a, b) for a in mos for b in mxs]
    for key in cand_keys:  # judgment values off the grid
        if key not in lls:
            lls[key] = prof_theta(cal._cvals(*key))[1]

    def prof_over(keys, lt):
        out = -math.inf
        for key in keys:
            cv = cal._cvals(*key)
            out = max(out, best_alpha(lt, cv)[1], fl(places, math.exp(lt), 0.0, cv))
        return out

    ll_hat = prof_over(cand_keys, lt_hat)
    line = ll_hat - cal.CHI2_90 / 2
    live = [k for k in cand_keys if lls[k] >= line - 1e-6] or cand_keys

    def prof(lt):
        return prof_over(live, lt)

    la, ll_a = best_alpha(lt_hat, cal._cvals(m_o, m_x))
    alpha = math.exp(la) if ll_a > fl(places, math.exp(lt_hat), 0.0, cal._cvals(m_o, m_x)) else 0.0

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
    return cal.Fit3(math.exp(lt_hat), math.exp(low), math.exp(high), alpha, m_o, m_x, mo_int, mx_int, mo_est,
                    mx_est, ll_hat, len(places), int(sum(len(p.y) for p in places)))  # fmt: skip


_orig_fit3 = cal.fit3
cal.fit3 = fit3

# ---------------------------------------------------------------------------------------------------------
# place_data with the parking level and "other restriction" per rule (cal.place_data plus two arrays)
# ---------------------------------------------------------------------------------------------------------


def parking_level(rubric) -> int | None:
    """0, 1 or 2 (2+) extra spaces; 'depends' or a named requirement counts 1; None when blank."""
    m = rubric.get("parking_min_per_unit")
    if m is not None and pd.notna(m):
        return min(int(round(float(m))), 2)
    t = rubric.get("parking")
    t = str(t).strip().lower() if t is not None and pd.notna(t) else ""
    if t.startswith("no"):
        return 0
    if t.startswith("depends") or "requir" in t or "space" in t:
        return 1
    return None


_orig_place_data = cal.place_data


def place_data(state, store, geoids, years, params=None, counts=None, split_detached=False,
               undercount="table", drop=(), require_counts=True):  # fmt: skip
    """`cal.place_data`, then `extra["park"]` and `extra["rest"]` (C, T, R) rebuilt from the same rules in
    the same order (the loop below mirrors `cal.place_data`'s)."""
    out = _orig_place_data(state, store, geoids, years, params, counts, split_detached, undercount, drop,
                           require_counts)  # fmt: skip
    if not out:
        return out
    all_reforms = adu.load_reforms(state)
    reforms = all_reforms[(all_reforms["theme"] == "adu") & (all_reforms["status"] == "in_force")]
    from lotline.config import load_state

    fips = load_state(state).fips
    for pl in out:
        mine = reforms[reforms["jurisdiction_geoid"].isin([pl.geoid, fips])]
        per_year, unknown_all = [], []
        for y in pl.years:
            mid = pd.Timestamp(f"{int(y)}-07-01")
            live = []
            for r in mine.itertuples():
                if not (r.effective_date <= mid and (pd.isna(r.end_date) or r.end_date > mid)):
                    continue
                rubric = adu.with_parking(adu._resolved(reforms, r.reform_id), all_reforms, pl.geoid, mid)
                if adu._no_adus(rubric):
                    continue
                failed, unknown = adu.restriction_fields(rubric)
                live.append((set(failed), list(unknown), parking_level(rubric)))
                unknown_all += [u for u in unknown if u not in unknown_all]
            per_year.append(live)
        combos = list(itertools.product((False, True), repeat=len(unknown_all)))
        shape = pl.types.shape
        assert len(combos) == shape[0] and max(len(lv) for lv in per_year) == shape[2], pl.name
        park = np.zeros(shape, dtype=int)
        rest = np.zeros(shape, dtype=bool)
        nbr = np.zeros(shape, dtype=bool)
        for t, live in enumerate(per_year):
            for r_i, (failed, unknown, lvl) in enumerate(live):
                for c_i, c in enumerate(combos):
                    hit = {f for f, b in zip(unknown_all, c, strict=True) if b and f in unknown}
                    fails = failed | hit
                    park[c_i, t, r_i] = lvl if lvl is not None else (1 if "parking" in fails else 0)
                    rest[c_i, t, r_i] = bool(fails & OTHER)
                    nbr[c_i, t, r_i] = "by_right" in fails
        assert (nbr == pl.extra["no_by_right"]).all(), pl.name
        pl.extra["park"], pl.extra["rest"] = park, rest
    return out


cal.place_data = place_data

# ---------------------------------------------------------------------------------------------------------
# Fitting version C
# ---------------------------------------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class FitC(cal.Fit3):
    slopes: tuple = ()
    slope_se: tuple = ()


LOG_REF = [0.0]  # log median lots of the full fit set, fixed once in main and passed to every fit


def vector(b, c_part: float, log_ref: float) -> tuple:
    return (0.0, 1.0, 1.0, 1.0, 1.0, *map(float, b), float(c_part), float(log_ref))


def loglik_c(places, lt: float, la: float, b, log_ref: float) -> float:
    v = np.asarray(vector(b, 0.0, log_ref))
    alpha, theta = math.exp(la), math.exp(lt)
    total = 0.0
    for pl in places:
        ks = _k(pl, v)  # (C, T)
        lf = pl.log_fact
        share = pl.w / pl.w.sum()
        keep = share > 0
        per = np.log(share[keep]) + jr._marginal(pl.y, theta * ks[keep], alpha, lf)
        m = per.max()
        if not np.isfinite(m):
            return -math.inf
        total += float(m + math.log(np.exp(per - m).sum()))
    return total


def _unpack(q):
    lt, la, g_br, g_p1, g_p2, g_x, b_s = q
    return lt, la, (-g_br * g_br, -g_p1 * g_p1, -g_p2 * g_p2, -g_x * g_x, b_s)


def c_partial(places, b, log_ref: float) -> float:
    """Mean c over restricted rules in force (combination-weighted): tier 0's value for borrowed partial types."""
    v = np.asarray(vector(b, 0.0, log_ref))
    num = den = 0.0
    for pl in places:
        c = rule_c(pl, v)
        restricted = pl.extra["no_by_right"] | (pl.extra["park"] > 0) | pl.extra["rest"]
        live = (pl.cr > 0)[None] & restricted
        w = (pl.w / pl.w.sum())[:, None, None] * live
        num += float((w * c).sum())
        den += float(w.sum())
    return num / den if den > 0 else 1.0


def fit_c(places, log_ref: float, starts: int = 4, seed: int = 83) -> FitC:
    def neg(q):
        lt, la, b = _unpack(q)
        v = loglik_c(places, lt, la, b, log_ref)
        return -v if math.isfinite(v) else 1e12

    rng = np.random.default_rng(seed)
    x0 = np.array([math.log(7.5e-4), math.log(1.5), 0.7, 0.5, 0.5, 0.5, 0.0])
    best = None
    for s in range(starts):
        q = x0 if s == 0 else x0 + rng.normal(0, 0.5, size=len(x0))
        for _ in range(2):
            q, val = shp.nelder_mead(neg, q, step=0.3, iters=4000, tol=1e-8)
        if best is None or val < best[1]:
            best = (q, val)
    q, val = best
    lt, la, b = _unpack(q)
    # observed information in the natural parameters (log θ, log α, b...); a slope at its bound (0) gets SE 0
    z = np.r_[lt, la, b]

    def ll_nat(x):
        return loglik_c(places, x[0], x[1], x[2:], log_ref)

    h = shp.hessian(ll_nat, z, step=1e-3)
    at_bound = np.r_[False, False, np.isclose(np.asarray(b[:4]), 0.0, atol=1e-6), False]
    free = ~at_bound
    info = -h[np.ix_(free, free)]
    w_, vecs = np.linalg.eigh((info + info.T) / 2)
    cov_f = (vecs / np.maximum(w_, 1e-8)) @ vecs.T
    se = np.zeros(len(z))
    se[free] = np.sqrt(np.clip(np.diag(cov_f), 0, None))
    theta = math.exp(lt)
    cp = c_partial(places, b, log_ref)
    return FitC(
        theta,
        theta * math.exp(-cal.Z_95 * se[0]),
        theta * math.exp(cal.Z_95 * se[0]),
        math.exp(la),
        vector(b, cp, log_ref),  # m_owner carries the whole vector; `_cvals` reads it
        None,
        (1.0, 1.0),
        (float("nan"), float("nan")),
        False,
        False,
        -val,
        len(places),
        int(sum(len(p.y) for p in places)),
        tuple(map(float, b)),
        tuple(map(float, se[2:])),
    )


def fit_c_task(args):
    key, places = args
    t0 = time.time()
    return key, fit_c(places, LOG_REF[0]), time.time() - t0


def fit_c_task_ref(args):
    key, places, log_ref = args
    LOG_REF[0] = log_ref
    return fit_c_task((key, places))


# ---------------------------------------------------------------------------------------------------------
# One variant (ajr.run_variant with Form A's fit swapped and Form B's fits reusable)
# ---------------------------------------------------------------------------------------------------------


def run_variant(name, pool, store, places, new, with_dose, seed, tests, form, b_cache, log_ref):
    log(f"=== {name} ({form}): {len(places)} places, {sum(len(p.y) for p in places)} place-years ===")
    jobs = {"all": places} | {f"without {st}": [p for p in places if p.state != st] for st in ajr.STATES}
    if tests:
        jobs |= {f"without place {g}": [p for p in places if p.geoid != g] for g in sorted(new)}
    if form == "A":
        fa_f = {k: pool.submit(ajr.fit_a_task, (k, v)) for k, v in jobs.items()}
    else:
        fa_f = {k: pool.submit(fit_c_task_ref, (k, v, log_ref)) for k, v in jobs.items()}
    need_b = [k for k in jobs if k not in b_cache]
    fb_f = {k: pool.submit(ajr.fit_b_task, (k, jobs[k], with_dose)) for k in need_b}
    fa = {}
    for k, f in fa_f.items():
        _, fit, sec = f.result()
        fa[k] = fit
        extra = (
            f"m_o {fit.m_owner}, m_x {fit.m_other}"
            if form == "A"
            else ", ".join(f"{n} {b:+.3f}" for n, b in zip(NAMES, fit.slopes, strict=True))
        )
        log(f"  {form} {k}: theta {fit.theta * 1000:.4f}/1,000, alpha {fit.alpha:.3f}, {extra}, "
            f"loglik {fit.loglik:.2f} ({sec:.0f}s)")  # fmt: skip
    for k, f in fb_f.items():
        _, fit, sec = f.result()
        b_cache[k] = fit
        log(f"  Form B {k}: loglik {fit.fit.loglik:.2f}, alpha {fit.fit.alpha:.3f} ({sec:.0f}s)")
    fb = {k: b_cache[k] for k in jobs}
    loso = [f"without {st}" for st in ajr.STATES]
    ft = {k: pool.submit(ajr.tau_task, (k, jobs[k], fa[k].m_owner, fa[k].m_other)) for k in loso}
    taus = {k: f.result()[1] for k, f in ft.items()}
    tier_rows, ls_rows = [], []
    for st in ajr.STATES:
        held = [p for p in places if p.state == st]
        others = [p for p in places if p.state != st]
        shifts = [jr.state_shift([p for p in others if p.state == s], fb[f"without {st}"])
                  for s in ajr.STATES if s != st]  # fmt: skip
        s_b = jr.shift_spread(shifts)
        inputs = ajr.tier_inputs(st, store, held)
        r, ls = ajr.tiers_for_state(st, inputs, held, fa[f"without {st}"], taus[f"without {st}"],
                                    fb[f"without {st}"], s_b, seed)  # fmt: skip
        tier_rows += r
        ls_rows += ls
    tiers = ajr.tier_gains(pd.DataFrame(tier_rows)).assign(variant=name)
    tiers["form"] = tiers["form"].replace({"A": form})
    lsd = pd.DataFrame(ls_rows).assign(variant=name)
    lsd["form"] = lsd["form"].replace({"A": form})
    out = {"fa": fa, "fb": fb, "tiers": tiers, "logscores": lsd}
    if tests:
        ta = pd.DataFrame(ajr.test_a_rows([p for p in places if p.geoid in new],
                                          {g: fa[f"without place {g}"] for g in new},
                                          {g: fb[f"without place {g}"] for g in new}, seed))  # fmt: skip
        ta["form"] = ta["form"].replace({"A": form})
        tb, _ = ajr.test_b_rows(store, fa["all"], fb["all"], seed)
        tb = pd.DataFrame(tb)
        tb["form"] = tb["form"].replace({"A": form})
        out["test_a"], out["test_b"] = ta.assign(variant=name), tb.assign(variant=name)
    return out


def summarize(v: dict, form: str) -> dict:
    t = v["tiers"]
    out = {"claim_tier": {f: jr.claim_tier(t[t["form"] == f]) for f in (form, "B")}}
    if "test_a" in v:
        out["test_a"] = {f: {st: jr.test_a_pass(v["test_a"][(v["test_a"]["form"] == f)
                                                            & (v["test_a"]["state"] == st)])
                             for st in ajr.STATES} for f in (form, "B")}  # fmt: skip
        tb = v["test_b"]
        out["test_b"] = {f: {r.state: bool(r["pass"]) for _, r in tb[tb["form"] == f].iterrows()}
                         for f in (form, "B")}  # fmt: skip
    return out


def fit_rows(name, form, fa) -> list[dict]:
    rows = []
    for k, f in fa.items():
        r = {"variant": name, "form": form, "fold": k, "theta": f.theta, "theta_low": f.low,
             "theta_high": f.high, "alpha": f.alpha, "loglik": f.loglik, "places": f.n_places,
             "place_years": f.n_years}  # fmt: skip
        if form == "A":
            r |= {"m_owner": f.m_owner, "m_other": f.m_other}
        else:
            r |= {f"b[{n}]": b for n, b in zip(NAMES, f.slopes, strict=True)}
            r |= {f"se[{n}]": s for n, s in zip(NAMES, f.slope_se, strict=True)}
            r |= {"c_partial": f.m_owner[10]}
        rows.append(r)
    return rows


def detached_conditional_ids() -> set[str]:
    p = pd.read_csv(PROPOSED, dtype=str)
    return set(p.loc[p["tags"].fillna("").str.contains("detached-conditional"), "reform_id"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=7)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        run(a, store)


def run(a, store) -> None:
    places, new = ajr.all_places(store)
    ev = jr.events(places)
    with_dose = jr.g_identified(ev)
    log_ref = float(np.log(np.median([np.nanmean(p.extra["parcels"]) for p in places])))
    LOG_REF[0] = log_ref
    log(f"fit set {len(places)} places, {sum(len(p.y) for p in places)} place-years; events {len(ev)} in "
        f"{ev['state'].nunique()} states -> g {'estimated' if with_dose else 'held at 0'}; "
        f"median lots {math.exp(log_ref):.0f}")  # fmt: skip
    ev.to_csv(a.out / "events.csv", index=False)
    summary, fits, tiers, ls, ta, tb = {}, [], [], [], [], []
    b_cache: dict = {}
    with ProcessPoolExecutor(a.workers) as pool:
        res = {}
        res["A′"] = run_variant("A′", pool, store, places, new, with_dose, ajr.SEED, True, "A", b_cache, log_ref)
        res["C"] = run_variant("C", pool, store, places, new, with_dose, ajr.SEED, True, "C", b_cache, log_ref)
        for nm, form in (("A′", "A"), ("C", "C")):
            summary[nm] = summarize(res[nm], form)
            fits += fit_rows(nm, form, res[nm]["fa"])
        # B's own fit rows once
        for k, f in b_cache.items():
            fits.append(ajr.fit_row("A′ run", k, "B", f))
        ids = detached_conditional_ids()
        orig_load = adu.load_reforms

        def load_dc(st):
            r = orig_load(st)
            hit = r["reform_id"].isin(ids)
            r.loc[hit, "by_right"] = False
            return r

        adu.load_reforms = load_dc
        ajr._reforms.cache_clear()
        ajr._field_counts.cache_clear()
        ajr._COV.clear()
        p_dc, new_dc = ajr.all_places(store)
        log(f"sensitivity: {len(ids)} [detached-conditional] rows read as not by right")
        res["C, detached-conditional not by right"] = run_variant(
            "C, detached-conditional not by right", pool, store, p_dc, new_dc, with_dose, ajr.SEED, False,
            "C", {}, log_ref,
        )  # fmt: skip
        nm = "C, detached-conditional not by right"
        summary[nm] = summarize(res[nm], "C")
        fits += fit_rows(nm, "C", res[nm]["fa"])
        adu.load_reforms = orig_load
        ajr._reforms.cache_clear()
        ajr._field_counts.cache_clear()
        ajr._COV.clear()
    for v in res.values():
        tiers.append(v["tiers"])
        ls.append(v["logscores"])
        if "test_a" in v:
            ta.append(v["test_a"])
            tb.append(v["test_b"])
    pd.DataFrame(fits).to_csv(a.out / "fits.csv", index=False)
    pd.concat(tiers).to_csv(a.out / "tiers.csv", index=False)
    pd.concat(ls).to_csv(a.out / "logscores_tier1.csv", index=False)
    pd.concat(ta).to_csv(a.out / "test_a.csv", index=False)
    pd.concat(tb).to_csv(a.out / "test_b.csv", index=False)
    pd.DataFrame(ajr.event_check(places, ev, res["A′"]["fa"]["all"])).assign(form="A′").pipe(
        lambda d: pd.concat([d, pd.DataFrame(ajr.event_check(places, ev, res["C"]["fa"]["all"])).assign(form="C")])
    ).to_csv(a.out / "event_check.csv", index=False)
    log("test C for A′: the scenario engine with A′'s values")
    tc = pd.DataFrame(ajr.test_c_rows(store, res["A′"]["fa"]["all"]))
    tc.to_csv(a.out / "test_c_a_prime.csv", index=False)
    summary["A′"]["test_c"] = {st: jr.test_c_pass(tc.loc[tc["state"] == st, "ratio"]) for st in ajr.STATES}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    sys.exit(main())
