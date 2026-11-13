### LB-fragment · 2026-11-13 · ADU model · Do D-083's place factors still pass on the new ADU rule rows?

- **Outputs:** `reports/adu-covariate-screen-new-rows/` (PLAN.md, README.md, results.html, screen.csv, factors.csv,
  influence.*); `--m-owner/--m-other` flags in `scripts/dev/adu_covariate_screen.py`; branch `ws/adu-screen-new-rows`;
  results page https://claude.ai/artifact/RVRKQx3D1pr4VCFCUzgQrh.
- **Answer:** housing age passes much more strongly (Holm p 0.0005, α −28%, robust to dropping any place). Owner share
  misses the within-state p bar (0.117) but, pooled across states, is stronger than before (α −35%).
- **HANDOFF:** none. Next step for Ben: a method entry adding owner share and housing age to Form A.
- **What Claude did:** asked by Ben ("Yes, do both"); wrote the plan before the run; reran D-083 unchanged except the
  rows and Form A's multipliers; built the results page. Caveat: the rows are not yet on main (22 state tests fail).
