### LB-NNN · 2026-11-19 · rule-agents · What broke when the rule agents met a state the app has never seen?

**Question.** A proof-of-concept run of the missing-middle agents on one place (Burlington, VT; a throwaway
data folder, no import) proposed no rows: the scout alone used 88.5k tokens against a 60k limit, every city
link it found returned 404, and two commands crashed. What needs fixing before the agents go into the
multi-state setup guide?

**Outputs.**
- `src/lotline/rule_agents/common/budget.py`: per-run limits saved in `RUN/limits.json` (`ledger limits`), so
  every agent's `ledger status` uses the run's budget; token default 120k -> 250k (the Agent tool's count
  includes everything an agent reads).
- `src/lotline/rule_agents/__main__.py`: `ledger summary` no longer crashes; new `ledger limits`.
- `src/lotline/rule_agents/common/places.py`: one places reader; MM, ADU (`worklist --jurisdictions`) and fees
  all accept a places CSV for a state with no jurisdictions table.
- `common/fetch.py`, `common/docstore.py`: a 404 suggests the Wayback copy; dead links and timeouts are
  remembered for a day, not a month.
- `common/handoff.py` (`url_key`), MM and ADU hand-off: one task per page however its address is written.
- MM CLI: `compare` and ADU/fees `compare` handle a new state; `reconcile` no longer fails on single-coder
  places; `select-b` skips places whose budget is spent.
- Agent prompts: scout and coder search/fetch counts now fit the place's limit; scouts try the archived copy
  of a dead link; MM scout records failed links; commands say who writes the finding when the budget stops a
  place. User guide: `--budget`, `--jurisdictions`.

**How Claude did it and how it was checked.** Claude (Opus 5.5) ran the proof of concept in a separate
session, reproduced both crashes, wrote the fixes and tests (limits saved, summary runs, places CSV, URL key,
dead-link expiry); rule-agent tests pass, ruff clean, compliance 0 FAIL. Rerun on Burlington follows.
