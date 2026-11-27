"""Uptake hazard and pool depletion: each place's yearly ADUs under current and Handbook rules (`pool_paths`),
the state effect (D-043/D-044) and extrapolation noise (D-030). Part of `scenarios.adu`; the method is in that
module's docstring.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model import hazard
from lotline.model.scenarios.adu_own_rate import own_rate_paths
from lotline.model.scenarios.adu_params import NEW_RULE
from lotline.model.scenarios.adu_rule_priors import type_probs
from lotline.model.scenarios.adu_rules import P_COLS


@dataclass(frozen=True)
class Paths:
    """Gross ADU permits per place (rows) and year (columns) under each set of rules, for one parameter
    set."""

    handbook: np.ndarray
    current: np.ndarray

    @property
    def added(self) -> np.ndarray:
        return self.handbook - self.current


def pool_paths(
    eligible, h_mature, h_floor, rule_share, rule_age, ramp_params, horizon, enabled=True, lead=0, h_own=None
):
    """Gross ADUs per year under current and Handbook rules, depleting the pool of parcels without an ADU.

    `rule_age` is the current rule's age in years at the origin (NaN: no rule). `ramp_params` gives the ramp
    (`hazard.adu_ramp`; D-048: 1 every year). With `enabled=False` the Handbook path equals the current-rules
    path, so nothing is added. `lead` years (D-061) run first under current rules only, on one shared pool,
    and are not returned: the window's year t has rule age a + lead + t and Handbook ramp(t).
    `h_own` (D-091; None or NaN per place: off) replaces the no-reform hazard, in the lead years too, and
    scales the Handbook hazard by the mechanism's ratio (`own_rate_paths`). D-099: where today's rule share c
    is 0 (no ADUs allowed), the Handbook's new hazard is multiplied by `adu_new_rule_share` (ν; 1 = none).
    """
    e = np.asarray(eligible, dtype=float)
    hm = np.asarray(h_mature, dtype=float)
    floor = np.nan_to_num(np.asarray(h_floor, dtype=float), nan=0.0)
    c = np.asarray(rule_share, dtype=float)
    age = np.nan_to_num(np.asarray(rule_age, dtype=float), nan=0.0)
    own = np.full(len(e), np.nan) if h_own is None else np.asarray(h_own, dtype=float)
    nu = float(ramp_params.get(NEW_RULE, 1.0))  # D-099: first-years share where no ADUs are allowed today
    r = e.copy()
    for s in range(1, int(lead) + 1):  # lead years: current rules only, nothing reported (D-061)
        h_lead = np.minimum(np.maximum(c * hm * hazard.adu_ramp(age + s, ramp_params), floor), 1.0)
        h_lead, _ = own_rate_paths(own, h_lead, h_lead)
        r = r - r * h_lead
    age = age + int(lead)
    r_hb, r_cur = r.copy(), r.copy()
    hb, cur = np.zeros((len(e), horizon)), np.zeros((len(e), horizon))
    for i, t in enumerate(range(1, horizon + 1)):
        h_rule = c * hm * hazard.adu_ramp(age + t, ramp_params)
        h_cur = np.minimum(np.maximum(h_rule, floor), 1.0)
        if enabled:
            h_new = h_rule + (1.0 - c) * hm * hazard.adu_ramp(t, ramp_params) * np.where(c <= 0, nu, 1.0)
            h_hb = np.minimum(np.maximum(h_new, floor), 1.0)
        else:
            h_hb = h_cur
        h_cur, h_hb = own_rate_paths(own, h_cur, h_hb)
        hb[:, i], cur[:, i] = r_hb * h_hb, r_cur * h_cur
        r_hb, r_cur = r_hb - hb[:, i], r_cur - cur[:, i]
    return Paths(hb, cur)


def with_rule_probs(places: pd.DataFrame, params: Mapping[str, float]) -> pd.DataFrame:
    """Type probabilities for every place (`type_probs`), and a rule age of `adu_unknown_rule_age_years` where
    the type is drawn and no rule date is known (D-022)."""
    out = places.copy()
    probs = type_probs(out)
    for k, col in enumerate(P_COLS):
        out[col] = probs[:, k]
    out["p_partial"] = probs[:, 1:4].sum(axis=1)
    sampled = probs.max(axis=1) < 1
    age = out["rule_age"] if "rule_age" in out else pd.Series(np.nan, index=out.index)
    out["rule_age"] = age.where(~(sampled & age.isna()), params["adu_unknown_rule_age_years"])
    return out


def extrapolation_noise(n: int, n_places: int, shared: float, seed: int) -> np.ndarray:
    """Standard-normal extrapolation noise (draws × places): √shared · z_d + √(1 − shared) · e_di (D-030).

    z_d is one number per draw, common to every place; e_di is each place's own. Every entry stays standard
    normal, so `hazard.widen` keeps each place's mean and spread; only the correlation between places,
    `shared`, changes. shared = 1: one z per draw; 0: independent per place (before D-030).
    """
    rng = np.random.default_rng(seed)
    common = rng.standard_normal((n, 1))
    own = rng.standard_normal((n, n_places))
    return np.sqrt(shared) * common + np.sqrt(1.0 - shared) * own


def state_effect(spec: Mapping[str, float] | None = None) -> tuple[np.ndarray, np.ndarray, frozenset[str]]:
    """config/params/adu_state_effect.yaml (D-044): τ's grid, its probabilities, and the fitted states.

    `spec` replaces the file (tests): keys adu_state_tau_prob__<τ, _ for .> and
    adu_state_effect_fitted__<ST>.
    Probabilities are renormalised (the file rounds them to 6 significant figures).
    """
    spec = spec if spec is not None else {k: s.value for k, s in load_params("adu_state_effect").items()}
    pairs = sorted(
        (float(k.removeprefix("adu_state_tau_prob__").replace("_", ".")), v)
        for k, v in spec.items()
        if k.startswith("adu_state_tau_prob__")
    )
    grid = np.array([t for t, _ in pairs])
    probs = np.array([q for _, q in pairs], dtype=float)
    fitted = frozenset(k.removeprefix("adu_state_effect_fitted__") for k, v in spec.items()
                       if k.startswith("adu_state_effect_fitted__") and v == 1)  # fmt: skip
    return grid, probs / probs.sum(), fitted


def state_noise(states, fitted, grid, probs, n: int, seed: int) -> np.ndarray:
    """τ_d · z_ds per draw and place (draws × places), the log state multiplier (D-043, D-044).

    τ_d is drawn from the grid once per draw; z_ds is one standard normal per draw and state, shared by the
    state's places. Places in a fitted state (or with no state) get 0: their spread is in the place effects.
    """
    states = pd.Series(states, dtype=object).reset_index(drop=True)
    out = np.zeros((n, len(states)))
    unseen = states.notna() & ~states.isin(fitted)
    if not unseen.any():
        return out
    rng = np.random.default_rng(seed)
    tau = rng.choice(grid, size=n, p=probs)
    names = sorted(states[unseen].unique())
    z = rng.standard_normal((n, len(names)))
    col = states[unseen].map({st: i for i, st in enumerate(names)}).to_numpy()
    out[:, unseen.to_numpy()] = tau[:, None] * z[:, col]
    return out
