### LB-NNN · 2026-11-17 · Build: WS-SCALE task 3 (part 1), one jurisdiction resolver
- **Question:** Can the five copies of "point's place, else township, else county" in the parcel adapters
  become one shared function without moving a single parcel's jurisdiction?
- **What I did:**
  - `geo.resolve(steps, known)`: an ordered list of `(how, geoids, must_be_known)` steps; the first usable
    GEOID wins and every row gets a `how` label. `geo.jurisdictions_table` / `geo.known_geoids` replace the
    per-adapter table loaders.
  - Rewrote `metc_parcels.resolve` (also used by Ramsey and MnGeo), `onemap_parcels.resolve_jurisdictions`
    (also Charlotte UDO), `stratmap_parcels`, `oh_parcels` and `rlis_parcels` as step lists. Function names
    and outputs unchanged; their existing tests pass unedited.
  - Synthetic tests (`tests/core/test_geo_resolve.py`): point in a place, in a township, outside both, on
    the shared border, an alias hit.
- **Inputs:** cached raw parcel snapshots in `LOTLINE_DATA_DIR` (offline, nothing downloaded or written).
- **Outputs:** `src/lotline/geo.py`, the five adapters, `tests/core/test_geo_resolve.py`,
  `docs/adding_a_state.md` step 8.
- **Findings:** Zero-difference check on cached raw data: each adapter's `load()` run offline, with every
  resolver call computed by both the old function (from git) and the new one on the same inputs. Results in
  the PR description (rows compared, GEOID and `how` differences per adapter).
- **Decisions:** none (mechanics only).
- **AI:** Claude wrote the resolver, the adapter changes, the tests and the check harness; checked as above.
- **Open / next:** aliases files, geography columns and side tables (task 3, part 2); `place_inputs` (task 4).
