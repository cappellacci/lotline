### LB-NNN · 2026-10-18 · Build: Registering hand-downloaded files; superseding abandoned queries
- **Question:** How do files that can only be downloaded in a browser (Travis CAD rolls behind a bot challenge; the Minneapolis and St. Paul manual exports, #9) enter the manifest, and how is a replaced query's intact raw folder kept out of provenance?
- **What I did:** Added `lotline manifest register <file> --source --url --license [--vintage]` (`DataStore.register`): links the file (or copies it across file systems) to `raw/<source>/<vintage>/`, records its sha256 with `adapter=manual_export` and the file's save time, refuses a different file under the same name and is a no-op when repeated; `DataStore.registered(source)` lists them for adapters. Added `--abandoned` to `lotline manifest supersede`, which also marks intact files but only with `--path`, for the pages of a query that was replaced (Columbus's first pull, `q-f0979caf`).
- **Inputs:** WS-TX and WS-OH round-1 reports (2026-10-15).
- **Outputs:** `src/lotline/io/store.py`, `src/lotline/cli.py`, `tests/core/test_manifest_register.py`.
- **Findings:** none beyond the design.
- **Decisions:** Ben, 2026-10-18, on the WS-OH questions: keep Columbus permits' repeated project totals and unit typos as reported for now; look for a Columbus ADU source; spot-check a sample of reform rows; leave the apartment code 401 (4-19 units → MF5) mapping as it is.
- **AI:** Claude Code (WS-CORE) wrote the change and 4 tests; 379 tests pass.
- **Open / next:** after OH #104 merges, supersede `q-f0979caf` with `--abandoned` and regenerate provenance.
