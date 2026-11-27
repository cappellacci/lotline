## LB-xxx · 2026-11-06 · WS-APP · App section 3 (How well does it hold up?): scorecard, overlap check, tornado, technical fold

**Question answered:** Can the page lead with "we predicted this before we could see it", and show which assumptions drive the answer, without new model arithmetic?

**Outputs**
- Section 3 of `src/lotline/app/template.html`:
  - **Scorecard table** from `results_scorecard`: check, measure, result, target, verdict as a glyph plus a word, report path. If no rows are scored yet, the page says so.
  - **Blind-test card:** a placeholder until the frozen ranges and observed outcomes are in the bundle.
  - **Overlap check:** the rule in plain words. Its thresholds are read from `config/params/aggregate.yaml` at build time.
  - **Tornado:** the net statewide midpoint with each assumption alone at its P10 or P90.
  - **Technical fold:** draw percentiles for every factor per scenario, plus a pointer to the engine results dashboard.
- `src/lotline/app/aggregate.js`: `tornado()`, built only from `summarize`, so it uses the same arithmetic as the sliders.
- `src/lotline/app/build.py`: `overlap_thresholds` in the payload.
- Tests:
  - `tests/app/test_aggregate_parity.py`: the tornado vs Python (each factor at q = 10 and 90, sorted by swing).
  - `tests/app/test_build.py`: every section-3 part is on the page, the thresholds equal config, and the scorecard row is embedded.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) wrote the section and the tests. Checked by `tests/app` (25 passed), ruff and `compliance_check.py`, and by viewing the built fixture page in a browser (scorecard, overlap card and tornado). The overlap text was first drafted with "lot counts" as a measure; that was corrected to the actual three modifiers (rent, home value, mortgage rate; `hazard.calibration_distance`).
