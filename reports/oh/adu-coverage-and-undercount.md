# Ohio ADUs: coverage of the flagged permits, the flag undercount (Columbus), and new places

*OH data thread, 2026-11-10. Ohio's run of the North Carolina steps in D-074 (PR #358). Descriptive counts
only: no engine, scenario, calibration or fit run. Ohio has no holdouts (`config/states/oh.yaml`).*

## 1. Coverage: how much of Ohio's eligible land has ADU-flagged permits

Script: `uv run python scripts/dev/oh_adu_coverage.py`. Lots are theme `adu` in `processed/oh/eligible_parcels`
(current rule version), the newest year at or before 2024 for each jurisdiction, made non-overlapping with
`lotline.model.scenarios.adu.non_overlapping`, as the ADU scenario does. A jurisdiction is **covered** when an
ADU-flagged permit source reaches it:

- **Columbus** (`columbus_permits`, flags from the Franklin Auditor's permit descriptions) and **Cincinnati**
  (`cincy_permits`);
- the **Franklin County part** of every other jurisdiction (`franklin_permits`). A place that reaches beyond
  Franklin (Dublin, Westerville, Reynoldsburg …) counts by the share of its single-family parcels inside
  Franklin;
- the 12 **Montgomery** jurisdictions that `montgomery_permits.covered_places` lists.

**Ohio has 3,416,591 eligible ADU lots. 526,745 (15.4%) are covered**:

| Source | Covered lots |
|---|---:|
| `columbus_permits` | 173,843 |
| `montgomery_permits` (12 places, incl. Dayton and the unincorporated county) | 166,620 |
| `franklin_permits` (Franklin suburbs and unincorporated Franklin) | 129,301 |
| `cincy_permits` | 56,981 |

By kind:
- Places hold 1,894,149 lots, and 22% of them are covered.
- County remainders hold 1,318,781 lots, and 8% are covered (Franklin and Montgomery only).
- Townships hold 203,661 lots, and none are covered.

That is above NC's 9% before D-074. Most of it is two counties, though, and in those counties the flags come
from description parsers, so every count is a lower bound.

### The 25 largest jurisdictions by eligible lots

| # | Jurisdiction | Kind | Eligible lots | Covered | Source |
|---:|---|---|---:|---|---|
| 1 | Columbus | place | 173,843 | yes | columbus_permits |
| 2 | Hamilton County remainder | county | 95,725 | no | — |
| 3 | Toledo | place | 81,585 | no | — |
| 4 | Cleveland | place | 80,693 | **new (§3)** | cle_permits |
| 5 | Stark County remainder | county | 69,775 | no | — |
| 6 | Montgomery County remainder | county | 64,928 | yes | montgomery_permits |
| 7 | Akron | place | 59,904 | no | — |
| 8 | Cincinnati | place | 56,981 | yes | cincy_permits |
| 9 | Butler County remainder | county | 54,749 | no | — |
| 10 | Clermont County remainder | county | 54,511 | no | — |
| 11 | Mahoning County remainder | county | 50,611 | no | — |
| 12 | Summit County remainder | county | 48,360 | no | — |
| 13 | Dayton | place | 43,447 | yes | montgomery_permits |
| 14 | Wood County remainder | county | 42,562 | no | — |
| 15 | Warren County remainder | county | 42,162 | no | — |
| 16 | Trumbull County part | county | 41,447 | no | — |
| 17 | Delaware County remainder | county | 40,162 | no | — |
| 18 | Lucas County remainder | county | 38,257 | no | — |
| 19 | Miami County remainder | county | 36,748 | no | — |
| 20 | Franklin County remainder | county | 35,802 | yes | franklin_permits |
| 21 | Medina County remainder | county | 33,489 | no | — |
| 22 | Licking County part | county | 32,259 | no | — |
| 23 | Greene County remainder | county | 30,087 | no | — |
| 24 | Geauga County remainder | county | 27,725 | no | — |
| 25 | Lake County remainder | county | 27,553 | no | — |

The next largest places, none of them covered:

| Place | Eligible lots |
|---|---:|
| Parma | 27,537 |
| Youngstown | 21,992 |
| Canton | 21,780 |
| Lorain | 20,213 |
| Hamilton | 18,606 |
| Springfield | 16,476 |
| Mentor | 16,311 |
| Strongsville | 15,698 |
| Elyria | 15,559 |
| Cuyahoga Falls | 15,302 |
| Middletown | 15,149 |
| Euclid | 15,052 |

Kettering (18,621) is covered.

Places that are only partly covered, by their Franklin share:

| Place | Franklin share |
|---|---:|
| Dublin | 78% |
| Westerville | 79% |
| Reynoldsburg | 72% |
| Pickerington | 10% |
| New Albany | ~100% |
| Canal Winchester | 94% |
| Lithopolis | 2% |

---

## 2. Flag undercount k in Columbus (D-074 step 1)

### 2.1 Detection rule (written and committed before any count)

**What was looked at before writing it.**
- The column layouts of the Franklin County Auditor's appraisal files: `Dwelling.xlsx`, `Improvement.xlsx`
  and `Parcel.xlsx`.
- The improvement code list in the Dec 2016 file, and how often the codes CBN, UFR, DBS, RM1, MIS, OTH, O99
  and RG1–RG4 appear in the 2016 and 2019 files.
- **The 12 Columbus ADU-flagged permits issued 2017-01-01 to 2019-06-30**, on the Dec 2016 and Dec 2019 rolls.
  This is the learn-on cohort. What they showed:
  - **1 of 12** gained a second dwelling card. It was a new house and an ADU built together on a lot that was
    vacant in 2016.
  - **4 of 12** show the ADU only as a detached-garage improvement (code RG1): either a new one with year
    built 2017–2018, or one whose area grew. This is how the Auditor cards a carriage house: as a garage, not
    as a dwelling.
  - **2** were already two- or three-family buildings.
  - **5** show no change.
  - Across the county, the detached-garage codes are being recoded: RG2 went from 240 rows in 2016 to 8,980 in
    2019. So the garage code itself means nothing.
- **Not looked at before this rule was committed:** any permit issued 2020 or later, and the 2024 roll.

**What the roll can and cannot see.** The Auditor's `Dwelling.xlsx` has one row per dwelling card: `CARD`,
`LIVUNITS` (units), `STYLE`, `YRBLT` and `SFLA` (living area). Outbuildings sit in `Improvement.xlsx` under
codes that have no living-area or dwelling code; there is no "garage apartment" or "guest house" code. So the
roll shows a second home only as:

1. **a new dwelling card**: the parcel has 2 or more `Dwelling.xlsx` rows with living area above 0; or
2. **a unit or use change**: `LIVUNITS` summed over dwelling cards goes from 1 to 2 or more, or `LUC` goes from
   510 (single family) to 520 (two family), and card 1's year built is unchanged.

A carriage house over a garage, carded as a garage, is **invisible as a dwelling**. A new detached garage
(an RG1–RG4 line with year built 2020–2024 that wasn't on the 2019 roll) and added living area (`SFLA` up by
200 sq ft or more on card 1) are reported only as an **outer envelope**, never counted as ADUs, just as NC's
signal 3 is.

**Rolls and matching.**
- The earlier roll is the last appraisal snapshot of 2019 (**2019-12-18**); the later one is the last of 2024
  (**2024-12-30**). That is 5.03 years.
- The key is the Auditor's parcel number (`PARCEL ID`, `010-012345-00`). Split lots get new numbers, so new
  lots are never counted. Only numbers present in both rolls are compared.
- A parcel whose `ACRES` grew by more than 20% is a **possible merge** and is set aside.

**Denominator.** A parcel counts when, on the 2019 roll:
- its `LUC` maps to `SF_DETACHED` in `config/crosswalks/oh_dte_luc.csv` (510);
- it has exactly one dwelling card; and
- that card has `LIVUNITS` 1.

The jurisdiction is the parcel's in the processed `parcels` table (2023 roll), else its taxing district's
where 95% of the district lies in one jurisdiction (as `scripts/dev/oh_franklin_history.py` does).

**Groups** (one per gaining parcel), as in NC with the year moved to the later roll:

| Group | Test | Counted |
|---|---|---|
| New card, built 2020+ | Signal 1, newest added card's `YRBLT` 2020–2024 | Yes (strict count) |
| New card, older building | Signal 1, added card built before 2020 | Yes, shown apart |
| Unit or use change | Signal 2 only | Yes, shown apart |
| Teardown and rebuild with two homes | Card 1's `YRBLT` moved to 2020+ | Yes, shown apart |
| Possible merge | Acreage up by more than 20% | No |

**R** = Columbus denominator parcels in any counted group.

**P** = Columbus ADU-flagged permits (`columbus_permits` rows with `adu_type` set) issued **2020-01-01 to
2024-06-30**, matched to roll parcels by their 9-digit parcel number.

**Group (a), permitted but unflagged**: R \ P parcels that have a non-flagged Columbus new-structure dwelling
permit (`permit_class_raw` "101|", "102|", "103|" or "106|" with "1,2,3 Family - New Structure") issued in the
same window.
- **As written**: every such permit counts.
- **ADU-only** (NC's deviation, adopted beforehand here): duplex permits (103) are left out of (a), because a
  two-unit permit is a duplex.
- **Sensitivity**: a "434|1,2,3 Family - New Structure" permit (a new accessory building, the class Columbus
  files many garages and carriage houses under) also counts as (a).

**Group (b)**: the other R \ P parcels.

**Reported:** |P∩R|, |a|, |b|, |P\R|, and k = (|P∩R| + |a|) / |P∩R| with a 90% Wilson interval
(`nc.wake_roll_diff.k_undercount`). The Chapman total (|R|+1)(|P|+1)/(|P∩R|+1) − 1 is the lower-bound check,
with P restricted to denominator parcels.

**Columbus's flags are a parser.** Unlike Raleigh's field flag, they come from the Auditor's permit
descriptions (`franklin_permits.adu_flags`). In D-074's terms they are a parser source, so this k is a
parser-recall check, not a field-flag k.

**Expected, before counting.** The learn-on cohort shows that the roll sees about 1 Columbus ADU in 12. So R
will be small, P∩R near zero, and k probably can't be estimated. If |P∩R| is 0, k is undefined, and that is
reported as the result.

**Montgomery (second test).** Montgomery's CAMA files do carry dwelling cards (`DWELL.DAT`, with registered
extracts for 2011, 2012, 2014, 2018, 2021, 2022, 2024, 2025 and 2026). But Montgomery has **7 ADU-flagged
permits in all** (2020–2026), so |P∩R| can't be more than a handful. The test is not run here; §2.3 says why.

### 2.2 Results

*The rule was committed in c38920b before the first count. Counts come from `uv run python
scripts/dev/oh_franklin_roll_adu_diff.py`; the aggregates are in `reports/oh/franklin-roll-adu-diff.json`,
and no parcel-level table is written. Functions and tests: `src/lotline/adapters/states/oh/franklin_roll_diff.py`
and `tests/states/oh/test_franklin_roll_diff.py`.*

**Bottom line: the Franklin roll can't measure k.**
- **The Auditor cards almost no ADU as a dwelling.** Of 13 Columbus flagged permits on 2019 single-family
  parcels, **1** shows a second home on the 2024 roll. **7** show only a new detached garage, and 6 show
  living area added to the house.
- **So |P∩R| = 1, and k = 2.0 (90%: 1.14–8.27) means nothing.** It doesn't change between the as-written,
  ADU-only and accessory-structure (434) versions: the one group-(a) parcel has a single-family (101) permit.
  The Chapman total, **377 (95%: 65–766)**, is just as uninformative.
- **D-074's k stays Raleigh's (1.07, 1.02–1.21).** Ohio adds no evidence for or against it. Columbus's flags
  are a parser source, so they would take k_parser from a hand check (§3.3), not from k.

**Franklin County, Dec 2019 → Dec 2024 (5.03 years)**
- Single-family parcels in the 2019 roll: **287,374**. Another 608 are gone by 2024 and not compared.
- **Gained a second home: 70**, or **0.048 per 1,000 lots a year** (95%: 0.038–0.061). Of these:
  - 6 new cards built 2020–24 (the strict count);
  - 21 new cards for older buildings;
  - 42 unit or use changes;
  - 1 teardown rebuilt with two homes.
  - No possible merges were counted.
- **Columbus: 53 of 166,038 gained.** By group: 2 strict, 11 older-building cards, 39 unit or use changes and
  1 rebuild.
- **Unincorporated Franklin: 11 of 32,909.** The 15 suburbs together have 6.
- **Envelope, not counted:**
  - 1,076 parcels gained a detached garage built 2020–24 (703 of them in Columbus);
  - 3,485 parcels added 200 sq ft or more of living area to the house.
  - Most are just garages and additions.

**Columbus undercount table** (P = flagged permits issued 2020-01-01 to 2024-06-30: 23 parcels; by issue
year 5, 8, 5, 2, 3)

| | As written | ADU-only (no 103) | With 434 |
|---|---:|---:|---:|
| \|R\| | 53 | 53 | 53 |
| \|P\| (parcels) | 23 | 23 | 23 |
| …on a 2019 single-family parcel | 13 | 13 | 13 |
| **\|P ∩ R\|** | **1** | **1** | **1** |
| **\|a\| permitted but unflagged** | **1** | **1** | **1** |
| **\|b\| unpermitted or not found** | **51** | **51** | **51** |
| **\|P \ R\|** | **22** (12 on single-family parcels) | 22 | 22 |
| **k** (90% Wilson) | **2.0 (1.14–8.27)**, not usable | same | same |
| Chapman total (95%) | 377 (65–766) | same | same |

**Why group (b) is large and means little.** 39 of Columbus's 53 roll gains are unit or use changes (LUC 510
→ 520, or `LIVUNITS` 2). In this city those are mostly duplex conversions and recodes, not ADUs. The roll's
own signal can't tell them apart, and Columbus's layer has no alteration permits to check them against.

