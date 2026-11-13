### LB-fragment · 2026-11-13 · ADU model · Do D-083's place factors still pass on the new ADU rule rows?

- **Outputs:** `reports/adu-covariate-screen-new-rows/` (PLAN.md, README.md, results.html, screen.csv, factors.csv,
  influence.*); `--m-owner/--m-other` flags in `scripts/dev/adu_covariate_screen.py`; branch `ws/adu-screen-new-rows`;
  results page https://claude.ai/artifact/RVRKQx3D1pr4VCFCUzgQrh.
- **Answer:** housing age passes much more strongly (Holm p 0.0005, α −28%, robust to dropping any place). Owner share
  misses the within-state p bar (0.117) but, pooled across states, is stronger than before (α −35%).
- **HANDOFF:** none. Next step for Ben: a method entry adding owner share and housing age to Form A.
- **What Claude did:** asked by Ben ("Yes, do both"); wrote the plan before the run; reran D-083 unchanged except the
  rows and Form A's multipliers; built the results page. Caveat: the rows are not yet on main (22 state tests fail).

### LB-fragment · 2026-11-13 · ADU model · Do the place factors pass on the final, source-checked rows?

- **Outputs:** `reports/adu-covariate-screen-final-rows/` (README.md, results.html, screen.csv, factors.csv,
  influence.*, summary.json, run-log.txt); branch `ws/adu-screen-new-rows` with #419's config merged in.
- **Answer:** both pass. Housing age Holm p 0.0004, α −30%; owner share Holm p 0.081, α −21%, both robust to
  dropping any place. Owner share's pass depends on Form A's refitted m_x (0.8): at 0.7 its Holm p is 0.110.
- **HANDOFF:** none. Next step unchanged: a method entry adding both factors to Form A, scored on the data tiers.
- **What Claude did:** asked by Ben ("Rerun screen"); refitted Form A's multipliers on the final rows, reran the
  screen and influence check, ran the m_x 0.7 sensitivity, built the results page.
