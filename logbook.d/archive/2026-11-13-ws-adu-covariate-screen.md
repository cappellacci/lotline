### LB-NNN · 2026-11-13 · Method: D-083 (proposed), a screen of the ADU place effects against unused place factors
- **Question:** which pre-window place factors might explain the large ADU place effects (α 1.92) and the
  state misses of the D-079 refit? The candidates are factors the confounder register names that no ADU fit
  has tested.
- **Decisions:** Ben asked for the screen ("Draft the screen") after a methodology review in chat. D-083 is
  proposed and still needs Ben's acceptance.
- **What Claude did:**
  - Reviewed the ADU uptake study: D-023/D-025/D-031, the mechanism fits D-039 through D-079, D-045's audit,
    and `docs/research/lotline-confounder-register.csv`. A read-only helper agent digested the documents, and
    the key values were spot-checked against `config/params/hazard.yaml` and the D-079 refit README.
  - Wrote D-083. It defines seven factors and two references, all measured before 2016, an availability rule,
    a one-factor-at-a-time Poisson-gamma refit (within-state as the main read, pooled as a second), a
    three-part bar, and the holdout handling.
- **Outputs:** `docs/analysis_plan.md` (D-083). No code, no run, no data read.
- **How it was checked:** the entry's references were checked against the analysis plan, `calibrate_adu.py`
  (`frailty_loglik_place`), the ACS adapter's tables and holdout note, and the parcel schema fields.
  `compliance_check.py` was run.
- **AI disclosure:** Claude Code wrote the review and the entry. Ben decides whether to accept it.
