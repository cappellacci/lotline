### LB-NNN · 2026-11-26 · review · Calibration phase 6: archive one-off scripts, document "one command"

**Question:** Can a reader reproduce every fitted value from the README, and tell which development scripts
still matter?

**Outputs:**
- `scripts/archive/` with 110 scripts moved from `scripts/dev/`, and `scripts/archive/README.md`: an index of
  what each answered and the decisions it names.
- `scripts/dev/README.md`: the 56 scripts that stay, each with why.
- `README.md`: "Reproduce the fitted parameters" and a Documentation link to `docs/calibration.md`.
- `docs/calibration.md`: step status brought up to date (18 of 22 run from code; four recorded; one frozen).
- `docs/adding_a_state.md`: step 14 and the state-list table point at the library fit sets
  (`adu_fit_set.STATES`, `mm_fitsets.STATES`) and `lotline calibrate`, not the old scripts.
- `config/validation/README.md`: test B is read by `adu_fit_set.roll_towns`.
- 306 `scripts/dev/<name>` paths updated in 131 files. Not changed: `LOGBOOK.md`, `HANDOFF.md`, `logbook.d/`,
  `reports/`, and the source column of `config/params/adu_partial_share_grid.csv`, whose step writes it.
- `pyproject.toml`: ruff skips line length in `scripts/archive/`.
- `src/lotline/adapters/national/geoparts.py` (`township_shares`): a pandas 3.1 regression from #550. Places
  with no 2020 township parts (Minnesota's Baldwin, Credit River and 7 others) left an empty table, and `.map`
  on it returned strings, so the share division failed. That stopped the eligible-proxy step. The fix looks
  totals up by index; there is a new test in `tests/core/test_geoparts.py`.

**What Claude did:**
- Classified every file in `scripts/dev/`. A script stays if any of these hold:
  - a hand-recorded calibration step names it;
  - tests, CI, `pyproject.toml`, the app page or a how-to doc runs it;
  - it is a frozen V5/V8/V9 validation script;
  - it is a live tool cited by library code (the NC crosswalk writer, the Minneapolis and Franklin roll
    checks, the Houston check, the ADU development run);
  - a script that stays imports it.
- Everything else moved with `git mv`, so history follows each file.

**Checked:**
- `lotline calibrate --check` OK (22 steps, 130 values, lock matches).
- `params_table.py --check` up to date after regenerating.
- Fast test tier: 2,879 passed. Ruff clean. Compliance 0 FAIL.
- `lotline calibrate --run --quick` on every runnable step: 18 minutes. Every value matched config exactly
  except three, where quick mode uses a coarser grid:
  - MM C4's ramp half-way point (4.0 against 4.5), and the mature rate with it;
  - the τ probabilities, all 3.98 times config from normalizing over fewer τ values;
  - the partial-share grid (3 rows instead of 10).
- The run needs `CENSUS_API_KEY` even with a cached lookup; the README says so.
