### LB-NNN · 2026-11-25 · Review · Baseline: forecast places with a short history or no lot count (thread 17, part A)

- **Question:** Why does the baseline leave some places out, and can they be forecast?
- **Outputs:** `src/lotline/model/baseline.py` (`level_estimates`, `cycle_index`, `forecast_draws`);
  `config/params/baseline.yaml` (`level_min_years`, `count_only_places`); tests in
  `tests/model/test_baseline_model.py`; `docs/model_and_assumptions.md` parameter table;
  `docs/analysis_plan.md` deviation entry (2026-11-25); review log rows A20–A21.
- **Decision:** Ben, 2026-11-25: "Model them too". Proposed HANDOFF decision in the PR.
- **What Claude did and how it was checked:** Claude Code reviewed `baseline.py` and `results.py`, found which
  places the baseline drops and why (new to BPS, or no eligible-parcel count), and added two routes behind
  config switches. Hand-worked tests check each route. Ran `lotline results` for all six states, one at a
  time: coverage of origin-year homes is now 99.6% or more everywhere; Ohio's baseline P50 +4.5%; ADU and
  missing middle unchanged. The V1 backtest was not rerun.
