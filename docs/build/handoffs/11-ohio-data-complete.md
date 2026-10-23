# Thread 11: Ohio, end-to-end data collection (WS-OH)

**Goal:** get Ohio's data good enough to feed the engines statewide (baseline, ADU, missing middle, fees, combining and aggregation) and, above all, to **add Ohio to the multi-state ADU and missing-middle estimation panels** (more places with dated rules and ADU / 2–4 unit permit counts). Follow the North Carolina pattern: **assess, write a subtask plan for Ben's approval, then work it.** Target: done within the week of 2026-10-26.

**Read first:**
- the shared rules in `docs/build/handoffs/README.md`, plus one more for data threads: **don't run engine, scenario or dev-run scripts** (`model/*`, `scripts/dev/*_run.py`, `simulate_state.py`) unless Ben asks;
- the North Carolina thread's outputs, as the template and for its lessons: `docs/build/handoffs/10-north-carolina-data-complete.md`, `docs/build/nc-data-plan.md`, and PRs #199–#214 (`gh pr list --repo cappellacci/lotline --state merged --search "NC thread 10"`);
- `docs/build/workstreams/WS-OH.md`; `docs/data_availability.md` (OH table); `docs/research/lotline-data-catalog.csv` (OH rows: Cleveland permits, Columbus capacity charges, county auditor transfers);
- `config/states/oh.yaml` and `config/reforms/oh.csv`;
- `docs/analysis_plan.md` D-014 to D-035 (eligibility, tiers, D-017 known-land-use gate, D-022 unknowns, D-024 and D-025 panels, D-035 eligible history).

## Snapshot on main (2026-10-23, verify it yourself)
| Input | Status | Known gap |
|---|---|---|
| Jurisdictions | 952 (567 places, 297 townships, 88 county remainders); tiers 826 / 126 | No tier 1, because year built is missing from the statewide roll |
| Parcels | 6.09M parcels, all 88 counties, statewide 2023 roll (`oh_parcels`) | **One roll year only**: the estimators need eligible-parcel history, so find a second roll (NC used Wake 2019; D-035 scales ACS to one roll). Summit, Lucas, Muskingum, Meigs and others are >10% unknown land use (D-017 fallback). No year built or units. |
| Permits | Columbus (2010–2026), Cincinnati (2010–2026). ADU flags: Cincinnati 26, Columbus 0. 2–4 units: 1,479 and 1,100. | No other city. Cleveland permits are in the catalog. Columbus has no ADU flag: check its permit fields and work-class codes. Dayton, Toledo, Akron and suburbs: check for open permit layers. |
| ADU rules | 20 rows, 15 places | Uncoded among the 20 largest: Akron, Parma, Canton, Lorain, Cuyahoga Falls (amlegal blocks automated reading: fill-in table for Ben). Dayton OH: Ben's lookup (Ord. 31991-22A, 2022-09-21) vs the coded 2023-05-10 row: reconcile. |
| Missing-middle rules | 1 row | Dates for 2–4 units legal (Columbus zoning code update; Cincinnati Connected Communities 2024; others) |
| Fees | none | Columbus water and sewer system capacity charges (catalog), city fee schedules |
| Market, demand | ACS, FHFA, FRED, demand index (#187): statewide | — |

## Step 1: assess and plan (first PR, docs only)
Verify the snapshot, then write `docs/build/oh-data-plan.md`: one subtask per gap, each with what it feeds, the source, whether it is automatable without broad web research, an estimated cost, a priority (needed for the multi-state estimation panel / needed for an end-to-end run / improves accuracy), and an owner. Include at least:
1. **Permits with ADU and 2–4 unit flags** beyond Cincinnati: Columbus fields, Cleveland, others. These add places to the estimation panels, so they're the top priority.
2. **A second parcel roll year,** or another route to eligible-parcel history.
3. **Land-use gaps** in Summit and Lucas: county auditor files.
4. **ADU and missing-middle rule histories with dates** for the places with permit data first, then the 40 largest places. Use fill-in tables for Ben where sites block.
5. **Fees.**
6. **Ben's manual items,** with exact instructions.

Commit the plan as a PR and **ask Ben to approve it before heavy work.**

## Step 2: work the approved plan (small PRs)
- **Rules research:** no broad web-search sweeps. Use official pages you can reach directly, put anything you can't open into fill-in tables for Ben (`docs/research/ordinances/oh-adu-lookups-todo.csv`, `oh-mm-lookups-todo.csv`, Minnesota format, largest first), and code confirmed rows into `config/reforms/oh.csv` with the schemas 1.7 citation fields.
- **Parcels and permits:** through the IO layer, robots.txt first, never work around blocks.
- **Fees:** in `config/fees` format.

## Step 3: readiness report
`docs/build/oh-readiness.md`: coverage of every model input across Ohio's 952 jurisdictions (real vs fallback vs unknown), the number of places Ohio adds to the ADU and missing-middle estimation panels (with dated rules and flagged permits), and the remaining gaps with what closes each. **No model runs.**

**Stay out of:** `model/*` and `model/scenarios/*`; the demand index.

**Done when:** the plan is approved, its top-priority subtasks are merged or handed to Ben, and the readiness report is open. Never merge; Ben reviews.
