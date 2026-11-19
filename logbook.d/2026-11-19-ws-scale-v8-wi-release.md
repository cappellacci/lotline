### LB-NNN · 2026-11-19 · Validation: Wisconsin released from the V8 blind
- **Question:** Once V8 is scored, how does Wisconsin's full data become buildable without blurring the test?
- **What I did:** set `released_on: 2026-11-19` with a `released_note` on `V8-WI-TRANSFER` in
  `config/states/wi.yaml`, as for V5 and V9. The holdout filter then stops hiding Wisconsin's outcomes, and the
  test stays in the registry.
- **Outputs:** `config/states/wi.yaml`.
- **Decisions:** Ben 2026-11-19, "All as recommended": release Wisconsin; anything built afterwards is post-test.
  A Wisconsin permit adapter is allowed in a separate PR.
- **AI:** Claude made the edit. Checks:
  - `holdout.still_blind` returns nothing for Wisconsin;
  - the holdout and state-schema tests pass.
- **Open / next:** keep a blind copy of the Wisconsin processed tables before the first full rebuild, so V8
  can be re-run (as V9's `lotline-data-v9-blind`).
