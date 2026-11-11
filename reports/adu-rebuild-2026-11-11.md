# ADU processed-data rebuild, 2026-11-11

**What:** every state's processed tables were rebuilt with `lotline fetch` on `origin/main` at `1a5d4f04`, so they
pick up #375 (`eligible.permit_level`, permit-level county remainders), #376 (shared ADU parser fix, `adu_removed`),
#377 (D-078 undercount table), #378 (permit-level remainders in the ADU fit panels) and the state count PRs
#357-#372. Ben approved this on 2026-11-11. The states ran one at a time (MN, NC, OH, TX, OR), each source on its own,
then `eligible` again after the parcels. The holdout filter stayed on (`assert_no_leak` on every table). No engine,
scenario, fit, calibration or dev-run script was run, and no `--unblind` was used.

**Before figures:** before the rebuild, the old `permits/` and `eligible_parcels/` tables (built 2026-10-14 to
2026-11-10) were copied out of `LOTLINE_DATA_DIR`. Every "before" figure below comes from that copy, and every
"after" figure from the rebuilt tables. An ADU permit is a row with `building_type_std == "ADU"`, counted by
`issue_year`.

## Pass / fail

| State | Result | Notes |
|---|---|---|
| MN | **pass** | First try: Rochester failed (`xlrd` missing from the shared `.venv`). `xlrd>=2.0.2` is already declared in `pyproject.toml` (9261a43d) and locked at 2.0.2, so the venv was synced with `uv pip install xlrd==2.0.2`; that is not a new dependency. Rochester and St. Paul then rebuilt. |
| NC | **pass, with one source from cache** | Greensboro's ArcGIS server timed out twice (`ConnectTimeout`, gis.greensboro-nc.gov). Its table was rebuilt with the same adapter `build()` and holdout check from the cached 2026-11-09 raw pages (`download_layer(..., vintage="2026-11-09")`), so the new parser applies but the source rows are from 2026-11-09. |
| OH | **pass, parcels not refreshed** | `oh_parcels` began a fresh statewide re-download (1,045 of the roughly 5,600 queries in 2.5 hours, so about 13 hours in all) and was stopped. The adapter has not changed since the 2026-11-01 processed build, and none of the merged fixes touch it. `eligible` was rebuilt from the 2026-11-01 parcels. A partial raw folder, `raw/oh_parcels/2026-11-11` (258 MB), is left in the data dir and can be deleted. |
| TX | **pass** | |
| OR | **pass** | |

Free disk went from 27 GB to 15 GB during the run (StratMap and the NC/MN parcel rewrites). It never fell below the 5 GB stop line.

## ADU permits per source per year, before → after

Unchanged cells show one number. "Other yrs" covers issue years before 2015. "Reclassified" counts permits that
were already in the old table but changed type; "new rows" counts permits newly published by the source. 2026 is a
partial year.

#### MN

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| metc | 0 | 29 | 27 | 29 | 30 | 34 | 29 | 34 | 39 | 36 | 53 | 0 | 1 | 341 | 0% |
| mpls | 0 | 2 | 30 | 25 | 35 | 28 | 16 | 17 | 14 | 16 | 13 | 15→**17** | 0 | 211→**213** | +1% |
| rochester | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 0 | 0 | 0 | 5 | 0% |
| stpaul | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0% |

St. Paul has no ADU rows in either build (V5 holdout still active; the filter stayed on).

