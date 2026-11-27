### LB-NNN · 2026-10-20 · Build: baseline calibration fixes and state-total scoring (D-029)
- **Question:** Are the baseline's ranges calibrated for state totals, and do five defects found in review
  (cycle start, spec C centring, cycle variance counted twice, shared seeds, place-only scoring) explain the
  NC/TX under-forecast?
- **What I did:** pre-declared D-029 in `docs/analysis_plan.md` (own commit, before any run). Then in
  `model/baseline.py`: the cycle starts at the state's origin-year level (`cycle_start_at_origin`); 1/k and a
  place's own variance use counts divided by the state cycle index (`detrend_dispersion`, `cycle_index`);
  per-place draws get their own generator per state, size class and origin; `pit_step`, `step_share`,
  `crps_from_draws`. `model/demand.py`: spec C signals centred at fit-sample means (`DemandFit.multiplier`).
  `model/backtest.py`: state totals from draws summed draw by draw (`state_window`, `score_state`,
  `pit_histogram`, `--state-out`); V1 labelled a development set. Two flags in `config/params/baseline.yaml`.
- **Outputs:** the code above; tests in `tests/model/test_baseline_model.py`, `test_demand.py`,
  `test_backtest.py`; `docs/model_and_assumptions.md` (baseline steps, parameter table).
- **Findings:** synthetic common-cycle states: state-year P10–P90 coverage 72.5% → 81.5%, error/origin-gap
  correlation 0.52 → −0.17. V1 (MN NC OH TX, spec B): cells passing 17 → 19; place-level coverage and MAE
  about unchanged; state-total coverage single-family 47% → 85% (state-years) and 42% → 83% (5-year totals),
  mean/actual 0.75 → 0.86 (NC 0.69 → 0.80, TX 0.75 → 0.87). The gain comes from the cycle start; detrending
  is neutral to slightly negative on V1. In a stationary world the new start costs up to 5% MAE against the
  3-year mean (test relaxed, documented). Spec C (fixed) 17 cells; β still unstable.
- **Decisions:** D-029 (pre-declared; Ben to confirm adoption in the PR).
- **AI:** Claude Code wrote the pre-declaration, code, tests and runs; failing-on-old-code checked by running
  the new tests against `main`'s source. V1 outputs stayed in the session scratchpad (no data committed).
- **Open / next:** noisy origin totals (small states, 5+ units) suggest a local-level filter for the start;
  whether to adopt the new baseline, and to revisit spec C, is Ben's call.
