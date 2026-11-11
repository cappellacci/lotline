# NC parser hand check after #376 / #380: Mecklenburg, Asheville, Greensboro

*2026-11-11 · D-074 step 1 as amended by D-078 §2–3 · per source, never pooled · no model run*

## 1. Judging rule (written and committed before any sampled permit was read)

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

## 2. Sample and pools (fixed before drawing)

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

## 3. Estimator (fixed before drawing)

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

**Amendment to §2 (2026-11-11, after counting pool sizes, before any sampled description was read).** With every
ADU-like word in one pool, Mecklenburg's pool holds 59,454 permits, 39,291 of them only because code-101 house
permits carry the work type "Single Family Dwelling", and 10,185 for "kitchen" alone. Thirty draws cannot bound
misses in a pool that size. The pool is therefore split, the same way in all three sources:
- **Pool A (the near-miss pool, central estimate):** the brief's words plus the 2026-11-10 Charlotte words:
  accessory, dwelling (not "single/one/two family dwelling" or "multi-family dwelling"), guest, in-law / inlaw,
  granny, second unit, cottage, carriage, studio, pool house, living space / quarters, tiny house. 30 draws.
- **Pool B (broad words, sensitivity only):** suite, apartment / apt, kitchen(ette), plus for Asheville its
  2026-11-10 words garage, basement, rental. 30 draws (seed + 200). Its extrapolated misses are shown as a
  sensitivity row, not in the central k or its range, as the Charlotte check also kept "kitchen" out.
