### LB-NNN · 2026-11-10 · `study-design` · The ADU undercount table: settling the six open choices
- **Question:** D-074 and D-075 make the ADU undercount k a table keyed by source. How are unmeasured,
  parser, low-recall, Columbus and floor sources handled, and how is k drawn?
- **Decided by:** Ben, 2026-11-10, accepted all six proposals ("Yes, use your picks"). Recorded as D-078.
- **Outputs:** `docs/analysis_plan.md`, D-078 (method only; nothing is wired yet).
- **What Claude did and how it was checked:**
  - Read the measured k and recall values from the five state reports on `main` and cited each one in D-078.
  - Proposed one answer for each open choice.
  - Computed the field-flag prior centre by hand: exp(mean(ln 1.07, ln 1.13, ln 1.06)) = 1.086.
  - D-076 and D-077 were already used by the fees work, so this entry is D-078.
- **Open:**
  - Wiring the table: a contract-change PR.
  - The refit model-form entry.
  - The parser and Mecklenburg-remainder fix sessions are blocked on disk space.