**A better Ohio undercount signal.** Columbus's Council use variances for ADUs number **90** for 2020–2024
(`columbus_variances`), against **23** flagged permits in the same years. So the parser finds about **1 in 4**
approved ADUs, the same ratio `docs/build/oh-franklin-history-check.md` cites. Approvals are an upper bound,
since not every approved ADU is built. The panel already keeps the larger of the two counts each year. This
ratio (about 3.9) is the closest Ohio comes to a k for a parser source. It isn't a D-074 k, so it is reported
here only as a check.

### 2.3 Montgomery (second test): not run

Montgomery's CAMA extracts carry dwelling cards (`DWELL.DAT`), with registered files for Nov 2018 and Nov
2024, so the roll comparison could be built. It wasn't, for three reasons:
- **There are too few flags.** `montgomery_permits` flags **7** ADUs in all (2020–2026), so |P∩R| can't be
  more than a handful.
- **The rolls likely card ADUs the same way.** Franklin's Auditor cards carriage houses as garages, and
  Montgomery runs the same iasWorld-style CAMA (`DWELL`/`OBY` tables), so it probably does too.
- If it is wanted for a roll-based ADU count (not k), the Franklin script's `summarize` can take `DWELL.DAT`
  rows once `oh_parcels`' fixed-width reader exposes card, units and living area. That needs WS-CORE / WS-OH;
  see the PR.

