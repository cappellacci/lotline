### LB-NNN · 2026-11-25 · Review · Onboarding guards: FIPS must match the state; FHFA asks for ZIP prefixes

- **Question:** Which mistakes in a new state's config file fail silently or with a confusing error?
- **Outputs:** `src/lotline/config/__init__.py` (`STATE_FIPS`, moved from the rule agents' docstore; `StateConfig`
  checks `fips` against the state code); `src/lotline/rule_agents/common/docstore.py` (reads the one table);
  `src/lotline/adapters/national/fhfa.py` (empty `zip3_ranges` gives a plain error); tests in
  `tests/config/test_state_schema.py`.
- **Decision:** Ben, 2026-11-25 (overnight): fix what needs no decision.
- **What Claude did and how it was checked:** all six state files still load; a test refuses Wisconsin with
  Minnesota's FIPS and lets a test code (ZZ/99) through; another shows FHFA's ZIP rows ask for `zip3_ranges` instead
  of failing inside `pd.concat`. Config, core and rule-agent tests pass (913).
