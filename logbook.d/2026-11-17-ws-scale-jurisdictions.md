### LB-NNN · 2026-11-17 · Build: WS-SCALE, jurisdictions list without adapter output (straight-line build)
- **Question:** Can the list of governments be built from Census data and the state file alone, so adapters
  and the list no longer depend on each other and no hand rerun is needed?
- **What I did:**
  - Explained to Ben why the build was circular (the list read permit and parcel tables to find governments
    the Census permit survey files under a county; the adapters read the list to tag records). Ben chose the
    straight line, then (after a count showed the full Census list would add ~3,200 rows and move results)
    to write today's 220 extra governments down once.
  - `local_jurisdictions` (GEOID: name) in `config/states/{mn,nc,oh}.yaml` (23, 196, 1), generated from the
    built table's `in_bps = false` rows minus holdouts. `jurisdictions.local_geoids` reads only that list and
    the non-statewide holdouts.
  - `lotline unlisted [--state XX]` (`jurisdictions.unlisted`): GEOIDs the permit and parcel tables use that
    the list lacks.
  - Guide: step 2 key, the rebuild order in step 10.
- **Inputs:** cached Census and processed tables (offline, read-only).
- **Outputs:** `src/lotline/build/jurisdictions.py`, `src/lotline/config/__init__.py`, `src/lotline/cli.py`,
  the three state files, `tests/core/test_jurisdictions.py`, `docs/adding_a_state.md`.
- **Findings:** Rebuilt offline in memory, the jurisdictions table is identical to the one on disk for all
  five states (rows and every column). `lotline unlisted` finds 2 Met Council GEOIDs (139 permit rows,
  2010-25) that are not 2020 Census places or townships; the old build skipped them too, so nothing changes,
  but those permits are never counted (open question for Ben).
- **Decisions:** Proposed HANDOFF: "The jurisdictions list is the Census permit survey, the holdouts and each
  state file's `local_jurisdictions`; it reads no adapter output (Ben, 2026-11-17)."
- **AI:** Claude wrote the change, tests and checks; verified as above.
- **Open / next:** data tiers still come from parcels (one-way, does not change the list); the 2 Met Council
  GEOIDs; place tags in `place_inputs`; aliases.
