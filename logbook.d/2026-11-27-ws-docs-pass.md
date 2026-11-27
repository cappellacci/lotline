### LB-NNN · 2026-11-27 · docs · Docs pass in Ben's voice after the review and modularity work

**Question:** Do the user docs match what the code does today, read in Ben's voice, and hold no internal notes?

**Outputs:**
- `README.md`: `lotline run` as the main path, the live link, node for the app tests, a Validation section, and
  corrected calibration step counts (18 rerun from data; 132 fitted values).
- `docs/model_and_assumptions.md`: rewritten outside the generated parameter table.
  - Built parts are no longer "planned".
  - Fixed the outcome wording, the window (2027–2031), `adu_partial_rule_share` 0.7, D-025's status, the
    elasticity's 95th percentile, the missing-middle values after the 11-26 refit and φ as a variance.
  - Updated the ADU method values and switched the boundaries to TIGER/Line.
  - The results table now comes from app-2026-11-27.
- `docs/policy_scenario_comparison.md`: three empty required sections written from app-2026-11-27, with every
  result shown as a midpoint and its P10–P90 range. The range-driver shares were recomputed from the new
  bundles.
- `docs/adding_a_state.md`, `docs/adding_local_rules_with_agents.md`, `config/onboarding/steps.yaml`:
  - matched to `lotline run`, `lotline app` and `lotline validate`, and to the saved ADU priors (missing
    middle still borrows from the five states' tables);
  - corrected the code references;
  - removed "Ben's call" and other internal steps.
- `docs/data_availability.md`, `docs/disclosures.md`, `docs/calibration.md`, `docs/data_dashboard.md`, and the
  `scripts/archive/` and `scripts/dev/` READMEs: current facts and counts, the AI disclosure, and the external
  services.
- `src/lotline/app/template.html`: the in-app guide and the footer name `lotline app` and `lotline run`. Test
  updated in `tests/app/test_build.py`.

**What Claude did:**
- Wrote a style sheet from Ben's own rewrites in earlier sessions.
- Ran four drafting agents on separate files.
- Reviewed every draft: LLM-ism sweep, numbers against the bundles and config, every `lotline` command
  checked against the CLI, and the bold-lead bullets in the scenario comparison rewritten as prose.

**Checked:** tests/app and onboarding tests pass; compliance 0 FAIL (D4 warns about page length).
