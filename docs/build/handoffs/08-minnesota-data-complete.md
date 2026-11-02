# Thread 8: Finish Minnesota's data for statewide end-to-end simulation (WS-MN)

**Goal:** every input the baseline and the three scenarios (ADU, missing middle, fees) need exists for **all of Minnesota** (1,053 jurisdictions: 763 places, 218 townships, 72 county remainders), so a statewide end-to-end run is possible. Finish with a written readiness report and an integration run of what's already built (baseline + ADU). Minnesota is the pilot state; other states follow its pattern.

**Read first:** the shared rules in `docs/build/handoffs/README.md`; `docs/build/workstreams/WS-MN.md`; `docs/data_availability.md` (MN table); `docs/research/lotline-data-catalog-mn.csv`; `docs/analysis_plan.md` D-014 to D-025; `config/states/mn.yaml`; `config/reforms/mn.csv`.

**State on main (2026-10-20):**
- **Parcels:** metro only (Met Council 2021-2026 rolls, Minneapolis assessor, Ramsey). The other 80 counties use the ACS fallback.
- **Permits:** BPS statewide; Met Council (metro, ADU and duplex-to-fourplex flags from 2016); Minneapolis; St. Paul (holdout).
- **ADU rules:** 98 rows, mostly metro; outstate is mostly uncoded (D-022 draws them).
- **Missing-middle rules:** 2 rows.
- **Fees:** none coded.

**Stay out of the other threads' lanes:**
- **Thread 1** (missing-middle panel; `model/estimate_mm.py`) uses Met Council duplex-to-fourplex permits: don't build that panel.
- **Thread 2** writes `config/fees/*.csv` from the batch-1 records and builds `model/scenarios/fees.py`: add Minnesota fee *sources* here and coordinate rows through its converter format (same columns), in your own PR touching only `config/fees/mn.csv`, after thread 2's PR has merged. If it hasn't merged yet, write to `config/fees/mn_extra.csv` and say so.
- **Thread 3** builds the demand index for all states: don't duplicate it.
- **WS-ENGINE** owns the estimators and the scenario code.

