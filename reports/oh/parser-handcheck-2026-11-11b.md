# Cincinnati parser hand check after the adapter fix and the second parser round (2026-11-11b)

Method: D-081 item 1 (k_parser = precision ÷ recall), protocol of `reports/oh/parser-handcheck-2026-11-11.md`
(#384) with new seeds. Why: #388 (Cincinnati adapter) and #389 (second shared-parser round) moved
Cincinnati from 29 to 18 ADU flags (`reports/adu-rebuild-2026-11-11b.md`, #391), and D-081 item 3 says
Cincinnati is checked again and takes precision ÷ recall from that check.

## 1. Judging rule (written and committed before any description was read)

Each sampled permit is read by hand from its raw work description and given one label:

| Label | Meaning | Counts as a new ADU? |
|---|---|---|
| **ADU** | The permit creates a new secondary dwelling unit (its own living quarters, kitchen named or not stated) on a lot with, or getting, a main house: a new detached ADU, carriage house or garage apartment, or a conversion or addition that creates a second unit (basement, attic, garage, addition) | Yes |
| **HOUSE+ADU** | The permit builds a new main house, and its text says an ADU is built under the same permit | Yes, one ADU |
| **NOKITCHEN** | An in-law or mother-in-law *suite* or *quarters* whose text names no kitchen (D-081 item 2) | No; ADU in the no-kitchen sensitivity |
| **HOUSE** | A new main house whose text names an ADU only as a feature or plan ("ADU-ready", "future ADU", "ADU removed from scope") | No |
| **LEGAL** | An ADU that was already built is legalized, permitted after the fact, inspected or certified | No; reported separately |
| **WORK** | Work on an existing ADU or carriage house (repair, alteration, finishes) | No |
| **DEV** | A coach unit or carriage-house apartment that is one of a multifamily development's buildings, not a second unit beside a house (D-081 item 3) | No |
| **OTHER** | Anything else: a townhouse, apartment building, garage or shed without a unit, a negated ADU ("not a dwelling unit"), a carriage house turned into a non-dwelling use | No |
| **UNCLEAR** | The text can't tell | Not-ADU for the central value; ADU at the range ends it pushes outward |

"ADU" with no kitchen stated still counts: item 2 applies only to in-law or mother-in-law *suites* and
*quarters*, as in the parser's Rule 10.

**Sample.**
- **Flagged** = rows of the rebuilt processed table with `building_type_std == "ADU"` (all have `adu_type`).
  All of them are read (18 expected).
- **Near-miss net** = issued permits in the processed table that are not flagged and whose joined combo text
  matches, case-insensitive: `carriage`, `garage apartment`, `garage apt`, `in-law`, `in law`, `inlaw`,
  `mother`, `accessory dwelling`, `ADU` (whole word), `second unit`, `2nd unit`, `second dwelling`,
  `2nd dwelling`, `granny`, `dwelling unit`, `apartment`, `suite`, `cottage`, `guest house`,
  `living quarters` (the #384 list plus the #389 names).
- **Draw:** `numpy.random.default_rng(20261121)` orders the near-misses without replacement; the first 30
  are the registered sample. If the net holds 90 or fewer permits, all of them are read (a census) and the
  census is the headline, as in #384; the seeded 30 are also reported.
- **Blind reading:** flagged permits and near-misses are put in one sheet, shuffled with
  `numpy.random.default_rng(20261122)`, and shown with only a row number, permit number and text, never the
  flag or the parsed type. Labels are written to a file before the sheet is joined back to the flags.
- Permit numbers with several combo rows are judged once, on all their text joined (as the adapter joins it).
- Text source: the 2026-11-11 raw combo snapshot (`raw/cincy_permits/2026-11-11/combo_permits`); only permits
  in the processed table count. Ohio has no holdouts (`config/states/oh.yaml`).

**Measures.**
- **Precision** p = (ADU + HOUSE+ADU) / flagged permits read.
- **Recall** r = flagged true ADUs / (flagged true ADUs + true ADUs among the near-misses), the near-miss
  misses scaled to the net's size if only a sample is read. The net reaches only permits whose text uses
  ADU-like words, and Cincinnati only downloads combo text with six words (`COMBO_WORDS`), so r is recall
  inside the download net: an upper bound on true recall.
- **k_parser = p / r** (D-081 item 1).
- Intervals: 90% Wilson (z = 1.645) on p and r. The 90% range for k is simulated (D-081 item 1):
  200,000 independent draws, p ~ Beta(x_p + 0.5, n_p − x_p + 0.5) and r ~ Beta(x_r + 0.5, n_r − x_r + 0.5)
  (Jeffreys), seed `numpy.random.default_rng(20261123)`, k = p / r, 5th and 95th percentiles.
- **No-kitchen sensitivity:** the same with NOKITCHEN counted as ADU, both in the flags (the parser's
  `in_law_suite_needs_kitchen=False` run) and among the near-misses.
- **Checks asked for:** the 11 development carriage houses (2020P05427–5437) and the negated pool shed
  (2024P06273) are no longer flagged, and the #384 miss (2026P04020) now is.

**What I knew before writing the rule:** the flagged count (18), the no-kitchen sensitivity count (19), the
#384 report and its examples, and the adapter and parser code. No description had been read in this session.

## 2. What was read

- **Flagged:** 18 permits, all read.
- **Near-miss net:** 70 permits. That is under the 90 limit, so **all 70 were read (a census)**; the seeded 30
  (`default_rng(20261121)`) are reported as well. The net is larger than #384's 59 because the 11 development
  carriage houses and the negated shed have left the flags and now sit in it, and two names were added.
- **Blinding:** the 88 permits were read in one shuffled sheet (`default_rng(20261122)`) with only a row
  number, permit number and text. All 88 labels were written and the file locked before the sheet was joined
  to the flags. The sheet showed permit numbers, and I knew the #384 numbers of the development permits, the
  shed and the missed ADU, so blinding was not complete for those 13. Their texts leave no room for doubt
  either way (see §5).

## 3. Results

### 3.1 Flagged permits (18)

| Label | Permits | Example (short) |
|---|---:|---|
| ADU | 14 | "NEW DETACHED GARAGE WITH 2ND FLOOR ADU"; "985SF ADU AT BASEMENT LEVEL"; "RENOVATION OF EXISTING 2ND FLOOR STORAGE ABOVE GARAGE INTO ACCESSORY DWELLING UNIT" |
| UNCLEAR | 4 | "NEW CARRIAGE HOUSE" (2016P09903); "NEW DETACHED CARRIAGE HOUSE AND FENCE" (2023P09216); "REBUILD CARRIAGE HOUSE FROM EXISTING SHELL" (2022P04151); "NEW DETACHED GARAGE /CARRIAGE HOUSE WITH FINISHED SPACE ABOVE" (2022P04336) |
| DEV, OTHER, LEGAL, HOUSE, HOUSE+ADU, WORK, NOKITCHEN | 0 | |

All four unclear permits say "carriage house" and nothing about a unit, a kitchen or living quarters. A
Cincinnati carriage house can be a garage, a studio or a dwelling.

### 3.2 Near-misses (census of 70)

| Label | All 70 | Seeded 30 | Example (short) |
|---|---:|---:|---|
| ADU (missed) | **0** | 0 | |
| UNCLEAR | 2 | 1 | "ALTERATION OF EXISTING CARRIAGE HOUSE INTO SINGLE FAMILY DWELLING" (2023P09777); "CONVERSION OF EXISTING CARRIAGE HOUSE T STUDIO/WORK SPACE WITH FULL BATH AND KITCHENETTE" (2023P09580) |
| NOKITCHEN | 1 | 1 | "EXCAVATION/ ADDITION OF 'MOTHER-IN-LAW SUITE'" (2020P01254) |
| DEV | 11 | 2 | the 2020 masterplan carriage houses, 2020P05427–5437 |
| LEGAL | 1 | 1 | 2026P00690: certificate of occupancy, "2 FAMILY - ADU - 2 FAMILY TO SINGLE FAMILY" |
| HOUSE | 1 | 1 | 2023P07485: "NEW SINGLE FAMILY DWELLING … ADU IN BASEMENT REMOVED FROM PROJECT SCOPE" |
| WORK | 7 | 3 | "CARRIAGE HOUSE ALTERATION"; "REPAIR CARRIAGE HOUSE" |
| OTHER | 47 | 21 | townhouse rows, apartment buildings, the negated pool shed, "RENOVATE ATTACHED CARRIAGE HOUSE INTO ADDITIONAL BEDROOM" |

### 3.3 Precision, recall and k_parser = precision ÷ recall

Precision and recall have 90% Wilson intervals; k's 90% range is simulated (200,000 independent Jeffreys
beta draws, seed 20261123), per §1.

| Reading | Precision | 90% Wilson | Recall | 90% Wilson | **k** | 90% range (sim.) |
|---|---:|---:|---:|---:|---:|---:|
| **Central** (unclear = not ADU) | **14 / 18 = 0.78** | 0.59–0.90 | **14 / 14 = 1.00** | 0.84–1.00 | **0.78** | **0.61–0.95** |
| Unclear near-misses are ADUs | 14 / 18 = 0.78 | 0.59–0.90 | 14 / 16 = 0.88 | 0.68–0.96 | 0.89 | 0.67–1.16 |
| Unclear flags are ADUs | 18 / 18 = 1.00 | 0.87–1.00 | 18 / 18 = 1.00 | 0.87–1.00 | 1.00 | 0.92–1.09 |
| All six unclear are ADUs | 18 / 18 = 1.00 | 0.87–1.00 | 18 / 20 = 0.90 | 0.74–0.97 | 1.11 | 0.98–1.31 |

**Under the rule in §1, k_parser = 0.78. Across the four readings the 90% range runs from 0.61 to 1.31.**
k is below 1: the parser now misses nothing in its net, and the flags still hold up to four permits that may
not be units. The range is wide because the four bare "carriage house" flags decide it.

**The seeded 30 alone** hold no missed ADU, so they give the same recall (14/14) and the same k.

**A second reader would likely read two of the four differently.** The #384 check, by another session with the
same rule, labelled 15 of the 17 surviving flags ADU and 2022P04151 and 2022P04336 unclear. So it read
"NEW CARRIAGE HOUSE" and "NEW DETACHED CARRIAGE HOUSE AND FENCE" as ADUs, and the studio with a kitchenette
(2023P09580) as OTHER. With those labels: precision 16/18 = 0.89, recall 16/16, **k = 0.89 (0.74–1.02)**.
After unblinding I looked at the two permits' main-file fields: both are work class `RNEW` (new residential
building) under use group `1-2-3 FM`, with no floor area or valuation. An accessory garage is usually filed as
`RACCESS`, as 2022P04336 is, so `RNEW` leans towards a dwelling. It does not settle it, and the central labels
are left as read.

### 3.4 No-kitchen sensitivity (D-081 item 2)

The parser's `in_law_suite_needs_kitchen=False` run adds one flag, 2020P01254 ("ADDITION OF 'MOTHER-IN-LAW
SUITE'"), for 19 flags (`reports/adu-rebuild-2026-11-11b.md`). It is the only NOKITCHEN permit in the net, and
the sensitivity counts it as an ADU.

| Reading | Precision | Recall | k | 90% range (sim.) |
|---|---:|---:|---:|---:|
| Central | 15 / 19 = 0.79 | 15 / 15 = 1.00 | 0.79 | 0.63–0.95 |
| Unclear near-misses are ADUs | 15 / 19 | 15 / 17 = 0.88 | 0.89 | 0.69–1.15 |
| Unclear flags are ADUs | 19 / 19 | 19 / 19 | 1.00 | 0.92–1.09 |
| All unclear are ADUs | 19 / 19 | 19 / 21 = 0.90 | 1.11 | 0.98–1.29 |

The sensitivity changes the count by one permit and k by 0.01: Cincinnati's kitchen rule hardly matters.

## 4. Recall is only an upper bound

As in #384 §2.1: Cincinnati's main permit file has no work description, and the adapter downloads combo text
only for rows with `ADU`, `ACCESSORY DWELLING`, `CARRIAGE`, `GARAGE APARTMENT`, `IN-LAW` or `TOWNHO`
(`cincy_permits.COMBO_WORDS`). An ADU written up as a "second unit", "mother-in-law apartment" or "apartment
above the garage" was never downloaded, so this check cannot see it. Recall 1.00 is recall **inside the
download net**. Widening the net needs a new fetch (Ben's call; not done).

## 5. Checks asked for

| Check | Result |
|---|---|
| The 11 development carriage houses (2020P05427–5437) are no longer flagged | **Yes.** All 11 are in the near-miss net, unflagged, read as DEV |
| The negated pool shed (2024P06273, "NOT A DWELLING UNIT/ADU") is no longer flagged | **Yes.** Unflagged, read as OTHER |
| The #384 miss (2026P04020, garage with an ADU above, house permitted separately) is now caught | **Yes.** Flagged `detached`, read as ADU |
| The legalization (2026P00690) stays unflagged | Yes |
| "ADU IN BASEMENT REMOVED FROM PROJECT SCOPE" (2023P07485) stays unflagged | Yes |

No new false positive of a known kind appeared, and no new miss.

## 6. Proposed undercount-table row

Not written to `config/params/adu.yaml`; for Ben to accept with the other D-081 item 6 rows in one PR.
`kind: parser`, `interval: 0.90`. This replaces the #384 proposal (1.07, which was 1 / recall on the old flags).

| source | place | k | 90% range | citation |
|---|---|---:|---|---|
| `cincy_permits` | Cincinnati (OH) | **0.78** | 0.61–1.31 | `reports/oh/parser-handcheck-2026-11-11b.md` §3.3: precision 14/18 (4 bare "carriage house" flags unclear), recall 14/14 inside the combo-text download net (census of 70 near-misses, 0 missed); k = precision ÷ recall with simulated 90% range; the range spans the four readings of the 6 unclear permits. Recall is an upper bound (6-word download net). No-kitchen sensitivity: 0.79 |

If Ben would rather settle the four unclear flags than carry them in the range, the simplest route is a second
reader for those four permits only. Reading them as #384 did gives k = 0.89 (0.74–1.02).

*Hand judgments by Claude Code (Opus 5.5) on 2026-11-11, against the rule committed first (commit
`a83064d2`). Scripts were throwaway and kept in the session scratchpad. The seeds and the net above are enough
to redraw the same sheet from the 2026-11-11 raw snapshot and the rebuilt processed table (#391).*
