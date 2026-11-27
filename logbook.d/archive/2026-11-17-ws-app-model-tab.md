### LB-NNN · 2026-11-17 · WS-APP / ADU · Model tab: one shared frame and three model cards

- **Question:** How should the app's "The model" tab explain ADUs, missing middle and fee cuts together, and what is the final ADU text (#438)?
- **Decision (Ben, 2026-11-17, in chat):** keep the shared steps (question, data, baseline, ranges, other states, limits); step 3 gets a switcher with one card per model, each answering the same five questions (in one sentence, how it works, what it learned from, how we tested it, what it can't tell you). Claude drafts all three cards; the missing-middle card goes to the Missing Middle session to check.
- **Outputs:** `src/lotline/app/template.html` (model tab); app rebuilt locally at `reports/app/index.html` (gitignored).
- **Also updated:** blind-test status (Oregon and Charlotte opened and scored, St. Paul still locked on `main`), the ADU and missing-middle leave-a-state-out rows, the missing-middle limit (93 places, effect not clearly detected).
- **Sources for the numbers:** ADU: 2026-11-16 config note, D-096 tier-1 table (`reports/adu-types-fixed-rows/tiers.csv`), D-099. Missing middle: PR #443's C4 section of `docs/model_and_assumptions.md`. Fees: D-010, D-076, D-077.
- **What Claude did and how it was checked:** drafted the text and the switcher; app tests (45) pass; the built page was opened in the browser pane and the switcher clicked (one card shown at a time, tests table and diagram render). Mortgage rates and equity were first written as "not in the model"; `hazard.yaml` showed they are, and the text was corrected before commit.
