#!/usr/bin/env python3
"""The anchor's draw terms for Form A + place types (D-088): config/params/adu_anchor.yaml.

    uv run python scripts/dev/adu_types_slopes.py [--out config/params/adu_anchor.yaml] [--report DIR]

What the scenario's draws need from the fit (D-030), recomputed for the fit the engine now runs:

- the observed-information log-SEs of θ and α and their correlation, at the central fit, with the core-city
  term held at its estimate (`calibrate_adu.information_se` on the type-scaled places);
- for each judgment parameter the fit depends on (`scenarios.adu.anchor_inputs`), d log θ̂ / dp and
  d log α̂ / dp by central differences: the D-088 fit places (the D-079 joint-refit set, St. Paul out) are
  rebuilt with that parameter at central ± 10% of its range (clipped), and θ, α and β_core are refit at the
  central rule shares (m_o, m_x from adu.yaml). A parameter that leaves the fit inputs unchanged gets 0 and is
  left out. d β̂_core / dp is reported (`--report`), not written: the engine draws β_core on its own.

Same procedure as `scripts/dev/calibrate_adu.py --draw-terms` (D-048's fit), on the D-088 fit set and form.
Offline; holdout-filtered tables only.
"""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.io import DataStore, offline
from lotline.model import adu_screen as scr
from lotline.model import adu_types as ty
from lotline.model import calibrate_adu as cal
from lotline.model.scenarios import adu

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT_OUT = REPO / "config" / "params" / "adu_anchor.yaml"
STEP = 0.1  # central ± this share of the parameter's range, as calibrate_adu.py --draw-terms


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


R = _load("adu_joint_refit", "adu_joint_refit.py")


@functools.cache
def _store() -> DataStore:
    return DataStore()


@functools.cache
def _types() -> dict[str, str]:
    """Raw types for every jurisdiction, merged by D-088's rule over the central fit places."""
    store = _store()
    with offline.offline_build(store):
        raw = pd.concat([ty.jurisdiction_types(store, st) for st in R.STATES])
    places = _places_at(None)
    fit_t = pd.DataFrame([{"state": p.state, "geoid": p.geoid, "type": raw.get(p.geoid)} for p in places])
    mapping, _ = ty.merge_small(fit_t)
    return {g: mapping[t] for g, t in raw.items()}


def _places_at(params) -> list[cal.PlaceData]:
    """The D-088 fit places (`adu_joint_refit.fit_set`) with the transport evaluated at `params`."""
    store = _store()
    out = []
    with offline.offline_build(store):
        for st in R.STATES:
            geoids, _ = R.candidates(st, store)
            pls = cal.place_data(st, store, geoids, R.WINDOW, params=params, counts=cal.count_settings())
            out += [q for q in (R.limit_years(pl) for pl in pls) if q is not None and q.geoid != R.ST_PAUL]
    return out


def _typed(places) -> tuple[list[cal.PlaceData], np.ndarray]:
    types = _types()
    pz = [ty.with_types(p, ty.indicators(types.get(p.geoid, ty.REFERENCE))) for p in places]
    dmat = np.array([ty.type_d(p) for p in pz])
    zm = dmat[:, [j for j in range(dmat.shape[1]) if dmat[:, j].any()]]
    return pz, zm


def _key(places) -> tuple:
    return tuple(np.concatenate([np.r_[pl.base, pl.cr.ravel()] for pl in places]).round(15))


def fit_at(params) -> dict:
    """θ, α and β_core at the central rule shares, for the fit places built at `params`."""
    central = adu.central_params()
    p = central if params is None else params
    cv = cal._cvals(p["adu_owner_occupancy_share"], p["adu_partial_rule_share"])
    pz, zm = _typed(_places_at(params))
    f = ty._maximize(scr.prepare(pz, cv), zm)
    return {
        "theta": math.exp(f.lt),
        "alpha": math.exp(f.la),
        "core": float(f.b[0]) if len(f.b) else 0.0,
        "loglik": f.loglik,
        "key": _key(pz),
        "places": pz,
        "cv": cv,
    }


@functools.cache
def _central_key() -> tuple:
    return _key(_typed(_places_at(None))[0])