#### NC

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| asheville | 14→**15** | 36→**37** | 49→**50** | 34→**36** | 20 | 20→**22** | 19 | 26→**28** | 38→**39** | 30→**29** | 38 | 24→**26** | 13 | 361→**372** | +3% |
| cary | 0 | 0 | 0 | 0 | 3 | 1 | 3 | 3 | 3 | 13 | 6 | 11 | 0 | 43 | 0% |
| chapel hill | 2 | 5 | 2 | 8 | 5 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 0% |
| durham | 4 | 5 | 7 | 7 | 18 | 15 | 33 | 35 | 82 | 55 | 48 | 48 | 38 | 395 | 0% |
| greensboro | 0 | 0→**1** | 0→**1** | 2 | 1→**2** | 2 | 0→**1** | 2 | 3→**4** | 3→**4** | 5→**6** | 15 | 3→**4** | 36→**44** | +22% |
| meck | 7 | 8→**9** | 9→**10** | 22→**23** | 28→**31** | 41→**44** | 29→**31** | 45→**47** | 59 | 73→**79** | 53→**55** | 7 | 34→**39** | 415→**441** | +6% |
| raleigh | 0 | 0 | 0 | 0 | 1 | 2 | 23 | 55 | 54 | 37 | 61 | 67→**68** | 0 | 300→**301** | +0% |
| wilmington | 6 | 13 | 6 | 6 | 7 | 19 | 9 | 25 | 46 | 60 | 76 | 79→**81** | 5 | 357→**359** | +1% |

#### OH

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cincy | 0 | 0 | 1 | 0 | 0 | 11→**12** | 0 | 2 | 1 | 5 | 3→**4** | 3→**4** | 0 | 26→**29** | +12% |
| cle | 0 | 2 | 0 | 0 | 0 | 3 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 7 | 0% |
| columbus | 4 | 2 | 5 | 5 | 4 | 5 | 8 | 5 | 2 | 4 | 6 | 0 | 3 | 53 | 0% |
| columbus variances | 10 | 6 | 6 | 8 | 18 | 21 | 15 | 18 | 18 | 18 | 22 | 0 | 23 | 183 | 0% |
| franklin | 1 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 0 | 2 | 4 | 0 | 1 | 11 | 0% |
| montgomery | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 2 | 2 | 0 | 0 | 7 | 0% |

#### TX

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| austin | 151 | 234 | 357 | 340 | 375 | 330 | 341 | 325 | 243 | 90 | 9 | 2 | 369 | 3,166 | 0% |
| cstx | 0 | 2 | 0 | 6 | 5 | 8 | 2 | 4 | 2 | 4 | 5 | 7 | 0 | 45 | 0% |
| dallas | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0→**1** | 1→**2** | +100% |
| fw | 1→**2** | 5→**4** | 4→**3** | 4 | 4 | 9 | 9 | 9 | 16 | 14 | 8→**9** | 9→**11** | 21→**23** | 113→**117** | +4% |
| sa | 0 | 0 | 0 | 0 | 0 | 2 | 39 | 41 | 50 | 60 | 62 | 41→**45** | 0 | 295→**299** | +1% |

#### OR

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bend | 24 | 45 | 47 | 59 | 66 | 56 | 68 | 84 | 63 | 37 | 51 | 27→**29** | 28 | 655→**657** | +0% |
| medford | 0 | 0 | 0 | 0 | 0 | 6 | 32 | 37 | 54 | 52 | 32 | 23 | 0 | 236 | 0% |
| mwvcog | 0 | 0 | 0 | 8 | 12 | 67 | 24 | 28 | 56 | 21 | 46 | 0 | 0 | 262 | 0% |
| portland | 387 | 549 | 518 | 593 | 341 | 241 | 251 | 275 | 221 | 178 | 160 | 78 | 1,104 | 4,896 | 0% |

## What the parser fix changed

Gains and losses are matched by `permit_id`. "Reclassified" permits were in the old table with another type, so
the parser or adapter changed them. "New rows" were newly published by the source.

