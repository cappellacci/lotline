# ADU processed-data rebuild, 2026-11-11 (b): offline, code changes only

**What:** every state's processed tables were rebuilt with `lotline fetch --offline --state XX` (#382) on
`origin/main` at `a54f34d9`, one state at a time (MN, NC, OH, TX, OR). That picks up #388 (Cincinnati adapter
rules) and #389 (second shared ADU parser round, D-081 item 6). It also picks up #380 (the Rule 3b negation fix
for Dallas), which was not merged when the morning tables were built. Ben approved this on 2026-11-11. Nothing was
downloaded: offline mode sends no request, and the rebuild read only the cached raw snapshots. The holdout filter
stayed on (`assert_no_leak` on every table), and `--unblind` was not used. No engine, scenario, fit, calibration or
dev-run script was run. Free disk went from 18 GB to 15 GB and never came near the 5 GB stop line.

**Before figures:** before the rebuild, every `permits/` and `eligible_parcels/` table was copied out of
`LOTLINE_DATA_DIR`. Those tables were built that morning (2026-11-11) from the 2026-11-11 raw snapshots
(`reports/adu-rebuild-2026-11-11.md`). An ADU permit is a row with `building_type_std == "ADU"`, counted by
`issue_year`, as in that report.

**Every change is from code.** Three checks support this: (1) every permits table has exactly the same rows
(same `permit_id`s) before and after; (2) every state's `eligible_parcels` table is identical before and after; (3)
for each source that moved, an in-memory rebuild with the morning code's parser reproduces the "before" count, apart
from the adapter changes named below. The offline build read the same snapshots as the morning build. Greensboro
read its 2026-11-09 snapshot as planned.

## Movers (more than 5% or more than 5 permits)

| Source | ADU permits, before → after | Change | Why |
|---|---:|---:|---|
| **OH cincy** | 29 → 18 | −11 (−38%) | #388 development rule (−11 coach units) and negation (−1); +1 house permitted separately |
| **TX dallas** | 2 → 5 | +3 (+150%) | #389 new names (+4: "second dwelling", "2ND DWELLING UNIT"); #380 negation fix (−1) |
| **NC meck** | 441 → 426 | −15 (−3%) | #389 kitchen rule (−33), new names (+13), code 437 (+6), "upgraded" (−1) |
| **NC greensboro** | 44 → 41 | −3 (−7%) | #389 kitchen rule (−9), new names (+6) |

Two more sources barely moved in total but **reclassified many permits**. Both should get fresh hand checks too,
because k = precision ÷ recall depends on which permits are flagged, not just how many:

| Source | Before → after | Permits reclassified | Note |
|---|---:|---:|---|
| **TX fw** | 117 → 115 (−2) | +54 / −56 | In 2015–2026 the count drops from **94 to 64 (−32%)**: the new "GARAGE APT" names fall mostly before 2015 (pre-2015 23 → 51), while the kitchen-rule drops fall mostly after 2015. |
| **NC asheville** | 372 → 373 (+1) | +26 / −25 | The citation fix and new names (+26) and the kitchen rule, legalizations and new-house rule (−25) cancel out. |

**Hand-check list:** Greensboro, Mecklenburg, Fort Worth, Dallas, Asheville, Cincinnati. That is the expected list.
Fort Worth and Asheville are on it because of the reclassifications, not their net totals. Wilmington moved +4
(+1%, new "garage with apartment" names), which is under both thresholds. Every other source is unchanged.

## ADU permits per source per year, before → after

Unchanged cells show one number. "Other yrs" covers issue years before 2015. 2026 is a partial year.

#### MN

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| metc | 0 | 29 | 27 | 29 | 30 | 34 | 29 | 34 | 39 | 36 | 53 | 0 | 1 | 341 | 0 |
| mpls | 0 | 2 | 30 | 25 | 35 | 28 | 16 | 17 | 14 | 16 | 13 | 17 | 0 | 213 | 0 |
| rochester | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 0 | 0 | 0 | 5 | 0 |
| stpaul | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

