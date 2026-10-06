# WS-ENGINE · Model engine (baseline, mechanism, scenarios, aggregation)

**Start:** after `schemas-v1` (wk 2). Synthetic-data first; MN data from wk 3.
**Owns:** `src/lotline/build/` (except `eligible.py` signature, owned by CORE), `src/lotline/model/`, `config/params/`, `tests/model/`.
**Principle:** every equation has a unit test against a hand-worked example ("tests prove the method"). Every parameter comes from `config/params/*.yaml` with a source. Nothing state-specific lives in this package: states differ only through data and config.

## Read first
- `docs/research/lotline-two-prong-design.md`
- `docs/research/lotline-statistical-protocol.md` §5
- `docs/research/lotline-methods-review.md` §2–3
- `docs/research/lotline-causal-diagram*.md` (the modifiers in §3 become inputs)
- `docs/research/lotline-validation-plan.md` V1, V2, V6b

## Modules and tasks
- [ ] **`build/panels.py`:** jurisdiction × year panel with numerator/denominator kept separate:
  - units by type;
  - eligible parcels by tier;
  - BPS;
  - market covariates.
- [ ] **`model/baseline.py` (V1):**
  - per-jurisdiction forecast of permits by size class for 5 years;
  - inputs: recent trend, regional demand, rate regime;
  - Fay–Herriot shrinkage for small places;
  - P10/P50/P90.
  - Must beat last-3-year-mean and linear-trend benchmarks on the V1 backtest.
- [ ] **`model/proforma.py`:** residual land value for each prototype:
  - ADU 600–1,000 sq ft;
  - duplex;
  - triplex;
  - fourplex;
  - townhouses;
  - 5–6 unit.
  
  Two variants: rental (rent, cap rate) and for-sale (price). Inputs:
  - hard cost (PPI-indexed);
  - **code step at 3+ units** (C43);
  - fees (Handbook $50k and real local fees);
  - financing (rate);
  - profit hurdle;
  - existing-use value (C46).
- [ ] **`model/hazard.py`:**
  - annual redevelopment hazard for parcels whose new use beats existing use;
  - logistic ramp over event time;
  - ADU owner hazard depends on home equity and rate (C22); MM developer hazard on financing (C45).
  - Hazard parameters are calibrated in V2 and by WS-EVIDENCE.
- [ ] **`model/scenarios/{adu,mm,fees}.py`:** Handbook definitions exactly:
  - ADU: one per SF parcel, ≥600 sq ft, no parking;
  - MM: 2–6 units, 3 stories, setbacks and coverage non-binding, with the FAR assumption stated;
  - fees: −50% of $50k = −$25k/unit through the pro forma, with land-capture λ and revenue-replaced toggle.
- [ ] **`model/combine.py`:** one parcel allocation for stacked scenarios (each parcel takes its most profitable feasible option, C47). No double counting.
- [ ] **`model/aggregate.py`:**
  - statewide sum;
  - displacement share (0–50%), shown as "in this place" vs "net statewide";
  - completion factor;
  - net-new share (ADU 50–80%);
  - formalization.
- [ ] **`model/uncertainty.py`:** Monte Carlo over parameter ranges → P10/P50/P90. Sobol/Morris (SALib) ranking for the tornado chart.
- [ ] **V1 harness** with each state instance; **V2 harness** (calibration slope, AUC, predicted/observed ratio).
- [ ] **V6b:** fee threshold-crossing counts using the validated pro forma, under the $50k assumption and under real local fees.
- [ ] Public API used by the app: `run(state, scenarios, params_overrides) -> Results` (tidy tables + metadata).

## Acceptance
- Unit tests for each equation.
- V1 run on BPS for all 4 states meets thresholds or reports why not.
- V2 run for MN (and NC if data allow).
- Combined-scenario test proves no parcel is counted twice.
- A run is reproducible from config alone.

## Don'ts
- No state-specific branches in model code.
- No hard-coded numbers.
- Don't fit anything on holdout data (use the loaders; never bypass the filter).
