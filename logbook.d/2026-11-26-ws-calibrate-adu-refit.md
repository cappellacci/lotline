### LB-NNN · 2026-11-26 · Build: the three older ADU fits refitted on D-096's form (calibration phase 5)
- **Question:** do the three ADU values fitted on older model forms (state spread τ, drift σ, ramp) still
  hold on the current D-096 form?
- **What I did:**
  - Wrote runners for `adu_state_effect`, `adu_drift` and `adu_ramp_share` in `lotline.calibrate.adu_steps`.
    Each reads the same 70 places and 498 place-years as the rest of the ADU chain.
  - Added the arithmetic to `lotline.model.adu_refit`: `with_ramp` and `ramp_profile` (D-048 on D-047's
    grid), `typed_for_state_effect` (D-043/D-044 with the core multiplier folded in) and
    `drift_grids` / `drift_sigmas` (D-091's persistence forecaster).
  - Ran each full refit once and compared it with config. Ran `lotline results` for WI and MN on config and
    on a scratch copy holding the new τ grid.
- **Inputs:** the shared data store (offline).
- **Outputs:** `src/lotline/model/adu_refit.py`, `src/lotline/calibrate/adu_steps.py`,
  `src/lotline/calibrate/steps.py` (runners only), `docs/calibration.md`, tests in
  `tests/model/test_adu_fit_set.py` and `tests/calibrate/test_adu_steps.py`.
- **Findings:**
  - Ramp: no ramp still wins by a wide margin (log-likelihood −1,487.8 against −1,916.5 at a half-life of
    0.5 years and worse beyond). `adu_ramp_share` stays 1.
  - Drift: σ = 1.025, unchanged; leaving one state out gives 0.875–1.100 (config's note says 0.85–1.10).
  - State spread: τ̂ falls from 0.565 to 0 (90% upper bound 1.70 → 0.46), and the grid's mass moves
    toward 0 (P(τ = 0) 0.021 → 0.128). The place types now take up the difference between states.
  - Effect: none on the five fitted states (they never draw a state multiplier; MN's bundle is identical).
    Wisconsin's ADU 2027–2031: P50 506 → 505, P10 122 → 201, P90 2,088 → 1,391, mean 1,292 → 775.
- **Decisions:** for Ben: whether to write the refit τ grid (`adu_state_effect.yaml`). Nothing was written.
- **AI:** Claude Opus 5.5 wrote the code and tests and ran the refits. Checked against config by
  `lotline calibrate --run`, the no-ramp fit reproducing config's θ (0.000224), hand-worked unit tests, and
  before/after results bundles.
- **Open / next:** on Ben's yes, `--write` `adu_state_effect` and mark the three steps `current`.
