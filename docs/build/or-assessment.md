# Oregon as a fifth state: assessment

*2026-11-04. Prompted by office hours (A6 in `docs/research/office-hours-2026-11-03-tomasso-notes.md`). Inputs:
`docs/data_availability.md`, the OH and TX readiness reports, the Oregon rows of
`docs/research/lotline-data-catalog.csv` (scouted early October), `docs/research/lotline-validation-plan.md`
(V5, V8), `config/states/*.yaml`, `config/reforms/`, `config/fees/`. No Oregon data was downloaded. Four
endpoints were checked for record counts only (§3). Nothing here is a decision yet; §6 lists what Ben needs to
decide.*

**Decision (Ben, 2026-11-04): option C, transfer first then pool, lean scope.** The DLCD HB 4006 request is not
made (requests take too long). Follow-through: holdout `V9-OR-TRANSFER` in `config/states/or.yaml` (statewide,
from 2018), validation plan V9, brief `docs/build/workstreams/WS-OR.md`.

## 1. Bottom line

- **Oregon gives us what our four states lack most: lots of reform events and lots of uptake.** The D-019 ADU
  anchor rests on 16 places and 115 place-years. The pooled four-state D-025 did not converge, and D-024 (missing
  middle) gave no credible estimate (LB-099, D-037). Ohio adds 2 in-window missing-middle events. Oregon has a
  statewide ADU law (SB 1051, 2018) and a statewide middle-housing law (HB 2001) with two compliance dates
  (2021 and 2022), so every city above the size cutoffs is a dated event. Portland alone has permit-level ADU
  data back to 1995.
- **It covers the high-demand end of the market range.** Today the hazard is anchored at Portland's rent
  (`config/params/hazard.yaml`) and every high-rent place is an extrapolation from our lower-rent states. Oregon
  turns that end into fitted data. Amy's caveat (Oregon's uptake rides on demand) becomes something we test,
  not just a footnote.
- **The data is good where it matters and thin elsewhere.** Portland Metro has parcels with year built, values
  and *sale prices* (better than any of our four states), plus Portland and Bend permits with ADU flags. Outside
  those places, Oregon looks like Ohio: BPS, ACS and coded rules only.
- **The hard part is method, not data.** Statewide mandates treat almost every large city at once, so untreated
  controls are scarce (§4). And Oregon must not be calibrated on before we decide how it is used for validation:
  holdouts have to be set before any Oregon permits are loaded.
- **Recommendation: "transfer first, then pool"** (§5). Onboard Oregon's inputs, freeze a blind prediction of
  Oregon's ADU and middle-housing uptake from the four-state calibration, then unblind and add Oregon to the
  calibration. One effort yields a second unseen-state test (on a state from the Official Data List) *and* a
  stronger fit. WI stays the V8 state.
- **Size: about 8–11 working days for one workstream instance**, plus 1–2 days of engine time for the frozen
  prediction and refit. Feasible before Dec 16 only if it starts this week and stays lean (§7). One item has
  outside lead time: the DLCD HB 4006 city production data is only available by request.

## 2. What we hold for the four states, and what Oregon would offer

"Four states" sums up `docs/data_availability.md` (MN/NC rows as of 2026-10-19, TX 2026-10-30) and the OH
readiness report (2026-11-01). "Effort" is new work for Oregon.