---

## 3. More places

### 3.1 Scouting the largest uncovered places

A research subagent and Claude checked the largest uncovered places (2026-11-10). The checks were metadata
and counts only: ArcGIS Online searches, crawls of the city and county GIS service directories, the open-data
hubs, and one or two web searches per place. No permit portal was scraped.

| Place (eligible lots) | What exists | Usable? |
|---|---|---|
| **Cleveland (80,693)** | City ArcGIS layer `Building_Permits` (202,884 permits since 2015, work descriptions, parcel numbers), ODbL 1.0 | **Yes: adapter built (§3.2)** |
| Toledo (81,585) | City Data Hub (41 items) and `gis.toledo.oh.gov` (138 services) have a demolition layer, no permits. The Lucas Auditor has yearly cadastre layers 2000–2025, which are parcels, not permits | No |
| Akron (59,904) / Summit County | Summit County Building Standards issues Akron's permits in a Cityworks lookup portal with no export; `scgis.summitoh.net` has no permit layer | No |
| Parma (27,537), Euclid, Lakewood, Cleveland Heights, Strongsville, Mentor | Each city files its own permits (portals such as Citizenserve); Cuyahoga County has no countywide permit layer | No |
| Youngstown (21,992) / Mahoning | Mahoning County Building Inspection lookup portal only | No |
| Canton (21,780) / Stark | The "Building and Development" item is a 2013 property-cleanup map. The "Stark County Permits" layer belongs to Stark County, **Illinois** | No |
| Lorain, Elyria / Lorain County | No permit layer; the county hub's terms bar redistribution | No |
| Hamilton, Springfield, Cuyahoga Falls, Middletown | No open portal or permit layer found | No |

