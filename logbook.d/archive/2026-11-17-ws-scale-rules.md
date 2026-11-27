### LB-NNN · 2026-11-17 · Build: WS-SCALE task 8 (part 1), adapter rules as data
- **Question:** Can a state's adapter judgments sit in its settings file, named and sourced, with no change
  to any output?
- **What I did:**
  - `AdapterRule` and a `rules:` block in the state schema, with `value`, `unit`, `what`, `assumption`,
    `source`, `used_by` and an optional `low`/`high`. `state_rule(state, id)` reads one.
  - Ohio, three rules from the audit, each copied in two or three files:
    - `district_jurisdiction_share` 0.95;
    - `adu_repeat_days` 730;
    - `county_min_share` 0.99.
  - Texas, two rules: `austin_home_start` 2024-02-05 (was written in two modules) and
    `austin_home_two_unit_use`.
  - `nc/onemap_codes.py` reads its tier cutoffs from `config/params/tiers.yaml` instead of copying them.
- **Check:** all 12 module constants keep the same value and type, so no output can change. New tests check
  that each rule's `used_by` modules exist and read it, and that ranges are checked.
- **Outputs:** `src/lotline/config/__init__.py`, `config/states/{oh,tx}.yaml`, five adapters,
  `build/permit_theme.py`, `tests/config/test_state_schema.py`, `docs/adding_a_state.md` step 8.
- **Decisions:** none. No rule has a sensitivity range yet, because none has a source for one. Austin's rule is
  all or nothing, so a low/high share would be a method change (raised with Ben).
- **AI:** Claude wrote the schema, moves and tests.
- **Open / next:** the rest of `docs/build/ws-scale-audit.md` § 2 (MERGE 0.20, Durham, Cincinnati, ...).
