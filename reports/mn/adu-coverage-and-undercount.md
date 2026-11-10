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

---

## 3. Flag undercount k in Minneapolis: results

*Rule committed in 9e4b5390 before the first count. Counts from `uv run python
scripts/dev/mn_mpls_roll_adu_diff.py` (aggregates in `reports/mn/mpls-roll-adu-diff.json`; no parcel-level table
is written). Functions and tests: `src/lotline/adapters/states/mn/mpls_roll_diff.py`,
`tests/states/mn/test_mpls_roll_diff.py` (k and Chapman are NC's functions, imported).*

### Bottom line

- **k = 1.04 (90%: 1.02–1.10)** with duplexes removed (|P∩R| 94, |a| 4). **As written: 1.06 (1.03–1.12)**
  (|a| 6). The lower bound is above 1 in every version, so D-074 step 4's trigger holds for Minneapolis too.
- Minneapolis's ADU type comes from our scope-text parser, so this is Minneapolis's **k_parser**, measured on the
  roll (as D-074 allows for Cary). It is close to Raleigh's field-flag k (1.07, 1.02–1.21).
- **79% of the ADUs the assessor coded on 2017 single-family lots carry an ADU-typed permit** (94 of 119; 95%
  Wilson 71–85%), against Raleigh's 73%. That is **1.27 real ADUs per typed one**, the analogue of Raleigh's
  1.38. The Chapman total gives the same ratio, **1.27 × the typed permits** (95%: 1.20–1.33).
- **Met Council's field undercounts Minneapolis much more than the parser does.** Over 2017–2025, Met Council's
  Minneapolis ADU rows add up to 110 units; the parser types ADUs on 191 parcels (1.7×). Met Council's field is
  the only ADU source for the other 183 covered metro jurisdictions (§3.3).

### 3.1 Groups on the main pair (2017 → 2026 rolls)

75,264 single-family parcels on the 2017 roll; 173 are gone by 2026 (split, merged or retired), so 75,091 are
compared.

| Group | Parcels | In R |
|---|---:|---|
| ADU added (strict) | 111 | Yes |
| Rebuild with an ADU | 8 | Yes |
| Duplex with an ADU | 3 | Yes as written; removed in the central version |
| Possible merge | 1 | No |
| Duplex, no ADU | 183 | No (missing middle) |
| No ADU | 74,785 | No |

R is 122 as written and 119 with duplexes removed: **0.18 ADUs per 1,000 single-family lots a year** over 9.0
years. Raleigh's roll gave 0.13 for a narrower signal (detached only).

### 3.2 D-074 quantities

P = Minneapolis CCS permits typed ADU, issued 2017-01-01 to 2025-06-30: 175 parcels, 137 of them on 2017
single-family parcels (the only ones R can contain).

| | As written | **Duplexes removed (central)** | Wide (a) | Strict R | 2017 → 2024 rolls (central) |
|---|---:|---:|---:|---:|---:|
| \|R\| | 122 | **119** | 119 | 111 | 41 |
| \|P\| (parcels) | 175 | **175** | 175 | 175 | 145 |
| …on a 2017 single-family parcel | 137 | **137** | 137 | 137 | 111 |
| **\|P ∩ R\|** | 95 | **94** | 94 | 89 | 28 |
| **\|a\| permitted but unflagged** | 6 | **4** | 9 | 2 | 2 |
| **\|b\| unpermitted or not found** | 21 | **21** | 16 | 20 | 11 |
| **\|P \ R\|** | 80 | **81** | 81 | 86 | 117 |
| …on a 2017 single-family parcel | 42 | **43** | 43 | 48 | 83 |
| …outside the denominator | 38 | **38** | 38 | 38 | 34 |
| **k** (90%) | 1.06 (1.03–1.12) | **1.04 (1.02–1.10)** | 1.10 (1.05–1.17) | 1.02 (1.01–1.07) | 1.07 (1.02–1.22) |
| Chapman total (95%) | 175.8 (167–185) | **173.3 (164–182)** | 173.3 | 170.7 (162–180) | 161.2 (133–189) |
| Chapman ÷ P on single-family parcels | 1.28 | **1.27** | 1.27 | 1.25 | 1.45 |

Checks (§2, reported, not used):
1. **Parser seen, text silent.** 19 of the 25 R \ P parcels (central) have a non-ADU permit whose work type the
   parser reads (remodel, addition, accessory, conversion). That is weak evidence, since nearly every house has
   such a permit in nine years; it says the parser could at most have caught these from the text.
2. **P \ R by status.** 165 of the 175 P parcels have a live permit (not cancelled, expired, void, withdrawn or
   denied); 74 of the live ones are not in R. So most of P \ R is not dead permits: the ADU is unfinished,
   coded by the assessor on a parcel outside the denominator, or not coded at all.
3. **Outside the window.** 24 P-type parcels have their ADU-typed permit issued outside the window (Dec 2016, or
   after 2025-06-30); 1 of them is in R \ P. They are not added (rule §2).

### 3.3 Field flag against parser, by year (count check)

| Year | Roll: first ADU label (2017 SF parcels) | CCS ADU-typed parcels | Met Council ADU units (Minneapolis) |
|---|---:|---:|---:|
| 2017 | — | 30 | 22 |
| 2018 | 13 | 25 | 9 |
| 2019 | 12 | 34 | 18 |
| 2020 | 28 | 27 | 10 |
| 2021 | 20 | 16 | 7 |
| 2022 | 8 | 17 | 12 |
| 2023 | 5 | 13 | 8 |
| 2024 | 5 | 16 | 11 |
| 2025 | 36 | 13 | 13 |
| 2026 | 9 | 14 (partial) | — |
| **2017–2025** | | **191** | **110** |

The roll column is the January table in which a parcel first carries an ADU label. It is not an issue year.
- **Met Council records about 58% of the parser's Minneapolis ADUs.** Met Council's rows come from the city's
  annual survey response. They carry no PIN, so they cannot be matched by parcel and no k can be measured for
  them here. LB-057 had already noted that Met Council misses Minneapolis's internal ADUs.
- **What this means for the suburbs.** D-074 applies k "as measured" to field-flagged sources. In Minnesota the
  field source is Met Council, and in its one checkable city it records 1.7× fewer ADUs than the parser.
  Applying k = 1.04 to the Met Council suburbs would assume their reporting is as complete as Minneapolis's CCS
  text, which this check says it is not.
- **Decided (Ben, 2026-11-10): the Met Council suburbs are a floor.** k = 1.04 applies to Minneapolis's parsed
  CCS permits. Met-Council-only places keep their counts as reported, described as a lower bound on their ADUs.
  The 1.74 ratio is recorded here as the reason, not applied as a factor. That is a proposed HANDOFF decision;
  no config is changed in this PR.

### 3.4 Caveats

1. **The roll's ADU label is not stable from year to year.** About 65 parcels labelled ADU in 2021 lose the
   label in the 2022–2024 tables (back to `SINGLE FAMILY HOUSE`) and get it back in 2025, when the city moved to
   one row per building. This was found after the count, while reading the by-year column. The main pair ends
   on 2026, after the labels came back, so it is not affected. The 2017 → 2024 sensitivity is: its R (41) is far
   too low, and its P \ R (117) far too high. Its k (1.07) is still close, because the dropped labels thin out
   P∩R and (a) alike.
2. **Carriage houses are not counted.** The 2026 table lists 32 `CARRIAGE HOUSE` buildings on 2017
   single-family parcels without an ADU label. 29 were built before 1960 and 2 in 2017 or later. Most are old
   outbuildings that show up once the tables list each building, not new ADUs. The rule does not count them, as written.
3. **Lower bound.** Same as NC: a permitted ADU is more likely to be coded, so the Chapman total is a floor.
4. **Group (b) is reported, not added** (D-074): 21 roll ADUs with no new-residential permit. Some were
   permitted under a remodel or conversion whose text did not say "ADU" (check 1). The wide version counts
   those classes and gives k = 1.10.
5. **One city, a parser source.** k is Minneapolis's k_parser. Whether it transfers to Met Council's field is
   doubtful (§3.3).

---

## 4. More places: outstate permit sources (scouted 2026-11-10; Rochester adapter built)

The brief asked for adapters for the 3 largest uncovered places with an **openly licensed, record-level** permit
source. **None of the uncovered places has an openly licensed one that can mark an ADU.** The scouting checked
the publisher's metadata, record counts and robots.txt, plus count-only text queries, and read at most a
handful of sample rows. Rochester is the exception that was built (§4.1): Ben accepted its public-records
spreadsheets on 2026-11-10 (no license is stated, as for Greensboro and Portland).

| Place (eligible lots) | What exists | Record-level? | ADU marking | License / access | Verdict |
|---|---|---|---|---|---|
| **Rochester** (39,177) | Monthly "Detail Report Spreadsheet" files (.xls 2011–, .xlsx to 2026-10) in the city's public Laserfiche archive (`lf.rochestermn.gov`, linked from rochestermn.gov's building permit reports archive) | Yes (per permit: number, type, construction code 101/102/997, work description, valuation) | None; the description could be parsed | **No license stated**; robots.txt allows; one file per month (252 sheets, 113 of them .xlsx) | **Adapter built** (§4.1) |
| **Duluth** (28,251) | ePlace per-address lookup (account needed for detail) | No open extract | — | Login | None |
| **St. Cloud** (15,237) | ArcGIS server `sws.stcloudcity.com` (Accela/TRAKiT folders) | Unknown | — | **robots.txt disallows all paths**: not queried | Blocked; the city takes data requests |
| **Moorhead** (11,801) | Assessor CAMA permit table, `gis.moorheadmn.gov/.../Assessor_Permit_Review/MapServer/1`, 95,293 rows (repeated per parcel), 2019-07 to 2026-11 | Yes (date, number, reason, scope comment, parcel) | None. **The text names no ADU**: the 6 "ADU" hits are "Adult Day Care", the one "carriage" hit is a deck's carriage bolts | Disclaimer only ("reference purposes only, as-is") | Not useful for ADUs (0 found) |
| **Olmsted County** (unincorporated and contract towns) | Accela layer `services7.arcgis.com/tC18nF87RnYBtzwI/.../Olmsted_County_Permits_Planner_Map_View/FeatureServer/0`, 19,430 records, 1964–2026 | Yes (record type, subtype, opened date, 12-digit PIN) | None (no type or subtype names an ADU or accessory dwelling); no scope text, no issue date, no units | Disclaimer only | Not useful for ADUs |
| Mankato (Blue Earth Co.) | Nothing found | — | — | — | None |
| St. Louis County unincorporated (17,689) | `gis.stlouiscountymn.gov` land-use service | — | — | Token required | None |
| Crow Wing County unincorporated (16,631) | County CRM permit field layer (land use, septic, shoreland), 2022–2026 | Yes | None; no scope text | No license; exposes owner names and edit operations: an internal layer, not open data | Not used |
| Sherburne County unincorporated (12,985) | County GIS permit services | — | — | **robots.txt disallows all paths** (names ClaudeBot) | Blocked |
| Cass, Itasca counties | Department pages and PDF forms only | — | — | — | None |