**Cleveland is the only record-level open permit source in Ohio beyond the four already covered.** Because
only one open source exists, §3 has one new place, not three. The Census BPS has place-level unit counts for
all of these cities but no ADU flag. Ben's standing rule is no records requests (memory, 2026-11), so none
are proposed.

### 3.2 Cleveland (`cle_permits`)

- **Adapter:** `src/lotline/adapters/states/oh/cle_permits.py`. Tests: `tests/states/oh/test_cle_permits.py`
  (16, synthetic rows).
- **Registered in:** `config/states/oh.yaml`. Provenance row and section in `docs/data_provenance.md` (only the
  Cleveland row was added).
- **License:** ODbL 1.0. Ben approved fetching it at run time on 2026-10-23 (`docs/build/oh-data-plan.md`,
  S7). The raw snapshot and `processed/oh/permits/cle_permits.parquet` stay in `LOTLINE_DATA_DIR`. Note that
  `docs/build/oh-readiness.md` (2026-11-01) still called it open; Ben reconfirmed on 2026-11-10.
- **Fetched** with `lotline fetch --state OH --source cle_permits`: 79,906 building permits (2015-01 to
  2026-11). 96% have a parcel number that maps to the Cuyahoga roll ID.
- **New one-family houses compared with Census BPS (units_1):**

  | Year | cle_permits | BPS units_1 |
  |---|---:|---:|
  | 2015 | 42 | 130 |
  | 2016 | 43 | 137 |
  | 2017 | 101 | 144 |
  | 2018 | 98 | 114 |
  | 2019 | 119 | 78 |
  | 2020 | 158 | 95 |
  | 2021 | 151 | 104 |
  | 2022 | 127 | 158 |
  | 2023 | 109 | 161 |
  | 2024 | 141 | 234 |
  | 2025 | 111 | 143 |

  The totals over 2017–2025 are close (1,115 against 1,231). Single years differ, because BPS counts by
  month reported and townhouse rows may be filed differently. 2015–2016 are low, likely because the permit
  system began then.
