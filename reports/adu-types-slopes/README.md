# Anchor draw terms recomputed for Form A + place types (D-088)

The engine draws θ and α each run and shifts them with the judgment parameters they were fitted at (D-030).
Until now those shifts (`config/params/adu_anchor.yaml`) were computed for D-053's fit. This recomputes them
for the fit the engine now runs.

**How it was run:** `scripts/dev/adu_types_slopes.py --report reports/adu-types-slopes`, offline, 4 workers,
2026-11-14.
- **Fit set:** D-088's 64 places and 395 place-years, St. Paul out.
- **Rule shares:** held at adu.yaml's values (m_o 1.0, m_x 0.4).
- **Per parameter:** the fit places are rebuilt with the parameter at central ± 10% of its range. Then θ, α and
  the core term are refit.
- **Check:** the central refit reproduces D-088 exactly (θ 0.4476 per 1,000, α 1.550, core +1.199).
- The first attempt was cut off by a laptop restart before it wrote anything, and was rerun from the start.

**Files:**
- `slopes.csv`: d log θ / dp, d log α / dp and d β_core / dp for each of the 24 judgment parameters. 15 are
  in the fit; 9 leave the fit inputs unchanged and get 0.
- `summary.json`: the central fit and the observed-information terms (log-SE θ 0.191, α 0.239,
  correlation 0.115).
- `totals.csv`, `engine-log.txt`: the statewide engine check with the new terms. Compare it with
  `reports/adu-types-engine/totals_types.csv`.
- `run-log.txt`: the slope run's log.

**Results:**
- **θ slopes are close to D-053's:** within about 25%, mostly 5–15%. The largest is the mortgage-rate
  semi-elasticity, 1.64 against 1.45.
- **α slopes for the cost and market parameters are about half of D-053's.** The core term now carries part of what α absorbed. The three transport elasticities change less, and dispersion's α slope flips sign but is small.
- **The core term barely moves:** its largest shift across a parameter's 10% step is about 0.02, against an SE
  of 0.411. So the engine draws β_core on its own, with no slopes.

**Statewide effect (2027–2031, 1,000 draws):**
- Additional homes move by −3.4% to +2.9% at P50 and by −5.7% to +1.1% at P90.
- Current-rules ADUs move up to +12% at P90 (TX).
Page: https://claude.ai/artifact/FiiNrCDR2gxt3q8FBjtRnZ
