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

*(Filled in after the rule above was committed.)*
