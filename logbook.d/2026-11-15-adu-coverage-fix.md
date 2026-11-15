### LB-NNN · 2026-11-15 · Build: ADU rule rows corrected after the coverage audit (D-095 follow-up)
- **Question:** Which ADU rule rows flagged by the coverage audit (blank placeholders, zone lists that cover every
  single-family district, limited areas read as citywide) are miscoded, and what do the sources say they should be?
- **What I did:**
  - Read every flagged row in fit places (largest first), using each row's own text and cited source, local copies of
    codes in `~/lotline-data/manual/`, and public code pages (Zoneomics mirrors, city PDFs, Wayback) for district lists.
  - Changed 33 rows: 4 blank/"none" rows set to the explicit no-ADU convention (Burnsville, Rosemount, Vadnais Heights
    before their ordinances; Chanhassen's "none" row); 17 zone lists that named every single-family district cleared to
    citywide (Charlotte 2012, Raleigh, Huntersville, Cornelius, Minneapolis 2023, Portland, Bend, Minnetonka, Mounds View,
    Rosemount, Cottage Grove); 12 rules that named a subset read as citywide given a zone list (Forest Lake 2004, Medford
    2016, Burnsville, Bloomington, Eagan, Inver Grove Heights, Blaine, St. Louis Park, Vadnais Heights).
  - Added notes to 26 flagged rows that are coded correctly, and marked 2 unsettled blanks `UNKNOWN-PLACEHOLDER`
    (Cottage Grove and Maplewood before their rewrites).
- **Inputs:** `reports/adu-coverage-audit/` (PR #437), `config/reforms/{mn,nc,or,tx}.csv`, sources cited per row.
- **Outputs:** `config/reforms/{mn,nc,or,tx}.csv` (61 rows), `docs/research/adu-coverage-fix-2026-11.md`.
- **Findings:**
  - Audit flags, before → after: blank 7 → 4 (fit 5 → 2), zones_switch 55 → 31 (fit 34 → 10), strong 35 → 32 (every
    remaining strong row was read by hand and is citywide on purpose).
  - The remaining zone switches are real changes in where ADUs are allowed (e.g. Plymouth 2009 → 2023, Medford 2016 → 2018).
  - The 0.75 judgment for an unmeasured zone list is blunt for rural-only rules (Forest Lake 2004): a parameter question.
- **Decisions:** none recorded here. Proposed for the ADU session: leave the two `UNKNOWN-PLACEHOLDER` place-years out
  of the fit, then refit.
- **AI:** Claude (Opus 5.5) read the rows and sources, with two research subagents (district lists for 20 places;
  pre-reform rules for 3 MN cities), and applied the edits with a script that records old → new values in
  `coding_notes`. Checked by recomputing coverage with `coverage_map` before and after for every changed row,
  rerunning the audit, `pytest tests -k reform` (99 passed) and `compliance_check.py` (0 FAIL). No code, params,
  fits or model runs.
- **Open / next:** ADU session refit. Fridley 2022 and New Brighton 2024 district lists could not be read (left
  citywide). The 43 flagged rows outside the fit were not changed.
