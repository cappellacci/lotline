### LB-NNN · 2026-10-28 · Policy analysis: Texas lookup trackers updated from Ben's research workbook
- **Question:** what does Ben's agentic research run on the Texas ADU, missing-middle and fee lookups settle,
  and what is still open?
- **What I did:**
  - Read the workbook (`~/lotline-data/manual/texas/Texas-Municipal-ADU-and-Missing-Middle-Research.xlsx`:
    city findings, a source register, a PDF inventory, the supplied lists and an issues list) and matched each
    finding to the three lookup tables.
  - Coded what it settles with an append-only script: a new Corpus Christi ADU row (Ord. 032357, 2021) and
    notes on Austin HOME (Part 21 dates) and San Antonio's 2023 ADU row (IB 402 agrees). Added a `status`
    column to the three tables.
- **Inputs:** the workbook and its two PDFs (Austin HOME Ord. 20231207-001, SB 15 enrolled); the lookup
  tables; `config/reforms/tx.csv`.
- **Outputs:** `config/reforms/tx.csv` (54 rows), `scripts/dev/tx_research_2026_10_27.py`,
  `docs/research/ordinances/tx-{adu,mm,fee}-lookups-todo.csv`, `docs/research/ordinances/README.md`,
  `tests/states/tx/test_reforms.py` (Corpus Christi no longer pending).
- **Findings:**
  - Settled: Corpus Christi ADUs by right in every residential district since Ord. 032357 (2021-02-23), owner
    occupancy, one detached unit, 500 to 1,000 sq ft by district; Austin HOME in effect 2023-12-18 for
    applications from 2024-02-05 (the coded date stays 2024-02-05).
  - Partial: Carrollton (an accessory building may be a dwelling only on 20,000 sq ft of buildable area);
    San Antonio missing middle (more than one unit without an owner on site needs a rezoning).
  - Open: 13 of 15 ADU lookups, 30 of 32 missing-middle lookups, all 5 fee lookups and 35 rows flagged for a
    second coder. The workbook adds Dallas and Fort Worth ADU source paths but no current rule.
- **Decisions:** none. The coded facts come from the workbook; Claude did not reopen their sources
  (Corpus Christi's code host disallows AI agents; no PDF reader here), so the new row is flagged.
- **AI:** Ben's research run produced the workbook; Claude transcribed it, coded the settled items and checked
  the script is append-only and idempotent (two runs, one change); the Texas reform tests pass.
- **Open / next:** Ben's lookups as listed; second-coder pass.
