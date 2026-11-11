# Ohio parser hand check after the shared parser fix: Cincinnati and Cleveland (2026-11-11)

Method: D-074 step 1 as amended by D-078 §2–3 (`docs/analysis_plan.md`), run per source, never pooled.
Ben approved re-measuring Cincinnati on 2026-11-11, because the parser fix (#376, #380) added 3 ADUs there
(`reports/adu-rebuild-2026-11-11.md`). Cleveland is a confirmation only: the fix did not change its counts.

## 1. Judging rule (written and committed before any description was read)

Each sampled permit is read by hand from its raw work description and given one label:

| Label | Meaning | Counts as a new ADU? |
|---|---|---|
| **ADU** | The permit creates a new secondary dwelling unit (its own living quarters, kitchen or not stated) on a lot with, or getting, a main house: a new detached ADU, carriage house or garage apartment, or a conversion or addition that creates a second unit (basement, attic, garage, addition) | Yes |
| **HOUSE+ADU** | The permit builds a new main house, and its text says an ADU is built under the same permit | Yes, one ADU, and the permit is still one SFD (Ben, 2026-11-11) |
| **HOUSE** | A new main house whose text names an ADU only as a feature or plan ("ADU-ready", "future ADU", "garage, no ADU"), with no ADU built under this permit | No: one SFD |
| **LEGAL** | An ADU that was already built is being legalized, permitted after the fact, inspected or certified (Ben, 2026-11-11) | No; reported separately |
| **WORK** | Work on an existing ADU or carriage house (repair, roof, porch, alteration, change of finishes) | No |
| **OTHER** | Anything else: a townhouse, a garage without a unit, a care facility, an in-law *bedroom* without separate quarters, a negated ADU ("not an ADU") | No |
| **UNCLEAR** | The text can't tell | Reported; counted both ways as a range |

- A permit is **flagged** if the processed table gives it `adu_type` (any value) or `building_type_std = ADU`.
- **Precision** = (ADU + HOUSE+ADU) / flagged permits read.
- **Recall** among the pool = flagged true ADUs / (flagged true ADUs + true ADUs found among the near-misses).
  The near-miss net only reaches permits whose text uses ADU-like words, so this recall is an upper bound
  on the true recall, as in `reports/oh/adu-coverage-and-undercount.md` §3.3.
- **k_parser = 1 / recall**, with a 90% Wilson interval on recall (z = 1.645), inverted.
- **UNCLEAR** permits are counted as not-ADU for the central value and as ADU for the range ends that they
  push outward.
- Duplicated permit numbers (one per plan-review item) are judged once, on all their text joined.
- Near-miss draw: `numpy.random.default_rng(20261111)` choosing without replacement from the non-flagged
  permits whose description matches the near-miss words (case-insensitive): `carriage`, `garage apartment`,
  `garage apt`, `in-law`, `in law`, `inlaw`, `mother`, `accessory dwelling`, `ADU` (whole word), `second unit`,
  `2nd unit`, `granny`, `dwelling unit`, `apartment`, `suite`, `cottage`, `guest house`. All of them if
  there are 30 or fewer.

**What I knew before writing the rule:** each source's count of flagged permits (Cincinnati 29, Cleveland 15)
and the adapters' code. No description had been read in this session.

**Inputs (all read-only, nothing re-downloaded):**
- `processed/oh/permits/cincy_permits.parquet` and `cle_permits.parquet` in `LOTLINE_DATA_DIR`, rebuilt
  2026-11-11 (`reports/adu-rebuild-2026-11-11.md`). Ohio has no holdouts (`config/states/oh.yaml`), so these
  tables are the holdout-filtered ones.
- The 2026-11-11 raw snapshots, for the work descriptions (the processed tables don't keep the text):
  `raw/cincy_permits/2026-11-11/combo_permits` and `raw/cle_permits/2026-11-11/building_permits`.
- Only permits in the processed table count (issued, not withdrawn or voided).

## 2. Cincinnati (`cincy_permits`)

### 2.1 What the near-miss net can reach

Cincinnati's main permit file has no work description. Text comes only from the combo-permit file, and the
adapter downloads only combo rows whose text has `ADU`, `ACCESSORY DWELLING`, `CARRIAGE`,
`GARAGE APARTMENT`, `IN-LAW` or `TOWNHO` (server-side filter, `cincy_permits.COMBO_WORDS`). That leaves
224 issued permits with text. **An ADU described only as a "second unit", "mother-in-law apartment",
"granny flat" or "apartment above the garage" was never downloaded, so this check cannot see it.** Reaching
those would mean a new download with a wider filter, which this task rules out. So the recall below is
recall *inside the download net*. It is an upper bound on the true recall.

### 2.2 Flagged permits: all 29 read

| Label | Permits | Years | Example (short) |
|---|---:|---|---|
| ADU | 15 | 2017, 2020, 2023–2026 | "NEW DETACHED GARAGE WITH ADU ON SECOND FLOOR"; "985SF ADU AT BASEMENT LEVEL" |
| UNCLEAR | 2 | 2022 | "REBUILD CARRIAGE HOUSE FROM EXISTING SHELL"; "garage/carriage house with finished space above" |
| OTHER: carriage houses in a 36-building development | 11 | 2020 | "Carriage House with 3 private garages … one-bedroom apartment unit above, within a 36 residential building masterplan" |
| OTHER: negated | 1 | 2025 | a pool shed, "NOT A DWELLING UNIT/ADU" |
| LEGAL, HOUSE, HOUSE+ADU | 0 | | |

- **The 11 development carriage houses** (2020P05427–5437) share one parcel with that project's 25 apartment
  buildings (`R-2`, 4 and 6 units). Each has garages for 2 or 3 households and one apartment above. They are
  new homes, but the developer's coach units in a multifamily site, not a homeowner's second unit beside a
  house. The parser reads "carriage house" and calls each one an ADU.
- **The negated shed** (2024P06273): the parser fix's negation handling catches "not an ADU" but not
  "NOT A DWELLING UNIT/ADU".
- **Precision: 15 / 29 = 0.52** (90% Wilson 0.37–0.66). It is 17/29 = 0.59 if both unclear permits are ADUs.
- **Effect on the counts:** 2020 drops from 12 to 1, and 2025 from 4 to 3. The other years stand
  (2022's 2 are unclear).

### 2.3 Near-misses

There are **59** unflagged permits with text that hits the near-miss words (mostly "townhome", "dwelling unit",
"apartment" and "carriage house"). The registered draw took 30 with seed 20261111. Because only 59 exist,
**I also read the other 29**, so the pool is a full census. The census is the headline. The seeded 30 are
reported too, as the rule wrote them.

| Label | Seeded 30 | All 59 | Example (short) |
|---|---:|---:|---|
| ADU (missed) | 1 | 1 | 2026P04020: "garage with accessory dwelling unit above … single-family dwelling … permitted separately" |
| UNCLEAR | 0 | 2 | "ADDITION OF 'MOTHER-IN-LAW SUITE'" (2020); "EXISTING CARRIAGE HOUSE INTO SINGLE FAMILY DWELLING" (2024) |
| LEGAL | 1 | 1 | 2026P00690: certificate of occupancy, "2 FAMILY - ADU - 2 FAMILY TO SINGLE FAMILY" |
| HOUSE (ADU removed from scope) | 1 | 1 | "NEW SINGLE FAMILY DWELLING … ADU IN BASEMENT REMOVED FROM PROJECT SCOPE" |
| WORK on an existing carriage house | 3 | 8 | "CARRIAGE HOUSE ALTERATION"; "REPAIR CARRIAGE HOUSE" |
| OTHER | 24 | 46 | townhouse rows, apartment buildings, a carriage house turned into a studio |

- **Why 2026P04020 was missed:** its second sentence mentions an "existing or proposed single-family
  dwelling", and the shared parser's "existing" veto reads across the sentence break. The first sentence
  alone parses as a detached ADU. The adapter then files the permit as an SFD (1 unit) from its use group, so
  it adds a house that is really being permitted separately (2026P02405).
- The legalization (2026P00690) is not flagged, which is right under Ben's rule.

### 2.4 Recall and k_parser

| Reading | Recall | 90% Wilson | k_parser = 1 / recall | 90% range of k |
|---|---:|---:|---:|---:|
| **Central** (census; unclear permits as not-ADU) | **15 / 16 = 0.94** | 0.76–0.99 | **1.07** | 1.01–1.31 |
| Range end: both unclear near-misses are ADUs | 15 / 18 = 0.83 | 0.65–0.93 | 1.20 | 1.07–1.54 |
| Range end: both unclear flagged permits are ADUs | 17 / 18 = 0.94 | 0.79–0.99 | 1.06 | 1.01–1.27 |
| Registered seeded 30 only (1 miss in 30 of 59, scaled ×59/30) | 15 / 17.0 = 0.88 | | 1.13 | |

**Under the rule in §1, k_parser = 1.07 (90% range 1.01–1.54).** The range runs from the lowest to the
highest Wilson bound across the readings.

**Precision is the bigger problem.** k only corrects for misses (D-078). Twelve of the 29 flagged permits
are not new ADUs, and 11 of those are in 2020. Scaling every year by one number can't fix errors that sit in
a single year. The counts need the 12 permits removed at the source (see §4). Until then, Cincinnati's 2020
count is about 11 too high.

## 3. Cleveland (`cle_permits`): confirmation

Cleveland uses its own rule (`cle_permits.adu_from_text`), not the shared parser, which is why #376 and #380
did not change it. Its text covers all 79,906 downloaded permits.

### 3.1 Flagged permits: all 15 read

| Label | Permits | Example (short) |
|---|---:|---|
| ADU | 7 | "GARAGE W/ IN-LAW SUITE ABOVE"; "REAR … IN-LAW SUITE CARRIAGE HOUSE" |
| HOUSE+ADU | 8 | "SINGLE FAM RES W/ DET GARAGE AND IN-LAW SUITE ABOVE" |
| LEGAL, OTHER, UNCLEAR | 0 | |

- **Precision: 15 / 15** (90% Wilson 0.85–1.00).
- All 8 HOUSE+ADU permits are already stored as one SFD plus an `adu_type`, which is what Ben's rule asks for.
- Nearly all cite a BOZA approval.

### 3.2 Near-misses

- **Registered draw: 30 of 1,312, seed 20261111.** The words in §1 are broad. In Cleveland, "suite" and
  "apartment" mostly hit office suites and apartment buildings. **0 ADUs** among the 30: office suites,
  apartment repairs and new apartment buildings. One permit adds a basement apartment to an `R-3` building
  that has a sprinkler system, which makes it a multi-unit building, not an ADU.
- **Added after the registered draw: a residential-only net.** Use group One Family, Two Family, Accessory
  Use, "PLEASE CHANGE" or blank: 74 permits, 30 drawn with seed 20261112. **0 ADUs**: owner and master suites,
  townhouse rows, adult family homes, demolitions, and attic space added to an existing unit.
- The one possible miss from the earlier check ("finishing the 2nd floor loft apartment", 2025;
  `reports/oh/adu-coverage-and-undercount.md` §3.3) was not drawn again. It stays as the only possible miss.

### 3.3 Recall and k_parser

| Reading | Recall | 90% Wilson | k_parser | 90% range of k |
|---|---:|---:|---:|---:|
| This check alone (0 misses in 60 read) | 15 / 15 = 1.00 | 0.85–1.00 | 1.00 | 1.00–1.18 |
| With the earlier possible miss as an ADU | 15 / 16 = 0.94 | 0.76–0.99 | 1.07 | 1.01–1.31 |

The current row, **1.07, stands as the centre.** Its range of 1.0–1.07 was not a Wilson interval. The honest
90% range, across both readings, is **1.00–1.31**. With only 15 matches, the interval is wide whatever the
point estimate.

## 4. What this does not settle (follow-ups, not done here)

- **Cincinnati adapter fixes** are needed before the refit counts Cincinnati at face value:
  - drop the 2020 development carriage houses (for example, carriage-house text on a parcel that also has
    `R-2` permits in the same batch, or "masterplan" in the text);
  - catch "NOT A DWELLING UNIT/ADU" as a negation;
  - stop the "existing" veto reading across sentences, and don't add an SFD for a permit whose text says the
    house is permitted separately.
  - Each is a parser or adapter change with tests. No code was changed here.
- **Cincinnati's download net** misses ADUs described without the six words. Widening `COMBO_WORDS` would need
  a new fetch (Ben's call).
- **The Cleveland near-miss words** should be narrowed to residential use groups in any later check. The
  broad set mostly reads office suites.

## 5. Proposed undercount-table rows

Not written to `config/params/adu.yaml`; for Ben to accept. `kind: parser`, `interval: 0.90`.

| source | place | k | 90% range | citation |
|---|---|---:|---|---|
| `cincy_permits` | Cincinnati (OH) | **1.07** | 1.01–1.54 | `reports/oh/parser-handcheck-2026-11-11.md` §2.4: recall 15/16 within the combo-text download net (59 near-misses read, all of them); the range covers 4 unclear permits. **Precision 15/29: use only after the 12 false positives are removed (§4).** Recall is an upper bound, because the download net reaches only 6 ADU words |
| `cle_permits` | Cleveland (OH) | **1.07** | 1.00–1.31 | `reports/oh/parser-handcheck-2026-11-11.md` §3.3 (confirmation): precision 15/15, 0 misses in 60 more near-misses read; the centre keeps the 2026-11-10 possible miss (`reports/oh/adu-coverage-and-undercount.md` §3.3); range from the 90% Wilson bounds on 15/15 and 15/16 |

*Hand judgments by Claude Code (Opus 5.5) on 2026-11-11. Each label was read from the work description,
against the rule committed first (commit `e86abafa`). Scripts were throwaway, kept in the session scratchpad;
the seeds and nets above are enough to redraw the same samples from the 2026-11-11 raw snapshots.*
