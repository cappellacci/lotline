# Wake County: second homes added to single-family lots, Nov 2019 → Dec 2023 roll

*WS-NC data thread, 2026-11-10. Descriptive counts only; no engine, scenario or calibration run.*

## 1. Detection rule (written and committed before any count)

### What the roll records

The two pre-revaluation rolls (`Real_Est_Data_Final_Nov2019.xlsx`, vintage 2019-11-30, and
`Real_Est_Data_Final_Dec2023.xlsx`, vintage 2023-12-31) have one row per **card**. A card is one building the
assessor values as a structure with its own Type & Use, units, heated area and year built. Garages, sheds and
other outbuildings are **not** cards: the extract has no outbuilding table. So the roll can show a second home
in only three ways:

1. **A new dwelling card**: the parcel gains a card whose Type & Use is residential (01 one family, 02 two
   family, 03/04 three/four family, 72 mobile home) with heated area above 0. This is how a detached ADU (a
   backyard cottage, a converted garage apartment that the assessor now lists as a building) appears.
2. **A unit or use change on an existing card**: units on a dwelling card go from 1 to 2 or more, or Type &
   Use goes from 01 (one family) to 02 (two family), with the main building's year built unchanged. This is
   how an attached or internal ADU *could* appear if the assessor recorded it as a unit.
3. **Added heated area** with a `Year_of_Addition` in 2019–2023. This is every addition, of which an attached
   ADU is a small part. **The roll cannot tell an attached ADU from a bedroom addition**, so this signal is
   reported only as an outer envelope and never counted as ADUs.

How the rule was learned: before writing it, Claude looked at the 26 Raleigh ADU-flagged permits issued
2019–2021 in both rolls (to see how a known ADU is carded). Detached ADUs that were built show up as signal 1;
the attached and internal ones show up only as signal 3. Raleigh permits issued in **2022–2023 were not
looked at** before this rule was committed, so the undercount check is reported for that cohort separately.

### Matching parcels across rolls

- **Key: `REAL_ESTATE_ID` (REID).** It is the county's account number and stays with the parcel; a parcel's
  PIN (`Parcel_Identification`) can be reissued after a re-map. Each REID has exactly one PIN in each roll.
  Only REIDs present in both rolls are compared.
- **Splits.** A split keeps the parent REID and gives the new lots new REIDs. New REIDs are not in the 2019
  roll, so new subdivision lots are never counted. The parent is compared as usual.
- **Merges (combinations).** A REID that absorbs a neighbour can gain the neighbour's house as a second card.
  A parcel whose deeded acreage grew by more than 20% is set aside as a **possible merge** and not counted.
- **PIN for the Raleigh permit match.** Raleigh's permits carry a 10-digit PIN. The roll's
  `Parcel_Identification` (`1714.09 05 9993 000`) becomes `1714059993` (map, block, lot; the `.09` sheet scale
  and the `000` suffix dropped).

### Denominator: single-family parcels in 2019

A 2019 parcel is in the denominator when, in the **2019 roll**:
- its land use (the adapter's own rule, `wake_realestate.build`: Type & Use + Design Style on card 01, then
  Land Class) is `SF_DETACHED`, so townhouses, condominium units, duplexes and manufactured homes on card 01
  are out; and
- it has **exactly one dwelling card**, and that card has 1 unit (a lot that already had two homes in 2019 is
  out).

Jurisdiction is the 2019 roll's `CITY` (2019 city limits), mapped with the adapter's crosswalk; outside city
limits is unincorporated Wake (37183). The adapter drops the few Wake parcels of Durham, Angier and Clayton,
and so does this count.

### Numerator: parcels that gained a second home

A denominator parcel **gained a second home** when, in the 2023 roll, it is the same REID and:
- **Signal 1:** it has two or more dwelling cards; or
- **Signal 2:** its dwelling units add up to 2 or more, or card 01's Type & Use became 02, while card 01's year
  built is unchanged.

Then the parcel is sorted into exactly one group:

