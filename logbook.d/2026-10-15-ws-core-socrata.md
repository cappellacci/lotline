### LB-NNN · 2026-10-15 · Build: Socrata pager for city permit portals
- **Question:** Can TX and OH load Socrata-hosted permits (Austin `3syk-w9eu`, Cincinnati `uhjb-xac9`) through the same cached, logged IO layer as ArcGIS sources?
- **What I did:** Added `lotline.io.socrata.download_dataset`: SODA paging with `$limit`/`$offset` ordered by the row id `:id`, an overlap check on every page, the dataset description saved as `dataset.json`, and each query's pages in their own `q-<hash>` folder (shared `query_folder`, moved to `io/store.py`). `select` is required, so no adapter downloads every column by default (Austin's dataset holds contractor and applicant names and phone numbers). SODA error messages are surfaced. An optional `SOCRATA_APP_TOKEN` is sent but never logged.
- **Inputs:** Austin Issued Construction Permits metadata and a one-week query.
- **Outputs:** `src/lotline/io/socrata.py`, `src/lotline/io/store.py`, `src/lotline/io/arcgis.py`, `tests/core/test_socrata.py`, `.env.example`.
- **Findings:** Live check: 1,195 Austin permits issued 2024-03-04 to 03-10 in 3 pages of 500 (2.9 s); an identical rerun came from cache (4 manifest entries). `permit_class` mixes coded labels ("R- 101 Single Family Houses") with plain ones ("Residential"), which WS-TX must map. A first version could loop forever if a server repeated full pages; overlap is now checked page by page.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) wrote the pager and 8 tests on a fake SODA server; 383 tests pass; live check in a scratch data folder.
- **Open / next:** a CKAN helper only if a source needs more than `fetch()` of a resource URL (San Antonio's CSVs don't).
