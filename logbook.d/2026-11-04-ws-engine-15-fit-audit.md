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
