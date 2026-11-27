### LB-NNN · 2026-11-09 · `engine` · The baseline forecast in the results bundle and on the Results tab
- **Question:** the app showed reforms as homes *added* but never the level they add to. How many homes does
  each state permit over 2027–2031 with no policy change, and can the page show it from the same bundle?
- **Decided by:** Ben, 2026-11-09: a new bundle table rather than rows in `totals`; export and show it in one PR.
- **Outputs:**
  - `src/lotline/schemas.py` 1.11: `results_baseline` (state, size_class all/1/2/3_4/5p, period, P10/P50/P90,
    mean, places, coverage_share, basis); `docs/schemas.md` regenerated. Additive (schemas-v1 line).
  - `src/lotline/model/results.py`: `baseline_table` sums every place's `baseline.forecast_draws` per draw
    and year (D-061 window), "all" summed within each draw across size classes; `build_bundle` loads the
    same panel V1 uses (`theme="adu"`, holdout-filtered) and adds the `baseline` part.
  - `src/lotline/app/template.html`: a "With no policy change" card on the Results tab (five-year range,
    per-year midpoint, a table by building size, places and coverage, the counting basis); the Baseline row
    in the range chart now reads "0 added, by definition".
  - Tests: `tests/model/test_results_baseline.py` (statewide sums and percentiles by hand, "all" is not the
    sum of the class percentiles, window labels, coverage by hand, agreement with
    `baseline.baseline_forecast` means on a real simulation, other states ignored); the fixture bundle
    regenerated with a synthetic baseline; `tests/app/test_build.py` checks the card and the state file.
- **What Claude did and how it was checked:** Claude Code (Opus 5.5) wrote the schema, function, page card
  and tests. Checked by the tests above, the full suite, ruff and `compliance_check.py` (0 FAIL), and by
  building the page from the fixture and reading the card in the in-app browser (no console errors).
- **Not done:** no real bundle was built (a model run, waiting for Ben's go-ahead together with the D-064
  rerun). The fee scenario can now read the baseline but is still pending. The coverage share is against
  BPS places in the panel; BPS rows with no GEOID are outside it.
