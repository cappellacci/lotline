### LB-NNN · 2026-11-25 · Review · Three fixes to the ADU rule priors (thread 17, part A)

- **Question:** Do the ADU engine's rule priors do what D-022 and D-102 (b) say, for a new state, for a place
  with a gap, and for county remainders?
- **Outputs:**
  - `src/lotline/model/scenarios/adu.py` (`rule_inputs`, `type_probs`, `rule_priors`, `no_state_rule_priors`,
    `_cities`, module docstring).
  - Tests in `tests/model/test_scenario_adu.py` and `tests/model/test_new_state_runs.py`.
  - `docs/analysis_plan.md` deviation entry (2026-11-25), review log rows A5–A11.
- **Decision:** Ben, 2026-11-25: "Fix them here please".
- **What Claude did and how it was checked:**
  - Claude Code reviewed `adu.py` at high depth and fixed three findings. A fourth (amended rules losing
    their zone limits) was checked against the reforms rows and found to be wrong.
  - New and updated tests check each fix by hand; the ADU and new-state test files pass.
  - Ran `lotline results` for all six states, one at a time, and compared with release `app-2026-11-24f`:
    only ADU moved (WI P50 −11%, MN, NC and OH within 2%, TX and OR unchanged).
