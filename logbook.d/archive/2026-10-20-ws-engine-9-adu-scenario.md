### LB-NNN · 2026-10-20 · Build: Handbook ADU scenario end to end, and a first check against observed ADUs (D-019)
- **Question:** How many extra homes would the Handbook ADU reform add in each place, over its current rules,
  and does the hazard match places that already allow ADUs?
- **What I did:**
  - `src/lotline/model/scenarios/adu.py`: current rules from the coded reforms (Handbook-equivalent, partial,
    none); the Handbook increment over them; observed ADU rates as an additionality floor; separate parcel pools
    (one ADU per parcel); net-new and formalization shares; P10/P50/P90 over 1,000 parameter draws, per year
    and five-year; inputs from processed tables (`places_from_store`).
  - Params: `config/params/adu.yaml`; `market.yaml` (`mortgage_rate_forecast`, drawn in forward runs; history
    uses actual rates); `aggregate.yaml` (net-new low end 0.45, formalization share, baseline ADU share).
  - Scripts: `adu_baseline_share.py`, `adu_current_rules_check.py`, `adu_dev_run.py`.
  - Docs: Model & Assumptions ADU scenario section, status, V2 row, sensitivity, parameter table; D-019.
- **Inputs:** Handbook ADU definition; judging findings MS-01, MS-09, MS-10; WS-CORE's check on #161; permits
  flagging ADUs (Met Council, Minneapolis, Raleigh, Austin); config/reforms; ACS; FRED rates.
- **Outputs:** the files above; `tests/model/test_scenario_adu.py`.
- **Findings:** baseline ADU share of 1-unit permits: 0.47% Twin Cities metro, 7.65% Austin (2019-22).
  Under current rules the model gives 1.8x observed ADUs in Minneapolis and Austin and 2.1x in Raleigh
  (2016-22); Minneapolis after 2021 is about 10x below the model's mature hazard. Development run (origin
  2025, anchor 0.004): Minneapolis, Raleigh and Columbus already have Handbook-equivalent ADU rules, so they
  add 0; Austin's +692 permits (P50, 5 years) is an artifact of its uncoded rules; San Antonio (owner
  occupancy and parking) adds 792 permits (P10 159, P90 3,044), 426 homes. Durham's eligible parcels are 5
  (data fault).
- **Decisions:** D-019 proposed, including a proposal (not applied) to re-anchor the hazard to 0.002.
- **AI:** Claude designed and wrote the module, parameters, scripts and tests; one jurisdiction-year worked by
  hand in a test; ran the check and development run on real data; parameters were not tuned to the check.
- **Open / next:** Ben's decision on the anchor; code Austin's ADU rules (WS-TX) and check Minneapolis's
  size/parking coding (WS-MN); fix Durham's denominator (WS-NC); statewide ranges need the aggregation step.
