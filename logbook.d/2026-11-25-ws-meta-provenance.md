### LB-NNN · 2026-11-25 · Review · Results record whether the code was committed and which blind tests it has seen (A21, #506)

- **Question:** Can a reader of a results bundle tell whether it came from committed code, and whether it was
  built after a blind test on its state was scored?
- **Outputs:** `src/lotline/schemas.py` (schemas 1.24: `results_meta.tree_clean`, `post_test`, `post_test_note`);
  `src/lotline/model/results.py` (`tree_state`, `post_test`, filled in `build_bundle`); `docs/schemas.md`
  (regenerated); `src/lotline/app/template.html` (run-details rows); tests in `tests/model/test_results.py`;
  review row A21. Closes #506.
- **Decision:** Ben, 2026-11-25: "yup do A21 and 506 next" (a WS-CORE schema change, approved in chat). No HANDOFF
  decision.
- **What Claude did and how it was checked:** Claude Code added three optional meta fields, so older bundles still
  read. A hand-worked test lists a released statewide test at origin 2025 but not at 2019, and never a blind one; a
  test shows `tree_state` is null outside a repository. Wisconsin's bundle was rebuilt: `post_test` is
  V8-WI-TRANSFER with its note, and `tree_clean` is false (uncommitted edits at the time). The app was built from
  it and its scripts pass `node --check`. No result changes: only meta fields are added.
