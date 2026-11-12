# Missing middle: can the method give an accurate statewide number? A methodology review (2026-11-11)

*WS-MM-REVIEW, step 1 (`docs/build/workstreams/WS-MM-REVIEW.md`, PR #390). Review only: nothing was run,
fitted, downloaded or tabulated for this document, and nothing in `config/` changed. Every claim cites a file,
report or D-entry; "AP" means `docs/analysis_plan.md`. Inputs were read through code, configs, published
reports, the reform CSVs, and the **column names and vocabularies** of processed tables on disk (no outcome
counts). St. Paul and Ramsey files were not opened.*

---

## Summary for Ben (plain language)

**The question.** Lotline's missing-middle headline is "extra homes in 2–4 unit buildings over five years,
statewide". Can today's method get that number right, and what would it take?

**Short answer: not yet, and the weakest part is not the model. It is the evidence underneath it.**

1. **The fit rests on reform dates nobody has confirmed.** Six of the 13 places in the adopted fit are small
   North Carolina towns (Wilson, Wake Forest, Morrisville, Sanford, Burlington, Garner). Their "reform date" is
   the date of a code rewrite, flagged `[earliest-known]`. The NC readiness doc warned in October not to use them
   as events until someone compares each with its predecessor code (`docs/build/nc-readiness.md` §2). Without
   North Carolina the fit falls from 0.12 to 0.013 per 1,000 lots (AP D-054). If those towns allowed duplexes
   all along, most of the signal goes away.
2. **We fit on very few reforms**: 13 places and 69 place-years, and 37 of those years come from three NC towns
   (`reports/mm-d042/places.csv`). The test places (Minneapolis, Durham) show a clear effect, about twice their
   own trend (AP D-059). The fit set on its own can't beat "no effect" at 2 SE (D-058, D-059).
3. **Oregon is the largest untapped source.** It has up to 65 places with a cap rise in 2016–2023 under one state
   law (HB 2001), 268 of 275 rule rows second-coded, two rollout dates (medium cities 2021, large 2022), and
   cities under the threshold as a built-in comparison. Its outcomes were seen in V9, so it would be an
   in-sample source, not a test.
4. **What we count is narrower than the Handbook target.** We count new 2–4 unit buildings in Census BPS. We
   miss 5–6 unit buildings, townhouses and house-to-duplex conversions. The teardown netting (it takes back
   about a third of homes) is judgment, not measured (D-063).
5. **Better counts are already on disk.** About 11 city permit files carry a unit count *and* a parcel ID
   (Minneapolis, Mecklenburg, Raleigh, Durham, Columbus, Cincinnati, Austin, College Station, Portland, Bend,
   Medford). Four places have two or more parcel rolls that can show a lot gaining units (Wake 2019/2023,
   Minneapolis ten years, Franklin County, Met Council 2021–25). The ADU work already has roll-diff code for
   three of them. None of this needs a download or a records request.
6. **The baseline ("what would have been built anyway") fails where markets swing.** Lubbock fell from 115 to
   25 buildings a year, Charlotte's single-family permits halved during V5, and Oregon's 2018–22 baseline ran
   low. A comparison of eligible and ineligible lots *in the same city*, which the causal diagram ranks
   strongest, is now possible because permits carry parcel IDs.

**What I recommend, in order** (each is an option below, for you to pick):

1. **Firm up the events first** (cheap, decisive): predecessor-code checks for the six NC towns, League City,
   Lewisville, Euclid and Houston 2023, plus Lubbock's two rows and Durham's effective date. That makes 13
   second-coder checks.
2. **Bring Oregon into the fit** in its own dated entry, using the HB 2001 tiers as the comparison.
3. **Count from permits with parcel IDs** where they exist, with each source's coverage measured against BPS
   and against rolls, as the ADU rebuild did. Keep BPS everywhere else and as the check.
4. **Measure the target's missing pieces from those permits**: 5–6 units, townhouses, conversions, teardowns
   and the vacant-lot share. Use them as measured ratios, not judgment.
5. **Pre-register missing-middle tests A–C**, five-state leave-one-state-out and the data-tier test, before any
   count.

**What accuracy hinges on, ranked:**

1. Whether the treated events are real (dates and prior rules).
2. The counterfactual baseline where markets swing.
3. How many treated places and post-years we have.
4. Target coverage: 5–6 units, townhouses, conversions, teardowns.
5. Place-to-place and state-to-state spread: α ≈ 8 and τ not estimable, so the statewide P90/P10 is about 19.
6. The denominator: ACS fallback, vacant lots and lot size.
7. The ADU overlap, which is not yet coded.

---

## Where the method stands (one paragraph)

The adopted method (D-054 (b), adopted by D-055) is a Poisson–gamma hazard. Expected 2–4 unit buildings in a
place-year are its own pre-reform pace × its growth in other permits, plus θ × u × eligible parcels × dose ×
F(PCR)/F(1) × ramp. It is fitted on 13 places whose rule raised the unit cap in 2013–2025, counting only the
newly allowed BPS building classes.
- θ is 0.12 per 1,000 eligible parcels a year (90%: 0.03–1.0), α is 8.4 (2.8–32), and the ramp's half-way point
  is 0.5 years, on the grid floor (`config/params/mm_hazard.yaml`).
- θ and the ramp lie on a ridge (D-058, D-059). But the five-year rate r5 is pinned at 0.08–0.11 per 1,000
  whatever the half-way point (D-062), so the ridge moves *when* homes come, not how many come in five years.
- The scenario (D-063, `src/lotline/model/scenarios/mm.py`) adds homes for the dose gap 1 − d. It uses homes per
  building drawn over 2.04–2.75 and nets teardowns as Binomial(buildings, s × house share).
- Track record:
  - D-038's first fit failed its placebo, and its backtest was no better than no effect.
  - D-042's confounder model did not predict.
  - D-054 missed Texas on Lubbock's baseline.
  - D-055's V9 re-score beat no reform on the Oregon headline, but its place ranges were too narrow (34% above
    P90).
  - D-059 transfers once Lubbock is set aside, but can't beat no effect at 2 SE.
  - V5 Charlotte passed: 119 in 89–172 (`reports/v5-charlotte/README.md`), county-wide and partly luck in the
    baseline.

