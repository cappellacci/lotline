"""Runners for the ADU calibration chain (phase 4): D-096's joint fit and the steps that follow it.

Each runner takes a `RunContext` and returns {params file: {key: value or {value, low, high}}}, rounded to the
precision config holds (so a rerun on unchanged data reproduces config exactly). The fit inputs come from
`lotline.model.adu_fit_set` (the D-096 fit set) and the arithmetic from `lotline.model.adu_refit`; both used
to live only in development scripts.

Quick runs (`--quick`) check the code path and the central values in minutes instead of hours:

- `adu_joint`: the rule-share grid cut to 0.6-1.0 on both shares (5 x 5 cells instead of 10 x 10), so the
  central θ, α and β_core are exact if the maximum hasn't moved; the profile interval of θ is taken over
  fewer cells.
- `adu_partial_share_grid`: the all-states rows at m_x 0.6, 0.7 and 0.8 (no folds, so no weights).
- `adu_anchor_slopes`: the observed-information terms and the first two slopes.
- `adu_new_rule`: ν on a coarse grid (0.5, 0.75, 1.0).

Heavy steps run their fits in a process pool: `LOTLINE_CALIBRATE_WORKERS` workers (default 4).
"""

from __future__ import annotations

import functools
import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore, offline
from lotline.model import adu_fit_set as fs
from lotline.model import adu_new_rule as nr
from lotline.model import adu_refit as rf
from lotline.model import adu_screen as scr
from lotline.model import adu_types as ty
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr
from lotline.model import score as sc
from lotline.model.scenarios import adu

Z_90 = 1.645  # a 90% interval spans ± this many SEs (D-030; config's intervals use it)
QUICK_GRID = (0.6, 0.7, 0.8, 0.9, 1.0)
QUICK_MX = (0.6, 0.7, 0.8)
QUICK_NU = (0.5, 0.75, 1.0)


def _workers() -> int:
    return max(1, int(os.environ.get("LOTLINE_CALIBRATE_WORKERS", "4")))


def sig(v: float, n: int = 3) -> float:
    """v to n significant figures. By hand: 0.00022411 -> 0.000224."""
    return float(f"{v:.{n}g}")


def fixed(v: float) -> dict:
    return {"value": v, "low": v, "high": v}


def _cv():
    p = load_params("adu")
    return cal._cvals(p["adu_owner_occupancy_share"].value, p["adu_partial_rule_share"].value)


def d096(store):
    with offline.offline_build(store):
        return fs.d096_places(store)


# ---------------------------------------------------------------------------------------------------------
# adu_joint (D-096): Form A + place types by fit 3's procedure
# ---------------------------------------------------------------------------------------------------------


def joint(ctx) -> dict:
    pz = d096(ctx.store)
    if ctx.quick:
        # fit3_types takes one grid for both shares; the quick grid keeps the cells near today's maximum
        f = ty.fit3_types(pz, estimate_beta=False, grid=QUICK_GRID)
    else:
        f = ty.fit3_types(pz, estimate_beta=False)
    se_t, se_a, _ = cal.information_se(
        [ty.typed_scaled(p, 0.0, np.array([f.type_beta[0], 0.0])) for p in pz],
        f.theta,
        f.alpha,
        cal._cvals(f.m_owner, f.m_other),
    )
    print(
        f"adu_joint: {len(pz)} places, {sum(len(p.y) for p in pz)} place-years; θ {f.theta:.6g} "
        f"({f.low:.6g}-{f.high:.6g}), α {f.alpha:.4f} (info log-SE {se_a:.3f}), m_o {f.m_owner}, "
        f"m_x {f.m_other}, core {f.type_beta[0]:.4f}",
        flush=True,
    )
    return {
        "hazard": {
            "adu_mature_hazard_ref": {"value": sig(f.theta), "low": sig(f.low), "high": sig(f.high)},
            "adu_place_effect_variance": {
                "value": round(f.alpha, 3),
                "low": round(f.alpha * math.exp(-Z_90 * se_a), 3),
                "high": round(f.alpha * math.exp(Z_90 * se_a), 3),
            },
        },
        "adu": {
            "adu_partial_rule_share": fixed(f.m_other),
            "adu_owner_occupancy_share": fixed(f.m_owner),
        },
        "adu_place_types": {
            "adu_types_core_log_multiplier": {
                "value": round(f.type_beta[0], 3),
                "low": round(f.type_low[0], 3),
                "high": round(f.type_high[0], 3),
            }
        },
    }


# ---------------------------------------------------------------------------------------------------------
# adu_partial_share_grid (D-097)
# ---------------------------------------------------------------------------------------------------------


def _grid_task(args) -> dict:
    fold, places, m_o, m_x = args
    return {"fold": fold, "m_x": m_x} | rf.fit_at_mx(places, m_o, m_x)


