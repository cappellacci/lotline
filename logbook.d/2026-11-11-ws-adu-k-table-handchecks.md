### LB-NNN · 2026-11-11 · `adu` · The undercount table takes the D-081 hand-check values
- **Question:** what k does each ADU parser source carry into the joint refit, now that parser k is
  precision ÷ recall (D-081) and the second parser round has been rebuilt (#391) and re-checked (#393, #394,
  #396)?
- **Decided by:** Ben, 2026-11-11 ("Yes, do both": merge the hand checks and write the table PR).
- **Outputs:**
  - `config/params/adu.yaml` `adu_flag_undercount`: new rows for Mecklenburg 0.98, Asheville before 2022 1.47,
    Greensboro 1.39, Fort Worth 1.14 and Cincinnati 0.78, and Cleveland's range widened to 1.00–1.31. Dallas
    is marked out of the fit.
  - `src/lotline/config/__init__.py`: parser rows may have k < 1, while field rows stay >= 1. This is a
    contract change.
  - Docstrings in `src/lotline/model/undercount.py`.
  - Tests in `tests/model/test_undercount.py`.
- **What Claude did and how it was checked:**
  - Copied each value from the hand-check reports' proposed rows.
  - Added a by-hand quantile test for a parser k below 1, and real-table asserts.
  - The ADU, undercount, calibration and eligible tests pass (552).
- **Open:**
  - The refit entry must remove Dallas from the fit set.
  - Fort Worth's no-kitchen count stays a named sensitivity.
  - Parser follow-ups listed in #394 and #396.
