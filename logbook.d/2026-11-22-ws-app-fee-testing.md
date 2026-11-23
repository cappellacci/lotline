### LB-NNN · 2026-11-22 · APP · Can a policymaker try their own fee change in the app?

- **Question:** the app's Fee reduction tab showed two fixed cases. Can a user change the size of the fee change
  and aim it at one kind of home (D-077), with the same model runs and ranges?
- **Outputs:**
  - `results_fee_types` (schemas 1.20) in `src/lotline/schemas.py`;
  - `fee_rows_and_types` and the build-time check `check_fee_line` in `src/lotline/model/results.py`;
  - `fee_policy_draws` in `src/lotline/model/aggregate.py` and `feePolicyDraws` in
    `src/lotline/app/aggregate.js`;
  - the "Try a different fee change" box in `src/lotline/app/template.html`;
  - tests in `tests/model/test_results.py` and `tests/app/test_aggregate_parity.py`;
  - app note in `docs/analysis_plan.md` (2026-11-22).
- **What Claude did and how it was checked:**
  - Measured that homes added are exactly linear in the fee change in every draw (NC, 100 draws; sd of the
    ratio 0), so the bundle carries only the half cut by size.
  - Wrote hand-worked tests and JS-Python parity tests, including that the default reproduces the engine's
    draws exactly.
  - Built NC's bundle; the linearity check passes on real data.
  - Drove the page in the browser: abolish doubles the half cut, a 50% rise loses it, duplexes-only works,
    Reset restores, and the headline follows.
  - A state whose bundle predates the table hides the box.