def slope(key: str) -> dict:
    central = adu.central_params()
    s = adu.specs()[key]
    d = STEP * (s.high - s.low)
    lo, hi = max(s.low, s.value - d), min(s.high, s.value + d)
    t0 = time.time()
    k0 = _central_key()
    f_lo = fit_at(central | {key: lo})
    if f_lo["key"] == k0:
        return {"key": key, "low": lo, "high": hi, "theta": 0.0, "alpha": 0.0, "core": 0.0, "in_fit": False}
    f_hi = fit_at(central | {key: hi})
    out = {
        "key": key,
        "low": lo,
        "high": hi,
        "theta": (math.log(f_hi["theta"]) - math.log(f_lo["theta"])) / (hi - lo),
        "alpha": (math.log(f_hi["alpha"]) - math.log(f_lo["alpha"])) / (hi - lo),
        "core": (f_hi["core"] - f_lo["core"]) / (hi - lo),
        "in_fit": True,
    }
    print(
        f"  {key:32s} {lo:g}..{hi:g}: dlogθ/dp {out['theta']:+.5g}  dlogα/dp {out['alpha']:+.5g}  "
        f"dβcore/dp {out['core']:+.5g}  ({time.time() - t0:.0f}s)",
        flush=True,
    )
    return out


def _entry(v: float, unit: str, how: str) -> list[str]:
    return [
        f"  value: {v:.6g}",
        f"  low: {v:.6g}",
        f"  high: {v:.6g}",
        f"  unit: {unit}",
        f'  source: "Estimated, scripts/dev/adu_types_slopes.py (D-088: Form A + place types; {how})"',
        "",
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, help="also write slopes.csv and summary.json here")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    c = fit_at(None)
    se_t, se_a, corr = cal.information_se(
        [ty.typed_scaled(p, 0.0, np.array([c["core"], 0.0])) for p in c["places"]],
        c["theta"],
        c["alpha"],
        c["cv"],
    )
    n_pl, n_yr = len(c["places"]), int(sum(len(p.y) for p in c["places"]))
    print(
        f"central: θ {c['theta'] * 1000:.4f}/1,000, α {c['alpha']:.3f}, core {c['core']:+.3f}, loglik "
        f"{c['loglik']:.2f} ({n_pl} places, {n_yr} place-years); info log-SE θ {se_t:.3f}, α {se_a:.3f}, "
        f"corr {corr:.3f}",
        flush=True,
    )
    keys = adu.anchor_inputs()
    print(f"{len(keys)} judgment parameters", flush=True)
    with ProcessPoolExecutor(a.workers) as pool:
        rows = list(pool.map(slope, keys))
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    where = f"{n_pl} places, {n_yr} place-years, m_o and m_x at adu.yaml's values, core term refit, {today}"
    lines = [
        "# How the fitted ADU anchor (theta = adu_mature_hazard_ref) and place-effect variance",
        "# (alpha = adu_place_effect_variance) move with the judgment parameters they were fitted at",
        "# (D-030), for the Form A + place types fit the engine runs (D-088). Generated by",
        "# scripts/dev/adu_types_slopes.py; do not edit by hand. Each simulation draw shifts log(theta) and",
        "# log(alpha) by slope x (drawn - central value) for every parameter here, so the anchor stays",
        "# consistent with the fit data under that draw's transport. Parameters the fit does not depend on",
        "# are left out (slope 0). D-048's version came from scripts/dev/calibrate_adu.py --draw-terms.",
        "",
        "adu_anchor_info_log_se_theta:",
        *_entry(se_t, "log-SE of theta (observed information, core-city term at its estimate)", where),
        "adu_anchor_info_log_se_alpha:",
        *_entry(se_a, "log-SE of alpha (observed information)", where),
        "adu_anchor_info_corr:",
        *_entry(corr, "correlation of log theta and log alpha (observed information)", where),
    ]
    for r in rows:
        if not r["in_fit"]:
            continue
        how = f"{where}; refit at central +/- 10% of the {r['key']} range"
        lines += [
            f"anchor_slope_theta__{r['key']}:",
            *_entry(r["theta"], f"change in log(theta) per unit of {r['key']}", how),
        ]
        lines += [
            f"anchor_slope_alpha__{r['key']}:",
            *_entry(r["alpha"], f"change in log(alpha) per unit of {r['key']}", how),
        ]
    a.out.write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out}")
    if a.report:
        a.report.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(a.report / "slopes.csv", index=False)
        summary = {
            "central": {k: c[k] for k in ("theta", "alpha", "core", "loglik")},
            "places": n_pl,
            "place_years": n_yr,
            "info": {"log_se_theta": se_t, "log_se_alpha": se_a, "corr": corr},
            "in_fit": [r["key"] for r in rows if r["in_fit"]],
            "not_in_fit": [r["key"] for r in rows if not r["in_fit"]],
        }
        (a.report / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
