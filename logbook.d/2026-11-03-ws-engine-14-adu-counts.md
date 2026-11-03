### LB-NNN · 2026-11-03 · engine · Do the ADU misses go away when the four states count the same thing?

- **Question:** Ben asked to fix the counts first, and to run every test across all four states and compare
  them. Two count rules were set in D-041 before any fit: co-built ADUs (built with a new house on the same
  parcel) are left out, and survey counts are corrected for under-reporting (ρ = 0.57).
- **Outputs:**
  - Code and tests: `src/lotline/model/calibrate_adu.py`, `scripts/dev/calibrate_adu.py` (`--counts`),
    `config/params/adu_counts.yaml`, tests in `tests/model/test_calibrate_adu.py`.
  - Run: `reports/adu-counts/` (counts, fits per state, statewide verdicts, market term, main backtest, log).
  - Plan: D-041 in `docs/analysis_plan.md`, plan before the fits, results after.
- **Findings:**
  - Texas falls from 2,785 to 1,108 ADUs (Austin was 66% co-built).
  - Pooled θ is 1.23 per 1,000 (0.81–2.11). Fitted alone, MN gives 1.25 and NC 1.27; TX gives 4.17.
  - Leave one state out: MN, NC and NC with Raleigh and Durham are useful; OH and TX are inside only; none
    is missed. In D-040, MN and TX were missed.
  - Leave one place out: 92% coverage. The error ties the no-effect benchmark.
  - S1 (co-built included) reproduces D-040's misses.
- **Decisions:** none adopted. θ in `hazard.yaml` is unchanged; the reading is for Ben to confirm.
- **AI:** Claude Code (Opus 5.5) wrote the rules, tests, run and write-up.
  - Rules were checked by hand-worked tests: co-built matching, source choice, thinning.
  - Counts were checked against the diagnosis note before the fit.
  - Table values in the plan were read from the CSVs; one pooled θ was corrected.
