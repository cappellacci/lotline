# Texas readiness (thread 12, step 3)

*WS-TX, 2026-10-26. Status: **draft**. It counts `main` at `f7cc92a` and, separately, what the open Texas PRs
would add once merged: #220 (San Antonio permits), #222 (Fort Worth), #223 (rules 21-40), #225 (Dallas),
#227 (StratMap adapter), #228 (docs), #230 (D-036, repeated totals without parcels) and #231 (Austin fees). Numbers come from the processed tables in `~/lotline-data`
and the branch files. **No engine, scenario or development run was made** (data-thread rule). Plan:
`docs/build/tx-data-plan.md`.*

## In short

- **Texas can run end to end today, but almost entirely on fallbacks.** Every one of its 1,006 jurisdictions
  (952 places, 54 county remainders) has a Census permit outcome, ACS, FHFA and a demand index. Only Austin
  has a parcel count, and only Austin has a coded water or sewer fee (#231).
- **The statewide parcel roll is the biggest single gain.** StratMap's CC0 statewide roll would replace the
  ACS denominator for most of Texas. The adapter is ready (#227) and waits for the download.
- **For the estimates:** Texas would bring **4 places to the ADU estimate** (Austin and San Antonio treated;
  Fort Worth and Dallas as comparisons) and **1 more treated place (League City, partly) plus 6 untreated
  on evidence** to the missing-middle estimate, which already counts 232 Texas places through BPS.

## 1. Coverage of each model input

"Real" means Texas's own data for that jurisdiction; "fallback" means the method's stated default for
missing data.

| Input | On `main` | With the open PRs | Fallback where missing | What closes the gap |
|---|---|---|---|---|
| Jurisdictions and tiers | 1,006 (952 places, 54 county remainders); tier 1: Austin; tier 3: 1,005 | same; tiers move when parcels load | — | Rebuild tiers after StratMap (S3) |
| Permit outcome (BPS) | All 1,006 are BPS reporters; 983 have a row in 2010-2024, 865 in all 15 years | same | A missing place-year is missing, never 0 (D-024) | — |
| Record-level permits | Austin only: 151,655 permits, 1971-2026 | + San Antonio 35,695 (2020-07 on; 2,585 of them ETJ, filed under Bexar), Fort Worth 297,362 (2001 on), Dallas 134,124 (to 2024-11-12): 4 cities with 4.6M of the 20.9M people in Texas places (22%) | BPS counts by building size; no ADU outcome | Houston has no record-level permits; Dallas 2025 needs the City's workbooks or a records request |
| ADU flag | Austin (R-102) | + San Antonio (own permit type), Fort Worth and Dallas (description parser) | — | — |
| Denominator (eligible parcels) | Austin from TCAD (2026 roll, Travis part); 1,003 jurisdictions on the ACS fallback; 2 with neither (Marshall Creek, Starbase: no 2020 population) | adapter for the StratMap roll (#227), not yet run | ACS one-unit homes (D-017), quality "low" | Ben's StratMap download → S2a run → S3 rebuild with D-035 history. The table on disk predates D-035, so rebuild either way |
| ADU rules | 18 places coded (8 allow ADUs, 10 "none") | 28 places (14 allow, 14 "none"); 33 rows await a second coder | D-022 draws a rule type for uncoded places | Ben's lookups (`tx-adu-lookups-todo.csv`: Corpus Christi, Pasadena, McKinney, Killeen first); second coder |
| Missing-middle rules | Austin (HOME 2024), Houston (Livable Places 2023) | + League City (duplexes in RSF-2, 2020, date to check), "none" rows for Mesquite, Waco, Round Rock, Richardson, Abilene, Edinburg | Uncoded places count as untreated by default (D-022) | `tx-mm-lookups-todo.csv` (32 places) |
| Fees | 2 Austin building-permit fee rows; no water or sewer fee | + Austin water/wastewater impact fees and street impact fee (#231): Austin's local total is **$1,434.74 per home**, used under D-034 (Ben, 2026-10-26) and stated as a floor until its parkland and meter fees are coded | Handbook $50,000 per home (D-034) for every other place | `tx-fee-lookups-todo.csv`: SAWS, Fort Worth, Houston, Dallas, Austin parkland and meters (**Ben**) |
| Prices | No sale prices (Texas non-disclosure law); TCAD appraised values for Austin | StratMap appraised values statewide once loaded | ACS values moved forward with FHFA | Nothing to collect: state law |
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
| Dallas (4819000) | comparison (no by-right ADU) | 1971 to 2024-11 | 2018 ("none") | One ADU in the window. The 2018 row has no earlier row, so 2010-2017 need a dated "none" row before use |

Waco (2023), Denton (2023), College Station (2023) and others now have dated rules (#223), but no
record-level permits, so they cannot enter.

**Missing-middle estimate (D-024).** Its outcome is BPS 2-4 unit homes, so all **232 Texas places of 10,000+
people** are already in. Treated: Austin and Houston on `main`; League City (one-third dose for one district,
date to check) with #223. Six more places become untreated on evidence rather than by default.

## 3. Remaining gaps and what closes each

| Gap | Effect | Closed by | Owner |
|---|---|---|---|
| No statewide parcels loaded | 1,003 jurisdictions on the ACS denominator (quality low) | StratMap download (§4 of the plan), then S2a run and S3 rebuild | **Ben**, then me |
| Austin's Williamson and Hays parts | Austin's denominator misses them (TCAD is Travis only) | Decide TCAD vs StratMap for Austin (`parcel_sources`, #227) | **Ben** |
| Repeated apartment totals (Fort Worth, Dallas) | 5+ unit permit counts up to 2.6x and 7.5x BPS | D-036 (#230: same day, same count of 50+, 3+ permits, under 300 sq ft per unit), decided by Ben 2026-10-26 | In review |
| Dallas 2025 permits | Dallas ends 2024-11-12 | City monthly workbooks or a records request | Later |
| Houston has no record-level permits | No ADU outcome for Texas's largest city | HCAD parcel changes (WS-TX brief), out of scope here | Later |
| Rule rows read on a mirror (33) | Dates marked CHECK can't serve as events yet | Second coder against the official codes | **Ben** |
| Uncoded rules (ADU 14 places, MM 32) | D-022 defaults | Fill-in tables in `docs/research/ordinances/` | **Ben** |
| Water or sewer fees outside Austin; Austin's parkland and meter fees | Fee scenario uses $50k outside Austin; Austin's $1,434.74 is a floor | Fill-in table `tx-fee-lookups-todo.csv` | **Ben** |
| Earlier parcel vintages | Denominator history is ACS scaled to one roll (D-035) | StratMap 2019-2025 downloads (S2b) | **Ben**, then me |
| Two places without ACS (Marshall Creek, Starbase) | No denominator at all | Check whether they report to BPS; else leave out and say so | Me |

## 4. Next update

After the StratMap run and the merge of the open Texas PRs, this report gets real parcel coverage by county
(share of known land use, places passing the D-017 gate) and the rebuilt tiers.
