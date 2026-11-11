# Fort Worth and Dallas: parser hand check after the second parser round, 2026-11-11b

*Draft. This commit fixes the judging rule and the draw (§1–2) before any sampled description is read.
Results follow in a later commit.*

## 1. Pools and draw (fixed before reading)

Tables: the offline rebuild of 2026-11-11b (#391) on `a54f34d9`. Each adapter's `build()` was re-run in memory
on the cached 2026-11-11 raw pages, once with the parser as is and once with
`parse_description(..., in_law_suite_needs_kitchen=False)`. The central run reproduces the processed tables
exactly (Fort Worth 115 ADUs, Dallas 5) and the no-kitchen run gives 166 and 5, as in #391.

The near-miss pool uses the same word list as #385 (§1 of `reports/tx/parser-handcheck-2026-11-11.md`).

| Source | Flagged | Near-miss pool | of which kitchen-rule drops | Draw |
|---|---:|---:|---:|---|
| Fort Worth | 115 | 415 | 51 (all 51 are in the near-miss pool) | 30 flagged; **all 51 kitchen-rule drops**; 30 of the other 364 near-misses |
| Dallas | 5 | 14 | 0 | all 5 flagged and all 14 near-misses (census) |

The Fort Worth near-miss pool is split into two strata: the kitchen-rule drops (flagged with no kitchen
required, not flagged now) are judged in full, because they carry the 2015–2026 question; the other 364
near-misses are sampled. Seed `numpy.random.default_rng(2026111102)`; flagged draw first, then the near-miss
draw, each without replacement. All judged permits go on one sheet in a shuffled order (seed 2026111103)
showing only a row number, filing year, permit type / subtype / use and the description, so each is judged
blind to its flag and stratum.

## 2. The judging rule (fixed before reading)

As in #385 §2, with Ben's two rules for this round:

- **NEW_ADU:** the permit creates a new dwelling unit accessory to a house on the same lot: a new detached
  unit, an addition built as a separate living unit, or a conversion of a garage or accessory building into a
  living unit. Named forms that count when the permit's work is to build or convert them: garage apartment /
  garage apt, ADU, accessory dwelling, second / 2nd dwelling (unit), servant's or additional living quarters,
  "living quarters" in a separate building, guest house *with* living, bed, bath or kitchen words, and an
  in-law / mother-in-law suite or quarters **that names a kitchen** (kitchen, kitchenette, stove, range,
  cooking).
- **INLAW_NK:** an in-law / mother-in-law suite or quarters that names no kitchen, or says "no kitchen / no
  stove". **Not an ADU** in the central case (Ben, this round). Two sub-labels, for the 2015–2026 question
  only:
  - **INLAW_NK_UNIT:** the suite is a separate unit in substance: detached, over or in a garage or accessory
    building, or described with its own bedroom and bath;
  - **INLAW_NK_ROOM:** an attached addition or a room in the house, or too short to tell.
  Both count as ADUs in the no-kitchen sensitivity.
- **LEGALIZE:** the unit already exists and the permit legalizes it ("already built", "without permit",
  "permitting existing", "work has been done"). Not new (D-080).
- **SFD_WITH_ADU:** a new main house that also names an ADU or guest quarters. One SFD, not an ADU.
- **REPERMIT:** a new permit for a unit that already has a flagged permit (cited by number, or the same
  text and site context). Not new.
- **CONTEXT:** the ADU is only context: work on an existing ADU, work on the main house, a structure "not to
  be used as a second dwelling", a demolition or removal.
- **NOT_ADU:** anything else (room additions, a guest suite inside the house, duplexes, build-to-rent
  "casita" cottages).
- **UNCLEAR:** too short to tell, e.g. "guest house" with no living words. Not an ADU in the central case; an
  ADU in a sensitivity.

One reading kept from #385: "living quarters" in a separate building is NEW_ADU; a sensitivity reads those as
UNCLEAR.

**Estimators (D-081).** With p_f = NEW_ADU share of the flagged sample, p_r = NEW_ADU share of the other
near-miss sample and c = NEW_ADU count in the kitchen-drop census:
true ADUs ≈ p_f·N_flagged + c + p_r·N_rest; precision = p_f; recall = p_f·N_flagged ÷ true ADUs;
**k = precision ÷ recall = true ADUs ÷ N_flagged**. 1 / recall is shown beside it. Intervals: 90% percentile
intervals from 200,000 simulated draws (seed 2026111104), with p_f and p_r drawn from their Jeffreys Beta
posteriors; the census stratum carries no sampling error. Dallas is a census, so its precision, recall and k
are exact counts; the recall interval is a Jeffreys interval on found ÷ true. If Dallas has fewer than 10 true
ADUs, recall is reported as a fact and no k is proposed.

**Assumption:** a permit with none of the near-miss words is not an ADU, so recall is an upper bound and k a
lower bound.
