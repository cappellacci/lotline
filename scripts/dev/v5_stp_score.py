#!/usr/bin/env python3
"""Score V5 St. Paul (analysis plan D-098) against St. Paul's unblinded BPS 2024-2025.

    uv run python scripts/dev/v5_stp_score.py        # writes reports/v5-stpaul/

Run only after the freeze is on main and Ben has asked to unblind (the release goes in config/states/mn.yaml).

1. Regenerates the frozen draws (same code, inputs, draws and seed as `v5_stp_predict.py --freeze`) and stops
   unless their summaries equal results/frozen/V5-MN-STPAUL.json, so scoring uses exactly what was frozen.
   The inputs read only years to 2023 and the 2023 roll and zoning snapshot, so the release does not move
   them.
2. Reads BPS 2758000 for 2024-2025 (and 2026 once published) from the raw Census files through the holdout
   filter, which no longer hides V5 once it is released. Refuses if V5 is not released.
3. Scores the pass rule (observed 2024-2025 sum within P10-P90) and D-098's other measures; homes as the
   secondary target. The no-reform benchmark is the baseline part of the same draws (D-098).
"""

from __future__ import annotations

import json
from pathlib import Path

from lotline.adapters.national import bps
from lotline.io import DataStore
from lotline.validation import holdout, v5
from lotline.validation import v5_stpaul as stp

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "v5-stpaul"


def main() -> None:
    h = {x.test_id: x for x in holdout.holdouts_for(stp.STATE)}[stp.TEST_ID]
    if not h.released_on:
        raise SystemExit(f"{stp.TEST_ID} is not released in config/states/mn.yaml")
    frozen = json.loads(holdout.frozen_path(stp.TEST_ID, REPO).read_text())
    store = DataStore()
    inp = stp.inputs(store)
    d = stp.draws(inp, frozen["draws"], frozen["seed"])
    if json.dumps(stp.summarize(d), sort_keys=True) != json.dumps(frozen["prediction"], sort_keys=True):
        raise SystemExit(f"regenerated draws differ from the freeze; run from commit {frozen['commit']}")

    table = bps.load(stp.STATE, store)
    years = stp.scorable_years(table)
    if not set(stp.PASS_YEARS) <= set(years):
        raise SystemExit(f"BPS has St. Paul rows for {years} only; the pass rule needs {stp.PASS_YEARS}")
    bld, hom = v5.observed(table, geoid=stp.ST_PAUL, years=years)
    idx = {y: j for j, y in enumerate(stp.YEARS)}
    bench = d["baseline"]
    bench_h = bench * inp.homes_per_baseline_building

    def block(key: str, obs: dict, b) -> dict:
        span = [idx[y] for y in stp.PASS_YEARS]
        out = {
            f"{stp.PASS_YEARS[0]}-{stp.PASS_YEARS[-1]}": v5.score(
                d[key][:, span].sum(1), sum(obs[y] for y in stp.PASS_YEARS), b[:, span].sum(1)
            )
        }
        return out | {str(y): v5.score(d[key][:, idx[y]], obs[y], b[:, idx[y]]) for y in years}

    res = {
        "test_id": stp.TEST_ID,
        "method": "analysis plan D-098",
        "frozen_commit": frozen["commit"],
        "years_scored": list(years),
        "observed": {"buildings": bld, "homes": hom},
        "baseline_per_year": inp.B,
        "primary": block("buildings", bld, bench),
        "secondary_homes": block("homes", hom, bench_h),
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
