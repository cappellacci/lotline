# Modularity plan: scenario contract, engine vs fitting, smaller files

Drafted 2026-11-26 in the code-review thread (handoff 17) at Ben's request. Status: **step 1 adopted by Ben
2026-11-26 ("Yes, adopt step 1"); steps 1.1–1.4 merged (#555, #556). Step 2 started by Ben 2026-11-26
("Start plan step 2"; the ADU and MM moves go to their owners); step 3 not yet decided.** Every step here changes model code, so each one is done by that model's owner session (ADU =
"ADU statewide prediction methodology", MM = "Missing Middle Analysis refresh") or by WS-CORE for the shared
parts. No step changes a number: each one must leave every results bundle the same, draw for draw.

## Why

- **Replicability (25%)** asks whether a new scenario or dataset plugs in without touching the mechanics.
  Data inputs already do this (adapters, `READS`, `lotline calibrate`). Scenarios do not yet.
- **Transparency (30%)** asks whether a reader can find the code behind a number. Today the forecast and
  one-off fitting and audit code share one folder of about 50 files.

## What it looks like today (checked 2026-11-26 on `main`)

- **Scenario names are written out in many places:**
  - `schemas.py:515` (`SCENARIOS`) and `model/results.py:71-73` (`ENGINE_SCENARIOS`, `FEE_SCENARIOS`);
  - `build_bundle` calls `adu.run`, `mm.run` and `fees.simulate` one by one (`results.py:848-854`), and each
    has its own draws function (`results.py:186`, `:222`, `:263`);
  - the app template names `adu`, `missing_middle` and `fees` 67 times and has a fixed tab per model;
  - `app/build.py` (4 times) and `dashboard/summarize.py` (3 times) name them too.
- **`src/lotline/model/` holds 49 modules (46 plus the three in `scenarios/`), about 20,600 lines.** An import trace from `model.results` and
  `app.build`:
  - **Forecast path (26):** adu_owner, adu_screen, adu_types, affordability, aggregate, baseline,
    calibrate_adu, calibrate_shape, eligible_proxy, estimate_adu, estimate_mm, fee_inputs, fee_levels,
    gutcheck, hazard, money, pooled_adu, proforma, results, rule_tags, scenarios/{adu,fees,mm}, shortfall,
    undercount.
  - **Calibration or command line only (7):** adu_fit_set, adu_forecast, adu_new_rule, adu_refit, adu_terms,
    joint_refit, score.
  - **Neither (17, reached only from scripts or tests):** adu_profiles, adu_reform_check, adu_trend, backtest,
    calibrate_mm, completion, dashboard, demand, fit_audit, mm_counts, mm_routes, mm_tests, pencil_out,
    place_types, project_size, runs, sensitivity.
  - Fitting modules (`calibrate_adu`, `estimate_adu`, `estimate_mm`, `calibrate_shape`) are on the forecast
    path because the engine imports helpers from them.
- **Large mixed files:** `scenarios/adu.py` 1,732 lines, `pooled_adu.py` 1,555, `calibrate_mm.py` 1,535,
  `estimate_adu.py` 1,345, `calibrate_adu.py` 1,306, `estimate_mm.py` 1,219.

## Step 1. A scenario contract (WS-CORE, then each owner; first priority)

**Goal:** adding a reform such as parking means one new module plus its config and labels, with no edits to
`results.py`, `schemas.py`, the app or the dashboard.

1. **Contract** (`src/lotline/model/scenarios/__init__.py`, WS-CORE, open a `contract-change` issue first).
   Each scenario module defines:
   - `NAME` (e.g. `"missing_middle"`);
   - `LABELS`: a plain-language title, a one-line definition and the Handbook text it follows;
   - `VARIANTS`: for fees, `{"fees": "handbook", "fees_local_half": "local_half"}`; one entry for the others;
   - `run(state, store, origin, draws, variant) -> ScenarioRun`, which returns draws in one shape (place x
     draw x year added, plus the parts the bundle already stores);
   - optional `extra_tables(run) -> dict[str, DataFrame]` for the tables only it has (ADU place types, the
     fee grid).

   A registry (`scenarios.all()`) is discovered the way state adapters are (`registry.py`).
2. **Results** (WS-CORE): `build_bundle` loops over `scenarios.all()`. The three per-scenario draws functions
   become one, fed by `ScenarioRun`. `ENGINE_SCENARIOS` and `FEE_SCENARIOS` are derived from the registry,
   not written out. `schemas.SCENARIOS` is checked against it in a test.
3. **Bundle:** add `meta.scenarios` (name, variants, labels) so the app reads the list from the data. This is a
   schema version bump; the app must accept the old bundles until the next release.
4. **App and dashboard** (WS-APP): the model tabs, picker and lanes are drawn from `meta.scenarios`. Cards
   specific to one model (the ADU place-type chart, the fee slider, the MM steps) stay, but each one is keyed
   by a capability the bundle declares (`extra_tables`), not by the scenario's name.
