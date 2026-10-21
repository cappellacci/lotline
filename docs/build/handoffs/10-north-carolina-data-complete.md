# Thread 10: North Carolina, end-to-end data collection (WS-NC)

**Goal:** get North Carolina's data into a state good enough to feed the engines end to end: the baseline forecast, the ADU scenario (D-025), the missing-middle scenario (D-024), the fee scenario, and combining and aggregation (thread 9) for all NC jurisdictions. Follow the Minnesota pattern (thread 8, `docs/build/handoffs/08-minnesota-data-complete.md`). **Start by assessing what exists, then write your own subtask plan, then work it.**

**Read first:**
- the shared rules in `docs/build/handoffs/README.md`;
- `docs/build/workstreams/WS-NC.md` and `docs/data_availability.md` (NC table);
- `docs/research/lotline-data-catalog.csv` (NC rows);
- `config/states/nc.yaml` and `config/reforms/nc.csv`;
- `docs/analysis_plan.md` D-012 (the Charlotte holdout covers Mecklenburg 37119), D-014 to D-025;
- `reports/nc/` (V0, the Charlotte pre-UDO note);
- the ordinance records: `docs/research/ordinances/batch1-2026-10-20.json` (Raleigh, Durham entries) and the manual-lookup CSVs in that folder;
- thread 8's `docs/build/mn-readiness.md` if it exists, as the template.

## Snapshot on main (2026-10-21, verify it yourself)
| Input | Status | Known gap |
|---|---|---|
| Jurisdictions | 322 (222 places, 100 county remainders); tiers 54 / 32 / 236 | Wilmington, Hickory, Salisbury and Statesville are filed under their counties by BPS and are not in the table (D-021's county-row rule mix handles them) |
| Parcels | 2.39M: NC OneMap for 10 largest counties; Wake Dec 2023 roll; Charlotte pre-UDO zoning layer | 90 counties on the ACS fallback, though the OneMap adapter can load all 100. The Wake roll is the automated copy (robots.txt): Ben's manual download and `lotline manifest register` are pending. Charlotte has no pre-2023 land use: Ben's request to Mecklenburg is pending. |
| Permits | Raleigh (2000–2026) and Durham (2007–2026), both with ADU flags (291 and 392) | No other city. Mecklenburg (`meck_permits`) is coded but blocked by a Cloudflare challenge (Ben's request pending). Greensboro, Winston-Salem, Cary, Fayetteville and others: check the catalog for open permit layers. |
| ADU rules | 31 rows covering 23 places, including S.L. 2026-59 as 19 per-city rows (effective 2027-01-15) | Most of the 20 largest places lack dated history (#166 was partial; the search budget ran out). D-022 draws uncoded places. |
| Missing-middle rules | 5 rows | Dates when 2–4 units became legal: Raleigh (2021), Durham (EHC 2019), Charlotte UDO (2023, holdout) and others to confirm |
| Fees | `config/fees/nc.csv`: 11 rows (from the batch-1 records) | Coverage beyond Raleigh and Durham; Charlotte Water; S.L. 2026-59 §49 fee disclosures (check whether published) |
| Market, rates, costs | ACS, FHFA, FRED: statewide | — |
| Demand index | Thread 3 (CBP shift-share), PR #187 | Wait for it to merge |
| Holdout | Charlotte V5 (3712000, plus 37119 from 2023-06-01) | **The V5 Charlotte prediction must be frozen by Nov 17.** Nothing may use Charlotte or Mecklenburg outcomes from 2023-06-01. |

## Step 1: assess and plan (first PR, docs only)
Verify the snapshot against the data directory and main. Then write `docs/build/nc-data-plan.md`: one subtask per gap, each with
- what it feeds (which engine and parameter);
- the source (adapter, API, manual download by Ben, or a fill-in lookup table);
- whether it is automatable without broad web research;
- an estimated cost (time; token-heavy or not);
- priority: *needed for an end-to-end run* vs *improves accuracy*;
- owner: you, Ben, or another thread.

Include at least these, plus anything else you find:
1. OneMap parcels for all 100 counties (tiers, land-use coverage, `parcel_sources`, the D-017 gate);
2. a rebuild of statewide eligible parcels with non-overlap checks;
3. permit sources with ADU and 2–4 unit flags beyond Raleigh and Durham (catalog first);
4. ADU rule histories for the 40 largest NC places: dated by-right and permit changes since 2010;
5. missing-middle rule dates for the same places;
6. fees by city and year (Raleigh fee guide history, Charlotte Water, others in the batch-1 records);
7. Ben's pending manual items (Wake files, the Mecklenburg request) with exact instructions;
8. what V5 Charlotte needs before Nov 17.

Commit the plan as a PR and **ask Ben to approve it before any heavy work** (large downloads, or research beyond targeted lookups).

## Step 2: work the approved plan (small PRs)
- **Rules research (ADU and missing middle):** don't run broad web-search sweeps; they were expensive and mostly blocked.
  - Use the batch-1 records and official city pages you can reach directly (council records, city ADU and housing pages).
  - Put everything you can't open into fill-in tables for Ben: `docs/research/ordinances/nc-adu-lookups-todo.csv` and `nc-mm-lookups-todo.csv`, same format as Minnesota (place, GEOID, population, what's needed, a starting link, blank answer columns), largest first.
  - Code confirmed rows into `config/reforms/nc.csv` with the schemas 1.7 citation fields. Unsourced or unread stays blank (D-022), with the `adus_per_lot = 0` convention for "no ADUs".
- **Parcels and permits:** through the IO layer, robots.txt first, never work around blocks. Mark anything blocked for Ben.
- **Fees:** in thread 2's `config/fees` format (`scripts/dev/ordinance_records.py` if merged).

## Step 3: readiness report
`docs/build/nc-readiness.md`: coverage of every model input across NC's jurisdictions (real vs fallback vs unknown), remaining gaps with what closes each, and a statewide integration run of what's built (baseline plus the ADU scenario as a development run, with the D-025 fragility warning), confirming it completes for every jurisdiction.

## Stay out of
- `model/*` and `model/scenarios/*` (WS-ENGINE and threads 1, 2, 9);
- the demand index (thread 3);
- Charlotte or Mecklenburg outcomes from 2023-06-01, ever.

**Done when:** the plan is approved and its "needed for an end-to-end run" subtasks are merged or handed to Ben, and the readiness report shows NC can run end to end. Never merge; Ben reviews.
