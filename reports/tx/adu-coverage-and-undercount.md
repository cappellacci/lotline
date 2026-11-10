# Texas ADUs: coverage, the flag undercount k, and more places (D-074 / D-075 steps for TX)

*WS-TX data thread (reopened for this task only), 2026-11-10. §0 was committed in 8d1e7c3d before any count. Descriptive counts only; no engine, scenario,
calibration or fit run. TX has no holdouts (`config/states/tx.yaml`); every processed table is read through
`DataStore.read`, which applies `holdout.apply`.*

## 0. Rules written and committed before any count

This section was committed before any count of R, P or HOME-era permits was made. What had been looked at
before writing it: the TCAD 2026 export's file list; the frequency of improvement types in `IMP_INFO.TXT`
over the whole roll (all of Travis County, no year, no city filter: 5,879 `ADDITIONAL LIVING QUARTER`, 1,892
`GARAGE APARTMENT`, 10,213 `2 FAM DWELLING`, 313,826 `1 FAM DWELLING` improvements); the detail-segment codes
in the first 200,000 rows of `IMP_DET.TXT`; the field lists of the five StratMap vintages; the distinct
values of `reform_flag_raw` and `permit_class_raw` in the processed Austin permit table (whole table, no year
split, no parcel match).

### 0.1 StratMap cannot measure k

The five StratMap vintages in `raw/stratmap_parcels/` (2019-03, 2022-07, 2024-02, 2025-06, 2026-09) carry
the same 35–40 fields: IDs, owner and mailing fields, legal area and description, the state and local
land-use codes, land, improvement and market values, situs address, tax year and **one `year_built` per
parcel**. There is no building, card or improvement table and no unit count, so a second home on a lot can
only show as a land-use code change (A1 to B?) or a rise in improvement value. Neither identifies a second
dwelling: districts keep A1 for a house with a garage apartment, and a value rise is any addition or
reappraisal. Many 2025 county parts, Travis among them, carry no land-use code at all
(`docs/build/tx-readiness.md` §3). **So k cannot be measured from a StratMap roll diff.**

### 0.2 What TCAD's single roll can do instead (deviation from D-074's two-roll design)

TCAD is 2026 only, but its export has **one record per improvement** (`IMP_INFO.TXT`: prop_id, imprv_id,
improvement type) and **a year built per improvement segment** (`IMP_DET.TXT`). A lot that gained a second
home in 2019–2023 shows, on the 2026 roll, a second dwelling improvement whose segments were built in those
years next to a main house built earlier. This replaces NC's two-roll diff with one roll's improvement
history. What it cannot see, and NC's diff could: an old outbuilding newly carded as a dwelling (its
segments keep their old year built), and a teardown that left no trace. Both are stated as limits; the first
puts converted-garage ADUs in "P \ R", not in R.

### 0.3 Detection rule (R)

Fields read, by position (Legacy 8.0.33 layout, confirmed on the file):
`IMP_INFO.TXT` prop_id (1, 12), imprv_id (17, 12), imprv_type_cd (29, 10), imprv_type_desc (39, 25);
`IMP_DET.TXT` prop_id (1, 12), imprv_id (17, 12), imprv_det_type_cd (41, 10), yr_built (86, 4);
`PROP.TXT` prop_id, prop_type_cd, sup_num, geo_id as in `tcad_parcels`. No owner, address or other personal
field is sliced.

- **Dwelling improvement:** type `01` 1 FAM DWELLING, `120` ADDITIONAL LIVING QUARTER, `21` GARAGE
  APARTMENT, `02` 2 FAM DWELLING, `03` TRIPLEX, `04` FOURPLEX, `11`–`14` mobile homes. Townhome (`16`) and
  condo (`15`, `22`) improvements are not dwellings for this purpose: their parcels leave the universe.
- **Improvement year built:** the earliest `yr_built` (1800–2026) among its **living-floor segments**
  (`1ST`, `2ND`, `3RD`, `4TH`, `5TH`, `RSBLW`); if it has none, the earliest among all its segments. An
  improvement with no valid year is not dated and cannot be a new one.
