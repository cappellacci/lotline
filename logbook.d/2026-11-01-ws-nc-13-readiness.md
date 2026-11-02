### LB-NNN · 2026-11-01 · Validation: North Carolina data readiness (thread 13, part A)
- **Question:** what is real and what is a fallback for every NC model input, what NC adds to the D-024 and
  D-025 panels, and whether V5 Charlotte's inputs are ready to freeze by Nov 17?
- **What I did:**
  - Checked the thread-13 snapshot against `main` (f9d9624) and the processed NC tables. Corrections: 454
    jurisdictions, not 322 (197 local-only places), and Hickory and Salisbury are not jurisdictions.
  - Counted coverage, tiers, panel places and rule dates with a read-only script that filters every outcome
    table for the holdout first.
  - Checked the V5 inputs and reproduced the N1 lot count and the town prior.
  - Refreshed the NC rows of `docs/data_availability.md` and wrote thread 10's closing section.
- **Inputs:** `~/lotline-data/processed/nc` (eligible rebuilt 2026-11-01 for #252), `config/reforms/nc.csv`,
  `config/fees/nc.csv`, the NC fragments.
- **Outputs:**
  - `docs/build/nc-readiness.md` and `scripts/dev/nc_readiness_counts.py`;
  - `reports/nc/V5-charlotte-inputs.md` (input check section);
  - the NC rows of `docs/data_availability.md`;
  - the closing section of `docs/build/handoffs/10-north-carolina-data-complete.md`.
- **Findings:**
  - 218 of 454 jurisdictions count from parcels (64.9% of the population of NC places).
  - D-025 gains 8 NC places with an in-window rule change. D-024 has 55 places of 10,000+, but only Durham and
    Raleigh are firm in-window events: 9 more rows are dated by the ordinance's adoption date.
  - V5: ACS, FHFA and the demand index run past 2023-06-01 for Charlotte, so annual inputs should stop at 2022.
    The Mecklenburg legacy permit file thins out in 2025.
- **Decisions:**
  - Proposed: annual V5 inputs are capped at 2022, using the holdout's own annual rule.
  - Proposed: run D-024 with and without the `[earliest-known]` events.
- **AI:** Claude Code (Opus 5.5) wrote the script and the docs. Every count in the report comes from the
  script's output. No engine, scenario or dev run; no held-out row was opened or counted.
- **Open / next:**
  - Part B (Minnesota).
  - Ben: the second-coder pass (#254), the Mecklenburg archive by Nov 10, the Durham V0 decision, and closing
    the stale branches.
- **Update (same evening):** after #254 merged with the second-coder review, the report and the counts were
  rerun on 7fc54e5. The script now treats `[predates]` rows as non-events (HANDOFF 2026-11-01).
  - Data sections are unchanged; only rules moved. There are now 92 rows; 28 local rows are second-coded and
    10 are tagged `[predates]`.
  - D-024 in-window events go from 11 to 10 (Asheboro is `[predates]`). D-025 still has 8 places; Matthews was
    re-dated to 2016 and Raleigh's overlay row to 2019-05-20.
