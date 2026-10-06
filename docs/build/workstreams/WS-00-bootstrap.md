# WS-00 · Repo bootstrap (Phase 0)

**Deadline:** merged and pushed **before Oct 7, 9:00 a.m. ET** (aim for Oct 6 evening). See BUILD_PLAN §0.
**Instance:** one Claude Code session in `~/Engineering/lotline` on branch `ws/bootstrap`. Ben has already created the GitHub remote **`https://github.com/cappellacci/lotline`** (BUILD_PLAN §7.1).

**Before any push:** run `git remote get-url origin` and `gh repo view --json owner -q .owner.login`. Both must point to `cappellacci`. If they don't, stop and ask Ben. Never create a repo or push to another account or organization.
**Owns:** repo root files, `.github/`, `pyproject.toml`, `uv.lock`, empty package skeleton, `scripts/dev/`, `logbook.d/`.

## Read first
`CLAUDE.md`, `HANDOFF.md` §3 (the T-gates), `docs/build/BUILD_PLAN.md` §3–4, `compliance_check.py`.

## Tasks
- [ ] 0. Confirm the owner check above passes.
- [ ] 1. **First commit on `main`** of the existing scaffold and research docs, as-is, so the history starts inside the registration period. Message: `Initial scaffold and research (created 2026-09-14 onward)`. Push.
- [ ] 2. Branch `ws/bootstrap`. Create `pyproject.toml`:
  - project `lotline`, `requires-python = ">=3.12"`, src layout;
  - minimal runtime deps for week 1: pandas, pyarrow, duckdb, httpx, pydantic, pyyaml, pandera;
  - dev deps: pytest, ruff, pip-licenses.
  
  Run `uv lock`. Commit `uv.lock`.
- [ ] 3. Package skeleton matching BUILD_PLAN §4: empty `__init__.py` files and a one-line docstring per module saying what it will hold. No logic yet. Add `src/lotline/cli.py` with a `lotline --version` command (entry point in pyproject).
- [ ] 4. `tests/test_smoke.py`: imports the package and checks the version. Makes T4 real.
- [ ] 5. `scripts/fetch_data.py`: stub CLI wrapper (`lotline fetch --state XX --source YY`) that prints "no sources registered yet". Satisfies the T10 path in `challenge.toml`.
- [ ] 6. Update `challenge.toml`:
  - `commands.setup = "uv sync --frozen"`;
  - `commands.test = "uv run pytest -q"`;
  - `repo_url = "https://github.com/cappellacci/lotline"` (already set; verify);
  - leave `state` empty (benchmark state not chosen).
  
  Put both commands in the README "Setup" and "Tests" sections.
- [ ] 7. Fix `.github/workflows/compliance.yml` for uv:
  - install uv (`astral-sh/setup-uv`);
  - run `uv sync --frozen`;
  - run the license scan inside the venv (`uv run pip-licenses ...`, or call `compliance_check.py --deps` via `uv run` so `pip-licenses` is found).
  
  Add a `tests.yml` workflow (`uv run pytest -q`, `uv run ruff check`).
- [ ] 8. Add `.github/dependabot.yml` (pip/uv + github-actions, weekly). Add the CodeQL default setup note in the README (Ben enables it in Settings).
- [ ] 9. `.gitignore`: add `results/` except `results/frozen/`, `reports/**/*.parquet`, and `~/lotline-data` (lives outside the repo; just document `LOTLINE_DATA_DIR` in `.env.example`).
- [ ] 10. `docs/disclosures.md`: add certifi (MPL-2.0, via httpx) with the justification "CA bundle only, unmodified, not distributed in our code". Add "Claude Code" under AI tools.
- [ ] 11. Create `logbook.d/README.md` (fragment format = the LOGBOOK entry template) and `scripts/dev/merge_logbook.py` (folds `logbook.d/*.md` into `LOGBOOK.md`, numbering LB-NNN in date order, then deletes the fragments).
- [ ] 12. Check `scripts/dev/create_issues.py` (already written by Cowork) runs in dry-run mode.
- [ ] 13. Run `python compliance_check.py --run`. Fix everything fixable. Open PR → CI green → Ben merges → push. **Confirm the push time is before Oct 7, 9:00 a.m. ET.**

## Acceptance
- `uv sync --frozen && uv run pytest -q` passes on a clean clone.
- `compliance_check.py --run` has 0 FAIL. WARN is acceptable for SBOM (exported at the end) and for GitHub settings checks that need a token.
- Repo is public; secret scanning, push protection, Dependabot alerts and CodeQL are enabled by Ben.

## Out of scope
Any data download, schema, or model code. Those start Oct 14.
