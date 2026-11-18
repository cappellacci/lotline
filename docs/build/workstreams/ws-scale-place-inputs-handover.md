# place_inputs: switch-over note for the ADU and MM owners (WS-SCALE, 2026-11-17)

From the WS-SCALE session. For the "ADU statewide prediction methodology" and "Missing Middle Analysis refresh"
sessions. Nothing in adu.py / mm.py reads this table yet; each owner switches their model in their own PR.

*Copy committed to the repo 2026-11-17; the original is in the side-session notes folder.* Ben approved the six
task-5 rules on 2026-11-17 ("all as recommended"). Rules 1 (one place set), 4 (parcel roll no later than
origin + 1), 5 (straddling places: county with most 2020 population) and 6 (county remainder population) land
in `place_inputs` / `jurisdictions` as WS-SCALE PRs, each with before/after bundles. Rules 2 (missing ACS:
state median, flagged) and 3 (D-056 scaling for MM) are filled or exposed in `place_inputs`; the model code
changes are the owners'.

## What exists (PRs #461, #465 and #468; #452 and #456-#467 are on main)
- `src/lotline/build/place_inputs.py`, table `place_inputs` (schemas 1.16), key (state, geoid, year).
  Row Y = what a run with origin Y reads. Build: `lotline fetch --state XX --source place_inputs`.
- Columns equal what the models compute today: checked on all five states at origin 2025, 0 differences.

## Switch-over, ADU (`adu.places_from_store`)
Replace the inline nearest-roll + `non_overlapping` + `acs_values` + `observed_adu_counts/observed_per_year`
+ `adu_types.jurisdiction_types` steps with a read of `place_inputs` at `year == origin`:
`eligible_parcels_adu` (+ `_reported_adu`, `overlap_removed_adu`, `parcels_year_adu`,
`parcels_after_origin_adu`, `denominator_source_adu`, `denominator_quality_adu`), `acs_geo`, `rent`,
`home_value`, `acs_end_year`, `observed_adu_per_year`, `place_type`. Keep: rule_inputs, county_mix, the
undercount by-k-row split (`observed_adu_by_k_row`), and the results.py drop of places with no rent/value.
Check: `lotline results --all` bundles identical before/after (same seed).

## Switch-over, MM (`mm.places_from_store`)
Replace `_nearest` + `non_overlapping` + `house_shares` + `acs_values` + `size_band` with `eligible_parcels_mm`
(+ block), `house_share` (raw; keep MM's fill rule), `rent`, `size_band`. Keep doses, pcr, f_share.

## Disagreements reproduced on purpose (task 5, Ben's call each)
See the WS-SCALE brief § Audit A and the list in the session's report.