- **Universe (denominator):** City of Austin real property (`tcad_parcels`, jurisdiction 4805000, highest
  supplement) with no townhome or condo improvement, whose **main house** — the type-01 improvement with the
  earliest year built — was built **before 2019**. These are lots with an existing house that survived to the
  2026 roll.
- **Gained a second home in the window (R):** a universe parcel with another dwelling improvement, other than
  the main house, built **2019–2023**. Its group is set by the newest such improvement:

  | Group | Newest second dwelling improvement | In R (headline)? |
  |---|---|---|
  | `alq` | `120` additional living quarter or `21` garage apartment | **yes (strict count)** |
  | `house` | a second `01` one-family dwelling | **yes** |
  | `multi` | `02`–`04` (a duplex or larger built next to a kept house) | no: reported apart (missing middle) |
  | `moho` | `11`–`14` mobile home | no: reported apart |

  R (headline) = `alq` + `house`; the strict count is `alq` alone.
- **Rate:** R ÷ universe × 1,000 ÷ 5 years (2019–2023), with a 95% Wilson interval. The same rule by single
  year built (2015–2025) is reported as a roll-based check on the permit series; years after 2023 are
  incomplete (a home built in 2025 may not be carded by the 2026 roll).

### 0.4 Permit side and k (D-074 step 1, with its 2026-11-10 duplex deviation)

