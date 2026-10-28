### LB-NNN · 2026-10-26 · Data feasibility: Texas loose ends after the merges (Dallas rule history, eligible rebuild, readiness)
- **Question:** what could be closed without Ben after the Texas PRs merged, while the StratMap download is
  blocked?
- **What I did:**
  - Added a 2010 "none" ADU row for Dallas (`scripts/dev/tx_adu_rows.py`) from the sources already read for
    its 2018 row, so every panel year has a dated rule; the 2018 row now supersedes it. The script reproduced
    the rest of `config/reforms/tx.csv` exactly.
  - Rebuilt Texas eligible parcels (`lotline fetch --state TX --source eligible`), a data build, not a model run.
  - Checked the two places without ACS (Marshall Creek, Starbase) against BPS.
  - Brought `docs/build/tx-readiness.md` up to the merged state.
- **Inputs:** `main` at `4721668`; processed Texas tables; D-025, D-035.
- **Outputs:** `config/reforms/tx.csv` (1 row added, 1 row's `supersedes`), `scripts/dev/tx_adu_rows.py`,
  `docs/build/tx-readiness.md`; the rebuilt `eligible_parcels` table in `~/lotline-data` (not in the repo).
- **Findings:** Austin now has eligible-parcel counts for every year 2010-2024 (ACS scaled to its 2026 TCAD
  roll; ADU-eligible 125,700 to 163,890); nothing else moved. Marshall Creek last reports to BPS in 2009 and
  has no 2020 population, so it should leave the jurisdictions table (WS-CORE). Starbase first reports in 2025.
- **Decisions:** none.
- **AI:** Claude made the changes and checks; counts only.
- **Open / next:** StratMap download (Ben); Marshall Creek's jurisdiction row (WS-CORE).
