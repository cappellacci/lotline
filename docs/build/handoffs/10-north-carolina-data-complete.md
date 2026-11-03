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

---

## Closed 2026-11-01 (thread 13)

**Delivered (all on `main` unless noted):**
- **Plan** `docs/build/nc-data-plan.md` (S1–S13; approved 2026-10-21).
- **Parcels:** OneMap for 48 counties (3.84M parcels; per-county crosswalks, the 0.6–1.4 check against ACS, and
  the `rural_home` rule); Wake rolls for Nov 2019 and Dec 2023; Charlotte's pre-UDO layer.
- **Permits:** Raleigh, Durham (annexations dated from 2013, #94), Greensboro, and the Mecklenburg legacy file
  (filtered for the holdout first).
- **Rules and fees:** 92 rule rows; 132 fee rows for 16 jurisdictions.
- **Denominator history:** #208 and #252 (D-035 and its addendum), with NC's table rebuilt.
- **V5 Charlotte:** N1 translation, the option (b) prior, and an input check (`reports/nc/V5-charlotte-inputs.md`).
- **Readiness report** `docs/build/nc-readiness.md` (this PR).
- **Second-coder review** (#254, merged): 28 local rows second-coded, 10 tagged `[predates]`, 5 rows added.

**Where North Carolina stands:**
- **Jurisdictions:** 454 (157 BPS places, 197 local-only places, 100 county remainders). 218 count from
  parcels, 64.9% of the population of NC places. Of the 40 largest places, 10 are on ACS: Charlotte, Concord,
  Greenville, Jacksonville, Chapel Hill, Kannapolis, Sanford, Thomasville, Asheboro and Clayton.
- **Tiers:** 124 / 94 / 236.
- **Real rolls:** 13 Wake jurisdictions have two (2019 and 2023, interpolated between them). Everyone else has
  one roll or ACS.
- **Rules:** 41 jurisdictions. 28 of the 71 local rows are second-coded (8 agree, 20 adjudicated); 43 have one
  coder.
- **Fees:** 16 jurisdictions; the Handbook's $50,000 elsewhere.
- **S10 integration run:** not done. The data-thread rule (thread 13) replaced it with counts.

### For the engine threads (week of 2026-11-02)
- **ADU estimate (thread 7, D-025): 8 NC places** with ADU-flagged permits and an in-window rule change.
  - Raleigh (2019-05-20 overlay, 2020 by right, 2022), Durham city (2019, 2023), unincorporated Durham County (2019)
    and Greensboro (2024-04-16).
  - The Mecklenburg towns: Cornelius (2023), Huntersville (2024), Matthews (2016, re-dated by the review) and
    Mint Hill (2011).
  - All four NC permit sources are full permit files, so no covered-places list is needed.
  - Raleigh's ADU flag starts in 2019.
  - Drop 2026 for the Mecklenburg towns and treat 2025 as partial: the legacy file ends.
  - Greensboro and Mecklenburg counts are lower bounds (description parser).
- **Missing-middle estimate (thread 1, D-024):** 55 BPS places of 10,000+.
  - Firm in-window events: Durham (2019) and Raleigh (2021, 2022).
  - Eight more in-window rows are dated `[earliest-known]`: Wake Forest, Wilson, Morrisville, Sanford,
    Burlington, Mooresville, Garner, Monroe. The second coder confirmed their current rules, not their start
    dates. **Run with and without them.**
  - Apex (2000) and New Bern (1996) are treated before 2010.
  - So are Asheboro and Goldsboro: their rows are `[predates]`.
  - **`[predates]` rows (10, HANDOFF 2026-11-01) are never events**, whatever their date.
- **V5 Charlotte (WS-ENGINE, #45, by Nov 17):** read the file and column table in
  `reports/nc/V5-charlotte-inputs.md`.
  - **Cap every annual input at 2022.** ACS, FHFA and the demand index run past 2023-06-01 for Charlotte, and
    ACS 2023–2024 housing counts include homes built in the window.
  - Option (a) only if Mecklenburg's archive arrives by Nov 10.
- **Local-only places** (197) have no BPS outcome of their own. Their permits are inside their county's BPS
  row, and D-020 keeps their parcels out of the county remainder. Engines that need a BPS outcome must skip
  them or use the county row.
- **Hickory and Salisbury** aren't jurisdictions. Their rule rows act only through the county rule mix (D-021).

### Rows not to lean on as dated events until checked
- 43 local rows still have one coder. Most reviewed rows are "partly": the current rule checks out, and the
  history or details were left unresolved.
- The `[earliest-known]` rows: 27 of the 45 local ADU rows (6 of them `[predates]`) and 8 in-window
  missing-middle rows.
- Sanford's 2018 missing-middle date is flagged unconfirmed (back on the lookup list).
- Wilson and Sanford dates come from Ben's lookups. The chapters carry no dates.
- Monroe 2022 is by special use permit only.
- Wilmington 2024: the district list wasn't read (coverage is from a news report).
- Gastonia 2025: the use table conflicts with the text.

### Decisions to fold into HANDOFF (thread 6)
None of these is in `HANDOFF.md` yet.

| Date | Decision | Fragment |
|---|---|---|
| 2026-10-19 | Mecklenburg DUPLEX-TRIPLEX → DUPLEX; patio homes → SF_ATTACHED (Ben) | `2026-10-19-ws-nc-3-onemap.md` |
| 2026-10-19 | S.L. 2026-59 enters the baseline for the 19 cities, with a sensitivity that adds Wake Forest and Holly Springs (proposed) | `2026-10-19-ws-nc-3-reforms.md` |
| 2026-10-19 | No use of Mecklenburg's current roll for Charlotte; ask the county for a pre-2023-06-01 archive | `2026-10-19-ws-nc-3-clt-preudo.md` |
| 2026-10-21 | **V5 option (b)**: the six towns' shares as a prior with a range; swap in the archive (a) if it arrives by Nov 10 (Ben) | `2026-10-21-ws-nc-8-v5-prep.md` |
| 2026-10-21 | Approve S1 (OneMap download), S3 (Greensboro) and capped rules research (Ben) | `2026-10-21-ws-nc-data-plan.md` |
| 2026-10-21 | The 0.6–1.4 ACS band for accepting a drafted county crosswalk (proposed) | `2026-10-21-ws-nc-1-onemap-statewide.md` |
| 2026-10-21 | A `date_basis` field (adoption / earliest-known) on rule rows (proposed contract change for WS-CORE) | `2026-10-21-ws-nc-4-rules-research.md` |
| 2026-10-23 | Durham's fee is the 2024 Reference Guide's (equal to the Raftelis maximum); the 2009 impact-fee tables stay out | `2026-10-23-ws-nc-rules-pass2.md` |
| 2026-11-01 | NC second-coder decisions (Ben: accept the recommendations; keep Mint Hill's duplexes by right). The `[predates]` rule itself is already in HANDOFF | `2026-11-01-ws-nc-second-coder.md` |
| 2026-10-23 | `rural_home` keyword rule ("RURAL IMPROVED" and similar read as houses) | `2026-10-23-ws-nc-outliers.md` |

### Left open on purpose
- **The "partly" second-coder verdicts** (43 single-coder rows), and a predecessor-code check for the 8
  `[earliest-known]` D-024 rows.
- **The Mecklenburg archive** (V5 option a), until Nov 10.
- **The Accela permit file** (the towns from 2025; Charlotte after the freeze).
- **Lookups:** missing-middle (17 places), ADU (add Davidson and Pineville), fees
  (Charlotte Water, Fayetteville PWC, Cary, High Point).
- **One-home rows for Fuquay-Varina and Indian Trail.** Pass 2 found no duplexes; not coded yet.
- **Durham V0**: whether to compare the city alone with BPS (Ben).
- **Troutman's backcast** (WS-CORE) and Princeville's mobile homes (not planned).
- **Carthage (V6a)**, new parcel counties, zoning layers: out of scope.
- **Stale branches** to close: `ws/nc-3-onemap`, `ws/nc-3-wake`, and #213 (`ws/nc-dev-run-2026-10-22`).
