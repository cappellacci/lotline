### LB-NNN · 2026-11-11 · `core` · Offline rebuilds from cached raw snapshots
- **Question:** how do we rebuild processed tables after a code change without re-downloading every ArcGIS
  layer? On 2026-11-11 a five-state rebuild that only needed reprocessing re-downloaded about 4,700 files
  (~3.5 GB; NC OneMap alone 1.4 GB), because the ArcGIS pager's default vintage is today's date and its cache
  only works within one vintage. It also mixed new data into a code-change before/after comparison.
- **Decided by:** requested by the five-state rebuild session; WS-CORE contract change, flagged in the PR.
- **Outputs:**
  - `src/lotline/io/offline.py` (new): `offline_build(store)` context, snapshot selection, build records in
    `manifest.builds.jsonl`, `prune_candidates()` (lists only).
  - `src/lotline/io/arcgis.py`, `src/lotline/io/socrata.py`: offline reads the newest complete cached snapshot
    of the same `q-<hash>` query; incomplete ones (pages missing against their own `layer.json` /
    `object_ids.json` / short-page rule) are skipped with a note; pages are never mixed across snapshots.
  - `src/lotline/io/http.py`: offline `fetch()` returns the cached copy of a URL (or the newest current copy in
    another dated folder) and never sends a request; `client()` refuses every request while offline.
  - `src/lotline/cli.py`: `lotline fetch --offline`; `lotline manifest prune-candidates` (dry run).
  - `tests/core/test_offline.py` (16 tests, synthetic fixtures); README "Data" section.
- **What Claude did and how it was checked:**
  - Wrote the code and tests. The no-network tests patch `httpx.Client.send` to fail the test; bypassing the
    offline branch in `arcgis.py` made 8 of them fail, so the guard bites.
  - Full `pytest` and `python compliance_check.py` (0 FAIL). Ran `lotline manifest prune-candidates` read-only
    on the real data dir: 2,020 older snapshot folders (9.63 GB) repeated by newer vintages. Nothing deleted.
  - Did not run an offline rebuild on real data (the five-state rebuild was using the data dir).
- **Open:** adapters that call the network directly (Rochester's folder listing, St Paul V5 archive, Charlotte
  UDO translation) fail loudly offline rather than reading a cache; holdout filtering is unchanged (it runs in
  each adapter's `load()` and `assert_no_leak` still runs in the CLI).
