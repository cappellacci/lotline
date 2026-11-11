# NC parser hand check after #376 / #380: Mecklenburg, Asheville, Greensboro

*2026-11-11 · D-074 step 1 as amended by D-078 §2–3 · per source, never pooled · no model run*

## Summary

The shared parser fix (#376, #380) changed what the three NC parser sources count. This check re-measures each
source's recall by hand, one source at a time, with the method in §§ 6–8 (written and committed before any
sampled permit was read; the git history of this file shows the order). k_parser = 1 / recall, as D-074 step 1
and D-078 §2 define it.

| Source | Flagged | Precision (90%) | Recall (90%) | **k = 1 / recall (90%)** | Before #376 |
|---|---:|---|---|---|---|
| `meck_permits` (Charlotte, the six towns, unincorporated) | 441 | 26/30 = 0.87 (0.73–0.94) | 0.94 (0.77–0.98) | **1.07 (1.02–1.31)** | 1.04 (up to 1.27–1.43) |
| `asheville_permits`, before 2022 (description only) | 212 | 23/30 = 0.77 (0.62–0.87) | 0.58 (0.48–0.66) | **1.71 (1.52–2.10)** | 1.59 (1.43–1.79) |
| ↳ city-flag benchmark, re-run | 130 city-typed | — | 82/130 = 0.63 (0.56–0.70) | 1.59 (1.44–1.79) | 1.59 (same 82/130) |
| `asheville_permits`, 2022 on (city type + description) | 160 | 29/30 = 0.97 (0.86–0.99) | 0.98 (0.86–0.98) | **1.02 (1.02–1.16)** | not measured |
| `greensboro_permits` | 44 (all read) | 33/44 = 0.75 (0.63–0.84) | 0.89 (0.41–0.90) | **1.12 (1.11–2.46)** | none (k = 1 placeholder) |

What changed and why it matters:

- **Mecklenburg** is close to its old value. The fix targeted the 14 misses the 2026-11-10 check listed (12 were
  434 upfits that name an ADU). Two of those kinds are still missed (an "existing garage upfit" and code 437);
  five clear misses remain in the strong stratum in all, plus about 1% of the near-miss pool.
- **Asheville before 2022 did not improve.** The city-flag benchmark finds exactly the same 82 of 130 as before
  #376, and the hand check gives a slightly lower recall (0.58). The fix did not touch the two parser
  behaviours that cause most of Asheville's misses (§4). Under D-078 §3 the low-recall flag stays on this row.
- **Asheville 2022 on** is near 1: the city's own ADU categories carry it.
- **Greensboro** gets its first measured k. Its point value is 1.12, but the range is wide: with 1,381 permits in
  its near-miss pool, 0 misses in 100 draws still allows up to 36 more ADUs (2.6% of the pool) against 33
  confirmed flags. Its precision is low for a different reason: #376 now flags "mother-in-law suite" additions
  (10 of 44 flags), which name no kitchen, so the judging rule marks them `AMBIGUOUS`, not ADUs.
- **Legalizations** (Ben, 2026-11-11): 4 permits legalize a unit that already existed, all in Asheville before
  2022 and all unflagged, so they inflate no count. None of the 134 flagged permits read is a legalization.
  Examples: "apartment made previously with no permits", "bring existing ADU in basement into compliance".
- **House + ADU** (rule 2): 4 of the 30 Asheville pre-2022 flags are new-house permits whose text names an ADU in
  the same house ("new stick built house with ADU in basement"). The adapter's `NEW_HOUSE` pattern misses "stick
  built house", "residence" and "new build structure", so they are counted as ADUs. None in the other sources.

### A caution on k = 1 / recall

D-074 defines k = 1 / recall, which assumes every flag is a true ADU. Where precision is below 1, the factor
that turns counted flags into true new ADUs is (true positives + misses) / flagged = precision / recall. It is
given here for Ben to choose between; the proposed rows below follow D-074 as written.

| Source | k = 1 / recall | precision / recall (90%) |
|---|---|---|
| Mecklenburg | 1.07 | 0.93 (0.76–1.17) |
| Asheville before 2022 | 1.71 | 1.31 (1.07–1.55) |
| Asheville 2022 on | 1.02 | 0.99 (0.88–1.13) |
| Greensboro | 1.12 | 0.84 (0.72–1.75) |

## 1. Results by source

Counts are judged permits. "Strong" is the stratum of every unflagged permit that names an ADU outright (read in
full); "pool A" is the near-miss pool; "pool B" the broad-word pool (sensitivity only). FN = strong misses +
pool-A miss rate × pool-A size.

