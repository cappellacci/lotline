### LB-NNN · 2026-11-27 · review · The headline, tested by what it shows

**Question:** If the page's headline used the wrong percentile, or the browser's arithmetic drifted from
Python's, would a test fail?

**Outputs:**
- `tests/app/need_card_harness.js`: a "hero" mode runs the page's `heroUpdate` under node and returns the
  headline line and note.
- `tests/app/test_need_card.py`: the headline is checked against P50 of the reforms summed run by run, and
  the note against that sum's P10 and P90, for both fee views.
- `tests/app/test_aggregate_parity.py`: JS against Python with an overlap share on half the draws.
- `src/lotline/model/aggregate.py`: `headline_kind` needs growth's whole range positive (the need table's
  rule), so a range crossing zero no longer leaves the table with no headline row. Test in
  `test_aggregate_need.py`.
- `src/lotline/app/build.py`: `check_draws_line_up` refuses a bundle whose scenarios have different draw
  ids, instead of the page quietly trimming to the shortest. Test in `test_build.py`.
- `tests/app/conftest.py`: a closing note when node is missing and the app tests were skipped.

**What Claude did:** Worked tests-review findings 1, 4, 10, 11 and 12 (2026-11-27).

**Checked:**
- Each new test was mutation-checked by hand:
  - the headline at P60 fails both headline tests;
  - P50 in place of P10 fails the range test;
  - `1 + overlap` in the JS fails the overlap test.
- All six bundles in release app-2026-11-24f pass the draw check.
- The headline kind is unchanged for every configured state.
- Fast tier passed; ruff clean; compliance 0 FAIL.
