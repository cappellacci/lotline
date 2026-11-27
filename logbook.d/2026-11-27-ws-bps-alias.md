### LB-NNN · 2026-11-27 · Data: a BPS ID alias keeps Minnetonka Beach's permit history on its own GEOID
- **Question:** how do we stop the BPS backfill from moving a place's whole history to a wrong GEOID in the
  latest file, without a special case in `bps.py`?
- **What I did:**
  - The problem came from #563's re-key report. BPS ID 27501400 (Village of Minnetonka Beach, MN) is filed as
    2743270 in 2007-2023 and as 2767130, another place, in the latest file. `backfill_geoids` moves every
    year to the latest GEOID. So Minnetonka Beach had local permits but no BPS series, and 2767130 got a
    series that isn't its own.
  - `bps.load` now applies `bps_id` aliases from `config/crosswalks/<st>_aliases.csv` (source `bps`, field
    `bps_id`; `id_aliases`, `apply_id_aliases`) before the backfill, from 1992 on, when IDs link years.
  - New file `config/crosswalks/mn_aliases.csv` holds one row: 27501400 → 2743270.
  - The other re-keys in the report are left alone (Baldwin, Nowthen and Elko New Market in MN; three in OH).
- **Decision:** Ben (2026-11-27) said to build the alias on top of #563, not to add a special case.
- **Outputs:** `src/lotline/adapters/national/bps.py`, `config/crosswalks/mn_aliases.csv`, a hand-worked test
  in `tests/core/test_bps.py`, and MN added to the aliases-file test. PR stacked on #563 (branch
  `ws/bps-alias`).
- **AI:** Claude Opus 5.5 wrote the hook and the test. To check it, MN's BPS, jurisdictions and place inputs
  were rebuilt offline into a copy of the data store, and MN results were compared before and after (see
  the PR).
- **Open / next:** the missing-middle session reruns MN once this merges.
