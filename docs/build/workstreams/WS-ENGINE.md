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

## Added 2026-11-06 (Ben): results export, housing-need share, and the national-data-only gate
The app (WS-APP) is a static page built from **pre-computed results**; it does no model arithmetic in the browser except the final aggregation across draws. Three tasks follow.

- [ ] **Results export (contract with WS-APP):** `lotline results --state XX` writes `reports/results/<state>/` (gitignored): per scenario (adu, mm, fees, each stacked combination) the **parameter draws** the browser needs to re-aggregate (eligible parcels by tier; uptake rate θ; pencil-out share; completion factor; net-new share; displacement share; overlap allocation for combined runs), the funnel stages (Legal → Pencils → Built), the P10/P50/P90 statewide totals the engine computed itself (the parity target), the housing-need denominator, the overlap/confidence flag, scorecard rows, and metadata: `commit_sha`, `run_at`, engine version, config hash, data tier, state role. Schema in `schemas.py` (ask WS-CORE via a `contract-change` issue), a fixture bundle under `tests/fixtures/results/`, and a test that a bundle round-trips. Sliders map onto named draw columns, so every slider in the app corresponds to one parameter in `config/params/`.
- [ ] **Housing-need denominator (office hours A2), decided 2026-11-06:** `config/params/housing_need.yaml`, two kinds of entry, never mixed on the page.
  - `household_growth_5y` for onboarded states: the state demographer's projection (MN State Demographic Center, NC OSBM, TX Demographic Center, Ohio DSA, Oregon OEA), with value, low/high, unit, source URL and vintage. The page reads "x% of the homes the state expects to need over five years".
  - `shortage_stock` for every state (used as the headline denominator where no demographer projection is coded): a **blend of two published state-level shortage estimates as low and high, geometric mean as the value**: Up for Growth *Housing Underproduction in the U.S.* (annual state table; 2024 report on 2022 data; 2025 report pending) and Zillow's housing-deficit estimate (2023 data; state-level). Freddie Mac's state table (Feb 2020 Insight, 2018 data; newer figure national only) is recorded as a third, dated check in `notes`, not blended, because of its vintage. The page reads "x% of the state's estimated shortage", with both sources and their vintages named beside the number. Record the CRS comparison (IN12628, Dec 2025) in the evidence register: the national estimates differ by ~1.5× on method alone and the existence of a shortage is itself disputed, which is why this is a range and not a number.
  - The bundle carries `denominator_kind` on every share; the app must never put a share-of-growth next to a share-of-shortage without the label.
- [ ] **Gate for the national-data-only tier (decides whether the app shows 50 states), pass rule decided 2026-11-06; pre-registered as D-053 in `docs/analysis_plan.md`:** the proxy already exists (`build/eligible.from_acs`, `denominator_source = acs_sf_fallback`). Run it for MN, NC, TX, OH and OR, sum to state totals, and compare with `from_parcels` state totals for the same theme and year. Leave one state out: fit one scale factor (the geometric-mean ratio real ÷ proxy, standing for the share of single-family homes on single-family-only-zoned, lot-size-eligible parcels) on four states, apply it to the fifth, and record the fifth's ratio. **Pass: every one of the five leave-one-out ratios lies in [0.7, 1.4].** The log-sd of the five ratios becomes `eligible_proxy_sd` in `config/params/`, drawn once per draw for any tier-3 state (so the proxy's spread is carried in the range). **Pass → every state gets a bundle, with the overlap flag and the "zoning not observed" caveat. Fail → onboarded states only; the rest grey with "bring your own state"; logged as a finding.** About half a day; fits freeze week (Nov 17–24).
- [ ] **CLI (contract with WS-CORE, decided 2026-11-06):** `lotline results --state XX` writes one bundle; `lotline results --all` writes every bundle **and builds the page** (`reports/app/index.html`), so a judge's regenerate is one command. `scripts/build_app.py` stays callable on its own for app work.

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
