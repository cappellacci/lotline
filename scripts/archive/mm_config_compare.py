#!/usr/bin/env python3
"""Statewide five-year added homes, D-055 values against C4 (same places, seed, draws).

    uv run python scripts/archive/mm_config_compare.py reports/mm-d092/config-c4/compare.json

Origin 2025; the Handbook scenario at config (C4) and with D-055's θ, α and half-way point (Poisson years).
Reads rolls, rules, ACS and market series only; no permits.
"""

import json
import sys
import time
from types import SimpleNamespace

import numpy as np

from lotline.io import DataStore
from lotline.model.scenarios import mm

sp = mm.specs()
n, seed = int(sp["mm_scenario_draws"].value), int(sp["mm_scenario_seed"].value)
OLD = {
    "mm_mature_hazard_ref": (0.0001235, 0.0000325, 0.001006),
    "mm_place_effect_variance": (8.415, 2.80, 32.4),
}
old_sp = dict(sp)
for k, (v, lo, hi) in OLD.items():
    old_sp[k] = SimpleNamespace(value=v, low=lo, high=hi)
store, out = DataStore(), {}
for st in ("MN", "NC", "OH", "TX", "OR"):
    t = time.time()
    places = mm.places_from_store(st, store, 2025)
    r = {}
    for name, p, half, phi in (
        ("D-055", old_sp, 0.5, None),
        ("C4", sp, sp["mm_ramp_half_years"].value, sp["mm_year_spread_phi"].value),
    ):
        res = mm.simulate(
            places,
            mm.draw_params(n, seed, p),
            half,
            sp["mm_ramp_slope_years"].value,
            seed,
            int(sp["mm_rule_min_coded"].value),
            phi=phi,
        )
        for meas, arr in (("buildings", res.buildings), ("homes_net", res.homes_net)):
            x = arr.sum(1)
            r[f"{name} {meas}"] = [round(float(v)) for v in np.percentile(x, [10, 50, 90])] + [
                round(float(x.mean()))
            ]
        r[f"{name} year5_share"] = round(float(res.homes_net[:, 4].mean() / res.homes_net.sum(1).mean()), 3)
    out[st] = r
    print(st, f"{time.time() - t:.0f}s", json.dumps(r), flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
