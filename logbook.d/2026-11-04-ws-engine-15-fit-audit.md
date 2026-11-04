### LB-NNN · 2026-11-04 · engine · Why does the ADU fit miss: measurement, shape or noise?

- **Question:** the four-state ADU fit misses in opposite directions by state (MN low, TX high) and has a
  large place spread (α 2.28). Ben asked for an audit before any new fit.
- **Outputs:**
  - D-045 in `docs/analysis_plan.md`: method pre-registered in c5a7167, code in 992546d before the run,
    results added after.
  - `src/lotline/model/fit_audit.py` with hand-worked tests in `tests/model/test_fit_audit.py`.
  - `scripts/dev/fit_audit.py`; run once into `reports/adu-fit-audit/`.
- **Findings:**
  - State-level misses are mostly within the model's own noise: a correct model is "useful" for TX only 38%
    and OH 25% of the time. MN is the real miss.
  - Survey-counted MN suburbs come in at 0.32 of expected. City-records places come in at 0.94. Many large
    suburbs never report an ADU.
  - Observed counts are flat or falling while the ramp expects them to rise 3–5×.
  - Home value has a positive residual effect (×1.86 across its interquartile range).
- **Decisions:** none. Next step proposed to Ben: settle the suburban zeros (true zero or reporting gap),
  then free the ramp and home-value terms (approach 2) against an empirical benchmark (approach 3).
- **AI:** Claude Code (Opus 5.5) wrote D-045, the code and tests, ran the audit once, drilled into
  co-built and source overlaps with throwaway queries, and wrote up the results. Values were read from the
  run's log and CSVs.

### LB-NNN · 2026-11-04 · engine · Are the suburban zeros true zeros or reporting gaps?

- **Question:** many large MN suburbs report no ADU permit in the Met Council survey. Is that a gap in the
  survey or real? Ben chose to settle this before any new fit.
- **Outputs:** `scripts/dev/fit_audit_zeros.py`; `reports/adu-fit-audit/zeros_by_detached.csv`,
  `zeros_assessor.csv` and the run log; a dated follow-up and a correction under D-045 in
  `docs/analysis_plan.md`.
- **Findings:**
  - The zeros are true zeros, caused by attached-only rules: 7 observed against 87 expected (0.08).
  - Survey-counted suburbs that allow detached ADUs come in at 0.46, the same as Minneapolis's city records
    (0.42).
  - Assessor rolls agree: 1 of 21,255 Eagan parcels and none of 20,762 Lakeville parcels went from 1 to 2
    units between 2021 and 2025.
  - Correction: the earlier "city records 0.94" was Austin; without it, city records come in at 0.42.
- **Decisions:** none. Proposed D-046: give "no detached ADUs" its own multiplier and refit.
- **AI:** Claude Code (Opus 5.5) ran exploratory queries, then wrote them up as a script and ran it once.
  Values were read from its log.
