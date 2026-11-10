# Minnesota ADUs: where the permit flags reach, and how much they undercount

*WS-MN data thread, 2026-11-10. Runs D-074's NC count steps (PR #358) for Minnesota so all five states are
comparable before one joint refit. Descriptive counts only: no engine, scenario, calibration or fit run. The St.
Paul holdout (V5, outcomes from 2024-01-01) is applied through `holdout.apply` on every permit and roll read.*

## 1. Coverage audit

*Counts from `uv run python scripts/dev/mn_adu_coverage.py` (aggregates in `reports/mn/adu-coverage.json`).*

**Method.** ADU-eligible lots are `eligible_parcels` (theme `adu`, rule version 1.1), each jurisdiction's
newest roll at or before 2024, summed over **non-overlapping units** with
`lotline.model.scenarios.adu.non_overlapping`, as the ADU scenario does (the raw sum, 1,699,352, counts
local-only places twice; the non-overlapping total is 1,688,996). A jurisdiction is **covered** when a permit
source that can mark a permit as an ADU holds record-level permits for it:
- **Met Council residential permits** (field): `HOUSING_TYPE = ADU`, every 7-county metro community, 2009–2025
  (ADU rows from 2014, 2016 on in practice);
- **Minneapolis CCS** (parser): the scope-of-work text, Minneapolis only, Dec 2016 on.

St. Paul's own permit file has no ADU flag; it is covered through Met Council, through 2023 only (V5).

**Bottom line.**
- **47% of Minnesota's eligible lots (799,300 of 1,688,996) sit in a covered jurisdiction** (184 of 1,051
  units). All of them are in the 7-county metro.
- Only **20% (345,983)** sit in one of the **53 places that have ever recorded an ADU permit**. Many covered
  suburbs report none: Met Council fills communities that skip its survey from Census BPS, which has no ADU
  type, so a zero there is "not reported", not "none built".
- **No county unincorporated area is covered** (297,234 lots, 18% of the state). Outstate, no city has
  record-level permits in the repo.
- Of the 25 largest units, 15 are covered. The 10 uncovered are **Rochester, Duluth and St. Cloud**, Moorhead,
  and six county remainders (St. Louis, Cass, Crow Wing, Itasca, Sherburne). §4 scouts them.

| By kind | Covered lots | Not covered | Share covered |
|---|---:|---:|---:|
| Places (cities) | 771,952 | 526,379 | 59% |
| Townships | 27,348 | 66,083 | 29% |
| County unincorporated remainders | 0 | 297,234 | 0% |
| **Minnesota** | **799,300** | **889,696** | **47%** |

**The 25 largest units by eligible lots.** "Parcels, scaled" is a parcel count from a roll year other than 2024,
scaled to 2024 by ACS (`parcels_scaled_acs`); "ACS" is the single-family ACS fallback. ADU permits are all
ADU-typed rows in the covered sources, all years (Minneapolis: 139 Met Council rows + 211 CCS rows; the two
overlap, so do not add them).

