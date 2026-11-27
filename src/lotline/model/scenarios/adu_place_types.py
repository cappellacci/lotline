"""ADU place types (D-088, D-089): the core-city multiplier and the town prior. Part of `scenarios.adu`; the
method is in that module's docstring.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model.scenarios.adu_params import Z_90

TYPE_FILE = "adu_place_types"
CORE, TOWN = "core", "town"


def type_terms(spec: Mapping[str, float] | None = None) -> dict[str, float]:
    """The core-city term's estimate and SE, and the town prior's SD, from config/params/adu_place_types.yaml
    (`spec` replaces the file: keys as there, each a value or a (value, low, high) tuple).
    se = (high − low) / (2 × 1.645). By hand: 1.199 (0.546-1.898) -> se 1.352 / 3.2897 = 0.4110."""
    if spec is None:
        p = load_params(TYPE_FILE)
        c = p["adu_types_core_log_multiplier"]
        core = (c.value, c.low, c.high)
        town = p["adu_types_town_prior_sd"].value
    else:
        core = spec["adu_types_core_log_multiplier"]
        core = tuple(core) if isinstance(core, (tuple, list)) else (core, core, core)
        town = spec["adu_types_town_prior_sd"]
    return {"core": float(core[0]), "core_se": (core[2] - core[1]) / (2 * Z_90), "town_sd": float(town)}


def central_type_log_multiplier(types, spec: Mapping[str, float] | None = None) -> np.ndarray:
    """Each place's log multiplier at central values: β̂_core for a core city, 0 otherwise (the town prior's
    centre is the suburb rate)."""
    tt = type_terms(spec)
    types = pd.Series(types, dtype=object).reset_index(drop=True)
    return np.where(types == CORE, tt["core"], 0.0)


def type_log_multipliers(types, states, n: int, seed: int, spec=None) -> np.ndarray:
    """Log hazard multiplier per draw and place (draws × places), D-088 and D-089:

    - core city: β_d ~ N(β̂_core, se), one per draw, shared by every core city;
    - town: s × z_ds, z standard normal, one per draw and state (shared by the state's towns), s the town
      prior's SD;
    - suburb, or a place with no type: 0.

    By hand with se and s at 0: a core city gets β̂ in every draw, a town 0.
    """
    tt = type_terms(spec)
    types = pd.Series(types, dtype=object).reset_index(drop=True)
    states = pd.Series(states, dtype=object).reset_index(drop=True).fillna("")
    rng = np.random.default_rng(seed)
    core = rng.normal(tt["core"], tt["core_se"], size=n)
    out = np.zeros((n, len(types)))
    is_core = (types == CORE).to_numpy()
    out[:, is_core] = core[:, None]
    is_town = (types == TOWN).to_numpy()
    if is_town.any():
        names = sorted(states[is_town].unique())
        z = rng.standard_normal((n, len(names)))
        col = states[is_town].map({st: i for i, st in enumerate(names)}).to_numpy()
        out[:, is_town] = tt["town_sd"] * z[:, col]
    return out
