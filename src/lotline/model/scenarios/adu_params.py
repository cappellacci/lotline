"""The ADU scenario's parameters and their draws (D-030): judgment ranges, the fitted anchor and
place-effect variance, and D-097's partial-rule-share grid. Part of `scenarios.adu`; the method
is in that module's docstring.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import CONFIG_DIR, load_params
from lotline.model import proforma

PARAM_FILES = ("proforma", "hazard", "adu", "market")
AGGREGATE_KEYS = ("adu_net_new_share", "adu_formalization_share")
FIXED = proforma.NOT_SAMPLED | {"adu_simulation_draws", "adu_simulation_seed"}


def specs() -> dict:
    """Every parameter the scenario uses: pro forma, hazard, adu.yaml and the two ADU shares in
    aggregate.yaml."""
    out = {}
    for name in PARAM_FILES:
        out |= load_params(name)
    agg = load_params("aggregate")
    return out | {k: agg[k] for k in AGGREGATE_KEYS}


def _adu_value(key: str) -> float:
    """One central value from config/params/adu.yaml (for helpers whose callers pass other param sets)."""
    return float(load_params("adu")[key].value)


def net_new_homes(added, p: Mapping[str, float]):
    """Homes from ADU permits added: added × adu_net_new_share × (1 − adu_formalization_share). The one place
    this is computed: the central path and every draw use it, and the bundle's per-draw net-new share is
    `net_new_homes(1.0, p)`."""
    return added * p["adu_net_new_share"] * (1 - p["adu_formalization_share"])


def central_params() -> dict[str, float]:
    return {k: s.value for k, s in specs().items()}


Z_90 = 1.644854  # standard normal 95th percentile: a 90% interval spans ±Z_90 log-SDs
LOGNORMAL = ("adu_mature_hazard_ref", "adu_place_effect_variance")
SENSITIVITY = ("mortgage_rate_forecast", "adu_extrapolation_shared_share")
NOT_IN_FIT = frozenset({"adu_extrapolation_widening"})


def anchor_inputs() -> list[str]:
    """The drawn parameters the D-019 fit 3 likelihood depends on: the anchor θ and place-effect variance α
    were fitted at their central values, so each draw shifts θ and α with them (`draw_params`, D-030)."""
    skip = FIXED | set(LOGNORMAL) | set(SENSITIVITY) | set(AGGREGATE_KEYS) | NOT_IN_FIT
    return [k for k, s in specs().items() if k not in skip and s.low != s.high]


def log_sd(spec) -> float:
    """Log-SD of a lognormal whose 90% interval is (low, high): (ln high − ln low) / (2 × 1.645). The same
    convention as the fit's own predictive check (`calibrate_adu.Fit3.log_se`).

    By hand, anchor 0.000453-0.003173: (ln 0.003173 − ln 0.000453) / 3.2897 = 1.9466 / 3.2897 = 0.5917.
    """
    return (np.log(spec.high) - np.log(spec.low)) / (2 * Z_90)


def draw_params(n: int, seed: int, anchor: Mapping[str, float] | None = None) -> list[dict[str, float]]:
    """n parameter sets (D-030).

    - Judgment parameters: triangular(low, central, high); fixed ones held.
    - `SENSITIVITY` parameters (the 2015-25 mortgage-rate stress range, the shared share of extrapolation
      noise): held at central; their low and high are run as sensitivities, not mixed into the forecast range.
    - The estimated anchor θ and place-effect variance α (`LOGNORMAL`): lognormal with median at the estimate
      and log-SD from the 90% interval (`log_sd`), correlated as the fit's observed information says, then
      shifted with the judgment parameters they were fitted at:
      log θ_d = log θ̂ + sd_θ ε_θ + Σ_j g_j (p_jd − p̂_j), g_j = d log θ̂ / d p_j (config/params/adu_anchor.yaml,
      from `scripts/dev/calibrate_adu.py --draw-terms`; a parameter not listed there has slope 0); the same
      for α.
    """
    rng = np.random.default_rng(seed)
    sp = specs()
    held = FIXED | set(SENSITIVITY) | set(LOGNORMAL)
    cols = {
        k: np.full(n, s.value) if k in held or s.low == s.high else rng.triangular(s.low, s.value, s.high, n)
        for k, s in sp.items()
    }
    a = anchor_terms() if anchor is None else anchor
    corr = a["adu_anchor_info_corr"]
    e1, e2 = rng.standard_normal(n), rng.standard_normal(n)
    eps = {
        "adu_mature_hazard_ref": e1,
        "adu_place_effect_variance": corr * e1 + np.sqrt(1 - corr**2) * e2,
    }
    for key, tag in zip(LOGNORMAL, ("theta", "alpha"), strict=True):
        s = sp[key]
        shift = sum(a.get(f"anchor_slope_{tag}__{j}", 0.0) * (cols[j] - sp[j].value) for j in anchor_inputs())
        sd = log_sd(s) if s.low < s.high else 0.0
        cols[key] = np.exp(np.log(s.value) + sd * eps[key] + shift)
    return [{k: float(v[i]) for k, v in cols.items()} for i in range(n)]


NEW_RULE = "adu_new_rule_share"  # D-099
GRID_FILE = "adu_partial_share_grid.csv"
SHARE_DRAWS = (
    "adu_partial_share_draws"  # 0 fixed; 1 the grid's weights; 2 the fold maxima; 3 all at the set m_x
)
CORE_SHIFT = "adu_types_core_shift"


def partial_share_grid() -> pd.DataFrame:
    """D-097: config/params/adu_partial_share_grid.csv, A + place types refitted at each m_x on the 0.1 grid
    (m_x, θ̂, α̂, β̂_core, log-likelihood, weight, weight_fold_max)."""
    return pd.read_csv(CONFIG_DIR / "params" / GRID_FILE)


def apply_partial_share_grid(
    sets: list[dict[str, float]], grid: pd.DataFrame, mode: int, seed: int, central_mx: float
) -> list[dict[str, float]]:
    """D-097: one m_x per draw, with θ, α and the core term moved to that grid row's refit.

    The draw's own lognormal spread and judgment shifts stay: θ_d × θ̂(m) ÷ θ̂(m̂), α_d × α̂(m) ÷ α̂(m̂), and the
    core term shifted by β̂(m) − β̂(m̂) (`adu_types_core_shift`), m̂ the configured central m_x. `mode` 1 draws m
    from `weight`, 2 from `weight_fold_max`, 3 puts every draw at the set's own `adu_partial_rule_share`.
    Own stream: (seed, 97).

    By hand: grid rows m 0.4 (θ 2, α 1, β 1) and 0.7 (θ 1, α 2, β 2), central 0.7, mode 3 with a set at
    m_x 0.4 and θ 3: θ 3 × 2 / 1 = 6, α × 0.5, core shift −1."""
    g = grid.set_index("m_x")
    c = g.loc[round(central_mx, 1)]
    if mode == 3:
        ms = np.array([round(p["adu_partial_rule_share"], 1) for p in sets])
    else:
        w = g["weight" if mode == 1 else "weight_fold_max"].to_numpy(dtype=float)
        ms = np.random.default_rng([seed, 97]).choice(g.index.to_numpy(), size=len(sets), p=w / w.sum())
    out = []
    for p, m in zip(sets, ms, strict=True):
        r = g.loc[m]
        q = dict(p)
        q["adu_partial_rule_share"] = float(m)
        q["adu_mature_hazard_ref"] = p["adu_mature_hazard_ref"] * r["theta"] / c["theta"]
        q["adu_place_effect_variance"] = p["adu_place_effect_variance"] * r["alpha"] / c["alpha"]
        q[CORE_SHIFT] = float(r["core"] - c["core"])
        out.append(q)
    return out


def anchor_terms() -> dict[str, float]:
    """config/params/adu_anchor.yaml: the anchor's observed-information terms and judgment slopes (D-030),
    for the Form A + place types fit (D-088; `scripts/archive/adu_types_slopes.py`)."""
    return {k: s.value for k, s in load_params("adu_anchor").items()}
