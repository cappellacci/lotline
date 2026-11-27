### LB-fragment · 2026-11-02 · [build] · What does the engine thread need now that all four states' data is on main?

- **Question:** With NC and MN closed (PRs #255–#262 merged on 2026-11-02), what should the next WS-ENGINE thread
  do, in what order, and under what rules?
- **Outputs:** `docs/build/handoffs/14-engine-four-state-refresh.md` (new thread 14 brief); a row for it in
  `docs/build/handoffs/README.md`.
- **What it says:** four tasks: (1) teach the panel builders the rule tags (`[predates]`, `[earliest-known]`,
  `DATE UNCONFIRMED`, "none" rows), which no engine code reads yet; (2) panel counts on the four-state data,
  checked against the readiness reports; (3) dated D-024 and D-025 amendment entries before any fit, then one run
  each after Ben's go-ahead; (4) V5 Charlotte and St. Paul freezes by Nov 17.
- **AI:** Claude Code (Opus 5.5) wrote the brief from the four readiness reports, the OH and TX closing sections,
  D-024/D-025 in `docs/analysis_plan.md` and a `git grep` showing no code reads the tags. Script flags and freeze
  file names were checked against the repo.
- **Proposed HANDOFF decision:** `DATE UNCONFIRMED` rows count as events; engines also run without them (Ben,
  2026-11-02).