### Mecklenburg (`meck_permits`)

| | Size | Judged | NEW_ADU | AMBIGUOUS | EXISTING / NOT / other |
|---|---:|---:|---:|---:|---:|
| Flagged | 441 | 30 | 26 | 3 | 1 not (a guest house amended to a sunroom) |
| Strong (all read) | 23 | 23 | 5 | 2 | 2 existing, 14 not ("THIS IS NOT AN ADU", "GARAGE ONLY, NO ADU") |
| Pool A | 2,150 | 100 | 1 | 10 | 89 not |
| Pool B | 18,115 | 30 | 0 | 0 | 30 not |

- TP = 0.867 × 441 = 382; FN = 5 + 0.01 × 2,150 = 26.5; recall 0.935; **k 1.07 (1.02–1.31)**.
- Sensitivity, `AMBIGUOUS` as ADUs (mostly mother-in-law additions, guest houses, "garage/guest house 2nd
  level"): k 1.57 (1.35–1.99). Pool B, worst case at its 90% bound: up to 5.9 (it cannot be bounded with 30
  draws on 18,115 permits; none of its 30 was an ADU).
- 3 of the 26 true flags rest on the county's "New. Accessory Dwelling Unit." work type alone with a project
  name that names another structure ("Pool Cabana", "Garage", "Accessory Structure"). Counting them as not ADUs
  gives precision 23/30 and k 1.08: no material change.
- **Still missed** (strong stratum): an "existing garage upfit" with the ADU work type on a 434 permit; "Garage
  addition … Add Second Story. ADU"; a reissued permit whose note says the unit is now "the accessory dwelling
  unit"; and two code-437 permits with the ADU work type ("ADU" and a Huntersville "detached 1-car garage"). Code
  437 is still not in `classify`'s allowed codes, as the 2026-11-10 check proposed. Pool A: one 2007 "attached
  garage w/ mother-in-law apt".
- Before → after: the 2026-11-10 central 1.04 rested on 14 found misses among 325 Charlotte and county flags (the
  towns were not in that check). Now: 441 flags for Charlotte, the towns and the county (+26 from the fix,
  `reports/adu-rebuild-2026-11-11.md`) and 5 + ~21 estimated misses. The upper end (1.31) is close to the old
  strict case (1.27).

### Asheville before 2022 (`asheville_permits`, application years 2014–2021)

| | Size | Judged | NEW_ADU | AMBIGUOUS | other |
|---|---:|---:|---:|---:|---:|
| Flagged | 212 | 30 | 23 | 2 | 4 house + ADU, 1 not (mother-in-law suite, "kitchenette no stove", sink and oven later removed) |
| Strong (all read) | 151 | 151 | 60 | 9 | 42 house + ADU, 14 existing, 4 legalize, 21 not, 1 duplicate record |
| Pool A | 462 | 100 | 12 | 14 | 72 not, 1 existing, 1 house + ADU |
| Pool B | 2,769 | 30 | 0 | 2 | 28 not |

- TP = 0.767 × 212 = 162.5; FN = 60 + 0.12 × 462 = 115; recall 0.585; **k 1.71 (1.52–2.10)**.
- Sensitivity, `AMBIGUOUS` as ADUs: k 2.07 (1.82–2.53).
- **City-flag benchmark:** the description rule alone finds 82 of the 130 city-typed ADUs of 2022–2026: detached
  64/86 (0.74), attached 18/44 (0.41). k = 1.59 (1.44–1.79). This is the same 82 as on 2026-11-10: #376 changed
  none of them.
