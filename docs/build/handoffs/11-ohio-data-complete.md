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

## Status 2026-11-01: handoff for the engine week

The plan (`docs/build/oh-data-plan.md`, #217) was approved. Its top-priority subtasks are merged, and the readiness
report, `docs/build/oh-readiness.md` (#234), is current to `main` at 6a70f9d. **Start there.** S7 (Cleveland
permits) and S8 (fees) have not started; both wait on Ben.

**Delivered (all merged):**
- Franklin County Auditor ADU flags (#224) and the Columbus recall work (#243): Council variances as an upper bound,
  with the larger of the two counts kept each year.
- Ohio rules: 29 ADU places and 4 missing-middle places (#226, with the tracker in
  `docs/research/ordinances/oh-rules-tracker.csv`).
- County land use and year built for Summit, Lucas, Cuyahoga, Butler and Franklin (#232).
- Franklin yearly rolls for 2016–2025 (#237 check, #239).
- Montgomery CAMA yearly rolls for 2011–2026 (Dayton off the ACS fallback), Montgomery ADU flags and Warren land use
  (#246).
- Interpolation between real rolls, labelled `parcels_interpolated`: the D-035 addendum, schemas 1.9 (#252, closes
  #251).

**Where Ohio stands:**
- **Jurisdictions:** 952. 885 count from parcels (95.5% of the population counted) and 67 use the ACS fallback.
  Of the 40 largest places, only Hamilton and Middletown are on ACS.
- **Tiers:** 85 / 800 / 67.
- **Yearly real rolls:** 27 jurisdictions (14 in Franklin, 13 in Montgomery).
- **Rules:** 49 rows: 38 ADU rows covering 29 places, 4 missing-middle rows, and parking and other rows. 24 are
  second-coded or adjudicated; 25 have one coder.
- **Fees:** the Handbook's $50,000 everywhere.

### For the engine threads (week of 2026-11-02)
- **ADU estimate (thread 7, D-025): 15 Ohio places.**
  - **7 treated in the window:** Cincinnati 2023-10-02, Columbus 2025-12-24, Bexley 2025-10-09, Dublin 2019,
    Gahanna 2024-05-01, Whitehall (special use 2023, by right 2025), Dayton 2023 (conditional use).
  - **8 "no ADUs" comparisons:** Grandview Heights, Groveport, Hilliard, New Albany, Obetz, Upper Arlington,
    Worthington, Kettering.
  - The Franklin and Montgomery permit sources flag only ADUs, so **the panel's caller must list their covered
    places**: a year with no ADUs has no permit row. Montgomery's list is `montgomery_permits.covered_places`
    (12 places).
  - All Ohio ADU counts except Cincinnati's are lower bounds: they come from permits whose description names an
    ADU.
  - Columbus keeps the larger of its permit count and its Council-variance count each year.
- **Missing-middle estimate (thread 1, D-024):** all 156 Ohio places of 10,000+ are in through BPS.
  - Two are treated in the window: Cincinnati (2024) and Euclid (Ord. 120-2024).
  - Dayton (2006) and Grove City (1979) were already treated before 2010. Code them as always treated, not as
    in-window events.
- **Eligible lots (thread 9, and anything that reads `eligible_parcels`):** #252 changes years that fall between
  two real rolls.
  - In Ohio that is Montgomery. For example, Dayton 2020 drops from 45,399 to 43,719.
  - **North Carolina's Wake County 2020–2022 also changes, in 13 places**: Raleigh rises about 1%, Zebulon 13.6%,
    Knightdale 13.2%. **Tell the NC thread and rebuild NC's `eligible` table before rerunning anything.**
  - Ohio's processed tables were last rebuilt before #252 merged. Rebuild with
    `OH_PARCELS_VINTAGE=2026-10-19 lotline fetch --state OH --source eligible`.
  - **Always set `OH_PARCELS_VINTAGE=2026-10-19`.** Without it, `oh_parcels` starts a new statewide download dated
    today, which takes most of a day.
- **Rows not to lean on as dated events until checked:**
  - The 15 in-window ADU and missing-middle rows have one coder: Ben merged #226 before a second coder checked
    them.
  - Cleveland Heights 2026 and Findlay 2027 are pending.
  - Grandview Heights' "no ADUs" date (2020-04-09) is from Ben's research agent and wasn't opened here.
  - Hamilton 2018 is for relatives or an on-site employee only.
- **Population weights:** `jurisdictions.pop_2020` totals 7.84 million for Ohio, against about 11.8 million. The
  township figures look partial, so check them before weighting by population.

### Decisions to fold into HANDOFF (thread 6)
None of these is in `HANDOFF.md` yet. Each is in the logbook fragment named.
| Date | Decision | Fragment |
|---|---|---|
| 2026-10-20 | Placeholder date 2010-01-01 for a "no ADUs" rule that predates the window; ADUs for family or an employee only count as owner-occupied (proposed) | `2026-10-20-ws-oh-4-adu.md` |
| 2026-10-26 | One roll vintage per jurisdiction from the statewide layer (proposed) | `2026-10-26-ws-oh-8-summit-land-use.md` |
| 2026-10-27 | Use the real Franklin yearly counts in place of scaled ACS for Franklin places | `2026-10-27-ws-oh-11-franklin-yearly.md` |
| 2026-10-28 | **Keep the 10% unknown-land-use gate (D-017)**: Hamilton and Middletown stay on ACS | `2026-10-26-ws-oh-8-summit-land-use.md` (#232) |
| 2026-10-28 | **Bias Columbus ADU counts toward recall**: Council variances plus looser flag rules; the larger source count each year | `2026-10-30-ws-oh-12-columbus-adu-recall.md` |
| 2026-10-30 | Drop roll polygons that appear in no Montgomery CAMA year (old lots) | `2026-10-31-ws-oh-13-montgomery-cama.md` |
| 2026-10-30 | Pre-window missing-middle rows (Dayton 2006; Grove City 1979, decided 2026-11-01) are coded for the current-rules scenario and count as treated before 2010 | `2026-10-26-ws-oh-7-rules.md` |
| 2026-11-01 | **Montgomery decisions:** fill-only land use; commercial year built added; the same 99% county-share rule; ADU-panel coverage of at least 100 reported permits a year (12 places); Auditor terms accepted; no 2023 CAMA file | `2026-10-31-ws-oh-13-montgomery-cama.md` |
| 2026-11-01 | **D-035 addendum:** interpolate linearly between two real rolls (`parcels_interpolated`, schemas 1.9) | `2026-11-01-ws-core-interpolate-roll-years.md` |
| 2026-11-01 | Drop the OGRIP request for a 2022 statewide roll | `2026-10-31-ws-oh-13-montgomery-cama.md` |
| 2026-11-01 | Merge the Ohio rules (#226) with only the 21 "no ADUs" rows second-coded (by Codex) | `2026-10-26-ws-oh-7-rules.md` |

**Logbook fold note:** `2026-10-26-ws-oh-7-rules.md`, `2026-10-31-ws-oh-13-montgomery-cama.md` and
`2026-10-26-ws-oh-9-readiness.md` each carry dated addenda inside one entry, so they fold as one entry each.

### Left open on purpose
- **S7, Cleveland permits:** the ODbL question is undecided.
- **S8, city fees:** not started.
- **Second-coder pass:** 25 rows, the 15 in-window rows included.
- **A disclosure line for Codex** (second coder) in `docs/disclosures.md`.
- **Unresolved ADU rules:** Westerville, Reynoldsburg, Lorain, Canal Winchester, Akron, Parma and Canton; see each
  place's `next_step` in the tracker.
- **Covered places with no ADU rule yet:** Grove City (ADU), and Montgomery's Centerville, Miamisburg, Trotwood and
  others.
- **Zoning layers:** not planned.
- **pyogrio:** approved and then removed (2026-10-26), so nothing is left to fold; Texas's "no pyogrio" decision
  stands.
- **Unused raw files:** a partial `raw/oh_parcels/2026-11-01/` snapshot, from a stalled run, is unused and can be
  deleted.
