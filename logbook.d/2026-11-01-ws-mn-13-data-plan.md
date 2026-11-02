### LB-NNN · 2026-11-01 · Data feasibility: Minnesota data plan for the Nov 12 readiness report (thread 13, part B)
- **Question:** what does Minnesota need by Nov 12 to stand where Ohio and Texas did on 2026-11-01, and what does
  St. Paul's V5 freeze (Nov 17) need?
- **What I did:**
  - Checked thread 8's snapshot against `main` (f9d9624) and the processed MN tables. Every outcome table was
    read through `holdout.apply`, and parcel rolls with the snapshot rule.
  - Cut thread 8's tasks down to five must-do subtasks (M1–M5) and three for if time allows (M6–M8).
- **Inputs:** `~/lotline-data/processed/mn`, `config/reforms/mn.csv`, `config/fees/mn.csv`, the MN catalog and
  scouting notes.
- **Outputs:** `docs/build/mn-data-plan.md`.
- **Findings:**
  - MN's `eligible_parcels` predates D-035, so parcel-counted places have no denominator history before 2021.
    Two jurisdictions have no row at all.
  - The pre-2024 St. Paul rolls exist: 2021, 2022, and 2023 (exported 2023-12-26). But no parcel table carries
    zoning, so H1/H2 lots need St. Paul's zoning layer.
  - 185 metro places have Met Council permits; 76 of them have an ADU rule and 49 an in-window change.
- **Decisions:** for Ben: approve the plan and the MnGeo download; choose the V5 H1/H2 source.
- **AI:** Claude Code (Opus 5.5) did the assessment and wrote the plan from read-only counts. No download, and
  no model run.
- **Open / next:** M1 (St. Paul V5 note) once approved.