## Tasks, in priority order (small PRs)
1. **Outstate parcels.** `docs/research/lotline-data-catalog-mn.csv` lists MnGeo's compiled opt-in county parcels (59 of 87 counties).
   - Build `adapters/states/mn/mngeo_parcels.py` (one current roll; record its date; the snapshot rule applies: St. Paul parcels only from rolls dated 2023 or earlier).
   - Crosswalk land use; use non-personal fields only.
   - Set `parcel_sources` in `mn.yaml` so the metro sources keep priority (#154/#165 guard).
   - Report counties covered, parcels, land-use-known shares, and tiers (D-016, D-017).
   - Counties outside MnGeo stay on ACS. List them.
2. **Eligible parcels statewide:** rebuild `jurisdictions` and `eligible_parcels` for MN after task 1. Report jurisdictions by denominator source and quality, and that no jurisdiction has two sources (D-020 non-overlap).
3. **Missing-middle rules.** Code 2–4 unit rules (theme `missing_middle`) for the places already known:
   - **From the batch-1 records** (`docs/research/ordinances/batch1-2026-10-20.json`, `missing_middle_legal`): Minneapolis 2020-01-01 (with the 2022/2023-24 injunction windows as sensitivity rows), Duluth, St. Louis Park, Rochester (not legal), Brooklyn Park and Coon Rapids (not legal); St. Paul's rules may be coded, its outcomes never.
   - **Everyone else:** the remaining large places go on a fill-in table for Ben (`docs/research/ordinances/mn-mm-lookups-todo.csv`, same format as the ADU one: place, GEOID, population, what's needed, a starting link if known, blank answer columns). Put the 40 largest MN places first, metro and outstate. No broad web research.
4. **Outstate ADU rules:** the same fill-in-table approach for the 30 largest outstate places (Rochester, Duluth and St. Cloud are coded; next Mankato, Moorhead, Winona, Owatonna, Austin MN, Willmar…), as `docs/research/ordinances/mn-adu-outstate-lookups-todo.csv`.
5. **Minnesota fee sources:**
   - **Met Council Sewer Availability Charge (SAC):** per-unit rates by year, as long a history as Met Council publishes. Applies to the metro sewer service area; record which places are in it.
   - **The Minneapolis zoning layers** (primary zoning and built form, in the catalog): for rule coverage (D-021) of ADU and missing-middle rules in Minneapolis.
   - **Met Council Regional Planned Land Use:** a metro proxy for single-family-only areas, with documented limits.
   - All through the IO layer, with provenance rows.
6. **Readiness report:** `docs/build/mn-readiness.md`.
   - **The table:** for each model input (parcels, eligible parcels, permits, ADU rules, missing-middle rules, fees, rents and values, rates, costs, demand index, holdouts), the coverage across MN's 1,053 jurisdictions; what's real data vs fallback vs unknown (D-022); and the gaps with what closes each (Ben's lookups, a thread, or accepted as fallback).
   - **Integration run:** the baseline forecast and the ADU scenario statewide (`scripts/dev/adu_dev_run.py --state MN`), labelled as a development run with the provisional ADU anchor, until D-025 replaces it. Confirm it completes for every jurisdiction with no errors, and report what fraction of the state's eligible parcels sit in places with real vs drawn rules.

## Done when
PRs for tasks 1–5 are open with green CI; the readiness report lists every remaining gap; the integration run completes for all of MN. Never merge; Ben reviews.

---

## Closed 2026-11-02 (thread 13, part B)

Thread 8 was never run as written. Thread 13 cut it to five must-do items (`docs/build/mn-data-plan.md`, #256,
approved 2026-11-01) and did those. The integration run (task 6) was replaced by counts, under the data-thread
rule.

**Delivered (open PRs, in review order):**
- **#256** the plan.
- **#259** V5 St. Paul inputs: the city's dated zoning snapshot (2023-11-26) gives 55,269 eligible H1/H2 lots
  on the pre-window roll.
- **#260** missing-middle rules from the batch-1 records: St. Louis Park 2025 and Duluth 2026; "one home" rows
  for Rochester, Brooklyn Park and Coon Rapids; a fill-in table for 33 of the 40 largest places.
- **#261** Greater Minnesota parcels: `mngeo_parcels`, 31 outstate counties, with `jurisdictions` and
  `eligible_parcels` rebuilt.
- **This PR** the readiness report (`docs/build/mn-readiness.md`), the counts script, the second-coder sheet,
  and the MN rows of `docs/data_availability.md`.
- **#258** (contract-change, WS-CORE) provenance for the St. Paul zoning archive.

**Where Minnesota stands:**
- **Jurisdictions:** 1,053. 539 count from parcels (86% of the population), and 1,043 have every year
  2010–2024. Of the 40 largest places, only Mankato is on ACS.
- **Tiers:** 130 / 408 / 515.
- **Rules:** 109 rows, all single-coder: ADU for 80 places, missing middle for 7.
- **Fees:** 13 jurisdictions; the Handbook's $50,000 elsewhere.

### For the engine threads (week of 2026-11-02)
- **ADU estimate (D-025): 74 MN places with Met Council or Minneapolis permits and a dated rule.**
  - 45 have an in-window change (9 of those rows are dated `[earliest-known]`) and 29 are "no ADUs" controls.
  - St. Paul never enters.
  - Met Council's file covers every metro community, so no covered-places list is needed.
- **Missing-middle estimate (D-024):** 100 BPS places of 10,000+.
  - In-window events: Minneapolis 2020 (the injunction windows as sensitivity) and St. Louis Park 2025. St.
    Louis Park's effective date is from a search snippet.
  - Rochester, Brooklyn Park and Coon Rapids are untreated on evidence.
- **V5 St. Paul (#45, by Nov 17):** read `reports/mn/V5-stpaul-inputs.md` (#259). **Cap annual inputs at
  2023.** Disclose D-013's exposure in the freeze file.
- **Eligible lots changed for every MN place.** The old table had no pre-2021 history for parcel-counted
  places. **Rebuild or re-read before rerunning anything**; anything run on the old table is stale.
- **Population weights:** `pop_2020` covers places and townships (4.97M). County remainders are blank.

### Rows not to lean on as dated events until checked
- Every MN rule row has one coder (`mn-second-coder-2026-11-02.csv`; the 55 priority-1 rows first).
- St. Louis Park 2025's effective date.
- The 9 `[earliest-known]` D-025 event rows.
- Brooklyn Park and Coon Rapids: placeholder 2010 dates.

### Decisions to fold into HANDOFF (thread 6)

| Date | Decision | Fragment |
|---|---|---|
| 2026-11-01 | MN plan approved (M1–M5 must-do, M6–M8 if time), with the MnGeo download (Ben) | `2026-11-01-ws-mn-13-data-plan.md` |
| 2026-11-01 | V5 St. Paul H1/H2 lots from the dated pre-window zoning snapshot (option b) (Ben) | `2026-11-01-ws-mn-13-v5-stpaul.md` |
| 2026-11-01 | Cap V5 St. Paul annual inputs at 2023 (proposed) | `2026-11-01-ws-mn-13-v5-stpaul.md` |
| 2026-11-02 | MnGeo counties: the 0.6–1.4 ACS band; a place whose main county is not loaded stays on ACS; split metro/outstate places take the majority source (proposed) | `2026-11-02-ws-mn-13-mngeo.md` |
| 2026-11-02 | **Seasonal cabins (class 4c12) are not single-family houses for eligibility** (Ben): the lake townships' undercount against ACS is accepted; Aitkin, Cass and Cook stay on ACS | `2026-11-02-ws-mn-13-readiness.md` |
| 2026-11-02 | "None" rows (no ADUs, one home per lot) are controls, never events, in the panel counts (proposed; matches OH and TX practice) | `2026-11-02-ws-mn-13-readiness.md` |

### Left open on purpose
- **M6** (outstate ADU fill-in table), **M7** (Met Council SAC fees) and **M8** (planned land use, Minneapolis
  zoning): not started.
- An ADU lookup table for the 109 covered metro places with no rule. It's the cheapest way to grow D-025.
- **County code tables** for the five bare-code counties.
- Pre-2021 metro rolls (#11).
- #258 (provenance for the zoning archive).
