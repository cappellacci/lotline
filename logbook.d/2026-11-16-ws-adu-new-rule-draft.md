### LB-NNN · 2026-11-16 · ADU · Uptake where a place first allows ADUs (D-099 draft)

- **Question:** the gut check found that places with no ADU rule today (Dallas, Fort Worth, Cleveland) get the
  full fitted core-city rate under the Handbook reform. Do places that first allow ADUs build less in their
  first years? Ben: "When done let's do the fix".
- **Outputs:**
  - `docs/analysis_plan.md` D-099 (drafted, not accepted);
  - `src/lotline/model/adu_new_rule.py` with `tests/model/test_adu_new_rule.py`;
  - `adu_new_rule_share` (1, no effect) in `config/params/adu.yaml`;
  - the ν term in `scenarios.adu.pool_paths`, with a test;
  - `scripts/dev/adu_new_rule.py` (not run).
- **What Claude did:**
  - listed the fit places' first ADU-allowing rows from the rule rows only (about 27 after 2016-01-01,
    no counts read);
  - drafted the entry; wrote the helpers and the engine term behind ν = 1, with hand-worked tests;
  - wrote the profile and held-out script without running it.
- **How it was checked:** unit tests (first year, flags, scaling, the engine at ν 0.5 against hand, partial
  rules unaffected); ν = 1 leaves every existing test unchanged; ruff passes.
