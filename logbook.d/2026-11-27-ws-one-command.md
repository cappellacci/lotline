### LB-NNN · 2026-11-27 · review · One command from clone to page, and plain errors

**Question:** Can a new user get from a clean clone to the page with one command, and does every common
mistake (unknown state, no data yet, no Census key offline, a hand-download source) say what to do next?

**Outputs:**
- `src/lotline/cli.py`:
  - `lotline run [--state XX] [--offline] [--skip-fetch] [--draws N]`: fetch, results, data tab and page,
    with "step n of 3" progress.
  - `lotline app [--no-data-tab]`: rebuilds the page (and the data tab) from the results already written.
  - `fetch` keeps going past a source that fails (missing cache, or a hand-download source), prints each
    source before it starts, and ends with a summary of what was skipped.
  - `results` checks the national tables first and names the fetch command.
  - An unknown state is one line listing the configured states.
  - `main` prints setup errors (Census key, offline cache, missing files) as one line, with `--debug` for
    the traceback.
  - Help text: plain words, a "start here" line, and main and maintenance commands named. `provenance
    --check` (a no-op) is gone.
- `src/lotline/io/store.py`: `.env` is read from the working directory, then the checkout, so commands work
  from any folder.
- `src/lotline/adapters/national/acs.py`: an offline build needs no Census key.
- `src/lotline/onboarding.py`: `missing_national_tables`.
- `README.md`: status line and the command contract's Run row (`uv run lotline run --state MN`).
- Tests: `tests/core/test_cli_run.py` (new); `test_results.py` and `test_offline.py` updated.

**What Claude did:** Worked findings 2-7 and 15 of the 2026-11-27 usability review. Ran `lotline run
--state WI --skip-fetch --draws 100` and `lotline app` on the cached data: both built the page, about 90 s.

**Checked:** fast tier 2,837 passed, 2 skipped (#558); ruff clean; compliance 0 FAIL.
