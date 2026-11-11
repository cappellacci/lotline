# NC parser hand check after the second parser round (#389, #391): Mecklenburg, Greensboro, Asheville

*2026-11-11 · D-081 items 1 and 6 · per source, never pooled · no model run*

*Results are added below this method once every sampled permit is judged. The method (§§ M1–M3) was written and
committed before any sampled permit was read; the git history of this file shows the order.*

## Method (committed before reading)

This repeats the protocol of `reports/nc/parser-handcheck-2026-11-11.md` (#386) §§ 6–8 and its two amendments,
with new seeds, on the tables rebuilt offline in #391 (`reports/adu-rebuild-2026-11-11b.md`). Differences from
#386 are marked **(new)**.

### M1. Judging rule

Each sampled permit is judged by hand from its description text and its permit type (Mecklenburg: Census item
code and work type; Asheville: record subtype and category; Greensboro: application type and occupancy). The
judge does not see whether the parser flagged it: flagged and pool draws are shuffled into one sheet, and the flag
is joined back only after every row has a label.

| Label | Meaning | Counts as a new ADU? |
|---|---|---|
| `NEW_ADU` | The permit creates a dwelling unit accessory to a single-family house on the same lot: the text names an ADU, accessory dwelling or accessory apartment, a garage or basement apartment, a carriage house, second dwelling unit, living quarters called a dwelling or apartment, or a guest house, cottage or in-law suite **with** a kitchen or kitchenette named. New construction and conversions of existing space ("garage to ADU", "into ADU", "ADU upfit") both count. | yes |
| `INLAW_NOKITCHEN` **(new)** | An in-law / mother-in-law suite or quarters (attached or detached, new or converted) whose text names no kitchen or kitchenette. Not an ADU (D-081 item 2). | central: no; no-kitchen sensitivity: yes |
| `LEGALIZE` | A unit that already exists but was never permitted ("existing unpermitted", "work done by previous owner", "bring into compliance", "after the fact", "as-built", "already built"). Not new (D-080). | no, reported separately |
| `EXISTING` | Work on an ADU that already exists: repair, remodel, renovation, "upgrade existing …", re-roof, deck, addition to it, removing it, or change of use away from an ADU. | no |
| `HOUSE_PLUS_ADU` | A permit for a new house whose text also names an ADU in it or on the lot. One SFD; the ADU is not counted (brief rule 3). | no |
| `NOT_ADU` | No new accessory unit: garage, studio, office, pool house, owner's suite or addition with no kitchen and not called a dwelling; text saying it is not an ADU; demolitions; the ADU named only as context; **(new)** a unit in an apartment or multifamily building ("MMF … basement unit upfit" in a complex) rather than accessory to a house. | no |
| `AMBIGUOUS` | May be a new unit but the text does not say enough (a guest house or pool house with a bath but no kitchen named; "upfit" of a space that may already be an ADU). In-law suites go to `INLAW_NOKITCHEN`, not here. | central: no; reported as a second sensitivity |

Tie-breaks (as in #386): the county work-type phrase "New. Accessory Dwelling Unit." (Mecklenburg) counts as
naming an ADU unless the rest of the text says otherwise. A parenthetical work-type label such as "(interior
renovation)" is ignored. "Upfit" or "addition" that turns space into an ADU is `NEW_ADU`; "renovation", "remodel",
"repair" or "upgrade existing" of an ADU is `EXISTING`. **(new)** An alteration word that refers to something else
("main house will have service upgrade"; "existing garage being moved and upgraded to ADU") does not make a new
ADU `EXISTING`. For Mecklenburg the sheet shows whether the same parcel has an earlier ADU-flagged permit; a 434
upfit on such a parcel is `EXISTING` unless the text says a second unit is being made. Two permits for the same
unit: each is judged on its own text.

### M2. Sample and pools

- **Data.** The processed permit tables in `~/lotline-data/processed/nc/permits/` as rebuilt offline by #391
  (`main` at `a54f34d9`, with #388 and #389). Descriptions are joined in memory from the same raw snapshots the
  rebuild read (Asheville 2026-11-11 pages, Greensboro 2026-11-09 pages, the registered Mecklenburg GeoPackage),
  **only for permit ids present in the holdout-filtered processed table**. Nothing is downloaded; no description
  is written to the repo.
- **Flagged:** `building_type_std == "ADU"`.
- **Strong stratum (read in full):** unflagged permits of the parser-eligible types whose text has an explicit
  ADU term (`ADU`, `accessory dwelling`, `accessory apartment`, `garage apartment`, `second dwelling`,
  `additional dwelling`, `accessory living`) **(new)** plus `garage apt` and `2nd dwelling`, the names #389
  added. In-law words stay in pool A.
- **Pool A (near-miss, central):** other unflagged eligible permits with: accessory, dwelling (not "single / one /
  two / multi family", "SF / MF / TH / 2F", "existing / principal / main dwelling"), guest, in-law / inlaw,
  granny, second unit, cottage, carriage, studio, pool house, living space / quarters, tiny house.
- **Pool B (broad words, sensitivity only):** suite, apartment / apt, kitchen(ette); Asheville also garage,
  basement, rental.
- Eligible types: Mecklenburg codes 101, 434, 437, 438 and no code; Asheville Residential `ADU_TEXT_CATEGORIES`
  plus the city's ADU categories; Greensboro Residential permits whose occupancy is in `ADU_OCCUPANCIES`, not
  Total Demolish. Excluding demolitions as before.
- **Strata:** Mecklenburg; Greensboro; Asheville before 2022; Asheville 2022 on (split on `issue_year`, as the #386
  code did).
- **Draws** **(new seeds)**: `numpy.random.default_rng(seed)` with base seeds Mecklenburg `20261121`, Asheville
  before 2022 `20261122`, Asheville 2022 on `20261123`, Greensboro `20261124`. Flagged: 30 (Greensboro: all 41,
  a census). Pool A: 100 (seed + 100) for Mecklenburg, Greensboro and Asheville before 2022, the size #386 ended
  with after its second amendment; 30 for Asheville 2022 on. Pool B: 30 (seed + 200).
- **(new) Seeded draws do not exclude permits read in #386**; a permit drawn again is judged again, blind.

### M3. Estimator (D-081 item 1)

- **Precision** p = `NEW_ADU` / judged flagged, 90% Wilson interval.
- **Misses:** FN = (`NEW_ADU` in the strong stratum, counted) + m × (pool-A size), m = pool-A miss rate, 90% Wilson.
- **TP** = p × N (N = flagged count). **Recall** r = TP / (TP + FN).
- **k = p / r** = (TP + FN) / N: true new ADUs per counted flag.
- **Intervals by simulation (D-081 item 1).** 100,000 independent draws p\* ~ Beta(x + ½, n − x + ½) and
  m\* ~ Beta(y + ½, n_A − y + ½) (Jeffreys, whose quantiles track Wilson's); each draw gives r\* and k\*.
  Reported: precision's Wilson interval, and the 5th–95th percentiles of r\* and k\*. Seed 20261125. The strong
  stratum is a census and enters as a constant. For Greensboro (flagged census) p is still drawn, for
  comparability with #386.
- **No-kitchen sensitivity** (`in_law_suite_needs_kitchen=False`): `INLAW_NOKITCHEN` counts as an ADU, and N
  becomes the source's no-kitchen flag count from #391 (Mecklenburg 459, Asheville 390, Greensboro 50; Asheville
  split by year in memory with the same setting). k′ = (TP′ + FN′) / N′, with TP′ and FN′ from the same labels
  counting `INLAW_NOKITCHEN` as yes. Because the extra no-kitchen flags already sit in the strong stratum or pool A
  of the central run, they are counted once, as true units, in TP′ + FN′.
- **Second sensitivity:** `AMBIGUOUS` also counted as yes.
- Pool B's misses are shown as a sensitivity row, not in the central k or its range.
- Misses in text with no ADU-like word are not estimated.