- **P:** Austin permits flagged as ADUs (`building_type_std == "ADU"`: class R-/C- 102 Secondary Apartment),
  issued **2018-07-01 to 2023-06-30** (six months' lead, because a 2019 year built can come from a late-2018
  permit, and six months' completion lag, as D-074), matched to the roll by `parcel_id` (= "48453" + TCAD
  geo_id, the permits' `tcad_id`). One per parcel. A flagged permit on a parcel outside the universe is
  listed apart, not as P \ R. Sensitivity: D-074's own window, 2019-01-01 to 2023-06-30.
- **Group (a), permitted but unflagged:** a parcel in R \ P with an Austin permit at the parcel in the same
  window for new residential building or added units that is not flagged ADU (classes 101, 103, 104, 436,
  and plain-class "New" with units). **As in D-074's deviation, parcels whose only such permit is a 103
  (two-family building) are left out of (a)** (a duplex rebuild, not an ADU); the as-written value with them
  is reported too.
- **Group (b), unpermitted or not found:** R \ P with no such permit.
- **k = (|P∩R| + |a|) / |P∩R|**, 90% interval from the Wilson interval on |P∩R| / (|P∩R| + |a|), inverted
  (`nc.wake_roll_diff.k_undercount`). Beside it: the Chapman total (|R| + 1)(|P| + 1)/(|P∩R| + 1) − 1 as a
  lower bound, and |P \ R|.
- **HOME window (not part of k):** the same match for 2024–2025 is reported only as a check on the HOME rule
  below, because R-102 nearly stops after HOME.

### 0.5 Austin HOME rule: ADUs filed as houses or duplexes (2024 on)

HOME (phase 1, effective **2024-02-05**) removed the secondary-apartment use; a second or third home on a lot
is now one permit per building, an R-101 house or an R-103 two-family building (`austin_permits` module
doc). D-070's TX caveat: those ADUs count as houses or duplexes, so the observed ADU floor falls. **Rule**,
applied to permits issued from 2024-02-05:

A permit counts as an ADU (ADU-equivalent) when all hold:
1. its class is 101, 102 or 103 with work class New (or 436, added units), not a demolition;
2. its parcel has a **house that stays**: on the 2026 TCAD roll the parcel has a type-01 dwelling
   improvement built **before the permit's issue year** (the existing house), and no condo or townhome
   improvement;
3. **no residential demolition** (classes 645, 646) is filed at the parcel from three years before the
   permit's issue date to the end of the data (a demolished house means a rebuild, not an addition).

Units counted: `units_new` of the permit (101/102 → 1; 103 → its units, usually 1 per side or 2 per
building). Reported both ways: **ADU permits** (each qualifying permit is one ADU building; this is the unit
the model's outcome uses) and **ADU-equivalent homes** (their units). Permits failing (2) or (3) stay houses
or duplexes. The same rule is applied to 2015–2023 as well, so the HOME-era count can be compared with a
consistent series (before HOME it measures "second buildings on existing-house lots", which includes the
R-102 ADUs and the group-(a) permits).

Known limits, before counting: a house built in the issue year and an ADU permitted the same year are not
counted (condition 2 asks for an earlier year); a demolition filed outside the city's BP data (none known) is
missed; the 2026 roll shows a house still standing in January 2026, so a 2025 permit that later replaces it
is counted until a demolition permit appears.

---

## In short

- **Coverage:** **13.8% of Texas's 7.32 million ADU-eligible lots** sit in the four places whose permits flag
  ADUs (San Antonio, Fort Worth, Dallas, Austin). With College Station added: 14.1%. Texas has no overlapping
  units (every place is a BPS reporter), so the raw sum and the non-overlapping sum are the same. The two
  largest units, unincorporated Harris County and Houston (14% of the state between them), have no
  record-level permits.
- **k in Austin: 1.13 (90% interval 1.09–1.18)**, from |P∩R| = 242 and group (a) = 31. The duplex deviation
  changes nothing, because none of the 31 group-(a) permits is a duplex. StratMap can't measure k, because it
  has no building detail. TCAD's single 2026 roll can, through its improvement records (a deviation from
  D-074's two-roll design, §0.2).
- **The roll side is weak in Austin:**
  - Only 532 of the 1,605 parcels with an ADU-flagged permit (2018-07 to 2023-06) keep their parcel ID on the
  2026 roll. Austin ADU lots are usually re-platted or turned into two-unit condominiums, and then get new IDs.
  - TCAD's "additional living quarter" also covers pool houses and casitas.
  - So the Chapman total and group (b) are not usable measures. k uses only the ADUs that our flags miss, so
  it is the robust number.
- **Austin HOME rule (§0.5):** in 2024 and 2025 the rule finds 106 and 151 permits that add a building next
  to a house that stays, against 90 and 9 R-102 permits. Pre-HOME checks show the rule needs two corrections
  (§3): a recall correction (lots that change ID) and a precision range for R-101 permits. **Austin ADU
  permits: about 104–217 in 2024 and 53–290 in 2025, against 330–375 a year in 2019–2022 (R-102 × k).**
- **More places:** only one large uncovered place has an open, scriptable record-level source that flags ADUs:
  **College Station** (new adapter `cstx_permits`, its "Living Quarters" subtype). It counts 2–8 ADU permits a
  year, **0.14 per 1,000 eligible lots a year in 2021–24**. Its license is not stated. **Denton** has an ADU
  subtype, but its portal sits behind a bot check, so Ben would download it by hand (steps in §4.3). Houston,
  El Paso, Arlington, Plano, Corpus Christi, Lubbock, Laredo, Amarillo, Frisco, Garland, McKinney and Grand
  Prairie have no usable source (§4.3).
- **Rule rows:** no new rows are needed for College Station or Denton (both coded). One row is proposed for a
  check: College Station before 2018 (§5).

## 1. Coverage audit (D-075 step 1)

`uv run python scripts/dev/tx_adu_coverage.py` (theme `adu`, current rule version, each unit's newest
eligible-lot year ≤ 2024; `adu.non_overlapping` with Census county shares).

- **7,315,760 eligible lots in 1,003 units.** The raw sum is the same: every Texas place reports to the BPS
  (`in_bps`), so no county remainder holds a local-only place's homes and nothing is removed.
- Denominator mix (share of lots): ACS fallback 29.1%, parcels interpolated 26.2%, parcels scaled to ACS 44.6%.
- **Covered** (record-level permits that flag ADUs): Austin 163,890; San Antonio 365,165; Dallas 230,655;
  Fort Worth 252,742. **Total 1,012,452 = 13.8%.** With College Station (22,450, §4): 1,034,902 = 14.1%.
- Houston's summary file (`checks.houston_permits`) has monthly counts and no ADU field, so Houston is not
  covered.

The 25 largest units by eligible lots, together 50.9% of the state. 27.2% of their lots are covered.

| # | Place | GEOID | Eligible lots (2024) | Denominator | ADU-flagged permits? |
|---:|---|---|---:|---|---|
| 1 | Harris County unincorporated | 48201 | 575,338 | parcels scaled to ACS | no (no county permit file) |
| 2 | Houston | 4835000 | 444,742 | ACS fallback | no (summary counts only) |
| 3 | San Antonio | 4865000 | 365,165 | parcels interpolated | **yes**: permit type |
| 4 | Fort Worth | 4827000 | 252,742 | parcels scaled to ACS | **yes**: parser |
| 5 | Dallas | 4819000 | 230,655 | parcels scaled to ACS | **yes**: parser (to 2024-11) |
| 6 | El Paso | 4824000 | 182,889 | parcels scaled to ACS | no (new-residential layer, no ADU signal) |
| 7 | Montgomery County unincorporated | 48339 | 178,794 | parcels scaled to ACS | no |
| 8 | Bexar County unincorporated | 48029 | 175,564 | parcels scaled to ACS | no (San Antonio's ETJ rows are a part) |
| 9 | Fort Bend County unincorporated | 48157 | 171,077 | parcels scaled to ACS | no |
| 10 | Austin | 4805000 | 163,890 | parcels scaled to ACS (TCAD) | **yes**: R-102 class (to 2023), HOME rule after |
| 11 | Arlington | 4804000 | 96,400 | parcels interpolated | no (3-year rolling layer; robots.txt bars our agent) |
| 12 | Corpus Christi | 4817000 | 88,238 | parcels scaled to ACS | no (monthly PDF/XLSX reports) |
| 13 | Travis County unincorporated | 48453 | 84,649 | parcels scaled to ACS | no |
| 14 | Lubbock | 4845000 | 75,436 | parcels scaled to ACS | no (dashboard only) |
| 15 | Plano | 4858016 | 73,482 | parcels interpolated | no (aggregates only) |
| 16 | Hidalgo County unincorporated | 48215 | 66,000 | parcels interpolated | no |
| 17 | Laredo | 4841464 | 64,016 | parcels interpolated | no (2014–2018 layers, frozen; no ADU hits) |
| 18 | Amarillo | 4803000 | 62,437 | ACS fallback | no (monthly PDFs) |
| 19 | Frisco | 4827684 | 58,449 | parcels interpolated | no (active permits only) |
| 20 | Williamson County unincorporated | 48491 | 58,166 | ACS fallback | no |
| 21 | Garland | 4829000 | 57,764 | parcels interpolated | no (no portal found) |
| 22 | McKinney | 4845744 | 56,189 | parcels interpolated | no (2023 snapshot only) |
| 23 | Denton County unincorporated | 48121 | 52,035 | parcels scaled to ACS | no |
| 24 | Brownsville | 4810768 | 46,846 | parcels interpolated | no (2023–26 snapshot; accessory type is mostly sheds) |
| 25 | Grand Prairie | 4830464 | 42,684 | parcels scaled to ACS | no (quarterly PDFs) |

What this means for D-075's tier test: Texas's measured places are its four big cities. The tier-2 city is
San Antonio (the largest measured city by lots); the tier-0/1 target is then Austin, Dallas and Fort Worth
(plus College Station once its rows are accepted).

## 2. Flag undercount k in Austin

`uv run python scripts/dev/tx_austin_adu_k.py` (aggregates in `reports/tx/austin-adu-roll.json`; no parcel
table written). Functions and tests: `src/lotline/adapters/states/tx/austin_adu_roll.py`,
`tests/states/tx/test_austin_adu_roll.py`; k, Wilson and Chapman from `nc.wake_roll_diff`.

### 2.1 Roll side (R)

- 239,626 City of Austin TCAD parcels; 225,873 have improvement records; **universe 157,588** (a type-01
  house built before 2019, no condo or townhome improvement).
- **Second dwelling built 2019–2023: 918 in R** (`alq` 591, `house` 327), plus 3 `multi` and 1 `moho`
  reported apart. That is **1.17 per 1,000 universe lots a year** (95% Wilson 1.09–1.24). Strict count
  (`alq` alone): 0.75.
- By year built (roll check, same rule one year at a time):

| Year built | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024* | 2025* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `alq` | 133 | 122 | 121 | 140 | 113 | 117 | 96 | 141 | 126 | 84 | 116 |
| `house` | 72 | 66 | 83 | 78 | 68 | 32 | 71 | 84 | 74 | 47 | 134 |
| R-102 permits issued | 151 | 234 | 357 | 340 | 375 | 330 | 341 | 325 | 243 | 90 | 9 |

\* incomplete: a home built in 2024–25 may not be carded by the January 2026 roll. The 2025 `house` jump
(134) is consistent with HOME-era second houses.

### 2.2 Match and k (P window 2018-07-01 to 2023-06-30)

| Quantity | Value |
|---|---:|
| R (headline) | 918 |
| P (flagged, on universe lots, one per parcel) | 305 |
| Flagged permits on lots outside the universe | 1,300 |
| \|P∩R\| | 242 |
| Group (a): R \ P with an unflagged new-building permit | 31 (all R-101; none R-103) |
| Group (a) as written (duplexes in) | 31 |
| Group (b): R \ P with no such permit | 645 (`alq` 503, `house` 142) |
| \|P \ R\| | 63 |
| **k = (242 + 31) / 242** | **1.13 (90%: 1.09–1.18)** |
| k as written | 1.13 (1.09–1.18), the same |
| k, strict R (`alq` only) | 1.07 (1.04–1.14), \|P∩R\| 82, \|a\| 6 |
| k, D-074's own P window (2019-01-01 to 2023-06-30) | 1.12 (1.09–1.17), \|P∩R\| 237, \|a\| 29 |
| k, adding ADU-named addition permits to (a) (sensitivity) | 1.21 (1.16–1.27), +19 |
| Chapman total (lower-bound check) | 1,156 (95%: 1,100–1,213) |
| Flagged share of R | 26% (24–29%) |

**How to read it.**

- **k is the number to use, and it agrees with Raleigh's** (1.07, 1.02–1.21).
  - (a) needs a permit for a new house on a lot whose old house stays, and the roll must show that second home.
  - The 31 such parcels are second houses permitted as R-101 instead of R-102.
  - Adding the 19 ADU-named addition permits (attached ADUs filed as R-434; fetched for this check, see
    below) gives 1.21. That is a sensitivity, because D-074's group (a) counts new buildings only.
- **Permitted ADUs are carded as houses, not as "additional living quarters".**
  - Of the 242 matched, 160 sit in `house` and only 82 in `alq`.
  - So the `alq` group is mostly something else. Its segments are first floors, HVAC and bathrooms, and the
    addition permits on those lots describe pool houses, casitas, studios with a bath, and garage
    conversions. TCAD values them as living quarters; most have no kitchen and are not homes.
- **Group (b) and the Chapman total are not measures of unpermitted ADUs here.**
  - 262 of the 645 group-(b) lots have an addition or remodel permit (R-434/435) in the window, against
    10.2% of all universe lots.
  - Only 19 of those permits name an ADU.
  - The rest are R lots whose second structure the roll calls living quarters.
  - Following D-074, (b) is reported, not added.
- **Most flagged ADUs leave the universe.**
  - Only 532 of the 1,605 flagged parcels keep their ID on the 2026 roll.
  - Of 1,614 R-102 permits issued 2019–2023, 556 have an ID on the 2026 roll, and 309 of those have a house
    built before the permit year.
  - The likeliest cause is that Austin owners often split a house and an ADU into a two-unit condominium
    regime, which creates new IDs. This is not checked: the legal description is never read.
  - So R comes from lots that kept their ID. That may lean toward owner-occupied ADUs, and it is why the
    flagged share of R (26%) and the Chapman total understate the flags.
  - k needs only the R lots, and their permits sit on the same IDs.

**Addition permits (added for this check).** The adapter downloads only the classes that add or remove
dwellings. `scripts/dev/tx_austin_additions_fetch.py` downloaded the R-434 "Addition & Alterations" and R-435
"Renovations/Remodel" building permits issued 2018-07-01 to 2025-12-31 (32,294 rows; 22,806 in Austin inside
the k window) through the IO layer (manifest source `austin_permits`, name `additions_434_435`; same
non-personal field list). They are read only by these scripts and not added to the processed table.

### 2.3 What would give Texas a two-roll k

An older TCAD certified export (for example 2019 or 2020, same Legacy 8 layout) would make NC's two-roll
design possible: improvements gained between two rolls, matched by `prop_id`. A condominium split also leaves
a trail between two rolls (the parent ID disappears, and two condo units appear on the same land). If
traviscad.org's public-information page lists earlier certified exports, Ben can download one in a browser
(the site has a bot check) and run `lotline manifest register --source tcad --vintage <export date>`.
StratMap can't stand in: it has one year built per parcel and no improvement table.

## 3. Austin ADUs by year under the HOME rule

Rule §0.5. Columns: R-102 permits (the old ADU class); permits passing the rule (by class); the homes they
add; permits with the HOME phrase ("TWO/THREE UNIT RES"); phrase permits passing the rule.

| Year | R-102 | Rule passes (101 / 102 / 103) | Homes | HOME phrase | Phrase and rule |
|---|---:|---|---:|---:|---:|
| 2019 | 375 | 92 (42 / 50 / 0) | 92 | 0 | 0 |
| 2020 | 330 | 97 (53 / 44 / 0) | 97 | 0 | 0 |
| 2021 | 341 | 113 (44 / 69 / 0) | 113 | 0 | 0 |
| 2022 | 325 | 108 (39 / 68 / 1) | 109 | 0 | 0 |
| 2023 | 243 | 122 (61 / 60 / 1) | 123 | 0 | 0 |
| 2024 | 90 | 106 (63 / 37 / 6) | 112 | 37 | 2 |
| 2025 | 9 | 151 (132 / 6 / 13) | 155 | 149 | 11 |

**Post-count notes (written after these counts were read; the §0.5 rule itself is unchanged):**

1. **HOME-phrase permits are mostly teardowns, and the rule correctly keeps them out.** 233 phrase permits
   (2024–2026) sit on 107 lots, 1–3 permits per lot. 160 of them are on lots with a 645/646 demolition, and
   only 40 sit on a lot whose house predates the permit year. They are 2- and 3-unit rebuilds (missing
   middle), not ADUs.
2. **Recall: the rule misses lots that changed ID.** Measured on R-102 permits, the old class whose ADUs are
   known, the rule passes 291 of 1,614 issued 2019–2023 (18%). In 2024–2025 it passes 43 of 99 (43%, 95%
   Wilson 34–53%). Recent permits have had less time to be re-platted.
3. **Precision of R-101 passes.** Of the 305 R-101 permits that pass the rule in 2016–2022, only 36 (12%)
   show a new dwelling improvement on the 2026 roll beside the kept house. For R-102 passes the share is
   363 of 439 (83%). Before HOME, most "new house on a lot with a house" R-101 permits were not second homes
   (rebuilds whose demolition was filed another way, or permits never built). After HOME, R-101 is the ADU
   vehicle, so its precision is unknown and lies somewhere between those two values.

**Estimate (a range, not one number).** ADU permits = (R-102 passes + p × other passes) ÷ recall, with p
from 0.12 (pre-HOME R-101 precision) to 0.83 (R-102 precision) and recall 0.434 (2024–25 pooled).

| Year | Low (p = 0.12) | High (p = 0.83) | Middle (p = 0.47) |
|---|---:|---:|---:|
| 2024 | 104 | 217 | 160 |
| 2025 | 53 | 290 | 171 |

Recall's own 95% interval (0.34–0.53) widens each bound by about ±25%.

**Check on pre-HOME years.** The same estimator for 2021 gives 367 (low p) to 522 (high p), against R-102 ×
k = 341 × 1.13 = 385. Its low end reproduces the flagged count, which supports the recall correction. For
comparison, D-070's trailing floor put Austin at 232 a year and the pre-HOME level at about 371.

**What this means for D-070's TX caveat.** HOME did not raise Austin's ADU permits in 2024–25. Even the
high end (217–290) stays below 2019–2022 (330–375 flagged, about 370–420 with k). Part of the old volume
moved into 2- and 3-unit teardowns, which the HOME phrase marks. The central value for the floor would be
the middle column. The range is wide, and only a 2027 TCAD roll (which would show which 2024–25 R-101
permits became second homes) can narrow it. **Wiring this into `austin_permits` is a WS-TX/WS-CORE
follow-up.** It needs the TCAD roll inside a permit adapter (a cross-source dependency), so nothing in the
processed table changes in this PR.

## 4. More places

### 4.1 College Station (new adapter `cstx_permits`)

- Source: "Permits - Master Dataset", Socrata `hrbn-znt6` on data.cstx.gov. 22,600 permits of the
  downloaded types (1989 to 2026-11); 563–1,111 a year in 2010–2026. No license is stated (as for Dallas).
  robots.txt allows `/resource` with a one-second delay. Fetched with `lotline fetch --state TX --source
  cstx_permits`.
- ADUs: the city's own subtype "Living Quarters" (Accessory 2016; Residential Accessory 2018 on). The
  description parser on accessory and addition permits finds no further ADUs.

| Year | ADU permits | Eligible lots | Per 1,000 lots |
|---|---:|---:|---:|
| 2016 | 2 | 18,923 | 0.11 |
| 2017 | 0 | 19,044 | 0 |
| 2018 | 6 | 20,140 | 0.30 |
| 2019 | 5 | 20,918 | 0.24 |
| 2020 | 8 | 21,605 | 0.37 |
| 2021 | 2 | 21,594 | 0.09 |
| 2022 | 4 | 22,127 | 0.18 |
| 2023 | 2 | 21,927 | 0.09 |
| 2024 | 4 | 22,450 | 0.18 |
| 2025 | 5 | 22,450 (2024) | 0.22 |
| 2026 (to 2026-11) | 7 | | |
| **2021–24** | **12** | | **0.14 a year** |

Eligible lots: `eligible_parcels` (theme `adu`; parcels scaled to ACS, the 2025 StratMap roll 22,450). For
comparison, D-075's NC rates run from Greensboro's 0.03 to Asheville's 2.7.

**Hand check (30 matches, 30 non-matches; descriptions read in memory, phone numbers and emails scrubbed,
nothing stored):**
- **Matches:** 30 of the 45 ADU permits, drawn at random. All 30 carry the city's "Living Quarters" subtype,
  so precision is 30/30 by construction. Most have no description; those that do say "Living quarters over
  garage", "Guest house" or "Present built addition to rear". The city counts guest houses as living quarters.
  Whether every one has a kitchen is not stated.
- **Non-matches:** the 21 accessory or addition permits whose description holds a dwelling-like word (living,
  guest, apartment, quarter, kitchen, casita, studio, suite...), plus 9 drawn at random from the other 2,431.
  - 3 possible misses: "Adding a new guest house in the same place as garage" (2015, before the subtype
    existed), "Casita" (2023, subtype "Other") and "Garage living space" (2017, subtype "Storage Building").
  - The other 27 are outdoor kitchens, room additions, sorority and church additions, apartment complexes
    and blank or code-only descriptions.
- **Recall:** at most 3 missed among 48 candidates, so recall is at least 45/48 = 0.94 (90% Wilson
  0.85–0.97). This is a field-flagged source (the city's subtype), so under D-075 §2 it draws k from the
  measured sources (Raleigh, Austin) rather than 1/recall.

Tests: `tests/states/tx/test_cstx_permits.py` (synthetic rows: types, units, the subtype and parser ADUs,
statuses, IDs, privacy, schema). Provenance row: `docs/data_provenance.md`.

### 4.2 Why College Station and not El Paso, Arlington or Plano

The brief named El Paso, Arlington and Plano as candidates. None qualifies:
- **El Paso** has a "NewResidential" layer (1994–2026, 42,763 rows, units and Census category) with no ADU
  signal: blank descriptions, and no casita or ADU hits. It is good for house and duplex counts, not ADUs.
- **Arlington**'s "Issued Permits" layer is CC-BY 4.0, but it is a rolling 3-year window with no ADU type.
  Its host's robots.txt disallows our crawler, so no adapter is built.
- **Plano** publishes only aggregates (133 summary rows).

Of the 17 cities scouted, the only record-level sources that flag ADUs are College Station (scriptable),
Denton (bot-checked) and Irving (text only, one ADU hit in 25,000 permits).

### 4.3 Scouted, not built

| Place | What exists | Why no adapter | What would close it |
|---|---|---|---|
| Denton (4819972) | "Building Safety Yearly Permits" (CKAN), CSV per year 2020–2026, `PERMIT_SUBTYPE` 'ACCESSORY DWELLING UNIT' (scout: 11, 7, 16, 7, 15 in 2021–25; 0 in 2020, so check the naming); monthly XLSX from 2016 (CC-BY per the scout, not verified) | Dataset pages return a Cloudflare Turnstile check to scripts; robots.txt disallows `/api/` and `/datastore/`. No license on the yearly set | **Ben, by hand:** open https://data.cityofdenton.com/dataset/building-safety-yearly-permits in a browser, download `2020_All_Permits_issued.csv` … `2026_All_Permits_Issued.csv`, put them in one folder and run `lotline manifest register --source denton_permits --vintage 2026-11-10 <file>` for each. An adapter then reads the registered CSVs (a follow-up; its layout needs the real file) |
| Irving (4837000) | ArcGIS "Residential Permits Issued" 2018-01 to 2025-02 (9,640 + 15,481 rows), description text | One clear ADU in seven years; no license; Irving's ADU rule row is "none" (guest quarters by site plan) | Not worth an adapter |
| Houston | Summary XLSX only; record-level data only through the permit search or Open Records | No record-level open source | A records request (Ben does not file them) |
| Corpus Christi | Monthly PDF and XLSX reports, 2023-09 to 2026-09 | Not opened; 3 years | Check whether the XLSX lists permits |
| Amarillo, Grand Prairie, Killeen | Monthly or quarterly PDFs, or a yearly summary | PDFs | — |
| Lubbock, Garland, Frisco, McKinney, Laredo, Brownsville | Dashboard; no portal; active permits only; a 2023 snapshot; 2014–2018 layers; a 2023–26 snapshot | No ADU signal or no history | — |

Scouting notes: the source scout made small count and sample queries (at most about 20 rows each) against
these portals. One package-metadata request went to Denton's `/api/3/action/` path before robots.txt was read
(it disallows `/api/`); no further request went there.

## 5. Proposed rule rows (not in `config/reforms/tx.csv`)

- College Station (`TX-4815976-adu-2018`, single coder; `-adu-2023`, agreed in Ben's 2026-10-30 review) and
  Denton (`-adu-2023`, `-adu-2026`) are already coded. **Ben's acceptance of College Station's rows** is what
  D-074 step 2 needs before it enters the fit. The 2018 row is single-coder.
- **Proposed for a check, College Station before 2018:** the city issued "Living Quarters" accessory permits
  in March 2016, and ADU-like accessory living quarters appear in the UDO (§6.5.B.7). The 2018-11-29 row may
  be an amendment, not the first allowance. Proposed row, to be confirmed against the UDO history (City of
  College Station Code of Ordinances, Unified Development Ordinance Art. 6 §6.5.B.7, ordinance history
  notes):

  | reform_id | jurisdiction_geoid | theme | status | effective_date | by_right | owner_occ | adu_detached_allowed | adus_per_lot | coverage | source |
  |---|---|---|---|---|---|---|---|---|---|---|
  | TX-4815976-adu-2010 | 4815976 | adu | in_force | 2010-01-01 (in force at window start; to confirm) | True | True | True | 1 | Areas zoned and used for single-family residential use | UDO §6.5.B.7 history; evidence: 'Living Quarters' permits from 2016-03 (cstx_permits) |

  If the UDO history shows living quarters were allowed before 2010, the 2018 row is an amendment of an
  existing allowance, not a D-025 event.
- No row is proposed for Irving. Its "none" row (guest and servants' quarters by S-P-1 site plan) fits its
  permits (one ADU in seven years).

## 6. Not done here, and why

- Austin's HOME rule is not in the `austin_permits` adapter (§3). It needs the TCAD improvements inside a
  permit adapter, and processed tables feed the model; that is for WS-TX/WS-CORE.
- No engine, scenario, calibration or fit run. No HANDOFF or LOGBOOK edit (fragment in `logbook.d/`).
- The two-roll k needs an older TCAD export (§2.3); the Denton adapter needs Ben's download (§4.3).
