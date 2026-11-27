### LB-NNN · 2026-11-17 · ADU / WS-ENGINE · ADU detail in the results bundle for the app's evidence card

- **Question:** The redesigned Results page's ADU evidence card (PR #466) needs ADUs by place type, statewide no-reform ADUs by year, and if possible estimated ADUs statewide in past years. Can the bundle carry them?
- **Asked by:** the UI/UX workflow session, on Ben's "Yes, ask it" (2026-11-17).
- **Outputs:** schemas 1.15: `results_adu_place_types` (state, place_type, places, lots, base_p10/base/base_p90, added_p10/added/added_p90; ADUs a year, window average, medians as base/added) and `results_adu_baseline` (state, period, p10/p50/p90 of statewide current-rules ADUs per window year); `results.adu_place_type_table`, `results.adu_baseline_years`; `read_bundle` reads older bundles without them as empty; tests by hand.
- **Item 3 not done:** the engine forecasts from the origin; it has no backcast of statewide ADUs for past years, and one would be a model estimate for uncounted places, not a count. Told the app session to keep showing counted permits.
- **What Claude did and how it was checked:** wrote the code and tests; a real Texas run gave core 577 / 535, suburb 171 / 462, town 3 / 7 ADUs a year (no reform / added, medians), no-reform statewide about 790 a year (355–2,080), consistent with the bundle's five-year 5,513 permits added.
