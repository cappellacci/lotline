# D-086 ADU rule history: Minnesota, part 2 (`mn-2`)

First coder: Claude Code, 2026-11-13, working from the D-086 brief. Coded blind to counts: no permit data,
`LOTLINE_DATA_DIR` or report file was opened (only this report's folder was written). St. Paul was not coded. Every new row is `single_coder`. The coder tag
`claude-d086` is in each new or edited row's `coding_notes`; the `coder` column says `claude` (see deviations).

D-023 grade: no ADUs 0; permit, conditional or special use 1/3; by right with owner occupancy 2/3; by right without
it 1. "Event" below means a grade change inside 2014–2025 between two coded rules (an adoption from "no ADUs" is
not an event under D-086).

## Candidate events for the second coder

| Place | Date | Grade before -> after | Status |
|---|---|---|---|
| **Orono** (2748580) | 2022-11-14 | 1/3 (guest house by CUP, no rent) -> 2/3 or 1 (ADU by right; no rental separately; owner occupancy not stated) | **NEW.** Depends on whether a non-rentable guest house counts as an ADU. |
| Minneapolis (2743000) | 2021-03-06 | 2/3 -> 1 (owner occupancy dropped for attached/detached) | Already coded; unchanged. |
| New Brighton (2745430) | 2024-09-24 | unknown (servants' quarters rules, fields blank) -> 2/3 | NEW pre-2024 row, weak source; only one fit year after the change, so it should not qualify as an event. |
| Plymouth (2751730) | 2023-09-12 | 2002 rule: by right, owner occupancy unknown -> 2/3 | Already coded; the 2002 owner-occupancy rule is still unknown. |

No other grade changes were found. Minnetonka (1/3 -> 1/3), Roseville (2/3 since 2011), St. Lawrence township
(1/3 -> 1/3) and Stillwater (1/3) keep their grades.

## Per place

| Place | Versions found (effective date: what changed, grade) | Rows added / changed | Searched, nothing older found |
|---|---|---|---|
| Lakeville (2735180) | 2013-03-04 (coded): internal "multiple generations" quarters by administrative permit, 2/3 or 1 (owner occupancy not stated). Code history also lists Ord. 920 (2014-04-07), 1065 (2022-04-04), 1121 (2026-02-17); what they changed was not found. | none | Zoneomics code history (§11-50-11.F); Dakota County ADU guide (2022-12-06: allowed, administrative permit, no owner occupancy); searches for Ords. 920 and 1065 found only broad zoning updates. |
| Maplewood (2740382) | 2023-12-11 (coded): Ord. 1044, by right, no owner occupancy. | none | Zoneomics code (no earlier ADU or accessory-apartment text); Dec 2023 workshop packet (search summary). Prior status not found, so no "no ADUs" row. |
| Medina (2741480) | 2011-11-15 (coded): Ord. 514, CUP, 1/3. | none | Searches for later amendments to 826.98; the 2020 code PDF the row cites is gone (404, no archive copy); Chapter 8 TOC read. |
| Minneapolis (2743000) | **Before 2014-12-05: no ADUs in single-family zones** (except an area around Ventura Village, 2001). 2014, 2016, 2021, 2023 coded. Ord. 2025-023 (2025-05-15) edits detached standards only. | **Added** `MN-2743000-adu-2010-none`; 2014 row now `supersedes` it. | The Green Line ADU pilot sometimes cited is St. Paul's, not Minneapolis's. |
| Minnetonka (2743252) | **Before 2021-10-04: internal/attached ADUs by CUP, owner occupancy, 35% or 950 sq ft, detached only with a variance** (city handout uploaded 2019-10-08). 2021-10-04 (coded): detached ADUs added, still CUP. Grade 1/3 -> 1/3. | **Added** `MN-2743252-adu-pre2021`; 2021 row now `supersedes` it. | |
| Mound (2744476) | 2024-11-03 (coded): Ord. 7-2024, 2/3. | none | June 2024 Planning Commission packet (draft ADU code; says nothing on prior status). |
| Mounds View (2744530) | 2025a (internal ADU by right) and 2025b (detached CUP) coded. A city handout (undated) says internal ADUs and additions (by CUP) were allowed in R-1 with owner occupancy, so an older rule probably exists; its date was not found. | none | Zoneomics code history (§160.087 lists Ords. from 1988 to 2025; which one added ADUs is unknown). City WebLink refused connections. |
| New Brighton (2745430) | **Before 2024-09-24: "servants' quarters" rules on a very small subset of lots** (Star Tribune, via search summaries; text not found). 2024-09-24 (coded). | **Added** `MN-2745430-adu-pre2024` (all rubric fields blank); 2024 row now `supersedes` it. | City documents 403; no code mirror. |
| Orono (2748580) | **Before 2022-11-14: guest houses by CUP on lots twice the district minimum, non-rental; non-rental guest apartments inside the house permitted** (struck text of Ord. 279). 2022-11-14 (coded): ADUs by right on lots of 1 acre or more. | **Added** `MN-2748580-adu-pre2022`; 2022 row now `supersedes` it. **Filled blanks** on the 2022 row from the signed ordinance: `adus_per_lot`=1, `min_lot_sqft`=43560, parking 2 spaces. | |
| Plymouth (2751730) | 2002 and 2023 coded; Ord. 2025-02 (2025-03-25) minor. | none (already chained by `supersedes`). | Zoneomics §21190.04 (current text only); the city's 2023 document is 403 with no archive copy, so the 2002 owner occupancy and size are still unknown. |
| Ramsey (2753026) | 2022-03-14 (coded): Ord. 22-04, 2/3. | none | Ramsey's 2021 and 2022 staff research ("Research for Introductions of ADU's in the City of Ramsey") implies none before, but does not say so: no "no ADUs" row. |
| Richfield (2754214) | 2015 (coded): code history says §514.05 Subd. 8 was "Added, Bill No. 2015-4; amended, Bill No. 2015-9". Adoption date still not found. | none | Zoneomics ch. 5 history notes. City documents 403. "Ordinance 2022-27" (detached ADUs) found in searches is **Richfield, Utah**: do not use. |
| Rochester (2754880) | 2023-01-01 (coded): UDC. The city says ADUs "became eligible accessory uses in all residentially zoned districts" then. A 2019 change named in the existing row was not found. | none | City ADU page and UDC (search summaries); the pre-2023 Land Development Manual was not found online. |
| Rogers (2755186) | 2020-05-26 (coded, all fields blank). See "Existing rows to check". | none | Zoneomics code read. |
| Rosemount (2755726) | **Before 2024-06-04: no ADUs** (Dakota County guide, updated 2022-12-06). 2024-06-04 (coded). | **Not added** (see deviations): a "no ADUs" row is sourced but cannot be chained safely. | |
| Roseville (2755852) | 2010 (CUP), 2011 (Ord. 1418, by right), 2021 (Ord. 1606) coded. Ords. 1644 (2023) and 1682 (2024) content not found. | none (already chained by `supersedes`). | Zoneomics (ADU section missing from the mirror); civicplus code host no longer resolves. |
| St. Lawrence township (2713957184) | Governed by **Scott County Zoning Ordinance No. 3** (county zoning for unincorporated townships), coded from it: 2010 and 2025. | none (already chained by `supersedes`). | |
| St. Louis Park (2757220) | 2020-11-13 (coded). A 2025 code rewrite (Ord. 2690-25, 2025-03-03 per search summaries) may have relaxed owner occupancy; not confirmed. | none | City pages 404; the city's ADU study page says Council began discussing ADUs in January 2019 (search summary). |
| Stillwater (2762824) | 2017 (coded, `[predates]`). Ord. 1202 (2023-06-06) recodified §31-501 to 31-503 as §28-322 to 28-324 with the same rules (CUP in TR/RB, CTR CUP, 10,000 or 14,000 sq ft lots). No owner-occupancy text in the code. | none | Zoneomics ch. 3 and 5 read. |
| Vadnais Heights (2766460) | 2024-07-16 (coded): Ord. 774. Sec. 38-626 carries only Ord. 774 in its history. | **Filled blanks** on the 2024 row from Sec. 38-626: by_right (attached; detached is CUP), owner_occ, detached, 1 per lot, 1,200 sq ft. | Prior status not found. |
| Wayzata (2768818) | 2022-06-30 (coded): Ord. 811. | none | Zoneomics and wayzata.com search summaries; nothing on prior status. |

## Deviations from the brief (forced by `tests/states/mn/test_reforms.py`)

- **No `end_date` on replaced rows.** The MN test `test_windows_end_after_they_start` allows `end_date` only on
  `suspended` rows. MN chains amendments through `supersedes` alone (and `scenarios.adu._live` drops superseded
  rows), so the chains are consistent without end dates. Every new row is chained that way.
- **`coder` is `claude`, not `claude-d086`.** `test_pipeline_and_ben_rows` allows only `claude`, `ben` and
  `pipeline+ben`. The tag `claude-d086` is at the start of each new row's notes (after `NO ADU RULE.` on the none
  row, which that test requires first) and in a dated note on each edited row. If Ben wants the column value, the test
  needs a one-line change.
- **Rosemount "no ADUs" row not added.** The Dakota County guide (updated 2022-12-06, Wayback copy) lists Rosemount
  under "Cities that do not currently allow for ADUs", so the row is sourced. But in MN it could only be ended by
  `supersedes`. `MN-2755726-adu-2024` leaves `adus_per_lot` blank, and `_resolved` would then fill it with 0 from
  the none row, turning the 2024 rule into "no ADUs". The current code (§11-6-7.A, Zoneomics) does not state ADUs
  per lot, so I could not fill it. Ready to add once the 2024 row's `adus_per_lot` is confirmed (or end dates are
  allowed). Not an event either way: it is an adoption.

