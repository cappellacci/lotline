### LB-NNN · 2026-11-26 · review · Review loose ends: HUD year, TIGERweb layer check, FHFA folders, Actions by SHA

**Question:** Can a new HUD file, a renumbered TIGERweb service or an FHFA refresh quietly change inputs, and are
the CI actions pinned to fixed code?

**Outputs:**
- `src/lotline/adapters/national/hud_il.py`: the fiscal year comes from the file's `medianYYYY` column, else from
  the registered vintage folder (`fy2027`), so a FY2027 file is never labelled 2026 dollars.
- `src/lotline/adapters/national/tiger_boundaries.py`: `check_layer` refuses a layer whose name or vintage group
  ("ACS 2025") doesn't match, checked from the saved `layer.json` on every load.
- `src/lotline/adapters/national/fhfa.py`: `raw_vintage` saves each refresh under its pull date, and a plain run
  reads the newest saved copy (the old `current` folder still works), so a refresh never overwrites the file an
  earlier result used. `docs/data_provenance.md` regenerated.
- `.github/workflows/*.yml`: every action pinned to a commit SHA, with the version tag as a comment; Dependabot
  (github-actions) keeps them current.
- Tests in `tests/core/test_hud_il.py`, `test_tiger_boundaries.py` (new), `test_fhfa.py`, `test_geo.py`.

**What Claude did:** Worked items 6, 7 and 10 of the 2026-11-25 ingestion review and the Actions item; resolved
each action tag to its commit with the GitHub API. Checked a cached TIGERweb `layer.json` to confirm the fields.

**Checked:** fast test tier 2,902 passed, 2 skipped; ruff clean; compliance 0 FAIL; provenance current.
