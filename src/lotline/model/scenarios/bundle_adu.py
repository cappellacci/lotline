"""The ADU scenario on the scenario contract (`scenarios/__init__.py`): what `adu.run` adds to the bundle.

The model is `adu.py` (owner: the ADU methodology session); this module only reshapes its draws.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.model.scenarios import Inputs, ScenarioRun, year_shares_of
from lotline.model.scenarios.adu_params import net_new_homes

NAME = "adu"
ORDER = 10
LABELS = {
    "title": "ADUs",
    "definition": "Allow one accessory dwelling unit (a backyard cottage, garage or basement apartment) on "
    "every lot with one house.",
    "handbook": "one ADU per parcel with an existing single-family building; detached/semi-detached "
    "≥600 sq ft allowed; no added parking.",
}
VARIANTS = {"adu": "handbook"}
TABLES = ("adu_place_types", "adu_baseline")


def from_draws(places: pd.DataFrame, run_draws: Mapping) -> ScenarioRun:
    """The `results_draws` factors from `adu.run(..., return_draws=True)`'s last element.

    Per draw d: eligible by data tier (after the D-056 scale where applied); pencil-out share = the eligible-
    weighted mean of the pro forma's feasible share; θ = five-year permits added ÷ (eligible × pencil-out);
    net-new share = adu_net_new_share × (1 − adu_formalization_share) of that draw; completion single-family.
    """
    elig = np.asarray(run_draws["eligible"], dtype=float)  # draws x places
    n = elig.shape[0]
    tiers = places["data_tier"].to_numpy() if "data_tier" in places else np.full(elig.shape[1], 3)
    by_tier = tuple(elig[:, tiers == t].sum(axis=1) for t in (1, 2, 3))
    total = elig.sum(axis=1)
    pencils = (elig * np.asarray(run_draws["pencil"], dtype=float)).sum(axis=1)
    pencil_share = np.divide(pencils, total, out=np.zeros(n), where=total > 0)
    added = np.asarray(run_draws["added"], dtype=float).sum(axis=(1, 2))
    theta = np.divide(added, pencils, out=np.zeros(n), where=pencils > 0)
    sets = run_draws["params"]
    net_new = np.array([net_new_homes(1.0, p) for p in sets])
    return ScenarioRun(
        eligible=by_tier,
        theta=theta,
        pencil_out_share=pencil_share,
        net_new_share=net_new,
        completion={"single_family": added},
        year_shares=year_shares_of(np.asarray(run_draws["added"], dtype=float).sum(axis=1)),
        raw={"places": places, "draws": run_draws},
    )


def run(inputs: Inputs, variant: str) -> ScenarioRun:
    from lotline.model.scenarios import adu

    places = inputs.places
    _, totals, run_draws = adu.run(
        places, inputs.origin, draws=inputs.draws, eligible_proxy=inputs.eligible_proxy, return_draws=True
    )
    out = from_draws(places, run_draws)
    out.raw = {**out.raw, "totals": totals, "state": inputs.state, "origin": inputs.origin}
    return out


def extra_tables(run: ScenarioRun) -> dict[str, pd.DataFrame]:
    from lotline.model import results

    raw = run.raw
    places, run_draws, st = raw["places"], raw["draws"], raw["state"]
    own = places["observed_rate"].notna().to_numpy()
    return {
        "adu_place_types": results.adu_place_type_table(st, places, run_draws),
        "adu_baseline": results.adu_baseline_years(st, run_draws, raw["origin"], own=own),
    }
