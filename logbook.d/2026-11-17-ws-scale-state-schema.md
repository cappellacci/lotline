### LB-NNN · 2026-11-17 · Build: WS-SCALE task 2 (part 2), every state file checked against the schema
- **Question:** Do all five state settings files pass the schema and agree with the rest of the repo?
- **What I did:** `tests/config/test_state_schema.py`, parametrized over `all_states()` so a new state needs
  no test edit. Beyond pydantic's shape check, it tests that:
  - every GEOID in the file starts with the state's FIPS code and has a place, township or county length;
  - holdout ids name the state;
  - `parcel_sources` names real sources and has a `*` default;
  - named files exist and alias GEOIDs are in the state;
  - sources have a URL and license;
  - no two states share a FIPS code or a ZIP prefix.
- **Inputs:** `config/states/*.yaml`, `config/crosswalks/*_aliases.csv`.
- **Outputs:** `tests/config/test_state_schema.py`, `docs/build/workstreams/WS-SCALE.md` (task 2 ticked).
- **Findings:** all five pass (47 tests). Planting an NC GEOID in MN's `local_jurisdictions` fails the test.
- **Decisions:** none new. The `inputs:` block from issue #455 §5 stays unbuilt until task 8 decides it.
- **AI:** Claude wrote the tests and the mutation check.
- **Open / next:** task 1 (finish the audit).
