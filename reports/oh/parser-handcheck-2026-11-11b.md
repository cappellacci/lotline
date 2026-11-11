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
