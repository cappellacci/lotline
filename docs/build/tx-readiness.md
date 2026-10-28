# Texas readiness (thread 12, step 3)

*WS-TX, 2026-10-26; updated 2026-10-27 after the StratMap load (#238) and #233. Status: **draft**. The ten Texas
PRs (#218, #220, #222, #223, #225, #227-#231) were merged on 2026-10-26; #233 and #238 on 2026-10-27. The middle
column lists what all of them added to the earlier `main` (`f7cc92a`).
Merging accepted the defaults proposed in them: ETJ permits under the Bexar remainder (#220), Fort Worth's
non-rental ADUs kept and flagged (#222), Austin on TCAD (#227). Numbers come from the processed tables in
`~/lotline-data` and the repo files. **No engine, scenario or development run was made** (data-thread rule).
Plan: `docs/build/tx-data-plan.md`.*

## In short

- **Texas can run end to end today.** Every one of its 1,006 jurisdictions (952 places, 54 county remainders)
  has a Census permit outcome, ACS, FHFA and a demand index. **458 count eligible parcels from real rolls**
  (439 places with 67% of the people in Texas places, and 19 county remainders), up from Austin alone; 546
  stay on the ACS fallback. Tiers: 125 tier 1, 161 tier 2, 720 tier 3 (was 1 / 0 / 1,005). Only Austin has a
  coded water or sewer fee (#231).
- **StratMap is loaded, but its releases are uneven.** Of the five statewide releases Ben downloaded, 2022
  and 2026 carry no land-use codes at all, so the 2019 and 2025 releases are read (#238). Of the 40 places of
  100,000+ people, 32 count from parcels; **Houston does not** (its 2019 extract is partial and its 2025 roll
  has 85% known land use, under the 90% gate).
- **For the estimates:** Texas would bring **4 places to the ADU estimate** (Austin and San Antonio treated;
  Fort Worth and Dallas as comparisons) and **1 more treated place (League City, partly) plus 6 untreated
  on evidence** to the missing-middle estimate, which already counts 232 Texas places through BPS.

## 1. Coverage of each model input

"Real" means Texas's own data for that jurisdiction; "fallback" means the method's stated default for
missing data.

| Input | Before 2026-10-23 | Added 2026-10-23 to 26 (merged) | Fallback where missing | What closes the gap |
|---|---|---|---|---|
| Jurisdictions and tiers | 1,006 (952 places, 54 county remainders); tier 1: Austin; tier 3: 1,005 | Rebuilt from StratMap (S3, 2026-10-27): tier 1: 125 (123 places, 2 remainders); tier 2: 161; tier 3: 720 | — | More counties' land use (local-code crosswalks) |
| Permit outcome (BPS) | All 1,006 are BPS reporters; 983 have a row in 2010-2024, 865 in all 15 years | same | A missing place-year is missing, never 0 (D-024) | — |
| Record-level permits | Austin only: 151,655 permits, 1971-2026 | + San Antonio 35,695 (2020-07 on; 2,585 of them ETJ, filed under Bexar), Fort Worth 297,362 (2001 on), Dallas 134,124 (to 2024-11-12): 4 cities with 4.6M of the 20.9M people in Texas places (22%) | BPS counts by building size; no ADU outcome | Houston has no record-level permits; Dallas 2025 needs the City's workbooks or a records request |
| ADU flag | Austin (R-102) | + San Antonio (own permit type), Fort Worth and Dallas (description parser) | — | — |
| Denominator (eligible parcels) | Austin from TCAD (2026 roll, Travis part), one year only; 1,003 jurisdictions on the ACS fallback; 2 with neither (Marshall Creek, Starbase) | **StratMap 2019 and 2025 loaded (#238): 21.0M parcels.** 458 jurisdictions count from parcels: 193 with both rolls, 173 with 2019 only, 91 with 2025 only, and Austin on its 2026 TCAD roll; other years are ACS scaled to the rolls (D-035). 2023 ADU-eligible parcels against the ACS fallback: San Antonio 365,676 (357,081), Fort Worth 246,154 (236,037), Dallas 230,547 (243,946), El Paso 182,489 (177,422), Plano 72,080 (69,170). Parcel rows are quality "low" (StratMap has no unit counts) | ACS one-unit homes (D-017), quality "low", for 546 jurisdictions; 2 with neither | Local land-use code crosswalks (Harris Z codes; `loc_land_use` for counties without the state code) |
| ADU rules | 18 places coded (8 allow ADUs, 10 "none") | 28 places (14 allow, 14 "none"); 33 rows await a second coder | D-022 draws a rule type for uncoded places | Ben's lookups (`tx-adu-lookups-todo.csv`: Corpus Christi, Pasadena, McKinney, Killeen first); second coder |
| Missing-middle rules | Austin (HOME 2024), Houston (Livable Places 2023) | + League City (duplexes in RSF-2, 2020, date to check), "none" rows for Mesquite, Waco, Round Rock, Richardson, Abilene, Edinburg | Uncoded places count as untreated by default (D-022) | `tx-mm-lookups-todo.csv` (32 places) |
| Fees | 2 Austin building-permit fee rows; no water or sewer fee | + Austin water/wastewater impact fees and street impact fee (#231): Austin's local total is **$1,434.74 per home**, used under D-034 (Ben, 2026-10-26) and stated as a floor until its parkland and meter fees are coded | Handbook $50,000 per home (D-034) for every other place | `tx-fee-lookups-todo.csv`: SAWS, Fort Worth, Houston, Dallas, Austin parkland and meters (**Ben**) |
| Prices | No sale prices (Texas non-disclosure law); TCAD appraised values for Austin | StratMap land and building appraised values on every loaded parcel (2019, 2025) | ACS values moved forward with FHFA | Nothing to collect: state law |
| Market and rates | ACS for 950 of 952 places and all 54 counties (2010-2024); FHFA (county, tract, ZIP, CBSA); FRED (national) | same | — | — |
| Demand index | 253 of 254 counties, 2010-2023 (every jurisdiction's county is covered) | same | — | — |
| Zoning | None on parcels; the HOME rows name SF-1 to SF-3; Dallas permits carry base zoning | same | Rule rows' coverage text | No open statewide zoning (National Zoning Atlas license) |

## 2. What Texas adds to the estimation panels

**ADU estimate (D-025).** A place enters with record-level ADU counts and a dated rule. Today the sample is
the Twin Cities. Whether to pool other states is an estimation decision for WS-ENGINE and Ben. If it pools,
Texas offers:

| Place | Role | Years with ADU-flagged permits | Rule rows | Notes |
|---|---|---|---|---|
| Austin (4805000) | treated (2015 easing, HOME 2024) | 1971-2026 | 2010, 2015, 2023, 2024 | R-102 nearly stops after HOME, when ADUs became 2- and 3-unit uses |
| San Antonio (4865000) | treated (UDC 2023-01-01) | 2020-07 on (2021-2025 full) | 2001, 2023 | 39, 41, 50, 60, 60 ADU permits a year 2021-2025 |
| Fort Worth (4827000) | comparison (no rentable ADU) | 2001 on | 2010 ("none") | 113 non-rental ADUs in 25 years: count them or leave the outcome out (#222) |
| Dallas (4819000) | comparison (no by-right ADU) | 1971 to 2024-11 | 2010 and 2018 ("none") | One ADU in the window. The 2010 row (non-rental special exception only, start of window) was added 2026-10-26 so every panel year has a dated rule |

Waco (2023), Denton (2023), College Station (2023) and others now have dated rules (#223), but no
record-level permits, so they cannot enter.

**Missing-middle estimate (D-024).** Its outcome is BPS 2-4 unit homes, so all **232 Texas places of 10,000+
people** are already in. Treated: Austin and Houston on `main`; League City (one-third dose for one district,
date to check) with #223. Six more places become untreated on evidence rather than by default.

## 3. Remaining gaps and what closes each

| Gap | Effect | Closed by | Owner |
|---|---|---|---|
| Land use missing or unmapped in many counties | 546 jurisdictions on the ACS denominator, Houston among them. Per release, counties with 90%+ known land use: 63 of 193 (2019), 65 of 247 (2025) | Crosswalks for districts' own codes (`loc_land_use`; Harris's Z codes), which would bring Houston, Travis 2025 and Williamson in; ask TxGIO why the 2022 and 2026 releases carry no land use | Me (crosswalks), **Ben** (TxGIO) |
| Partial county extracts | 2019: Harris has 66% of its 2025 parcels and about 30 counties are under 80%; those county parts are left out with every jurisdiction touching them (`min_county_roll_completeness`, Ben, 2026-10-27) | Nothing more unless a fuller 2019-era roll appears | Done |
| Releases not read | 2024 (35% land use) is registered but not read: each statewide roll takes about 2.6 GB in memory | Per-vintage parcel files (a WS-CORE contract change) to read all releases | WS-CORE |
| Austin's Williamson and Hays parts | Austin's denominator misses them (TCAD is Travis only); StratMap has Williamson without land use | TCAD kept for Austin (`parcel_sources`); rebuild TCAD for the new PTAD C and X crosswalk rows | Me |
| Repeated apartment totals (Fort Worth, Dallas) | 5+ unit permit counts up to 2.6x and 7.5x BPS | D-036 (#230, merged: same day, same count of 50+, 3+ permits, under 300 sq ft per unit), decided by Ben 2026-10-26 | Done |
| Dallas 2025 permits | Dallas ends 2024-11-12 | City monthly workbooks or a records request | Later |
| Houston has no record-level permits | No ADU outcome for Texas's largest city | HCAD parcel changes (WS-TX brief), out of scope here | Later |
| Rule rows read on a mirror (33) | Dates marked CHECK can't serve as events yet | Second coder against the official codes | **Ben** |
| Uncoded rules (ADU 14 places, MM 32) | D-022 defaults | Fill-in tables in `docs/research/ordinances/` | **Ben** |
| Water or sewer fees outside Austin; Austin's parkland and meter fees | Fee scenario uses $50k outside Austin; Austin's $1,434.74 is a floor | Fill-in table `tx-fee-lookups-todo.csv` | **Ben** |
| Two places without ACS (Marshall Creek, Starbase) | No denominator at all | Checked 2026-10-26: Marshall Creek reports to BPS only to 2009 and has no 2020 population (it looks absorbed into a neighbour, not verified), so it should leave the jurisdictions table (WS-CORE). Starbase first reports in 2025, so its earlier history belongs to the Cameron County remainder. Neither affects 2010-2024 estimates | WS-CORE |

## 4. Next update

After the local land-use crosswalks (Houston) and Ben's rule and fee lookups. Note: #238's description gave
530 jurisdictions on parcels; that count included 72 county-remainder rows for counties that are not Texas
jurisdictions (StratMap places every parcel outside a city in its county's remainder). The right count is
458. Those 72 extra rows sit in the `eligible_parcels` table on disk but match no jurisdiction, so nothing
uses them; `resolve_jurisdictions` could leave them out (a small follow-up).
