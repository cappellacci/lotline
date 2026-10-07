# Lotline: canonical tables (data dictionary)

<!-- GENERATED from src/lotline/schemas.py by `lotline schemas --write`. Do not edit by hand. -->

**Schemas version 1.4** (tag `schemas-v1`). Every adapter's output is validated against these tables; a state that brings its own data only has to produce them.

Conventions: unknown is null (never 0 or false); money is nominal dollars of the row's year unless `dollar_year` says otherwise; jurisdiction keys are Census GEOIDs (state 2, county 5, place 7, county subdivision 10 digits); combined categories are never split by guesswork. *Required* means the column must be present; *nullable* means its values may be empty.

## `jurisdictions`



| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `state` | text | yes | no | matches `^[A-Z]{2}$` |
| `geoid` | text | yes | no | unique |
| `name` | text | yes | no |  |
| `kind` | text | yes | no | one of `state`, `county`, `county_unincorporated`, `place`, `township`, `region`, `other` |
| `county_geoid` | text | no | yes |  |
| `bps_id` | text | no | yes |  |
| `pop_2020` | integer | no | yes | ≥ 0 |
| `data_tier` | integer | yes | no | one of `1`, `2`, `3` |

## `parcels`

One row per parcel per roll vintage. Feeds the eligible-parcel rule (build/eligible.py).

Table checks: `one_row_per_parcel_vintage`

| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `state` | text | yes | no | matches `^[A-Z]{2}$` |
| `parcel_id` | text | yes | no |  |
| `vintage` | integer | yes | no | ≥ 1900; ≤ 2100 |
| `vintage_date` | date | no | yes |  |
| `jurisdiction_geoid` | text | yes | no |  |
| `county_geoid` | text | no | yes | matches `^\d{5}$` |
| `lot_sqft` | number | yes | yes | ≥ 0 |
| `lot_width_ft` | number | no | yes | ≥ 0 |
| `land_use_std` | text | yes | no | one of `SF_DETACHED`, `SF_ATTACHED`, `DUPLEX`, `TRI_QUAD`, `MULTIFAMILY_5P`, `MOBILE_HOME`, `CONDO_UNIT`, `VACANT_RESIDENTIAL`, `MIXED_USE`, `COMMERCIAL`, `INDUSTRIAL`, `AGRICULTURAL`, `INSTITUTIONAL`, `OTHER`, `UNKNOWN` |
| `land_use_raw` | text | yes | yes |  |
| `units` | integer | no | yes | ≥ 0 |
| `year_built` | integer | no | yes |  |
| `bldg_sqft` | number | no | yes | ≥ 0 |
| `land_value` | number | no | yes | ≥ 0 |
| `bldg_value` | number | no | yes | ≥ 0 |
| `value_basis` | text | no | yes | one of `market`, `assessed`, `appraisal`, `unknown` |
| `last_sale_price` | number | no | yes | ≥ 0 |
| `last_sale_date` | date | no | yes |  |
| `sale_qualified` | true/false | no | yes |  |
| `sale_multi_parcel` | true/false | no | yes |  |
| `homestead` | true/false | no | yes |  |
| `zoning_raw` | text | no | yes |  |
| `zoning_source` | text | no | yes |  |
| `sf_only_zoned` | true/false | no | yes |  |
| `hoa` | true/false | no | yes |  |
| `in_floodplain` | true/false | no | yes |  |
| `in_historic_district` | true/false | no | yes |  |
| `lon` | number | no | yes | ≥ -180; ≤ 180 |
| `lat` | number | no | yes | ≥ -90; ≤ 90 |
| `source` | text | yes | no |  |

## `eligible_parcels`

The denominator: eligible parcels per jurisdiction-year, stored apart from permits (protocol §5.1-5.2). One row per jurisdiction, year and eligibility-rule version, so a rule change never overwrites history.

Table checks: `one_row_per_key`

| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `state` | text | yes | no | matches `^[A-Z]{2}$` |
| `jurisdiction_geoid` | text | yes | no |  |
| `year` | integer | yes | no | ≥ 1980; ≤ 2100 |
| `theme` | text | yes | no | one of `adu`, `missing_middle`, `fees`, `parking`, `tod`, `lot_size`, `process`, `hoa`, `moratorium`, `other` |
| `rule_version` | text | yes | no |  |
| `eligible_parcels` | integer | yes | no | ≥ 0 |
| `data_tier` | integer | yes | no | one of `1`, `2`, `3` |
| `denominator_source` | text | yes | no | one of `parcels`, `acs_sf_fallback`, `published` |
| `denominator_quality` | text | yes | no | one of `high`, `medium`, `low` |

## `permits`

One row per permit, or per permit type × year where a source publishes only aggregates (`n_buildings`). `issue_year` is always set; `issue_date` only when the source has it (`date_precision` says which). Unit counts may be derived (Raleigh land-use codes) or inferred (Mecklenburg Census codes): say so in `units_confidence`, and leave them null if unknown.

Table checks: `one_row_per_permit`, `date_matches_year`

| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `state` | text | yes | no | matches `^[A-Z]{2}$` |
| `permit_id` | text | yes | no |  |
| `parcel_id` | text | no | yes |  |
| `jurisdiction_geoid` | text | yes | no |  |
| `issue_year` | integer | yes | no | ≥ 1970; ≤ 2100 |
| `issue_date` | date | yes | yes |  |
| `date_precision` | text | yes | no | one of `day`, `month`, `year` |
| `application_date` | date | no | yes |  |
| `final_date` | date | no | yes |  |
| `final_date_type` | text | no | yes | one of `certificate_of_occupancy`, `completion`, `final_inspection`, `other` |
| `building_type_std` | text | yes | no | one of `SFD`, `ADU`, `TH`, `U2`, `U3_4`, `U5_6`, `U7P`, `DTQ`, `MF5`, `OTHER`, `UNKNOWN` |
| `type_confidence` | text | yes | no | one of `high`, `inferred`, `unknown` |
| `adu_type` | text | no | yes | one of `attached`, `detached`, `internal_conversion`, `unknown` |
| `permit_class_raw` | text | no | yes |  |
| `reform_flag_raw` | text | no | yes |  |
| `n_buildings` | integer | no | yes | ≥ 0 |
| `units_new` | integer | yes | yes | ≥ 0 |
| `units_removed` | integer | yes | yes | ≥ 0 |
| `units_confidence` | text | yes | no | one of `reported`, `derived`, `inferred`, `unknown` |
| `is_demolition` | true/false | yes | yes |  |
| `is_conversion` | true/false | yes | yes |  |
| `floor_area_sqft` | number | no | yes | ≥ 0 |
| `zoning_raw` | text | no | yes |  |
| `valuation_usd` | number | no | yes | ≥ 0 |
| `fees_paid_usd` | number | no | yes | ≥ 0 |
| `tenure` | text | no | yes |  |
| `source` | text | yes | no |  |

## `bps_place_year`

Census Building Permits Survey, annual, one row per permit-issuing place. `units_*` include Census imputation for months a place didn't report; `units_*_rep` are reported only. `imputed` is True when any month was imputed (months_reported < 12 or reported != total).

Table checks: `one_row_per_place_year`

| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `state` | text | yes | no | matches `^[A-Z]{2}$` |
| `bps_id` | text | yes | no | matches `^\d{2}\d{6}$` |
| `geoid` | text | yes | yes |  |
| `county_geoid` | text | yes | no | matches `^\d{5}$` |
| `name` | text | yes | no |  |
| `year` | integer | yes | no | ≥ 1980; ≤ 2100 |
| `months_reported` | integer | yes | no | ≥ 0; ≤ 12 |
| `bldgs_1` | integer | yes | no | ≥ 0 |
| `bldgs_2` | integer | yes | no | ≥ 0 |
| `bldgs_3_4` | integer | yes | no | ≥ 0 |
| `bldgs_5p` | integer | yes | no | ≥ 0 |
| `units_1` | integer | yes | no | ≥ 0 |
| `units_2` | integer | yes | no | ≥ 0 |
| `units_3_4` | integer | yes | no | ≥ 0 |
| `units_5p` | integer | yes | no | ≥ 0 |
| `units_1_rep` | integer | yes | no | ≥ 0 |
| `units_2_rep` | integer | yes | no | ≥ 0 |
| `units_3_4_rep` | integer | yes | no | ≥ 0 |
| `units_5p_rep` | integer | yes | no | ≥ 0 |
| `imputed` | true/false | yes | no |  |

## `market_geo_year`

Market conditions by geography and year. Each source fills its own columns; the rest may be absent. `geo` is prefixed by level so codes can't collide (county 27053 vs ZIP 27053): `national:US`, `state:27`, `cbsa:33460`, `county:27053`, `zip5:55415`, `tract:27053000100`.

Table checks: `one_row_per_geo_year`

| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `geo` | text | yes | no | matches `^(national|state|cbsa|county|place|cousub|zip5|tract):[0-9A-Z]+$` |
| `year` | integer | yes | no | ≥ 1940; ≤ 2100 |
| `hpi` | number | no | yes | > 0 |
| `hpi_base2000` | number | no | yes | > 0 |
| `hpi_change_pct` | number | no | yes |  |
| `median_value` | number | no | yes | ≥ 0 |
| `median_rent` | number | no | yes | ≥ 0 |
| `ppi_resid_inputs` | number | no | yes |  |
| `mortgage_rate` | number | no | yes |  |
| `cpi_u` | number | no | yes | > 0 |

## `acs_geo_year`

American Community Survey 5-year estimates, long format: one row per geography, vintage and variable. `end_year` is the last year of the 5-year window (2023 = 2019-2023). Adjacent vintages share four years of sample, so never difference them; compare non-overlapping windows. `moe` is the published 90% margin of error (0 where Census marks the estimate as controlled). Labels are kept per vintage because some categories changed over time (e.g. B25034 year-built bands).

Table checks: `one_row_per_geo_vintage_variable`

| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `geo` | text | yes | no | matches `^(state|county|place|cousub|tract):[0-9]+$` |
| `end_year` | integer | yes | no | ≥ 2009; ≤ 2100 |
| `table_id` | text | yes | no | matches `^[BC]\d{5}[A-Z]?$` |
| `variable` | text | yes | no | matches `^[BC]\d{5}[A-Z]?_\d{3}$` |
| `label` | text | yes | no |  |
| `estimate` | number | yes | yes |  |
| `moe` | number | yes | yes | ≥ 0 |

## `reforms`

One row per reform component, coded with the protocol §5.4 rubric (a vector, not a yes/no). Amendments are new rows that `supersedes` the earlier one (dose increments, C09). Two coders per row, disagreements logged (protocol §5.4). Treatment timing: `adoption_date` vs `effective_date` (§5.3).

| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `reform_id` | text | yes | no | unique |
| `state` | text | yes | no | matches `^[A-Z]{2}$` |
| `jurisdiction_geoid` | text | yes | no |  |
| `theme` | text | yes | no | one of `adu`, `missing_middle`, `fees`, `parking`, `tod`, `lot_size`, `process`, `hoa`, `moratorium`, `other` |
| `component` | text | yes | no |  |
| `status` | text | yes | no | one of `in_force`, `suspended`, `repealed`, `opted_out`, `pending` |
| `announced_date` | date | no | yes |  |
| `adoption_date` | date | no | yes |  |
| `effective_date` | date | yes | no |  |
| `end_date` | date | no | yes |  |
| `supersedes` | text | no | yes |  |
| `by_right` | true/false | yes | yes |  |
| `owner_occ` | true/false | yes | yes |  |
| `unit_cap` | integer | yes | yes | ≥ 0 |
| `far_cap` | number | no | yes | ≥ 0 |
| `max_stories` | number | no | yes | ≥ 0 |
| `min_lot_sqft` | number | no | yes | ≥ 0 |
| `adu_max_sqft` | number | no | yes | ≥ 0 |
| `adu_detached_allowed` | true/false | no | yes |  |
| `adus_per_lot` | integer | no | yes | ≥ 0 |
| `lot_split` | true/false | yes | yes |  |
| `parking` | text | yes | yes |  |
| `parking_min_per_unit` | number | no | yes | ≥ 0 |
| `fee_change_usd` | number | no | yes |  |
| `dollar_year` | integer | no | yes | ≥ 1970; ≤ 2100 |
| `coverage` | text | yes | no |  |
| `coverage_zones` | text | no | yes |  |
| `source_url` | text | yes | no |  |
| `coder` | text | yes | no |  |
| `coder_2` | text | yes | yes |  |
| `coder_agreement` | text | yes | no | one of `agree`, `adjudicated`, `single_coder` |
| `coding_notes` | text | no | yes |  |

## `fees`

Development fees by jurisdiction, year, component and building type (protocol §5.9). Water/sewer is its own component. A fee charged as a percent of value goes in `pct_of_value` with `basis = "pct_of_value"`; a mixed fee is two rows (e.g. Raleigh: a per-unit amount plus a percent).

Table checks: `one_row_per_key`

| Column | Type | Required | Nullable | Rule |
|---|---|---|---|---|
| `state` | text | yes | no | matches `^[A-Z]{2}$` |
| `jurisdiction_geoid` | text | yes | no |  |
| `year` | integer | yes | no | ≥ 1970; ≤ 2100 |
| `effective_date` | date | no | yes |  |
| `fee_component` | text | yes | no | one of `water_sewer`, `impact`, `permit`, `planning`, `other` |
| `fee_type` | text | yes | no |  |
| `building_type_std` | text | yes | no | one of `SFD`, `ADU`, `TH`, `U2`, `U3_4`, `U5_6`, `U7P`, `DTQ`, `MF5`, `OTHER`, `UNKNOWN` |
| `basis` | text | yes | no | one of `per_unit`, `per_sqft`, `per_lue`, `pct_of_value`, `flat`, `other` |
| `amount_usd` | number | yes | yes | ≥ 0 |
| `amount_per_unit_usd` | number | yes | yes | ≥ 0 |
| `pct_of_value` | number | no | yes | ≥ 0; ≤ 100 |
| `dollar_year` | integer | yes | no | ≥ 1970; ≤ 2100 |
| `payment_timing` | text | no | yes |  |
| `source` | text | yes | no |  |

## Version history

| Version | Change |
|---|---|
| 1.0 | seven canonical tables from BUILD_PLAN §5.1; bps_place_year adds bps_id, months, reported units |
| 1.1 | market_geo_year: level-prefixed geo, FHFA HPI columns |
| 1.2 | acs_geo_year (ACS 5-year, long format with MOE) |
| 1.3 | market_geo_year.cpi_u |
| 1.4 | schemas-v1 freeze: eligible_parcels (denominator); permits allow year-only dates, unknown units and demolitions, ADU type, zoning, floor area; parcels eligibility inputs; reforms rubric fields, two coders, status and amendments; fees components, basis, dollar year; nullable booleans; misspelled-column guard |
