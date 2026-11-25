### LB-NNN · 2026-11-25 · Review · Issue triage; missing middle's fast-ramp case explained in one sentence (thread 17)

- **Question:** Which open code issues still need work, and should the app show missing middle's fast-ramp case?
- **Outputs:** `src/lotline/app/template.html` (missing-middle card note; Model tab wording); issue triage table in
  `reports/review/2026-11-code-review.md`; issues #247, #406, #138 and #448 closed with notes; #506 kept for A21.
- **Decision:** Ben, 2026-11-25: close #247, #406 and #138 "as recommended"; no fast-ramp result in the app, one
  sentence instead ("Yes, add the note"). No HANDOFF decision.
- **What Claude did and how it was checked:** Claude Code checked each issue against `main` (code, config and the
  analysis plan) before proposing an outcome. The note's 3.6× comes from D-100's fast-ramp run (3.61 in every state);
  the ratio depends only on the two ramp values in `config/params/mm_hazard.yaml` (4.0 and 0.5 years), both checked.
  The app was built with the Texas bundle; the note is on the page and every inline script passes `node --check`.
  App tests pass.
