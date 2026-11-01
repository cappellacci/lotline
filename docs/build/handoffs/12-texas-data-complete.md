# Thread 12: Texas, end-to-end data collection (WS-TX)

**Goal:** get Texas's data good enough to feed the engines statewide and, above all, to **add Texas places to the multi-state ADU and missing-middle estimation panels.** Texas is the opposite of Ohio: Austin is rich (Travis roll, 3,166 ADU permits since the 1970s) and almost everything else is national data only. Follow the North Carolina pattern: **assess, write a subtask plan for Ben's approval, then work it.** Target: done within the week of 2026-10-26.

**Read first:**
- the shared rules in `docs/build/handoffs/README.md`, plus one more for data threads: **don't run engine, scenario or dev-run scripts** unless Ben asks;
- the North Carolina thread's outputs, as the template and for its lessons: `docs/build/handoffs/10-north-carolina-data-complete.md`, `docs/build/nc-data-plan.md`, PRs #199–#214;
- `docs/build/workstreams/WS-TX.md`; `docs/data_availability.md` (TX table); `docs/research/lotline-data-catalog.csv` (TX rows: Houston plat activity, Austin Water and SAWS impact fees, the sale-price non-disclosure note);
- `config/states/tx.yaml` and `config/reforms/tx.csv`; `reports/tx/V0.md`;
- `docs/analysis_plan.md` D-008 (repeated project totals), D-014 to D-035.

## Snapshot on main (2026-10-23, verify it yourself)
| Input | Status | Known gap |
|---|---|---|
| Jurisdictions | 1,006 (952 places, 54 county remainders); tiers: 1 tier 1 (Austin), 1,005 tier 3 | Everything outside Austin is national data only |
| Parcels | 239,626 from the Travis CAD 2026 roll (hand-registered) | Austin's Williamson and Hays parts; **no other county**. Check for a statewide parcel layer (TxGIO / StratMap land parcels, from appraisal-district data) and confirm its license and fields before planning on it. One roll year (D-035). |
| Permits | Austin (1971–2026): 3,166 ADU, 8,790 2–4 unit | No other city. Check open permit data for San Antonio, Houston (plat activity; permits), Dallas, Fort Worth, El Paso and the large suburbs: which flag ADUs or units per building? |
| ADU rules | 23 rows, 19 places (18 of the 20 largest coded) | Corpus Christi, Pasadena (blocked: fill-in table for Ben); McKinney needs a second check; Killeen's overlay vote (2026-10-20) outcome |
| Missing-middle rules | 2 rows | Austin HOME (2024), Houston, San Antonio and others: dates for 2–4 units legal |
| Fees | 2 rows | Austin Water and SAWS impact fees (catalog), city fee schedules |
| Prices | ACS, FHFA | Texas doesn't disclose sale prices (catalog note); rely on ACS and FHFA |

