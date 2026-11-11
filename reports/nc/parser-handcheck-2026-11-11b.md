# NC parser hand check after the second parser round (#389, #391): Mecklenburg, Greensboro, Asheville

*2026-11-11 · D-081 items 1 and 6 · per source, never pooled · no model run*

The method (§§ M1–M3 at the end) was written and committed (`f90a2efb`) before any sampled permit was read; the
git history of this file shows the order. One change was made after reading, for Mecklenburg only; it is
explained in §2 and both numbers are shown.

## Summary

The second parser round (#389) and the offline rebuild (#391) moved three NC parser sources. This check measures
each one again with the #386 protocol and new seeds, and reports k = precision ÷ recall (D-081 item 1).

| Source | Flagged | Precision (90%) | Recall (90%) | **k = p ÷ r (90%)** | D-081 interim | 1 ÷ r |
|---|---:|---|---|---|---:|---:|
| `meck_permits` | 426 | 27/30 = 0.90 (0.77–0.96) | 0.92 (0.80–0.96) | **0.98 (0.86–1.13)** | 0.93 | 1.09 |
| ↳ as pre-registered (before the frame fix in §2) | 426 | 0.90 (0.77–0.96) | 0.89 (0.75–0.95) | 1.02 (0.88–1.19) | | 1.13 |
| `asheville_permits`, issued before 2022 | 220 | 28/30 = 0.93 (0.82–0.98) | 0.63 (0.57–0.68) | **1.47 (1.33–1.61)** | 1.31 | 1.58 |
| `asheville_permits`, issued 2022 on | 153 | 27/30 = 0.90 (0.77–0.96) | 0.90 (0.78–0.96) | **1.00 (0.87–1.16)** | 0.99 | 1.11 |
| `greensboro_permits` | 41 (all read) | 40/41 = 0.98 (0.90–0.99) | 0.70 (0.41–0.88) | **1.39 (1.10–2.33)** | 0.84 | 1.42 |

Precision has a 90% Wilson interval. Recall and k have the 5th–95th percentiles of 100,000 simulation draws, with
precision and the near-miss rate drawn independently (M3).

**No-kitchen sensitivity** (`in_law_suite_needs_kitchen=False`). Here in-law suites with no kitchen count as
ADUs, and N is the no-kitchen flag count:

| Source | N (no-kitchen) | k, no-kitchen (90%) | k, no-kitchen and `AMBIGUOUS` counted (90%) |
|---|---:|---|---|
| Mecklenburg | 459 | 1.00 (0.86–1.19) | 1.10 (0.93–1.32) |
| Asheville before 2022 | 231 | 1.44 (1.30–1.57) | 1.69 (1.52–1.84) |
| Asheville 2022 on | 160 | 1.00 (0.86–1.17) | 1.15 (0.97–1.34) |
| Greensboro | 50 | 1.43 (1.03–2.36) | 2.00 (1.35–3.16) |

The no-kitchen setting barely moves k. The extra flags are in-law suites, and under this setting they are true,
so the numerator and the denominator grow together.

What changed since the #386 interim values:

- **Greensboro, 0.84 → 1.39.** The kitchen rule fixed precision: the in-law suites with no kitchen that made
  10 of 44 flags are gone, and 40 of 41 flags are real. Recall is now the issue. Three ADUs that name
  themselves are still missed (§3), and one near-miss draw ("Residential Garage with Dwelling Unit") is a miss.
  With 1,380 near-miss permits, that one draw adds 14 estimated misses. So the range stays wide.
- **Asheville before 2022, 1.31 → 1.47.** Precision rose from 0.77 to 0.93, because house + ADU permits are now
  read as the house. Recall rose only from 0.58 to 0.63. The ADU's own permit still often cites or repeats the
  house ("NEW SINGLE FAMILY ADU", "ADU IN BASEMENT OF SINGLE FAMILY RESIDENCE"), and the parser reads that as a
  conflict (25 of 55 named misses; §3). The D-078 §3 low-recall flag should stay on this row.
- **Mecklenburg, 0.93 → 0.98.** This is close to 1: about 3 in 30 flags are false and about 8% of true ADUs are
  missed. Both known #391 issues show up. One of the 30 flagged draws is an apartment-complex "MMF … Basement Unit
  Upfits" permit on code 437. One named miss is the "Existing Garage Being Moved and **Upgraded** to ADU"
  permit.
- **Asheville 2022 on, 0.99 → 1.00.** No change. Two of the three false flags come from the description rule on
  alteration permits, not from the city's ADU types.
- **The "upgrade" veto** is confirmed as two real misses: the Mecklenburg permit above, and Asheville's "BUILD NEW
  450 SQ FT ADU … MAIN HOUSE WILL HAVE SERVICE UPGRADE" (2016).
- **Legalizations (D-080):** 1 flagged permit in Asheville 2022 on legalizes an existing unit. Its text reads
  "converted … several years ago without a permit; this is a retroactive permit". The parser's legalization rule
  missed "retroactive" (spelled "RETROACTOVE") and "without a permit". There are 4 more legalizations among
  unflagged permits (Asheville: 3 before 2022, 1 from 2022), which inflate no count.
- **House + ADU:** 2 of 30 flagged Asheville pre-2022 draws are new-house permits that name an ADU: "3 STORY NEW
  BUILD STRUCTURE … TO BE ATTACHED ADU" and "TWO STORY RESIDENTIAL DWELLING AND ADU". There are none in the
  other sources.

**k below 1.** Mecklenburg's central k (0.98) is under 1. That is allowed under D-081 (precision ÷ recall), but
`adu_flag_undercount` still says `k >= 1` in its `unit` line. Ben should decide whether the table accepts k < 1 or
floors it at 1.

## 1. Results by source

"Strong" is every unflagged eligible permit that names an ADU outright; all of them were read. "Pool A" is the
near-miss pool and "pool B" the broad-word pool (sensitivity only). TP = precision × flagged count; FN = strong
misses + pool-A miss rate × pool-A size; k = (TP + FN) / flagged.

### Mecklenburg (`meck_permits`)

| | Size | Judged | NEW_ADU | INLAW_NOKITCHEN | AMBIGUOUS | other |
|---|---:|---:|---:|---:|---:|---|
| Flagged | 426 | 30 | 27 | 0 | 0 | 2 not, 1 existing |
| Strong (all read, with the §2 addendum) | 29 | 29 | 11 | 0 | 2 | 14 not ("NOT AN ADU", "GARAGE ONLY, NO ADU"), 2 existing |
| Pool A | 2,139 | 99 | 1 | 2 | 2 | 93 not, 1 existing |
| Pool B | 17,549 | 29 | 0 | 0 | 1 | 28 not |

- TP = 383; FN = 11 + 0.010 × 2,139 = 32.6; **k = 0.98 (0.86–1.13)**; recall 0.92 (0.80–0.96).
- **False flags (3 of 30):**
  - the apartment "MMF The Colony Apartments – Bldg 5 Basement Unit Upfits" (code 437; #391 point 1);
  - a "Screened porch … New. Accessory Dwelling Unit." permit, which has the ADU work type but is a porch;
  - "issued to allow a CO to be created for this ADU … originally permitted … under B4075783". This is a second
    permit for a unit already counted, so it is a double count.
- **Work type alone (tie-break M1):** 3 of the 27 true flags rest on "New. Accessory Dwelling Unit." while their
  project names name another structure ("Pool house", "SHED", "Pool House & Pool"). Counted as not ADUs, k is
  0.88 (0.74–1.05).
- **Named misses (11).** The "upgrade" veto ("Existing Garage Being Moved and Upgraded to ADU"); "existing garage
  upfit" with the ADU work type; "Garage addition … Add Second Story. ADU"; "Master closet, screen porch & garage
  Apt. addition"; a reissued "New Residence" permit whose note says the unit is now "the accessory dwelling
  unit"; "Bolton Mother in law suite" with the county work type "Accessory Dwelling Unit". The kitchen rule vetoes
  that last one even though the county typed it an ADU. The other 5 are the run-together texts in §2.
- **Pool A miss:** "Harrison Tucker Guest House New. SF Dwelling Detached."

### Asheville before 2022 (`asheville_permits`, issue years 2014–2021)

| | Size | Judged | NEW_ADU | INLAW_NOKITCHEN | AMBIGUOUS | other |
|---|---:|---:|---:|---:|---:|---|
| Flagged | 220 | 30 | 28 | 0 | 0 | 2 house + ADU |
| Strong (all read) | 147 | 147 | 55 | 0 | 2 | 45 house + ADU, 18 existing, 3 legalize, 24 not |
| Pool A | 426 | 100 | 15 | 2 | 13 | 65 not, 4 house + ADU, 1 existing |
| Pool B | 2,394 | 30 | 0 | 0 | 0 | 30 not |

- TP = 205; FN = 55 + 0.15 × 426 = 119; **k = 1.47 (1.33–1.61)**; recall 0.63 (0.57–0.68).
- **Why the 55 named ADUs are missed.** Sorted by the parser's own `evidence`:
  - 25: `conflict: an ADU and another dwelling type`. These are ADU records that cite or repeat the house: "NEW
    SINGLE FAMILY ADU FOR …", "ADU IN BASEMENT OF SINGLE FAMILY RESIDENCE", "ACCESSORY DWELLING UNIT … REF.
    16-01065 FOR NEW SFD", and Accessory Structure records that repeat the house permit's text.
  - 15: `ADU named: unit change unclear`. Here an alteration word vetoes a new unit: "NEW DETACHED GARAGE WITH
    ACCESSORY APARTMENT", "SECOND STORY ADDITION OF A 2 BEDROOM/1 BATHROOM ADU", and the "SERVICE UPGRADE" permit.
  - 12: the parser says `ADU` but the adapter drops it, mostly through `NEW_HOUSE` matching "REF. NEW SINGLE
    FAMILY HOME" in an ADU's own permit ("CONSTRUCTION OF A NEW BASEMENT LEVEL ACCESSORY APARTMENT …, REF. NEW
    SINGLE FAMILY HOME PERMIT 17-04931"). Other drops come from words like "demolition".
  - 3 other.
- **Pool A misses (15):** 10 of them have no ADU name the parser knows: "632 SQ FT ACCESSORY APT", "MORRIS GARAGE
  WITH ACCESSORY APT.", "CHANGE FINISHED BASEMENT INTO ACCESSORY DEWELLING UNIT", "NEW GUEST HOUSE- STUDIO
  APARTMENT", "ONE BATH STUDIO APARTMENT ON SLAB", "DETACHED STUDIO / OFFICE DWELLING".
- **Judgement on paired records:** where a project has a house record and a separate Accessory Structure record
  with the same text, the accessory record was judged the ADU's (`NEW_ADU`) and the house record
  `HOUSE_PLUS_ADU`. Judging all 6 such accessory records as `HOUSE_PLUS_ADU` instead gives k ≈ 1.43.

### Asheville 2022 on (`asheville_permits`, issue years 2022–2026)

| | Size | Judged | NEW_ADU | INLAW_NOKITCHEN | AMBIGUOUS | other |
|---|---:|---:|---:|---:|---:|---|
| Flagged | 153 | 30 | 27 | 0 | 0 | 2 not, 1 legalize |
| Strong (all read) | 37 | 37 | 1 | 0 | 1 | 16 house + ADU, 10 existing, 9 not |
| Pool A | 219 | 30 | 2 | 1 | 3 | 22 not, 1 existing, 1 legalize |
| Pool B | 1,256 | 30 | 0 | 0 | 0 | 30 not |

- TP = 138; FN = 1 + 0.067 × 219 = 15.6; **k = 1.00 (0.87–1.16)**; recall 0.90 (0.78–0.96).
- **False flags:** the retroactive garage apartment (legalization); "FINISH BASEMENT. SEPARATE PERMIT WILL BE
  APPLIED FOR TO CREATE ADU", where the ADU is a future permit; and an alteration whose mother-in-law suite comes
  with "a bathroom & kitchen have been demoed".
- **Misses:** "BUILD A 13'X17' SINGLE STORY ADU … GUEST HOUSE" (strong, `unit change unclear`). The two pool-A
  misses are "RECD AMENDMENT TO ADD A MOTHER-IN-LAW SUITE. ADD BATHROOM, KITCHEN …" and a basement
  "MOTHER-IN-LAW SUITE … FULL BATHROOM AND KITCHENETTE". The parser's kitchen rule did not see "KITCHENETTE (WET
  BAR …)" in the second, or the amendment's kitchen in the first.
- Records that the city typed `ADU Attached` but whose text describes the whole new house were judged `NEW_ADU`
  (the ADU's record; the house has its own SFD record).

### Greensboro (`greensboro_permits`)

| | Size | Judged | NEW_ADU | INLAW_NOKITCHEN | AMBIGUOUS | other |
|---|---:|---:|---:|---:|---:|---|
| Flagged | 41 | 41 (all) | 40 | 1 | 0 | – |
| Strong (all read) | 8 | 8 | 3 | 0 | 1 | 2 existing, 2 not ("not an ADU", "not to be used as ADU") |
| Pool A | 1,380 | 100 | 1 | 1 | 2 | 95 not (mostly sheds: "ACCESSORY BLDG 10X16"), 1 existing |
| Pool B | 2,616 | 30 | 0 | 0 | 0 | 30 not |

- TP = 40; FN = 3 + 0.01 × 1,380 = 16.8; **k = 1.39 (1.10–2.33)**; recall 0.70 (0.41–0.88).
- **False flag:** "Sunroom/porch and in-law suite addition, kitchen remodel". The kitchen rule takes the house's
  kitchen remodel as the suite's kitchen.
- **Named misses:**
  - "Framing, Plumbing, Electrical, HVAC … for Accessory Dwelling Unit": the HVAC alteration word vetoes it;
  - "Renovate existing heated second floor of existing garage to be functional ADU";
  - "demolish the existing 2 car garage and rebuild with a second level ADU": the parser says `ADU`, but the
    demolition is dropped.
- **Pool A miss:** "Residential Garage with Dwelling Unit" (2023). The parser does not read a "garage with
  dwelling unit" as an ADU.
- The upper end (2.33) comes from the near-miss pool. With 1 miss in 100 draws from 1,380 permits, up to about 60
  more ADUs are possible.

## 2. Mecklenburg frame fix (made after reading; both numbers shown)

While judging, one pool-B draw turned out to be the county's run-together text "ADUNew. SF Dwelling Detached. ;
Mother suite". The project name "ADU" is glued to the work type "New.", so the strong-stratum pattern `\bADU\b`
missed it. Older Charlotte filings also abbreviate the term as "Acc Dwell Unit". All unflagged eligible permits
with these forms (`ADU` followed by New/Upfit/Addition/Repair, `ADU` after a lowercase letter, or "Acc Dwell") were
counted: there are **5**. All 5 were read, and all name an ADU: "Acc Dwell Unit – … DETACHED GARAGE W/ caretaker
apartment", "1909 Kenwood ADUNew. Detached Garage > 1 story", and others. None of the 5 is flagged, because the
parser does not find the term either.

These 5 move into the strong stratum, and the pools shrink by the ones they held (pool A −1, pool B −2). Both
results are in the Summary:

- as pre-registered: k = 1.02 (0.88–1.19);
- with the frame fixed: k = 0.98 (0.86–1.13).

The difference is small. The fix matters most for pool B, which as pre-registered extrapolated 1 miss in 30 to
585 permits (k with pool B up to 6.1). After the fix, pool B has 0 misses in 29.

## 3. Proposed fixes (not made)

These are recall and precision points for whoever does the next parser round. They are not made here.

- `meck_permits`: before parsing, split the project name from the work type ("ADUNew." → "ADU New."), and read
  "Acc Dwell Unit" as an ADU name (5 misses). Guard code 437 against apartment complexes ("MMF", "Apartments",
  "Unit #'s") (#391 point 1).
- Shared parser, alteration veto: do not let "upgrade(d)", "HVAC" or "addition" veto a named new ADU when the
  same clause says "new", "to ADU", "create" or "build" (#391 point 2; 2 confirmed misses here plus about 15 in
  Asheville's strong stratum).
- Shared parser, conflict: when the text says "single family ADU", "ADU in basement of single family residence /
  new home" or "ADU … ref. … SFD", return `ADU`. The house is the context, not a second dwelling (25 Asheville
  misses).
- `asheville_permits.NEW_HOUSE`: do not match "REF. NEW SINGLE FAMILY HOME …" when the text's subject is an
  accessory apartment.
- New names: "accessory apt", "studio apartment" (detached or basement), "garage with dwelling unit", "dwelling
  unit" in a garage or shed conversion.
- Legalization: add "retroactive", "without a permit".
- Kitchen rule: count "kitchenette (wet bar …)" and a kitchen added in an amendment. Don't count a "kitchen
  remodel" of the main house as the suite's kitchen.

## 4. Proposed undercount-table rows

For the session that collects `adu_flag_undercount` rows (D-081 item 6: all k values in one PR). These are
**not** written to `config/params/adu.yaml`.

| Source | Place | kind | value | low | high | interval | report | notes |
|---|---|---|---:|---:|---:|---|---|---|
| `meck_permits` | Charlotte and the Mecklenburg towns (NC) | parser | 0.98 | 0.86 | 1.13 | 0.90 | `reports/nc/parser-handcheck-2026-11-11b.md` | k = p ÷ r (D-081). p 27/30, r 0.92. As pre-registered 1.02 (0.88–1.19); no-kitchen 1.00 (0.86–1.19). Replaces 1.04 (1.0–1.27). Needs k < 1 allowed in the table (§ Summary) |
| `asheville_permits`, before 2022 (`last_year: 2021`) | Asheville (NC), before 2022 | parser | 1.47 | 1.33 | 1.61 | 0.90 | same | p 28/30, r 0.63. Keep `low_recall: true` (D-078 §3). No-kitchen 1.44 (1.30–1.57). Replaces 1.59 (1.43–1.79) |
| `asheville_permits`, 2022 on (`first_year: 2022`) | Asheville (NC), 2022 on | field (unchanged) | – | – | – | – | same | Keep the field prior (D-081 item 1: field rows unchanged). The hand check gives 1.00 (0.87–1.16), inside the prior's range; recorded as a check only |
| `greensboro_permits` | Greensboro (NC) | parser | 1.39 | 1.10 | 2.33 | 0.90 | same | p 40/41 (census), r 0.70. Wide range from the 1,380-permit near-miss pool. No-kitchen 1.43 (1.03–2.36). Replaces the k = 1 placeholder |

## 5. Reproducing this check

- The scripts (`load.py`, `draw.py`, `addendum.py`, `score.py`), the labels (sheet row or permit id, stratum and
  label; no description text) and `results.json` are in the session's shared notes folder,
  `nc-parser-handcheck-2026-11-11b/`, not in the repo, because they read raw permit text in memory.
- Pool sizes and the no-kitchen extra counts were computed before any description was read. Asheville's
  no-kitchen N is split by year with a parser-level count (11 before 2022, 7 from 2022). Their sum, 391, differs
  from #391's full rebuild (390) by one permit; Mecklenburg and Greensboro use #391's totals (459, 50).
- Demolition words exclude permits from pools A and B only, never from the strong stratum. #386 found a real
  "demolish … garage and rebuild with … ADU" there.
- One reader judged every permit. There was no second coder.

## 6. What this does not do

- No engine, scenario, fit or calibration run; no download; no `--unblind`; no change to `config/` or to code.
- Misses in text with no ADU-like word are not estimated.

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
