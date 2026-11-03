### LB-NNN · 2026-11-03 · engine · What range should θ carry into a state the model never saw?

- **Question:** Ben confirmed that a statewide θ is the goal, and asked how θ is calculated and how well it
  transfers to states with no ADUs. The answer: a new state needs no ADU data. But θ's current range
  (0.81–2.11 per 1,000) leaves out the state-to-state spread: alone, MN gives 1.25, NC 1.27, OH 2.34 and TX
  4.17.
- **Outputs:** D-043 in `docs/analysis_plan.md`. It is the method only, written before any fit:
  - a state multiplier with spread τ, estimated with θ and α;
  - an unseen-state draw shared by all of a state's places;
  - how τ combines with the extrapolation widening;
  - a leave-one-state-out validation;
  - a reading rule, with a fallback if τ can't be estimated.
- **Build and run (Ben approved the method, 2026-11-03):**
  - Code: the state-multiplier likelihood (Gauss-Hermite), fit, multipliers and unseen-state draw in
    `src/lotline/model/calibrate_adu.py`; `--state-effect` in `scripts/dev/calibrate_adu.py`; the scenario
    widening `hazard.widen_unseen_state` (not wired into the run yet).
  - Tests: nodes, the τ = 0 identity and direct integration by hand or numerically, recovery of τ on
    simulated states, and the shared draw (`tests/model/test_calibrate_adu.py`, `tests/model/test_hazard.py`).
  - Run once: `reports/adu-state-effect/`.
- **Findings:**
  - τ = 0, with a 90% interval of 0–0.67. With four states, state differences can't be told apart from place
    differences.
  - K1, the spread already seen, is 0.79, close to τ's upper bound.
  - Leave one state out: none missed. Median P90 ÷ P10 is 28.7, about the same as D-041.
  - Under the rule as written, the central run adds no state spread. Changing that needs a new entry.
- **Decisions:** none adopted. `hazard.yaml` is unchanged; the reading is for Ben to confirm before V8.
- **AI:** Claude Code (Opus 5.5) explained θ, drafted D-043, wrote the code and tests, ran the fit once and
  wrote up the results.
  - The full fit at τ = 0 reproduces D-041's θ and log-likelihood exactly.
  - Table values were read from the run's CSVs.