## Step 1: assess and plan (first PR, docs only)
Verify the snapshot, then write `docs/build/tx-data-plan.md`: one subtask per gap, each with what it feeds, the source, whether it is automatable without broad web research, an estimated cost, a priority (needed for the multi-state estimation panel / needed for an end-to-end run / improves accuracy), and an owner. Include at least:
1. **Permit sources with ADU and units-per-building fields** for the large cities. Top priority: each adds places to the panels. Watch for repeated project totals (D-008) and city limits at issue date (annexation, as Durham #206).
2. **Parcels beyond Travis:** a statewide layer if one exists and is licensed for reuse, otherwise the largest counties' appraisal districts (some need a manual download, like TCAD).
3. **ADU and missing-middle rule histories with dates** for places with permit data first, then the 40 largest. Use fill-in tables for Ben where sites block.
4. **Fees.**
5. **Ben's manual items,** with exact instructions.

Commit the plan as a PR and **ask Ben to approve it before heavy work** (large downloads, research beyond targeted lookups).

## Step 2: work the approved plan (small PRs)
- **Rules research:** no broad web-search sweeps. Use official pages you can reach directly, put anything you can't open into fill-in tables for Ben (`docs/research/ordinances/tx-adu-lookups-todo.csv`, `tx-mm-lookups-todo.csv`), and code confirmed rows into `config/reforms/tx.csv` with citation fields.
- **Downloads:** through the IO layer, robots.txt first, never work around blocks. Mark manual downloads for Ben.

## Step 3: readiness report
`docs/build/tx-readiness.md`: coverage of every model input across Texas's 1,006 jurisdictions (real vs fallback vs unknown), the number of places Texas adds to the ADU and missing-middle estimation panels, and the remaining gaps with what closes each. **No model runs.**

**Stay out of:** `model/*` and `model/scenarios/*`; the demand index.

**Done when:** the plan is approved, its top-priority subtasks are merged or handed to Ben, and the readiness report is open. Never merge; Ben reviews.

---

## Closed 2026-11-01 (Ben: close Texas data; engine focus next)

The done-when is met. The plan (`docs/build/tx-data-plan.md`) was approved and its subtasks merged. The
readiness report, `docs/build/tx-readiness.md`, is current to 2026-11-01. **Start there.**

**Delivered (all merged):**
- Permits for San Antonio, Fort Worth and Dallas, plus D-036 (#218-#231).
- StratMap statewide parcels with a standard-library file-geodatabase reader (#238).
- Readiness report (#240, refreshed in #245).
- Rule and fee rows from Ben's two research workbooks and his own lookups (#241, #242, #244, #249).
- County land-use codes and the jurisdiction fix (#245).
- The fee rule (#248).

The rule and fee rows rebuild with the scripts in `docs/research/ordinances/README.md` ("Replay order"); all of
them can be rerun without changing the files.

**Where Texas stands:**
- **Parcels:** 1,006 jurisdictions; 478 count from parcels and 526 use the ACS fallback.
- **Tiers:** 125 / 176 / 705.
- **Rules:** 103 rows, ADU rules for 39 places and missing middle for 39. 81 rows are flagged for a second coder.
- **Fees:** local totals for San Antonio $6,981, Fort Worth $5,828, Austin $6,763, Houston $4,383 and Dallas
  $931; the Handbook $50,000 elsewhere.

### For the engine threads (week of 2026-11-02)
- **ADU estimate (thread 7, D-025):** Ben decided on 2026-10-30 to pool Texas in.
  - Austin (4805000) and San Antonio (4865000) are treated places; Fort Worth (4827000) and Dallas (4819000) are
    comparisons. All four have record-level ADU permits.
  - Their rule rows and dates are in `docs/build/tx-readiness.md` §2. Dallas's 2018 row now takes effect
    2018-06-30, and Austin's 2015 row 2015-11-30.
  - Fort Worth's ADUs are non-rental (#222): decide whether they count as an outcome.
- **Missing-middle estimate (thread 1, D-024):** all 232 Texas places of 10,000+ are in through BPS.
  - Five places have a dated change in the window: Austin 2024-02-05, Houston 2023-11-27, League City 2020-09-29,
    Lewisville 2022-12-01 and Lubbock 2023-10-01.
  - Five allowed two or more homes from before 2010.
  - 29 are untreated on evidence, as one-home rows.
  - Several start dates are 2010-01-01 by convention and flagged.
- **Fee scenario (thread 2):** issue #247 (contract change, WS-CORE).
  - The per-place low-high fee range is in the central rows' notes but doesn't reach P10-P90 yet.
  - The newest-year-per-component rule leaves Austin's 2023 water and wastewater impact fees out (about $7,700
    for the newest plat cohort), so Austin's $6,763 is a floor.
- **Combine and aggregate (thread 9):** Texas's eligible-parcel table is rebuilt (2026-10-30). Two jurisdictions
  have no denominator (Marshall Creek, Starbase; see the readiness report).
- **Rows not to lean on as dated events until checked:**
  - Killeen 2026 (overlay only; ordinance number unconfirmed).
  - Lewisville 2026 (approval reported at the meeting; no signed ordinance found).
  - Denton 2023 (date unsupported; kept with a note).
  - The 74 rows the 2026-10-30 review could not check.

### Decisions to fold into HANDOFF (thread 6)
None of these is in `HANDOFF.md` yet. Each is in the logbook fragment named.
| Date | Decision | Fragment |
|---|---|---|
| 2026-10-27 | No pyogrio (its wheels bundle LGPL and MPL libraries); a standard-library file-geodatabase reader instead | `2026-10-27-ws-tx-filegdb.md` |
| 2026-10-27 | Leave out a county's part of a StratMap release when it has under 80% of the county's parcels in the other release (`min_county_roll_completeness`) | `2026-10-27-ws-tx-filegdb.md` |
| 2026-10-27 | Read only the 2019-03 and 2025-06 StratMap releases, one roll per release at its release year (proposed) | `2026-10-27-ws-tx-filegdb.md` |
| 2026-10-30 | The 35 proposed rule corrections: groups A and B accepted; Denton's date kept with a note; Abilene stays at one home; four rows renamed to their new year | `2026-10-30-ws-tx-corrections.md` |
| 2026-10-30 | **Pool Texas into the ADU estimate (D-025)**: Austin and San Antonio treated, Fort Worth and Dallas comparisons | `2026-10-30-ws-tx-wrapup.md` |
| 2026-10-30 | **Fees that vary by area or plat date:** the median area or newest plat cohort is the central per-home fee, the rest the range | `2026-10-30-ws-tx-fee-rule.md` |
| 2026-10-30 | Apply a county's own land-use codes only where they are use codes (Johnson, Wichita), not land-type codes (proposed) | `2026-10-30-ws-tx-wrapup.md` |
| 2026-11-01 | Don't pursue TxGIO about the missing land-use codes; close the Texas data thread for engine work | `2026-11-01-ws-tx-carrollton.md` |

**Logbook fold note:** all 22 Texas fragments are well formed. Two other fragments stop
`scripts/dev/merge_logbook.py`, because each holds more than one entry:
- `2026-10-19-ws-nc-3-clt-preudo.md` (2 entries);
- `2026-10-20-ws-engine-17-d025-results.md` (4 entries).

Split each into one file per entry before folding.

### Left open on purpose
- **Pasadena:** pending for ADU and missing middle (no zoning; `test_reforms.py` PENDING).
- **Second-coder pass:** 74 rows not checked.
- **Land-type county codes** (Williamson, Galveston and others; `tx_county_land_use.csv`, `applied = no`).
- **Not pursued:** Harris's Z codes, the TxGIO question, Dallas 2025 permits and Houston record-level permits.
- **Ben's open lookups:** `docs/research/ordinances/tx-*-lookups-todo.csv`.
