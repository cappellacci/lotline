### LB-NNN · 2026-11-25 · Build: the ADU calibration chain reruns with one command (calibration phase 4)
- **Question:** can every current ADU fitted value be re-derived from the fetched data with `lotline calibrate`,
  without any number changing?
- **What I did:**
  - Moved the fit-set builders out of the dev scripts and into library code:
    - `lotline.model.adu_fit_set`: D-079's places, D-096's `UNKNOWN-PLACEHOLDER` cut, the owner and age
      readers, place types.
    - `lotline.model.adu_refit`: the m_x grid's leave-one-state-out weights and the slopes' central differences.
  - Wrote runners for six steps in `lotline.calibrate.adu_steps`: `adu_joint`, `adu_partial_share_grid`,
    `adu_anchor_slopes`, `adu_calibration_range`, `adu_town_prior_sd` and `adu_new_rule`.
  - Extended the framework minimally: a step can return a whole table as CSV text, compared row by row and
    written with `--write`; low/high differences are reported beside the value's.
  - The calibration scripts (`adu_mx_grid`, `adu_config_fit`, `adu_types_slopes`, `adu_reference`,
    `adu_new_rule`) now import the library. The research scripts re-export it under their old names, and the
    `adu_refit_fixed_rows.py` wrapper passes its years to the library builders.
- **Inputs:** the shared data store (offline).
- **Outputs:**
  - New: `src/lotline/model/adu_fit_set.py`, `src/lotline/model/adu_refit.py`,
    `src/lotline/calibrate/adu_steps.py`, `tests/model/test_adu_fit_set.py`,
    `tests/calibrate/test_adu_steps.py`.
  - Edited: `docs/calibration.md` and the dev scripts named above.
- **Findings:**
  - On the real data, the library builds the same 70 places and 498 place-years as the old chain, field for
    field, for both the D-096 inputs and the slopes' inputs.
  - Every value reproduces config except one: the D-060 calibration range's rent high ($1,822 vs $1,826).
    Config's range was computed without the D-096 cut (513 place-years), so it does not quite match the
    anchor's fit set.
  - D-099's held-out gain reproduces the decision but not the number in config's source text
    (−0.37 vs −0.11).
- **Decisions:** Ben, 2026-11-26 ("Yes, use $1,822"): the calibration range follows the anchor's own 498
  place-years. Rent high $1,826 → $1,822, written by `lotline calibrate --run --step adu_calibration_range
  --write`; source text and a dated note in `docs/analysis_plan.md` (D-060) corrected.
- **AI:** Claude Opus 5.5 wrote the code and tests. Checked with a field-by-field comparison of the old chain and
  the library on the real data, `lotline calibrate --run` against config, unit tests on hand-worked fixtures,
  ruff and the compliance check.
- **Open / next:** phase 5, refitting the three stale steps on the current form (Ben's call).
