### LB-NNN · 2026-11-25 · Review · Code review tidy-ups: thresholds to config, dead stubs, label consistency, app slots (thread 17, part A)

- **Question:** Can the small review findings (A10, A26–A30) be cleared without moving any result?
- **Outputs:** `config/params/adu.yaml` (`adu_blank_field_restrict_prob`, `adu_rule_parcel_known_min_share`);
  `config/states/tx.yaml` (`austin_adu_universe_before`, `austin_demolition_lookback_years`),
  `config/states/oh.yaml` (`development_adu_min`); `config/params/mm.yaml` source; `src/lotline/model/scenarios/adu.py`;
  the Austin ADU roll, Cincinnati, Wake, Franklin and Minneapolis roll-diff adapters; Greensboro, Mecklenburg and
  CSTX permits; `src/lotline/adapters/comparables/` removed; `src/lotline/app/build.py`, `template.html`;
  `docs/model_and_assumptions.md` parameter table; `docs/build/BUILD_PLAN.md` note; review rows A10, A26–A30.
- **Decision:** Ben, 2026-11-25: "keep going" after the adapter fixes. No HANDOFF decision.
- **What Claude did and how it was checked:** Claude Code moved hard-coded thresholds into config with sources
  (values unchanged), deleted four empty packages, aligned units-confidence labels with Raleigh and Durham, made the
  CSTX dedupe order-independent and made the app build check every template slot. Two "dead code" items from the
  subagent review were checked and kept (one reproduces a logged check, one is tested); the BPS end year was judged
  a data fact and left. Tests added for the label changes; full suite and compliance check run before the PR.
