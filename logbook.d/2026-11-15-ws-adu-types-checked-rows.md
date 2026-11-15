### LB-NNN · 2026-11-15 · ADU · Does A + place types transfer between states on the checked rule rows?

- **Question:** D-088 picked Form A + place types on the old rule rows. Does it still hold, and does it transfer,
  on the source-checked rows (#419)?
- **Outputs:** `reports/adu-place-types-checked/` (tables, run log, README, `results.html`);
  `scripts/dev/adu_types_checked_page.py`; a rescoring note under D-088 in `docs/analysis_plan.md`. Results page
  published as an Artifact.
- **Result:** A + P is useful (inside P10–P90 and within ×2) in all 4 scorable states at tiers 1 and 2, the first
  form to pass D-075's claim rule. D-088's rule still keeps Form A, on one place (College Station, test A). Test D
  unchanged: no form forecasts within a state over time. Decision on the rule outcome and on config goes to Ben.
- **What Claude did:** reran D-088's unchanged script on the stack top, offline; wrote the page builder and notes.
- **How it was checked:** the run's Form A and A′ fits reproduce D-087's on the same rows (θ 0.503, α 2.648;
  θ 0.379, β_o −0.78); every place's type matches D-088's; ruff and format checks pass.
