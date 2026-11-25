### LB-NNN · 2026-11-25 · Review · Toolchain pins: Python 3.12, dependency bounds, uv version, Node on CI

- **Question:** What stops a fresh setup or a CI image change from running an untested toolchain?
- **Outputs:** `.python-version` (3.12); `pyproject.toml` (bounds on httpx, pandas, pandera, pyarrow, pydantic, pyyaml;
  `[tool.uv] required-version`); `uv.lock` (metadata only); `.github/workflows/tests.yml` and `compliance.yml`
  (`actions/setup-node`, Node 22); `tests/app/conftest.py`.
- **Decision:** Ben, 2026-11-25 (overnight): "go with your suggested order"; item 2. Declaring numpy as a direct
  dependency is left for Ben (CLAUDE.md: ask before adding a dependency). Merge left to Ben.
- **What Claude did and how it was checked:** `uv lock` after the bound changes left every package version as it was.
  With `CI=1` and no node on PATH, `pytest tests/app` stops with a clear error (exit 4); with node, 76 app tests pass.
  ruff clean.
