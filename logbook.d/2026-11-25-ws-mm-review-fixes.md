### LB-NNN · 2026-11-25 · Review · Two fixes to the missing-middle dose pools (thread 17, part A)

- **Question:** Do the missing-middle dose pools treat county remainders and new states as D-022 and D-102
  (b) intend?
- **Outputs:** `src/lotline/model/scenarios/mm.py` (`dose_pools`, `borrowed_pool`, `cost_index_at`,
  `log_sd`, `simulate`, `run`); tests in `tests/model/test_scenario_mm.py`; `docs/analysis_plan.md` deviation
  entry (2026-11-25); review log rows A12–A16.
- **Decision:** Ben, 2026-11-25: "Fix them here".
- **What Claude did and how it was checked:** Claude Code reviewed `mm.py` at high depth and fixed two real
  findings and three small ones. Tests check each by hand. Ran `lotline results` for all six states, one at a
  time, against `main` after #524: only missing middle moved (Wisconsin P50 −52%, NC within 1%, others
  unchanged).
