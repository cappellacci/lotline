# Ohio ADUs: coverage of the flagged permits, the flag undercount (Columbus), and new places

*OH data thread, 2026-11-10. Ohio's run of the North Carolina steps in D-074 (PR #358). Descriptive counts
only: no engine, scenario, calibration or fit run. Ohio has no holdouts (`config/states/oh.yaml`).*

## 1. Coverage: how much of Ohio's eligible land has ADU-flagged permits

Script: `uv run python scripts/dev/oh_adu_coverage.py`. Lots are theme `adu` in `processed/oh/eligible_parcels`
(current rule version), the newest year at or before 2024 for each jurisdiction, made non-overlapping with
`lotline.model.scenarios.adu.non_overlapping`, as the ADU scenario does. A jurisdiction is **covered** when an
ADU-flagged permit source reaches it:

- **Columbus** (`columbus_permits`, flags from the Franklin Auditor's permit descriptions) and **Cincinnati**
  (`cincy_permits`);
- the **Franklin County part** of every other jurisdiction (`franklin_permits`). A place that reaches beyond
  Franklin (Dublin, Westerville, Reynoldsburg …) counts by the share of its single-family parcels inside
  Franklin;
- the 12 **Montgomery** jurisdictions that `montgomery_permits.covered_places` lists.

**Ohio has 3,416,591 eligible ADU lots. 526,745 (15.4%) are covered**:

| Source | Covered lots |
|---|---:|
| `columbus_permits` | 173,843 |
| `montgomery_permits` (12 places, incl. Dayton and the unincorporated county) | 166,620 |
| `franklin_permits` (Franklin suburbs and unincorporated Franklin) | 129,301 |
| `cincy_permits` | 56,981 |

By kind:
- Places hold 1,894,149 lots, and 22% of them are covered.
- County remainders hold 1,318,781 lots, and 8% are covered (Franklin and Montgomery only).
- Townships hold 203,661 lots, and none are covered.

That is above NC's 9% before D-074. Most of it is two counties, though, and in those counties the flags come
from description parsers, so every count is a lower bound.

### The 25 largest jurisdictions by eligible lots

| # | Jurisdiction | Kind | Eligible lots | Covered | Source |
|---:|---|---|---:|---|---|
| 1 | Columbus | place | 173,843 | yes | columbus_permits |
| 2 | Hamilton County remainder | county | 95,725 | no | — |
| 3 | Toledo | place | 81,585 | no | — |
| 4 | Cleveland | place | 80,693 | **new (§3)** | cle_permits |
| 5 | Stark County remainder | county | 69,775 | no | — |
| 6 | Montgomery County remainder | county | 64,928 | yes | montgomery_permits |
| 7 | Akron | place | 59,904 | no | — |
| 8 | Cincinnati | place | 56,981 | yes | cincy_permits |
| 9 | Butler County remainder | county | 54,749 | no | — |
| 10 | Clermont County remainder | county | 54,511 | no | — |
| 11 | Mahoning County remainder | county | 50,611 | no | — |
| 12 | Summit County remainder | county | 48,360 | no | — |
| 13 | Dayton | place | 43,447 | yes | montgomery_permits |
| 14 | Wood County remainder | county | 42,562 | no | — |
| 15 | Warren County remainder | county | 42,162 | no | — |
| 16 | Trumbull County part | county | 41,447 | no | — |
| 17 | Delaware County remainder | county | 40,162 | no | — |
| 18 | Lucas County remainder | county | 38,257 | no | — |
| 19 | Miami County remainder | county | 36,748 | no | — |
| 20 | Franklin County remainder | county | 35,802 | yes | franklin_permits |
| 21 | Medina County remainder | county | 33,489 | no | — |
| 22 | Licking County part | county | 32,259 | no | — |
| 23 | Greene County remainder | county | 30,087 | no | — |
| 24 | Geauga County remainder | county | 27,725 | no | — |
| 25 | Lake County remainder | county | 27,553 | no | — |

The next largest places, none of them covered:

| Place | Eligible lots |
|---|---:|
| Parma | 27,537 |
| Youngstown | 21,992 |
| Canton | 21,780 |
| Lorain | 20,213 |
| Hamilton | 18,606 |
| Springfield | 16,476 |
| Mentor | 16,311 |
| Strongsville | 15,698 |
| Elyria | 15,559 |
| Cuyahoga Falls | 15,302 |
| Middletown | 15,149 |
| Euclid | 15,052 |

Kettering (18,621) is covered.

Places that are only partly covered, by their Franklin share:

| Place | Franklin share |
|---|---:|
| Dublin | 78% |
| Westerville | 79% |
| Reynoldsburg | 72% |
| Pickerington | 10% |
| New Albany | ~100% |
| Canal Winchester | 94% |
| Lithopolis | 2% |

---

## 2. Flag undercount k in Columbus (D-074 step 1)

### 2.1 Detection rule (written and committed before any count)

**What was looked at before writing it.**
- The column layouts of the Franklin County Auditor's appraisal files: `Dwelling.xlsx`, `Improvement.xlsx`
  and `Parcel.xlsx`.
- The improvement code list in the Dec 2016 file, and how often the codes CBN, UFR, DBS, RM1, MIS, OTH, O99
  and RG1–RG4 appear in the 2016 and 2019 files.
- **The 12 Columbus ADU-flagged permits issued 2017-01-01 to 2019-06-30**, on the Dec 2016 and Dec 2019 rolls.
  This is the learn-on cohort. What they showed:
  - **1 of 12** gained a second dwelling card. It was a new house and an ADU built together on a lot that was
    vacant in 2016.
  - **4 of 12** show the ADU only as a detached-garage improvement (code RG1): either a new one with year
    built 2017–2018, or one whose area grew. This is how the Auditor cards a carriage house: as a garage, not
    as a dwelling.
  - **2** were already two- or three-family buildings.
  - **5** show no change.
  - Across the county, the detached-garage codes are being recoded: RG2 went from 240 rows in 2016 to 8,980 in
    2019. So the garage code itself means nothing.
- **Not looked at before this rule was committed:** any permit issued 2020 or later, and the 2024 roll.

**What the roll can and cannot see.** The Auditor's `Dwelling.xlsx` has one row per dwelling card: `CARD`,
`LIVUNITS` (units), `STYLE`, `YRBLT` and `SFLA` (living area). Outbuildings sit in `Improvement.xlsx` under
codes that have no living-area or dwelling code; there is no "garage apartment" or "guest house" code. So the
roll shows a second home only as:

1. **a new dwelling card**: the parcel has 2 or more `Dwelling.xlsx` rows with living area above 0; or
2. **a unit or use change**: `LIVUNITS` summed over dwelling cards goes from 1 to 2 or more, or `LUC` goes from
   510 (single family) to 520 (two family), and card 1's year built is unchanged.

A carriage house over a garage, carded as a garage, is **invisible as a dwelling**. A new detached garage
(an RG1–RG4 line with year built 2020–2024 that wasn't on the 2019 roll) and added living area (`SFLA` up by
200 sq ft or more on card 1) are reported only as an **outer envelope**, never counted as ADUs, just as NC's
signal 3 is.

**Rolls and matching.**
- The earlier roll is the last appraisal snapshot of 2019 (**2019-12-18**); the later one is the last of 2024
  (**2024-12-30**). That is 5.03 years.
- The key is the Auditor's parcel number (`PARCEL ID`, `010-012345-00`). Split lots get new numbers, so new
  lots are never counted. Only numbers present in both rolls are compared.
- A parcel whose `ACRES` grew by more than 20% is a **possible merge** and is set aside.

**Denominator.** A parcel counts when, on the 2019 roll:
- its `LUC` maps to `SF_DETACHED` in `config/crosswalks/oh_dte_luc.csv` (510);
- it has exactly one dwelling card; and
- that card has `LIVUNITS` 1.

The jurisdiction is the parcel's in the processed `parcels` table (2023 roll), else its taxing district's
where 95% of the district lies in one jurisdiction (as `scripts/dev/oh_franklin_history.py` does).

**Groups** (one per gaining parcel), as in NC with the year moved to the later roll:

| Group | Test | Counted |
|---|---|---|
| New card, built 2020+ | Signal 1, newest added card's `YRBLT` 2020–2024 | Yes (strict count) |
| New card, older building | Signal 1, added card built before 2020 | Yes, shown apart |
| Unit or use change | Signal 2 only | Yes, shown apart |
| Teardown and rebuild with two homes | Card 1's `YRBLT` moved to 2020+ | Yes, shown apart |
| Possible merge | Acreage up by more than 20% | No |

**R** = Columbus denominator parcels in any counted group.

**P** = Columbus ADU-flagged permits (`columbus_permits` rows with `adu_type` set) issued **2020-01-01 to
2024-06-30**, matched to roll parcels by their 9-digit parcel number.

**Group (a), permitted but unflagged**: R \ P parcels that have a non-flagged Columbus new-structure dwelling
permit (`permit_class_raw` "101|", "102|", "103|" or "106|" with "1,2,3 Family - New Structure") issued in the
same window.
- **As written**: every such permit counts.
- **ADU-only** (NC's deviation, adopted beforehand here): duplex permits (103) are left out of (a), because a
  two-unit permit is a duplex.
- **Sensitivity**: a "434|1,2,3 Family - New Structure" permit (a new accessory building, the class Columbus
  files many garages and carriage houses under) also counts as (a).

**Group (b)**: the other R \ P parcels.

**Reported:** |P∩R|, |a|, |b|, |P\R|, and k = (|P∩R| + |a|) / |P∩R| with a 90% Wilson interval
(`nc.wake_roll_diff.k_undercount`). The Chapman total (|R|+1)(|P|+1)/(|P∩R|+1) − 1 is the lower-bound check,
with P restricted to denominator parcels.

**Columbus's flags are a parser.** Unlike Raleigh's field flag, they come from the Auditor's permit
descriptions (`franklin_permits.adu_flags`). In D-074's terms they are a parser source, so this k is a
parser-recall check, not a field-flag k.

**Expected, before counting.** The learn-on cohort shows that the roll sees about 1 Columbus ADU in 12. So R
will be small, P∩R near zero, and k probably can't be estimated. If |P∩R| is 0, k is undefined, and that is
reported as the result.

**Montgomery (second test).** Montgomery's CAMA files do carry dwelling cards (`DWELL.DAT`, with registered
extracts for 2011, 2012, 2014, 2018, 2021, 2022, 2024, 2025 and 2026). But Montgomery has **7 ADU-flagged
permits in all** (2020–2026), so |P∩R| can't be more than a handful. The test is not run here; §2.3 says why.