---

## 1. The target: is "extra 2–4 unit buildings on eligible parcels" the right estimand?

**What we know.**
- The Handbook benchmark is **2–6 units on single-family-only parcels, up to 3 stories**, with setbacks and
  coverage assumed not to bind (HANDOFF.md, scenario definitions).
- The fit counts BPS `units_2 + units_3_4` buildings (AP D-024, D-038). BPS files townhouses as 1-unit and 5–6
  unit buildings as 5+ with apartments, so neither can be seen
  (`docs/research/lotline-causal-diagram-mm.md` §0, last row).
- D-063 chose "2–4 only, and say so" (choice 1, approved 2026-11-08).
- **Teardowns** are netted in the scenario: teardowns ~ Binomial(buildings, s × house share). The house share
  comes from the roll, and s = `mm_teardown_share_scale`, a judgment of 0.5–1.0. That takes back about a third of
  gross homes (D-063, first run and rerun).
- **Conversions** (a house split into 2–4 units without a new building) are not counted anywhere:
  - BPS counts new buildings only;
  - the fit's outcome is BPS;
  - the scenario adds only new buildings.

  The processed permit schema already has `is_conversion`, and Austin's class 436 marks conversions (source
  inventory, below). The Minneapolis roll diff found 183 lots that became duplexes with no ADU
  (`reports/mn/adu-coverage-and-undercount.md` §3.1). The Columbus roll diff found 39 changes from land-use code
  510 to 520, mostly duplexes (`reports/oh/adu-coverage-and-undercount.md` §2.2).

**How good the evidence is.**
- For the 2–4 count itself: good (BPS is uniform).
- For what is left out: we have no measurement. Portland's mix runs 3.4 homes per building, mostly fourplexes,
  against BPS's 2.08 in our places (`mm_hazard.yaml`, `mm_units_per_project` notes). V5 Charlotte built 86 of 94
  as duplexes (`reports/v5-charlotte/README.md`). So the 5–6 share is probably small where duplexes dominate and
  larger where fourplexes pencil.
- Houston townhouses mostly went on land that was not single-family (causal diagram §4, E016). Counting them
  needs a parcel test, not just a class.

**What accuracy hinges on.**
- The teardown scale, since it removes about a third of homes.
- Whether conversions are a material share of net homes, especially in older cores (Minneapolis, Columbus).
- The 5–6 and townhouse shares in places where fourplexes and townhouses pencil (Portland, Austin).

**Options.**