#### NC

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| asheville | 15→**19** | 37→**42** | 50→**48** | 36 | 20→**21** | 22→**19** | 19→**21** | 28→**24** | 39→**38** | 29→**30** | 38 | 26→**23** | 13→**14** | 372→**373** | +1 (+0%) |
| cary | 0 | 0 | 0 | 0 | 3 | 1 | 3 | 3 | 3 | 13 | 6 | 11 | 0 | 43 | 0 |
| chapel hill | 2 | 5 | 2 | 8 | 5 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 0 |
| durham | 4 | 5 | 7 | 7 | 18 | 15 | 33 | 35 | 82 | 55 | 48 | 48 | 38 | 395 | 0 |
| greensboro | 0 | 1→**0** | 1→**0** | 2 | 2→**1** | 2→**1** | 1→**0** | 2 | 4 | 4→**6** | 6 | 15→**16** | 4→**3** | 44→**41** | -3 (-7%) |
| meck | 7→**6** | 9→**8** | 10→**9** | 23→**20** | 31 | 44→**43** | 31→**29** | 47 | 59→**61** | 79→**77** | 55 | 7 | 39→**33** | 441→**426** | -15 (-3%) |
| raleigh | 0 | 0 | 0 | 0 | 1 | 2 | 23 | 55 | 54 | 37 | 61 | 68 | 0 | 301 | 0 |
| wilmington | 6 | 13 | 6 | 6→**7** | 7 | 19→**21** | 9→**10** | 25 | 46 | 60 | 76 | 81 | 5 | 359→**363** | +4 (+1%) |

#### OH

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cincy | 0 | 0 | 1 | 0 | 0 | 12→**1** | 0 | 2 | 1 | 5 | 4→**3** | 4→**5** | 0 | 29→**18** | -11 (-38%) |
| cle | 0 | 2 | 0 | 0 | 0 | 3 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 7 | 0 |
| columbus | 4 | 2 | 5 | 5 | 4 | 5 | 8 | 5 | 2 | 4 | 6 | 0 | 3 | 53 | 0 |
| columbus variances | 10 | 6 | 6 | 8 | 18 | 21 | 15 | 18 | 18 | 18 | 22 | 0 | 23 | 183 | 0 |
| franklin | 1 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 0 | 2 | 4 | 0 | 1 | 11 | 0 |
| montgomery | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 2 | 2 | 0 | 0 | 7 | 0 |

#### TX

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| austin | 151 | 234 | 357 | 340 | 375 | 330 | 341 | 325 | 243 | 90 | 9 | 2 | 369 | 3,166 | 0 |
| cstx | 0 | 2 | 0 | 6 | 5 | 8 | 2 | 4 | 2 | 4 | 5 | 7 | 0 | 45 | 0 |
| dallas | 0 | 0 | 0→**1** | 0 | 0 | 0 | 0 | 1 | 0→**1** | 0 | 0 | 0 | 1→**2** | 2→**5** | +3 (+150%) |
| fw | 2→**4** | 4→**1** | 3 | 4→**2** | 4→**3** | 9→**7** | 9→**6** | 9→**6** | 16→**11** | 14→**9** | 9→**7** | 11→**5** | 23→**51** | 117→**115** | -2 (-2%) |
| sa | 0 | 0 | 0 | 0 | 0 | 2 | 39 | 41 | 50 | 60 | 62 | 45 | 0 | 299 | 0 |

#### OR

| Source | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Other yrs | Total | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bend | 24 | 45 | 47 | 59 | 66 | 56 | 68 | 84 | 63 | 37 | 51 | 29 | 28 | 657 | 0 |
| medford | 0 | 0 | 0 | 0 | 0 | 6 | 32 | 37 | 54 | 52 | 32 | 23 | 0 | 236 | 0 |
| mwvcog | 0 | 0 | 0 | 8 | 12 | 67 | 24 | 28 | 56 | 21 | 46 | 0 | 0 | 262 | 0 |
| portland | 387 | 549 | 518 | 593 | 341 | 241 | 251 | 275 | 221 | 178 | 160 | 78 | 1104 | 4,896 | 0 |


## Gains and losses by cause

Each moving source was rebuilt in memory (offline, scratch only, nothing written to the data dir) four ways: with
the morning's parser (`1a5d4f04`, before #380), with the parser before #389 (`96866008`), with today's parser, and
with today's parser in its no-kitchen setting. The adapters were always today's code. Comparing these runs gives
three steps:

- **adapter** = morning table → today's adapter with the morning parser (#388 Cincinnati rules; #389's Meck code
  437 and Asheville `NEW_HOUSE`);