| Group | Test | In the headline count? |
|---|---|---|
| **New card, built 2019 or later** | Signal 1, the newest added dwelling card has year built 2019–2023 | **Yes** |
| New card, older building | Signal 1, added card's year built before 2019 (an existing outbuilding converted or newly carded, or a building the assessor found) | Yes; shown separately |
| Unit or use change | Signal 2 only | Yes; shown separately (internal/attached ADU or duplex conversion; the roll can't tell which) |
| Teardown and rebuild | Card 01's year built moved to 2019 or later (the main house was replaced) and the lot now has 2 homes | Yes; shown separately (a real second home, but built with a new house, not added to an existing one) |
| Possible merge | Acreage grew by more than 20% | **No** |

The headline count is all "Yes" groups. The **strict count** is the first group alone (a new building added to
a lot whose main house stayed). Both are reported.

### False positives and how each is handled

| Case | Handling |
|---|---|
| New subdivision lot | Not in the 2019 roll (new REID): never counted |
| Townhouse or condominium | Card 01 styled townhouse/condo/duplex is not `SF_DETACHED`: out of the denominator |
| Teardown and rebuild with one house | Still one dwelling card: not counted |
| Teardown and rebuild with a house and an ADU | Counted in its own group (a second home was gained) |
| Merge that brings in a neighbour's house | Acreage test: set aside, not counted |
| Card renumbering | Counts compare the number of dwelling cards, not card numbers |
| Old structure newly carded (found by the assessor, not built) | Its own group ("older building"); a strict count without it is reported |
| Duplex conversion (missing middle, not an ADU) | Can't be told from an internal ADU; signal 2 is its own group |
| Second home on a vacant 2019 lot (new house + ADU built together) | Not in the denominator (vacant in 2019); counted separately for the record, not in the rate |

### Rate

Rate per 1,000 single-family parcels a year = parcels that gained a second home ÷ 2019 single-family parcels
× 1,000 ÷ **4.08 years** (2019-11-30 to 2023-12-31). Uncertainty is shown as a 95% Wilson interval on the
proportion, plus the strict-to-headline range.

### Raleigh undercount check

- Raleigh's ADU-flagged permits (`adu_type` set) issued 2019-01-01 to 2023-12-31 are matched to roll parcels by
  PIN → REID. Lag: a permit issued less than about a year before the Dec 2023 roll may not be built or carded
  yet, so the main comparison uses permits issued **through 2022-12-31**; permits issued in 2023 are shown
  separately.
- Roll side: Raleigh denominator parcels flagged by the headline rule.
- Three numbers: **in both**, **roll only**, **permits only**. A flagged permit on a parcel outside the
  denominator (vacant or not single-family in 2019) is listed apart, not as "permits only".
- Ratio of real ADUs to flagged permits: (both + roll only + permits only) ÷ flagged permits, which counts each
  source's finds once, and a Chapman (Lincoln–Petersen) estimate of the total that neither source sees, with its
  95% interval. The two sources are not independent (a permitted ADU is more likely to be carded), so the
  capture–recapture total is a lower bound on the true total.

---

## 2. Results

*Rule committed in 56330e7 before the first count. Counts from `uv run python
scripts/dev/nc_wake_roll_adu_diff.py` (aggregates in `reports/nc/wake-roll-adu-diff.json`; no parcel-level
table is written). Function and tests: `src/lotline/adapters/states/nc/wake_roll_diff.py`,
`tests/states/nc/test_wake_roll_diff.py`.*

### Bottom line

- **The roll sees very few second homes added to Wake's single-family lots: 88 of 256,532 over 4.08 years,
  about 0.08 per 1,000 lots a year** (95% interval 0.07–0.10). The strict count, a new building added next to
  a house that stayed, is 47 (0.045). Raleigh (48) and unincorporated Wake (32) hold 91% of them; the eleven
  other towns together have 8.
- **In Raleigh, about 73% of the ADUs the assessor had carded by Dec 2023 carry an ADU-flagged permit**
  (32 of 44; 95% interval 58–84%). So there are about **1.4 real ADUs per flagged one (1.2–1.7)**. A
  capture–recapture estimate that also counts flagged ADUs the roll hasn't carded gives the same ratio,
  **1.37 (1.20–1.54)**. These are lower bounds (see caveats).
- **The roll undercounts too, and by more than the flags:** about half of Raleigh's flagged permits issued
  2019–2022 (31 of 63) show no second home on the Dec 2023 roll. A roll count elsewhere in Wake is therefore a
  floor, not a measure. The roll can't replace the permit flags; it is a check on them.

### 2.1 By jurisdiction

Single-family parcels on the Nov 2019 roll that are still on the Dec 2023 roll (2019 city limits). "Gained" is
the headline count (all counted groups); the strict count is "new card, built 2019 or later". Rates are per
1,000 single-family parcels a year over 4.08 years; the interval is a 95% Wilson interval on the headline.

| Jurisdiction | SF parcels 2019 | Gained | New card ≥2019 (strict) | New card, older bldg | Unit/use change | Rebuild, 2 homes | Merge (not counted) | Rate | 95% interval | Strict rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| Raleigh | 85,376 | 48 | 29 | 5 | 3 | 11 | 0 | 0.14 | 0.10–0.18 | 0.08 |
| Cary | 37,797 | 1 | 0 | 0 | 1 | 0 | 1 | 0.01 | 0.00–0.04 | 0 |
| Apex | 14,488 | 2 | 2 | 0 | 0 | 0 | 0 | 0.03 | 0.01–0.12 | 0.03 |
| Wake Forest | 11,515 | 2 | 0 | 0 | 1 | 1 | 0 | 0.04 | 0.01–0.15 | 0 |
| Fuquay-Varina | 10,258 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0–0.09 | 0 |
| Holly Springs | 10,645 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0–0.09 | 0 |
| Garner | 8,429 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0–0.11 | 0 |
| Morrisville | 3,828 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0–0.25 | 0 |
| Knightdale | 4,744 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0–0.20 | 0 |
| Wendell | 3,034 | 1 | 0 | 0 | 1 | 0 | 0 | 0.08 | 0.01–0.46 | 0 |
| Zebulon | 1,814 | 2 | 0 | 0 | 0 | 2 | 0 | 0.27 | 0.07–0.98 | 0 |
| Rolesville | 2,664 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0–0.35 | 0 |
| Unincorporated Wake | 61,940 | 32 | 16 | 8 | 3 | 5 | 2 | 0.13 | 0.09–0.18 | 0.06 |
| **Wake County** | **256,532** | **88** | **47** | **13** | **9** | **19** | **4** | **0.08** | **0.07–0.10** | **0.045** |

- **Denominator.** 256,899 single-family parcels on the 2019 roll; 367 (0.14%) are gone by 2023 (merged, split
  into new REIDs or retired) and are not compared.
- **When the strict cards were built:** 2019: 6, 2020: 6, 2021: 5, 2022: 18, 2023: 12. The rise in 2022–23
  matches Raleigh's flagged permits (23 in 2021, 55 in 2022).
- **Not in the rate:** 8 parcels vacant in 2019 now have two homes (likely a house and an ADU built together), and 38,362
  REIDs on the 2023 roll are new (mostly new lots).
- **Zeros are not proof of no ADUs.** In Raleigh, the roll showed only half of the flagged ADUs (§2.2), so a
  town's real count may be about twice its roll count. Outside Raleigh there is
  no permit file in this repo to check against (sibling sessions are looking at Cary).
- **Unincorporated Wake** is mostly rural: many of its gains are a second house or a mobile home on a large lot
  (5 of its 32 are teardowns with two homes, 8 are older buildings newly carded), not backyard cottages.

### 2.2 Raleigh undercount check

Raleigh's ADU-flagged permits (`adu_type` set) issued 2019–2022, matched by 10-digit PIN to Raleigh's 2019
single-family parcels. Permits issued in 2023 are left out of the main comparison (too recent to be built and
carded by the Dec 2023 roll: only 4 of 41 were).

**As committed (rule §1 unchanged):**

| | Count |
|---|---:|
| Flagged permits issued 2019–2022 | 81 (81 parcels) |
| …on a parcel outside the denominator (vacant, duplex or not single-family in 2019) | 23 |
| …on a 2019 single-family parcel (the flagged set) | 58 |
| Roll: Raleigh parcels that gained a second home | 48 |
| **In both** | **27** |
| **Roll only** | **21** |
| **Permits only** | **31** |

**ADU-only adjustment (deviation, 2026-11-10, made after the first count; both versions are reported).**
Looking at the 21 roll-only parcels showed two things the committed rule did not anticipate:
- **4 are duplexes, not ADUs**: each has a Raleigh duplex permit (code 103, two units) issued 2018–2023, and
  most are teardowns rebuilt as two homes. They leave the roll set.
- **5 carry an ADU flag issued outside 2019–2022** (4 in 2023, one in another year): they are flagged ADUs, so
  they join the flagged set.

| | As committed | ADU-only |
|---|---:|---:|
| Roll set | 48 | 44 |
| Flagged set | 58 | 63 |
| **In both** | **27** | **32** |
| **Roll only** | **21** | **12** |
| **Permits only** | **31** | **31** |
| Share of roll finds that carry a flag (95% Wilson) | 56% (42–69%) | **73% (58–84%)** |
| Real ADUs per flagged ADU (inverse of the share) | 1.78 (1.44–2.37) | **1.38 (1.20–1.72)** |
| All seen ÷ flagged ((both + roll only + permits only) ÷ flagged) | 1.36 | 1.19 |
| Chapman total ÷ flagged (95%) | 1.76 (1.46–2.07) | **1.37 (1.20–1.54)** |
| Roll ÷ flagged | 0.83 | 0.70 |

**Reading the ratio.** The headline is **about 1.4 real ADUs per flagged permit in Raleigh (1.2 to 1.7)**, from
the ADU-only column. Without the duplex adjustment it would be 1.8; that is the upper end, and the adjustment is
the better reading, since a two-unit permit is a duplex by Raleigh's own code.

**What the 12 roll-only ADUs had.** 7 had a Raleigh permit issued 2018–2023 with no ADU flag: two "New
Residential Dwelling" permits coded single-family (101), two accessory structures, a change of use, an addition
and an alteration. The other 5 had no permit in those years. So most unflagged ADUs did go through the permit
office, coded as something else; a few may be unpermitted or permitted before 2018.

**Why 31 flagged permits show no second home.** Of these, 30 still have one dwelling card in 2023, and 8 added
more than 200 sq ft of heated area to the main card (an attached ADU, or a detached one folded into the main
card). The rest show no change: the ADU wasn't finished, the permit was dropped, or the assessor hadn't carded
it yet. The flagged permits issued 2019–2021 (the ones the rule was learned on) were found less often (6 of 21)
than those issued in 2022 (21 of 37), which points to unbuilt or abandoned permits and assessor practice, not
only lag. None of the 7 attached and internal ADUs among the 2019–2022 flags is on the roll, as §1 expected: **the roll
cannot see attached or internal ADUs**.

### 2.3 Caveats

1. **Detached ADUs only.** The ratio is measured on ADUs the assessor carded as their own building. Attached
   and internal ADUs (9% of Raleigh's 2019–2022 flags) can't be seen on the roll, so their undercount is unknown.
2. **Lower bound.** Capture–recapture assumes the two sources are independent. They aren't: a permitted ADU is
   more likely to be carded. Positive dependence biases the Chapman total down, so the true ratio is likely
   higher than 1.37.
3. **Roll-only may hold non-ADUs.** A second house on a large lot, a guest house or a carriage house the
   assessor carded counts as a second home here. Raleigh's lots are small enough that most will be ADUs, but this
   wasn't checked case by case.
4. **Small counts.** 32 matches and 12 roll-only. One case moves the ratio by about 0.04.
5. **One city.** The ratio is Raleigh's. Its flags are maintained by its permit staff; other places' flags
   (Durham's) or parsers (Greensboro's, Mecklenburg's) may undercount by different amounts.
6. **The adjustment came after looking.** The duplex and other-year rules were added after the first count, on
   the cases they change. Both versions are reported so the effect is visible (1.78 → 1.38).
7. **Rule learned on 2019–2021 cases.** The rule was written after looking at 26 flags issued 2019–2021. The 2022
   cohort (37 flags) was not looked at first; its match rate (21 of 37, 57%) is higher than the learned-on
   cohort's (6 of 21), so the rule was not tuned to fit.

### 2.4 What this means for the NC ADU rate

- Raleigh's flagged-permit ADU count is an undercount of about **1.4× (1.2–1.7×)** for detached ADUs; the true
  factor for all ADUs is at least that.
- Raleigh's rates per 1,000 single-family lots a year over the window: roll 0.13, flagged permits 0.18,
  capture–recapture total 0.25. (The capture–recapture population spans permits issued 2019–2022 and cards to
  Dec 2023, so this is a rough rate.)
- The roll comparison adds no new places to the panel: outside Raleigh and the rural county it finds almost
  nothing, and it detects only about half of the ADUs where we can check. It is useful as a correction factor
  for the flags, not as a second outcome series.