def partial_share_grid(ctx) -> dict:
    """Returns the grid as CSV text under its file name (`lotline.calibrate.run` compares it row by row and,
    with --write, writes it)."""
    pz = d096(ctx.store)
    m_o = load_params("adu")["adu_owner_occupancy_share"].value
    folds = rf.folds_of(pz)[:1] if ctx.quick else rf.folds_of(pz)
    mxs = QUICK_MX if ctx.quick else cal.GRID3
    jobs = [(fold, sub, m_o, m) for fold, sub in folds for m in mxs]
    with ProcessPoolExecutor(_workers()) as pool:
        prof = pd.DataFrame(list(pool.map(_grid_task, jobs)))
    if ctx.quick:
        text = prof.drop(columns="fold").to_csv(index=False, float_format="%.6g")
    else:
        text = rf.grid_csv(rf.grid_table(prof, m_o, len(pz), int(sum(len(p.y) for p in pz))))
    return {"adu_partial_share_grid.csv": text}


# ---------------------------------------------------------------------------------------------------------
# adu_anchor_slopes (D-088, D-030)
# ---------------------------------------------------------------------------------------------------------


@functools.cache
def _slope_store() -> DataStore:
    return DataStore()


@functools.cache
def _slope_types() -> dict[str, str]:
    store = _slope_store()
    with offline.offline_build(store):
        return fs.slope_types(store, fs.slope_places(store))


def _slope_key(places) -> tuple:
    return tuple(np.concatenate([np.r_[pl.base, pl.cr.ravel()] for pl in places]).round(15))


def slope_fit(params) -> dict:
    """θ, α and β_core at the central rule shares for the fit places built at `params` (None: central)."""
    central = adu.central_params()
    p = central if params is None else params
    cv = cal._cvals(p["adu_owner_occupancy_share"], p["adu_partial_rule_share"])
    store = _slope_store()
    with offline.offline_build(store):
        places = fs.slope_places(store, params)
    pz, zm = fs.typed(places, _slope_types())
    f = ty._maximize(scr.prepare(pz, cv), zm)
    core = float(f.b[0]) if len(f.b) else 0.0
    out = {"theta": math.exp(f.lt), "alpha": math.exp(f.la), "core": core, "loglik": f.loglik}
    return out | {"key": _slope_key(pz), "places": pz, "cv": cv}


@functools.cache
def _central_key() -> tuple:
    return slope_fit(None)["key"]


def slope_task(key: str) -> dict:
    central = adu.central_params()
    s = adu.specs()[key]
    lo, hi = rf.slope_bounds(s.value, s.low, s.high)
    f_lo = slope_fit(central | {key: lo})
    if f_lo["key"] == _central_key():  # the parameter leaves the fit inputs unchanged
        return {"key": key, "low": lo, "high": hi, "theta": 0.0, "alpha": 0.0, "core": 0.0, "in_fit": False}
    f_hi = slope_fit(central | {key: hi})
    out = {"key": key, "low": lo, "high": hi, "in_fit": True}
    out["theta"] = rf.log_slope(f_lo["theta"], f_hi["theta"], lo, hi)
    out["alpha"] = rf.log_slope(f_lo["alpha"], f_hi["alpha"], lo, hi)
    out["core"] = (f_hi["core"] - f_lo["core"]) / (hi - lo)  # reported, not written (the engine draws it)
    print(f"  {key}: dlogθ/dp {out['theta']:+.5g}, dlogα/dp {out['alpha']:+.5g}", flush=True)
    return out


def anchor_slopes(ctx) -> dict:
    c = slope_fit(None)
    se_t, se_a, corr = cal.information_se(
        [ty.typed_scaled(p, 0.0, np.array([c["core"], 0.0])) for p in c["places"]],
        c["theta"],
        c["alpha"],
        c["cv"],
    )
    keys = adu.anchor_inputs()
    keys = keys[:2] if ctx.quick else keys
    with ProcessPoolExecutor(_workers()) as pool:
        rows = list(pool.map(slope_task, keys))
    out = {
        "adu_anchor_info_log_se_theta": fixed(sig(se_t, 6)),
        "adu_anchor_info_log_se_alpha": fixed(sig(se_a, 6)),
        "adu_anchor_info_corr": fixed(sig(corr, 6)),
    }
    for r in rows:
        if r["in_fit"]:
            out[f"anchor_slope_theta__{r['key']}"] = fixed(sig(r["theta"], 6))
            out[f"anchor_slope_alpha__{r['key']}"] = fixed(sig(r["alpha"], 6))
    return {"adu_anchor": out}


# ---------------------------------------------------------------------------------------------------------
# adu_calibration_range (D-060) and adu_town_prior_sd (D-089)
# ---------------------------------------------------------------------------------------------------------


