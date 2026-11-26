"""The fee scenario on the scenario contract (`scenarios/__init__.py`): what `fees.simulate` adds to the
bundle, twice, as D-065 labels them: `fees`, the Handbook benchmark ($50,000 cut in half), and
`fees_local_half`, real local fees cut in half. Run over every place the baseline forecasts (D-076).
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.model.scenarios import Inputs, ScenarioRun, year_shares_of

NAME = "fees"
ORDER = 30
LABELS = {
    "title": "Fee reduction",
    "definition": "Cut the one-time development fees a builder pays per new home by half.",
    "handbook": "total development fees cut 50% from a $50,000/unit baseline.",
}
VARIANTS = {
    "fees": {
        "variant": "handbook",
        "title": "Fee reduction",
        "definition": "Benchmark: a $50,000 fee cut in half",
    },
    "fees_local_half": {
        "variant": "local_half",
        "title": "Fee reduction, real local fees",
        "definition": "Real local fees cut in half",
    },
}
TABLES = ("fee_types",)
TYPES_FOR = "local_half"  # the variant whose sizes feed the fee section's slider (D-077)


def from_sim(sim: Mapping, tier: int, variant: str = "handbook") -> ScenarioRun:
    """The `results_draws` factors from `scenarios.fees.simulate` (D-065, D-076).

    A fee cut opens no lots, so the funnel's first stage holds homes instead: eligible = the five-year
    baseline homes in the building sizes a cut covers (1, 2 and 3-4 units; 5+ take no dose, D-073), all in
    the state's data tier; pencil-out share = 1; θ = five-year homes added ÷ those homes (the cut's % change,
    ramp included). Completion single-family for 1-unit homes and multifamily for 2-4, weighted by that
    draw's added homes; net-new share = 1 (the model adds new buildings and tears none down).

    By hand: 10,000 covered homes, 150 added (120 houses, 30 in 2-4 unit buildings), completion 0.95 and
    0.85 -> θ 0.015, completion 0.93; `aggregate.homes_from_draws` gives 150 permits and 139.5 homes in place.
    """
    n = sim["n"]
    by_class = sim["added_by_class"]
    if by_class:
        covered = sum(sim["by_size"][c].sum() for c in by_class)
        sf = by_class["1"].sum(axis=(1, 2))
        mf = sum(by_class[c].sum(axis=(1, 2)) for c in by_class if c != "1")
    else:  # no size split: every unit takes the house's dose (D-032)
        covered = sim["base"].sum()
        sf = sim["added"].sum(axis=(1, 2))
        mf = np.zeros(n)
    added = sf + mf
    return ScenarioRun(
        eligible=tuple(covered if t == tier else 0.0 for t in (1, 2, 3)),
        theta=added / covered if covered > 0 else np.zeros(n),
        pencil_out_share=1.0,
        net_new_share=1.0,
        completion={"single_family": sf, "multifamily": mf},
        year_shares=year_shares_of(np.asarray(sim["added"], dtype=float).sum(axis=1)),
        raw={"sim": sim, "variant": variant},
    )


def run(inputs: Inputs, variant: str) -> ScenarioRun:
    from lotline.model import fee_inputs
    from lotline.model.scenarios import fees

    st, origin = inputs.state, inputs.origin
    places = inputs.shared("fee_places", lambda: fee_inputs.statewide_places(st, inputs.store, origin))
    sim = fees.simulate(places, origin, mode=variant, draws=inputs.draws)
    out = from_sim(sim, inputs.data_tier, variant)
    out.raw.update(places=places, origin=origin, draws=inputs.draws)
    return out


def size_types(run: ScenarioRun) -> pd.DataFrame:
    """`results_fee_types` rows at the half cut, for `TYPES_FOR` (empty otherwise, or without a size split):
    per size and draw the homes added, that size's completion draw (the ones results drew) and baseline."""
    from lotline.model import results

    sim, c = run.raw["sim"], run.completion_draws
    by_class = sim["added_by_class"]
    types = pd.DataFrame(columns=list(results._columns("fee_types")))
    if run.raw["variant"] != TYPES_FOR or not by_class:
        return types
    n = sim["n"]
    return pd.concat(
        [
            pd.DataFrame(
                {
                    "scenario": run.scenario,
                    "size": k,
                    "draw": np.arange(n),
                    "fee_change_share": 0.5,
                    "units_added": by_class[k].sum(axis=(1, 2)),
                    "completion_factor": c["single_family"] if k == "1" else c["multifamily"],
                    "baseline_homes": float(sim["by_size"][k].sum()),
                }
            )
            for k in by_class
        ],
        ignore_index=True,
    )


def extra_tables(run: ScenarioRun) -> dict[str, pd.DataFrame]:
    """`results_fee_types`: the half-cut rows, plus every slider stop for a size not linear in the cut."""
    from lotline.model import results

    raw = run.raw
    types = results.fee_types_with_stops(raw["places"], raw["origin"], raw["draws"], size_types(run))
    return {"fee_types": types}
