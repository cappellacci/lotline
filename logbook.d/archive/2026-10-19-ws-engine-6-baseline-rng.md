### LB-NNN · 2026-10-19 · Build: baseline cycle draws shared across size classes; mean kept flat (D-011)
- **Question:** Do the baseline's random numbers couple size classes by design, and does the mean drift?
- **What I did:** in `src/lotline/model/baseline.py`, drew one matrix of cycle calendar years per state,
  origin and draw from its own seeded generator (`cycle_years`, `cycle_factor`), shared by all size classes
  and scenarios; centred the shocks by log(mean(exp(x))) instead of mean(x) (`cycle_shock_series`). Added
  tests for both (each fails on the old code) and updated the hand-worked shock test. Re-ran the V1 backtest
  three ways (before, fix (a) only, both).
- **Inputs:** judging panel 2026-10-19 MS-06, MS-07; processed BPS panels for MN NC OH TX (holdout-filtered).
- **Outputs:** `src/lotline/model/baseline.py`, `tests/model/test_baseline_model.py`, `docs/analysis_plan.md`
  (D-011).
- **Findings:** V1 spec B goes from 17 to 13 of 48 cells; (a) alone changes nothing (17 cells, MAE equal to
  3 decimals); (b) moves the mean down, and the bias test (on the mean) fails in 5 more cells (26 → 21 OK).
  MAE: single-family 10.08 → 10.13, 5+ 2.82 → 2.77. The old mean drift was partly hiding a post-2022
  under-forecast.
- **Decisions:** D-011 (Ben accepted MS-06/MS-07, 2026-10-19; drop in pass count flagged for Ben).
- **AI:** Claude wrote the change and tests; checked that the new tests fail on the old code (correlation
  −0.02 old vs 0.77 new for differing place sets) and ran the backtest before and after.
- **Open / next:** the place-level gamma and count draws still share one generator across places and states,
  so they depend on which places are present (coupling now does not); draw rents and values jointly (MS-06
  last point); address the post-2022 under-forecast.
