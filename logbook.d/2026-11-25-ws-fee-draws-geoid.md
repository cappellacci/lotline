### LB-NNN · 2026-11-25 · Review · Local-fee draws keyed by place (thread 17, A19)

- **Question:** Do a place's local-fee draws depend on which other places are in the run?
- **Outputs:** `src/lotline/model/scenarios/fees.py` (`fee_draws`); test
  `test_fee_draws_are_keyed_by_place_not_row_order` in `tests/model/test_fee_scenario.py`; review row A19.
- **Decision:** Ben, 2026-11-25: "Yes, do A19". No HANDOFF decision (a reproducibility fix, not a method change).
- **What Claude did and how it was checked:** Claude Code replaced the one shared random stream (row order) with one
  stream per place, seeded by the run seed and the place's geoid, as the ADU and missing-middle draws already are. A
  test shows a place's draws survive adding a place and reversing the rows. `lotline results` was rerun for all six
  states, one at a time, against the bundles from the baseline-coverage run: only the real-local-fee scenario moves
  (P50 within 2 homes in every state; P10 and P90 within about 2%); the benchmark fee, ADU and missing-middle
  results are identical.
