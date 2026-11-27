### LB-NNN · 2026-11-17 · Build: WS-SCALE task 4 (part 2), place_inputs as a fetch step (schemas 1.16)
- **Question:** Can `place_inputs` be built by `lotline fetch` like any other table, validated by a schema?
- **What I did:**
  - `PlaceInputs` schema (49 columns, one row per state, geoid, year), `SCHEMAS_VERSION` 1.16, history row,
    `docs/schemas.md` regenerated.
  - Registered `place_inputs` as a national build step; `RUN_LAST` makes a plain `lotline fetch` build it
    after every adapter (sources otherwise run in name order).
  - Guide: what the table is and where it sits in the rebuild order.
- **Inputs:** five states' processed tables (offline, read-only).
- **Outputs:** `src/lotline/schemas.py`, `src/lotline/registry.py`, `src/lotline/cli.py`,
  `src/lotline/build/place_inputs.py`, `docs/schemas.md`, tests, `docs/adding_a_state.md`.
- **Findings:** builds and validates for all five states over every BPS year (OR 5,712 rows, MN 35,802,
  NC 15,436, OH 32,368, TX 34,204; 3-43 s each). Not written to the shared data directory (Ben's call).
- **Decisions:** none new.
- **AI:** Claude wrote the schema, registration and tests; verified as above.
- **Open / next:** run `lotline fetch --source place_inputs` for the five states; owners' switch-over PRs.