| Input | MN / NC / OH / TX today | Oregon source (catalog) | Oregon quality vs. our four | Effort |
|---|---|---|---|---|
| Geography, BPS, ACS, FHFA, FRED | National adapters, all states | Same (FIPS 41). No townships; counties permit unincorporated land, as in NC and TX | Same | Config only |
| **Permits with ADU flag (R5)** | MN: Met Council ADU category, Minneapolis text. NC: Raleigh, Durham. OH: text rules, undercounts (Cincinnati 26 ADUs, Columbus 53 permits + 183 variances). TX: Austin R-102, SA type, text elsewhere | **Portland** residential permits 1995–2026 with `IS_ADU`, `NEW_UNITS`, `NEWTYPE`; separate demolitions layer; milestone layer for finals. **Bend** permitting table 1934–now (206,859 rows) with `HB2001ADU`, `HB2306Path`, units, finaled date, taxlot. Eugene dashboard spreadsheets (2012–2025, ADU field unconfirmed). Salem (thin, recent only) | **Better.** A true ADU flag, not text matching. Portland's volume is far above any of our cities | 2 adapters (Portland, Bend); Eugene optional |
| **Statewide production by type** | Nothing like it in any of our four states | **DLCD HB 4006 "permitted and produced"** reports, every city over 10,000, 2019 on, units by type | **New kind of source.** Statewide city-level ADU and middle counts would add dozens of places to both panels | **Request the raw data from DLCD now** (summary PDFs only online) |
| Parcels with land use (R1) | MN: Met Council, Mpls, Ramsey. NC: OneMap + Wake. OH: statewide, 95.5% of population on parcels. TX: StratMap, 478 of 1,006 jurisdictions | **RLIS Taxlots** (Metro: Multnomah, Washington, Clackamas; 647,192 lots): land use, state class, year built, building sq ft, land and building values, **sale price and date**. Statewide ORMAP: geometry only, attributes county by county | Metro: **tier 1, better than any of ours** (sale prices). Rest of state: ACS fallback (tier 3) unless county layers are added | 1 adapter (RLIS); rest of state on fallback, as Ohio started |
| Parcel history (R2) | MN 2021–25 archives; NC Wake 2023/2019; OH Franklin and Montgomery yearly; TX StratMap 2019 + 2025 | RLIS quarterly releases and a taxlot-change layer (archive depth to confirm) | Possibly good; unconfirmed | Check depth, then D-035 anchors |
| Zoning (R3) | City layers only; unknown zoning counts as single-family-only | **Statewide zoning layer** (DLCD/ODOT, 229 jurisdictions, 114,823 polygons, generalized state classes) | Better coverage. But since HB 2001, every "single-family" class allows middle housing in covered cities, so the class alone says less | Join to parcels; mostly needed for eligibility (§4.2) |
| Sale prices and rents (R7) | No open sales anywhere (TX confidential) | RLIS `SALEPRICE`/`SALEDATE` in Metro | **Best of the five** for the pro forma | Included in RLIS adapter |
| **Fees (R8)** | MN 171 rows, NC 132, TX 58, OH none. Real fees mostly far below $50k | League of Oregon Cities 2025 SDC survey (89 cities, averages by type and region); OHCS 2022 SDC study (per-unit SDCs by type, incl. ADU and middle housing); city SDC schedules (Portland, Bend, Eugene, Salem) | Oregon SDCs are known to be high, so this may be the **one state near the Handbook's $50k**: useful for Amy's A4 point. Still to be measured | `config/fees/or.csv`, 4 cities + survey as a check |
| **Reform dates (R9)** | MN 104 rows, NC 92, OH 49, TX 103; mostly local ordinances, coded one by one | **State laws** set the dates for most places: SB 1051 (ADUs, 2018), HB 2001 (middle housing, 2021/2022 by city size), SB 458 (middle-housing land divisions, 2022), HB 2138 (2025). Local rows: Portland (ADU history, RIP 2021), plus early or late adopters per DLCD compliance tracking | **Fewer rows for more coverage.** The ADU calibration already applies a statewide row to every place (`model/calibrate_adu.py`, `jurisdiction_geoid` = state FIPS). But Oregon's laws apply by city size and UGB, which a single statewide row can't express, so it needs one row per covered place (generated from population) or a coverage rule (WS-CORE) | ~10 state-law rows + local rows for the panel places; second coder as usual |
| Housing need (A2) | Population and household projections per state (to add) | Oregon Housing Needs Analysis (state-produced housing need by city; to verify) | Probably the best "share of need" denominator of the five | 1 param file |

Endpoint checks (2026-11-04, counts only): Bend permits, RLIS taxlots and the statewide zoning layer all answered.
**Portland's permit MapServer did not answer** from this network (timed out twice). It worked in October. Check it
again before building the adapter.

## 3. What Oregon would add to the estimation panels

For comparison, Ohio added 15 ADU-panel places (7 rule changes, 8 "no ADUs" controls) and 2 in-window
missing-middle events (`docs/build/oh-readiness.md` §2).

| Panel | Oregon places, lean scope | With DLCD HB 4006 data |
|---|---|---|
| ADU (D-019 fit / D-025) | Portland (long history; ADU fee waiver from 2010), Bend (flagged ADUs), Eugene if its sheets carry ADUs. Few places, but large counts | Every city over 10,000 with SB 1051 effective mid-2018: dozens of places, counts from 2019 on (so 2018 is the only pre-year) |
| Missing middle (D-024) | Portland (RIP, 2021) and Bend (HB 2001), from permits with unit counts | Every covered city, treated in 2021 or 2022. BPS 2–4 unit permits cover all places |

## 4. Method issues specific to Oregon

1. **Few untreated controls.** Both laws reach every city above a size cutoff, and the compliance dates bunch in
   2021–22. Within Oregon, the only controls are small cities below the cutoffs (a different market) and the
   pre-years. What saves the design: (a) the two compliance dates and early adopters (Portland, some Metro
   cities) stagger treatment; (b) in a pooled panel, untreated places in MN/NC/OH/TX are controls for the same
   years; (c) route 1 (D-037) calibrates a hazard on treated place-years and does not need a control group.
   Item (c) is the main use. Oregon mostly strengthens the mechanism fit, not the difference-in-differences
   checks.
2. **Eligibility depends on the urban growth boundary (UGB), not just the city.** Both laws apply inside UGBs,
   including unincorporated urban land in the Metro counties. `build/eligible.py` has no boundary rule beyond
   the jurisdiction. Needs either a UGB layer (DLCD publishes one) joined in the adapter, or a WS-CORE
   `contract-change` issue. Small for the lean scope (Portland and Bend are mostly inside their UGBs), bigger
   statewide.
