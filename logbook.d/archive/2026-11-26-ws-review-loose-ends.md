### LB-NNN · 2026-11-26 · review · Code review loose ends: commit id without git, config GEOID guard, numpy

**Question:** Can someone run Lotline from a downloaded copy, and would a re-keyed place in config fail loudly?

**Outputs:**
- `src/lotline/model/results.py` (`commit_sha` fallback), `src/lotline/COMMIT`, `.gitattributes`.
- `src/lotline/build/jurisdictions.py` (`config_orphans`), plus `lotline unlisted` and the onboarding check.
- `pyproject.toml` / `uv.lock`: numpy declared directly.

**What Claude did:**
- `commit_sha` falls back from git to `LOTLINE_COMMIT`, then to a `git archive` stamp, then to all zeros.
- Config GEOIDs that the jurisdictions table lacks now fail the check if they are in fees or the state file's lists. Reform rows are only listed.
- Added numpy (BSD-3-Clause) as a direct dependency, approved by Ben in chat.

**Checked:**
- New unit tests.
- Fast suite: 2,846 passed.
- `git archive` fills the stamp with the commit id.
- `lotline unlisted` on real data lists only the 17 expected reform orphans (NC 2, OR 15).
