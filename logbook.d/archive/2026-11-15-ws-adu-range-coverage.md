### LB-NNN · 2026-11-15 · ADU · Are the ADU ranges the right width?

- **Question:** could the ADU ranges be narrowed honestly? Ben asked for the range coverage check.
- **Outputs:**
  - `reports/adu-range-coverage/` (place table, coverage tables, state width parts, README, `results.html`);
  - `scripts/dev/adu_range_coverage.py` and `scripts/dev/adu_range_coverage_page.py`;
  - results page published as an Artifact.
- **Result:**
  - Held out by state, A + P's place ranges are about right overall, slightly narrow: 69% fall in the middle 80%.
  - Core cities are too wide (88%) and suburbs too narrow (62%). Core cities hold 97% of observed ADUs.
  - Place-to-place luck is the largest source of a state total's width where a few cities make up the total.
  - Suggests a type-specific spread, which would need its own entry, and core-city counts.
- **What Claude did:**
  - Wrote the check: leave-a-state-out refits, predictive draws, randomized percentiles, and the state total
    with each source of spread switched off.
  - Ran it offline.
- **How it was checked:**
  - The leave-a-state-out fits match the D-088 rescoring run's fold fits on the same rows. For example, A + P
    without TX has core +1.93 in both.
  - ruff passes.
