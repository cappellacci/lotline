### LB-NNN · 2026-11-03 · [engine] · Where should the scenarios' effect sizes come from, given that the in-state estimates can't size them?
- **Question:** the four-state runs left D-024 without a credible estimate and D-025 without an estimate. Ben
  asked what we are doing wrong, given that the goal is a five-year prediction for any state.
- **What I did:**
  - Computed each run's smallest detectable effect from its standard error. The four-state D-024 could only
    detect about 10× permits, and October's D-025 about 30×. More of the same data won't close that gap.
  - Listed the design problems the run exposed: reforming cities were already growing; always-treated places
    are identified across places; rules are coded as allowed, not binding; the outcome is measured with noise.
  - Wrote D-037: route 1, mechanism-based effects anchored to external evidence. The ADU scenario already
    works this way; missing middle needs an uptake hazard with an evidence-based anchor. The in-state results
    become a consistency check and out-of-sample tests.
  - Kept the choice reversible: nothing retired; an `effect_source` switch in the scenario contract; both
    sources shown side by side; revisit triggers written down.
  - Amended the V5 freeze proposal's effect row to match.
- **Outputs:** `docs/analysis_plan.md` (D-037); `reports/engine14/v5_freeze_proposal.md`.
- **Decisions:** D-037 (Ben, 2026-11-03). Proposed for HANDOFF: "Scenario effects come from the mechanism route
  (D-037); in-state estimates validate; the choice is reversible by `effect_source`."
- **AI:** Claude Code (Opus 5.5) diagnosed the power problem, computed the table from the committed
  `estimates.csv` files, and drafted the entry. No model run.
