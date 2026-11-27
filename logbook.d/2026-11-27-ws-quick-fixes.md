### LB-NNN · 2026-11-27 · review · Pre-release quick fixes from the four-angle review of main

**Question:** Which small problems would trip a judge or a new-state analyst on a clean clone, now or in a
year, and can they be fixed without touching the models?

**Outputs:**
- `pyproject.toml`, `.github/workflows/*.yml`: uv needs `>=0.13.5` only (the `<0.14` cap would stop every
  command once uv 0.14 ships); CI pins uv 0.13.5 in setup-uv instead.
- `src/lotline/io/filelock.py` (new) and its users (`io/http.py`, `rule_agents/common/fetch.py`,
  `docstore.py`): one cross-platform file lock, so the package loads on Windows (no top-level `fcntl`).
  `tests/core/test_filelock.py` fails if any module imports `fcntl` at top level again.
- `src/lotline/model/results.py`: `config_hash` uses POSIX relative paths, the same on every platform.
- `src/lotline/validation/v9.py`: `AS_OF = 2026-11-05` (the freeze commit's date) replaces today's date, so a
  rerun of the V9 freeze after 2027-01-15 still counts the same rules.
- `src/lotline/cli.py`: `lotline results --all` builds the page from this run's bundles only (a failed state's
  old bundle no longer reaches the page), builds no page when every state fails, resolves paths from the repo
  root, and drops the stale "PR #313" guard. Tests in `tests/model/test_results.py`.
- `src/lotline/app/template.html`: no dated internal note on the slider card; "engine" becomes "model" in
  visible text; the home page's first sentence is fixed; a caption under the results chart explains the log
  scale and why the headline is not the three midpoints added; a load error tells visitors to reload, with the
  rebuild hint only on a local `file:` page and in the console.
- `config/onboarding/steps.yaml`, `docs/adding_a_state.md`: the first run no longer calls the fee dev script
  (fees are in the bundle); `onboarding.py`'s unlisted-GEOID check reads "todo" with no jurisdictions table.
- Archived: `adapters/states/mn/denominators.py` → `scripts/archive/mn_denominators.py` (test removed);
  the three `rule_agents/mm` re-export shims (`dates`, `access`, `pdftext`) removed, callers import
  `rule_agents.common` directly.

**What Claude did:** Ran four read-only review agents on main (modularity, ease of use, long-term stability,
tests and correctness; reports kept outside the repo), checked their top findings against the code, and made
the fixes above. Model-owned findings went to the ADU and MM sessions (net-new equation copy, borrowed priors
to `config/priors/`, archiving research modules, the MM Pencils test), with Ben's approval.

**Checked:** fast tier 2,869 passed, 2 skipped (#558); `tests/app` 88 passed; ruff clean; compliance 0 FAIL.
A `.gitattributes` LF rule for `config/` was tried and dropped: `config/validation/adu_roll_counts.csv` has
CRLF endings and renormalizing it would change a calibration input's bytes; left for the model owner.
