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
