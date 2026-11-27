### LB-NNN · 2026-11-25 · Review · CodeQL gate: escape page values read from embedded JSON (T6)

- **Question:** Can the five open high CodeQL alerts (`js/xss-through-dom`) be closed by fixing the code?
- **Outputs:** `src/lotline/dashboard/template.html`, `src/lotline/model/dashboard.html`,
  `reports/dashboard/index.html`, `reports/fees-phase2-run/fees-phase2-results.html`; `compliance_check.py` (the local
  T6 line says open alerts are only read with `--github`).
- **Decision:** Ben, 2026-11-25 (overnight): "go with your suggested order"; item 1. Merge left to Ben.
- **What Claude did and how it was checked:** Claude Code traced each alert to its source: every page parses its data
  with `JSON.parse(...textContent)`, which CodeQL treats as DOM text, so data values reached `innerHTML` unescaped.
  Tooltip rows, the parcel sources table, the backtest header and swatch, and the fee report's building-mix rows now
  escape (or `Number()`) every data value; the run picker resolves its id from RUNS. No local CodeQL, so the PR's
  CodeQL run is the check. Dashboard tests pass and every edited page's script passes `node --check`.
