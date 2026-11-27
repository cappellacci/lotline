### LB-NNN · 2026-11-27 · ws/mm-text-fixes · Missing middle: stale φ, θ and ramp text in mm_hazard.yaml

- **Question:** Does the missing-middle config text still match the values after the 2026-11-26 refit and #581?
- **Outputs:** `config/params/mm_hazard.yaml` (unit and notes text only; no value changed), and the regenerated
  parameter table in `docs/model_and_assumptions.md` (`scripts/dev/params_table.py`).
- **What changed:**
  - `mm_year_spread_phi` now gives variance = mean + φ × mean² (size 1/φ) and says g has variance φ, as the fit.
  - `mm_mature_hazard_ref` now quotes 1.66 per 1,000 (0.14–19.0), a five-year rate of 0.26 per 1,000 at half 4.5,
    and log-SD 1.501. Run-10 figures are labelled as run 10, and the §7 tests as not yet rerun at φ 13.03.
  - `mm_ramp_slope_years` now gives the year shares at half 4.5 (0.005, 0.018, 0.065, 0.21, 0.50; mean 0.159).
  - The fast-ramp note now says 0.80 at half 4.5.
- **How Claude worked and checked:** Raised by the review session's docs pass. The year shares and log-SD were
  computed with `scenarios.mm.year_shape` and the config's low/high values. `params_table.py --check`, compliance
  and the parameter tests were run.
