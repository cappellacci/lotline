"""A toy scenario for the scenario-contract test (#554): a fixed number of homes per eligible lot.

It is registered only in tests (`lotline.model.scenarios.registered`), never in the real bundle. It shows
that a new reform is one module: with nothing else edited it appears in the bundle's draws, totals and
`meta.scenarios`, and in the app built from that bundle.
"""

from __future__ import annotations

import numpy as np

from lotline.model.scenarios import Inputs, ScenarioRun

NAME = "toy"
ORDER = 90  # after the built-in scenarios, so their shared draws are unchanged
LABELS = {
    "title": "Toy reform",
    "definition": "A test reform: one home for every 100 eligible lots over five years.",
    "handbook": None,
}
VARIANTS = {"toy": "fixed"}
HOMES_PER_LOT = 0.01  # five-year homes permitted per eligible lot


def run(inputs: Inputs, variant: str) -> ScenarioRun:
    places, n = inputs.places, inputs.draws
    tiers = places["data_tier"] if "data_tier" in places else 3
    lots = places["eligible_parcels"].groupby(tiers).sum()
    eligible = tuple(np.full(n, float(lots.get(t, 0.0))) for t in (1, 2, 3))
    added = sum(eligible) * HOMES_PER_LOT
    return ScenarioRun(
        eligible=eligible,
        theta=HOMES_PER_LOT,
        pencil_out_share=1.0,
        net_new_share=1.0,
        completion={"single_family": added},
        year_shares=np.full((n, 5), 0.2),
    )
