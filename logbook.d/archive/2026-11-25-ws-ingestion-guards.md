### LB-NNN · 2026-11-25 · Review · Ingestion guards: no HTML pages saved as data; no silent empty baseline

- **Question:** Which silent ingestion failures from the nightly review can be turned into clear errors cheaply?
- **Outputs:** `src/lotline/io/http.py` (`HtmlNotDataError`, `allow_html`); `src/lotline/rule_agents/common/fetch.py`
  (opts in: ordinance pages are HTML); `src/lotline/model/baseline.py` (`forecast_draws` raises when the panel has no
  origin-year rows); tests in `tests/core/test_io.py` and `tests/model/test_baseline_model.py`.
- **Decision:** Ben, 2026-11-25 (overnight): "go with your suggested order"; item 4. Left for later: `commit_sha`
  without git (would collide with open #533), and a check that GEOIDs named in config survive a new BPS year.
- **What Claude did and how it was checked:** the HTML test is decided by the body (an HTML tag first, or any tag
  under a `text/html` header), not the header alone; a scan of all 30,658 cached raw data files found none that
  would be refused. Tests cover a block page, an HTML-labelled CSV that is kept, and an origin year past the data.
  `tests/core/test_io.py`, `tests/rule_agents` and the baseline and backtest tests pass; ruff clean.
