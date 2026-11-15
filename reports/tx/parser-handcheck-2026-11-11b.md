# Fort Worth and Dallas: parser hand check after the second parser round, 2026-11-11b

**What:** fresh hand checks of the shared ADU parser on `fw_permits` (Fort Worth) and `dallas_permits` (Dallas)
after the second parser round (#389) and the offline rebuild (#391). Method: the #385 protocol with new seeds,
scored as D-081 says (k = precision ÷ recall, with intervals by simulation). The rule and the draw (§1–2) were
committed in `a2fca77a` at 16:00 on 2026-11-11, before any sampled description was read. No engine, scenario,
fit or dev-run script was run, nothing was downloaded, and `--unblind` was not used.

**Headline.**

| Source | Flagged | Precision (90%) | Recall (90%) | **k = precision ÷ recall (90%)** | 1 / recall |
|---|---:|---:|---:|---:|---:|
| Fort Worth, all years | 115 | 0.77 (0.63–0.87) | 0.70 (0.51–0.86) | **1.09 (0.85–1.47)** | 1.42 |
| Fort Worth, 2015–2026 | 64 | 0.93 (14/15) | 0.82 (0.57–0.95) | **1.14 (0.92–1.60)** | 1.22 |
| Dallas (census) | 5 | 1.00 (5/5) | 0.83 (5 of 6; 0.51–0.97) | **not proposed: 6 true ADUs** | |

- **Fort Worth is no longer a low-recall source under D-081's kitchen rule.** In #385 its k was 2.49. Two
  things changed. #389 now reads the names #385 listed ("GARAGE APT", "living quarters", "second dwelling").
  And under D-081 item 2, in-law suites with no kitchen named are no longer counted as ADUs, so the parser no
  longer "misses" them.
- **The kitchen rule removes real separate units in Fort Worth.** Its 2015–2026 drop (94 → 64) is almost all
  purpose-built in-law suites. 43 of the 51 kitchen-rule drops are detached, garage or accessory-building
  suites (38 of the 44 dropped from 2015 on). They are not ADUs by the D-081 rule. But Fort Worth bars separate
  kitchen service in "detached habitable accessory" units (#385 §2), so this is the form its ADUs take. With
  them counted, Fort Worth's 2015–2026 total is about 115 rather than 73. This is the biggest open choice for
  Fort Worth (§4).
- **Dallas:** the five flagged permits are all real, and the parser now finds 5 of the 6 true ADUs. Six is
  below the 10 the rule set (§2), so no k is proposed, and **Dallas stays out of the fit** (D-081 item 4).
- The new "GARAGE APT" names bring in repairs: 4 of the 16 newly flagged permits in the sample are siding,
  stairs or bricking work on an existing garage apartment (§5).
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

**Two notes on the draw, written after it ran.** The flagged and near-miss draws hold 15 permits from 2015 on
and 15 from before, by chance. The 2015–2026 rows below are domain estimates from those halves. The near-miss
word list was rebuilt from #385's §1 text, which gives a flagged-plus-pool total of 530 permits against #385's
517. So the list is close to #385's but not identical.

## 3. Fort Worth (`fw_permits`)

### 3.1 Labels

| Label | Flagged sample (30 of 115) | Kitchen-rule drops (all 51) | Other near-misses (30 of 364) |
|---|---:|---:|---:|
| NEW_ADU | **23** (5 of them "living quarters") | 1 | **3** (2 "living quarters") |
| INLAW_NK_UNIT | 1 | **43** | 0 |
| INLAW_NK_ROOM | 0 | 2 | 0 |
| LEGALIZE | 0 | 1 | 3 |
| REPERMIT | 1 | 2 | 0 |
| SFD_WITH_ADU | 0 | 1 | 0 |
| CONTEXT | 4 | 1 | 10 |
| NOT_ADU | 0 | 0 | 9 (6 D.R. Horton "Casita Master" build-to-rent permits) |
| UNCLEAR | 1 | 0 | 5 ("guest house" with no living words) |

Three re-permit cases were checked against the table after labelling. "RE-PERMITTING PB09-04952" (flagged)
cites a permit that is itself flagged, so it is a double count. Two 2024 and 2025 permits both read "300 SQ FT
IN LAW SUITE PREVIOUS PERMIT PB22-07979", and the cited 2022 permit is in the kitchen-drop census too. Under
the no-kitchen reading they would count that one suite three times.

### 3.2 Estimates

True ADUs ≈ p_f × 115 + c + p_r × 364. k = true ÷ 115. Intervals are 5th–95th percentiles of 200,000 draws.

| Case | Precision | Recall | **k = precision ÷ recall** | 1 / recall |
|---|---:|---:|---:|---:|
| **Central (D-081 rule)** | 0.77 (0.63–0.87) | 0.70 (0.51–0.86) | **1.09 (0.85–1.47)** | 1.42 (1.16–1.95) |
| "Living quarters" as UNCLEAR | 0.60 | 0.84 (0.59–0.96) | 0.71 (0.55–1.03) | 1.19 |
| UNCLEAR counted as ADU | 0.80 | 0.48 (0.37–0.62) | 1.65 (1.26–2.11) | 2.07 |
| No-kitchen suites (UNIT) counted, central parser | 0.80 | 0.53 (0.42–0.62) | 1.50 (1.26–1.88) | 1.87 |
| No-kitchen suites (UNIT + ROOM) counted, central parser | 0.80 | 0.53 (0.41–0.61) | 1.52 (1.27–1.89) | 1.90 |

By period, central case and no-kitchen (UNIT) case:

| Period | Flagged | Precision | Recall | k (central) | k, no-kitchen suites counted |
|---|---:|---:|---:|---:|---:|
| 2015–2026 | 64 | 0.93 (14/15) | 0.82 (0.57–0.95) | **1.14 (0.92–1.60)** | 1.80 (1.60–2.25) |
| Before 2015 | 51 | 0.60 (9/15) | 0.56 (0.32–0.81) | 1.08 (0.68–1.77) | 1.17 (0.78–1.87) |

Before 2015, precision is low. Four of its six non-ADU flags in the sample are new "GARAGE APT" names on repair
permits (§5). From 2015 on, precision is high.

## 4. The no-kitchen sensitivity and Fort Worth's 2015–2026 drop

**Is the kitchen rule removing real ADUs?** The 51 permits it drops were judged in full:

| Label | 2015–2026 (44) | Before 2015 (7) |
|---|---:|---:|
| INLAW_NK_UNIT: detached, garage or accessory-building suite, or with its own bedroom and bath | **38** | 5 |
| INLAW_NK_ROOM: attached addition or a room | 1 | 1 |
| NEW_ADU (a kitchen is named, so the parser dropped it wrongly) | 1 | 0 |
| LEGALIZE / REPERMIT / SFD_WITH_ADU | 4 | 0 |
| CONTEXT | 0 | 1 |

- **Almost every drop is a separate unit in substance.** Most are permits typed "Residential Accessory
  Struct | New | Accessory Dwelling" that say only "MOTHER IN LAW SUITE", "600 SQ FT IN LAW SUITE" or "NEW
  DETACHED MOTHER-IN-LAW SUITE (817 SQ FT)". Several say "no kitchen" or "no stove" outright: "HABITABLE
  ACCESSORY (MOTHER IN LAW SUITE) WITHOUT KITCHEN" and "new garage + mother in law suite (no stove)". Fort
  Worth's code bars separate service to these units, and its one-family districts allow accessory dwellings
  only when they are not rented (TX-4827000-adu-2010). So a Fort Worth "ADU" usually has no kitchen.
- **Under D-081 item 2 these suites are not ADUs, and the drop is correct by that rule.** A fit from 2015 on
  sees Fort Worth's ADU count fall by a third because of how the rule is defined, not because of a parser
  error. The parser does what the rule says: in the central case, precision on 2015–2026 flags is 0.93, and the
  dropped suites were judged not-ADU under the same rule.
- **The no-kitchen sensitivity** is the parser run with `in_law_suite_needs_kitchen=False` (#391: 166 flagged).
  Counting these suites as true ADUs, the 166 flags have precision 0.82 (0.72–0.89), recall 0.79 (0.63–0.91) and
  **k = 1.04 (0.87–1.30)**. For 2015–2026 the figure is **1.07 (0.95–1.33)** on 108 flags. Taking the central
  count (115) with no-kitchen suites counted as true gives k = 1.50, or 1.80 for 2015–2026.
- **The choice for Ben:** Fort Worth is the one source where the kitchen rule changes the substance. The
  options are (a) to keep D-081 item 2 and carry the no-kitchen count (166, k 1.04) as Fort Worth's named
  sensitivity in the refit's uncertainty, or (b) to make a Fort Worth exception that counts accessory-structure
  in-law suites, because the city bars the kitchen. This report proposes (a), which follows the rule as
  decided.
- **Units side:** 6 of the 51 dropped permits (5 of the 43 separate suites) are typed "Residential Building
  Permit | New | Single Family Residence" and carry 1 new SFD unit. Under the central rule those suites count
  as new houses, which is not consistent with treating them as "not a dwelling unit". PB16-09120 (typed SFD,
  1 unit) and PB16-14342 (accessory structure) have the same text in the same year ("construct a mother in
  law quarters on property") and may be one suite filed twice.

## 5. What the parser still gets wrong (follow-up, not done here)

1. **"GARAGE APT" on repair permits.** It fires on "RES-BRICKING HOUSE & GARAGE APT", "EB//RES GARAGE APT IN
   REAR /SIDING AND WINDOW", "REPLACE STAIRS TO GARAGE APT AND SIDING AS NEEDED" and "MLH/RES/REMODEL GARAGE APT
   AND CONVERT TO LIVING AREA". All four are "Residential Building Permit | Remodel", mostly before 2015.
   Precision in the sample is 10/16 for newly flagged permits and 13/14 for permits flagged before #389. Two
   fixes would work: `fw_permits.classify` could require conversion or new-build words when the subtype is
   Remodel, or the parser's repair-word veto could add siding, bricking and stairs.
2. **"KITCHEN NO OVEN" reads as no kitchen.** "DETACHED MOTHER IN LAW SUITE TO INCLUDE BED/BATH AND KITCHEN NO
   OVEN" is dropped by the kitchen rule, though it names a kitchen.
3. **Re-permits are flagged.** "RE-PERMITTING PB09-04952" counts a unit whose first permit is already
   flagged.
4. **Still missed:** "NEW LIVING QUARTER LOCATED BEHIND HOUSE" (singular, no "detached"), "NEW LIVING QUARTERS/
   NO KITCHEN", and "CHANGE FROM STORAGE BLDG TO GUEST HOUSE … CONVERTED TO LIVING AREA". Two of the three
   already carry 1 SFD unit in the table.

## 6. Dallas (`dallas_permits`), census

| Label | Flagged (all 5) | Near-misses (all 14) |
|---|---:|---:|
| NEW_ADU | **5** | **1** |
| SFD_WITH_ADU | 0 | 1 ("NEW SFD W/DETACHED GARAGES AND 2 STORY DETACHED GUEST QUARTERS") |
| CONTEXT | 0 | 5 (2 "cannot be used as a 2nd dwelling", the #380 shed among them) |
| NOT_ADU | 0 | 1 (a guest suite inside the house) |
| UNCLEAR | 0 | 6 ("guest house" with no living words) |

- **Precision 5/5.** The flagged permits are "ADU APPROVED BY BOA", "400SF ACCESSORY DWELLING UNIT(BDA…)", "2ND
  DWELLING UNIT", "CONSTRUCT DETACHED GARAGE WITH SECOND DWELLING" and "Finish work on revoked permit … 2nd
  dwelling approved by bda". The revoked permit it cites is not in the table or the raw pages, so this is the
  unit's only record and not a double count.
- **Recall 5 of 6 (0.83; Jeffreys 90% 0.51–0.97); k within the census = 6 ÷ 5 = 1.20**, or 2.40 if every
  bare "guest house" is an ADU. The one miss is "ADDITION PORCH/GARAGE/2ND DWELLING UNIT" on a two-family land
  use, which the adapter skips by design.
- **Not proposed as a k.** Six true ADUs from 1999 to 2024 is below the pre-set threshold of 10. The figure is
  reported as a fact, and Dallas stays out of the fit (D-081 item 4). If Ben wants Dallas in, a floor entry
  (count only, `floor: true`) is the option that does not need a k.

## 7. Limits

- One judge (Claude Code), with no second coder. The "living quarters" and UNCLEAR sensitivities move Fort
  Worth's k from 0.71 to 1.65. The INLAW_NK_UNIT / ROOM split used the permit type as evidence, since an
  "Accessory Struct | New" permit was read as a separate building.
- Recall is measured only within the word-defined pool. A real ADU filed with none of the words lowers recall
  further, so k is a lower bound.
- The 2015–2026 split rests on 15 + 15 sampled permits plus the census. Its intervals are wide.
- The simulation uses Jeffreys Beta draws for each sampled stratum, not Wilson-matched Betas (D-081 item 1
  names Wilson intervals). At these sample sizes the two agree to about ±0.01 on precision.

## Proposed undercount-table rows

For `adu_flag_undercount` in `config/params/adu.yaml`. Proposed only; that file is not edited here.

| Source | k (precision ÷ recall) | 90% range | Citation / notes |
|---|---:|---|---|
| `fw_permits` (Fort Worth) | **1.14** | **0.92–1.60** | This report §3.2, the 2015–2026 window the refit uses. Precision 14/15, recall 0.82, from 30 flagged + 30 near-miss permits + a census of all 51 kitchen-rule drops, seeds 2026111102–05, rule in §2 (committed `a2fca77a`). All years: 1.09 (0.85–1.47). **Named sensitivity:** no-kitchen count (`in_law_suite_needs_kitchen=False`, 108 flags for 2015–2026) with k 1.07 (0.95–1.33). No longer a low-recall row. |
| `dallas_permits` (Dallas) | **none** | (census k 1.20; 2.40 with guest houses) | This report §6. 6 true ADUs in a census of 5 flagged + 14 near-misses, below the threshold of 10. Stays out of the fit (D-081 item 4), or enters as a floor source if Ben prefers. |

## How this was made

Claude Code wrote throwaway scripts in its scratch folder, outside the repo. The scripts read the cached
2026-11-11 raw pages from disk and re-ran each adapter's `build()` in memory three ways: with today's parser,
with the no-kitchen switch, and with the pre-#389 parser (`96866008`) to tell the new flags from the old ones.
They kept only `permit_id`s present in the holdout-filtered processed tables and checked that the flag sets
match those tables exactly. Then they built the pools and drew the seeded samples. Phone numbers and e-mails were
scrubbed from descriptions in memory, and no description was stored. Claude Code committed the rule before
printing the shuffled sheet, then labelled all 130 permits by hand without seeing their flag or stratum. It
looked up the cited permits after labelling and computed the estimates with numpy. No data was written to the
repo, the data dir or the manifest. Labels (permit ids and labels only, no text) and the scripts are in the
side-session notes folder.
