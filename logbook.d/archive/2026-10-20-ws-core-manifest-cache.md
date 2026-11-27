### LB-NNN · 2026-10-20 · Build: Manifest read incrementally (cached reruns no longer re-read the whole log)
- **Question:** Why does a rerun of Ohio's statewide parcels from cache take ~45 minutes of CPU?
- **What I did:** `DataStore.manifest()` and `supersessions()` re-read and re-parsed the whole append-only log on every call, and the pagers call it once per cached page (17,270 entries now). They now parse only the lines added since the previous call (cache keyed by path, checked by inode and size), leave a half-written trailing line for the next call, and re-read a replaced file in full. Test added.
- **Inputs:** WS-OH's report on the Ohio rerun (#150).
- **Outputs:** `src/lotline/io/store.py`, `tests/core/test_io.py`.
- **Findings:** On the real manifest: first read 0.1 s; 200 further lookups 0.3 s in total.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) wrote the change and test; all tests pass.
- **Open / next:** none.
