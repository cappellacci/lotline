### LB-NNN · 2026-11-26 · Build: ADU fitting code leaves the forecast folder (modularity step 2, ADU part)
- **Question:** can `src/lotline/model/` hold only what an ADU forecast runs, with the ADU fitting code next to
  its calibration runners, without any result changing?
- **What I did:**
  - Engine helpers first: `PlaceData`, `Fit3`, `_cvals`, `GRID3`, `CHI2_90` and `Z_95` (from `calibrate_adu`)
    and `nelder_mead` (from `calibrate_shape`) moved unchanged to a new engine module, `model/adu_rates.py`.
    The forecast modules `adu_owner`, `adu_screen` and `adu_types` read them from there; the fitting modules
    re-import them.
  - Moved to `src/lotline/calibrate/adu/`: calibrate_adu, calibrate_shape, estimate_adu, pooled_adu,
    adu_fit_set, adu_forecast, adu_new_rule, adu_refit, adu_terms, joint_refit, score.
  - Moved to `src/lotline/validation/`: adu_profiles, adu_reform_check, adu_trend, fit_audit (each still has a
    test, so none was archived).
  - Tests moved alongside (`tests/calibrate/adu/`, `tests/validation/`). Imports, the `steps.py` runner
    strings, the lock's script notes and path mentions in docs, config comments and scripts were rewritten by
    one script; the ADU lines left `MOVING` in `tests/core/test_module_layout.py`.
- **Decision (mine, the brief left it to the owner):** `pooled_adu` went to `calibrate/adu/`. Nothing in the
  forecast calls it; only the missing-middle estimator (`estimate_mm`) and its tests do.
- **Inputs:** none new (results runs read the shared data store).
- **Outputs:** `src/lotline/model/adu_rates.py`, `src/lotline/calibrate/adu/`, the moved validation modules and
  tests; PR (see branch `ws/adu-move`).
- **Findings:** until missing middle moves `estimate_mm`'s helpers, the forecast still reaches
  `calibrate/adu/` through `scenarios/mm.py` → `estimate_mm`; the guard allows it while `estimate_mm` is in
  `MOVING`.
- **AI:** Claude Opus 5.5 did the moves with a scripted rewrite. Checked by bundle hashes for MN, NC, OH, TX, OR
  and WI before and after (every part except run-time metadata), the guard test, `lotline calibrate --check`,
  the non-slow tests, ruff and the compliance check.
- **Open / next:** modularity step 3 for ADU (split `scenarios/adu.py` by method step).
