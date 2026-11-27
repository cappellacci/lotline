### LB-NNN · 2026-10-21 · Data feasibility: North Carolina data plan (thread 10, step 1)
- **Question:** what does North Carolina still need before every engine can run end to end for all 322 NC
  jurisdictions, and in what order should it be done?
- **What I did:**
  - Checked the thread 10 snapshot against `main` (`b0777eb`) and the processed NC tables in `~/lotline-data`
    (jurisdictions, parcels, eligible parcels, permits, reform and fee rows).
  - Probed open permit layers with one ArcGIS search per city and metadata/count queries only (no downloads).
  - Wrote one subtask per gap with what it feeds, source, cost, priority and owner.
- **Inputs:** `docs/build/handoffs/10-north-carolina-data-complete.md`, `docs/build/workstreams/WS-NC.md`,
  `config/states/nc.yaml`, `config/reforms/nc.csv`, `config/fees/nc.csv`, `docs/research/lotline-data-catalog.csv`,
  `docs/research/ordinances/batch1-2026-10-20.json`, `reports/nc/charlotte_pre_udo_parcels.md`, D-012 to D-025.
- **Outputs:** `docs/build/nc-data-plan.md`.
- **Findings:**
  - The 79 NC places counted from parcel rolls have an eligible-parcel count for one year only (2023 Wake,
    2026 OneMap), so engines that need 2010–2024 have no denominator for Raleigh, Greensboro, Durham and
    others (S13, an end-to-end blocker; method choice for WS-CORE and Ben).
  - Greensboro has an open permit layer the catalog missed: 125,092 permits, 1990-07-30 to 2026-10-20, with
    unit counts and zoning (S3). That would give D-025 a third NC ADU adoption (2024-04-16).
  - OneMap holds 5,926,051 parcels; 1.63M (10 counties) are loaded. Fees are Raleigh FY2026 only.
- **Decisions:** proposed in the PR, for Ben: approve the S1 download, the Greensboro adapter and capped rule
  research; V5 Charlotte roll option (b) now, (a) if Mecklenburg answers by Nov 10; S13 issue to WS-CORE.
- **AI:** Claude Code (Opus 5.5) did the assessment and wrote the plan. Counts come from queries on the
  processed tables and the ArcGIS endpoints named in the plan; no Charlotte or Mecklenburg outcome from
  2023-06-01 was read.
- **Open / next:** Ben's approval, then step 2 in small PRs (S13 issue and S2 first).
