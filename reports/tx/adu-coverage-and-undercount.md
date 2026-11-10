# Texas ADUs: coverage, the flag undercount k, and more places (D-074 / D-075 steps for TX)

*WS-TX data thread (reopened for this task only), 2026-11-10. Descriptive counts only; no engine, scenario,
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

## 1. Coverage audit (D-075 step 1)

*(filled in after the counts)*

## 2. Flag undercount k in Austin

*(filled in after the counts)*

## 3. Austin ADUs by year under the HOME rule

*(filled in after the counts)*

## 4. More places

*(filled in after the counts)*

## 5. Proposed rule rows (not in `config/reforms/tx.csv`)

*(filled in after the counts)*