- **The ADU rule** (`adu_from_text`): the description names "in-law suite / apartment / unit", "carriage
  house", "ADU", "accessory dwelling", "granny flat" or "garage apartment" on a one-family, two-family,
  accessory-use or unlabelled permit. It is vetoed when:
  - the unit is existing, historic, being removed or only being altered;
  - the text says "not for in-law suite";
  - the work is a roof, porch or window on the unit.

  "Adult" never matches. When the permit also builds the main house, the row stays an SFD (1 unit) and
  carries `adu_type`, so the ADU is counted without being counted as a house.

**ADU permits by year** (eligible lots: 80,693)

| Year | ADU-only permits | House + ADU permits | All ADUs | Per 1,000 eligible lots |
|---|---:|---:|---:|---:|
| 2015 | 0 | 1 | 1 | 0.012 |
| 2016 | 2 | 0 | 2 | 0.025 |
| 2017–2019 | 0 | 0 | 0 | 0 |
| 2020 | 3 | 5 | 8 | 0.099 |
| 2021 | 1 | 1 | 2 | 0.025 |
| 2022 | 0 | 1 | 1 | 0.012 |
| 2023 | 0 | 0 | 0 | 0 |
| 2024 | 1 | 0 | 1 | 0.012 |
| 2025 | 0 | 0 | 0 | 0 |
| **2015–2025** | **7** | **8** | **15** | **0.017 a year** |

