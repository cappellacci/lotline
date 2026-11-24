### LB-NNN · 2026-11-23 · APP · Can the ADU chart show which part of the no-change forecast is counted and which is estimated?

- **Question:** judges will ask why NC's no-change ADU forecast sits above its permit history. Can the chart
  show it?
- **Outputs:**
  - `results_adu_baseline` basis and mean (schemas 1.21) in `src/lotline/schemas.py` and
    `adu_baseline_years` in `src/lotline/model/results.py`;
  - the split bars, the no-change whisker and the relabelled history in `recordHtml`
    (`src/lotline/app/template.html`);
  - a test in `tests/model/test_results.py`;
  - app note in `docs/analysis_plan.md` (2026-11-23).
- **What Claude did and how it was checked:**
  - Hand-worked test: the means add up and the old shape is kept without `own`.
  - 769 app, core and results tests pass.
  - Built NC's bundle and checked the chart in the browser. The own-count group's mean (298) equals its
    2023-25 pace, the plain-language point for judges.
  - Also fixed #510's schema-version test, which failed in CI because `tests/core` had not been run locally.
