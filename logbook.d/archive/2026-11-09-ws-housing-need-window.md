### LB-NNN · 2026-11-09 · Engine: housing-need growth over the 2027–2031 window
- **Question:** The "% of housing need" denominator was each demographer's 2025→2030 change. How do we match
  it to the D-061 window (D-061 open item 2)?
- **What I did:** Ben chose to interpolate to mid-2026 → mid-2031 (2026-11-08). In `scripts/dev/housing_need.py`:
  - each state now lists the July-1 years its demographer publishes around the window;
  - `window_years` takes the years from the forecast window;
  - `population_at` reads a missing year on the straight line between published ones, never beyond them;
  - each entry's notes say how each year was read.

  I downloaded the MN, NC, OH and OR files and the Texas projections table through `lotline.io.http.fetch`
  (source `state_pop_projections`) and checked every stored 2025 and 2030 against them. All match, except
  that Texas's low and high 2030 differ by about 0.03%, which is noted in the entry. MN and OR publish every
  year, NC and OH every five years (2035 added), and Texas's table every ten years (2040 added). Then I
  regenerated `config/params/housing_need.yaml`. New central values: MN 45,989; NC 205,251; TX 675,323;
  OH −33,316; OR 42,291.
- **Outputs:** `scripts/dev/housing_need.py`; `config/params/housing_need.yaml`; the parameter table in
  `docs/model_and_assumptions.md`; D-061 item 2 marked settled in `docs/analysis_plan.md`;
  `tests/test_housing_need_window.py`.
- **How Claude helped and how it was checked:** Claude (Claude Code) found the source files, with web-fetch
  agents and the in-app browser for the Texas page's data URL, and parsed them locally. It made the code
  change and wrote hand-worked tests: interpolation, a three-scenario growth example, the window years and the
  generated units. NC's new values were checked by hand (514,305 people × 0.3991 households per person =
  205,251). The Texas zip downloads sit behind a user-information form, which Claude did not fill in. Ruff, the
  need, results and app tests (62), and `compliance_check.py` (0 FAIL) pass. No model run was made.