### 4.1 Rochester (`rochester_permits`)

**Source and adapter.** `src/lotline/adapters/states/mn/rochester_permits.py`, tests in
`tests/states/mn/test_rochester_permits.py` (18, synthetic sheets and grids), provenance row in
`docs/data_provenance.md`, source entry in `config/states/mn.yaml`.
- The archive's folder-listing service (the JSON POST the web viewer uses) lists 252 monthly "Detail Report
  Spreadsheet" files, 2005-09 to 2026-10. All 252 were downloaded through `lotline.io.http.fetch` (61.6 MB,
  each in the manifest).
- **Formats.** The 139 sheets to 2017-03 are `.xls` (Excel 97), read with `xlrd` (BSD-3-Clause; Ben approved the
  dependency on 2026-11-10). The 113 later sheets are `.xlsx`.
  - 2007-11 to 2026-10 share one layout with labels that change from month to month, so each column is matched
    by pattern, and the personal labels (address, contractor, owner) can never match.
  - 2005-09 to 2007-10 (26 sheets) are an extract from the city's old permit system (`read_legacy`), read by
    field position: type code (`R101` …, a Census code), permit class, issue date, units and a type
    description. There is no parcel and no free-text description, so these months add new homes but no ADU
    signal. Rochester's first coded ADU rule is the 2023 UDC (`MN-2754880-adu-2023`).
  - The 2014-11 sheet leaves every issue date blank. Its 127 building permits take the report month
    (`date_precision = month`).
