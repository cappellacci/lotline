### LB-NNN · 2026-10-20 · Run: D-023 ADU estimation rerun stopped by the numerical guard (underpowered)
- **Question:** With separation handled, does the pre-registered D-023 model produce usable estimates on the
  Twin Cities panel?
- **What I did:** ran `scripts/dev/estimate_adu.py --full --out reports/adu-d023/` once (the one rerun).
- **Inputs:** main after #179/#180 plus the fix (#181).
- **Outputs:** `reports/adu-d023/run-2026-10-20-log.txt`; dated note under D-023.
- **Findings:** the point fit converged but kept 143 of 760 place-years (53 all-zero places, 87 separated
  observations dropped; 29 cells dropped; θ and δ not identified: collinear with fixed effects). A bootstrap
  draw exceeded the coefficient bound and the run stopped with `EstimationError`; no estimate was produced
  or read. Reported as underpowered, per D-023.
- **Decisions:** none; options listed under D-023 for Ben.
- **AI:** Claude ran the script once and reported its diagnostics.
- **Open / next:** Ben's choice of a re-specification (new dated entry) before any further run.