- **#380** = morning parser → pre-#389 parser;
- **#389 parser** = pre-#389 parser → today's parser. Each changed permit is sorted by the evidence tags today's
  parser leaves (`NO_KITCHEN_TAG`, `LEGALIZATION_TAG`, "house cited by permit number", "administrative note
  ignored", "alteration", and the matched ADU name).

Each run with today's parser reproduces the rebuilt table exactly, and the three steps add up to each total.

| Source | Before | Adapter | #380 | New ADU names | Asheville citation / admin notes | Kitchen rule | Legalizations | "Upgrade" / door repair words | After | No-kitchen sensitivity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| OH cincy | 29 | **+1 / −12** (development −11, "not a dwelling unit" −1, house permitted separately +1) | 0 | 0 | – | 0 | 0 | 0 | 18 | 19 |
| NC greensboro | 44 | 0 | 0 | +6 | – | −9 | 0 | 0 | 41 | 50 |
| NC asheville | 372 | −2 (new-house rule) | 0 | +13 | +13 / −1 (house + ADU on one permit, now read as the house) | −16 | −4 | −2 | 373 | 390 |
| NC meck | 441 | +6 (code 437) | 0 | +13 | – | −33 | 0 | −1 | 426 | 459 |
| NC wilmington | 359 | 0 | 0 | +4 | – | 0 | 0 | 0 | 363 | 363 (rule not used) |
| TX dallas | 2 | 0 | −1 | +4 | – | 0 | 0 | 0 | 5 | 5 |
| TX fw | 117 | 0 | 0 | +54 | – | −49 | −6 | −1 | 115 | 166 |

**No-kitchen sensitivity** is the ADU count when every adapter's parser call uses
`parse_description(..., in_law_suite_needs_kitchen=False)`. It comes from a full in-memory rebuild of each source,
so adapter rules still apply. Every other parser-using source was rebuilt the same way, and its sensitivity count
equals its central count: Raleigh 301, Cary 43, Chapel Hill 30, San Antonio 299, CSTX 45 and Austin 3,166. Durham,
Rochester and the MN, OH (other than Cincinnati) and OR sources do not use the shared parser. Wilmington's adapter
decides ADUs with the parser's `ADU` name pattern, not `parse_description`, so the kitchen rule does not reach it.

### Examples (raw descriptions, shortened; owner names, phone numbers and e-mails left out)

**Cincinnati (#388 adapter).** Lost: eleven 2020 "Two-story Carriage House with 3 private garages at first floor and
walk-up one-bedroom apartment unit above" permits in one masterplan development (2020: 12 → 1); and "BUILDING AN
ANCILLARY SHED STRUCTURE FOR STORAGE AND PLUMBING… [not a dwelling unit]" (2025). Gained: "New construction of a
detached accessory structure consisting of a garage with accessory dwelling unit above" (2026; the house is
permitted separately). The sensitivity adds "ADDITION OF 'MOTHER-IN-LAW SUITE'" (2020).

**Greensboro.** Gained (new names): "Convert garage to dwelling unit. ADD INTERIOR WALLS FOR BATHROOM & KITCHEN",
"Change of Use - Detached Garage to Dwelling Unit", "Convert existing shed to dwelling unit", "adding detached
garage with apartment above". Lost (kitchen rule): "ADDITION - MOTHER-IN-LAW SUITE", "turning basement into
mother-in-law suite", "CONVERTING GARAGE INTO A MOTHER IN LAW SUITE", "Addition of mother-in-law suite". None of
the nine names a kitchen.

**Asheville.**
- Gained, citation / admin-note fix (Rule 4b/4c): "2 STORY GARAGE APARTMENT…, REF. NEW HOUSE PERMIT 14-16326",
  "NEW ACCESSORY APARTMENT OVER GARAGE…, REF. NEW SINGLE FAMILY HOME 16-005…", "ACCESSORY DWELLING UNIT (SFR
  16-05077) REC AMENDMENT TO ADD MECHANICAL…". Seven of the 13 are from 2016.
- Gained, new names: "DETACHED 2-CAR GARAGE WITH APARTMENT ON 2ND FLOOR", "CONSTRUCTION OF NEW GARAGE WITH UPSTAIRS
  APARTMENT", "RESIDENTIAL INTERIOR RENOVATION TO CREATE BASEMENT APARTMENT, 1 BEDROOM AND 1 BATHROOM".
- Lost, kitchen rule: "CONSTRUCTION OF A DETACHED GARAGE WITH IN LAW SUITE ABOVE, FOR PERSONAL USE ONLY",
  "FINISHING BASEMENT FOR MOTHER IN LAW SUITE TO INCLUDE FULL BATHROOM".
- Lost, legalizations: "CONVERT EXISTING DETACHED GARAGE TO APARTMENT… ALL WORK WAS DONE BY PREVIOUS OWNER AND
  NOT PERMITTED", "After-the-fact residential renovation permit request to bring an existing lower-level living
  space into compliance".
- Lost, new house (adapter `NEW_HOUSE` −2, parser −1): "NEW STICK BUILT HOUSE WITH ADU IN BASEMENT", "CONSTRUCTION
  OF NEW SINGLE FAMILY RESIDENCE… ALSO CONSTRUCTING DETACHED GARAGE WITH UPSTAIRS APARTMENT".
