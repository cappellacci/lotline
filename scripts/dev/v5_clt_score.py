#!/usr/bin/env python3
"""Score V5 (analysis plan D-071) against Mecklenburg County's unblinded BPS 2023-2025.

    uv run python scripts/dev/v5_clt_score.py        # writes reports/v5-charlotte/

1. Regenerates the frozen draws (same code, inputs, draws and seed as `v5_clt_predict.py --freeze`) and stops
   unless their summaries equal results/frozen/V5-NC-CHARLOTTE.json, so scoring uses exactly what was frozen.
   The inputs read only years to 2022 and the pre-window roll, so the release does not move them.
2. Reads BPS 37119 for 2023-2025 from the raw Census files through the holdout filter, which no longer hides
   V5 once it is released in config/states/nc.yaml (released_on). Refuses if V5 is not released.
3. Scores the pass rule (observed 2023-2025 sum within P10-P90) and D-071's other measures; homes as the
   secondary target. The no-reform benchmark is Poisson(B) each year.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from lotline.adapters.national import bps
from lotline.io import DataStore
from lotline.validation import holdout, v5

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "v5-charlotte"
BENCH_SEED = 1


def main() -> None:
    h = {x.test_id: x for x in holdout.holdouts_for(v5.STATE)}[v5.TEST_ID]
    if not h.released_on:
        raise SystemExit(f"{v5.TEST_ID} is not released in config/states/nc.yaml")
    frozen = json.loads(holdout.frozen_path(v5.TEST_ID, REPO).read_text())
    store = DataStore()
    inp = v5.inputs(store)
    d = v5.draws(inp, frozen["draws"], frozen["seed"])
    if json.dumps(v5.summarize(d), sort_keys=True) != json.dumps(frozen["prediction"], sort_keys=True):
        raise SystemExit(f"regenerated draws differ from the freeze; run from commit {frozen['commit']}")

    bld, hom = v5.observed(bps.load(v5.STATE, store))
    n = frozen["draws"]
    bench = np.random.default_rng(BENCH_SEED).poisson(inp.B, size=(n, len(v5.YEARS))).astype(float)
    bench_h = bench * inp.homes_per_baseline_building
    span = f"{v5.YEARS[0]}-{v5.YEARS[-1]}"
    res = {
        "test_id": v5.TEST_ID,
        "method": "analysis plan D-071",
        "frozen_commit": frozen["commit"],
        "observed": {"buildings": bld, "homes": hom},
        "baseline_per_year": inp.B,
        "primary": {span: v5.score(d["buildings"].sum(1), sum(bld.values()), bench.sum(1))}
        | {str(y): v5.score(d["buildings"][:, j], bld[y], bench[:, j]) for j, y in enumerate(v5.YEARS)},
        "secondary_homes": {span: v5.score(d["homes"].sum(1), sum(hom.values()), bench_h.sum(1))}
        | {str(y): v5.score(d["homes"][:, j], hom[y], bench_h[:, j]) for j, y in enumerate(v5.YEARS)},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "score.json").write_text(json.dumps(res, indent=2) + "\n")
    print(f"wrote {OUT / 'score.json'}")
    for k in ("primary", "secondary_homes"):
        for per, s in res[k].items():
            print(
                f"  {k} {per}: observed {s['observed']:,.0f}  P10 {s['p10']:,.0f}  P50 {s['p50']:,.0f}  "
                f"P90 {s['p90']:,.0f}  pass {s['pass']}  {s['verdict']}  pct {s['percentile']:.0f}  "
                f"CRPS {s['crps_model']:.1f} vs no-reform {s.get('crps_no_reform', float('nan')):.1f}"
            )


if __name__ == "__main__":
    main()
