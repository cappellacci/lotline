# Thread 2: Fee table from pipeline records; first fee scenario (WS-CORE-FEES)

**Goal:** turn the fee items the city-ordinance pipeline already found and checked into `config/fees/*.csv`, then build a first fee-scenario module.

**Read first:** `config/fees/README.md`; the `fees` schema in `docs/schemas.md` (1.7: citation fields); `docs/research/ordinances/batch1-2026-10-20.json` (23 cities; each entry has `city` and `record.fee_schedules[].items[]` with quotes and links); `config/params/fees.yaml` and D-010 (fee elasticity); `src/lotline/model/proforma.py` (fees enter the pro forma per unit); the Handbook fee scenario (cut fees by 50% of $50,000/unit; see HANDOFF S1 and `challenge.toml`).

**Deliver:**
1. **PR A, converter:** `scripts/dev/ordinance_records.py`, which writes `config/fees/<st>.csv` from the records.
   - Include only items whose schedule link was read and that have a quote.
   - Map `component` to `fee_component`, `applies_to` to `building_type_std` (single_family→SFD, adu→ADU, duplex_to_fourplex→U2/U3_4 as stated, per_unit_any→OTHER with a note), and `basis` to `FEE_BASIS`.
   - Convert per-sq-ft and per-meter fees to `amount_per_unit_usd` using the pro forma's prototype sizes; state the assumption in `notes`.
   - Fill `dollar_year`, `effective_date` and the citation fields; set `verified_by` only where a checker verdict exists (not stored in batch-1 JSON: leave blank and note it).
   - Validate with `lotline.config.load_fees`. Tests on a small synthetic record set. Report coverage: cities × years × components.
2. **PR B, fee scenario:** `model/scenarios/fees.py`.
   - **Incidence:** the Handbook fee cut, applied to each place's actual per-unit fees where coded, otherwise the national prior. Incidence is the land-capture share λ (`fees.yaml`, E064/E066).
   - **Two channels:** (a) feasibility through the pro forma (prototypes whose residual land value crosses the threshold); (b) the elasticity route (D-010) as the fallback for places without parcel data.
   - **Output:** P10/P50/P90 like the ADU scenario, on non-overlapping places (D-020).
   - **Tests:** hand-worked; a zero cut equals the baseline; a bigger cut never lowers output.
   - Log open choices as D-entries.

**Done when:** both PRs open with green CI; coverage table and a development run for a few places in PR B, labelled as development.
