### LB-NNN · 2026-11-09 · `app` · The results page labels the five-year window 2027–2031 (D-061)

- **Question:** why does the page say 2026–2030 when D-061 moved the window to 2027–2031, and where else
  does it print years?
- **Outputs:**
  - `src/lotline/app/aggregate.js`: `windowLabel(bundle)` reads the window from the bundle's multi-year
    `totals.period` ("2027-2031") and returns it with an en dash, or null when no such row exists.
  - `src/lotline/app/template.html`: the results lead and the headline eyebrow use `AGG.windowLabel(b)`
    instead of `origin_year + 1 … origin_year + horizon_years`, which ignored the lead year; with no
    window in the bundle they print no years rather than a guess. No schema change (meta has no lead year).
  - `tests/app/test_window_label.py`: the fixture (origin 2025) labels 2027–2031, agreeing with
    `baseline.window_label`; no multi-year row gives null; the page no longer works the window out from meta.
- **What Claude did and how it was checked:** found the only year label (used twice); the funnel and
  share-of-need cards print no years and the page has no per-year chart. The new page test failed on the
  old template and passes on the fix; `pytest tests/app` 38 passed; `compliance_check.py` 0 FAIL. Rebuilt the
  page from `tests/fixtures/results/zz/bundle.json` and read it in the in-app browser: both labels show
  2027–2031. Follows up the issue spotted in the missing-middle bundle fragment (2026-11-09-ws-mm-bundle).
