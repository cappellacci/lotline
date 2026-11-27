### LB-NNN · 2026-11-27 · Missing middle · The forecast's yearly spread uses φ as the fit does

- **Question:** The fit treats φ as the yearly multiplier's variance, and the forecast drew it with
  variance 1/φ. What changes when the forecast matches the fit?
- **Outputs:**
  - `src/lotline/model/scenarios/mm.py`: g ~ Gamma(1/φ, φ).
  - `tests/model/test_scenario_mm.py`: a hand-worked variance test and a match to the fit's NB pmf.
  - `src/lotline/validation/v5_stpaul.py`: a docstring note. The frozen V5 draw is unchanged.
  - `docs/analysis_plan.md`: the deviation of 2026-11-27, plus a corrected line in the 2026-11-26 φ entry.
- **Decision:** Ben, 2026-11-27: "yes, make the forecast match the fit and rerun"; "yes, fix that entry
  too". The review/cleanup session found the bug.
- **What Claude did and how it was checked:**
  - Checked the claim against `likelihood._nb_core` and the forecast.
  - Fixed the draw and wrote the tests. Both new tests fail on the old form.
  - Rebuilt MN, NC, OH, TX, OR and WI before and after on the same data. Only missing-middle parts moved.
    The P50s of homes net fell 1–8%, and the statewide P10–P90 barely changed.
  - Non-slow tests: 2,834 passed. Compliance: 0 FAIL.
