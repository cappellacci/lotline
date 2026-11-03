### LB-NNN · 2026-11-03 · engine · Does the ADU anchor predict state totals? (D-040)

- **Question:** D-039 found city-level ADU predictions too wide and centred too low for big adopters. Do the
  errors cancel in state totals, which are the tool's headline numbers?
- **Outputs:** `docs/analysis_plan.md` D-040 (plan written and committed before the run, results after);
  `src/lotline/model/calibrate_adu.py` `predict_places` (joint draws: shared θ, independent place effects);
  `scripts/dev/calibrate_adu.py --statewide`; tests in `tests/model/test_calibrate_adu.py` and
  `tests/model/test_statewide_backtest.py`; `reports/adu-statewide/` (log, `statewide.csv`, draws).
- **Result:** leave one state out, 1 of 4 state totals useful (NC towns), MN over-predicted 3.6×, TX
  under-predicted 8.7×. The anchor does not yet transfer to an unseen state. Exploratory grouping points to a
  central-city vs suburb modifier.
- **What Claude did and how it was checked:** wrote the entry before the run; found that summing
  `predict_place` draws would give every place the same place effect, and wrote `predict_places` with a test
  of the variance and correlation against hand-worked values; tested the verdict bar and state sums by hand;
  ran once. The exploratory grouping is labelled as chosen after seeing the results.