3. **Portland is already used as an outside check.** The hazard's reference rent and value are Portland's
   (fixed, fine). But Portland's published ADU counts (E044, E046) and the "~4 per 1,000" comparison are
   plausibility checks today. Once Portland is in the fit, those checks are no longer independent. Seattle, Los
   Angeles and California APR remain outside checks; say so in D-037's notes.
4. **Demand context (Amy's caveat).** Oregon's uptake is high partly because the market is strong. The hazard's
   rent and value modifiers should explain that. If the frozen transfer prediction undershoots Oregon badly, the
   modifiers are too weak. That is a finding to report either way, not a reason to tune.
5. **Holdouts come first.** The protocol freezes predictions before outcomes are loaded. If Oregon will be used
   for any blind test, its holdouts must be written into `config/states/or.yaml` **before any Oregon permit,
   BPS row or HB 4006 file is fetched**. Today BPS is national, so check whether Oregon BPS rows already sit in
   `LOTLINE_DATA_DIR` and whether the holdout filter hides them once `or.yaml` names them.
6. **Licenses.** RLIS uses its own ODbL-style end-user license (the same share-alike question that keeps
   Cleveland out). Portland's permits state no license. Bend's terms are custom. Salem bars commercial
   redistribution. The zoning layer has custom terms. We never redistribute raw data, but each one needs a
   provenance row and a check against Rules T11 before its adapter is merged.

## 5. Options for how Oregon is used

| Option | What it buys | What it costs |
|---|---|---|
| **A. Fifth development state** (pool into calibration now) | Fastest route to a stronger ADU and MM fit | No independent test from Oregon; Portland checks lose independence; looks like we added the state that gives big numbers |
| **B. Unseen-state test only** (V8 on Oregon instead of WI) | Transfer test on an Official Data List state with lots of outcomes | Oregon never strengthens the fit; WI's work is dropped or doubled |
| **C. Transfer first, then pool** (recommended) | A frozen, blind Oregon prediction (a second transfer test, high-demand end), *then* Oregon in the calibration for the final numbers | Needs the freeze discipline; slightly more engine time (two runs) |
| D. Comparables only (as now) | No new work | Doesn't answer Amy or the underpowered panels |

Option C matches the 2026-10-28 purpose decision (show transfer) and Ben's "roll our own" framing (Oregon becomes
our own calibration data once unblinded). V8 on WI is unaffected. C differs from V8 in one way: Oregon was chosen
*because* it has high uptake, so it is a transfer test, not an unseen-state test, and the write-up should say so.

## 6. Decisions for Ben

1. Option A, B, C or D (recommended: C).
2. Lean scope (Portland Metro + Bend + state-law rows + BPS statewide) or statewide (also HB 4006 data and the
   UGB layer). Recommended: lean now, and send the HB 4006 request today so it can join if it arrives in time.
3. Whether Oregon's work is a new workstream (`ws/or`, one worktree, brief in `docs/build/workstreams/`) or
   folded into the engine thread. Recommended: its own workstream, as with OH and TX.
4. Does this displace anything? Engine work (thread 9, A1–A5 from office hours) is the critical path to
   Nov 17 and Dec 16; Oregon must not delay the V5 freezes.

## 7. Lean work plan (if C)

| Step | What | Paths | Days |
|---|---|---|---|
| 0 | Write holdouts and the transfer-test design into `config/states/or.yaml` and the validation plan *before* any outcome fetch; check BPS cache | `config/states/or.yaml`, `docs/research/lotline-validation-plan.md` | 0.5 |
| 1 | State config, jurisdictions (no townships), crosswalk for RLIS land use / state class | `config/states/or.yaml`, `config/crosswalks/or_*.csv` | 1 |
| 2 | RLIS taxlots adapter (tier 1 in Metro, sale prices), ACS fallback elsewhere | `src/lotline/adapters/states/or/rlis_parcels.py` + tests | 2 |
| 3 | Reform rows: state laws, Portland, Bend, Metro cities; second coder | `config/reforms/or.csv` | 1.5–2 |
| 4 | Fees: Portland, Bend, Eugene, Salem SDC schedules; LOC survey as a check | `config/fees/or.csv` | 1 |
| 5 | Housing-need parameter (OHNA) for A2 | `config/params/` (engine owns) | 0.5 |
| 6 | **Freeze** the blind Oregon prediction from the four-state calibration; commit to `results/frozen/` | engine | 1 |
| 7 | Outcome adapters: Portland permits, Bend permits; BPS Oregon unblinded with Ben's OK | `src/lotline/adapters/states/or/{portland,bend}_permits.py` + tests | 2–3 |
| 8 | Score the transfer test; refit D-019 with Oregon; readiness report like OH/TX | `docs/build/or-readiness.md`, `reports/` | 1 |

Total ≈ 8–11 days for the workstream plus 1–2 engine days. Started this week, the freeze (step 6) could land
around Nov 17–20 and the refit by early December, leaving two weeks for the deck and app.

Also, from A6: Washington and Vermont stay evidence-register items. Their data was not assessed here.
