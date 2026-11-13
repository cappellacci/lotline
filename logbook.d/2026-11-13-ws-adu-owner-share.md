### LB-NNN · 2026-11-13 · Method: D-084 (proposed), owner-occupied share as a place term in ADU Form A
- **Question:** how should owner-occupied share enter the ADU model, and how would we know it helps?
- **Decisions:** Ben asked for the draft ("Draft owner share"), after D-083's screen and its leave-one-place-out
  check found owner share robust. D-084 is proposed and still needs Ben's acceptance.
- **What Claude did:** wrote D-084. Its parts:
  - **Form A′:** Form A × exp(β_o z), with z centered and scaled on D-083's 57 places (0.6727, 0.1544).
  - **Owner share source:** 2011–15 in the fit and the latest vintage in the scenario, with county-subdivision
    and holdout fallbacks.
  - **Scoring:** D-079's tests.
  - **Decision rule:** D-079's, except that the score comparison also applies when neither form passes a tier.
  - **Before any fit:** an expected direction and three sensitivities.
- **Outputs:** `docs/analysis_plan.md` (D-084). No code, no fit, no data read beyond D-083's outputs (the
  center and scale were computed from `reports/adu-covariate-screen/factors.csv`).
- **How it was checked:**
  - D-079's tests and decision rule were read before writing.
  - The center and scale were recomputed from `factors.csv`.
  - `compliance_check.py` was run.
- **AI disclosure:** Claude Code wrote the entry. Ben decides whether to accept it.
