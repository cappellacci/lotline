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
