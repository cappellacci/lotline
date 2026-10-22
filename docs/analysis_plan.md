# Lotline: Analysis plan (pre-registration)

**Status: DRAFT, not yet pre-registered.** Per the validation plan (§2, integrity rule 1), §3 of
`docs/research/lotline-validation-plan.md` (tests and pass/fail criteria) is copied here, reviewed by Ben, committed
and tagged `prereg-v1` **before any V3 outcome model runs**. Until then this file only records decisions made
ahead of pre-registration, so they aren't lost.

## Decisions and deviations log

Dated, append-only. Each entry says what changed from the research documents, why, and who decided.

### D-001 · 2026-10-06 · V0 BPS reconciliation tolerance
- **Was (validation plan §3, V0, proposed):** "BPS totals match exactly."
- **Now:** our BPS place sums must be **within 1% of Census's state total in every compared year**; years outside
  1% are listed in the V0 report for explanation. Exact matches are still counted and reported.
- **Why:** Census revises state and county totals after the annual survey with late reports and corrections that
  the place files don't always carry (Census BPS methodology), so exact agreement isn't achievable even with a
  correct pipeline. First run (2026-10-06): exact match MN 10/32, NC 28/31, OH 20/34, TX 6/34 years; within 1%
  MN 30/32, NC 29/31, OH 34/34, TX 21/34. The check is read as directional evidence that the pipeline counts what
  Census counts.
