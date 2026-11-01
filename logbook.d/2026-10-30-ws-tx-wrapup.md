### LB-NNN · 2026-10-30 · Data feasibility: Texas wrap-up (county land-use codes, jurisdiction fix, readiness)
- **Question:** what closes the remaining Texas data gaps on Claude's side, and where does Texas stand after
  the rule and fee work (#241, #242, #244)?
- **What I did:**
  - **Jurisdiction fix.** `stratmap_parcels.resolve_jurisdictions` now leaves out parcels that fall in no Texas
    jurisdiction: a centroid in no known place, in a county whose remainder is not a BPS reporter. Test added.
  - **County land-use codes.**
    - Listed the codes left UNKNOWN by county and roll: 2.2M parcels across about 100 county-rolls.
    - A research subagent read official appraisal district documents for the 12 counties with the most of
      them: export layouts, land-type code PDFs, the Comptroller's 96-313. It proposed 431 code rows.
    - Most of these county fields hold land-type (valuation) codes, not uses. Reading Williamson's RES (about
      87% single-family) as a house lot would overcount. Mapping only a county's non-residential codes would
      lift places over the D-017 gate while their house lots stay unknown.
    - So only Johnson's and Wichita's codes, which are the districts' own state-category (use) codes, are
      applied. Their non-high rows are mapped by the PTAD crosswalk rule.
    - The rest are recorded with `applied = no`.
    - New `config/crosswalks/tx_county_land_use.csv` and loader, with a test.
  - **Rebuilt** TCAD, StratMap parcels, jurisdictions and eligible parcels. These are data builds, not model
    runs.
  - **Second-coder worksheet.** `docs/research/ordinances/tx-second-coder-2026-10-30.csv` has the 80 flagged
    rows by priority (dated reforms first), with what to check and blank columns for the second coder.
  - **Docs.** Refreshed `docs/build/tx-readiness.md` and the Texas rows of `docs/data_availability.md`.
- **Inputs:** `~/lotline-data` processed Texas tables; the appraisal district documents named in
  `tx_county_land_use.csv`.
- **Outputs:** `src/lotline/adapters/states/tx/stratmap_parcels.py`, `tests/states/tx/test_stratmap_parcels.py`,
  `config/crosswalks/tx_county_land_use.csv`, `docs/research/ordinances/tx-second-coder-2026-10-30.csv` and the
  ordinances README, `docs/build/tx-readiness.md`, `docs/data_availability.md`, `docs/data_provenance.md`
  (StratMap rows only), and rebuilt tables in `~/lotline-data` (not in the repo).
- **Findings:**
  - 478 of 1,006 jurisdictions now count from parcels (was 458): 458 places with 69% of the people in Texas
    places, plus 20 county remainders.
  - Tiers 125 / 176 / 705 (was 125 / 161 / 720). No jurisdiction lost parcels.
  - The non-jurisdiction rows in `eligible_parcels` went from 200 to 0.
  - Newcomers include Wichita Falls: 30,108 eligible from the 2019 roll, against an ACS fallback of 30,249.
    Also Burleson, Cleburne and Mansfield.
  - Four small cities (Jefferson, Kempner, Lampasas, Mingus) came in because the 80% county completeness check
    now counts only parcels inside jurisdictions.
  - 33 of 40 places of 100,000+ count from parcels.
  - Many counties' 2025 records carry no land-use code at all (Travis, El Paso, Fort Bend, Montgomery and
    others). No crosswalk can fix that.
- **Decisions:**
  - Ben 2026-10-30: pool Texas into the ADU estimate (D-025). Austin and San Antonio are treated; Fort Worth and
    Dallas are comparisons. Proposed for HANDOFF; WS-ENGINE implements it.
  - Proposed: apply county codes only where they are use codes (`applied`).
- **AI:** Claude wrote the code, tests and docs, and checked the subagent's proposed rows (enum, duplicates,
  residential coverage) before choosing what to apply. Before/after counts were compared on the rebuilt tables.
- **Open / next:**
  - Ben: a rule for fees that vary by area or plat date (SAWS, Fort Worth).
  - Ben: the second-coder pass and the remaining lookups; the TxGIO question.
  - Williamson's and Galveston's property-use tables, if Ben wants them.
  - Harris Z codes.
  - Per-vintage parcel files (WS-CORE).
- **Later the same day (second-coder review and Ben's second batch):**
  - **Review** (Ben's `tx-second-coder-reviewed.csv`), applied by `scripts/dev/tx_second_coder_2026_10_30.py`:
    - 2 of 80 rows agreed (Abilene ADU 2010, College Station ADU 2023): `coder_2 = ben-review`.
    - 4 "partly" findings went into the notes.
    - 74 rows had a boilerplate "could not independently confirm" note. They stay single-coder and flagged:
      the second-coder pass is not done for them.
  - **Ben's second batch** (answers to the ten questions, plus fees), applied by
    `scripts/dev/tx_ben_lookups_2026_10_30b.py`:
    - League City's Ord. 2026-10 is in force from 2026-05-26 and by right (Planning Director approval). This
      undoes the review's pending.
    - Tyler's garage apartments were in force by 2010: the row is renamed `TX-4874144-adu-2010`.
    - Laredo's R-1A, R-1B and R-1-MH allow one home.
    - Notes for Denton (the R4 SUP was in the 2019 code), McKinney (no universal 12,000 sq ft minimum),
      Killeen and Lewisville (ordinance numbers unconfirmed) and Edinburg.
    - SAWS 2015-2019 water totals ($4,597 / $4,777 / $4,861) noted on the component rows, not added as rows,
      which would double-count.
    - Houston's pre-2021 water rate ($790.55) added.
  - **Replay fixes:**
    - The 10-29 script matched fee rows on every column, so later notes made it re-add 10 rows. It now matches
      on place, year and fee type.
    - Renames in the corrections and batch scripts now run once, so a reused id
      (`TX-4815976-adu-2023`, now College Station's parking row) is not renamed again.
    - Edits meant for a renamed row go to that row.
    - Rerunning all five Texas scripts in order leaves `config/reforms/tx.csv` and `config/fees/tx.csv`
      unchanged.

