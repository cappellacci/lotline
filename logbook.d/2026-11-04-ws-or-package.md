### LB-NNN · 2026-11-04 · WS-OR: Oregon adapter package name
- **Question:** `or` is a Python keyword. What do we name the Oregon adapter package so the registry, tests and sibling imports all work?
- **What I did:** Claude Code (WS-OR worktree) read the registry and every place that turns a state code into a path. The registry tags sources with `st.name.upper()`, and the config loaders, the store (`interim/or/`, `processed/or/`) and the dashboard use `state.lower()`, so a mapped name like `oregon` would need a CORE change in the registry and would break the one-name convention. Kept `or`: adapters import siblings relatively (`from . import x`); tests and scripts use `importlib.import_module`. No contract change needed.
- **Inputs:** `src/lotline/registry.py`, `src/lotline/config/__init__.py`, `src/lotline/io/store.py`, `docs/build/workstreams/WS-OR.md` (Gotchas).
- **Outputs:** `src/lotline/adapters/states/or/__init__.py` (the two import rules), `tests/states/or/__init__.py`, `tests/states/or/test_package.py` (5 tests: the absolute import is a syntax error, importlib works, the registry tags an `or` package as `OR`, relative sibling imports work, the real registry still loads).
- **Findings:** pytest collects `tests/states/or/` without trouble, because it imports by dotted name through importlib.
- **Decisions:** none for HANDOFF; a workstream convention recorded in the package docstring.
- **AI:** Claude Code wrote the code and tests. Checked with the full suite (1392 passed), ruff and `compliance_check.py` (0 FAIL).
- **Open / next:** WS-OR step 1 (config and geography), then step 2 (RLIS parcels, pre-2018 archives).