| # | Unit | Eligible lots | Lots from | Covered | Source with an ADU flag | ADU permits |
|---:|---|---:|---|---|---|---:|
| 1 | Minneapolis city | 75,128 | parcels | Yes | Met Council (field); Minneapolis CCS (parser) | 350 |
| 2 | St. Paul city | 58,019 | parcels, scaled | Yes | Met Council (field), through 2023 (V5) | 25 |
| 3 | Rochester city | 39,177 | parcels, scaled | **No** | — | — |
| 4 | Duluth city | 28,251 | parcels, scaled | **No** | — | — |
| 5 | Blaine city | 24,137 | parcels | Yes | Met Council (field) | 0 |
| 6 | Bloomington city | 21,295 | parcels | Yes | Met Council (field) | 3 |
| 7 | Coon Rapids city | 20,749 | parcels | Yes | Met Council (field) | 0 |
| 8 | Lakeville city | 19,575 | parcels | Yes | Met Council (field) | 0 |
| 9 | Plymouth city | 17,987 | parcels | Yes | Met Council (field) | 3 |
| 10 | St. Louis County unincorporated | 17,689 | parcels, scaled | **No** | — | — |
| 11 | Woodbury city | 17,477 | parcels | Yes | Met Council (field) | 0 |
| 12 | Brooklyn Park city | 17,445 | parcels | Yes | Met Council (field) | 0 |
| 13 | Cass County unincorporated | 17,369 | ACS | **No** | — | — |
| 14 | Maple Grove city | 17,268 | parcels | Yes | Met Council (field) | 0 |
| 15 | Crow Wing County unincorporated | 16,631 | ACS | **No** | — | — |
| 16 | St. Cloud city | 15,237 | parcels, scaled | **No** | — | — |
| 17 | Eagan city | 14,450 | parcels | Yes | Met Council (field) | 0 |
| 18 | Itasca County unincorporated | 13,925 | ACS | **No** | — | — |
| 19 | Eden Prairie city | 13,469 | parcels | Yes | Met Council (field) | 0 |
| 20 | Minnetonka city | 13,338 | parcels | Yes | Met Council (field) | 15 |
| 21 | Shakopee city | 13,218 | parcels | Yes | Met Council (field) | 0 |
| 22 | Sherburne County unincorporated | 12,985 | parcels, scaled | **No** | — | — |
| 23 | Edina city | 12,682 | parcels | Yes | Met Council (field) | 5 |
| 24 | Cottage Grove city | 12,043 | parcels | Yes | Met Council (field) | 0 |
| 25 | Moorhead city | 11,801 | parcels, scaled | **No** | — | — |

---

## 2. Flag undercount k in Minneapolis: detection rule (written and committed before any count)

### Why Minneapolis, and which rolls