| Option | What it does | Cost |
|---|---|---|
| **1a. Keep 2–4, say so** (today) | Lowest risk; the headline understates the Handbook target by an unknown amount | none |
| **1b. Measured uplift ratios** | From permit sources that separate classes (TH in about 15 sources; U5_6 only in Minneapolis), measure (5–6 + TH on SF-zoned lots + conversions) ÷ new 2–4 buildings, per source with its range; apply it as a drawn ratio, carried as a range | one counting session per state; parcel join needed for "on SF-zoned lots" |
| **1c. Change the fitted outcome to 2–6 + TH homes** | Fit on permit counts directly | needs permits as the outcome (Q2), which drops the BPS-everywhere baseline |
| **Teardowns, T1** | Measure the share of new 2–4 buildings on lots that had a house, from permits with parcel IDs joined to the prior-year roll (Wake, Minneapolis, Franklin, Mecklenburg, Austin/TCAD), or from demolition permits on the same parcel within ±2 years (`is_demolition` exists in every processed permit table except Portland's) | part of the Q2 parcel join |

**Recommendation: 1b plus T1.**
- Keep the fitted 2–4 building count, which BPS gives everywhere.
- Add measured ratios for 5–6 units, townhouses and conversions, and measure the teardown share.
- Keep 1c as a later step, only if 1b's ratios turn out large and unstable.

---

## 2. The outcome measure: BPS or record-level permits?

**What we know.**
- BPS gives annual buildings and units for 1, 2, 3–4 and 5+ per permit-issuing place, back to 1992, with an
  imputation flag (`src/lotline/adapters/national/bps.py`).
- Places outside BPS sit inside their county row. That is why V5 Charlotte had to be scored on all of 37119.
- BPS has no townhouse class, no demolitions and no parcels.
- D-038 tried local permit files for homes per building and found 0.75–2.43 homes per "2–4 unit building",
  which is impossible: the files list one permit per unit or per duplex side (D-038 results).
  **Any permit-based count must first collapse permits to buildings** (parcel × issue date × address).
- D-038 check 6 (the share of 2–4 unit buildings on eligible parcels) was never done, because Cincinnati's and
  Austin's permit parcel numbers did not match the rolls' `parcel_id` format (D-038 results).

**Inventory of sources on disk** (`LOTLINE_DATA_DIR` = `~/lotline-data`). Every processed permit table has
`units_new`, `units_removed`, `building_type_std` (U2, U3_4, U5_6, TH, DTQ, MF5), `is_demolition` and
`is_conversion`. "Offline" means the source rebuilds with `lotline fetch --offline` (#382,
`manifest.builds.jsonl`). Licences are quoted from `docs/data_provenance.md`.

*A. Record-level permits*

| St | Place | Years | Unit field | 2–4 classes | Parcel ID (filled) | Demos | Licence | Offline | MM use |
|---|---|---|---|---|---|---|---|---|---|
| MN | Minneapolis | 2016–26 | `dwellingUnitsNew` | U2, U3_4, **U5_6**, TH | APN (1.00) | yes | CC0 1.0 | yes | **strong**; test place |
| MN | Met Council 7-county | 2009–25 (yearly) | `UNITS` | **DTQ only** (2–4 not split), TH | PIN (0.38) | yes | public domain (MGDPA) | yes | weak; **holds Ramsey: use `holdout.apply`** |
| MN | Rochester | 2005–26 | `units` | U2, U3_4, TH | 0.87 | yes | no licence stated | **probably no** (Laserfiche listing needs the network; `rochester_permits.py:168-200`) | medium |
| NC | Mecklenburg / Charlotte | 1990–26 | `numunits` + Census item code | U2, U3_4, TH | 1.00 | yes | no licence stated | yes | **strong**; V5 released |
| NC | Raleigh | 2000–26 | `housingunitstotal` | U2, U3_4, TH; **`missing_middle` Y/N flag from 2019–20** | PIN (0.92) | yes | Open Raleigh policy | yes | **strong**; test place |
| NC | Durham | 2007–26 | `DWELLING_UNITS` (0.43 filled) | U2, U3_4, TH | PIN15 (1.00) | yes | Durham open-data terms | yes | medium; test place |
| NC | Greensboro | 1990–26 | `NumUnits` | U2, U3_4, TH | none | yes | no licence stated | yes | medium (no parcel) |
| NC | Cary | 2019–26 | `housingunits` | U2, TH | 0.71 | yes | CC0 (dataset) / ODbL (portal) | yes | weak (short) |
| NC | Chapel Hill | 2015–21 | "New Dwelling Units" | U2, U3_4, TH | none | yes | no licence stated | yes | weak (ends 2021) |
| NC | Wilmington | 2014–26 | none (text) | U2, U3_4 | 0.98 | yes | no licence stated | yes | weak (parser) |
| NC | Asheville | 2014–26 | none (text) | U2 | none | yes | PDDL 1.0 | yes | weak; the parser round dropped 104 homes of 5+ (`reports/adu-rebuild-2026-11-11b.md`) |
| OH | Columbus | 2010–26 | `UNITS` | U2, U3_4, TH | 1.00 | yes | CC0 1.0 | yes | **strong** (no MM event: comparison) |
| OH | Cincinnati | 2010–26 | `units` | U2, U3_4, TH | 1.00 | yes | public domain | yes | **strong** (Connected Communities) |
| OH | Cleveland | 2015–26 | none (0.17 filled) | U2, U3_4 | 0.96 | yes | ODbL 1.0 (derived tables not redistributed) | yes | weak |
| OR | Portland | 1994–26 | `NEW_UNITS` | U2, U3_4, TH | 1.00 | **no** | no licence stated | yes | **strong** (no demolitions) |
| OR | Bend | 1990–26 | `Units` | U2, U3_4, TH; **HB2001 / HB2306 flags** | 1.00 | yes | Bend GIS terms, as is | yes | **strong** |
| OR | Medford | 2020–26 | `NO_UNITS` | DTQ + U2, TH | 1.00 | yes | no licence stated | yes | medium (starts 2020) |
| OR | Salem / Keizer / Marion / Polk (MWVCOG) | 1998–25 | `UNITS` | U2, U3_4 | none | yes | no licence stated | yes | medium |
| TX | Austin | 1971–26 | `housing_units` | U2, U3_4 (no TH); HOME flag; class 436 = conversion | TCAD id (0.99) | yes | public domain | yes | **strong** |
| TX | Fort Worth | 2001–26 | `Units` | U2, U3_4, TH | none | yes | CC-BY 4.0 | yes | medium (comparison) |
| TX | Dallas | 1974–2024 | `UNITS` | U2, U3_4 | none | flag never set | no licence stated | yes | weak (ends 2024) |
| TX | College Station | 1989–26 | `number_units` | U2, U3_4, TH | 1.00 | yes | no licence stated | yes | medium |
| TX | San Antonio | 2020–26 | none | U2 | none | yes | CC-BY | yes | weak |
| TX | Houston | monthly summary only | SF / MF totals | none | none | — | — | yes | BPS check only (causal diagram §6.5) |

The Franklin and Montgomery auditor permit files (OH) are read for ADUs only and have no unit field.

*B. Parcel rolls (a lot gaining units)*

| St | Area | Vintages on disk | Unit / type field | Existing diff code | Licence | MM use |
|---|---|---|---|---|---|---|
| MN | Minneapolis | **10 annual, 2017–26** | `TOTAL_UNITS` (0.83), `BUILDINGUSE` (DUPLEX, TRI_QUAD) | `mpls_roll_diff.py` (ADU rule) | CC0 1.0 | **strong** (test place) |
| MN | Met Council 7-county | 2021–25, plus 2026 | `NUM_UNITS` (0.36), `DWELL_TYPE` | none | public domain | medium; **holds Ramsey** |
| NC | Wake | **2019-11 and 2023-12**, card level | `UNITS` per card, `TYPE_AND_USE` 01–04, year built per card | `wake_roll_diff.py` | no licence stated | **strong**: Wake towns, Raleigh |
| OH | Franklin Co. | 10 Parcel (2016–25), 4 Dwelling | `LIVUNITS` per card, LUC 510/520 | `franklin_roll_diff.py` | "as is" | **strong** (no events: a floor test) |
| OH | Montgomery Co. | 9 vintages, 2011–26 | LUC; unit field not confirmed | none | "as is" | medium |
| TX | StratMap statewide | 5 on disk (adapter loads 2019 and 2025) | no units; state land-use class | none | CC0 1.0 | medium (class only) |
| TX | Austin (TCAD) | 1 | improvement type 02/03/04 with year built | `austin_adu_roll.py` | public information | medium (one vintage, dated by year built) |
| NC | OneMap (48 counties) | 1 | land-use class only | — | as is | weak |
| OR | RLIS (Portland metro) | 1 | no duplex class | — | RLIS EULA | weak |

None of these needs a new download, records request or staff email. RLIS's housing inventory has duplex and plex
rows, but only its ADU rows were fetched (`adapters/checks/rlis_housing.py`), so that would be a named download
step.

**How good the evidence is.**
- The ADU rebuild showed that source-by-source measurement works:
  - roll k for Raleigh, Minneapolis, Austin and Portland is 1.04–1.13 (`reports/*/adu-coverage-and-undercount.md`);
  - D-072's coverage rule (a source's new units are at least 0.8 × BPS over the same area) is a ready screen.
