### LB-NNN · 2026-11-15 · ws/adu-engine-drift · D-093: the engine reads D-091's outcome

- **Question:** What happens to the statewide ADU results when places with their own ADU counts take their
  no-reform rate from those counts with drift, and the bill's effect from the model's ratio?
- **Answer:** Additional homes move under 10% at P50 in every state (TX +9%, OH +8%); the no-reform baseline
  falls in MN, NC, OH and TX and its top end roughly halves; OR rises a little.
- **Outputs:** `src/lotline/model/scenarios/adu.py` (`own_rate_draws`, `own_rate_central`, `own_rate_paths`),
  `config/params/adu.yaml` (`adu_own_rate_drift`, `adu_drift_sigma`), `tests/model/test_adu_own_rate.py`,
  `scripts/dev/adu_engine_drift_check.py`, `scripts/dev/adu_engine_drift_page.py`, `reports/adu-engine-drift/`,
  D-093 in `docs/analysis_plan.md`, a row in `docs/model_and_assumptions.md`. Page:
  https://claude.ai/artifact/RbG2SiXAtPKiJY1xMoyTQV
- **Claude's part:** wrote the code, tests, check script and page; built on #434 after the missing-middle
  session handed ADU work over; checked with hand-worked tests, the switch-off identity and the model suite.