D-074 step 1 needs a place with both a permit file that marks ADUs and two parcel rolls. In Minnesota only
Minneapolis has both:
- **Rolls.** The city assessor's tables (`mpls_assessor_parcels`, assessment years 2017–2026, each "as of January
  2") record **building use**, and the assessor has an ADU code: `R WITH ACCESSORY DWELLING` / `M WITH ACCESSORY
  DWELLING` (2017–2021 labels), `SF HOUSE W/ADU` and `DUPLEX W/ADU` (2022 on), and a separate building row
  `DETACHED ADU` (2025 on, when the tables list one row per building). Unlike Wake's roll, this code can mark
  **internal and attached** ADUs as well as detached ones. The Met Council rolls (`roll_2021`–`roll_2025`) carry
  no ADU code (none of their land-use labels names one), so they are not used.
- **Permits.** Minneapolis CCS (`processed/mn/permits/mpls_permits.parquet`). Its ADU type comes from the
  **scope-text parser** (`mpls_permits`), not a city field. So the k measured here is a **parser** undercount:
  under D-074 step 1 it is Minneapolis's k_parser, measured on the roll in place of a hand check (as D-074 allows
  for Cary). Met Council's Minneapolis ADU rows (a city-reported field) carry no PIN, so they cannot be matched
  by parcel; they are compared by year only (§3, check 3).

How the rule was written: Claude looked at the list of building-use labels in each roll year (no counts of
them, and no parcel was matched to any permit) and at the permit table's class codes. Nothing else.

**Main pair: the 2017 and 2026 rolls** (2017-01-02 → 2026-01-02, 9.0 years). **Sensitivity: 2017 and 2024**
(2024-01-02; the 2017–2024 tables have one row per parcel, so no building collapse is involved).

### Matching parcels across rolls

- **Key:** `parcel_id` = `27053` + the 13-digit Hennepin PIN (the adapter's key). Only parcels on both rolls are
  compared. Splits get new PINs, so new lots are never counted; merges are set aside by the area test below.
- **2025–2026 tables:** read raw, one row per building, so a `DETACHED ADU` building row is seen even when the
  processed table's collapse (building use of the building with the most units) hides it.

### Denominator: single-family parcels on the 2017 roll

A parcel is in the denominator when, on the 2017 roll, its `land_use_std` is `SF_DETACHED`, its building use is
**not** an ADU label (it had no ADU in January 2017), and `TOTAL_UNITS` = 1.

### R: parcels that gained an ADU

A denominator parcel is in R when, on the later roll (same parcel), **any** of its building rows has an ADU label
(`R WITH ACCESSORY DWELLING`, `M WITH ACCESSORY DWELLING`, `SF HOUSE W/ADU`, `DUPLEX W/ADU`, `DETACHED ADU`).
Each is then put in exactly one group:

| Group | Test | In R? |
|---|---|---|
| **ADU added** | ADU label; not a duplex label; main year built not moved to 2017 or later | **Yes (strict)** |
| Rebuild with an ADU | ADU label; year built moved from before 2017 to 2017 or later (house replaced) | Yes, shown apart |
| Duplex with an ADU | Later label `DUPLEX W/ADU` (the house also became a duplex) | Yes, shown apart |
| Possible merge | Lot area grew by more than 20% | **No** |
| Duplex, no ADU | No ADU label; units ≥ 2 or land use `DUPLEX` | No (missing middle), reported |

R (headline) = the three "Yes" groups; R (strict) = "ADU added" alone. "Year built" on the 2025–2026 tables is
the earliest building's, so an added detached ADU does not move it.

### P: ADU-typed permits

P = Minneapolis CCS permits with `building_type_std = ADU` (any status, as NC kept every flagged permit), issued
**2017-01-01 to 2025-06-30** (six months of completion lag before the 2026-01-02 roll; for the 2024 sensitivity,
to 2023-06-30), as a set of parcels. ADU-typed permits issued outside the window (Dec 2016, or after the lag
cut-off) are reported on their own line, not added to P.

### Groups (a) and (b), k and the checks (D-074 step 1)

Every parcel in R \ P falls in one group:
- **(a) permitted but unflagged:** it has a CCS permit issued in the window that is not ADU-typed and **builds new
  residential space**: `permit_class_raw` work type `New` with occupancy `SFD`, `TFD` or `TH`, or `units_new` ≥ 1
  (Wrecking permits never count).
- **(b) unpermitted or not found:** no such permit.

Reported:
- |P∩R|, |a|, |b|, |P \ R| (with P \ R split into parcels in the denominator and outside it);
- **k = (|P∩R| + |a|) / |P∩R|**, 90% interval from the Wilson interval on |P∩R| / (|P∩R| + |a|), inverted
  (`lotline.adapters.states.nc.wake_roll_diff.k_undercount`);
- the **Chapman total** (|R| + 1)(|P| + 1) / (|P∩R| + 1) − 1 with P limited to denominator parcels, a lower
  bound (permitted ADUs are more likely to be coded on the roll).

Versions, all fixed now:
- **As written:** R headline; (a) as above.
- **Duplexes removed (central, NC's deviation):** the "duplex with an ADU" group leaves R, and a permit with
  occupancy `TFD` or `units_new` ≥ 2 (a two- or three-family rebuild or conversion) no longer qualifies for (a).
- **Wide (sensitivity, NC's §2.4 note 2):** (a) also takes non-ADU permits with work type `Accessory`,
  `Conversion` or `UnitCon`, and `Res:Accessory:New` (a new accessory building), the classes ADUs are often filed
  under.
- **Strict R:** k on the "ADU added" group alone.
- **2017 → 2024 rolls:** central version on the shorter pair.

### Checks reported beside k, not used

1. Of the R \ P parcels, how many have a non-ADU-typed CCS permit whose class is one of the ADU work types the
   parser looks at (`ADU_WORK`), i.e. the parser saw the permit but its text did not name an ADU.
2. P \ R by status: cancelled, expired or withdrawn permits are expected not to show on the roll.
3. Met Council's Minneapolis ADU rows by year beside the CCS ADU-typed permits by year, and the roll's first
   ADU appearance by roll year (consecutive rolls), as a count check of the field flag against the parser.
