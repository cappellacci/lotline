### LB-NNN · 2026-11-15 · ADU · Should core cities and suburbs have their own place-luck spread? (method draft)

- **Question:** the range coverage check found core cities' ranges too wide and suburbs' too narrow. Ben asked
  for the method entry that would test a spread per type ("Draft D-094").
- **Outputs:** `docs/analysis_plan.md`, D-094 (proposed, not accepted; method only, before any fit).
- **What it says:** Form A + P + S gives core cities and suburbs their own place-effect variance, fitted as
  α_sub and λ = log(α_core ÷ α_sub); D-088's decision rule with A + P as the base decides; the held-out log
  score, not coverage by type, is the deciding test, because the coverage split has been seen. Off by default;
  nothing goes to config or the engine without a later approval.
- **What Claude did:** read how α is fitted (`adu_types.fit_types`) and drawn (`joint_refit.predict`,
  `scenarios/adu.py`), and drafted the entry.
- **How it was checked:** the figures it cites were read from `reports/adu-range-coverage/`; no code changed.