- For 2–4 unit buildings the BPS comparison is direct (same class), which is easier than for ADUs, which BPS
  can't see.
- The new difficulty is **counting buildings, not permits**.

**What accuracy hinges on.**
- The permit-to-building collapse.
- The parcel join, which failed in D-038 on ID formats.
- Each source's coverage against BPS, in both directions:
  - permits can include conversions and alterations that BPS leaves out;
  - BPS imputes some months.

**Options.**

| Option | What it does | Cost per source |
|---|---|---|
| **2a. BPS only** (today) | Uniform; no parcels, types or demolitions | none |
| **2b. Permits as the outcome where strong, BPS elsewhere** | About 11 "strong" sources; the per-source k = permit buildings ÷ BPS buildings over the same area and years, before the reform only (D-072 screen ≥ 0.8; per-source k as D-078) | about 0.5 session each: building collapse + parcel join + BPS ratio; reuses adapters |
| **2c. Rolls as a check (test B)** | Wake 2019→2023, Minneapolis year on year, Franklin 2016→2025, Met Council 2021→25 (holdout filter): lots that go from 1 unit to 2–4 units, with a pre-registered rule like `wake_roll_diff.py` §1 (merges, splits, card changes) | about 1 session each; three of the four have ADU diff code to extend |
| **2d. Parser sources** (Wilmington, Asheville, Cleveland, San Antonio) | precision ÷ recall from a hand check, as D-081 | about 1 session each; low priority |

**Recommendation: 2b for the strong sources plus 2c for test B; leave 2d for now.**
- Keep BPS as the outcome for every other place and as the per-source check.
- **Raleigh's own `missing_middle` flag** gives a direct hand check of the class mapping from 2019–20 on.

---

## 3. The denominator: rule 1.1 eligible parcels

**What we know.**
- Rule 1.1 counts single-family-zoned parcels with one house or vacant residential land
  (`src/lotline/build/eligible.py:90-95`, D-014).
- `min_lot_sqft_missing_middle` is 0 with no range, and its notes say "sensitivity range to be sourced"
  (`config/params/eligibility.yaml:12-18`).
- The ACS fallback supplies 330 of the 560 panel places' denominators (D-024) and has no vacant land (D-014
  limits). Houston's denominator is the low-quality ACS fallback (causal diagram §6.5).
