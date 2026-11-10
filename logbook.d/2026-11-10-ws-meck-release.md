### LB-NNN · 2026-11-10 · `data` · Mecklenburg permits honour the V5 release
- **Question:** after V5 was released (#355), why did NC's rebuilt permits still stop Charlotte at
  2023-06-01?
- **Decided by:** Ben released V5 (#355). This fixes the adapter to follow that release.
- **Outputs:**
  - `src/lotline/adapters/states/nc/meck_permits.py`: the filter (query and town check) now comes from
    `holdout.still_blind`, not the whole registry, so a released holdout filters nothing.
  - `tests/states/nc/test_meck_permits.py`: filter tests run on the blind registry (`v5_blind`, as #355 did),
    plus a test that the released registry filters nothing.
- **What Claude did and how it was checked:**
  - Rebuilt NC (`lotline fetch --state NC`). BPS and the OneMap parcels picked the release up (314,379
    Charlotte parcels); Mecklenburg permits didn't (449,925 rows, unchanged).
  - After the fix: 482,249 rows. Charlotte has 14,901 permits in 2023 and 13,912 in 2024, and 6,883 in 2025.
    2025 is about half because this is the county's legacy ("Winchester") layer; to be checked.
  - Tests in `tests/states/nc` and `tests/core/test_holdout.py` pass.
- **Open:** 2025 coverage of the legacy layer.