- Lost, "upgrade": "UPGRADE EXISTING STUDIO/APARTMENT ABOVE DETACHED GARAGE" is a correct drop. "BUILD NEW 450 SQ
  FT… ADU WITH CARPORT BELOW… MAIN HOUSE WILL HAVE SERVICE UPGRADE FROM 200 AMP TO 400 AMP" is a **new false
  negative** (see below).

**Mecklenburg.**
- Gained, new names: "GARAGE APT", "RES DET GARAGE W/LIVING QUARTERS", "ATTACHED GARAGE W/ MOTHER-IN-LAW APT",
  "DETACHED GARAGE W/ APARTMENT" (mostly code 438, residential garages).
- Lost, kitchen rule: "RES IN LAW SUITE/SCR PRCH", "CONVERT GARAGE TO IN-LAW SUITE", "Upfit 2nd floor of garage to
  mother-in-law suite", "detached garge w/ in law suite above". Ten of the 33 are from 2009 or 2018.
- Gained, code 437: "detached 1-car garage… New. Accessory Dwelling Unit", "ADU New. Accessory Dwelling Unit", and
  **four "MMF … Basement Unit Upfits" permits in apartment complexes** (see below).
- Lost, "upgraded": "Existing Garage Being Moved and Upgraded to ADU. New. Accessory Dwelling Unit." This is a
  **new false negative**.

**Wilmington** (gained, new names through the adapter's use of the parser's `ADU` pattern): "construct garage apt",
"BUILD GARAGE W/ APARTMENT ABOVE", "DETACHED GARAGE WITH UPSTAIRS APARTMENT/ main house permitted separately".

**Dallas.** Gained: "CONSTRUCT DETACHED GARAGE WITH SECOND DWELLING", "2ND DWELLING UNIT", "RESIDENTIAL ADDITION
OF 400SF ACCESSORY DWELLING UNIT", "Finish work on revoked permit 0506061029 - 2nd dwelling approved…". The last
one finishes work on an earlier permit, so it may count the same unit twice. Lost (#380): "DETACHED STORAGE SHED -
CAN NOT BE USED AS SECOND DWELLING UNIT" (the 2026-11-11 false positive, now fixed).

**Fort Worth.**
- Gained, new names, 54: "GARAGE APT" spellings are the largest group (about 24) ("NEW RES/…/GARAGE APT", "GARAGE APT IN BACK
  @…", "RES/GARAGE APT/HV", "EB/REAR GARAGE APT"), plus "detached living quarters" (4) and "garage with/w
  apartment / living quarters" (most of the rest). 36 of the 54 are before 2015.
- Lost, kitchen rule, 49: "RES/ADDITION/MOTHER-IN-LAW SUITE/GAMEROOM/GARAGE", "RES/ NEW MOTHER-IN-LAW QUARTERS",
  "RES/DETACHED MOTHER-IN-LAW SUITE/NO KITCHEN". 42 of the 49 are 2015 or later.
- Lost, legalizations, 6: "CONVERTING GARAGE INTO APARTMENT (WORK HAS BEEN DONE)", "Accessory Dwelling 924 square
  feet… Accessory already built without permit", "ALREADY BUILT DETACHED MOTHER IN LAW SUITE".
- Lost, repair words: "GARAGE APARTMENT/REPLACE 1 EXTERIOR DOOR" (correct).

## Precision and recall points for the hand checks

1. **Meck code 437 brings in apartment basement units.** Four of the six code-437 gains are "MMF … Basement Unit
   Upfits" permits in apartment complexes. They read as ADUs through "basement unit". Only two are real ADUs. This
   is a precision loss from #389 that the Meck hand check should measure, or that a guard should fix (code 437 plus
   an apartment-complex or multi-unit context).
2. **"Upgrade" now vetoes real new ADUs.** "BUILD NEW 450 SQ FT ADU… MAIN HOUSE WILL HAVE SERVICE UPGRADE"
   (Asheville) and "Existing Garage Being Moved and Upgraded to ADU. New. Accessory Dwelling Unit." (Meck) are both
   new ADUs that #389 now drops. These are recall losses.
3. **A house and an ADU on one permit now counts as the house only** (Asheville, 3 permits). Examples: "NEW STICK
   BUILT HOUSE WITH ADU IN BASEMENT", and a new single-family residence "ALSO CONSTRUCTING DETACHED GARAGE WITH
   UPSTAIRS APARTMENT". A methods call: should one permit be able to count as both a house and an ADU?
4. **The kitchen rule is the biggest single effect.** It removes 107 permits across the four NC/TX sources (Meck
   33, FW 49, Asheville 16, Greensboro 9). Some say "NO KITCHEN" explicitly (correct drops). Many are purpose-built
   detached suites that just don't mention a kitchen. The sensitivity column is the upper bound to carry into the
   refit's uncertainty.
5. **Fort Worth's year mix shifts.** Its 2015–2026 count falls by a third (94 → 64), while its pre-2015 count more
   than doubles (23 → 51). A fit that uses 2015 onward sees Fort Worth as a −32% mover.
6. **Fort Worth has two ADU rows with 0 new units** (demolitions): "RELOCATE STAIRS… OF THE REAR GARAGE APT. & Demo
   3 sided enclosure" (not an ADU permit at all) and "demo and rebuild garage apt". Row counts include them; unit
   sums do not (115 rows, 113 units).
7. **Fort Worth legalizations repeat.** The same "Storage Shed / Already Built… REVISED 10/23/19… (MOTHER IN LAW
   SUITE) WITHOUT KITCHEN" text appears on a 2019 and a 2023 permit.