def calibration_range(ctx) -> dict:
    r = cal.fit_set_range(d096(ctx.store))
    out = {}
    for key in (
        "adu_calibration_rent_low_usd",
        "adu_calibration_rent_high_usd",
        "adu_calibration_value_low_usd",
        "adu_calibration_value_high_usd",
    ):
        out[key] = fixed(round(r[key]))
    for key in ("adu_calibration_rate_low", "adu_calibration_rate_high"):
        out[key] = fixed(round(r[key], 2))
    return {"hazard": out}


def town_prior_sd(ctx) -> dict:
    """D-089: s = |β̂_core| / 1.645, from the core multiplier in config (written by `adu_joint`)."""
    core = load_params("adu_place_types")["adu_types_core_log_multiplier"].value
    return {"adu_place_types": {"adu_types_town_prior_sd": fixed(round(abs(core) / Z_90, 3))}}


# ---------------------------------------------------------------------------------------------------------
# adu_new_rule (D-099)
# ---------------------------------------------------------------------------------------------------------


def nu_profile(places, first, nus, k=nr.K) -> pd.DataFrame:
    cv, zm = _cv(), rf.type_columns(places)
    rows = []
    for nu in nus:
        f = ty._maximize(scr.prepare(nr.scaled_all(places, nu, first, k), cv), zm)
        rows.append({"nu": nu, "theta": math.exp(f.lt), "alpha": math.exp(f.la), "core": float(f.b[0]),
                     "loglik": f.loglik})  # fmt: skip
    return pd.DataFrame(rows)


def nu_interval(prof: pd.DataFrame) -> dict:
    """ν̂ and its 90% profile interval. By hand: ll (−3, 0, −1.2) at ν (0.5, 0.75, 1.0) -> ν̂ 0.75; 2 × 1.2 =
    2.4 <= 2.706 keeps 1.0, 2 × 3 = 6 does not keep 0.5 -> 0.75-1.0."""
    top = prof["loglik"].max()
    inside = prof[2 * (top - prof["loglik"]) <= cal.CHI2_90]["nu"]
    return {"nu": float(prof.loc[prof["loglik"].idxmax(), "nu"]), "low": float(inside.min()),
            "high": float(inside.max())}  # fmt: skip


def held_out_task(args) -> dict:
    j, places, first, k, nus = args
    prof = nu_profile([p for p in places if p.geoid != j.geoid], first, nus, k)
    nu_hat = nu_interval(prof)["nu"]
    flags = nr.new_rule_flags(j.years, first[j.geoid], k)
    sub = jr.subset_years(j, [y for y, fl in zip(j.years, flags, strict=True) if fl])
    out = {"geoid": j.geoid, "nu_minus_j": nu_hat}
    core = float(ty.type_d(j)[0])
    for tag, nu in (("hat", nu_hat), ("one", 1.0)):
        r = prof[prof["nu"] == nu].iloc[0]
        rate = r["theta"] * math.exp(r["core"] * core)
        p = scr.prepare([nr.scaled(sub, nu, np.ones(len(sub.y), dtype=bool))], _cv())
        out[f"ls_{tag}"] = float(scr.place_loglik(p, np.array([rate]), r["alpha"])[0])
    return out


def new_rule(ctx) -> dict:
    """D-099's main variant: ν̂ with its interval, and the held-out gain over ν = 1. D-099 adopts ν only if the
    interval excludes 1 and the gain exceeds 2 SE (then tests A, B and D, and Ben's call); otherwise ν = 1."""
    pz = d096(ctx.store)
    nus = QUICK_NU if ctx.quick else nr.NU_GRID
    rows = pd.concat([adu.load_reforms(st) for st in fs.STATES], ignore_index=True)
    ids = {p.geoid for p in pz}
    first = {g: f for g, f in nr.first_allowing_year(rows).items() if g in ids}
    iv = nu_interval(nu_profile(pz, first, nus))
    targets = [p for p in pz if p.geoid in first and nr.new_rule_flags(p.years, first[p.geoid]).any()]
    with ProcessPoolExecutor(_workers()) as pool:
        ho = pd.DataFrame(list(pool.map(held_out_task, [(j, pz, first, nr.K, nus) for j in targets])))
    gain, se = sc.paired(ho["ls_hat"] - ho["ls_one"]) if len(ho) > 1 else (float("nan"), float("nan"))
    passes = not (iv["low"] <= 1.0 <= iv["high"]) and gain > 2 * se
    verdict = "passes" if passes else "fails"
    print(f"adu_new_rule: ν̂ {iv['nu']} ({iv['low']}-{iv['high']}), held-out gain {gain:.2f} "
          f"(2 SE {2 * se:.2f}), {len(ho)} places; {verdict} D-099 parts 1-2", flush=True)  # fmt: skip
    if passes and not ctx.quick:
        raise ValueError(
            f"D-099's held-out check now passes (ν̂ {iv['nu']}, gain {gain:.2f} > 2 SE {2 * se:.2f}): "
            "tests A, B and D and Ben's decision are needed before adu_new_rule_share changes from 1"
        )
    return {"adu": {"adu_new_rule_share": fixed(1.0)}}


