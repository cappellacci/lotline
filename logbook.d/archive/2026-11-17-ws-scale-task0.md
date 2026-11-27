### LB-NNN · 2026-11-17 · Build: WS-SCALE task 0, a new state runs with no code edits
- **Question:** Can a state that is not one of the five run `lotline results` from its state file alone,
  with national data only, no permit adapter and no coded reforms?
- **What I did:**
  - Put the `REFORM_STATES` method choice to Ben in chat; he chose **"borrow only"**: an unlisted state is
    added to the run on the fly (`adu.reforms_with`), borrows the listed states' rule priors, field
    probabilities and blank shares, and feeds nothing back (`adu.pooled_states`). With no
    `config/reforms/<st>.csv` it gets an empty reforms table.
  - Ben agreed WS-SCALE makes the guard in `adu.py` itself: `observed_adu_counts` treats a missing permit
    table as empty (covers `adu.places_from_store` and `results.build_bundle`). `mm.py` switched to the same
    two helpers (one line).
  - `tests/core/test_config.py` checks the five states are present instead of pinning the list.
  - Updated `docs/adding_a_state.md` §3, step 3, step 7, step 14, §6 and §7.
- **Inputs:** WS-SCALE brief § Audit D; `docs/adding_a_state.md` §3.
- **Outputs:** `src/lotline/model/scenarios/adu.py`, `src/lotline/model/scenarios/mm.py`,
  `tests/model/test_new_state_runs.py`, `tests/core/test_config.py`, `docs/adding_a_state.md`.
- **Findings:** A synthetic tier-3 state "ZZ" (no permits, no reforms file, not listed) builds and validates a
  full bundle labelled `national_only`, `eligible_proxy` true, data tier 3, no observed ADU rows; its rule
  priors equal those built without it. For the five listed states the code path is unchanged (same dict, same
  order, same pools).
- **Decisions:** Proposed HANDOFF: "A state outside `REFORM_STATES` borrows shared rule priors and feeds none
  back; joining `REFORM_STATES` is part of pooling a state into the calibration (Ben, 2026-11-17)."
- **AI:** Claude wrote the change and the test. Checked: the new tests fail on the old code (5 of 5) and pass
  on the new; full pytest, ruff and `compliance_check.py` (0 FAIL).
- **Open / next:** Task 2 schema issue; tasks 3–4 with zero-difference checks.
