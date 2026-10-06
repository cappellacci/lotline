# WS-CORE · Contracts, plumbing, national adapters (week 1, then contract maintainer)

**Start:** Oct 14, 9:01 a.m. ET. **Target:** tag `schemas-v1` by Oct 17–18; all of the below by Oct 20.
**Owns:** `src/lotline/{schemas.py,config/,io/,cli.py}`, `src/lotline/adapters/national/`, `src/lotline/validation/holdout.py`, `src/lotline/build/eligible.py` (rule skeleton only), `tests/core/`, `config/states/*.yaml` (structure + holdouts only; state instances fill in the sources).

## Read first
- `docs/build/BUILD_PLAN.md` §4–5 (contracts are specified there)
- `docs/research/lotline-statistical-protocol.md` §5
- `docs/research/lotline-validation-plan.md` §2–3

## Tasks
- [ ] **Schemas (`schemas.py`).** pandera models for the seven canonical tables in BUILD_PLAN §5.1, with the `building_type_std` enum. Version constant `SCHEMAS_VERSION = "1.0"`. Contract test helper `assert_conforms(df, table)` that any adapter test can call.
- [ ] **Config.** pydantic models:
  - state config: sources (name, url, licence, access method, cadence), land-use crosswalk path, tier rules, `train_until` per place, holdouts;
  - parameter files: value/low/high/unit/source/notes.
  
  Loader validates on read.
- [ ] **IO.**
  - `LOTLINE_DATA_DIR` resolution;
  - raw / interim / processed paths;
  - download-with-cache (ETag / Last-Modified, sha256);
  - an append-only `manifest.jsonl` writer;
  - **ArcGIS REST pager** (handles `maxRecordCount`, `resultOffset`, `objectIds` fallback, `exceededTransferLimit`, rate limiting);
  - **Socrata SODA pager**;
  - CKAN resource download;
  - polite retries;
  - user-agent naming the project.
- [ ] **Provenance.** `lotline provenance --write` regenerates `docs/data_provenance.md` from the manifest plus each adapter's metadata (source, version, access date, licence, cleaning steps, limitations). `--check` fails if any processed table lacks a row.
- [ ] **Holdouts** (BUILD_PLAN §5.4):
  - registry read from state configs; a loader filter on by default;
  - `--unblind` requires `results/frozen/<test_id>.json` committed on `main` (check with `git merge-base --is-ancestor`);
  - tests prove holdout rows never leak.
  - **Pre-fill:**
    - MN: St. Paul, outcome years 2024–2026, test `V5-MN-STPAUL`;
    - NC: Charlotte, outcome dates 2023-06-01 onward, test `V5-NC-CHARLOTTE`.
- [ ] **National adapters**, each with a contract test on a small fixture plus a live smoke test marked `@pytest.mark.network` (skipped in CI by default):
  - **Census BPS** place and county annual files, 1990s–2025. Keep `reported` vs `imputed`. Handle universe changes since 2023. → `bps_place_year`.
  - **ACS 5-year:** B25024, B25003, B25064, B25077, B25034 for places, counties and tracts (needs `CENSUS_API_KEY`). Keep margins of error.
  - **FHFA HPI:** state, CBSA, county, ZIP5, tract annual.
  - **FRED:** MORTGAGE30US (annual average).
  - **BLS PPI** WPUIP2311001 (FRED mirror is fine).
  - **Census geographies:** places, county subdivisions (MN and OH townships matter), counties, and the BPS-ID ↔ GEOID crosswalk → `jurisdictions`.
- [ ] **CLI:**
  - `lotline fetch --state XX [--source]`
  - `lotline build --state XX`
  - `lotline validate --state XX --step V0`
  - `lotline provenance`
  
  `scripts/fetch_data.py` delegates to it.
- [ ] **Eligible-parcel rule skeleton** (`build/eligible.py`): function signature, tier logic and a parameterized lot-size floor. State crosswalks plug in later.
- [ ] **V0 report scaffold** (`validation/v0.py`): coverage table (rows, years, null rates per column), BPS reconciliation chart, licence list. Writes `reports/<state>/V0.md`.
- [ ] Run BPS + ACS + FHFA for MN, NC, TX, OH end to end. Commit the generated `reports/*/V0-national.md` (small markdown only).
- [ ] Tag `schemas-v1`. Post a "contract freeze" note in the PR. Unblock WS-MN, WS-NC, WS-ENGINE.

## After week 1
Maintain contracts. Answer `contract-change` issues within a day. Bump the schemas version with a migration note.

## Acceptance
- Contract tests pass.
- National data for all four states builds from a clean `LOTLINE_DATA_DIR` with one command.
- The holdout leak test passes.
- `docs/data_provenance.md` is generated.
- CI is green.

## Gotchas
- BPS place IDs ≠ Census GEOIDs (crosswalk needed).
- BPS imputed rows must be flagged, not dropped.
- ACS 5-year windows overlap, so don't difference adjacent years.
- FHFA sub-county indexes are "developmental" and may be suppressed for thin tracts.