- Built with `lotline fetch --state MN --source rochester_permits`: 51,040 permit rows.
- One parcel number per permit from 2007-11 on, but it is the city's 6-digit number, not the Olmsted County PIN.
  So there is no roll match, and **no k is measured here**.

**New homes vs Census BPS (sanity check).** From 2006 on, new SFD and townhouse permits are within about 10% of
BPS single-family units in most years. The exceptions are 2007 (383 vs 420) and 2023 (207 vs 241). Apartments' units are reported only in the
2005–2007 extract (code 105).

**ADU permits per 1,000 eligible lots** (39,177 eligible lots, 2024):

| Issue year | Building permits | New SFD/TH | BPS 1-unit | ADU permits | Per 1,000 lots |
|---|---:|---:|---:|---:|---:|
| 2005 (Sep–Dec) | 1,023 | 237 | 702 | 0 | 0.00 |
| 2006 | 2,936 | 512 | 507 | 0 | 0.00 |
| 2007 | 2,633 | 383 | 420 | 0 | 0.00 |
| 2008 | 2,397 | 284 | 287 | 0 | 0.00 |
| 2009 | 1,944 | 270 | 265 | 0 | 0.00 |
| 2010 | 1,983 | 200 | 200 | 0 | 0.00 |
| 2011 | 1,822 | 204 | 195 | 0 | 0.00 |
| 2012 | 2,028 | 310 | 299 | 0 | 0.00 |
| 2013 | 2,107 | 340 | 323 | 0 | 0.00 |
| 2014 | 2,199 | 365 | 352 | 0 | 0.00 |
| 2015 | 2,260 | 373 | 359 | 0 | 0.00 |
| 2016 | 2,339 | 423 | 403 | 0 | 0.00 |
| 2017 | 2,875 | 473 | 437 | 0 | 0.00 |
| 2018 | 2,419 | 371 | 347 | 0 | 0.00 |
| 2019 | 2,447 | 310 | 296 | 0 | 0.00 |
| 2020 | 2,029 | 279 | 296 | 0 | 0.00 |
| 2021 | 2,325 | 257 | 251 | 0 | 0.00 |
| 2022 | 2,044 | 218 | 234 | 0 | 0.00 |
| 2023 | 2,026 | 207 | 241 | 3 | 0.08 |
| 2024 | 2,317 | 194 | 193 | 2 | 0.05 |
| 2025 | 3,735 | 241 | 240 | 0 | 0.00 |
| 2026 (Jan–Oct) | 3,152 | 221 | — | 0 | 0.00 |

