# Thread 9: Combining scenarios and statewide aggregation (WS-ENGINE-AGG)

**Goal:** turn per-place scenario results into the numbers a legislator sees. Combine the reforms on the same lots without double counting, add places up to counties and the state with honest ranges, convert gross permits to net new homes, and cap the result by what local demand can absorb. Build it now against a **common scenario output contract** with stub scenarios, so the real ADU (D-025), missing-middle (thread 1, D-024) and fee (thread 2) results plug in when they land.

**Read first:** the shared rules in `docs/build/handoffs/README.md`; `docs/research/lotline-two-prong-design.md`; `docs/research/lotline-causal-diagram.md` §1 (the forward-model formula) and C26, C30, C47 (displacement and substitution, ADU vs missing middle on one lot); `docs/research/lotline-statistical-protocol.md` §5.10 (gross to net); `config/params/aggregate.yaml` (net-new share, formalization, displacement, completion factors, publishing minimum D-015); `docs/analysis_plan.md` D-015, D-019, D-020, D-022; `src/lotline/model/scenarios/adu.py` (`run()`, `non_overlapping()`); `src/lotline/model/baseline.py` (baseline draws); the judging methodology report's MS-04 (no demand cap), in `reports/judging/2026-10-19-0518-e31b4ed/judge-methodology.md` (local, gitignored).

## Deliver (small PRs)
1. **D-026 in `docs/analysis_plan.md`, before code:** the choices below, with sources and ranges; what's judgment; the tests that prove them.
2. **Scenario output contract** (`model/scenarios/contract.py`, plus a schema entry if it becomes a processed table; propose a contract-change issue if so):
   - **Rows:** place × year × draw for each scenario: added permits by building type, the eligible parcels it used, and flags (drawn rules D-022, outside calibration range).
   - **Retrofit:** make `adu.run()` emit it (or add an adapter function), without changing its numbers.
   - **Stub scenarios** for missing middle and fees, clearly labelled, for tests and the integration run.
3. **`model/combine.py`: several reforms on the same lots.**
   - **Rule:** a parcel builds at most one project. Where both an ADU and a 2–4 unit building are allowed and feasible, the project is the more profitable one (the pro forma's residual land value vs existing-use value; the two-prong design). At place level: split each place's eligible parcels by which option wins, using the pro forma's feasibility shares, then apply each scenario's uptake only to its share.
   - **Fees** shift feasibility (cost) for both: apply fee changes inside the pro forma, not as a separate add-on.
   - **Tests:** a hand-worked example; combined ≤ ADU-alone + missing-middle-alone; all levers off = baseline exactly; each lever alone = its scenario alone.
4. **`model/aggregate.py`: places to counties to state.**
   - **Draws:** sum draws across non-overlapping places (D-020), never percentiles; P10/P50/P90 from the summed draws.
   - **Gross to net:** apply the ADU net-new share and formalization share (D-019), and completion factors for permits → completions. Show them separately.
   - **Displacement (C26):** a sourced share of each place's gain is reallocated from neighbours (`displacement_share` in `aggregate.yaml`). Report "in this place" vs "net statewide", which differ.
   - **Publishing minimum (D-015):** places under 20 eligible parcels are folded into their county or region in outputs, never shown alone.
   - **Tests:** sum-of-draws vs sum-of-percentiles on a hand-worked case; displacement conserves totals as specified; publishing folds correctly.
5. **`model/absorption.py`: the demand cap (MS-04).**
   - **Cap:** induced units in a county-year ≤ a sourced share of projected household growth plus a vacancy band.
   - **Data:** Minnesota State Demographic Center county household projections (public; add an adapter through the IO layer); ACS households and vacancy for the base.
   - **Parameter:** a sourced parameter with a range, plus how often the cap binds, reported per county. Where it binds, scale down that county's places in proportion.
   - **Tests:** the cap binds and doesn't bind as constructed; never negative; totals respect the cap.
6. **`scripts/dev/simulate_state.py --state MN`:** the end-to-end command. Baseline + scenarios (real where available, stubs labelled otherwise) → combine → aggregate → absorption → a results bundle for the app (place, county, state × year × scenario × outcome with P10/P50/P90/mean, plus the drivers needed for "what moves this"). Runtime target: statewide in a few minutes.

## Coordinate
- **WS-ENGINE (D-025)** edits `model/estimate_adu.py`; **thread 1** adds `model/estimate_mm.py`; **thread 2** adds `model/scenarios/fees.py`. Don't edit those files. Consume their outputs through the contract; if a change is needed, say so in your PR.
- **The results bundle format** feeds thread 5 (the app). Document it in `docs/schemas.md` or a README.

## Done when
D-026 and PRs 2–6 are open with green CI. `simulate_state.py --state MN` runs end to end, with stubs labelled, and its output shows combined ≤ sum of parts and summed-draw ranges. Never merge; Ben reviews.