5. **Owners** move their module to the contract: ADU, MM and fees, one PR each, after steps 1 and 2 merge.
6. **Proof:** a test scenario `tests/fixtures/scenarios/toy.py` (a fixed number of homes per eligible lot)
   registered only in tests. With nothing else changed it must appear in the bundle, the app and the
   dashboard. That test is the evidence for judges.

**Done when:** the toy scenario test passes, the three real bundles are the same draw for draw as before
(compare `results_draws` by hash), and `docs/adding_a_state.md` gains a short "Adding a scenario" section.

**Size:** about 1 day for WS-CORE (steps 1–3), 1 day for WS-APP (step 4), half a day per owner (step 5).

## Step 2. Split the forecast from fitting and audits (owners; after step 1)

**Goal:** `src/lotline/model/` holds only what a forecast runs, and every fitted value's code sits in
`src/lotline/calibrate/`.

1. **Move helpers the engine uses out of fitting modules.** For example, whatever `scenarios/adu.py` imports
   from `calibrate_adu`, `estimate_adu` and `calibrate_shape`, and `scenarios/mm.py` from `estimate_mm`.
   They go into small engine modules (e.g. `model/adu_rates.py`), and the fitting modules import from those.
2. **Move fitting code** (`calibrate_adu`, `calibrate_mm`, `calibrate_shape`, `estimate_adu`, `estimate_mm`,
   `joint_refit`, `adu_refit`, `adu_fit_set`, `adu_terms`, `adu_new_rule`, `adu_forecast`, `score`) to
   `src/lotline/calibrate/adu/` and `src/lotline/calibrate/mm/`, next to the step runners that call them.
3. **The 17 modules with no forecast or calibration caller:** each owner keeps the ones a test or a
   `validation/` check uses (backtest, gutcheck-style checks go to `src/lotline/validation/`). The rest go
   with phase 6's script archive (`scripts/dev/archive/`), with a line in the archive README saying what
   each one produced and which report holds the result.
4. **Guard test:** an import-graph test (like the trace above) fails if a module under `model/` imports from
   `calibrate/`, so the split stays put.

**Done when:** the guard test passes, every bundle is the same draw for draw, and `lotline calibrate --check`
still passes.

**Progress (2026-11-26, Ben: "Owners do them").**

- **Shared part, done (WS-CORE):** the six modules no model owns moved out of `model/`: `completion`, `runs`
  and `dashboard` (now `runs_dashboard`) to `calibrate/`; `backtest`, `demand` and `sensitivity` to
  `validation/`. Their tests moved with them. The fee model has nothing to move: none of its modules imports
  fitting code.
- **Guard test:** `tests/core/test_module_layout.py`. It reads the import graph with `ast` and fails if a
  `model/` module imports `calibrate/`, or if a `model/` module is neither reached from the forecast (results
  bundle with its discovered scenarios, the app, the data dashboard) nor listed in its `MOVING` table. Each
  `MOVING` line names the owner; the owner deletes it when the module moves, and a stale line fails. The
  holdout filter (`validation.holdout`) may still be imported from `model/`: it guards data.
- **Owners' part (briefs sent):** ADU has 14 modules in `MOVING`, three of them on the forecast path through
  helpers (`calibrate_adu` via `adu_owner`, `adu_screen`, `adu_types`; `calibrate_shape` via `adu_types`;
  `estimate_adu` via `pooled_adu`). MM has 8, one on the forecast path (`estimate_mm` via `scenarios/mm.py`).
  Step 2 is done when `MOVING` is empty.

**Size:** about 1 day per model owner. It pairs with phase 6 (dead `scripts/dev` scripts), so do them
together.

## Step 3. Break up the largest files (owners; optional, after step 2)

Split by the steps the methodology already names, one module per step, each with its own hand-worked test:

- `scenarios/adu.py`: legal lots → pays-off share → uptake hazard and ramp → own-rate persistence and drift
  → place types → totals.
- `pooled_adu.py`: the data assembly vs the likelihood vs the reporting.
- `calibrate_mm.py` and `estimate_mm.py`: C4 fit, year spread, ramp, and the tests that score them.

**Done when:** no engine module is over about 600 lines, and the bundles are unchanged. Only worth doing if
time remains before the Dec 16 deadline; steps 1 and 2 carry most of the scoring value.

## Order and owners

| Step | Owner | Depends on | Changes numbers? |
|---|---|---|---|
| 1.1–1.3 contract, results, bundle meta | WS-CORE (`contract-change` issue) | — | No (checked by hash) |
| 1.4 app and dashboard from `meta.scenarios` | WS-APP | 1.3 | No |
| 1.5 ADU, MM and fee modules onto the contract | each owner session | 1.2 | No |
| 1.6 toy scenario test and docs | WS-CORE | 1.4, 1.5 | — |
| 2 forecast vs fitting split (+ phase 6) | each owner session | 1.5 | No |
| 3 smaller files | each owner session | 2 | No |

## Decisions for Ben

1. **Go ahead with step 1?** Recommended: yes. It is the change judges would see under "add a scenario
   without touching the mechanics".
2. **Bundle schema bump for `meta.scenarios`:** yes, with the app reading old bundles until the next release.
3. **Step 3:** do it only if steps 1 and 2 are done by about Dec 5.