- **Five ADU permits in 21 years of sheets, all after the 2023 UDC** (`MN-2754880-adu-2023`, effective
  2023-01-01). That is 0.04 per 1,000 lots a year for 2023–2025, close to Greensboro (0.03) and far below
  Minneapolis.
- Two of the five are new houses built with an attached ADU. Rochester files these as **two-family** permits
  (code 103, "Two-family dwelling (SFD with attached ADU)"), and BPS counts them as two-unit buildings. The
  adapter writes each as a house row and an ADU row, so the city's two units are still counted once each.
- The 2025–2026 jump in building permits comes from reroof, window and residing permits, which first appear
  as building permits in 2025. They are not new homes.

**Hand check of the ADU rule.** Rochester's descriptions name an ADU too rarely for a draw of 30 matches, so
every match was read. Descriptions were read in memory from the registered files; none is stored in the repo.
- **The `.xls` years (2007-11 to 2017-03) add no ADU.** The same broad pattern finds 10 hits there, all non-ADUs:
  hotels ("Guest House Inn & Suites", "Millies Guest House") and trade work on a carriage house. The hand check
  below was done on the 2017-04 on sheets, before the `.xls` sheets were added.
- **Every text hit (13).** The pattern was broad: ADU, accessory dwelling, in-law, carriage house, guest house,
  across all permit types.
  - **Flagged and correct, 5 of 5:** an attached-ADU addition, a one-bedroom ADU with a garage, an ADU in a
    detached garage's upper level, and two new houses with an attached ADU. Precision 5/5 (90% Wilson
    0.65–1.00).
  - **Correctly not flagged, 8:**
    - a garage with a "future ADU" (finished later as a flagged ADU on the same parcel);
    - a basement "mother-in-law suite [non-rental]" (ambiguous; left out by rule);
    - commercial boilers for a "Carriage House";
    - a hospital "Guest House";
    - four electrical and HVAC trade permits for new ADUs. Every one sits on a parcel whose building permit is
      flagged, which is direct evidence that the rule catches the ADUs the city files.
