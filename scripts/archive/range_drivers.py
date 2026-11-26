#!/usr/bin/env python3
"""What drives each result's range: first-order sensitivity shares from the runs in the results bundles (#54).

    uv run python scripts/archive/range_drivers.py --results reports/results --out reports/range-drivers

For each state and scenario, the result is the five-year additional homes, net statewide, of each of the
bundle's runs (`results_draws`: lots × θ × pencil-out × completion × net-new × (1 − displacement), which
reproduces the bundle's totals exactly). The inputs are each run's own parameter draws, regenerated from the
scenario's configured seed (the same calls `adu.run`, `mm.run` and `fees.simulate` make), plus the
aggregate draws the bundle records (completion, net-new, displacement). `model.sensitivity.first_order`
gives each input's share of the spread of log(homes + 1): log, because the ranges are multiplicative
(P90 ÷ P10).

Nothing is rerun and no model code or config is changed. Run it after `lotline results`, on the same
commit, so the seeds and draws match. The script checks this exactly: the bundle's ADU net-new share is
adu_net_new_share × (1 − adu_formalization_share) of each run's draw, so the regenerated draws must give it
to 1e-9, or it stops.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.model import sensitivity as sens
from lotline.model.scenarios import adu, fees, mm

SCENARIOS = ["adu", "missing_middle", "fees", "fees_local_half"]
# Inputs that are a function of another input's draw, so they would be counted twice: the core-city term's
# shift is set by the drawn partial-rule share (D-097); the ADU net-new share is adu_net_new_share ×
# (1 − adu_formalization_share).
DERIVED = {"adu": {"adu_types_core_shift", "net_new_share"}}
LABELS = {
    "adu_mature_hazard_ref": "ADU uptake rate (how fast owners add ADUs once allowed; fitted)",
    "adu_partial_rule_share": "How much a partial ADU rule counts (partial-rule share m_x, with its refit)",
    "adu_place_effect_variance": "How much places differ from each other (α)",
    "adu_feasibility_dispersion": "How much lots differ in what an ADU costs and earns",
    "adu_net_new_share": "Share of ADUs that are new homes, not replacements",
    "adu_formalization_share": "Share of ADU permits that legalize an existing unit",
    "theta": "Missing-middle uptake rate (fitted)",
    "alpha": "How much places differ from each other (α, missing middle)",
    "units": "Homes per 2-4 unit building",
    "teardown_scale": "How often a new building replaces a house",
    "fee_permit_elasticity": "How strongly building responds to a fee cut (elasticity)",
    "land_capture_share": "Share of a fee cut that goes to landowners instead of builders",
    "hard_cost_per_sqft_usd": "Construction cost per square foot",
    "single_family_sqft": "Size of a new house",
    "operating_expense_share": "Operating costs as a share of rent",
    "cap_rate": "Cap rate (what investors pay for a dollar of rent)",
    "completion_factor": "Share of permitted homes that get finished",
    "net_new_share": "Share of homes that are new, not replacing one",
    "displacement_share": "Share that would have been built elsewhere in the state anyway",
    "other": "Not explained by any one input (place-to-place luck, rule draws, the unseen-state multiplier)",
}
BUNDLE_INPUTS = {
    "completion_factor": "Share of permitted homes that get finished",
    "net_new_share": "Share of homes that are new, not legalized or replacing one",
    "displacement_share": "Share that would have been built elsewhere in the state anyway",
}


def param_draws(scenario: str, n: int) -> pd.DataFrame:
    """Each run's own parameter draws, exactly as the scenario made them."""
    if scenario == "adu":
        central = adu.central_params()
        seed = int(central["adu_simulation_seed"])
        sets = adu.draw_params(n, seed)
        mode = int(central.get(adu.SHARE_DRAWS, 0))
        if mode:
            sets = adu.apply_partial_share_grid(
                sets, adu.partial_share_grid(), mode, seed, adu.specs()["adu_partial_rule_share"].value
            )
        return pd.DataFrame(sets)
    if scenario == "missing_middle":
        sp = mm.specs()
        return mm.draw_params(n, int(sp["mm_scenario_seed"].value), sp)
    return pd.DataFrame(fees.draw_params(n, int(fees.central_params()["fee_simulation_seed"])))


def homes(d: pd.DataFrame) -> np.ndarray:
    lots = d["eligible_tier1"] + d["eligible_tier2"] + d["eligible_tier3"]
    h = lots * d["theta"] * d["pencil_out_share"] * d["completion_factor"] * d["net_new_share"]
    return (h * (1 - d["displacement_share"])).to_numpy(dtype=float)


def run(results: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(results.glob("*/bundle.json")):
        b = json.loads(path.read_text())
        st = b["meta"]["state"]
        draws = pd.DataFrame(b["draws"])
        for sc in SCENARIOS:
            d = draws[draws["scenario"] == sc].sort_values("draw").reset_index(drop=True)
            n = len(d)
            p = param_draws(sc, n)
            if sc == "adu":
                want = p["adu_net_new_share"] * (1 - p["adu_formalization_share"])
                if not np.allclose(want.to_numpy(), d["net_new_share"].to_numpy(), rtol=0, atol=1e-9):
                    raise SystemExit(f"{st}: the regenerated ADU draws do not match the bundle's runs")
            y = np.log1p(homes(d))
            inputs = {k: p[k].to_numpy(dtype=float) for k in p.columns}
            inputs |= {k: d[k].to_numpy(dtype=float) for k in BUNDLE_INPUTS}
            inputs = {k: v for k, v in inputs.items() if k not in DERIVED.get(sc, set())}
            shares = sens.drivers(inputs, y)
            spread = float(np.exp(np.percentile(y, 90)) / max(np.exp(np.percentile(y, 10)), 1e-9))
            for k, s in shares.items():
                rows.append({"state": st, "scenario": sc, "input": k, "label": LABELS.get(k, k),
                             "share": round(s, 4),
                             "p90_over_p10": round(spread, 2), "draws": n})  # fmt: skip
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--results", type=Path, default=Path("reports/results"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t = run(a.results)
    t.to_csv(a.out / "drivers.csv", index=False)
    top = (
        t[t["input"] != "other"].sort_values("share", ascending=False).groupby(["state", "scenario"]).head(3)
    )
    print(top.to_string(index=False))
    print(t[t["input"] == "other"][["state", "scenario", "share"]].to_string(index=False))


if __name__ == "__main__":
    main()
