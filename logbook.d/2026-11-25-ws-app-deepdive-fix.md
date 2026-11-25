### LB-NNN · 2026-11-25 · Review · Model page deep dives restored after the A30 caption change (thread 17, A31)

- **Question:** Why did the Model page's ADU and missing-middle state-by-state sections stop rendering?
- **Outputs:** `src/lotline/app/template.html` (`drawDeepDive`, `mmDeepDive`); test
  `test_every_window_label_call_on_b_sits_in_a_function_that_takes_b` in `tests/app/test_window_label.py`; review
  row A31.
- **Decision:** none needed (a regression fix); merge left to Ben.
- **What Claude did and how it was checked:** the nightly brittleness review (a Claude Code subagent) served the app
  from the test fixture and saw "ReferenceError: b is not defined" in `mmDeepDive`. Claude Code confirmed that #529
  (A30) had replaced a literal window with `AGG.windowLabel(b)` in two functions that hold only `bs`, switched both to
  `bs[0]`, and added a static test; the test fails on `main`'s template and passes with the fix. App tests pass.