- **Non-matches, two draws of 30 (seed 20261110) from residential building permits not flagged:**
  - **Draw 1, from a pool of 1,021 descriptions with an ADU-like word including "kitchen":** 30/30 are not
    ADUs, almost all kitchen remodels. As in Charlotte, "kitchen" alone finds nothing, so it was dropped from
    the pool.
  - **Draw 2, from a pool of 214** (living quarter, apartment, suite, kitchenette, second unit, dwelling unit,
    studio, in-law, guest, carriage, cottage, above/over garage, rental unit, two-family, duplex): **no clear
    miss** (0/30; 90% upper bound 8%, about 18 of 214).
    - 4 are ambiguous basement finishes with a kitchenette, one with a "non-rental duplex" agreement. The agreement
      suggests the owner promised not to rent the space, so these are probably not ADUs.
    - The rest are suites, guest baths, duplex repairs, a 55-unit apartment building, and egress windows in
      existing rental units.
  - A full pass over every code-103 or "two-family" permit found 1 more ambiguous case: a 2022 "Two family
    home, 1 unit above 3 car garage ... (duplex)", filed before the UDC allowed ADUs, so read as a duplex.
- **Recall** = true flagged ADUs / (true flagged + missed):

| Case | TP | FN | Recall |
|---|---:|---:|---:|
| Central: no clear miss found | 5 | 0 | 1.00 |
| 90% upper bound on clear misses in pool 2 (0/30 → 8% of 214 ≈ 18) | 5 | 18 | 0.22 |
| The 5 ambiguous cases are all ADUs (4 kitchenette basements, the 2022 two-family) | 5 | 5 | 0.50 |

  With TP this small, the worst cases mostly show how little five ADUs can tell us. For D-074's pooled
  k_parser, Rochester adds **5 matches and 0 clear misses**. It should be pooled with the other parser
  sessions' counts, not given a ratio of its own.

**What enters D-074 step 2.** Rochester has a record-level source with far more than 1,000 permits, an ADU rule
row and eligible lots, so it qualifies. Its 2017–2022 zeros are pre-UDC years, and it gives the fit a
"rule change, few takers" case.

**Still not usable.** St. Cloud and Duluth could be added only through a records request, which Ben has ruled
out, so they close as no usable source. Moorhead and Olmsted have no ADU signal.

## 5. Rule rows

**No new ADU rule rows are proposed.** Rochester, the one new place, already has `MN-2754880-adu-2023` (UDC
§60.300.020G.5, adopted 2022-09-07, effective 2023-01-01, by right, owner-occupied, up to 1,000 sq ft). Its
counts fit that row: the first ADU permit is 2023-04-14. Duluth (`MN-2717000-adu-2010`) and St. Cloud
(`MN-2756896-adu-2024`) have rows but no permit source. Moorhead has no ADU row. None is proposed, since its
permits show no ADUs to fit.

## 6. What this means for the joint refit

- **Coverage rises from 47% to 50%** with Rochester (838,477 of 1,688,996 lots). The rest, outstate cities
  other than Rochester plus townships and county remainders, has no ADU outcome. In a leave-one-state-out
  test, that share is the "no permit data" tier.
- **k for Minnesota.** Minneapolis's parser k is 1.04 (1.02–1.10), close to Raleigh's 1.07. The Met Council
  field, which carries every other covered place, records about 58% as many Minneapolis ADUs as the parser does
  (§3.3). That gap is larger than k. Ben's call (2026-11-10): the suburbs are reported as a floor, not scaled.
