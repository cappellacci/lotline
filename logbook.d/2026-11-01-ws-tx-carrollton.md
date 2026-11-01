### LB-NNN · 2026-11-01 · Policy analysis: Carrollton ADU rule; TxGIO question dropped
- **Question:** what does Ben's Carrollton lookup settle, and what happens to the open TxGIO question?
- **What I did:**
  - Coded `TX-4813024-adu-2011` with `scripts/dev/tx_ben_lookups_2026_11_01.py` (rerun-safe).
  - Set the Carrollton ADU tracker row to coded and added `test_carrollton_adu_2011`.
  - Marked the TxGIO question as not pursued in `docs/build/tx-readiness.md`.
- **Inputs:** Ben's lookup in chat (2026-11-01). Its sources are the Carrollton CZO (April 2026 and 2020
  editions), the CZO amendment register and Article 24.
- **Outputs:** `config/reforms/tx.csv` (103 rows), `docs/research/ordinances/tx-adu-lookups-todo.csv`,
  `scripts/dev/tx_ben_lookups_2026_11_01.py`, `tests/states/tx/test_reforms.py`, `docs/build/tx-readiness.md`,
  ordinances README.
- **Findings:**
  - Under Ord. 3421 (ratified 2011-01-11), an accessory building may be a dwelling only on a lot with at least
    20,000 sq ft of buildable area, in the SF-detached, SF-attached/townhouse and D districts. No SUP is named,
    so it is coded by right. A separate meter is prohibited and there is no size cap.
  - Rental is unresolved, so owner occupancy is left blank. A guest house (Ord. 1947) cannot be rented, and the
    code does not say whether every accessory dwelling is a guest house.
  - The effective date and the pre-2011 rule are unresolved, so the row is flagged.
  - D-021 measures the lot minimum on total lot area, so Carrollton's coverage is an upper bound.
- **Decisions:** Ben 2026-11-01: the TxGIO question is not pursued, because an answer would come too late.
  Those counties stay on their 2019 roll or the ACS fallback.
- **AI:** Claude coded the row from Ben's findings and ran the Texas tests and the full suite.
- **Open / next:**
  - Pasadena (ADU and missing middle) and Dallas (impact fee), from Ben's pending lookups.
  - Second-coder pass.
  - #247 (WS-CORE).
