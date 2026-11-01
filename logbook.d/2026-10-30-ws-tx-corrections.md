### LB-NNN · 2026-10-30 · Policy analysis: Ben's decisions on the Texas rule-row corrections
- **Question:** which of the 35 corrections proposed from Ben's second research workbook (LB fragment
  `2026-10-30-ws-tx-research-workbook-2.md`) should change rows coded earlier?
- **What I did:**
  - Grouped the 35 proposals by the strength of their evidence: checked against a local official PDF, or
    workbook only. Recommended a decision for each and put the three judgement calls and the renaming question
    to Ben.
  - Applied his answers with `scripts/dev/tx_corrections_2026_10_30.py`. It edits field by field, adds a dated
    note naming the correction numbers to each edited row, renames four rows and their `supersedes`
    references, and fills the `decision` column.
  - Made `tx_research_2026_10_29.py` rerun-safe after the renames; replaying both scripts gives the same file.
  - Added `test_corrections_2026_10_30`.
- **Inputs:** `docs/research/ordinances/tx-corrections-2026-10-29.csv`; `config/reforms/tx.csv`.
- **Outputs:** `config/reforms/tx.csv` (17 rows corrected, 4 renamed), `tx-corrections-2026-10-29.csv`
  (decisions), `scripts/dev/tx_corrections_2026_10_30.py`, `scripts/dev/tx_research_2026_10_29.py`,
  `tests/states/tx/test_reforms.py`, ordinances README.
- **Findings / changes:**
  - Effective dates corrected from local PDFs: Dallas ADU 2018-06-30, Austin ADU 2015-11-30, Abilene LDC
    2010-06-01.
  - Corrected from the workbook: College Station ADU 2018-11-29 (Ord. 2018-4059), Frisco rentable ADU
    2019-10-01, Arlington 2014-07-10.
  - Moved to 2010-01-01 because the earlier dates were unsupported: San Antonio and Laredo.
  - McKinney goes from "no ADU" to a rentable by-right ADU (treated in D-025).
  - El Paso 2011 has no ADU parking minimum.
  - League City duplexes are by right in RSF-2.
  - FLAGs cleared on the Dallas (2), Houston and Austin 2015 rows. 67 of 89 rows are still flagged.
- **Decisions (Ben, 2026-10-30):**
  - Accept groups A and B; group B keeps its FLAGs.
  - Denton keeps 2023-03-07 with a note that it is unsupported. Not to be used as a dated event until the
    real date is found.
  - Abilene stays at one home per lot (the district text governs over the use matrix).
  - Rename the four rows whose year moved.
- **AI:** Claude summarized and ranked the proposals, wrote the script and test, and checked replay
  stability. Texas and panel tests pass.
- **Open / next:**
  - Denton's real ADU date.
  - League City RSF-5 SUP duplex row (start date).
  - College Station 2023 parking row, if one space per bedroom is confirmed.
  - Second-coder pass on the 67 flagged rows.
