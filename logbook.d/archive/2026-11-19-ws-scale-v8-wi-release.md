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
- **Blind copy (Ben 2026-11-19, "All as recommended"):** saved `~/lotline-data-v8-blind` before any full
  Wisconsin rebuild, as for V9. It holds:
  - `processed/WI` copied, with the five input tables' SHA-256 checked equal to the frozen file;
  - `manifest.jsonl` copied;
  - `raw` and `manual` linked to the shared folder.
  V8's scripts are rerun with `LOTLINE_DATA_DIR=~/lotline-data-v8-blind`.
- **Open / next:** full Wisconsin rebuild only after this merges.
