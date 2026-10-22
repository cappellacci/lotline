### LB-NNN · 2026-10-21 · Build: Durham permits judged by city limits at issue date (#94, NC thread 10)
- **Question:** do Durham permits on land annexed after they were issued push city-only counts above BPS?
- **What I did:**
  - Found a dated annexation source: the city's approved "Consolidated Annexation" development cases
    (`Planning` FeatureServer layer 19; 196 approved cases with polygons, approvals 2013-09 to 2026-06).
  - `durham_permits` now moves a located city permit to the county (37063) when it lies inside an annexation
    approved after its issue date; hand-worked tests on a synthetic polygon.
  - Rebuilt the table and compared city-only new single-family and townhouse units with BPS 3719000.
- **Inputs:** the hosted Inspections layer, CoD_Boundary, Planning layer 19, processed NC BPS.
- **Outputs:** `src/lotline/adapters/states/nc/durham_permits.py` (`annexed_after_issue`,
  `download_annexations`), `tests/states/nc/test_durham_permits.py`, `docs/data_provenance.md`.
- **Findings:**
  - Only 53 of 77,603 permits move from city to county (24 in 2024). City-only units are within -5% to +8% of
    BPS 1-unit in 2013-2025 before and after; annexation timing does not explain the gap in #94.
  - Annexations approved before 2013 are not in the layer, so 2007-2012 is not corrected.
- **Decisions:** for Ben: whether V0 can now compare Durham city alone with BPS (the 2026-10-14 interim rule
  compares city + county).
- **AI:** Claude Code (Opus 5.5) found the layer with metadata and statistics queries, wrote the change and
  tests, and ran the comparison.
- **Open / next:** pre-2013 annexation dates (ordinances) if 2007-2012 matter for V4's Durham backtest.