| Source | Newly counted (reclassified) | Newly counted (new rows) | No longer counted | Of those, removals (`adu_removed`) |
|---|---:|---:|---:|---:|
| NC meck | 28 | 0 | 2 | 0 (both negations) |
| NC asheville | 13 | 0 | 2 | **2** |
| NC greensboro | 9 | 0 | 1 | 0 (a negation) |
| TX fw | 4 | 2 | 2 | 0 (both "already built") |
| OH cincy | 3 | 0 | 0 | - |
| TX dallas | 1 | 0 | 0 | - (the one gain is a false positive, fixed in #380) |
| MN mpls | 1 | 1 | 0 | - |
| TX sa, OR bend, NC wilmington, NC raleigh | 0 | 4, 2, 2, 1 | 0 | - |
| every other source | 0 | 0 | 0 | - |

In all: 59 permits reclassified as new ADUs, 7 no longer counted, and 2 of the 7 are explicit ADU removals.
`adu_removed` is a parser field, not a `permits` column. It was found by re-running `parse_description` on the
raw descriptions of the permits that dropped out.

Examples of reclassified permits (raw descriptions, shortened; names and phone numbers left out):

- **Mecklenburg, gained** (code-434 alteration permits naming an ADU): "ADU Upfit (interior renovation)",
  "Accessory Dwelling Upfit (interior completion)", "Mother-in-law suite Upfit (interior renovation)", "Garage
  Apartment Upfit", "In-Law Suite Addition (expand footprint)". The parser itself says "ADU named: unit change
  unclear" for these; the Meck adapter counts them as one new ADU. **Precision risk:** an "upfit (interior
  renovation)" of an ADU may be work on an existing unit.
- **Mecklenburg, lost:** "Detached Garage > 1 story. THIS IS NOT INTENDED TO BE AN ADU"; "Guest house … WITH NO
  KITCHEN". Both are correct exclusions.
- **Asheville, gained:** "NEW ADDITION WITH IN-LAW SUITE AND OFFICE", "ACCESSORY APARTMENT ADDITION IN DAYLIGHT
  BASEMENT", "360 SQ FT ADDITION FOR MOTHER-IN-LAW SUITE … KITCHENETTE". **Possible false positives:** a
  bathroom remodel in the main house that only mentions "FOR DETACHED ADU", and remodels that cite another
  permit "(17-07985 FOR ADU)". The ADU is named as context there, not created by the permit.
- **Asheville, lost (true removals):** "RECD AMENDMENT FORM TO REMOVE ADU DESIGNATION"; "REMOVING KITCHEN
  ELEMENTS … NO LONGER USING AS ADU".
- **Greensboro, gained:** "ADDITION - MOTHER-IN-LAW SUITE", "Addition - Accessory Dwelling", "ALTERATIONS-REMODEL
  FOR IN-LAW SUITE". **Lost:** "add bathroom to accessory building. not to be used as ADU" (correct).
- **Fort Worth, gained:** "Second living unit on 1 lot", "RES REMODEL (GARAGE APARTMENT)", "Turning garage into
  mother in law suite". **Lost:** "MOTHER-IN-LAW SUITE ALREADY BUILT", "MOTHE IN LAW SUITE WAS BUILD W/OUT A
  PERMIT". These are legalizations of existing units, now read as context. Whether a legalized unit counts as
  production is a methods question for the hand checks.
- **Dallas, gained (false positive):** "DETACHED STORAGE SHED - CAN NOT BE USED AS SECOND DWELLING UNIT". The
  negation guard missed "not be used" and the new Rule 3b names. This was a small bug from #376, fixed with tests
  in **#380** (not merged). Dallas goes back to 1 after that PR and a rebuild.

Cincinnati's 3 gains were not pulled from raw. Their `permit_class_raw` values are RALT / RNEW / RADD
(alteration, new, addition).

## Sources moving by more than 25%

- **TX dallas: 1 → 2 (+100%).** One permit, a false positive (above; fixed in #380).
- No other source moved by more than 25%. The largest were Greensboro +22% (36 → 44, 9 additions now read as ADUs),
  Cincinnati +12% and Mecklenburg +6%.

## County remainders and other permit-level lot counts

**37119 (Mecklenburg, unincorporated).** The stored ADU denominator changed kind in this rebuild:

| ADU eligible lots, 37119 | 2010 | 2015 | 2020 | 2023 | 2024 | 2026 |
|---|---:|---:|---:|---:|---:|---:|
| before (`acs_sf_fallback`, the whole county) | 233,801 | 244,840 | 262,935 | 273,448 | 275,566 | - |
| after (`parcels` 2026, `parcels_scaled_acs` before that) | 18,506 | 19,380 | 20,812 | 21,644 | 21,812 | 21,812 |

The rebuilt NC OneMap parcels place 31,156 parcels in 37119, which now counts from the roll. The ACS-fallback
row, which still held Charlotte and the six towns, is gone. Because the row is no longer ACS-fallback,
`eligible.permit_level` leaves it as it is: the BPS-kind and permit-level counts are the same (21,812 in 2024).
Charlotte (3712000) is still on the ACS fallback (203,927 in 2024), and Archdale (3701720) also moved to parcels
(3,591 → 3,678). **Ben should check this change before the joint refit.** It is the denominator the D-074
permit-level remainder was built to fix, and it now comes from parcels by a different route.

**Other remainders that differ between the BPS kind and the permit level** (`eligible.load(..., remainder="permits")`,
ADU theme, 2024; the same 15 years 2010-2024 differ in each):

| GEOID | Jurisdiction | BPS kind | Permit level | Difference |
|---|---|---:|---:|---:|
| 27019 | Carver County unincorporated (MN) | 3,712 | 0 | -3,712 |
| 27139 | Scott County unincorporated (MN) | 7,930 | 1,978 | -5,952 |
| 37025 | Cabarrus County (NC) | 71,518 | 16,213 | -55,305 |
| 37071 | Gaston County unincorporated | 50,375 | 26,805 | -23,570 |
| 37167 | Stanly County | 22,812 | 11,279 | -11,533 |
| 37089 | Henderson County | 40,244 | 29,225 | -11,019 |
| 37151 | Randolph County unincorporated | 36,235 | 27,069 | -9,166 |
| 37101 | Johnston County unincorporated | 55,857 | 48,760 | -7,097 |
| 37001 | Alamance County unincorporated | 23,953 | 18,218 | -5,735 |
| 37161 | Rutherford County unincorporated | 21,337 | 15,960 | -5,377 |
| 37127 | Nash County unincorporated | 16,308 | 11,247 | -5,061 |
| 37023 | Burke County unincorporated | 23,489 | 18,917 | -4,572 |
| 37159 | Rowan County | 46,640 | 42,814 | -3,826 |
| 37057 | Davidson County unincorporated | 40,154 | 36,669 | -3,485 |
| 37145 | Person County | 13,914 | 11,413 | -2,501 |
| 37197 | Yadkin County | 12,311 | 10,073 | -2,238 |
| 37147 | Pitt County unincorporated | 17,804 | 15,806 | -1,998 |
| 37031 | Carteret County unincorporated | 16,824 | 15,371 | -1,453 |
| 37133 | Onslow County unincorporated | 39,607 | 38,812 | -795 |
| 37105 | Lee County unincorporated | 10,575 | 10,024 | -551 |
| 37107 | Lenoir County unincorporated | 8,947 | 8,724 | -223 |
| 37027 | Caldwell County unincorporated | 27,268 | 27,167 | -101 |
| 37169 | Stokes County unincorporated | 11,997 | 11,940 | -57 |

OH, TX and OR have no remainder that differs between the two kinds. Carver at 0 means its local-only members hold
all of its ACS homes; check whether that is expected before using a Carver remainder rate.

Other stored `eligible_parcels` changes (ADU theme): 61 MN rows (2026 parcel counts, each under ±40, from the
refreshed Met Council parcels) and 126 NC rows in 8 jurisdictions (37119 and Archdale above, plus small
2026-roll changes). OH, TX and OR are unchanged.

## Input to the next step (parser hand checks)

These parser sources' ADU counts changed through reclassification, so they need a new 1/recall check: **NC meck
(+28/−2), NC asheville (+13/−2), NC greensboro (+9/−1), TX fw (+4/−2), OH cincy (+3), TX dallas (+1, false
positive, #380), MN mpls (+1).** Precision checks worth adding: Meck "ADU upfit (interior renovation)" and
Asheville main-house remodels that mention an ADU only as context. Fort Worth "already built" legalizations need
a methods call. Every other source's ADU count moved only by newly published rows, or not at all.

## How this was made

Claude Code ran the fetches and wrote throwaway comparison scripts, kept outside the repo. They read the
before-copy and the rebuilt tables and count ADU rows by source and year. They also match gained and lost
`permit_id`s, pull those permits' raw descriptions, and call `eligible.load` with both remainder kinds. Only
aggregates and short shortened descriptions appear here. No downloaded data is committed.
