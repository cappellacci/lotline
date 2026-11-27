### LB-NNN · 2026-11-25 · Review · Tests in parallel (pytest-xdist) and a 3-minute fast tier

- **Question:** How can the 20-plus-minute test command, flagged by the judges, be made quick to run?
- **Outputs:** `pyproject.toml` and `uv.lock` (dev dependency `pytest-xdist`, MIT, and `execnet`, MIT; marker `slow`);
  `tests/slow_tests.txt` and `tests/conftest.py` (marks the 40 listed tests `slow`); `.github/workflows/tests.yml`,
  `challenge.toml` and `README.md` (`uv run pytest -q -n auto`; the fast tier documented).
- **Decision:** Ben, 2026-11-25: "Yes, add xdist". Built on #536 (toolchain pins), which removed the second CI run.
- **What Claude did and how it was checked:**
  - Full suite with 6 workers: 2,845 passed in 11 min 41 s, against about 14–16 min serial on the same laptop. The
    40 slowest tests (7–147 s each, all simulation-recovery fits) cap the gain.
  - Those 40 are marked `slow` from one list, so no test file changed: `-m "not slow" -n auto` runs 2,805 tests in
    2 min 52 s.
  - Compliance 0 FAIL. Shrinking the slow fits' sizes is left to the model owners.
