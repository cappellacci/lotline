# WS-EVIDENCE · Out-of-state comparables and causal estimators

**Start:** week 3 (Oct 28). Comparables table v1 by Nov 10; estimators ready for `prereg-v1`.
**Owns:** `src/lotline/adapters/comparables/`, `src/lotline/evidence/`, `config/reforms/comparables.csv`, `tests/evidence/`, `reports/comparables/`.
**Role:**
1. Supplies the **evidence prong**: uptake curves from places that reformed years ago, which set the upper range Minnesota's low uptake can't.
2. Builds the **estimators** the state instances use in V3/V4.

## Read first
- `docs/research/lotline-statistical-protocol.md` (all)
- `docs/research/lotline-methods-extraction.csv`
- `docs/research/lotline-evidence-register.csv`
- `docs/research/adu-study-design.md`
- `docs/research/lotline-validation-plan.md` V3–V4

## Comparable sources (adapters)

| Key | Source | Use |
|---|---|---|
| `portland_permits` | Portland residential permits since 1995 (`IS_ADU`, `NEW_UNITS`) + demolition layer | ADU 2010/2018, RIP 2021 backtests |
| `portland_rlis` | Metro RLIS taxlots (sale price, year built, building sq ft; quarterly) | V2 mechanism lab; denominators. ODbL-style terms: runtime fetch only. |
| `seattle_permits` | Seattle `76t5-zqzr` (units added/removed, dwelling type, completed date) | Seattle 2019 ADU backtest |
| `ca_apr` | California HCD APR Table A2 (2018+, ADU and SB 9 flags, APN) | CA ADU and SB 9 backtests; ADU/BPS ratio |
| `la_permits` | LADBS 2020+ (`ADU_CHANGED`, `SQUARE_FOOTAGE`) | SB 13 750 sq ft bunching (V6c) |
| `bend_permits` | Bend permitting table (`HB2001ADU`, units, finaled) | small-city comparable |
| Austin | reuse WS-TX adapter | HOME |

## Tasks
- [ ] Adapters + contract tests (same schemas).
- [ ] `config/reforms/comparables.csv`: rubric-coded reforms with dates and sources (Portland, Seattle, CA, Bend, Spokane if data allow).
- [ ] **Comparables table v1:** event-time uptake per 1,000 eligible parcels per year with ranges, by place and theme. Every number traces to an adapter or an E-id.
- [ ] **Estimators** (`evidence/`):
  - `did.py`: Callaway–Sant'Anna / imputation estimator, not-yet-treated controls, NB/Poisson with offset, event-study plots, HonestDiD-style sensitivity;
  - `synth.py`: demeaned SC with Abadie donor rules, augmented SC, placebo-in-space inference, conformal intervals;
  - `pooling.py`: hierarchical NB uptake curves (start simple: empirical Bayes; PyMC optional);
  - `transport.py`: Mahalanobis similarity score, overlap flags, inverse-odds weights.
  
  Verify licenses of any library before adding it. Implement it ourselves if a license is unclear.
- [ ] **Estimator tests:** recover known effects from simulated panels (staggered adoption, heterogeneous effects, a TWFE-bias case).
- [ ] **V4 leave-one-place-out backtests** across comparables + MN/NC places (coordinate with state instances).
- [ ] **V6c (optional):** SB 13 bunching at 750 sq ft.

## Acceptance
- Simulation tests pass.
- Comparables table documented.
- Backtest harness produces the V4 coverage metric.
