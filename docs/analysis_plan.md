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