- **Decided by:** Ben, 2026-10-06 (PR #66).
- **Open:** Texas 2003–2014 runs 1–2% high (Denton County unincorporated, 2014); for WS-TX to explain.

### D-002 · 2026-10-14 · V1 baseline specification B (variance floor from a place's own history)
- **Was (WS-ENGINE spec A, declared before the first run):** a place's level and its uncertainty from its last 5 years only.
- **Now (spec B):** the same, plus a floor on a place's year-to-year variance from its own longer history, so a one-off subdivision year in a tiny township isn't read as its normal pace.
- **Why / how decided:** added **after** the first Minnesota run showed the problem. It is logged here as a deviation for that reason. On the V1 windows, A passes 19 of 48 cells and B 17, but B has 13% lower error for 5+ unit buildings. Both are reported (PR #93).
- **Decided by:** Ben, 2026-10-14.

### D-003 · 2026-10-14 · V1 coverage uses randomized coverage for whole-number outcomes
- **Was (validation plan V1):** "P10–P90 coverage 70–90%", read as the share of outcomes inside the interval.
- **Now:** randomized (probability-integral) coverage. For counts that are mostly 0, the inclusive check reads ≥90% almost everywhere and flatters any model. The inclusive share is still reported.
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-004 · 2026-10-14 · V1 bias is judged on the model's mean
- **Was:** "no systematic bias in the post-2022 window" (statistic unspecified).
- **Now:** mean signed error of the model's **mean** forecast (not its P50) for 2023 on, within ±25% of the model's post-2022 MAE. Means add up to state totals; medians of skewed counts don't.
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-005 · 2026-10-14 · V1 scores only places with at least 20 eligible parcels
- **Was:** every non-reforming place scored.
- **Now:** places with fewer than `v1_min_eligible_parcels` = 20 eligible parcels at the forecast origin are still forecast (and rolled into their county for reporting) but left out of V1 scoring: a few lots swing their rates for every method.
- **Effect (2026-10-14 run):** still 17 of 48 cells pass. Single-family model MAE 10.08 vs 9.66 for the 3-year mean, so the model now loses on single-family. 5+ units: 2.82 vs 3.29 (3-year mean) and 3.94 (trend).
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-006 · 2026-10-14 · Pre-declared next V1 specification: two demand signals (before any run)
- **Why:** every method under-forecasts NC and TX single-family building in 2023–25 (model mean 70–87% of observed). Recent pace alone can't anticipate a demand surge.
- **Specification C, fixed now, run once:** spec B with the place's level multiplied by `exp(β_h · g + β_p · q)`, where
  - `g` = growth of occupied housing units in the place's county: ACS B25003_001 for the 5-year window ending at the forecast origin vs the **non-overlapping** window ending 5 years earlier, annualized;
  - `q` = FHFA house-price change over the 3 years to the origin, from the panel's fallback chain (county → CBSA → state non-CBSA → state), annualized;
  - `β_h`, `β_p` are estimated by pooled Poisson regression on **fit years only** (all years ≤ origin, within state), never on the forecast years;
  - no other changes; same windows, parameters and pass criteria (D-003 to D-005).
- **Reporting:** spec C is compared with spec B and both benchmarks in every cell. Whichever passes more cells is not automatically adopted; Ben decides, and the choice is logged as D-007.
- **Decided by:** Ben, 2026-10-14 (choice of signals proposed by Claude Code, approved before running).

### D-007 · 2026-10-15 · Baseline stays spec B; spec C (demand signals) not adopted
- **Compared (PR #95, both runs from `python -m lotline.model.backtest --spec B|C`, fits ending 2016/2018/2020,
  MN NC OH TX):** B and C each pass 17 of 48 V1 cells. Single-family MAE 10.08 (B) vs 10.01 (C); 5+ units 2.82
  vs 2.92. NC/TX single-family post-2022 bias of the mean −8.00/−11.08 (B) vs −7.16/−9.53 (C); every NC/TX
  single-family cell still fails under both.
- **Decision:** keep spec B as the baseline. C's gain is small, it is worse for 5+ units, and its fitted
  coefficients are unstable (signs flip across states and windows; |β| up to 66 for 2–4 unit buildings, where
  household and price growth are correlated).
- **Kept for reproducibility:** spec C remains available as `--spec C` (default B).
- **Open:** a more stable demand form (one combined signal, or a statewide cycle term), pre-declared before
  any run, to address the NC/TX single-family under-forecast.
- **Decided by:** Ben, 2026-10-15.

### D-008 · 2026-10-19 · Repeated project totals counted once
- **Was:** permit units summed as each city reports them (WS-OH Columbus and Cincinnati adapters, PRs #106/#112).
  Several city files put a multi-building project's **total** on every building's permit: Columbus 2023, nine
  permits on one parcel each say 198 units; Austin 2022, nine permits on one parcel each say 280.
- **Now:** when permits are counted (`lotline.build.permits.count_units`), if at least
  `repeated_total_min_permits` = 3 new-construction permits on the same parcel, jurisdiction and year all report
  the same count of at least `repeated_total_min_units` = 50 units, that count is counted **once** (on the lowest
  `permit_id`); the others count 0. Demolitions and permits with no parcel are never grouped. The adapters'
  tables stay as reported.
- **Parameters:** `config/params/permits.yaml` (ranges 20–100 units, 2–5 permits).
- **Sensitivity, both ways:** the rule on is the primary count; `dedupe=False` gives the as-reported count, and
  both are shown wherever permit counts are compared or used.
- **Effect (2026-10-19, 5+ units vs BPS):** Columbus 2023 1.41 → 1.02 of BPS; Austin 2022 1.42 → 1.25. Over
  2018–2025 the rule removes 1,963 units (13 permits) in Columbus and 4,167 (31) in Austin; none in Cincinnati,
  whose excess over BPS has a different cause (open).
- **Why:** counting a project nine times overstates multifamily building, the outcome most reforms target.
- **Decided by:** Ben, 2026-10-19.

### D-009 · 2026-10-19 · Pro forma specification choices the research docs leave open
- **Research docs (methods review §2a, register C43/C46/C48/C54):** feasible when value − (hard + soft + fees +
  financing + target profit) ≥ existing-use value × (1 + margin); code step at 3+ units; fee carry depends on
  payment timing. They don't say what the profit is measured on, or how the code step and fees enter.
- **Chosen (`src/lotline/model/proforma.py`, `config/params/proforma.yaml`):**
  - profit = margin × finished value (not × cost), so a fee change moves residual land value one-for-one, plus
    interest when fees are paid at permit (`fee_paid_at_permit`). The register's NZ hurdles (17–25% on cost)
    are converted to value (h / (1 + h) ≈ 15–20%);
  - the code step is a percentage added to hard cost per sq ft for triplexes, fourplexes and 5–6 unit
    buildings, with a longer build time; townhouses stay under the residential code; a switch
    (`triplex_under_irc`) covers places such as Austin (PM2024-0002) that let triplexes use it;
  - land capture λ enters as the share of a fee cut that does not reach builders (fees causal diagram,
    (1 − λ)); the "revenue replaced" toggle (C51) is left to `model/scenarios/fees.py`, since it acts on
    infrastructure capacity, not on project cost;
  - an ADU keeps the house, so its existing-use value is 0.
- **Why:** the simplest forms that match the docs' equations and keep each line checkable by hand.
- **Reporting:** a fee cut is reported both as the cut itself (exactly $25,000 per unit when fees are paid at
  completion) and with the interest saved when fees are paid at permit.
- **Decided by:** proposed by WS-ENGINE; accepted by Ben, 2026-10-19 (the "approx." parameter values are to be
  checked against their sources in a follow-up PR before V2 uses them).

### D-010 · 2026-10-19 · Fee elasticity re-anchored to the evidence register; low end 0
- **Research docs (methods review §3c; fees causal diagram):** ε 0.5–3, central 1.5, with a note that E081
  argues for the low end and that the low case must include zero. The central value had no study behind it,
  and the high case (3 × 0.75 × ~7% ≈ +16%) fell outside the V6 pass band (judging panel MS-03).
- **Chosen (`config/params/fees.yaml` `fee_permit_elasticity`):** central **0.3** (E081, tract-level unit
  elasticity), low **0** (E058 and E062: fee effects not significant), high **1.75** (E080 and E082, metro-wide
  supply elasticities). E059/E060 (non-water/sewer fees can raise building) are handled by the revenue-replaced
  toggle in `scenarios/fees.py`, not by a negative ε.
- **Cost to price:** the studies estimate elasticities with respect to price. For the project at the margin of
  feasibility, price ≈ total development cost (land included), so a fee cut of (1 − λ) × Δfee reaching
  builders acts like a price rise of (1 − λ) × Δfee / TDC. The formula %Δ permits = ε × (1 − λ) × Δfee / TDC ×
  ramp(t) is unchanged; it slightly overstates the effect where projects earn above-normal profit.
- **Effect:** at an illustrative TDC of $350k (the $25k cut ≈ 7%), central ≈ +1% and high ≈ +9% single-family
  permits over 5 years, inside V6's 0 to +12% band (test: `test_fee_elasticity_range_includes_zero_...`).
  No results change yet: no model code reads ε. The V6b pro forma route remains the primary fee estimate; ε is
  the fallback where parcel data are missing.
- **Decided by:** Ben, 2026-10-19 (accepting MS-03 via the coordinator).

### D-011 · 2026-10-19 · Baseline cycle: shared calendar years, and centred so the mean stays flat
- **Was (`model/baseline.py`):** the cycle shocks were demeaned (x − mean x) and resampled from the same
  random-number stream as the per-place draws, after them. Two problems (judging panel MS-06, MS-07):
  (a) which cycle years a draw got depended on how many places were in the run, so single-family and 5+ unit
  draws were coupled or not by accident; (b) E[exp(Σ shocks)] > 1, so the mean drifted up with the horizon
  (about +6% by year 5).
- **Now:** (a) one matrix of resampled calendar years per state, origin and draw (`cycle_years`, seeded by
  simulation seed, state and origin only), shared by every size class and scenario; a size class with no
  change for a drawn year takes another of its years. (b) shocks centred by log(mean(exp(x))), so each
  year's factor averages 1 and the mean stays flat when nothing changes. Tests: `test_cycle_keeps_the_mean_
  flat_over_the_horizon`, `test_cycle_coupling_does_not_depend_on_which_places_are_present` (both fail on
  the old code).
- **Effect on V1 (spec B, MN NC OH TX, run 2026-10-19):** **17 → 13 of 48 cells pass.** All of it comes
  from (b): with (a) alone the run is unchanged (17 cells; model MAE 10.084 / 0.368 / 0.196 / 2.824 for
  1 / 2 / 3–4 / 5+ units vs 2.822 before for 5+). With both: beats benchmarks 40 → 41 cells, coverage OK
  33 → 32, **bias OK 26 → 21**; MAE 10.08 → 10.13 (single-family), 0.368 → 0.367, 0.196 → 0.193,
  2.82 → 2.77 (5+). The six flipped cells (MN 2018 1, 2; MN 2020 3–4, 5+; TX 2018 5+ fail now; MN 2018 3–4
  passes now) all turn on the bias test, which judges the mean (D-004). The model already under-forecasts
  after 2022; the old upward drift of the mean was partly hiding that.
- **Why:** the old pass count leaned on an artefact. The under-forecast after 2022 is now visible and is
  the thing to address (e.g. state momentum or spec C), not to tune away here.
- **Decided by:** Ben, 2026-10-19 (accepting MS-06 and MS-07 via the coordinator); the drop to 13 of 48 is
  for Ben to note in the PR.

### D-012 · 2026-10-19 · Charlotte holdout extended to Mecklenburg County BPS rows (disclosed leak)
- **Found:** BPS has no Charlotte place row. Charlotte-Mecklenburg Code Enforcement reports Charlotte's permits, and the Mecklenburg towns', under Mecklenburg County (37119). The V5 holdout filtered only Charlotte's place GEOID (3712000), so the 2023–2025 rows for 37119, which carry Charlotte's post-UDO outcomes, were not held out. Found by WS-NC while building parcels (#123), confirmed by WS-CORE.
- **Where they went:** the processed NC `bps_place_year` table and therefore the V1 backtests (D-002 to D-007), whose NC scores for windows reaching 2023–2025 include these rows in aggregate. No Charlotte- or Mecklenburg-specific outcome figure was printed, plotted or reported; V0 never compared NC years from 2023 on (held-out years are skipped by date window). The V5 Charlotte prediction has not been made, so it can't have been tuned to them.
- **Fix:** holdouts can name `reporting_geoids`, held out over the same window; Charlotte names 37119 (`config/states/nc.yaml`). Holdout places are always jurisdictions in their own right (`build/jurisdictions.local_geoids`), so no adapter can relabel their rows as the county's. The processed NC BPS table was rebuilt: 37119 now ends in 2022. Mecklenburg towns' 2023+ outcomes are hidden too (the cautious side).
- **Consequence:** NC V1 results that used 2023–2025 must be re-run with the rebuilt table and reported with this note; the V5 Charlotte test proceeds, with this disclosure in its report.
- **Decided by:** Ben, 2026-10-19 (fix and disclose).
- **Re-run note (2026-10-20, WS-ENGINE):** V1 spec B re-run on the rebuilt tables (`python -m lotline.model.backtest
  --state MN NC OH TX --spec B`, eligibility rule 1.1): **17 of 48 cells pass** (was 13 after D-011);
  beats benchmarks 39 (was 41), coverage OK 34 (32), bias OK 25 (21). Model MAE by size class 11.62 / 0.370 /
  0.188 / 2.13 for 1 / 2 / 3–4 / 5+ units (was 10.13 / 0.367 / 0.193 / 2.77). Passes by state: MN 6, NC 2,
  OH 6, TX 3. The change cannot be pinned on D-012 alone: since D-011 the same run also picked up rule 1.1
  denominators (D-014), the ACS fallback for rolls with unknown land use (D-017), one GEOID per BPS ID (#158)
  and new full parcel rolls. Rates are per eligible parcel, so denominator changes move every state's MAE
  (single-family MAE rose in all four states). The backtest's `--rule-version` default now follows
  `build.eligible.RULE_VERSION` (it was pinned to 1.0, which no longer exists).

### D-013 · 2026-10-19 · St. Paul post-reform figures removed from a research doc (disclosed exposure)
- **Found:** the judging panel (2026-10-19) flagged that `docs/research/lotline-mn-scouting.md` quoted St. Paul's post-reform outcome counts for held-out years (from a public Minneapolis Fed article), written during scouting before the holdout rules existed.
- **Fix:** the figures were replaced with a note; WS-CORE made the edit with the line masked and did not read them. They remain in git history and in the public source; the history is not rewritten.
- **Consequence:** the people and agents building Lotline may have seen these figures before the V5 St. Paul prediction is frozen. The V5 prediction must not use them, and its report will disclose this exposure. The test remains a forward test of the model, which has no access to them.
- **Decided by:** Ben, 2026-10-19.

### D-014 · 2026-10-19 · Missing-middle eligibility includes vacant single-family-zoned lots (rule 1.1)
- **Was (rule 1.0):** a parcel was eligible for missing middle only if it held an existing single-family house (at most one unit) on single-family-only zoning, the same building test as ADUs.
- **Now (rule 1.1):** missing middle also counts **vacant residential lots** on single-family-only zoning. The Handbook defines the scenario as "2–6 units on single-family-only parcels"; only the ADU definition requires an existing single-family building.
- **Why:** the judging panel's methodology review (MS-02, 2026-10-19). Vacant lots carry the lowest existing-use value, so they are where small multi-unit buildings are most likely to pencil; leaving them out understated the missing-middle denominator and departed from the Handbook definition.
- **Limits:** where a jurisdiction has no usable parcels, the ACS fallback (one-unit detached homes) has no vacant land, so its missing-middle denominator still excludes vacant lots; those denominators are already `low` quality.
- **Decided by:** Ben, 2026-10-19.

### D-015 · 2026-10-19 · Places below 20 eligible parcels are not published on their own
- **Rule:** results for a place with fewer than `min_eligible_parcels_publish` eligible parcels (20; range 10–50; `config/params/aggregate.yaml`) are folded into its county or region in the tool and reports, never shown by themselves.
- **Why:** the judging panel's transparency review (TR-07, 2026-10-19). Small places have rates too noisy to read, and so few parcels that a result could point at individual properties. 20 matches the V1 scoring floor (D-005).
- **Decided by:** Ben, 2026-10-19.

### D-016 · 2026-10-19 · Data tiers follow the loaded parcels
- **Was:** every jurisdiction was tier 3 (national data only) unless a state config listed it by hand; none did, so Austin, Columbus and Cincinnati, which have parcel rolls, were labelled tier 3.
- **Now:** `build/jurisdictions.tiers_from_parcels` assigns tiers from each jurisdiction's latest roll. Tier 1: land use known for at least 90% of parcels and year built for at least 80% of built parcels; tier 2: land use only; tier 3 otherwise (`config/params/tiers.yaml`; tier definitions from the state briefs and BUILD_PLAN §5). `data_tiers` in a state config still overrides.
- **Why:** the Model & Assumptions draft (#135) found every jurisdiction at tier 3; tiers drive how results are labelled and how wide their ranges are.
- **Decided by:** Ben, 2026-10-19.

### D-017 · 2026-10-20 · Parcel rolls with mostly unknown land use use the ACS denominator
- **Found:** with Ohio's statewide parcels (#150), Summit County sends no land use, so Akron's roll counted **0 eligible parcels rated `high` quality**: parcels of unknown use are never eligible, and the quality share counted only unknown units, lot size and zoning. Lucas County (55% unknown) gave Toledo a large undercount.
- **Now:** a jurisdiction-roll is used as a parcel denominator only if its land use is known for at least `tier2_min_land_use_share` (0.9, the tier 2 threshold from D-016) of its parcels; otherwise that jurisdiction uses the ACS fallback (`build/eligible.usable_rolls`). On Ohio's 2023 rolls this moves 18% of parcels, including all of five counties (Hardin, Lucas, Meigs, Muskingum, Summit at jurisdiction level), to the fallback.
- **Decided by:** Ben, 2026-10-20.

### D-018 · 2026-10-20 · ADU hazard: functional forms the research docs leave open
- **Research docs:** the two-prong design and protocol §5.5–5.8 say the mature hazard comes from comparable
  places and is transported by effect modifiers (price-to-cost first, C22 equity and rates for ADUs), with a
  ramp over event time and no silent extrapolation. They don't give the functional forms, the reference place
  or how to widen outside the comparables' range.
- **Chosen (`src/lotline/model/hazard.py`, `config/params/hazard.yaml`):**
  - anchor: 4 ADU permits per 1,000 eligible lots a year (2–5), the adu-study-design calibration band, with
    **Portland 2015–19** as the reference place (ACS 2015–19 rent and value, `scripts/dev/adu_reference.py`);
    the comparables pooling of protocol §5.7 is not built yet, so this is the band, not a fitted posterior;
  - price-to-cost enters through the **share of lots that pencil**, F = Φ((ln PCR − ln(1 + margin)) / σ), a
    lognormal spread of lot-level ratios around the place's ratio; uptake among lots that pencil is the same
    everywhere (u = h_ref / F(PCR_ref)). This makes uptake rise with profit, stay a probability and match the
    anchor at the reference;
  - reference and target share the same cost parameters (national hard cost), so with national costs only
    rent (and home value, rates) transports; Portland's higher local costs are not netted out (open);
  - equity as a power of median home value and rates as an exponential in the mortgage rate, both judgment
    with ranges that include no effect;
  - logistic ramp in years since adoption, half-way at 2 years;
  - calibration range = the span of Portland, Seattle and Los Angeles (rent, home value) and 2015–23 (rates);
    outside it the hazard gets mean-preserving lognormal noise with log-sd = w × log distance (w = 1).
- **Why:** the simplest forms that use the pro forma, keep each step checkable by hand and make extrapolation
  visible. The fitted comparables model (protocol §5.7) can replace the anchor and σ later without changing
  the interface.
- **Decided by:** proposed by WS-ENGINE, 2026-10-20; for Ben to confirm in the PR.

### D-019 · 2026-10-20 · ADU scenario: increment over current rules, additionality, and a first check against observed ADUs
- **Research docs:** the Handbook defines the scenario (one ADU per eligible single-family parcel, ≥600 sq ft,
  no parking); the protocol (§5.10) asks for net-new and formalization adjustments; the judging panel asked for
  the increment over existing local rules (MS-01), a wider net-new range and a formalization share (MS-09), and
  additionality for ADUs already counted as 1-unit permits (MS-10). How to combine these is left open.
- **Chosen (`src/lotline/model/scenarios/adu.py`):**
  - current rules from the coded reforms in force at the origin: Handbook-equivalent (c = 1), partial (owner
    occupancy, parking, discretionary, attached only or a cap under 600 sq ft: c = `adu_partial_rule_share`
    0.3, judgment) or none (c = 0); uncoded rubric fields count as not restrictive and are listed;
  - the Handbook adds (1 − c) × h_m × ramp(t) on top of the current rule's own ramp; observed ADU rates
    (2019–22, where permits flag ADUs) are a floor under both paths, so ADUs already built are never "added";
  - a separate pool of parcels without an ADU under each set of rules (at most one ADU per parcel);
  - `adu_net_new_share` low end 0.50 → 0.45 (E039 ≈ 48%); new `adu_formalization_share` 0.10 (0–0.30,
    judgment from E049, E050); new `baseline_adu_share_of_one_unit` 0.033 (0.0047 Twin Cities metro – 0.0765
    Austin, `scripts/dev/adu_baseline_share.py`);
  - forward runs draw a flat 2026–30 mortgage rate from `mortgage_rate_forecast` (6.60%; 2.96–6.81%, the
    2015–25 annual range as a stress range, `market.yaml`); validation uses each year's actual rate;
  - where a place's only parcel roll is after the origin (Austin's 2026 roll), that roll is used and flagged
    (a denominator, not an outcome).
- **First check against observed ADUs** (`scripts/dev/adu_current_rules_check.py`, 2016–22, before every
  holdout window, actual rates, central-parameter draws; raised by WS-CORE on #161). Model ADU permits under
  each place's coded current rules vs observed: **Minneapolis 315 vs 179 (1.8x)**, **Raleigh 172 vs 81
  (2.1x)**, **Austin 4,230 vs 2,302 (1.8x)** (Austin's ADU rules are not coded; treated as mature). The
  closer fit in Minneapolis before 2021 rests on the judgment partial share (0.3) under its owner-occupancy
  rule; after the rule was dropped (2021–22) Minneapolis built 16–17 a year, against a mature Handbook hazard
  of 2.71 per 1,000 parcels (~200 a year): an order of magnitude. Austin, inside the calibration range on rent
  (distance 0), builds 1.98 per 1,000 a year against the model's 4.06. Durham could not be checked: its
  ADU-eligible parcel count is 5 (a denominator fault, reported to WS-NC/WS-CORE).
- **Reasons, in the order the evidence supports them:** (1) the anchor: Portland's ~4 per 1,000 is gross,
  includes formalization and a $7–12k fee waiver (E047) and long-built ADU know-how (C24); Austin and Raleigh,
  post-reform and with rents near or inside the range, run at about half of it; (2) transport through rent
  alone: with national construction costs, Minneapolis's price-to-cost (1.0) is only 11% below Portland's, so
  σ = 0.5 lowers its hazard by ~20%, far less than observed; local costs (climate, foundations) and lot or
  design rules (size, setbacks, internal ADUs keeping owner occupancy) are not in the model; (3) Minneapolis's
  rule coding leaves size and parking uncoded, so "Handbook-equivalent" may overstate its rules.
- **Superseded proposal:** a hand-set anchor of 0.002 was proposed here and **declined by Ben (2026-10-20)**:
  a hand-picked anchor is arbitrary. Instead the anchor is estimated from Lotline's own post-reform data with
  the pre-registered split below.
- **Pre-registration (written and committed before any fit was run, 2026-10-20):**
  - *Quantity:* `adu_mature_hazard_ref` (θ, the reference place's mature ADU permits per eligible parcel a
    year), estimated on the log scale. Expected count for place i in year y: μ = θ × k, with
    k = eligible parcels × (mature hazard at θ = 1, from that year's ACS rent and value, newest vintage ≤ y,
    2025 dollars, and that year's actual mortgage rate) × the largest c × ramp(years since effective, at
    mid-year) over the coded ADU rules in force (`config/reforms/*.csv`, read at run time) — the scenario's
    current-rules path without the observed floor (the floor would make the fit circular). All other
    parameters at their central values.
  - *Likelihood:* negative binomial, Var = μ + αμ², α estimated (Poisson when α → 0).
    `adu_partial_rule_share` is estimated jointly only if its 90% profile interval is narrower than its
    judgment range (0.1–0.6); otherwise it stays at 0.3 (judgment) and the report says so.
  - *Interval:* 90% profile-likelihood interval for θ (α, and s if estimated, profiled out); it becomes θ's
    low–high range in `hazard.yaml`.
  - *Observed counts:* ADU permits per place-year, the larger of the flagging sources each year (Met Council or
    city), from holdout-filtered tables. A place-year enters only if a coded ADU rule is in force by 1 July and
    its permit source flags ADUs that year.
  - *Fit set:* Minneapolis 2016–2025; every other Twin Cities place with a coded ADU rule, 2016–2025 (Met
    Council flags from 2016); Austin 2016–2023 once its ADU rules are coded (its 2024–25 counts, 90 and 9, look
    incomplete and are excluded in advance).
  - *Test set:* Raleigh 2021–2025 (rule in force from July 2020); Durham once its eligible-parcel count is
    fixed. Reported: observed vs predicted (median and 90% interval from a parametric bootstrap: log θ normal
    from the profile interval, NB counts) per year and in total.
  - *Never used:* St. Paul (V5, all years), Charlotte (V5), any held-out row.
  - *Decision rule:* the fitted θ and interval replace the anchor whatever the test shows; a test total outside
    its 90% interval is reported as a transport failure, not refitted.
- **Results of the pre-registered fit (run 2026-10-20 after the pre-registration commit fd21217;
  `scripts/dev/calibrate_adu.py`):**
  - *Data used:* fit set = Minneapolis (2016–25) and 10 Twin Cities suburbs with coded ADU rules (Apple
    Valley, Blaine, Bloomington, Eagan, Edina, Maplewood, Minnetonka, Plymouth, Roseville, St. Louis Park):
    64 place-years, 243 ADU permits, 222 of them Minneapolis's. Austin is not in it: its ADU rules are not
    coded yet (the pre-registered rule). Test set = Raleigh 2021–25. Durham is not tested: the roll the test
    would use has 5 ADU-eligible parcels.
  - *Partial-rule share:* profile maximum at s = 1.00, 90% interval 0.26–1.00, wider than the judgment range,
    so **not identified; kept at 0.3 (judgment)**.
  - ***Anchor: θ = 0.000467 per parcel a year, 90% profile interval 0.000275–0.000868*** (0.47 per 1,000; α =
    6.6). Written to `hazard.yaml` as value and range, per the decision rule.
  - *Test (Raleigh 2021–25):* observed 230; predicted mean 112, median 62, 90% predictive interval 2–445.
    Inside, so not a transport failure by the pre-registered rule, but the interval is wide because α is large
    and the mean is half of what Raleigh built.
  - *Cross-check with Portland (4 per 1,000; E046, E047):* the estimate is 0.12 of it. Reasons, none of which
    the fit can separate: Portland's count is gross permits, including legalized units (formalization, E049)
    and a $7–12k fee waiver from 2010 (E047); Portland's higher construction costs are not netted out (the
    model uses national costs for both); "per 1,000 lots" in the Portland figure is undefined (E022; protocol
    §0); and the fit set is mostly one Midwestern city plus suburbs whose ADU rules remain restrictive.
  - *Misfit, reported not fixed:* with s held at 0.3 the fitted path underpredicts Minneapolis 2016–20 (under
    its owner-occupancy rule: about 30 a year observed vs 2–8 fitted) and overpredicts it from 2023 (13–16 vs
    13–21). The current-rules check with the new anchor gives 0.3x observed in Minneapolis (45 vs 179,
    2016–22), Raleigh (24 vs 81) and Austin (592 vs 2,302, rules uncoded). Heavily restricted suburbs (permits
    by conditional use, owner on site, extra parking, occupant caps) with no ADUs carry the same s = 0.3 as
    Minneapolis's lighter rule and pull θ down.
  - *Exploratory, not pre-registered and not used:* treating Austin's uncoded rules as mature
    Handbook-equivalent adds 2,545 permits; then s is identified (0.22, 0.10–0.56) and θ = 0.000779
    (0.000400–0.001751); Raleigh 230 vs mean 187 (90% 8–704). WS-CORE notes Austin's rules cover SF-3 lots of
    5,750+ sq ft only, so this overstates Austin's coverage (D-021 proposal).
  - *Effect on the development run* (origin 2025; five-year sums of place means, added ADU permits / additional
    homes): MN 1,362 / 753; NC 2,088 / 1,154; OH 1,584 / 876; TX 7,859 / 4,340 (with the 0.004 band anchor
    they were 9,607, 17,561, 10,722 and 54,180 permits; NC also falls through D-020).
- **Next specification (to be pre-registered before it is run, not run here):** a partial-rule share graded
  by the number of Handbook conditions a rule fails, rule coverage (D-021), and a place random effect in place
  of a single α; refit when Austin's rules are coded and Durham's roll is fixed.
- **Fit 2 pre-registration (written and pushed before fit 2 was run, 2026-10-20; follows D-022):**
  - *Unchanged from fit 1:* quantity θ, NB likelihood, 90% profile interval, fit and test sets, the
    partial-share rule (estimated jointly only if its 90% interval is narrower than 0.1–0.6), the decision
    rule (fit 2's θ and interval replace fit 1's in `hazard.yaml` whatever the test shows).
  - *Blank rubric fields are integrated, not dropped:* a place-year whose rule class depends on blank fields
    enters with a two-component mixture, P(y) = q·NB(y; θ·k_A) + (1 − q)·NB(y; θ·k_B), where path A has those
    rules restricted (partial) and path B Handbook-equivalent, and q = 1 − Π(1 − p_field) with p_field the
    coded share restricting that field (`scenarios.adu.field_probabilities`, coded rules in force at the
    fit's run date, state share if 5+ values, else pooled). All rules of one place-year that depend on blanks
    move together (amendments share their resolved fields). Dropping them instead would remove Minneapolis's
    2021–25 years and most suburbs.
  - *Place-years with no coded rule* stay out of the fit (as in fit 1); *explicit "no ADUs"* place-years have
    an expected count of 0 and are left out, with any observed ADUs there reported.
  - *Parking:* a citywide parking reform with a zero minimum in force by 1 July fills a blank ADU parking
    field (D-022).
- **Fit 3 pre-registration (written and pushed before fit 3 was run, 2026-10-20; Ben's next specification):**
  - *Fit set:* Minneapolis, the Twin Cities places with coded ADU rules (St. Paul never), and **Austin
    2016–2023** (its rules are now coded; 2024–25 excluded as before). Place-years need a coded rule in force
    by 1 July and permits that flag ADUs that year. *Test set:* Raleigh 2021–25 and Durham 2021–25 if every
    roll the test uses has 1,000+ ADU-eligible parcels (after the NC rebuild). Never: St. Paul, Charlotte,
    any held-out row.
  - *Expected count:* μ_it = θ × u_i × parcels × h_m(θ = 1; that year's rent, value, actual rate) × max over
    the rules in force of c(type) × coverage × ramp(age at mid-year). Rule types (D-022): Handbook c = 1;
    owner occupancy only c = m_o; other restrictions (parking, not by right, attached only, cap under 600 sq ft)
    c = m_x; both c = m_o·m_x. Coverage per D-021 (zones, lot minimum; judgment shares where parcels can't
    measure it).
  - *Place effects:* yes. u_i ~ Gamma(mean 1, variance α), shared across a place's years, with counts Poisson
    given u_i (closed-form marginal likelihood per place). This replaces fit 2's per-year NB, whose large α
    (7.5) reflected differences between places, not years.
  - *Blank rubric fields (D-022):* integrated at place level: each place's blank fields restrict or not
    together over its years, with probabilities from the coded rules (state share if 5+ values, else pooled);
    the place likelihood is the probability-weighted sum over those combinations.
  - *Parameters:* θ (log scale), α, m_o, m_x. m_o and m_x on a grid 0.1, 0.2, …, 1.0; each is estimated if its
    90% profile interval (others profiled) is narrower than its judgment range (m_o 0.2–1.0, m_x 0.1–0.6),
    else held at its judgment value (m_o 0.5, m_x 0.3). θ's 90% interval: profile likelihood with α and any
    estimated share profiled out.
  - *Test prediction:* parametric bootstrap: log θ normal from its interval, a new u per test place, a
    blank-field combination per place, Poisson counts per year; observed vs median and 90% interval per year
    and in total.
  - *Decision rule:* θ, α (as `adu_place_effect_variance`) and any estimated share replace the configured
    values whatever the test shows; a test total outside its 90% interval is reported as a transport failure,
    not refitted. The scenario draws a new u per place in each simulation draw from the fitted α.
- **Fit 2 results (run 2026-10-20 after the fit-2 pre-registration, commit f5ee618):** the first run read
  every observed count as 0 (a variable-name bug in `place_years` overwrote the observed counts with the field
  counts); it was discarded, the bug fixed with a regression test, and the same specification re-run once:
  θ = 0.000790 (90% 0.000526–0.001255), α = 7.5, partial share not identified (0.06–1.00, kept at 0.3); Austin
  entered the fit set through WS-TX's coding (2,545 permits, fitted 306); Raleigh 230 vs mean 127 (90% 1–499).
  Superseded by fit 3.
- **Fit 3 results (run once on 2026-10-20 after the fit-3 pre-registration, commit 4aa1113, and the NC rebuild
  that fixed Durham):**
  - *Data:* fit set 16 places, 115 place-years, 2,799 ADU permits (Minneapolis 222, Austin 2016–23 2,545,
    14 suburbs 32); test set Raleigh and Durham 2021–25 (Durham's roll now has 67,180 ADU-eligible parcels).
  - ***θ = 0.001038 per parcel a year, 90% profile interval 0.000453–0.003173*** (0.26 of Portland's 4 per
    1,000); place-effect variance α = 4.735; ***m_o = 1.0 (0.9–1.0), estimated***; m_x not identified
    (0.1–1.0), kept at 0.3. Written to `hazard.yaml` (anchor, `adu_place_effect_variance`) and `adu.yaml`
    (`adu_owner_occupancy_share`) per the decision rule.
  - *Fitted place multipliers:* Austin 10.95, Edina 1.30, Minnetonka 1.29, Minneapolis 0.50, Richfield and
    Roseville 0.39, Burnsville 0.33, Plymouth 0.15, Bloomington 0.06, Blaine 0.02, Eagan, Lakeville and St.
    Louis Park ≈ 0.
  - *Minneapolis by year, observed vs typical-place mean:* 2016 28 vs 15.1; 2017 30 vs 29.6; 2018 25 vs 39.3;
    2019 35 vs 47.4; 2020 28 vs 56.0; 2021 16 vs 60.2; 2022 17 vs 53.0; 2023 14 vs 48.6; 2024 16 vs 49.2; 2025
    13 vs 49.8.
  - *Test:* Raleigh 2021–25 observed 23, 55, 54, 37, 61 (total 230) vs predicted mean 9.0, 19.9, 30.2,
    38.9, 43.1 (total 141; median 11; 90% 0–687); Durham observed 32, 35, 77, 51, 44 (239) vs 15.0, 23.5,
    28.6, 51.7, 53.1 (172; median 15; 90% 0–865). Inside, so not a transport failure by the rule; the
    intervals are wide because a new place's multiplier is unknown.
  - *Reading:* rent, home value and rates explain little of the difference between places; the owner-occupancy
    rule had no measurable effect; Minneapolis's decline after 2020 is not captured (the model rises with the
    ramp and rents). The Portland gap reasons above still apply.
- **Fit 4 pre-registration (written and pushed before fit 4 was run, 2026-10-20; Ben: fit 3 is not on trend):**
  - *Unchanged from fit 3:* fit set (Minneapolis 2016–25, the Twin Cities places with coded ADU rules, Austin
    2016–23), test set (Raleigh and Durham 2021–25), place-year inclusion rule, Poisson counts with a gamma
    place effect (variance α) shared over a place's years, blank rule fields integrated per place, coverage
    (D-021), graded shares m_o and m_x, holdouts (St. Paul never; Charlotte never; no held-out row).
  - *Expected count:* μ_it = θ · u_i · parcels · h_m(θ = 1, β_rate = 0; year t's rent, home value and **real
    construction cost**) · max_r c(type) · coverage · ramp · exp(−β_rate (r_t − r_ref)) · (1 − s_sub)^MM_it ·
    exp(Σ_j b_j x_itj).
  - *Construction cost by year (new):* the pro forma's hard cost per sq ft (2025 level) × the real cost index
    (PPI residential construction inputs / CPI-U, year t ÷ 2025; `market_geo_year.ppi_resid_inputs`). The
    reference place (Portland 2015–19) uses its own era's mean index (2015–19), so only cost changes relative
    to the reference transport.
  - *Rate effect (new, estimated):* β_rate with each year's actual 30-year rate. It replaces the judgment value
    if its 90% profile interval is narrower than 0.30; otherwise the judgment value 0.07 (0–0.15) stays.
  - *Substitution with missing middle (new, C47):* MM_it = 1 when a coded missing-middle rule allowing 2+
    units in single-family zones is in force by 1 July (`config/reforms/*.csv`, theme missing_middle,
    `unit_cap` ≥ 2 or blank, `by_right` not False; a blank `by_right` counts with the share of coded
    missing-middle rows that are by right). Uptake × (1 − s_sub). s_sub is estimated, with a 90% profile
    interval; it is "identified" only if that interval is narrower than 0.8; otherwise s_sub = 0 in the
    scenario and the report says so. In the fit set only Minneapolis (3 units from 2020-01-01) has MM_it = 1.
  - *Covariates for later:* the fit takes a generic table of place-year covariates x_itj with log-linear
    coefficients b_j, so dated ADU programs (fee waivers, pre-approved plans) and fee histories can enter later
    under their own pre-registration. None is added in fit 4.
  - *Diagnostic only (not used for any parameter):* a second fit adds a post-2020 indicator (years ≥ 2021)
    with coefficient γ, reported with its interval. If γ's interval excludes 0, the report says the trend is
    still not explained.
  - *Estimation:* maximum likelihood by coordinate ascent over (log θ, log α, β_rate, s_sub, m_o, m_x);
    90% profile intervals for θ, β_rate, s_sub, m_o and m_x (others re-maximized at each grid point). m_o and
    m_x follow fit 3's rule (estimated only if their interval is narrower than their judgment range).
  - *Test prediction and decision rule:* as fit 3; θ, α, β_rate (if identified), s_sub (if identified), and any
    identified share replace the configured values whatever the test shows. Forward runs keep 2025's real
    construction cost (index 1) and draw the rate path as before.
- **Fit 4: withdrawn before it was run (Ben, 2026-10-20).** The pre-registration above (commit cf123ba) stays
  as written, but no fit 4 was run: adding terms to chase the observed trend was rejected. The ADU estimation
  will be re-specified from the causal diagram (§3) and protocol §5.6–5.7 (staggered-adoption count model
  with year effects, place random effects, an eligible-parcel offset, event-time ramp effects and pre-period
  effect modifiers). Only a tested building block from that round is kept: `hazard.adu_price_to_cost` and
  `adu_mature_hazard` accept a real construction-cost index (`hazard.cost_index_by_year`, PPI residential
  inputs / CPI-U relative to 2025); it defaults to 1, so no current result changes.
- **Decided by:** scenario choices proposed by WS-ENGINE; estimation and split decided by Ben, 2026-10-20.

### D-020 · 2026-10-20 · Scenario geography: units that never share a parcel
- **Found (WS-CORE):** `places_from_store` modelled local-only places (`in_bps` False: Charlotte, Concord and
  other Mecklenburg and Cabarrus towns, 23 MN townships) and the county remainder rows that contain them, so
  their parcels were counted twice.
- **Now (`scenarios/adu.non_overlapping`):** local-only places stay as their own scenario units (they carry
  their own rules); their eligible parcels are subtracted from the remainder of each county they sit in, split
  by Census 2020 county shares (`geoparts.county_shares`), clipped at 0 and flagged. Only remainders whose
  denominator is the ACS fallback overlap: `eligible.allocate_homes` keeps local-only homes in them, while a
  remainder counted from a parcel roll holds only the parcels assigned to the county row (each parcel has one
  jurisdiction). Columns `eligible_parcels_reported` and `overlap_removed` show the change. The baseline
  permit series stays on BPS reporting units.
- **Effect (2026-10-20 tables):** eligible parcels removed: NC 344,992 of 3,413,981 (Mecklenburg's
  remainder 275,566 → 18,920), MN 10,459, OH 0, TX 0. WS-CORE's figures (NC 419,293, OH 4,000) also counted
  remainders built from parcel rolls (e.g. Union County, 27,997, which holds none of its towns' parcels).
- **Open:** places BPS files under a county that are not in `jurisdictions` (Wilmington, Hickory, Salisbury,
  Statesville) carry no rules of their own; a county row's c should become a parcel-weighted mix of the rules
  of the places inside it (with D-021's coverage share).
- **Decided by:** proposed by WS-CORE, implemented by WS-ENGINE, 2026-10-20; for Ben to confirm in the PR.

### D-021 · 2026-10-20 · Proposed: rule coverage (zones, minimum lot sizes) in the ADU rule classifier
- **Gap (WS-CORE):** `rule_restrictions` reads only the rubric's yes/no fields. A rule limited to some zones
  or to lots above a minimum size (Austin's 2015/2023 ADU rules: SF-3 only, lots of 5,750+ sq ft) reads as
  Handbook-equivalent for the whole place. This overstates current rules (understating the Handbook gain) and
  makes such a place a full-coverage observation in the anchor fit (D-019).
- **Proposal (for a follow-up PR; not built here):** each place's eligible parcels split into covered and
  not covered by its rule. Coverage share = share of ADU-eligible parcels whose zoning is in `coverage_zones`
  and whose lot meets `min_lot_sqft`, computed from parcel zoning and lot size where the roll has them; where
  it doesn't, a sourced default by rule scope ("citywide" 1.0; district- or lot-size-limited, judgment 0.5,
  range 0.2–0.8). Then c_place = c × coverage share (uncovered parcels have no rule and get the full Handbook
  increment), in the scenario and in the anchor fit alike. A county remainder's c = the parcel-weighted mix
  of the rules of the places inside it (D-020's open item). `min_lot_sqft > 0` with no parcel data counts as
  limited coverage rather than "partial", so the two adjustments don't overlap.
- **Decided by:** proposed by WS-CORE and WS-ENGINE, 2026-10-20; for Ben.
- **Implemented (2026-10-20, Ben approved):** `scenarios/adu.rule_coverage` and `coverage_map`. Zones and lot
  minimums are measured on each place's single-family detached parcels (latest roll) among parcels whose zoning
  or lot size is known (a written-out district name also matches its code's acronym, e.g. "Urban Neighborhood
  1" = UN1); where a roll can't measure a limit, `adu_rule_zoned_coverage_share` 0.75 (judgment). With no
  zones or lot minimum, a rule covers everything unless its text names a limited area explicitly ("only
  inside/within/in", "within …", new subdivisions, a half-mile corridor): `adu_rule_limited_coverage_share`
  0.2 (judgment). The uncovered share of a rule's type probabilities moves to "none". Examples measured:
  Minneapolis 2023 zones 94%; St. Paul 2016/2018 54%; Austin 2015 rule 64%, 2010 rule 49% (lot minimum from
  parcels × zones judgment). County rows: `county_mix` blends the rules of coded places BPS files under the
  county (Wilmington) by their share of the row's eligible parcels (ACS one-unit detached homes); the mean c
  is right, though a draw still picks one type for the whole row.

### D-022 · 2026-10-20 · Anything not coded is unknown (option C)
- **Decided by Ben (2026-10-20):** a place with no ADU row, and a blank rubric field in a coded row, are
  unknown, never "no rule" or "no restriction".
- **Now (`scenarios/adu.py`):**
  - rules are one of five types: none, owner occupancy only, other restrictions (parking, not by right,
    attached only, cap under 600 sq ft), both, Handbook-equivalent; c = 0, m_o, m_x, m_o·m_x, 1;
  - a blank field restricts with the share of coded rules that restrict it (state share if 5+ coded values,
    else pooled over the four states); a row's type is a probability over the five types;
  - a place with no ADU row takes the mean type probabilities of the coded places in its state and size band
    (<10k, 10–50k, 50k+ people in 2020), falling back to the state's pooled mean, then the all-state mean,
    below 5 coded places (`adu_rule_min_coded`);
  - explicit "no ADUs" rows stay "none" (#164); a citywide parking reform with no minimum settles a blank ADU
    parking field;
  - each simulation draw samples each place's type; the central path uses the expected c; outputs report each
    place's type probabilities, whether its type was drawn, and the drawn shares; a drawn rule with no known
    date is taken as long in force (`adu_unknown_rule_age_years` 10).
- **Counts behind it (config/reforms on main, 2026-10-20; rules in force on 31 December 2025):** coded field
  values restricting / known, pooled: owner occupancy 23/36, parking 18/34, by right 5/37, detached 5/40, size
  0/29. Coded places by state and band (none/partial/Handbook/uncertain): MN 50k+ 5/11/3/1, MN 10–50k 1/4/0/0;
  NC 50k+ 0/0/1/3; OH 50k+ 4/7/1/0, 10–50k 2/1/0/0; TX 50k+ 10/6/2/0. Small places in every state borrow
  their prior from the state's pooled coded places or the all-state mean.
- **Bias to watch:** states coded their largest places first, so priors for small places come from large
  ones. As WS-CORE's ordinance lookup codes more places, the priors and field shares update from the CSVs
  with no code change.
- **Calibration:** blank fields are integrated over (D-019 fits 2 and 3); places with no ADU row stay out of
  the fit.

### D-023 · 2026-10-20 · ADU effect estimated with a staggered-adoption count model (pre-registered; supersedes the D-019 fits)
- **Why:** the D-019 fits calibrated one anchor to places that already allowed ADUs, with no comparison places and no year effects. That departs from the causal diagram (`docs/research/lotline-causal-diagram.md` §3) and the statistical protocol (§5.6–5.7). Common shocks after 2021 (rates, construction costs, the market) could not be separated from the reform, and the modifiers' strength was imposed by judgment, not estimated. Fits 1–3 are superseded as estimates of the effect; fit 4 was withdrawn unrun (Ben, 2026-10-20).
- **Estimand:** additional ADU permits per eligible single-family parcel caused by an ADU rule, by years since it took effect, and how that effect varies with pre-reform conditions. "Additional" means relative to the same place without the rule (protocol §1).
- **Data:**
  - **Places and years:** every Twin Cities metro place with Met Council residential permits, 2016–2025; ADUs are flagged from 2016, so 2016 is the first year and the measurement is the same before and after each reform (C32).
  - **Outcome:** ADU permits per place-year. Minneapolis uses the larger of Met Council and city counts, as in `calibrate_adu.observed_adu_counts`.
  - **Exposure:** eligible parcels (rule 1.1) as the offset.
  - **Excluded:** St. Paul, entirely; it is the V5 blind test. Charlotte from 2023-06-01 is never used.
  - **Places with no dated ADU rule are left out of estimation,** not imputed. The adoption-date run (2026-10-20) fills them, and a place enters once its rule history is coded with a source.
- **Treatment and dose (C10, C11, C13):** D_it = the place's ADU rule in force on 1 July of year t, graded as: none = 0; permit or conditional use required; by right with owner occupancy; by right without it. The grade is multiplied by rule coverage (D-021). The adoption year T_i is the first year a by-right rule is in force. Places never treated (explicit "no ADUs") and not yet treated are the comparisons.
- **Model:** Poisson pseudo-maximum likelihood (PPML) on counts with the log(eligible) offset, place fixed effects and year fixed effects, estimated with Wooldridge's extended two-way fixed-effects estimator (cohort × event-time effects) for staggered adoption. TWFE with unit trends is not used (protocol §5.6).

  E[ADUs_it] = Eligible_it · exp( α_i + γ_t + Σ_k β_k · 1[t − T_i = k] + Σ_m θ_m · (X_im − X̄_m) · 1[t ≥ T_i] + ρ · (r_t − r̄) · 1[t ≥ T_i] + δ · MM_it )

  | Term | Meaning | Causal diagram |
  |---|---|---|
  | α_i | Place fixed effect | C06, C14, C15 (level differences) |
  | γ_t | Year fixed effect | National rates, costs, COVID and the cycle (C01–C03, C42) |
  | β_k | Event-time effects, k = 0…5+ | Ramp and builder learning (C24); grade and coverage enter by scaling the indicator with D_it |
  | θ_m | Effect modifiers, measured before adoption (bad-controls rule, C17) | Price-to-cost from the pro forma at the pre-adoption year (C40); median home value as the owner-equity proxy (C22); pre-reform 1-unit permits per 1,000 eligible parcels (C06); ACS household growth over the 5 years before adoption as the local-demand proxy (C04; a shift-share employment index replaces it if added later) |
  | ρ | Mortgage rate × treated | Rates as an effect modifier (C01, C22): the same rule yields less at higher rates |
  | δ | 2–4 units legal by right on the same lot | ADU ↔ missing-middle substitution (C30); reported as weakly identified if fewer than 5 places change status |

- **Inference:** wild cluster bootstrap by place (999 draws). Randomization inference that permutes adoption years among treated places is reported alongside, because treated places are few.
- **Checks, from causal diagram §5 (all reported, pass or fail):**
  1. **Pre-trend leads** k = −3…−1: jointly not different from 0 at the 10% level.
  2. **Placebo adoption dates** 2 years early: no effect.
  3. **Placebo outcome,** permits in 5+ unit buildings: no effect.
  4. **Excluding 2020–21:** effects within their 90% intervals.
  5. **Leave-one-treated-place-out:** no single place moves the pooled effect by more than its 90% interval.
- **Out-of-sample test (transport, protocol §5.5, §5.8):** with the Minnesota estimates and each place's own pre-reform modifiers, predict ADU permits for Austin (2016–2023, coded rules), Raleigh (2021–2025) and Durham (2019–2025). The test passes if each place's observed total lies in its 80% prediction interval, and the coverage of yearly 80% intervals across the three is between 60% and 95%. Places outside the Minnesota modifier range are flagged, and their intervals widened as in `hazard.widen`.
- **Forecast use:** for a target place, the scenario's added ADUs = Eligible × [exp(η_with rule) − exp(η_without)] summed over 2026–2030. η uses the place's α (or, for places without ADU data, a hierarchical prior by state, size band and modifiers; protocol §5.7), the event-time β, its own modifiers, ρ at the stated rate path (`mortgage_rate_forecast`) and γ_2026–2030 held at the 2025 level with the rate effect added. Uncertainty comes from bootstrap draws of all coefficients plus Poisson-gamma noise. The net-new and formalization shares (D-019) then apply as before.
- **Robustness (reported, not used to choose):** negative-binomial with place random effects (protocol §5.7); the Borusyak imputation estimator; the dose as a binary by-right indicator.
- **What would change the plan:** if the pre-trend check fails, report it and use HonestDiD bounds; there is no re-specification without a new dated entry. If too few places have dated rules after the adoption-date run, report the estimates as underpowered rather than adding assumptions.
- **Code:** `src/lotline/model/estimate_adu.py`, tested by recovering known β, θ and ρ from simulated staggered-adoption panels before any real run.
- **Implementation choices (Ben, 2026-10-20, before the real run):** dose grades in equal steps (1/3, 2/3, 1; `adu.yaml`); T_i is the first year a rule with P(by right) >= 0.5 is in force on 1 July; modifiers are measured at T-1 (price-to-cost with that year's rent and real construction cost; log home value; mean 1-unit permits per 1,000 eligible parcels over T-3..T-1; log household growth T-6..T-1); places that adopted before 2010 (Bloomington, Plymouth) don't inform the modifier terms; a new place's level comes from its own pre-adoption years where it has them, otherwise a draw from the Minnesota places. Hastings was removed before the run (Ben's lookup matched St. Paul's Ord. 23-43).
- **Decided by:** Ben, 2026-10-20.
- **Implementation notes (2026-10-20, WS-ENGINE; choices the specification leaves open, for Ben to confirm
  before the real run):**
  - *Dose values:* the grades are ordered in D-023 but not valued; equal steps are used: permit or conditional
    use 1/3, by right with owner occupancy 2/3, by right without it 1 (`adu.yaml` `adu_dose_grade_*`), times
    coverage (D-021). Blank by_right / owner_occ fields enter with their coded shares (D-022), so the dose is
    an expectation. The binary by-right dose is the robustness check.
  - *Adoption year T_i:* the first year (from 1990) a rule whose P(by right) ≥ 0.5 is in force on 1 July.
    Places adopting before 2016 have only late event times in the panel; cohort cells that are constant within
    a place are collinear with its fixed effect and dropped by the estimator (reported).
  - *Modifiers (year T_i − 1):* price-to-cost from the pro forma with that year's ACS rent (newest vintage,
    not before 2010) and real construction cost (`hazard.cost_index_by_year`); log median home value; BPS
    1-unit permits per 1,000 eligible parcels, mean of T − 3 … T − 1; household growth = log of ACS households
    (B25003) at T − 1 over T − 6 (vintages from 2015 and 2010 at the earliest). Places adopting before 2010
    get modifiers measured after adoption; they are listed.
  - *PPML:* places with no ADU permit in any year are dropped (no finite fixed effect; no information under
    Poisson fixed effects); regressors collinear with the fixed effects are dropped; both are reported.
  - *Bootstrap:* the wild cluster score bootstrap uses Webb six-point weights (few clusters) and CR2-adjusted
    cluster scores; without CR2, standard errors ran ~10–15% low on simulated panels. Intervals are basic
    bootstrap intervals; the lead test is a Wald test with the bootstrap covariance.
  - *Randomization inference:* statistic = the overall effect (event-time cells averaged with counterfactual
    expected permits as weights).
  - *Transport:* a target place's level α comes from its own pre-adoption years (with its sampling error) when
    it has permits then, else a draw from the Minnesota places' α; Minnesota year effects; count noise is
    Poisson-gamma with the panel's overdispersion (moment estimate). Raleigh's panel starts in 2019 and
    Durham's in 2016 so their pre-adoption years inform α; only D-023's test years are scored.
  - *Smoke test of the panel (2026-10-20, counts only):* 21 Twin Cities places with dated ADU rules × 2016–2025
    (164 left out for no dated rule; St. Paul excluded); 12 ever treated (6 adopting in 2016–2025), 9 never
    treated; 13 places have no ADU permit in any year. With today's coding the estimate would be underpowered;
    the run waits for the adoption-date research.
- **First real run aborted (2026-10-20):** the one-time run failed numerically: PPML separation (cohort ×
  event-time cells, and possibly place and modifier combinations, with all-zero outcomes put the maximum
  likelihood at infinity), giving coefficients in the hundreds, exp overflows in the bootstrap and
  randomization inference, absurd transport means, then a crash writing `--out`. The run was treated as
  aborted and **no estimate from it was looked at or interpreted**; its log is committed unread as
  `reports/adu-d023/aborted-2026-10-20-log.txt` (warnings may be truncated). **Fix, mechanical and independent
  of the results:** separation removed before fitting (Correia, Guimarães & Zylkin 2019): places and years
  with all-zero outcomes, one-signed indicator columns whose rows all have zero outcomes (dropped with their
  rows), then the iterated-rectifier check for any remaining separated observations, repeated until nothing
  changes, every drop reported; modifiers entered as z-scores over the treated places (θ per standard
  deviation); the fit fails loudly (`EstimationError`) on non-convergence, |η − offset| > 30, a coefficient
  beyond ±20, or an effectively zero standard error, and the same guards apply in the bootstrap,
  randomization inference, leave-one-out and transport (which also refuses a predicted mean above 5% of
  eligible parcels a year); `--out` is a directory of named CSVs, written only after every stage succeeds.
  Tested on synthetic panels with all-zero cohort cells and with a separating modifier. **One rerun follows.**
- **Rerun (2026-10-20, the one rerun after the fix) stopped by the numerical guard:** the point fit converged
  (11 iterations) but kept only **143 of 760 place-years**: 53 places with no ADU permit in any year and 87
  separated observations were dropped; 21 cohort × event-time cells were dropped (all-zero outcomes or no
  variation left) and 8 more as collinear with the fixed effects, and **all four modifier terms θ and δ were
  collinear with the fixed effects** in what remained. The wild score bootstrap then produced a draw beyond
  the coefficient bound and the run raised `EstimationError`; nothing was written. No estimate was printed
  (the script prints estimates only after the bootstrap). Log: `reports/adu-d023/run-2026-10-20-log.txt`.
  Under "what would change the plan" the result is reported as **underpowered**; no assumption was added and
  no further run was made. Options for Ben (each needs a new dated entry before any run): pool event times
  and cohorts (e.g. one post-adoption effect, or k = 0–1, 2–3, 4+), report the D-023 robustness estimators
  (negative binomial with place random effects, which keeps places with zeros; the Borusyak imputation
  estimator) as primary, or widen the panel (more places with dated rules, earlier ADU-flag years).

### D-024 · 2026-10-20 · Missing-middle effect estimated on a pooled four-state panel (pre-registered; approved before any estimate)
- **Why:** the missing-middle scenario needs an estimate, from observed reforms, of how many extra 2–4 unit
  homes get permitted when 2–4 units become legal on single-family lots. This entry fixes the estimand, sample,
  model, checks and out-of-sample test **before any estimate is run**. It mirrors D-023 and applies its lesson:
  check first whether the data can carry place fixed effects (smoke counts below).
- **Estimand:** additional homes permitted in 2–4 unit buildings per missing-middle eligible parcel, caused by
  a rule that allows 2–4 units on single-family lots, by years since the rule took effect, and how that varies
  with pre-reform conditions. "Additional" means relative to the same place without the rule (protocol §1).
  Gross homes: demolitions and the single-family rebuild they replace are netted out in the scenario, not here
  (causal diagram MM §1).
- **Why a pooled four-state panel, not Minnesota alone:** in the Twin Cities only Minneapolis has a coded
  missing-middle rule (St. Paul is the V5 blind test). One treated city cannot support a staggered design. The
  four reform states have 7 treated places with coded rules, all measured the same way by Census BPS.
- **Data (`src/lotline/model/estimate_mm.py`, `build_panel`):**
  - **Places and years:** every BPS permit-issuing place in MN, NC, OH and TX with at least 10,000 people
    (2020 Census; `mm_estimation_min_population`), plus every place with a coded missing-middle rule;
    2010–2025 (`mm_panel_first_year`, `mm_panel_last_year`): the first year with eligible-parcel rolls and ACS
    for every place, giving Minneapolis and Durham ten years before their reforms.
  - **Outcome:** BPS homes in 2-unit and 3–4 unit buildings (`units_2 + units_3_4`), the same measurement in
    every state and year. Townhouses are 1-unit buildings in BPS and stay out; 5–6 unit buildings are mixed
    into BPS 5+ with large apartments and stay out. A place-year with no BPS row is missing, never 0.
  - **Exposure:** missing-middle eligible parcels (rule 1.1, D-014) as the offset, from the nearest roll; the
    ACS fallback (D-017) supplies 330 of the 560 places' denominators. Place effects absorb level errors;
    only changes over time matter.
  - **Excluded:** St. Paul entirely (V5); Charlotte, Mecklenburg County and every place reporting under it
    entirely (holdout from 2023-06-01, D-012; Charlotte's reform falls in the window).
- **Treatment and dose:** from coded `missing_middle` rows in `config/reforms/*.csv`, in force on 1 July of
  year t. Dose D_it = units grade × approval grade × coverage:
  - units allowed on a single-family lot: 2 → 1/3, 3 → 2/3, 4 or more → 1. The outcome only counts 2–4 unit
    buildings, so a rule allowing more than 4 (St. Paul, Houston) counts as a full dose. The Handbook scenario
    allows 2–6 units: 5–6 unit buildings come from the pro forma side, not this estimate;
  - approval: by right 1, by permit or conditional use 1/3 (`mm_dose_grade_permit`, equal steps as in D-023);
  - coverage of single-family zones measured on parcels as in D-021 (`adu.rule_coverage`, reused as is);
  - blank fields take coded shares (D-022): a blank `by_right` takes the share of coded missing-middle rules
    that are by right (3 of 3 today); a blank cap takes the mean units grade of coded caps.
  - Adoption year T_i: the first year a rule with P(by right) ≥ 0.5 is in force on 1 July. Treated today:
    Minneapolis 2020, Durham city and Durham County 2020, Raleigh 2022, Austin, Houston and Cincinnati 2024.
- **Comparisons:** places with no coded missing-middle rule are unknown under D-022. With only coded
  places there are **no never-treated comparisons**: the 2024 adopters would be the only controls for
  2020–2023, and 2024–2025 would have none. **Decided:** places with no coded rule count as never treated for
  this estimate only. This is a deviation from D-022, stated here. It rests on two points: no statewide rule
  allowing 2–4 units on single-family lots is coded for any of the four states (the pipeline's Minnesota
  records found none as of 2025), and a place mislabelled as untreated pulls the estimate toward zero. The robustness checks bound that risk. To shrink it:
  - places the ordinance pipeline found legalizing 2–4 units should be coded with dates before the run (St.
    Louis Park 2025; Bloomington 2025–26 needs a manual lookup; `docs/research/ordinances/`; WS-MN);
  - places the pipeline found not to allow them (Brooklyn Park, Coon Rapids, Rochester) should be coded as
    explicit "no" rows.
- **Model (main):** Poisson pseudo-maximum likelihood with the log(eligible parcels) offset, place fixed effects
  and **state × year** fixed effects. The four states' markets moved differently, and each state has 56–232
  places. Effects are estimated with Wooldridge's extended two-way fixed effects, pooled into three event-time
  bins:

  E[y_it] = Eligible_it · exp( α_i + γ_{s(i),t} + Σ_b β_b · D_it · 1[t − T_i ∈ b] + Σ_m θ_m · z_im · 1[t ≥ T_i]
  + ρ · (r_t − r̄) · 1[t ≥ T_i] + δ · ADU_it ),  b ∈ {0–1, 2–3, 4+}

  | Term | Meaning | Causal diagram (MM) |
  |---|---|---|
  | α_i | Place fixed effect (includes duplexes some zones already allowed) | C05, C06, C14 (levels) |
  | γ_st | State × year effect | Rates, costs, COVID and the cycle by state (C01–C03, C42) |
  | β_b | Effect by years since adoption, pooled 0–1, 2–3, 4+, scaled by dose | Ramp and builder learning |
  | θ_m | Modifiers measured at T − 1, as z-scores over treated places. Main: price-to-cost of a rental duplex from the pro forma (C40; constant factors cancel in the z-score) and log median home value (the existing-use value a teardown must beat, C46). Robustness only: 2–4 unit homes per 1,000 eligible parcels over T − 3…T − 1 (C06) and log household growth T − 6…T − 1 (C04; the shift-share demand index from thread 3 replaces it when it lands, by a dated note) | Modifiers 1–2 of MM §2 |
  | ρ | Mortgage rate × treated | Developer financing (C45; the national 30-year rate stands in for construction-loan rates) |
  | δ | P(a by-right ADU rule is in force); uncoded places take the coded mean of their state, size band and year | ADU on the same lot competes (C47) |

  - **Why fixed effects here and not for ADUs (smoke counts):** every treated place has 2–4 unit homes in
    most years. A place fixed-effects model keeps 420 of 560 places; the 140 it drops (no 2–4 unit home in any
    year) are all comparisons, and under Poisson fixed effects they carry no information about the effect.
    With seven treated places, the main model has only two modifiers. More would be fitted from as many
    places as parameters.
  - Separation removal, numerical guards and failing loudly are as in D-023 (`estimate_adu.ppml`).
  - **Pre-specified fallback:** if the PPML fit raises `EstimationError` or drops a treated place, the negative
    binomial with place random effects (protocol §5.7; D-025's estimator if approved) becomes the main model,
    with the same terms. No new entry is needed for that switch, and the failure is reported.
- **Inference:** seven treated places is too few for the wild cluster bootstrap to be trusted alone. Reported:
  - the wild cluster score bootstrap by place (Webb weights, CR2, 999 draws, as in D-023) for intervals;
  - randomization inference as the test of "no effect": the seven adoption-year and dose paths are reassigned
    at random to places in the same state and size band (D-022 bands), 999 times. The p-value is the share of
    reassignments with an overall effect at least as large.
- **Checks (all reported, pass or fail; pass rules fixed now):**
  1. **Pre-trend leads** k = −3…−1: jointly not different from 0 at the 10% level.
  2. **Placebo adoption dates** 2 years early, using only pre-adoption years: the 90% interval contains 0.
  3. **Placebo outcome,** BPS homes in 5+ unit buildings: the 90% interval contains 0.
  4. **Substitution (reported, no pass rule):** BPS 1-unit homes as the outcome. A fall is the single-family
     rebuild being replaced (C30), which the scenario nets out; it is not noise.
  5. **Excluding 2020–21:** every bin's effect stays inside the main 90% interval.
  6. **Leave one treated place out** (Durham city and county also left out together, one ordinance): the
     overall effect stays inside the main 90% interval.
  7. **Comparison contamination:** re-fit (a) on places of 50,000+ people only (121 places) and (b) without
     comparison places the ordinance pipeline lists as having a missing-middle ordinance or an unknown status.
     Pass: the overall effect stays inside the main 90% interval.
  8. **Local measurement (reported):** for Minneapolis (Met Council and city permits), Durham and Raleigh
     (city permits), local 2–4 unit counts vs BPS, before and after adoption. If they differ by more than 25% in
     the post years, that city's local-count estimate is shown next to the BPS one.
- **Out-of-sample tests (protocol §5.5, §5.8):**
  - **A (headline): predict North Carolina.** Fit without Durham city, Durham County and Raleigh; NC's year
    effects still come from NC's comparison places. Predict their post-adoption 2–4 unit homes from their own
    pre-adoption level (α from their 2010–2019 or 2010–2021 years, with its sampling error), their modifiers and
    the fitted effects. Pass: each place's observed post-adoption total lies in its 80% prediction interval, and
    the coverage of yearly 80% intervals across the three places is between 60% and 95%.
  - **B: predict Minneapolis** the same way from a fit without it; same pass rule for its single total.
  - Either way, the later bins (2–3, 4+) then rest on one or two cities. This is stated with the results.
    Places outside the fitted modifier range are flagged and their intervals widened as in `hazard.widen`.
- **Forecast use:** for a target place, the scenario's added 2–4 unit homes = Eligible × [exp(η with the
  Handbook rule) − exp(η without)], summed over 2026–2030. The Handbook rule is 4+ units by right citywide
  (dose 1). Observed doses run 0.2–1 (only Houston is at 1), so dose 1 leans on the dose scaling; the binary
  dose check below shows how much. η uses the place's α where it is in the panel, otherwise a draw from places
  in the same state and size band. It also uses the bins' β, the place's modifiers, ρ under
  `mortgage_rate_forecast`, and γ held at the 2025 level with the rate effect added. Uncertainty comes from
  bootstrap draws of all coefficients plus Poisson-gamma noise. Demolitions and the rebuild substitution are
  then netted out in the scenario.
- **Robustness (reported, not used to choose):** the negative binomial with place random effects (it keeps
  the 140 all-zero places and gives the prior for places outside the panel); the Borusyak imputation
  estimator; a binary by-right dose; all four modifiers; the 50,000+ sample; Met Council 2–4 unit permits
  for the Twin Cities alone (2016–2025: 64 places, 1 treated, 40 with no 2–4 unit permit in any year; too thin
  to stand alone).
- **Not in this entry:** the within-city design the causal diagram ranks strongest, which compares eligible
  and ineligible lots in the same city (Raleigh R-1; Durham's suburban tier). It needs permits geocoded to
  zones, a later entry.
- **What would change the plan:** if the pre-trend check fails, report it and use HonestDiD bounds. If leave
  one out fails, report which place drives the effect and show the NB pooled estimate next to it. No other
  re-specification without a new dated entry.
- **Smoke test of the panel (2026-10-20, counts only; `scripts/dev/estimate_mm.py --smoke`):**
  - 560 places × 2010–2025 (MN 100, NC 56, OH 172, TX 232); 8,763 place-years with an outcome (197 missing
    from BPS); 2,682 places under the population floor and 2 holdout places excluded.
  - Treated: 7, all inside the panel years (2020: 3, 2022: 1, 2024: 3). Comparisons: 553, all uncoded.
  - 140 places have no 2–4 unit home in any year, none of them treated; a place fixed-effects model keeps 420;
    73% of place-years are zero.
  - Treated place-years by bin: 0–1: 14 (7 places); 2–3: 8 (4 places); 4+: 6 (3 places).
  - With coded comparisons only: 7 places, 0 never-treated comparisons.
  - 50,000+ sample: 121 places, 10 with no 2–4 unit home in any year.
  - Every treated place has all four modifiers. ADU rules are coded for 102 of the 560 places.
- **Decided by:** Ben, 2026-10-20, as proposed (including the `mm.yaml` choices: the 10,000-person floor and
  the 1/3 permit grade), before any estimate was run.
- **Run (2026-10-20, WS-ENGINE-MM; `scripts/dev/estimate_mm.py --full`, outputs in `reports/mm-d024/`):**
  - **First run aborted (17:06):**
    - PPML diverged (|η − offset| = 119.9), so the pre-specified fallback fired.
    - The script's fallback was a Poisson-gamma place random-effects model (Hausman, Hall & Griliches 1984),
      written in `estimate_mm.fit_re`. Its main estimates and added homes were printed.
    - Randomization inference then crashed: a reassignment's fit raised a plain `ValueError` that the loop did
      not catch. Nothing was written. The log is committed as is: `aborted-2026-10-20-log.txt`.
  - **Fix (mechanical, independent of the results) and one rerun (20:35, Ben: "try again"):**
    - divergence and overflow in `fit_re` raise `EstimationError`;
    - Newton steps are safeguarded: damped when not uphill, and never accepted if they lower the likelihood;
    - log a is held at a bound of 15 when the counts show no place heterogeneity;
    - randomization inference and every check count a failed fit instead of crashing.
    - Same specification and seed. The main fit is deterministic, and its estimates match the aborted run's
      exactly.
  - **The fallback is not "D-025's estimator", which D-024 names.** D-025 (`pooled_adu`) was on main from
    16:30, before both runs. The rerun kept the 17:06 fallback, as instructed. D-025's estimator was run as a
    robustness model, through `estimate_mm.fit_nb` with its code unchanged: on the D-024 panel relabelled so
    that its year effects are D-024's state × year effects and its δ is D-024's ADU term.
    - It converged on the real panel. At its maximum the analytic and numerical scores agree, and no place's
      likelihood jumps.
    - Its mode search can fail on synthetic panels with many never-permitting places (shared notes,
      2026-10-20), but not on this one.
    - **Ben to decide** whether D-025's estimate (below) replaces the fallback's as D-024's main estimate.
      That would follow D-024's wording; the checks would then need running for it.
  - **Implementation choices:**
    - state × year effects as one integer code per state and year;
    - randomization inference: each treated place's whole package moves (adoption year, calendar-year dose
      path, modifiers), within state and size band, to places with any 2–4 unit home;
    - the overall effect weights the bins by counterfactual expected homes (`estimate_adu.aggregate`, as in
      D-023);
    - added homes = fitted minus treatment-off means; their intervals hold place and year effects at the
      estimate;
    - check 7b dropped 16 Minnesota comparison places by name;
    - check 8 re-fits with a city's local counts when they differ from BPS by more than 25%.
  - **Main estimates (Poisson-gamma fallback; log scale; 90% basic bootstrap intervals):**
    - overall **0.77 (0.07 to 1.54)**, i.e. about 2.2 times the 2–4 unit homes at full dose;
    - years 0–1: 0.79 (0.20 to 1.38); 2–3: 1.14 (−0.62 to 2.91); 4+: −0.13 (−2.40 to 1.89);
    - price-to-cost: θ = 0.91 (0.05 to 1.78) per SD; home value: θ = −1.00 (−1.61 to −0.41) per SD;
      rate: ρ = 0.11 (−0.14 to 0.36); ADU rule: δ = −0.53 (−1.09 to 0.08).
    - Read the intervals as narrower than stated. On simulated panels with seven treated places, nominal 90%
      intervals covered 68–85% (`--coverage`).
  - **Randomization inference: p = 0.70** (956 reassignments, 43 not fitted). The effect is no larger than
    where the reform's timing and dose are moved to other places.
  - **Added 2–4 unit homes in the treated places' post-adoption years: 2,650 in all.**
    - **Houston alone accounts for 2,422 (1,426 to 3,188), about 91%.** It is the only full-dose place,
      has no zoning, and its deed restrictions bind (flagged by the methodology review).
    - The others: Durham city 150 (6 to 236), Raleigh 119 (−16 to 189), Minneapolis 93 (−109 to 201),
      Durham County 6, Cincinnati −8, Austin −131 (−286 to −12).
  - **Checks:**
    1. Leads: **pass** (p = 0.59).
    2. Placebo dates: **fail**, 0.54 (0.03 to 1.00).
    3. Placebo outcome (5+ units): **fail**, −1.11 (−1.53 to −0.54).
    4. Substitution (1-unit homes): 0.00 (−0.38 to 0.39).
    5. Excluding 2020–21: **pass**.
    6. Leave one out: **fail**. Without Minneapolis the overall effect is −0.02; the others give 0.56–1.34.
       D-024's rule asks for the NB pooled estimate alongside, and D-025's NB is the robustness line below.
    7. Contamination: 50,000+ only, **pass** (0.94); without the 16 pipeline-flagged places, **pass** (0.74).
    8. Local measurement: Met Council and Minneapolis agree with BPS (ratio 1.00); Raleigh too (0.98). The
       Minneapolis city source is 1.63× and Durham's 1.59×; re-fits with their local counts give 0.03 (−0.46
       to 0.65) and 0.51 (−0.27 to 1.39).
  - **Robustness:**
    - PPML: did not estimate (the same divergence).
    - Imputation estimator: did not estimate (its PPML diverged: |η − offset| = 124.4).
    - **D-025's negative binomial: −0.25 (−1.10 to 0.77)**; bins 0.07, −1.29, −1.85. Its place-year
      overdispersion is large (κ ≈ 5.5, σ ≈ 2.4). The Poisson-gamma model has none beyond the place effect,
      so it weights large-count place-years such as Houston's far more.
    - Binary dose: 0.69 (0.30 to 1.13).
    - All four modifiers: 1.35 (0.34 to 2.45).
    - Met Council, Twin Cities alone: −0.79 (−3.02 to 1.82).
  - **Out-of-sample tests:**
    - **A (North Carolina): fail.** Durham city 279 observed vs 80% interval 35–283 (inside); Raleigh 263
      vs 90–378 (inside); Durham County 12 vs 0–7 (outside). Yearly coverage 75%.
    - **B (Minneapolis): fail.** 304 observed vs 63–290; yearly coverage 67%.
    - D-024's rule (every total inside its 80% interval) passes only about half the time for three places
      even when the model is right (0.8³ ≈ 0.51). This is noted, not changed.
  - **Reading:** this run gives no credible estimate of the missing-middle effect.
    - The central estimate is positive, but randomization inference finds nothing unusual (p = 0.70).
    - Two placebo checks fail, one city drives the result, and D-025's model, which fits overdispersion
      better, gives a negative estimate with an interval spanning 0.
    - Both out-of-sample tests fail, and Houston supplies nine-tenths of the added homes.
    - The scenario should not take this as its missing-middle evidence prong without a new dated entry.
  - **Open:** WS-MN has not yet coded St. Louis Park's 2025 rule or the explicit "no" rows; check 7b covers
    that gap.
- **Switch to D-025's estimator (2026-10-21, Ben; written before the run of its checks):**
  - **Why:** D-024 names "D-025's estimator if approved" as the fallback. D-025 was approved and on main
    (16:30, 2026-10-20) before both runs, and its estimator converges on the real panel. The 2026-10-20 runs
    used the Poisson-gamma model instead.
  - **Decision:** D-024's main estimate is now D-025's negative binomial with normal place random effects
    (`pooled_adu`, unchanged, through `estimate_mm.fit_nb`). The Poisson-gamma run stays reported as the
    comparison. Its point estimate on the real panel is already known from the 2026-10-20 robustness line:
    −0.25 (−1.10 to 0.77).
  - **One run (Ben approves exactly one):** the same `--full` pipeline, spec and seed, with `nb` as the main
    model (`--method nb`). It covers:
    - the wild score bootstrap (999 draws) and added homes;
    - randomization inference (999 reassignments);
    - checks 1–8, where leave-one-out covers Minneapolis and Houston dependence (each treated place left out,
      plus Durham city and county together);
    - robustness: PPML, Poisson-gamma, binary dose, four modifiers, Met Council alone;
    - out-of-sample tests A and B with the same pass rules.
  - **Convergence rule (fixed now):**
    - A fit that raises `EstimationError` is not used: BFGS did not converge, the Hessian was not negative
      definite, a coefficient left ±20, or an SE was effectively 0.
    - For randomization inference, failed reassignments are skipped and counted. p is the share of the
      fitted reassignments with |overall effect| ≥ the observed one.
    - **If more than 10% of reassignments fail, p is reported as unreliable,** because failures may not be
      random.
    - A check whose fit fails is reported as "could not be estimated", which counts as a fail.
  - **The overall effect** weights the bins by counterfactual expected homes (as for the fallback), so the
    two models compare like with like. D-025's own place-year weighting is not used here.
  - Outputs go to `reports/mm-d024-nb/`, next to the fallback's `reports/mm-d024/`.
- **Run with D-025's estimator (2026-10-21, 06:35–19:47; `--full --method nb`, outputs in
  `reports/mm-d024-nb/`):** the one approved run. It completed.
  - **Side by side** (log scale with 90% intervals; e^x − 1 is the proportional change in 2–4 unit homes at
    full dose):

    | | D-025 negative binomial (main) | Poisson-gamma fallback (2026-10-20) |
    |---|---|---|
    | Overall effect | **−0.25 (−1.05 to 0.86)** | 0.77 (0.07 to 1.54) |
    | Years 0–1 / 2–3 / 4+ | 0.07 / −1.29 / −1.85 | 0.79 / 1.14 / −0.13 |
    | Randomization inference | p = 0.96 (973 fitted, 26 failed: reliable) | p = 0.70 (956 fitted, 43 failed) |
    | 1. Pre-trend leads | pass (p = 0.59) | pass (p = 0.59) |
    | 2. Placebo dates | pass: 0.39 (−0.17 to 0.95) | **fail**: 0.54 (0.03 to 1.00) |
    | 3. Placebo outcome, 5+ units | pass: −2.01 (−3.21 to 1.29) | **fail**: −1.11 (−1.53 to −0.54) |
    | 4. Substitution, 1-unit homes (no rule) | −0.64 (−0.96 to −0.34) | 0.00 (−0.38 to 0.39) |
    | 5. Excluding 2020–21 | pass | pass |
    | 6. Leave one out (Minneapolis; Houston) | pass (−0.68; −0.57; all −0.71 to −0.12) | **fail** (Minneapolis out: −0.02) |
    | 7. Contamination (a) 50,000+; (b) pipeline-flagged dropped | pass (−0.19); pass (−0.51) | pass (0.94); pass (0.74) |
    | 8. Local counts re-fit (Minneapolis; Durham) | −0.64; −0.33 | 0.03; 0.51 |
    | Out-of-sample A (NC) / B (Minneapolis) | **could not be estimated** (rate guard) | **fail** / **fail** |
    | Added 2–4 unit homes, all 7 places | 2,631; Houston 2,338 (−1,390 to 4,048) | 2,650; Houston 2,422 (1,426 to 3,188) |

  - **D-025's other terms:**
    - price-to-cost: θ = 1.19 (0.34 to 1.99) per SD;
    - home value: θ = −1.23 (−1.99 to −0.44) per SD;
    - rate × treated: ρ = 0.43 (0.13 to 0.70);
    - ADU rule: δ = 0.06 (−0.80 to 1.04).
  - **D-025's robustness:**
    - binary dose: −0.23 (−0.79 to 0.52);
    - four modifiers: −0.83 (−1.80 to 0.50);
    - Met Council alone: −2.22 (−5.38 to 1.60);
    - Poisson-gamma: 0.77, as before;
    - PPML and the imputation estimator: did not estimate (PPML diverges).
  - **Out-of-sample:** both tests stopped at the guard that refuses a predicted rate above 5% of eligible
    parcels a year in any draw (D-023's rule, applied to every draw). Durham's and Minneapolis's draws
    combine wide bin effects with the modifier and rate terms. Under the convergence rule this counts as a
    fail.
  - **Added homes:** D-025's total comes from the modifier and rate terms, not the bins. With ρ > 0 and the
    2024–25 rates, and Houston's modifiers, its predicted gain is positive although the bin effects are
    negative. Its interval spans 0.
  - **Interval coverage:** the simulation that found too-narrow intervals (68–85%) tested PPML. D-025's
    coverage on this design has not been measured.
  - **Reading for a policymaker:**
    - D-025's estimate is the more trustworthy of the two. It allows for the year-to-year noise in permit
      counts, and it passes the three checks the fallback failed (placebo dates, placebo outcome, leave one
      out).
    - What it finds: within 2–6 years of the rule, the seven cities show no detectable rise in 2–4 unit
      permits relative to similar places. The central estimate is a 22% fall (−0.25). The interval runs from
      a 65% fall to a 136% rise, and the reshuffled reform dates produce effects this large 96% of the time.
    - **Neither estimate is credible enough to drive the scenario effects:**
      - the fallback fails three checks and both out-of-sample tests;
      - D-025's is too imprecise to size an effect, and its out-of-sample tests could not be run.
    - **Recommendation:** use the in-state estimate as validation only. The scenario's missing-middle effect
      should come from the pro forma and the external evidence. This result says a large short-run jump is not
      what these cities saw, and the pro forma's ramp should be consistent with that.
  - **Run time:** 13 hours, 12.5 of them randomization inference (999 refits at roughly 6 minutes each on 8
    workers, against about 1.5 minutes measured for single fits).
  - **Code as run:** `pooled_adu` as of commit 448be4c. Main's later changes to it were not used: score
    accumulation by `bincount` (identical to 1e-10, faster) and D-025's own retry-from-main-estimates
    convergence rule. D-024's convergence rule (above) applied instead.

### D-025 · 2026-10-20 · ADU effect: pooled hierarchical negative binomial (pre-registered; main model replacing D-023's)
- **Why:** D-023's fixed-effects PPML was underpowered on the Twin Cities panel (53 places never recorded an
  ADU, 143 of 760 place-years kept, no modifier identified, the bootstrap tripped the guard; D-023 notes).
  Ben approved options 1 and 2 together (2026-10-20): pool the event-time effects and make the protocol's
  pooled model (§5.7) the main model. Written and pushed before any run of it on real data.
- **Main model (`src/lotline/model/pooled_adu.py`):**

  y_it ~ NegBin(mean μ_it, variance μ + κμ²),
  μ_it = Eligible_it · exp( a + u_i + γ_t + Σ_b β_b · D_it · 1[t − T_i ∈ band b] + Σ_m θ_m · z_im · 1[t ≥ T_i]
                            + ρ · (r_t − r̄) · 1[t ≥ T_i] + δ · MM_it ),  u_i ~ Normal(0, σ²)

  - bands b: event time k = 0–1, 2–3, 4+; D_it as in D-023 (grade × coverage, blanks per D-022);
  - u_i: place random effects (partial pooling: places with no ADU stay in, shrunk to the mean);
    γ_t: year fixed effects (first year 0); log(eligible parcels) offset;
  - z_im: the D-023 pre-adoption modifiers as z-scores over the treated places (θ per SD); places adopting
    before 2010 don't inform them (Ben, D-023 run choices); modifiers stay in and are flagged **weakly
    identified** when their 90% interval spans more than 1 on the log scale; never dropped silently;
  - r̄: the panel's mean rate.
- **Estimation:** maximum marginal likelihood; each place's integral over u_i by adaptive Gauss-Hermite
  quadrature with 31 nodes (15 proved too few for skewed places against brute-force integration in
  development); BFGS with analytic scores (posterior-weighted quadrature sums; checked against numerical
  derivatives); log σ and log κ mapped through tanh to stay within ±6 and ±8, and a variance parameter at its
  limit (no place heterogeneity, or Poisson counts) is held there and reported.
- **Separation and identification:** columns with no non-zero value, or whose non-zero rows all have zero
  counts, are dropped and reported; the iterated rectifier (Correia, Guimarães & Zylkin 2019) on the fixed
  design drops any separated rows; columns that become collinear are then dropped, intercept first; all
  reported. The fit fails loudly (`EstimationError`) if BFGS doesn't converge, a coefficient other than the
  intercept leaves ±20, the Hessian (free parameters) is not negative definite, or an SE is effectively 0.
- **Inference:** wild cluster score bootstrap by place, 999 draws, Webb weights (one Newton step from the
  estimate with the analytic place scores); basic bootstrap 90% intervals. **Overall effect** = the band
  effects averaged with weights equal to the treated place-years in each band. Randomization inference: 999
  permutations of adoption years among treated places, re-fitting the model; statistic = the overall effect.
- **Checks (D-023, same pass rules, applied to this model):** pre-trend leads k = −3…−1 jointly zero (Wald
  with the bootstrap covariance, pass p ≥ 0.10); placebo adoption 2 years early on pre-adoption data
  (overall effect's 90% interval contains 0); placebo outcome, permits in 5+ unit buildings (same); excluding
  2020–21 (band effects and overall effect inside the main 90% intervals); leaving out each treated place
  (overall effect inside the main 90% interval).
- **Robustness (reported, not used to choose):** D-023's fixed-effects PPML with the pooled bands (reported
  as "did not estimate" with the guard's message if it fails); the Borusyak-Jaravel-Spiess imputation
  estimator for counts (PPML with place and year effects on untreated place-years, imputed untreated means for
  treated place-years, effect per band = log Σy / Σμ̂0; place-cluster pairs bootstrap, 999 draws); the main
  model with a binary by-right dose.
- **Transport test (D-023 rule):** Austin 2016–2023, Raleigh 2021–2025, Durham 2019–2025, predicted with
  this model's bootstrap draws and year effects, each place's own pre-adoption modifiers, its random effect
  from its pre-adoption years (posterior mode and curvature, a normal draw) when it has permits then, else
  u ~ Normal(0, σ²), negative-binomial counts; widened outside the Minnesota modifier range (as D-023). Passes
  if each place's observed total lies in its 80% interval and yearly 80% coverage is 60–95%. Raises on
  non-finite or absurd (> 5% of eligible parcels a year) means.
- **Sample, holdouts, exclusions:** as D-023 (Twin Cities places with Met Council permits, 2016–2025; St.
  Paul out entirely; Charlotte from 2023-06 never used; places with no dated ADU rule left out and counted).
- **Simulation properties (development, before any real run):** on synthetic panels with ~70% all-zero
  places and ~50–130 ADU permits, band effects, θ, ρ and δ were covered by their 90% intervals in at least
  22 of 30 panels each; with no reform effect and a −0.7 common shock from 2022, the overall effect's 90%
  interval contained 0 in 87–97% of 70 panels, with a small negative lean (~−0.15, a third of its spread).
- **Run once;** whatever it shows is reported. No re-specification without a new dated entry.
- **Decided by:** Ben, 2026-10-20 (options 1 and 2); details written by WS-ENGINE before the run.
- **The run (2026-10-20, once; log `reports/adu-d025/run-2026-10-20-log.txt`):** the main model converged on
  the full panel (76 places, 760 place-years, 31 treated, 53 with no ADU in any year; no column dropped, no
  separated rows, no variance parameter at a bound) and its estimates with bootstrap intervals were printed.
  The run then **stopped at randomization inference**: one of the 999 refits with permuted adoption years
  did not converge (BFGS) and the guard raised `EstimationError`, so randomization inference, the five checks,
  the robustness estimators and the transport test were not computed and no CSV was written. The main-model
  estimates are reported as they stand, without those checks. Not re-run. Decision needed (new dated entry):
  how to treat a permutation refit that does not converge (e.g. count and report failed permutations and
  compute the p-value over the rest, or restart BFGS from the main estimate), then run the remaining stages
  once.
- **Convergence rule for repeated refits (Ben, 2026-10-20; written before the remaining stages are run):**
  in any stage that refits the model many times (randomization inference, the wild bootstrap, leave-one-out
  and the checks), a refit that does not converge is retried once, starting from the main-model estimates;
  if it still fails it is excluded and counted, and results are reported over the rest ("998 of 999
  converged; p over 998"). Isolated failures never stop the run. A stage stops, and is reported as not
  computed, only if failures exceed 5% of its refits; a stage that is a single refit (a check, the binary
  dose) is reported as not computed if it fails after the retry, and the run continues. Wild-bootstrap draws
  are one Newton step, not refits: a draw beyond the coefficient bound is excluded and counted the same way.
  The remaining stages (randomization inference, the five checks, robustness, transport) are then run once,
  reusing the main model as estimated: its fit is recomputed deterministically only to recover the Hessian
  and place scores, and checked to match the logged estimates.
- **Remaining stages run (2026-10-20, once; log `reports/adu-d025/remaining-2026-10-20-log.txt`, 5 h 07 min):**
  the main model was recomputed and matched all 22 logged estimates to 1e-4 (reused, unchanged); its wild
  bootstrap kept 999 of 999 draws. **Randomization inference: 928 of 999 permutation refits converged (84 on
  the retry from the main estimates, 71 excluded = 7.1%), above the 5% limit, so the stage is not computed.**
  A defect in the run script then stopped the whole run instead of only that stage (the stage failure was not
  caught), so the five checks, the robustness estimators and the transport test were not run. Fixed in code
  (the script now records a failed stage and continues; randomization inference stops as soon as its 5%
  limit is broken) but **not re-run**: running the checks, robustness and transport needs Ben's go-ahead.
  Reading: about 1 in 14 permuted adoption-date panels does not converge even after a retry.
- **Checks, robustness and transport run (2026-10-21, once; log `reports/adu-d025/stages-2026-10-21-log.txt`;
  Ben approved; refits sped up first by an identical score accumulation, 7442d47):** main model reused
  (matched all 22 logged estimates; bootstrap 999/999 kept). Randomization inference not re-attempted: **not
  computed: 71 of 999 (7.1%) failed, above the 5% limit**. Checks against D-023's pass rules:
  1. pre-trend leads: Wald 5.94, **p = 0.025 → fails** (the D-023 rule calls for HonestDiD bounds);
  2. placebo dates (−2 years): **not computed** (the refit did not converge after a retry);
  3. placebo outcome (5+ units): 0.48 (−0.62 to 1.64) → passes;
  4. excluding 2020–21: overall 2.91, every band and the overall effect inside the main intervals → passes
     (the refit converged on the retry);
  5. leave one treated place out: 31 of 31 refits converged (3 on retry); no place moves the overall effect
     outside its interval → passes.
  Robustness: fixed-effects PPML (193 rows kept; two modifiers collinear with fixed effects): bands −0.16,
  −0.59, −0.39 with SEs ≈ 2.4 (uninformative); Borusyak imputation: only 7 treated place-years imputable
  (162 not: their places have no permits before adoption): bands −0.52 (−1.71 to 0.68), −1.55 (−3.09 to
  −0.35), 4+ not estimable, overall −0.94 (−2.25 to 0.30); binary dose: overall 1.50 (0.33 to 2.67), bands
  1.48, 1.23, 1.61. **The robustness estimators do not support the main estimate's size, and the imputation
  estimate has the opposite sign on very few rows.** Transport: **not computed**: the code checked single
  predictive draws against the 5% limit, while this entry specifies the predicted mean; with σ ≈ 2.1 Austin's
  draws (no pre-adoption years, so u from the prior) exceeded it. Fixed to check the mean, with a test, and a
  transport failure now records the stage instead of stopping the run; **not re-run** pending Ben.
- **Transport re-run (2026-10-21, once, Ben approved; log `reports/adu-d025/transport-2026-10-21-log.txt`):**
  transport only, with the guard on the predicted mean; main model reused (matched all 22 logged estimates).
  **Fails the D-023 rule:** totals inside their 80% intervals: Austin no (observed 2,545 vs P10–P90 0–279),
  Raleigh no (230 vs 0–49), Durham yes (269 vs 9–272); yearly coverage 15% (rule 60–95%). No place is outside
  the Minnesota modifier range. Austin has no pre-adoption years in its window (adopted 2010), so its effect is
  drawn from the prior; in Raleigh (2022 on) and Durham (2020 on) the missing-middle term δ = −2.69, identified
  from Minneapolis alone, pushes predictions far below what was observed.
- **HonestDiD bounds: choices fixed before running (2026-10-21, WS-ENGINE; Ben asked for them because the
  pre-trend test failed, as D-023 pre-registers; Rambachan & Roth 2023):**
  - *Event study input:* the pre-trend-leads refit (the one check 1 used): the lead coefficients for event
    times k = −3, −2, −1 are the pre-period coefficients, relative to the omitted periods (k ≤ −4 and the
    never-treated). That reference, not k = −1, is normalised to 0, so the restrictions chain from
    δ_{−4} = 0 through the estimated δ_{−3}, δ_{−2}, δ_{−1}.
  - *Target:* the pooled post-adoption effect at realised doses, θ = the mean over treated place-years with
    k ≥ 0 of β_band(k) × dose_it (same bands, weights by place-years). The bias for that target is
    Σ_k ω_k δ_k, where ω_k is the share of those place-years at event time k (k = 0 … the panel's largest),
    since the leads are indicators, not dose-scaled.
  - *Relative magnitudes, Δ^RM(M̄):* every post-period step |δ_k − δ_{k−1}| ≤ M̄ × M_pre, with
    M_pre = max(|δ_{−3}|, |δ_{−2} − δ_{−3}|, |δ_{−1} − δ_{−2}|). The bias is in δ_{−1} ± M̄ M_pre Σ_k ω_k (k + 1)
    (ω ≥ 0, so the extreme is every step at the bound). M̄ ∈ {0.5, 1, 1.5, 2}.
  - *Smoothness, Δ^SD(M):* post-period second differences at most M, extrapolating the last pre-period slope
    s = δ_{−1} − δ_{−2}. The bias is in Σ_k ω_k [δ_{−1} + (k + 1) s] ± M Σ_k ω_k (k + 1)(k + 2) / 2.
    M ∈ {0, 0.05, 0.1, 0.2} (log points per year²; M = 0 is linear extrapolation).
  - *Inference:* the identified set's bounds are recomputed on each of the leads refit's 999 bootstrap draws
    (θ, δ and M_pre all re-drawn). The 90% robust interval runs from the 5th percentile of the lower bound to
    the 95th percentile of the upper bound. This is simpler than Rambachan & Roth's conditional (ARP) and
    FLCI intervals, and conservative.
  - *Reported:* identified set and robust interval for each M̄ and M, the breakdown M̄ (the smallest at which the
    interval includes 0), the original θ, and the ω_k. No result is used to choose a specification.
  - *Code:* `pooled_adu.honest_bounds`, tested on a synthetic event study with a known linear violation.
- **Implementation note: faster refits, estimates unchanged (2026-10-22, Claude Code; not a new decision):**
  real runs were slow (randomization inference took hours; hard refits run to the BFGS iteration limit).
  `pooled_adu` now (1) evaluates all 31 quadrature nodes at once with the same arithmetic in the same order,
  so log-likelihoods, scores, BFGS paths and estimates are **bit-identical** to the first runs'; (2) computes
  the Hessian analytically (Louis' identity) instead of by central differences of the analytic gradient,
  which agrees to 1e-7 relative and doesn't enter the estimate (`hessian="numerical"` keeps the old one);
  (3) can run the independent refits (randomization inference, leave-one-out, the single-refit checks) in
  parallel processes, with every permutation drawn up front in the serial order and results read back in
  order, so outputs, convergence counts and the 5% stop are the serial run's (`--workers`).
  **Checked on synthetic panels:** 999 permutations gave the same p and the same 999 permuted effects to the
  last bit (719 s → 342 s serial, 95 s on 8 processes); 360 hard refits (6 panels with retries and exclusions)
  gave identical effects and identical counts (303 first, 27 retried, 30 excluded) 3.5× faster. A warm start
  of BFGS from the main fit's curvature was tried and **not adopted**: its estimates differ from a cold
  start's at the stopping tolerance (~1e-4) and on the hard panels it excluded 41 refits instead of 30
  (`WARM_START`, off). A real rerun still needs Ben's approval; the scripts' check against the logged
  estimates (1e-4) is how it would confirm equivalence. Tests: `tests/model/test_pooled_adu.py` (speed
  section).

### D-029 · 2026-10-20 · Baseline calibration fixes and state-total scoring (pre-declared before any run)
- **Why:** a review on synthetic data (2026-10-20, coordinator session) found five problems in the baseline
  engine. In simulation, log forecast error against log(origin level / 5-year mean) had correlation 0.66,
  state-year P10–P90 coverage was 74% and 5-year total coverage 68% (nominal 80%). (1) The cycle's random
  walk starts at 1 from the level-window mean, not at the state's level in the origin year
  (`model/baseline.py`), a likely cause of the NC/TX under-forecast (D-006, D-011). (2) Spec C applies
  exp(β_h · g + β_p · q) with uncentred signals while dropping β_0 (`model/demand.py`), so a place at average
  demand gets a multiplier that is not 1; D-007's rejection of spec C rests on that bug, and its test
  re-implemented the formula and missed it. (3) The negative-binomial 1/k and the place's own variance
  (`use_direct_variance`) are estimated on raw annual counts that already contain the cycle, so cycle variance
  is counted twice. (4) The same `default_rng(simulation_seed)` is restarted for every size class, so classes
  share random numbers by accident. (5) The backtest scores only place-years, never state totals, and the V1
  windows have been used to choose specifications.
- **Fixed now, before any run (each with a hand-worked synthetic test):**
  1. **Cycle starts at the origin-year state level** (`cycle_start_at_origin` = 1). Each place's level is
     multiplied by a_s = S_T / S̄, where S_t is the state's total of the size class over the places that have a
     level, S_T its origin-year value and S̄ its mean over the level window; the random walk then runs from
     there, so E[S_{T+h}] = S_T when nothing changes. The level's variance scales by a_s². This is
     `state_momentum` with a 1-year recent window; if `use_state_momentum` = 1 its factor replaces a_s (never
     both). 0 restores the old start.
  2. **Spec C centred at the fit-sample means.** Multiplier = exp(β_h (g − ḡ) + β_p (q − q̄)), with ḡ, q̄ the
     means of g and q over the Poisson fit sample (the regression is fitted on the centred signals; slopes are
     unchanged, β_0 becomes the drift at average demand). β_0 stays unapplied, as D-006 intended: a place at
     average demand keeps spec B's level.
  3. **Dispersion on detrended counts** (`detrend_dispersion` = 1). Before 1/k and the place's own variance of
     annual rates are computed, each place-year count (and rate) is divided by the state's cycle index for that
     year, s_t = S_t / S̄ over the level window (s_t = 1 where S_t = 0). With no cycle (s_t ≡ 1) both estimates
     are exactly as before. 0 restores the raw estimates.
  4. **Random numbers per size class**: the per-place draws come from `default_rng([seed, size class column,
     state, origin])`, so classes and states never share random numbers by accident. The cycle years stay
     shared on purpose (D-011).
  5. **State-total scoring in V1.** For every state, fit end, size class and forecast year, the scored places'
     draws are summed draw by draw (so the shared cycle is kept), and compared with the sum of the same places'
     observed counts; also the window total (all forecast years, places scored in every year). Reported: the
     randomized P10–P90 coverage (D-003), the PIT histogram in deciles (non-randomized PIT, Czado et al. 2009),
     the CRPS of the summed draws, and absolute error of the P50 of the sum against the benchmarks' sums.
     These are **reported, not new pass criteria**; 80% is the reference.
- **V1 is a development set.** The 2016/2018/2020 windows have been used to choose among specs A, B and C,
  state momentum, the D-011 cycle fix and the scoring floor, so V1 scores are in-sample for specification
  choice and are labelled "development set" in the backtest output and reports. Confirmatory evidence comes
  only from the holdout tests.
- **Runs declared now (MN NC OH TX, fit ends 2016/2018/2020, eligibility rule as on `main`):** spec B old
  (`main` before this change) and new (all five fixes), place-level and state-level; attribution runs of the
  new code with `cycle_start_at_origin` = 0 and with `detrend_dispersion` = 0; spec C once with the fix. All
  are reported in the PR, whatever they show. No parameter is tuned on these runs; adopting the new baseline,
  and whether spec C deserves another look, is Ben's decision, logged as a later entry.
- **Decided by:** pre-declared by Claude Code (WS-ENGINE) at the coordinator session's request, 2026-10-20;
  Ben to confirm in the PR.

### D-030 · 2026-10-20 · ADU scenario: how the uncertainty draws are made
- **Was (`scenarios/adu.py` `draw_params`, `run`):** every parameter drawn triangular(low, central, high),
  including the estimated anchor `adu_mature_hazard_ref` (1.038e-3, 90% profile interval 0.453e-3–3.173e-3),
  whose triangular median is 1.47e-3, 41% above the estimate; the place-effect variance α fixed at 4.735; the
  extrapolation noise z drawn independently for every place, so it averaged out in state totals; the 2015–25
  mortgage stress range drawn triangular(2.96, 6.60, 6.81) (mean 5.46%) as if it were a forecast, independently
  of the cap rate and construction-loan rate; and the judgment parameters drawn independently of an anchor that
  was fitted at their central values.
- **Now:**
  - the anchor and α are lognormal with median at the estimate and log-SD from the 90% interval,
    (ln high − ln low) / 3.29 (anchor 0.592, the fit's own predictive-check convention; α 0.281 from the fit's
    observed information, giving 2.98–7.52); their correlation from the observed information (0.004);
  - each draw shifts log anchor and log α by Σ_j g_j (p_j − central p_j), g_j = d log θ̂ / d p_j from refitting
    the D-019 fit 3 likelihood with each judgment parameter moved by ±10% of its range
    (`scripts/dev/calibrate_adu.py --draw-terms` → `config/params/adu_anchor.yaml`; 19 parameters enter the
    fit, the largest being the partial-rule share, −3.05 per unit, and the ramp half-life, +0.27 per year);
  - the extrapolation noise is √s · z_draw + √(1 − s) · e_place with `adu_extrapolation_shared_share` s = 1.0
    (choice: it is a transport-model error; place-to-place differences are already in the fitted place
    effects); 0.5 is a sensitivity;
  - the mortgage rate is held at the central 6.60% in the forecast draws; its 2015–25 low and high are run as
    sensitivities (`scripts/dev/adu_dev_run.py`), so the cap-rate and loan-rate draws no longer mix with a
    rate scenario.
- **Effect (development run, origin 2025, five-year additional homes, P10 / P50 / P90):** Minnesota
  779 / 1,556 / 2,880 → 271 / 845 / 2,623; North Carolina 1,044 / 2,272 / 4,847 → 355 / 1,212 / 4,059; Ohio
  574 / 1,262 / 2,920 → 133 / 506 / 2,462; Texas 4,074 / 8,211 / 16,607 → 1,334 / 4,417 / 15,515. Rates at
  2.96% raise every state by about 30%; at 6.81%, under 2%.
- **Found while doing it, not changed here:** re-running the fit 3 likelihood on today's coded rules gives
  41 places and 253 place-years (θ̂ 0.000879, α̂ 3.52), not the 16 places and 115 place-years behind the
  configured 0.001038 and 4.735; the observed-information SE and the slopes come from today's fit set and are
  applied around the configured values. Refreshing the anchor itself is a separate decision.
- **Why:** reviewing the ADU ranges (2026-10-20) found them biased upward at the median and too narrow at the
  state level. Every result must be a range that a reader can trust (Rules; CLAUDE.md).
- **Decided by:** proposed by Claude Code (ADU draws fix), for Ben to confirm.

### D-031 · 2026-10-21 · ADU effect: additive imputation as robustness to D-025, and review fixes ported to the D-025 path (written after D-025's main estimate was seen; not the main estimator)
- **What had been seen when this was written:** D-025's main estimate (overall 2.26 on the log scale, 90%
  interval 0.22–4.21) and its 2026-10-21 checks and robustness results (above). **This entry cannot change
  the D-025 main result.** It adds a robustness estimator, fixes defects in code the remaining D-025 stages
  use, and declares sensitivity runs before those stages are run. It was first drafted on 2026-10-20 (under a
  number since reserved by handoff 09) as a proposed replacement for D-023's main estimator. Ben kept D-025 as the main model (2026-10-21),
  so it was renumbered and reframed. No D-031 estimate has been computed on real data.
- **The 2026-10-20 review of D-023 (checked against the code and reproduced on synthetic panels), and what
  still applies:**
  1. treated places with no ADU before adoption had their pre-years dropped as separated, and their cohort
     cells entered the aggregate as near-zero contrasts (a simulated true log-50 effect came out near
     2.5–3.2); 2. places treated before 2016, and the 2016 cohort, have no untreated year, so already-treated
     places identified the year effects; 3. with singleton cohorts θ × post was collinear with the cohort
     cells; 4. the CR2 score bootstrap undercovered with singleton cohorts (37% for a 90% interval over 30
     synthetic panels). These are defects of D-023's fixed-effects design, which D-025 replaced. D-025's own
     imputation robustness run shows the data side of defect 1: 162 of 169 treated place-years could not be
     imputed, because their places had no permits before adoption.
  5. Permit or conditional-use places count as never treated, and the dose before T is ignored. This still
     holds in D-025 and is **not changed** here; the D-031 estimator handles it with a replaced-rule control.
  6. Randomization inference permuted T but not the dose path: **applies to `pooled_adu`; fixed (a).**
  7. D-023's transport used the largest year effect after the panel. D-025's transport refuses years
     outside the estimation years, so this does not apply.
  8. Household growth was measured from max(T − 1, 2015), giving 2010–15 adopters post-adoption growth. It
     is in the shared panel builder: **fixed (b).**
- **Deviations from D-025, written before its remaining stages (randomization inference, placebo dates,
  transport, HonestDiD) are run:**
  - **(a) Randomization inference moves each place's dose path with its permuted adoption year**
    (`estimate_adu.permute_adoption`): dose_new(t) = dose_old(t − (T_new − T_old)), held at the first
    observed value before the panel and the last after it. The 2026-10-20 attempt (7.1% of refits failed)
    permuted T only. A permuted place's post years then carried its old dose, often 0 or a permit grade. That
    may have contributed to the failed refits; this is not tested.
  - **(b) Household growth** = log(households at T − 1 / households at T − 6), and **missing** unless both
    ACS vintages exist (`estimate_adu.household_growth`). For places adopting in 2010–15 the modifier
    becomes missing, which means a zero deviation in the design. The D-025 main fit used the defective
    values, so `estimate_pooled_adu.py --remaining` will stop at its 1e-4 match check. **Decision for Ben:**
    (i) re-estimate the main model once on the corrected panel, report both, and condition the remaining
    stages on the corrected one (recommended: the defect is a measurement bug, independent of results); or
    (ii) keep the main model as estimated and report the corrected-growth refit as a sensitivity.
  - **(c) Sensitivity runs of the D-025 model** (`pooled_adu.sensitivity_runs`). Each is one refit under
    the D-025 convergence rule, with score-bootstrap intervals, reported beside the main estimate and not
    used to choose:
    1. *excluding places treated before 2016*, which have no untreated year in the panel (review point 2);
    2. *T at the announcement year* (C29): the coded `announced_date`, else the council `adoption_date`, of
       the rule that made the place by right; places with neither keep T and are counted. The dose path moves
       with T. With no anticipation this moves zero-effect years into band 0–1, so a smaller 0–1 band is
       expected; a larger effect points to anticipation;
    3. *parking and process reforms as time-varying controls* (C08, C21): 1 if a citywide zero-minimum
       parking reform (`adu.parking_waived`) or any coded process reform is in force on 1 July. A control
       with no variation is dropped and reported; on 2026-10-21 `config/reforms/mn.csv` codes 2 parking
       rows and no process rows.
- **D-031 robustness estimator: imputation on the additive scale** (`estimate_adu.impute`, reported
  beside D-025's log-scale imputation):
  - untreated model by PPML on untreated place-years only: E[y(0)] = Eligible · exp(α_i + γ_t + λ'Z), with
    Z = the replaced ADU rule's dose (carried forward from T − 1 in treated years), parking, process and
    missing middle;
  - ATT_k = 1,000 · Σ (y − μ̂0) / Σ Eligible for k ∈ {0–1, 2–3, 4+} and overall, in additional permits per
    1,000 eligible parcels a year; the ratio Σ (y − μ̂0) / Σ μ̂0 is secondary;
  - places treated in or before 2016, and treated places with no kept untreated year, are excluded and
    listed; an upper bound that counts every permit of the zero-pre places as additional is reported
    beside the ATT;
  - range: stratified place bootstrap (treated and untreated places resampled separately, 999 draws);
  - fewer than 3 contributing treated places means "not estimable". Given D-025's imputation run (7
    imputable treated place-years), this is the expected outcome in Minnesota. The estimator's value there is
    to state the exclusions and the zero-pre bound plainly.
- **Evidence (synthetic panels, `tests/model/test_estimate_adu.py`):** each regime test asserts that D-023
  fails and D-031 passes on the same panel. Zero pre-periods: D-023 2.5–3.2 against log 50; D-031's
  additive ATT within 10%. A 2016 cohort: D-023 ≈ −0.1 against ~0.9; D-031 within 15%. Pre-panel adopters
  whose effect keeps growing past k = 5: D-023 ≈ 0 against ~0.45; D-031 within 15%. Singleton cohorts:
  D-023 drops θ as collinear and undercovers; D-031 is unbiased, and its bootstrap covered 77% for a nominal
  90% over 30 panels, so with fewer than 10 contributing places its range is labelled "probably too narrow".
- **Not carried over from the first draft:** randomization inference as primary for this estimator, its own
  seven checks and transport, and the hierarchical-NB priors (D-025 already has θ).
- **Decided by:** Ben, 2026-10-21 (D-025 stays the main model; this estimator is robustness). Details by
  Claude Code; **(a)–(c) and the household-growth choice await Ben's approval.**
- **Plan for the corrected-growth refit (2026-10-21, written before running; Ben chose option (i) for (b)
  and approved each run once):**
  - *Panel:* the D-025 panel with household growth measured by `household_growth` (missing unless the T − 1
    and T − 6 vintages exist). `estimate_pooled_adu.py --hh-growth as_run` reproduces the first main model's
    panel, so both can be compared; the run prints every place whose household growth changes.
  - *Runs, once each:* `--full --hh-growth corrected`. This is the main model, its wild score bootstrap, and
    the remaining stages under the D-025 convergence rule: randomization inference with dose paths moved
    (D-031 (a)), the five checks, the robustness estimators (fixed-effects PPML, log-scale imputation,
    binary dose, D-031 additive imputation), the D-031 (c) sensitivity runs, and the transport test (guard on
    the predicted mean). The as-run main's transport is WS-ENGINE's 2026-10-21 re-run (above) and is not
    repeated.
  - *Comparison reported:* θ_hh_growth, the band effects and the overall effect, as-run against corrected,
    with their 90% intervals. "Household growth matters for this test" is defined in advance: the overall
    effect moves by more than a quarter of the as-run interval's half-width (0.5 log points), or its 90%
    interval starts or stops containing 0, or the transport verdict changes. Otherwise it does not matter
    here.
  - *HonestDiD for the corrected main:* computed with WS-ENGINE's `pooled_adu.honest_bounds` (the choices
    fixed above) once it is on `ws/engine-17-d025-results`; pending if it is not there when the refit ends.
    No separate implementation.
  - *Logs:* `reports/adu-d025/corrected-2026-10-21-log.txt`, CSVs in `reports/adu-d025/corrected-2026-10-21/`.
- **Corrected-growth refit (2026-10-21, once; log `reports/adu-d025/corrected-2026-10-21-log.txt`, CSVs in
  `reports/adu-d025/corrected-2026-10-21/`; 2 h 15 min):** household growth became missing for 5 places
  (Eagan 2014, Hugo 2012, Lakeville 2013, Minneapolis 2015, Richfield 2015). Every stage was computed.

  | | As-run main (2026-10-20) | Corrected main |
  |---|---|---|
  | θ_hh_growth (per SD) | −0.37 (−1.67 to 1.05) | 0.17 (−1.63 to 2.08) |
  | Band 0–1 | 2.32 (0.61 to 3.93) | 2.36 (0.56 to 4.00) |
  | Band 2–3 | 1.88 (−0.52 to 4.15) | 1.97 (−0.60 to 4.36) |
  | Band 4+ | 2.38 (−0.01 to 4.72) | 2.53 (−0.15 to 5.11) |
  | Overall | 2.26 (0.22 to 4.21) | 2.37 (0.12 to 4.51) |
  | Randomization inference | not computed (7.1% of refits failed, T-only permutation) | p = 0.111 over 970 of 999 (2.9% failed; dose paths moved) |
  | Pre-trend leads (pass p ≥ 0.10) | p = 0.025, fails | p = 0.052, fails |
  | Placebo dates | not computed | not computed |
  | Placebo outcome | 0.48 (−0.62 to 1.64), passes | 0.69 (−0.50 to 1.86), passes |
  | Excluding 2020–21 | passes | passes (3.18) |
  | Leave one out | passes | passes |
  | Transport (WS-ENGINE's as-run re-run vs this run) | 1 of 3 totals inside, yearly 15%: fails | 1 of 3 totals inside (Durham), yearly 15%: fails |

  The other estimates were close to the as-run ones (bands within 0.15, θ for price-to-cost −0.65 vs −0.58,
  δ −2.75 vs −2.69). Robustness on the corrected panel: fixed-effects PPML −0.16 / −0.59 / −0.39 (SEs ≈ 2.4);
  log-scale imputation overall −0.94 (−2.25 to 0.30) on 7 imputable rows; binary dose 1.57 (0.41 to 2.71);
  D-031 additive imputation **not estimable** (2 contributing treated places: 9 treated in or before 2016,
  22 with no ADU before adoption). D-031 (c) sensitivity runs, each inside the main 90% interval: excluding
  the 7 places treated before 2016, 2.92 (1.14 to 4.62); T at the announcement year (11 places re-dated),
  2.99 (1.13 to 4.98); parking and process controls, 3.01 (1.37 to 4.70).
  **Reading, by the rule fixed in the plan:** household growth **does not matter for this test**. The
  overall effect moves by 0.11, under the 0.5 threshold; its interval still excludes 0; the transport
  verdict is unchanged. θ_hh_growth is uninformative either way (intervals ±1.5 around 0). The randomization
  inference that now computes cannot be credited to household growth: this run also moved dose paths (D-031
  (a)), and refit failures fell from 7.1% to 2.9%. Its p = 0.111 means the overall effect is not
  distinguishable at 10% from effects produced by reshuffled adoption years. HonestDiD bounds for the
  corrected main are **pending** WS-ENGINE's `honest_bounds`.
- **HonestDiD run plan (2026-10-21, written before running; Ben approved one run per main):**
  - *Code review:* `pooled_adu.honest_bounds`, `honest_set`, `rm_breakdown` and `event_study_inputs`
    (68c7ae6, WS-ENGINE) were checked against the choices fixed above (3f0d5e2). The relative-magnitudes and
    smoothness bias formulas, the grids, the inputs from the leads refit and the bootstrap union interval
    all match, and no defect was found. One point for readers: θ is the effect at realised doses (each
    band × the place-year's dose), so it is smaller than the main model's "overall", which averages the
    per-unit-dose bands.
  - *Runs, once per main:* `estimate_pooled_adu.py --honest LOG --hh-growth as_run|corrected`. Each run
    recomputes that main model and checks it against its log to 1e-4 (as-run: `run-2026-10-20-log.txt`;
    corrected: `corrected-2026-10-21-log.txt`). It then refits the pre-trend-leads model exactly as check 1
    did (leads k = −3…−1, D-025 convergence rule, 999 wild-bootstrap draws, seed 1). From that refit it
    computes `honest_bounds` and the breakdown M̄ (`rm_breakdown`, grid step 0.01) for the pooled effect.
  - *Per band (an extension of the pooled target, using the same `honest_set`):* θ_b = mean over the band's
    treated place-years of β_b × dose, with ω restricted to the band's event times and renormalised.
  - *Reported:* identified sets, robust 90% intervals and breakdown M̄ for each target and main; the event
    study (leads and bands with 90% intervals); charts of the robust interval against M̄ with the breakdown
    marked. Nothing here changes the D-025 main result or chooses a specification.
- **HonestDiD runs (2026-10-21, once per main; logs `reports/adu-d025/honest-asrun-2026-10-21-log.txt` and
  `honest-corrected-2026-10-21-log.txt`): bounds not identified, and the printed bounds are invalid.**
  Both mains were reproduced (all 22 logged estimates matched) and both leads refits converged with 999 of
  999 draws. **But lead_1 (δ_−1) was dropped from both refits as "all counts zero where it applies":** the 22
  treated place-years one year before adoption had 0 ADU permits (k = −3: 5 permits in 19 place-years;
  k = −2: 1 in 21; k = −1: 0 in 22; k = 0: 9 in 22; places adopting 2017+, `permits_by_event_time.csv`).
  δ_−1's estimate is therefore −∞. `event_study_inputs` counted the dropped lead as 0, so every bound and
  breakdown value printed in those logs rests on δ_−1 = 0 and **is not valid**. The bounds CSVs were not
  kept; the logs are kept as the record.
  - *Fix (D-031, this PR):* `event_study_inputs` now raises if a lead or band was not estimated, with a test,
    and the `--honest` stage reports "not computed". This is a defect in the committed code, not a change of
    the choices fixed above.
  - *What can still be said, from valid quantities:* θ at realised doses from the leads refit is 1.47
    (−0.11 to 3.04) as-run and 1.52 (−0.25 to 3.34) corrected. **The pooled effect's 90% interval includes 0
    before any allowance for a trend violation**, so the pooled breakdown M̄ is 0 whatever δ_−1 is. The
    0–1-year band alone excludes 0: 1.60 (0.37 to 2.79) as-run, 1.61 (0.28 to 2.99) corrected. Its robustness
    to trend violations cannot be computed as specified. Leads: δ_−3 = 1.44 (0.49 to 2.44) as-run, 1.41 (0.36
    to 2.52) corrected; δ_−2 ≈ −0.2 with intervals spanning ±2.
  - *Reading:* the pre-adoption path (a blip at k = −3, then nothing the year before) looks like owners
    holding projects until the rule passed (C29), but with 0–5 permits a year across ~20 places it cannot
    be told apart from noise. The data are too thin for a trend-violation analysis.
  - *Options for Ben (each needs its own dated note before any run):* (1) pool leads k = −2…−1 into one lead
    (1 permit in 43 place-years: estimable, very weak), keeping the choices above; (2) run the same bounds on
    the announcement-dated sensitivity model (2.99, 1.13 to 4.98), whose re-dating moves the dip into the
    post period; (3) report HonestDiD as not identified and rest on the randomization inference (p = 0.111)
    and the failed leads test. Recommended: (3).
- **HonestDiD decision (Ben, 2026-10-21): option (3).** HonestDiD is recorded as **not identified** for the
  D-025 ADU effect. The inference rests on randomization inference (p = 0.111, corrected main) and the
  failed pre-trend leads test (p = 0.025 as-run, 0.052 corrected). Options (1) and (2) are not run.
  - *Ben's reasoning:* more data should make HonestDiD informative later. Concretely:
    - more adopting places with ADU permits in the years just before adoption, so δ_−1 (and δ_−2) can be
      estimated instead of sitting at −∞;
    - longer pre-adoption periods, so the largest pre-period step M_pre rests on more than three noisy leads;
    - the multi-state panel, which pools those years across states.
  - HonestDiD is rerun, with the code already tested here (`--honest`, which refuses unestimated leads), once
    that panel exists. No other run follows from this note.

### D-035 · 2026-10-22 · Eligible-parcel history for places counted from a parcel roll: ACS scaled to the roll (#208)
- **Found:** a jurisdiction counted from a parcel roll had a denominator only in its roll year(s), while ACS-fallback
  jurisdictions had one in every ACS end year (2010–2024). In NC that left 218 jurisdictions, Raleigh, Durham and
  Greensboro among them, with no denominator in the baseline level window, the V1 backtests or the fee scenario.
  The same holds wherever a state counts from a current roll only (MN outside the Met Council archives, OH, TX).
- **Now (`build/eligible.scale_history`, called by `combine`):** each real roll year is an anchor with scale factor
  parcels / ACS one-unit-detached homes, the ACS end year being the roll year or the nearest one within
  `scale_max_year_gap` (3 years; `config/params/eligibility.yaml`). Every other ACS year gets ACS × factor; with
  two or more anchors the factor is linear between them and flat outside. Real roll years keep their real counts.
  Filled rows have `denominator_source = "parcels_scaled_acs"` (new schema value) and the quality of the nearest
  roll. The ADU scenario's overlap step treats them like roll counts (`PARCEL_SOURCES`).
- **Why:** option 1 of #208. Mechanical, works in every state that has ACS, keeps ACS's year-to-year movement and
  ends exactly at the roll. Year-built backcasting (option 2) misses demolitions, splits and vacant lots and is
  tier 1 only; it stays a check, not the main path.
- **Limits:** the factor carries the roll's mix (vacant lots, zoning, exclusions) back in time unchanged, and ACS
  sampling noise moves the filled years. Rolls newer than ACS (NC OneMap 2026) anchor the latest ACS year (2024).
- **Decided by:** Ben, 2026-10-21 (option 1 in #208, real rolls kept wherever they exist).