- **#375 (permit-level remainders).** `eligible.allocate_homes` takes only BPS-reporting places out of a county
  remainder. That is right when the outcome is BPS, because BPS's county row holds the non-BPS towns. It is wrong
  when rates come from local permit files. The fix (`remainder="permits"`, `eligible.permit_level`) is generic
  code wired only into the ADU estimator (#378). D-080 §1 says a rate measured from BPS must keep the BPS-kind
  remainder.
- The MM scenario uses `adu.non_overlapping` (`src/lotline/model/scenarios/mm.py:254`), not `permit_level`.
  21 NC remainders and 2 MN ones (Scott, Carver) change under it (`reports/adu-rebuild-2026-11-11.md`).
- D-080 also moved 37119's ADU lots to the parcel roll: 21,812 in place of 275,566.

**How good the evidence is.**
- Level errors are absorbed by the place's own baseline in the fit, because only the excess over the baseline
  is scaled by eligible parcels.
- In the scenario, though, eligible parcels set the level directly (D-063). A 13× error like 37119's would carry
  straight through.
- The vacant share and lot size have not been measured for missing middle.

**What accuracy hinges on.**
- The scenario's eligible-lot level in large ACS-fallback places (Houston, the Texas counties).
- Whether vacant lots and built lots take up at the same rate. The causal diagram expects vacant lots higher
  (C46).

**Options.**

| Option | What it does | Cost |
|---|---|---|
| **3a. Leave as is** | — | none |
| **3b. Apply D-080's lesson to MM** | If Q2 moves to permit outcomes, those places take `permit_level`; BPS places keep BPS remainders; check 37119 and the 23 changed remainders for MM lots, as D-080 did | small; the code exists |
| **3c. Measure, don't assume, the vacant weight** | In parcel-joined permit places, the hazard on vacant and built eligible lots separately (the deferred D-038 check 6), and by lot-size tercile; enter a weight only if it differs by more than 2 SE | part of the Q2 join |
| **3d. Lot-size floor** | Source the `min_lot_sqft_missing_middle` range from the coded rules' own minimum lots (many NC rules are corner-lot or 1.5×-lot rules: Mint Hill, `config/reforms/nc.csv`) | small; rule reading |

**Recommendation: 3b and 3c, with 3d as a sensitivity.**

---

## 4. The treated set

**What we know** (full list from `config/reforms/*.csv`; "AP" lines are `docs/analysis_plan.md`):

| St | Place | Rule (eff. date) | Cap before → after | Coder / flags | In D-054 fit? | Holdout / test status | What it would take |
|---|---|---|---|---|---|---|---|
| MN | Minneapolis | 2040 plan (2020-01-01) | 1 → 3, R1–R2B | 2nd coder agrees | no | test place, released, not blind (D-054) | could join the fit; scored already |
| MN | **St. Paul** | Ord. 23-43 (2023-11-26) | 1 → 4 (6 with bonus, coded 4) | adjudicated | no | **V5 blind; never read** | nothing until unblinded |
| MN | St. Louis Park | Ord. 2690-25 (2025-03-28) | 1 → 3 (4 in N-2) | adjudicated; date from a search snippet | yes (1 yr) | — | confirm date |
| MN | Richfield | Bill 2023-2 (2023-01-24) | 2 by CUP → 2 by right | single; 2010 row `[earliest-known]` | no (no cap rise, D-042) | — | method change (count by-right switches) + 1 check |
| MN | Duluth | Ord. 26-019-O (2026-08-31) | → 4 | agree | no | after window | — |
| NC | Durham city / County | EHC (2019-09-03 / 10-28) | 1 → 2, urban tier | partly; **vote date used** | no | test places, released | 1 date check; EHC2 not coded |
| NC | Raleigh | TC-5-20 (2021-08-05), TC-20-21 (2022-08-08) | cap blank (lot-area rules) | partly | no (no cap rise) | test place | turn lot-area rules into a cap; TC-14-19 not coded |
| NC | Charlotte | UDO N1 (2023-06-01) | 1 → 3 | partly; triplex conditions not read | no | V5 **released** (passed) | could join; county-row outcome only in BPS, but Mecklenburg permits have parcels |
| NC | **Wilson, Wake Forest, Morrisville, Sanford, Burlington, Garner** | code rewrites, 2013–2022 | 1 → 2 (Burlington 1 → 4) | **`[earliest-known]`; 2nd coder "partly": first permission unresolved** (`nc-readiness.md` §2) | **yes: they carry the fit** | — | **6 predecessor-code checks** |
| NC | Mooresville | 2022 UDO | 1 → 2 | `[earliest-known]` | no (no pre-reform BPS) | — | — |
| NC | Monroe | 2022 UDO | ≤ 4 by special use only | `[earliest-known]` | no (not by right) | — | — |
| NC | Kannapolis, Cornelius, Mint Hill, Concord, Statesville | various | 2–4 | mixed (`[predates]`, 2nd coder "no", DATE INFERRED) | no | local-only or under Mecklenburg | permit-level outcomes would let some in |
| NC | Apex, New Bern, Asheboro, Goldsboro | before 2010 / `[predates]` | 2 | — | no (always treated) | — | — |
| OH | Euclid | Ord. 120-2024 (2024-11-06) | 1 → 2 | single | yes (1 yr) | — | 1 check |
| OH | Cincinnati | Connected Communities (2024-07-01) | 1 → 4 near corridors | 2nd coded | no (< half of lots covered) | — | a coverage-weighted event rule |
| TX | Austin | HOME phase 1 (2024-02-05) | 2 → 3 (SF-3); 1 → 3 (SF-1/2) | agree; prior row `[predates]` | yes (3–4 only) | — | SF-1/2 duplexes invisible in BPS; Austin permits + TCAD can see zones |
| TX | Houston | Livable Places (2023-11-27) | 2 → 8 | single; prior `[predates]` | yes (3–4 only) | — | 1 check; Ch. 42 lot-size rules sit in another theme |
| TX | League City | UDC (2020-09-29) | 1 → 2 (RSF-2) | single; "CHECK before using" | yes | — | 1 check |
| TX | Lewisville | UDC (2022-12-01) | 1 → 2 | single; "CHECK" | yes | — | 1 check |
| TX | Lubbock | UDC (2023-10-01) | 1(?) → 4 limited use | single; pre-UDC Ch. 40 not coded | **dropped (D-059)** | — | 2 checks (row + Ch. 40 row) |
| TX | Denton, Beaumont, Pearland, Wichita Falls | duplex by special permit | 2, not by right | flagged | no | — | — |
| TX | about 30 cities | one home per lot | cap 1 | flagged for 2nd coder | controls | — | 2nd coder on controls |
| OR | 111 places, 275 rows | HB 2001 medium (2021-06-30, → 2) and large tier (2022-06-30, → 4); about 10 early local ordinances (Portland 2021-08-01, Bend 2021-11-05); 2023 c.223 (2025); HB 2138 (2027) | → 2 or → 4 | **268 of 275 2nd-coded**; 7 single; 49 first-event rows `[earliest-known]` | no (needs its own entry, D-054) | V9 **released** (outcomes seen 2026-11-05) | **up to 65 places with a 2016–23 cap rise**; about 7 checks |

**What `[predates]` and `[earliest-known]` imply** (`src/lotline/model/rule_tags.py`):
- `[predates]` is never an event; it is moved before the panel.
- `[earliest-known]` is an event in main runs and dropped in a sensitivity.

For a T−3…T−1 baseline, an `[earliest-known]` place that already allowed duplexes has **treated pre-years**:
- the baseline absorbs the uptake;
- the "event" changes no rule;
- the place adds noise or a false signal.

The sensitivities are telling:
- D-038 check 5, tag-sensitive events dropped (9 places): θ 1.60 (0.35–26.2);
- D-042 check 8 (7 places): θ = 0.004;
- D-054's fold without NC: 0.013.

Today's θ is not robust to whether those six towns are real events.

**How good the evidence is.**
- Only Minneapolis, Durham, St. Paul and Oregon are well coded.
- The fit set is mostly single-coder or `[earliest-known]`.

**Options.**

| Option | Adds | Checks needed | Cost |
|---|---|---|---|
| **4a. Firm up the current set** | nothing new; makes the 13 trustworthy | 6 NC predecessor-code comparisons + League City, Lewisville, Euclid, Houston 2023 + Lubbock × 2 + Durham date = **13** | one rules session (NC) + one (TX/OH); some codes behind bot checks (Lubbock ecode360, D-059), so they may close as "no usable source" |
| **4b. Bring in the test places** (Minneapolis, Durham × 2, Charlotte) | 4 places with 2–6 post-years; all released | Durham date | small; but they stop being test places (tests move to Oregon / new places) |
| **4c. Oregon joins** | up to 65 places, one law, staggered | about 7 | own D-entry (D-054 requires it); in-sample, since V9 outcomes are seen |
| **4d. Method changes** (Raleigh lot-area → cap; Richfield by-right switch; Cincinnati coverage-weighted dose) | 3 places | 1–2 | each is a pre-registered rule change |

**Recommendation: 4a first, then 4c; 4b only with Oregon in place as the new out-of-sample check.** If the NC
predecessor checks show duplexes were allowed before, those towns become `[predates]`. The fit would then rest
on Houston, Austin and the newcomers, which is the honest state of the evidence.

---

## 5. Identification: what is the counterfactual?

**What we know.**
- The adopted baseline is the own-growth baseline: pre-reform mean (T−3…T−1) × growth in the place's other
  permits (D-038).
- Where it failed:
  - **Lubbock**: 191 expected, 25 built; the fall predates the reform and single-family fell too (D-054
    post-hoc, D-059).
  - **Oregon** 2018–22: the baseline ran low (D-055).
  - **Charlotte**: 1-unit buildings fell from about 6,900 to 3,747 during V5. The pass was partly baseline luck
    (`reports/v5-charlotte/README.md`).
- The alternatives tried so far did not help:
  - D-042's comparison-place baseline did worse in the backtest (MAE 0.185 against 0.153 for no effect);
  - D-058's stability rule flagged most large places, did not fix Lubbock, and its gain was all Lubbock.
- The causal diagram ranks **within-city eligible against ineligible lots** strongest (§3):
  - Raleigh R-1 against the other zones;
  - Durham's urban against suburban tier.

  D-024 deferred it because it "needs permits geocoded to zones". Permits with parcel IDs (Q2) plus zoning on the
  rolls now make it feasible in about six places.
- **Oregon's HB 2001 is a natural staggered design:**
  - medium cities by 2021-06-30;
  - large cities by 2022-06-30;
  - cities under the threshold untreated until 2025 (c.223) or never.

  All of them sit under one state's market, rates and code (`config/reforms/or.csv`).
- **θ–ramp ridge:** D-062 showed r5 is identified (0.08–0.11 at every half-way point), so the five-year total is
  not hostage to the ridge. Longer post-periods would place the ramp:
  - Oregon gives 3–4 years;
  - Durham and Minneapolis give 5–6.

**What accuracy hinges on.** Separating a market swing from a reform effect in the places that carry the fit.
Every method so far uses the place's own past or a state pool, so a local swing (Lubbock, Charlotte) passes
straight into θ or into the miss.

**Options.**

| Option | Counterfactual | Where it works | Cost |
|---|---|---|---|
| **5a. Own-growth (today)** | the place's past × other permits | everywhere (BPS) | none; fails on swings |
| **5b. Within-city lots** (triple difference) | ineligible single-family lots, or other zones, in the same city and year | permit + parcel + zoning places: Raleigh, Durham, Minneapolis, Austin (SF-1/2 against SF-3), Mecklenburg, Portland/Bend (zones on permits) | about 1 session per city to join zones; a new likelihood term |
| **5c. Oregon staggered tiers** | not-yet-treated and under-threshold Oregon cities | Oregon | part of 4c |
| **5d. Re-parameterize on r5** | — | — | done in effect (D-062); a slow-ramp sensitivity for years 6+ only |

**Recommendation.**
- **5c as the main design for the Oregon entry.**
- **5b as a pre-registered challenger** in the parcel-joined cities, scored on the same tests.
- Keep 5a as the transfer baseline for BPS-only places.
- 5d needs nothing new for the five-year headline.

---

## 6. Mechanism and transfer to a place with no history

**What we know.**
- Transport today is F(PCR) with σ held at 0.5 (judgment). The anchor moves with σ: 2.71 per 1,000 at 0.25 and
  0.93 at 0.8 (D-038 check 3).
- No place modifier has been identified:
  - builder capacity b sits at the grid edge with an interval spanning the whole grid (D-042);
  - land share was mostly measured after the event (D-042 check 6);
  - τ is not estimable (D-054).
- **D-072** (ADU zone model, #354, unmerged) sets levels per cell (3 place types × CBSA type) from observed
  counts. A cell counts as measured only with at least 3 places and at least 10 events, and it has a coverage
  screen.
- **D-075's data-tier test:**
  - tier 0: national data only;
  - tier 1: plus coded rules;
  - tier 2: plus one city's counts.

  A tier is "enough" if it passes in 4 of 5 held-out states.
- **Missing middle has an advantage ADUs lack:** BPS 2–4 unit history is national. Every BPS place's own
  pre-reform pace is available at tier 0, and the own-growth baseline already uses it.

**How good the evidence is.** Weak for any modifier, with 13 places. With Oregon, a D-072-style cell table
becomes possible (large cities; mid-size; small towns; unincorporated), but cells will be thin outside Oregon.

**What accuracy hinges on.** For a state like Texas (8.1 million eligible parcels, D-063), the uncoded places'
dose draw and the shared θ dominate the statewide range.

**Options.**
- **6a. Keep F(PCR) only.**
- **6b. A D-072-style cell level** for missing middle (place size × CBSA type), measured cells only. It enters
  only if it beats 6a's held-out log score by more than 2 paired SE (the D-075 §6 rule).
- **6c. Condition each place's multiplier on its own pre-reform 2–4 pace** (tier 0 data) in place of the fresh
  gamma draw D-063 uses. Every place is treated alike today, so a city that builds duplexes steadily gets the
  same draw as one that never has.

**Recommendation.**
- **Run the data-tier test with 6a first.**
- Then **6c as the challenger**: it uses data every state has, and it is the most likely fix for V9's too-narrow
  place ranges (Q9).
- **6b** waits until Oregon is in.

---

## 7. ADU and missing-middle overlap

**What we know.**
- HANDOFF 2026-09-30 says combined scenarios share one pool and model the overlap explicitly.
- It is **not coded**:
  - `overlap_share` is always NaN in `model/results.py:147,181`;
  - aggregation treats NaN as 0;
  - `model/combine.py` does not exist (D-063 deferred stacking).
- The ADU rebuild does not touch the stacking, but it changes the *outcome* boundary:
  - D-074's deviation drops duplexes (Census code 103) from ADU group (a);
  - Austin's post-HOME ADUs moved into the two-family class (causal diagram §6.6);
  - Rochester files a house plus attached ADU as code 103, which BPS counts as two units
    (`reports/mn/adu-coverage-and-undercount.md` §4.1).
- So the same permit can show up as an ADU in the ADU fit and as a 2-unit building in the MM outcome. In
  Austin 2025, 367 two-family permits against 9 ADUs is the clearest case (causal diagram §6.6).

**Options.**
- **7a.** A single permit-to-theme classification, shared by both themes and tested on synthetic fixtures. Each
  permit is an ADU, a 2–4 building, a conversion or other, never two. The MM outcome in permit places uses it,
  and BPS places carry a measured "ADU-in-2-unit" share from the permit places as a correction.
- **7b.** A competing-hazard stacking rule in `combine.py`: a lot that gets a 2–4 building can't also get an
  ADU in the same draw, and the scenario's eligible pools are shared.

**Recommendation: 7a now**, because it affects the counts both refits use. **7b** belongs with the combined
scenario work (WS-ENGINE). 7a needs a `contract-change` issue if it touches the shared permit schema.

---

## 8. Accuracy tests, to pre-register before any count

These copy ADU tests A–C (D-074 §3, D-075 §4–5), adapted. **What has already been seen:**
- Oregon 2018–25 (V9, D-055);
- Minneapolis, Durham and Durham County (D-038 to D-059);
- Charlotte (V5 released);
- every fit place's BPS series (D-038 to D-059).

**Not seen:**
- any permit-level 2–4 count;
- any roll diff for 2–4 units;
- any new place's outcome;
- St. Paul (blind).

| Test | Missing-middle version | Proposed pass rule (fixed before counting) |
|---|---|---|
| **A. New places out of sample** | Each newly entered place (Oregon cities not in the fit, places entering through 4a or 4d), predicted from a fit that leaves it out, over its post-years | ≥ 60% of places inside P10–P90, and median (observed ÷ P50) within ×2 |
| **B. Roll / permit check** | Wake 2019→2023 (Wake towns; Raleigh reported separately), Franklin 2016→2025 and Minneapolis: predicted lots gaining a 2–4 building against the roll diff, under a rule committed before the diff | each area's total inside P10–P90 |
| **C. No-reform floor** | In coded "none" places (MN 3, TX about 30) and Franklin County (no MM event): the baseline's no-reform forecast against observed 2–4 buildings, 2021–25 | ≥ 70% of places inside P10–P90; no state total missed. This tests the baseline, which Q5 says is the weak part |
| **Placebo** | the event moved 3 years early, pre-years only (D-038 check 1, kept) | the 90% upper bound below the main r5 |
| **Leave one state out** | five states with Oregon, D-054's scores and D-040 verdicts | no state with 3+ fit places missed |
| **Data tier** | tier 0 (BPS history + ACS + θ), tier 1 (+ coded rules), tier 2 (+ one city's permit counts), with the tier-2 city left out of the target | passes in ≥ 4 of 5 held-out states at the tier claimed |
| **V5 St. Paul** | unchanged: frozen on what `main` holds; never read | as D-037 |

The pass rules mirror the ADU ones on purpose, so the two themes can be compared on one page.

---

## 9. Uncertainty: are the ranges honest?

**What we know.**
- **Place ranges are too narrow.** In V9 (D-055) mean randomized coverage was 0.43 and 34% of places were above
  P90.
- **Statewide ranges are very wide.** P90/P10 is about 19 in the first scenario run, because one θ per draw
  spans a factor of 31 (D-063).
- Both are consistent with a gamma place effect that is the wrong shape. Its median sits far below its mean
  (D-038 test places: "every median is below the observed count"). Steady builders land above P90 while most
  places sit near zero.
- Parameters drawn today: θ, α and homes per building (triangular over 2.04–2.75). The teardown scale is
  0.5–1.0.
- Held fixed: σ, the ramp slope and half-way point, and the developer margin.
- No undercount k exists for missing middle. BPS is assumed complete, and BPS imputes some months (the `imputed`
  flag).

**Recommendation.**
- **Ranges:**
  - r5 (θ at the fitted ramp; D-062 showed this is the honest five-year range);
  - α, or 6c's conditional multiplier;
  - homes per building;
  - teardown share, once measured (T1);
  - per-source k for permit outcomes (as D-078);
  - the uplift ratios (1b).
- **Sensitivities, not draws:** σ, the slow-ramp years 6+, the vacant weight (3c), the lot-size floor (3d) and
  the 2–4-only target (1a against 1b).
- **Check:** place-level randomized coverage becomes a reported score in every test, with a target of 0.6–0.95,
  so narrowness is caught before a freeze, not after.

---

## Proposed sequence (for Ben to choose; nothing here is pre-registered yet)

1. **Rules session(s), no counts:** the 13 checks in 4a, plus Oregon's 7 single-coder rows.
   - The output is rule rows proposed in reports, which Ben accepts.
   - Codes behind bot checks close as "no usable source".
2. **D-entry (method only, before any count):** the target (1b + T1), the outcome (2b + 2c), the denominator
   (3b + 3c), the treated set (4a + 4c), the designs (5c main, 5b challenger), the overlap rule (7a), the tests
   (§8) and the uncertainty scores (§9). It states what was seen.
3. **Per-state counting sessions** (ADU pattern):
   - building collapse and parcel join;
   - k against BPS and rolls;
   - offline rebuild;
   - first fix Rochester's offline gap, or leave Rochester out.
4. **One joint five-state refit**, then the tests, then a results page (memory `run-results-page`).

Steps 1 and 3 can run in parallel sessions per state. Step 2 waits for Ben.

## Sources read

- AP D-014, D-017, D-024, D-038, D-042, D-054, D-055, D-058, D-059, D-062, D-063, D-071, D-074, D-075,
  D-078–D-081; D-072 on branch `ws/adu-three-zones` (#354).
- `docs/research/lotline-causal-diagram-mm.md` (§0, §3–6.7); `docs/research/mm-uptake-evidence.md`;
  `docs/build/nc-readiness.md` §2.
- `config/params/mm_hazard.yaml`, `config/params/eligibility.yaml`; `config/reforms/{mn,nc,oh,tx,or}.csv`.
- `src/lotline/model/{estimate_mm,calibrate_mm,rule_tags,results}.py`, `src/lotline/model/scenarios/mm.py`,
  `src/lotline/build/eligible.py`.
- `reports/mm-d038/`, `mm-d042/`, `mm-d054/`, `mm-d058/`, `mm-d059/`, `mm-d062/`,
  `mm-scenario-2026-11-08/`, `v9-oregon-d055/`, `v5-charlotte/README.md`;
  `reports/{mn,oh,tx,or}/adu-coverage-and-undercount.md`; `reports/nc/wake-roll-adu-diff.md`;
  `reports/adu-rebuild-2026-11-11.md` and `-11b` (#391).
- `docs/data_provenance.md` (licences); schema and vocabulary of processed tables in `~/lotline-data`
  (no outcomes).