- The two measures agree within their ranges. The hand check is measured on the pre-2022 text itself; the
  benchmark is measured on later text against an independent flag (the city's type). Each sees misses the other
  cannot: the benchmark catches ADUs whose text names no unit at all ("finish basement"); the hand check catches
  the pre-2022 filing habits (separate ADU records that cite the house permit) that later text uses less.
- **Why the parser misses them** (the parser's own `evidence` on the 60 strong misses):
  - 33: `conflict: an ADU and another dwelling type`. The ADU's own permit cites the house permit ("garage
    apartment, ref. new house permit 14-…", "accessory dwelling unit (SFR 16-…)"), or an Accessory Structure
    record repeats the house's text. The parser sees a house and an ADU and returns no type.
  - 16: `ADU named: unit change unclear`. An alteration word anywhere in the text, often in a later amendment
    ("RECD AMENDMENT TO CHANGE HVAC CONTRACTOR"), makes the parser treat a named ADU as work on an existing one.
  - 11 other: in 9 the parser returns `ADU` but the adapter drops it (its `NEW_HOUSE` or `EXISTING_ADU`
    pattern, or the permit's category); 1 is read as an ADU removal and 1 as a conversion of the house.
  These are shared-parser behaviours (`lotline.parse.permit_text`), so they are described here, not changed.

### Asheville 2022 on (`asheville_permits`, 2022–2026)

| | Size | Judged | NEW_ADU | AMBIGUOUS | other |
|---|---:|---:|---:|---:|---:|
| Flagged | 160 | 30 | 29 | 0 | 1 existing ("upgrade existing studio/apartment above detached garage") |
| Strong (all read) | 38 | 38 | 3 | 1 | 15 house + ADU, 9 existing, 10 not |
| Pool A | 228 | 30 | 0 | 2 | 27 not, 1 existing |
| Pool B | 1,409 | 30 | 0 | 3 | 27 not |

- TP = 154.7; FN = 3; recall 0.98; **k 1.02 (1.02–1.16)**. Sensitivity, `AMBIGUOUS` as ADUs: 1.12 (1.06–1.33).
- The 3 misses are alteration or accessory permits the city did not type as ADUs ("create a detached ADU",
  "build a 13'x17' single story ADU … guest house", "creation of ADU … on lower level"), all `unit change unclear`.

### Greensboro (`greensboro_permits`)

| | Size | Judged | NEW_ADU | AMBIGUOUS | other |
|---|---:|---:|---:|---:|---:|
| Flagged | 44 | 44 (all) | 33 | 10 | 1 existing ("detached accessory dwelling unit. Interior remodel/upfit") |
| Strong (all read) | 8 | 8 | 4 | 0 | 1 existing, 3 not ("not an ADU", "not to be used as ADU") |
| Pool A | 1,381 | 100 | 0 | 3 | 97 not (mostly sheds: "ACCESSORY BUILDING 10X12") |
| Pool B | 2,635 | 30 | 0 | 1 | 29 not |

- TP = 33; FN = 4 + 0 × 1,381 = 4; recall 0.89; **k 1.12 (1.11–2.46)**.
- Sensitivity, `AMBIGUOUS` as ADUs: precision 43/44 but pool A then has 3/100 misses: k 2.06 (1.47–3.62).
- The 10 ambiguous flags are all in-law / mother-in-law suites ("ADDITION - MOTHER-IN-LAW SUITE", "turning
  basement into mother-in-law suite"), new since #376. Whether they are ADUs decides most of Greensboro's count
  before 2024, so it is a question for Ben (raised in the PR).
- Misses: "Change of Use – Garage to Dwelling Unit 828 SF", "Framing, Plumbing … for Accessory Dwelling Unit",
  "demolish the existing 2 car garage and rebuild with a second level ADU", "Renovate existing heated second floor
  of existing garage to be functional ADU".
- Two flagged 2018 permits with the same contact name the same garage-to-ADU conversion; they may be one ADU on
  two permits. Both are counted as true here.

## 2. Proposed undercount-table rows

For the session collecting `adu_flag_undercount` rows. Not written to `config/params/adu.yaml`.

| Source | k | 90% range | Citation | Note |
|---|---:|---|---|---|
| `meck_permits` (Charlotte 3712000, the six towns, 37119) | 1.07 | 1.02–1.31 | `reports/nc/parser-handcheck-2026-11-11.md` §1 | replaces 1.04 (1.0–1.27) |
| `asheville_permits`, issue years before 2022 | 1.71 | 1.52–2.10 | same, §1 | replaces 1.59 (1.43–1.79); keep the D-078 §3 low-recall flag. The city-flag benchmark, unchanged at 1.59 (1.44–1.79), is the alternative |
| `asheville_permits`, issue years 2022 on | 1.02 | 1.02–1.16 | same, §1 | new row |
| `greensboro_permits` | 1.12 | 1.11–2.46 | same, §1 | replaces the k = 1 placeholder; range wide (small source, large near-miss pool) |

All four use k = 1 / recall as D-074 and D-078 define it; the precision / recall alternative is in the Summary.

## 3. Reproducing this check

- The sampling, judging sheet and scoring scripts and the labels (permit id, stratum, label; no description
  text) are in the session's shared notes folder, not in the repo, because they read raw permit text in memory.
- Seeds: as in §7, plus seed + 300 for the extra pool-A draws.
- The near-miss "dwelling" word excludes "SF / MF / TH / 2F / existing / principal / main dwelling" as well as
  "single / one / two / multi family dwelling" (the Mecklenburg work type "SF Dwelling Detached" alone put 39,000
  house permits in the pool). This was set after counting pool sizes and before any description was read.
- 90% Wilson intervals, z = 1.645. Greensboro's flagged permits are a census (44 of 44); its precision interval is
  kept for comparability.

## 4. Proposed fixes (not made)

- `lotline.parse.permit_text` (shared): when the text names an ADU and cites another permit for the house ("ref.
  new house permit", "SFR #…", "main house …"), return `ADU`, not a conflict; and read alteration words only from
  the first clause, not from "RECD AMENDMENT …" lines. Together these two cover 49 of Asheville's 60
  strong-stratum misses. Every state's counts would change, so it needs its own PR and rebuild.
- `asheville_permits.NEW_HOUSE`: also match "new … house", "residence", "new build structure", so a house permit
  that names its basement ADU stays a house (4 of 30 pre-2022 flags).
- `meck_permits.classify`: allow code 437 (2 misses here, as on 2026-11-10).

## 5. What this does not do

- No engine, scenario, fit or calibration run; no download; no `--unblind`; no change to `config/`.
- Misses in text with no ADU-like word are not estimated (they are below every k here).
- One reader judged every permit; no second coder.

## Method (committed before reading)

## 6. Judging rule (written and committed before any sampled permit was read)

Each sampled permit is judged by hand from its description text and its permit type (Mecklenburg: Census item
code, work type; Asheville: record subtype and category; Greensboro: application type and occupancy). The
judge does not see whether the parser flagged it: flagged and pool draws are shuffled into one sheet and the
flag is joined back only after every row has a label.

Labels:

| Label | Meaning | Counts as a new ADU? |
|---|---|---|
| `NEW_ADU` | The permit creates a dwelling unit accessory to a single-family house on the same lot: the text names an ADU, accessory dwelling or accessory apartment, a garage or basement apartment, a carriage house, or a guest house, cottage or in-law suite **with** a kitchen or kitchenette or called a dwelling, apartment or rental. New construction and conversions of existing space (garage, basement, room above garage, "to ADU", "into ADU", "ADU upfit") both count. | yes |
| `LEGALIZE` | A permit for a unit that already exists but was never permitted ("existing unpermitted", "bring to code", "after the fact", "as-built", "legalize"). Ben, 2026-11-11. | no, reported separately |
| `EXISTING` | Work on an ADU that already exists and was permitted, or that the text calls existing: repair, remodel, renovation, re-roof, deck, addition to it, removing it, or change of use away from an ADU. | no |
| `HOUSE_PLUS_ADU` | A permit for a new house whose text also names an ADU. One SFD; its ADU is not counted (rule 2 of the brief). | no |
| `NOT_ADU` | No new unit: garage, studio, office, pool house, owner's suite or addition with no kitchen and not called a dwelling; text that says it is not an ADU; demolitions; the ADU named only as context ("for the detached ADU" on work to the main house, a reference to another permit). | no |
| `AMBIGUOUS` | The text may be a new unit but does not say enough (an in-law suite, guest house or pool house with a bath but no kitchen named; "upfit" of a space that may already be an ADU). | central: no; sensitivity: yes |

Tie-breaks fixed now: the county's work-type phrase "New. Accessory Dwelling Unit." (Mecklenburg) counts as
naming an ADU unless the rest of the text says otherwise (as in the 2026-11-10 Charlotte check). A parenthetical
work-type label such as "(interior renovation)" is ignored; the judgment rests on the rest of the text. "Upfit"
or "addition" that turns space into an ADU is `NEW_ADU`; "renovation", "remodel" or "repair" of an ADU is
`EXISTING`. For Mecklenburg the sheet also shows whether the same parcel has another ADU-flagged permit issued
earlier; a 434 upfit on such a parcel is `EXISTING` unless the text says a second unit is being made.

## 7. Sample and pools (fixed before drawing)

- **Data.** The rebuilt processed permit tables in `~/lotline-data/processed/nc/permits/` (2026-11-11, `main`
  with #376 and #380; `reports/adu-rebuild-2026-11-11.md`). The descriptions are not in those tables, so they
  are joined in memory from the raw files the rebuild used (Asheville 2026-11-11 pages, Greensboro 2026-11-09
  pages, the registered Mecklenburg GeoPackage), **only for permit ids present in the holdout-filtered
  processed table**. Nothing was downloaded; no description is written to the repo.
- **Flagged:** `building_type_std == "ADU"`.
- **Strong stratum (read in full, every row):** unflagged permits of the parser-eligible types whose text has
  an explicit ADU term: `ADU`, `accessory dwelling`, `accessory apartment`, `garage apartment`,
  `second dwelling`, `additional dwelling`, `accessory living`.
- **Near-miss pool (sampled):** the other unflagged permits of the parser-eligible types whose text has an
  ADU-like word: accessory, dwelling, suite, studio, cottage, carriage, guest (house/quarters/suite), in-law /
  inlaw, granny, apartment, living (space/quarters), pool house, second unit, kitchen(ette)
  (Asheville also: garage, basement, rental, tiny, as in its 2026-11-10 pool), excluding demolitions.
  - Mecklenburg eligible types: codes 101, 434, 437, 438 and no code (437 added because the 2026-11-10 check
    found an ADU on it).
  - Asheville eligible types: Residential `ADU_TEXT_CATEGORIES` plus the city's ADU categories.
  - Greensboro eligible types: Residential permits whose occupancy is in `ADU_OCCUPANCIES` or blank, not
    Total Demolish.
- **Draws:** 30 flagged and 30 pool permits per stratum, `numpy.random.default_rng(20261111)` (Mecklenburg),
  `20261112` (Asheville before 2022), `20261113` (Asheville 2022 on), `20261114` (Greensboro). Asheville
  before 2022 and 2022 on (application year) are separate strata. Greensboro has fewer flagged permits than
  30 + margin, so all of them are read.

## 8. Estimator (fixed before drawing)

- **Precision** = `NEW_ADU` / judged flagged, 90% Wilson interval.
- **Misses:** FN = (`NEW_ADU` in the strong stratum, counted) + (pool miss rate × pool size). Pool miss rate
  has its own 90% Wilson interval.
- **Recall** = TP / (TP + FN), TP = precision × flagged count. **k_parser = 1 / recall.**
- **90% range for k:** low end from precision's upper bound and the miss rate's lower bound, high end from
  precision's lower bound and the miss rate's upper bound (both 90% Wilson; conservative, as both ends move
  together). Sensitivity: `AMBIGUOUS` counted as ADUs.
- Misses outside the pool (text with no ADU-like word) are not estimated; k is a lower bound on the true
  undercount for that reason (as in the Charlotte check).
- **Asheville city-flag benchmark (as in `reports/nc/asheville-adu-scout.md` §4).** Of the city-typed ADU
  permits (2022 on), the share the description rule alone would flag, re-run with the current parser. Before
  2022 every Asheville ADU comes from the description, so this benchmark, not the pool, is the main recall
  measure for that stratum; the pool check is reported beside it.

**Amendment to §7, then numbered §2 (2026-11-11, after counting pool sizes, before any sampled description was read).** With every
ADU-like word in one pool, Mecklenburg's pool holds 59,454 permits, 39,291 of them only because code-101 house
permits carry the work type "Single Family Dwelling", and 10,185 for "kitchen" alone. Thirty draws cannot bound
misses in a pool that size. The pool is therefore split, the same way in all three sources:
- **Pool A (the near-miss pool, central estimate):** the brief's words plus the 2026-11-10 Charlotte words:
  accessory, dwelling (not "single/one/two family dwelling" or "multi-family dwelling"), guest, in-law / inlaw,
  granny, second unit, cottage, carriage, studio, pool house, living space / quarters, tiny house. 30 draws.
- **Pool B (broad words, sensitivity only):** suite, apartment / apt, kitchen(ette), plus for Asheville its
  2026-11-10 words garage, basement, rental. 30 draws (seed + 200). Its extrapolated misses are shown as a
  sensitivity row, not in the central k or its range, as the Charlotte check also kept "kitchen" out.

**Second amendment (2026-11-11, after the first 30 pool-A draws were judged, before any further draw).** With 0 misses
in 30, the 90% Wilson upper bound on the miss rate is 8.3%, which on Greensboro's 1,381-permit pool A allows more
misses than it has flags. As the brief allows, 70 more pool-A permits are drawn (seed + 300, excluding those already
drawn) for Mecklenburg, Greensboro and Asheville before 2022, so pool A has 100 judged draws in those strata. The
judging rule is unchanged.
