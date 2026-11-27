### LB-NNN · 2026-11-03 · engine · Can the results dashboard show the calibration runs?

- **Question:** Ben asked for the dashboard (LB fragment `2026-11-03-ws-engine-14-dashboard.md`, PR #270) to show
  the latest runs after D-041. It only read effect-estimate runs (D-024, D-025).
- **What I did:**
  - `src/lotline/model/runs.py` reads calibration runs (manifest `kind: calibration`):
    - fits, with θ per 1,000 and α;
    - held-out state totals with their verdicts;
    - leave-one-place-out place totals, with coverage and error against no effect;
    - test places;
    - counts and the market term.

    It handles both layouts: the ADU calibration (`calibrate_adu.py`) and D-038's (`calibrate_mm.py`).
  - `src/lotline/model/dashboard.html`:
    - a headline tile for each calibration run;
    - five new sections: θ by fit, state totals (log scale), observed against predicted by place, test
      places, and counts and the market term;
    - each section shows only for the kind of run selected.
  - Hand-written manifests for:
    - `reports/adu-anchor-4state` (D-039);
    - `reports/adu-statewide` (D-040);
    - `reports/adu-counts` (D-041);
    - `reports/mm-d038` (D-038). Its CSVs are on PR #272's branch, so until that merges its card shows the
      manifest only.
- **Outputs:**
  - The files above, `tests/model/test_runs.py` (4 new tests) and a regenerated `reports/dashboard/index.html`.
  - Branch `ws/engine-14-dashboard-calib` = D-041's branch + the dashboard branch.
- **AI:** Claude Code (Opus 5.5) wrote the code, tests and manifests. Checks:
  - Hand-worked tests for each layout.
  - The reader reproduces the logged backtest numbers: D-039 48/51 places, 0.149 vs 0.141; D-041 47/51,
    0.099 vs 0.098; D-038 8/12, 0.235 vs 0.234.
  - The page was viewed in a browser with D-038's CSVs copied in: light and dark, desktop and phone width,
    calibration and mixed selections. One fix came from this: crowded log-axis labels at phone width.
  - Readings in the manifests repeat the analysis plan and are marked for Ben to confirm.
