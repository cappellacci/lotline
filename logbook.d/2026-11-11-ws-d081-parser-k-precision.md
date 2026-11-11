### LB-NNN · 2026-11-11 · `study-design` · Parser k as precision ÷ recall, and the hand-check decisions
- **Question:** the 2026-11-11 hand checks found parser flags with precision of 0.52–0.77. How should parser
  sources' k handle false positives, and what happens before the refit?
- **Decided by:** Ben, 2026-11-11 ("Yes, use your picks"). Recorded as D-081.
- **Outputs:** `docs/analysis_plan.md`, D-081.
- **What Claude did and how it was checked:**
  - Read #384, #385 and #386.
  - Proposed six decisions.
  - Checked that precision ÷ recall turns flagged counts into true ADUs, which 1 / recall does not when
    precision < 1.
  - Merged #382, #383, #384, #385 and #386.
- **Open:**
  - The Cincinnati adapter fix and the shared-parser round.
  - The offline rebuild.
  - Fresh checks for the sources that move.
  - One PR putting the k values into the table.
