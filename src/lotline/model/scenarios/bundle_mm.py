"""The missing-middle scenario on the scenario contract (`scenarios/__init__.py`): what `mm.run` adds to the
bundle (D-063).

The model is `mm.py` (owner: the Missing Middle Analysis session); this module only reshapes its draws.
"""

from __future__ import annotations

import numpy as np

from lotline.model.scenarios import Inputs, ScenarioRun, year_shares_of

NAME = "missing_middle"
ORDER = 20
LABELS = {
    "title": "Missing middle",
    "definition": "Allow small buildings of 2 to 6 homes (duplexes to small apartment buildings) on lots "
    "zoned for single-family homes only.",
    "handbook": "2–6 units on single-family-only parcels, up to 3 stories; setbacks and lot coverage assumed "
    "not to constrain.",
}
VARIANTS = {"missing_middle": "handbook"}


def from_result(res) -> ScenarioRun:
    """The `results_draws` factors from `scenarios.mm.simulate`'s `Result` (D-063).

    Per draw d: legal = parcels the Handbook rule newly opens, E × (1 − current dose), by data tier;
    pencil-out share = their feasible-share-weighted mean F(PCR); θ = five-year homes permitted (gross, in
    the added 2-4 unit buildings) ÷ pencil-out parcels; net-new share = 1 − houses torn down ÷ homes
    permitted, that draw's; completion multifamily.

    By hand: legal 1,000 in tier 1, pencils 400, 20 homes in 8 buildings that replace 6 houses -> θ 0.05,
    pencil-out 0.4, net-new 0.7; `aggregate.homes_from_draws` then gives 20 permits and 14 × completion homes.
    """
    legal = np.asarray(res.legal, dtype=float)
    n = legal.shape[0]
    total = legal.sum(axis=1)
    pencils = np.asarray(res.pencils, dtype=float)
    gross = res.homes_gross.sum(axis=1)
    torn = res.teardowns.sum(axis=1)
    return ScenarioRun(
        eligible=(legal[:, 0], legal[:, 1], legal[:, 2]),
        theta=np.divide(gross, pencils, out=np.zeros(n), where=pencils > 0),
        pencil_out_share=np.divide(pencils, total, out=np.zeros(n), where=total > 0),
        net_new_share=np.divide(gross - torn, gross, out=np.ones(n), where=gross > 0),
        completion={"multifamily": gross},
        year_shares=year_shares_of(res.homes_gross),
        raw=res,
    )


def run(inputs: Inputs, variant: str) -> ScenarioRun:
    from lotline.model.scenarios import mm

    _, res, _ = mm.run(inputs.state, inputs.store, inputs.origin, n=inputs.draws)
    return from_result(res)