## Uncertain points and existing rows to check

- **Rogers (`MN-2755186-adu-2020`) may not be a general ADU rule.** Table 4 lists "Dwelling, Accessory Units" as an
  accessory use in three districts. But the only ADU definition in the code mirror is "Temporary dwelling, farm" (a
  mobile home for farm family members in an agricultural district). The R-1 text says "Accessory buildings shall not
  contain dwelling units". Ramsey's January 2022 staff table lists Rogers as "ADU's not allowed". Not changed;
  Ben to decide.
- **Roseville's 2021 change may be dated wrong.** Ramsey's staff research of 2021-08-26 describes Roseville's then
  current §1011.12(B) with a 300–650 sq ft range and one added parking space. That is before Ord. 1606
  (2021-11-08), which the existing rows credit with the 650 sq ft cap. Either an amendment between 2011 and 2021 was
  missed, or Ramsey quoted a draft. Not changed.
- **Mounds View 2025b `supersedes` 2025a.** Ord. 1045 added detached ADUs by CUP. It did not repeal the internal ADU,
  which stays an accessory (by-right) use in §160.087(J). So the model reads Mounds View as 1/3 from 2025-09-13 when it
  is 2/3 for internal ADUs. This is outside the event window, so it has no effect on g. No end date was set on 2025a.
- **Richfield 2015 row:** `adu_detached_allowed` is False, but its notes and the code allow detached ADUs as part of
  a garage. Not changed.
- **Minnetonka 2021 ordinance number:** a search summary of the 2021-10-04 agenda names Ords. 2021-14 and 2021-15,
  not 2021-20. Not changed.
- **Orono guest houses:** whether a non-rentable guest house counts as an ADU decides whether the 2022 change is an
  event.
- **New Brighton pre-2024 row** rests on search summaries of one news article, and every rubric field is blank. Its
  coverage is free text, so the model will treat the old rule as broad. A second coder should find the old code
  text or drop the row.
- **Lakeville** Ords. 920 (2014) and 1065 (2022) touched §11-50-11.F. What they changed was not found.

## Sources not reachable

The Star Tribune returned 429. City sites for Minnetonka, Plymouth, Richfield, New Brighton and St. Louis Park
returned 403 or 404. Mounds View and Roseville code hosts refused connections. American Legal (amlegal) blocks
automated reads. The Wayback Machine was intermittently offline. Where an archived copy existed, it was used.
