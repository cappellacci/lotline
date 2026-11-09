### LB-NNN · 2026-11-09 · `app` · Plain-language gross and net counts, and each state's own permit record next to the forecast
- **Question:** "Net statewide" against "in the places that build" made no sense to Ben, and a five-year range
  means little without the state's own numbers. Can the page say what the two counts are, and show what
  actually gets built each year beside what the reform would add?
- **Decided by:** Ben, 2026-11-09. The toggle labels "All new homes" and "Net new housing" are his. So is the
  slider name "Homes that would have been built elsewhere in the state anyway", and the ask for a bar and
  whisker chart of actual counts and the prediction range.
- **Outputs:**
  - `src/lotline/app/template.html`:
    - the toggle and headline wording;
    - a "Why two numbers?" note under the range bars, with the state's own midpoints and the share taken out;
    - the need, tornado and funnel notes follow the new wording;
    - a new "What gets built now, and what the reform would add" card. Bars show actual yearly permits for
      2019–2025: ADU permits where local data mark them, with their coverage, and homes in 2–4 unit buildings
      from BPS. Whiskers show the reform's added permits each year for 2027–2031 (P10–P90 with the midpoint).
      For missing middle, a grey whisker shows the 2–4 unit homes expected with no change.
  - `src/lotline/app/knobs.yaml`: the slider wording.
  - Schemas 1.12: `results_observed`, and `results_baseline` gains size class `2_4` (summed within each draw).
    `results.observed_table` builds the new table.
  - Hand-worked tests (`tests/model/test_results_baseline.py`, `tests/app/test_build.py`) and a regenerated
    fixture.
- **What Claude did and how it was checked:**
  - Rebuilt the five bundles at f76df4a. The numbers are unchanged from run E; the new parts are added.
  - Read the TX and MN pages in the in-app browser (ADU and missing-middle views), with no console errors and
    no sideways scroll.
  - Moved the note below the range bars and replaced an overlapping "not modelled" label with a dashed
    divider and a caption.
  - App tests, the full suite, ruff and `compliance_check.py`.
