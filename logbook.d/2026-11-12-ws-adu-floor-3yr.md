### LB-NNN · 2026-11-12 · `model` · Why ADU test C failed, and the floor moved to 3 years
- **Question:** the D-079 refit failed D-074 test C, the no-reform floor, in all five states (43 of 73
  places). Is the model wrong, or is the test?
- **Decided by:** Ben, 2026-11-12 ("Yes, use 3 years"). Recorded as D-082.
- **Outputs:**
  - `config/params/adu.yaml`: `adu_observed_years` 4 → 3.
  - `docs/analysis_plan.md`: D-082.
  - `docs/model_and_assumptions.md`: parameter table regenerated.
- **What Claude did and how it was checked:**
  - Read `test_c_rows` and the engine's floor (`pool_paths`, `observed_per_year`).
  - Tabulated every counted place's ADUs for 2022–2025 from the processed permits, reading counts only and
    running no model. The engine floor averaged 2022–25 while the test averaged 2023–25; matching the
    windows removes 41 of the 43 failures.
  - Re-scored test C offline with the refit's Form A values after the change: every place is within 1% of
    its floor, and 42 are still slightly below 1. The cause is pool shrinkage and the k draws.
  - Ran `params_table.py --check`, ruff and the model tests.
- **Open:**
  - Ben's call on the sub-1% gap under test C's strict rule.
  - Austin's inferred HOME counts, which affect its floor.
  - The larger finding: the floor, not the model's rate, sets the baseline in nearly every counted place.
