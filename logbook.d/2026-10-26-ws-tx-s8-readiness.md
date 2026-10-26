### LB-NNN · 2026-10-26 · Validation: Texas readiness report, first draft (Texas plan S8)
- **Question:** how much of each model input is real Texas data across the 1,006 jurisdictions, and what does
  Texas add to the ADU and missing-middle estimation panels?
- **What I did:** counted coverage from the processed tables in `~/lotline-data` and the branch files of the
  open Texas PRs, keeping `main` and "with the open PRs" apart; no engine, scenario or development run.
- **Inputs:** processed Texas tables (jurisdictions, BPS, ACS, FHFA, FRED, demand, eligible parcels, permits);
  `config/reforms/tx.csv` on `main` and on #223; `config/fees/tx.csv`; D-022, D-024, D-025, D-034, D-035.
- **Outputs:** `docs/build/tx-readiness.md`.
- **Findings:** every jurisdiction has BPS, ACS (950 of 952 places), FHFA and the demand index, but only
  Austin has a parcel count and none has a water or sewer fee. With the open PRs, four cities with 22% of the
  population in Texas places have record-level permits. Texas could bring 4 places to the ADU estimate if it
  pools states, and League City (partly) plus six untreated-on-evidence places to the missing-middle one.
- **Decisions:** none; the report lists the open ones (#221, Austin's parcel source, Fort Worth's ADUs).
- **AI:** Claude computed the counts and wrote the report; figures are counts from the tables, no estimates.
- **Open / next:** rerun after the StratMap download and the merges.