# ---------------------------------------------------------------------------------------------------------
# Phase 5: the three steps fitted on older model forms, refitted on D-096's (not written without Ben)
# ---------------------------------------------------------------------------------------------------------

DRIFT_STATES = ("MN", "NC", "TX", "OR")  # D-090: Ohio has no counts before 2024


def _shares() -> tuple[float, float]:
    p = load_params("adu")
    return p["adu_owner_occupancy_share"].value, p["adu_partial_rule_share"].value


def state_effect(ctx) -> dict:
    """D-043/D-044 on D-096's form: τ's profile on `TAU_GRID` and (θ, α, τ) by maximum likelihood, with the
    rule shares and the core multiplier held at config (`adu_joint`), θ and α maximized at each τ. The five
    fit states stay listed as fitted. Quick: every fifth grid point, no interval."""
    m_o, m_x = _shares()
    core = load_params("adu_place_types")["adu_types_core_log_multiplier"].value
    tp = rf.typed_for_state_effect(d096(ctx.store), core)
    grid = cal.TAU_GRID[::5] if ctx.quick else cal.TAU_GRID
    probs = cal.tau_probabilities(cal.tau_profile(tp, m_o, m_x, grid))
    out = {f"adu_state_effect_fitted__{s}": fixed(1) for s in fs.STATES}
    for t, q in zip(grid, probs, strict=True):
        out[f"adu_state_tau_prob__{t:.2f}".replace(".", "_")] = fixed(sig(q, 6))
    if not ctx.quick:
        sf = cal.fit_state_effect(tp, m_o, m_x)
        out["adu_state_effect_sd"] = {"value": sig(sf.tau, 6), "low": 0, "high": sig(sf.tau_high, 6)}
        print(f"adu_state_effect: {sf.n_places} places, {sf.n_years} place-years; τ̂ {sf.tau:.4f} "
              f"(90% up to {sf.tau_high:.4f}), θ {sf.theta:.6g}, α {sf.alpha:.4f}, "
              f"P(τ = 0) {probs[0]:.4f}", flush=True)  # fmt: skip
    return {"adu_state_effect": out}


def drift(ctx) -> dict:
    """D-091 on D-096's fit set: σ maximizing the persistence forecaster's (F0) window likelihood with the
    drift integrated, over every place with history in MN, NC, TX and OR (fit 2016-2019, window 2021-2025).
    Leaving one state out gives the sensitivity range (printed, as config's notes hold it)."""
    grids = rf.drift_grids(d096(ctx.store), DRIFT_STATES)
    s = rf.drift_sigmas(grids, DRIFT_STATES)
    loso = {k: v for k, v in s.items() if k != "all"}
    each = ", ".join(f"{k} {v:.3f}" for k, v in loso.items())
    print(f"adu_drift: {len(grids)} places with history; σ {s['all']:.3f} (leaving one state out "
          f"{min(loso.values()):.3f}-{max(loso.values()):.3f}: {each})", flush=True)  # fmt: skip
    return {"adu": {"adu_drift_sigma": fixed(round(s["all"], 3))}}


def ramp_share(ctx) -> dict:
    """D-048 on D-096's form: the fit at each half-life on D-047's grid (and no ramp), rule shares held at
    config. D-048 keeps no ramp (share 1) while no ramp has the highest likelihood; if a ramp beats it on a
    full run the runner stops, because config's single share cannot hold a ramp and it is Ben's decision."""
    halves = (rf.NO_RAMP, 2.0) if ctx.quick else rf.RAMP_HALVES
    prof = rf.ramp_profile(d096(ctx.store), _cv(), halves)
    none = float(prof.loc[prof["half"] == rf.NO_RAMP, "loglik"].iloc[0])
    best = prof.loc[prof["loglik"].idxmax()]
    print("adu_ramp_share: " + "; ".join(
        f"{'no ramp' if r.half == rf.NO_RAMP else f'half {r.half}'} ll {r.loglik:.2f} (θ {r.theta:.4g})"
        for r in prof.itertuples()), flush=True)  # fmt: skip
    if best["half"] != rf.NO_RAMP and not ctx.quick:
        raise ValueError(
            f"a ramp with half-life {best['half']} years beats no ramp by {best['loglik'] - none:.2f} in "
            "log-likelihood on D-096's form: D-048 needs Ben's decision before adu_ramp_share changes"
        )
    return {"hazard": {"adu_ramp_share": fixed(1.0)}}
