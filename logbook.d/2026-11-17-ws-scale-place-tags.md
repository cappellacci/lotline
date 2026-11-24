### LB-NNN · 2026-11-17 · Build: WS-SCALE, place tags in place_inputs
- **Question:** Can every per-place tag the models compute on each run (place type, house price index and its
  geography, holdout flag, which sources cover a place) live in `place_inputs`, unchanged?
- **What I did:**
  - `place_inputs.place_tags`: `place_type` + `place_type_source` (D-088, D-089 default town),
    `is_holdout` (still-blind holdouts), `parcel_sources`, `permit_sources`; plus `cbsa_code`, `cbsa_type`,
    `hpi`, `hpi_geo` (the baseline panel's county → cbsa → state non-CBSA → state chain) and
    `bps_county_geoid`.
  - Ben chose (2026-11-17) to keep these in `place_inputs`, not as new `jurisdictions` columns.
- **Inputs:** five states' processed tables (offline, read-only).
- **Outputs:** `src/lotline/build/place_inputs.py`, `tests/build/test_place_inputs.py`.
- **Findings:** `place_type` equals the ADU model's in every place of all five states; `hpi` and `hpi_geo`
  equal the baseline panel's on all 6,335 compared rows. First run differed on one row: Rutherford College
  town (NC) straddles Burke and Caldwell counties; the panel takes that year's BPS county, `jurisdictions` the
  latest row's. The table now uses the BPS county (as the panel does); the disagreement goes on the task 5
  list. The earlier column checks still show 0 differences.
- **Decisions:** none new.
- **AI:** Claude wrote the code, tests and checks; verified as above.
- **Open / next:** aliases files; register `place_inputs` as a fetch step; owners' switch-over.