## Changes outside ADUs

These are not ADU counts, but the same parser changes moved them:

- **Asheville, 8 condominium permits (2018, one building)** go from MF5 with 13 units each to UNKNOWN. Each
  unit's permit quoted the building's "13 CONDO UNITS" in an amendment note, which #389 now drops as an
  administrative note. The old reading counted 104 homes for 13 condos, so the new reading is probably closer to
  right. Even so, Asheville MF5 units fall by 104 (1,699 → 1,595), which matters to whoever owns missing-middle
  counts.
- Mecklenburg: 100 more rows get a unit count from their text (total units −14). Chapel Hill: 29 more rows get a
  count (SFD units −1). Greensboro: SFD units −5. Austin: 3 rows' unit fields change, with no net change. CSTX: one
  `adu_type` changes. These come from the new "alteration" words ("upgrade", "replace 1 exterior door"), the
  kitchen rule and the new names.

## Problems found with `lotline fetch --offline` (first run on real data)

It worked: every source with a cached snapshot rebuilt, nothing was downloaded, and the failures were loud and
specific. Five issues:

1. **Two adapters still call the network directly** and fail offline: MN `rochester_permits` ("refused a network
   request to lf.rochestermn.gov") and NC `clt_udo_translation` ("refused … services.arcgis.com"). Both processed
   tables were left as they were. Rochester does not use the shared parser (its 5 ADUs are unchanged), and the UDO
   translation is not a permits table. The CLI exits 1 for MN and NC because of these two.
2. **Ohio parcels mix vintages per query.** "Newest complete snapshot" works query by query, so the 1,051 queries
   that finished in the stopped 2026-11-11 re-download were read from 2026-11-11, 64 from 2026-11-01 and 4,523 from
   2026-10-19. 9,100 "incomplete" notes were printed. The OH `eligible` table came out identical, so nothing moved
   here. But a stopped download now silently feeds an offline build, and the brief's "built from the 2026-11-01
   parcels" no longer describes `oh_parcels.parquet`. The partial `raw/oh_parcels/2026-11-11` folder (258 MB) is
   still there. A design choice is needed: delete it, or make offline builds use one vintage per source.
3. **Repeated notes:** `metc_parcels` printed the same five "skipped, downloaded from Parcel_Points_20XX (expected
   Parcel_Points_Aggregate)" notes about 13 times, so notes seem to pile up across calls.
4. **Empty build records:** `cary_permits` and `wake_realestate` rebuilt fine but recorded "0 cached
   snapshot(s)/file(s)" in `manifest.builds.jsonl`. They read their cache through a path the session doesn't track,
   which leaves a provenance gap.
5. A warning that is not new: `jurisdictions` skips three MN and one OR local permit GEOIDs unknown to the 2020
   Census.

## How this was made

Claude Code ran the five offline fetches and wrote throwaway comparison scripts, all kept in the session
scratchpad, outside the repo. The scripts:

- read the before-copy and the rebuilt tables and count ADU rows by source and year;
- rebuild each parser-using source in memory with three parser versions (taken from git at `1a5d4f04` and
  `96866008`) and the no-kitchen switch, with the module-level `parse_description` (and Wilmington's shared `ADU`
  pattern) swapped;
- record each permit's description text, sort each change by today's parser evidence tags, and diff every column
  of every permits table.

The categories are mechanical and come from the evidence tags. The precision and recall points above come from
reading the changed descriptions. Only aggregates and short shortened descriptions appear here, and no downloaded
data is committed.