- 14 of the 15 are detached (over or behind a garage, or a carriage house); 1 is attached.
- Nearly all cite a Board of Zoning Appeals (BOZA) approval, as expected under a "no ADU use" rule.
- 2020 stands out: 8 ADUs, 5 of them with a new house. These are infill new builds in a few neighbourhoods
  (BOZA 20-xxx).

### 3.3 Hand check of the description rule

Every match was read, plus 30 random non-matches and 30 targeted near-misses. There are only 15 matches, so
the "30 matches" sample is all of them.

| Sample | Read | ADUs | Verdict |
|---|---:|---:|---|
| Matches | 15 (all) | 15 | **Precision 15/15** |
| Random non-matches: residential, non-demolition | 30 | 0 | Roofs, windows, fences, one addition |
| Targeted near-misses: non-matches naming a suite, apartment, living space, dwelling unit, guest, cottage or kitchenette (30 of 77) | 30 | 0–1 | One possible miss: "finishing the 2nd floor loft apartment" in a one-family house (2025). The others were master suites, attic bedrooms, apartment buildings, a third unit in a two-family house (missing middle) and care-facility changes of use |

- **Recall:** at least 15/16 among the permits the near-miss net reaches, so k_parser is about 1.0–1.07 for
  Cleveland. ADUs filed with no telltale words can't be seen this way, so this is an upper bound on recall.
- **Fixed during the check:** the house + ADU test first missed abbreviations ("2 STY. 3,708 S.F. SINGLE
  FAMILY RESIDENCE", "SINGLE FAM RES"). That put 5 house + ADU permits in the ADU-only column. The pattern
  now allows periods and "FAM"; the counts above are after the fix. The ADU total (15) did not change.

## 4. Proposed ADU rule rows (not written to `config/reforms/oh.csv`)

**Cleveland (3916000) already has a row:** `OH-3916000-adu-2010-none` ("No ADU use: One-Family District
§337.02 permits one dwelling house per lot", effective 2010-01-01). The 15 permits are consistent with it:
each needed a BOZA variance. So **Cleveland joins the ADU panel now**, as an untreated large city. It has:
- a record-level source with far more than 1,000 permits;
- an accepted "none" row; and
- eligible lots.

**No new rows are proposed.** One open question carries over from `docs/research/ordinances/oh-rules-tracker.csv`
and was not researched here: do the Neighborhood Form-Based Code districts (Ord. 347-2024, effective
2024-07-01, four pilot areas) or the 2026 Housing Innovation District (Ord. 626-2026, effective 2026-07-01)
allow an ADU on a house lot? If either does, Cleveland needs a partial-coverage `adu` row with that date and
`coverage` set to the mapped areas. Until then, the 2010 "none" row stands for the whole city.

## 5. What this means for the joint refit

- **Coverage:** Ohio's flagged-permit places hold 15.4% of eligible lots, or about **17.8% with Cleveland**
  (+80,693).
- **k:** Ohio can't measure a field-flag k. The Franklin Auditor cards carriage houses as garages, so the roll
  sees about 1 in 13 flagged ADUs as a dwelling. Raleigh's k (1.07, 1.02–1.21) stays the only measured value.
  Applying it to Ohio's field flags is an assumption, and Ohio has none: all of Ohio's ADU sources are parsers.
- **k_parser:**
  - **Cleveland:** about 1.0–1.07, from the hand check above.
  - **Columbus:** the closest evidence is the Council variance ratio. That is about 3.9 approved ADUs per
    flagged permit for 2020–2024, an upper bound, since not every approved ADU is built. The panel already
    takes the larger count each year, so the ratio is not applied again.
- **Cleveland's rate:** 0.017 ADUs per 1,000 lots a year under a no-ADU rule. That is near Greensboro's 0.03,
  well below Raleigh (0.47) or Durham (0.73), and a useful zero-ish untreated control.
