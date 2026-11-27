### LB-NNN · 2026-11-26 · review · Ingestion guards: BPS re-key report and rolling-window permit layers

**Question:** When Census gives a permit ID a new GEOID, or a city permit layer rolls old permits out, does
anyone find out?

**Outputs:**
- `src/lotline/adapters/national/bps.py`: `rekeys` lists every building-permit ID whose GEOID changed (old
  GEOID, its years, the new GEOID). `load` writes it to `interim/<st>/bps_rekeys.csv` after the holdout filter,
  so it never names a hidden place-year, and prints a note when there are any.
- `src/lotline/cli.py`: `lotline unlisted` prints each re-key and asks for config naming the old GEOID to be
  checked.
- `src/lotline/adapters/snapshots.py` (new): `all_snapshots` reads every complete cached snapshot of a layer
  (from disk only) and `newest_rows` keeps each permit's newest copy. Used by `mpls_permits` and
  `stpaul_permits` (St. Paul after its holdout filter), so permits that roll out of the live layer are kept.
- Tests: `tests/core/test_bps.py`, `tests/core/test_snapshots.py` (new). `docs/data_provenance.md` regenerated.

**What Claude did:** Worked items 2 and 3 of the 2026-11-25 ingestion review. Ran both on the cached data:
- Re-keys: MN 4 (Baldwin, Nowthen, Minnetonka Beach, Elko New Market), OH 3 (Champaign County unincorporated,
  Waverly, West Carrollton). Minnetonka Beach: filed as 2743270 in 2007-2023, its history now sits under
  2767130; `config/states/mn.yaml` still lists 2743270 under `local_jurisdictions` (raised with Ben, not
  changed).
- Snapshots: Minneapolis 130,726 and St. Paul 86,593 permits, the same as the newest snapshot alone (nothing
  has rolled out between the cached snapshots yet). Minneapolis's 2026-10-14 snapshot used an older query and
  is skipped with a note.

**Checked:** fast tier 2,902 passed, 2 skipped; ruff clean; compliance 0 FAIL; provenance current.
