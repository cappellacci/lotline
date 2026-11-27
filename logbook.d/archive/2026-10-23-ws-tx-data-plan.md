### LB-NNN · 2026-10-23 · Data feasibility: Texas data plan (thread 12, step 1)
- **Question:** what does Texas need to run end to end and, above all, to add places to the ADU (D-025) and
  missing-middle (D-024) estimation panels; which sources can close each gap?
- **What I did:**
  - Checked the brief's snapshot against `main` (`f7cc92a`) and `~/lotline-data/processed/tx`.
  - Read D-024/D-025 to see what each panel needs from Texas: rule dates for the MM panel (its BPS outcome
    already covers 232 Texas places), ADU-flagged city permits for the ADU panel.
  - Probed sources with one metadata or count query each (robots.txt first, no bulk downloads): TxGIO
    StratMap parcels (DataHub API), Fort Worth, San Antonio, Dallas, Collin CAD, Arlington, San Marcos and El
    Paso permits, plus one ArcGIS Online search for other large cities.
- **Inputs:** `docs/build/handoffs/12-texas-data-complete.md`, `docs/build/nc-data-plan.md`, WS-TX brief,
  `config/reforms/tx.csv`, `config/fees/tx.csv`, `docs/data_availability.md`, the data catalog.
- **Outputs:** `docs/build/tx-data-plan.md`.
- **Findings:**
  - StratMap Land Parcels is CC0 with seven statewide vintages (2019–2026; 2026: 253 counties, 2.7 GB zip),
    so Texas can leave the ACS fallback almost everywhere; the download host blocks scripts, so Ben downloads.
  - Fort Worth (2001–2026, unit counts, CC-BY 4.0) and San Antonio (2020 on, an ADU permit type, CC-BY) can join
    the ADU panel; Dallas permits run to 2025 (the catalog says 2020) but carry no license.
  - Snapshot corrections: ADU rules cover 18 places, not 19; Austin HOME and Houston Livable Places are already
    coded as missing-middle rows; 16 rule rows await a second coder.
- **Decisions:** none recorded; four approvals asked of Ben in the plan's §6.
- **AI:** Claude ran the checks and wrote the plan; counts come from the processed tables and the live
  services' own count queries. One San Antonio `/api/` metadata call was made before reading its robots.txt,
  which disallows `/api/`; noted in the plan, not repeated.
- **Open / next:** Ben's approval and the StratMap download; then S1a (Fort Worth) and S1b (San Antonio).
