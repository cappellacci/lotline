### LB-NNN · 2026-11-26 · review · Plan to make the model more modular

**Question:** What would let a new scenario plug in without touching the mechanics, and keep the forecast
code apart from the fitting code?

**Outputs:** `docs/build/modularity-plan.md` (plan only; no code changed).

**What Claude did:**
- Counted where scenario names are written out (schemas, results, app template 67 times, app build,
  dashboard).
- Traced imports from `model.results` and `app.build`: 26 model modules on the forecast path, 7 used only by
  calibration or the command line, 17 reached only from scripts or tests.
- Wrote three steps with owners, order and "done when" checks:
  1. a scenario contract, with a toy scenario as proof;
  2. split the forecast from the fitting code, paired with phase 6;
  3. smaller files (optional).

**Checked:** counts rerun on `main` at 2026-11-26. Decisions for Ben are listed at the end of the plan and in
the PR.
