### LB-NNN · 2026-11-26 · review · Review loose ends: schema-version check, percentile NaN, stale skip

**Question:** Can the app build mix in a bundle it can't read, can a missing draw value quietly turn into a
number on the page, and is the skipped D-025 test still needed?

**Outputs:**
- `src/lotline/app/build.py`: `check_schemas_version` refuses a bundle from another schema line or a newer
  version than the code, with a message saying to pull or rerun `lotline results`. Older bundles in the same
  line still load, as before.
- `src/lotline/app/aggregate.js` (`percentile`): a missing value (null) gave 0, and a NaN sorted last, so P10 could
  look fine while P90 was NaN. Now any missing value makes every percentile NaN, as numpy does.
- `tests/model/test_estimate_mm_fit.py`: the `D025_MODE_BUG` skip stays, and now cites issue #558.
- Tests in `tests/app/test_build.py` and `tests/app/test_aggregate_parity.py`.

**What Claude did:** Read the three review items, made the changes and wrote the tests. To check the skip, it
removed it and ran the test: after 12 minutes it was still running, so the bug is real and the skip stays.

**Checked:** `tests/app` and the MM fit tests: 108 passed, 2 skipped; ruff clean; compliance 0 FAIL.
