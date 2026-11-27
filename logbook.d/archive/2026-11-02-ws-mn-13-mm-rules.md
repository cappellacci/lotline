### LB-NNN · 2026-11-02 · Rules: Minnesota missing-middle rules from the batch-1 records (thread 13, M4)
- **Question:** which Minnesota places can get a coded missing-middle rule from the batch-1 ordinance records
  without new research, and which of the 40 largest places still need a lookup?
- **What I did:**
  - Read the `missing_middle_legal` entries of the 21 MN places in `batch1-2026-10-20.json`.
  - Coded the five whose source was read, with the record's quote.
  - Checked that the Minneapolis 2040 Plan injunction windows are already coded, as two `moratorium` rows with
    start and end dates.
  - Wrote the fill-in table for the rest.
- **Inputs:** `docs/research/ordinances/batch1-2026-10-20.json`; the MN jurisdictions table (2020 population).
- **Outputs:**
  - `config/reforms/mn.csv` (5 rows);
  - `scripts/dev/mn_mm_batch1_2026_11_02.py` (idempotent);
  - `docs/research/ordinances/mn-mm-lookups-todo.csv` (33 places) and its README entry.
- **Findings:**
  - St. Louis Park (Ord. 2690-25, 2025) is a new in-window D-024 event, but its effective date comes from a
    search snippet.
  - Duluth (2026) falls after the window.
  - Rochester, Brooklyn Park and Coon Rapids are coded as "one home" (untreated on evidence).
  - The other 13 batch-1 records were "unknown", mostly because the code hosts blocked scripts.
- **Decisions:** none new. One-home rows follow the Texas convention, with a 2010-01-01 placeholder marked
  `[earliest-known]`.
- **AI:** Claude Code (Opus 5.5) coded the rows from the records' quotes. The rows are single-coder, and nothing
  new was fetched. Checked with the MN and core reform tests.
- **Open / next:** Ben's lookups (largest first); a second coder for the five rows, St. Louis Park's
  effective date first.
