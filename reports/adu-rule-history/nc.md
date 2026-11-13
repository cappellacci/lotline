# D-086 ADU rule history: North Carolina (first coder)

Coder: `claude-d086`, 2026-11-13. Method: D-086 in `docs/analysis_plan.md`. All rows `single_coder`; a second
coder re-codes every row that creates or moves an event. Coded from ordinance sources only: no permit data,
counts or `LOTLINE_DATA_DIR` were opened. File: `config/reforms/nc.csv`.

D-023 grade: no ADUs 0; permit / conditional / special use 1/3; by right with owner occupancy 2/3; by right
without owner occupancy 1.

## Candidate events (grade changes inside 2014–2025)

| Place | Date | Grade | What changed | Rows |
|---|---|---|---|---|
| **Greensboro** (3728000) | 2024-04-16 | **2/3 -> 1** | Owner occupancy dropped, cap 30% -> 50% of the house, 400 sq ft minimum and the parking space dropped | new `NC-3728000-adu-2010`; `-2024` now supersedes it |
| **Cornelius** (3714700) | between 2021-06-21 and 2023-01-17 | **2/3 -> 1** | Owner-occupied "Rental Cottage" use removed (TA 02-21, 2021-06-21); one-per-lot ADU rule with no occupancy clause (TA 01-22, 2023-01-17). 2021–2023 not coded (text not found), so the code will see the step at the 2023 row | new `NC-3714700-adu-2015`; `-2023` owner_occ filled |
| Raleigh (3755000) | 2020-07-07 | 1/3 -> 1 | Already coded (overlay -> by right). Now preceded by a "no ADUs" row; the 2019 overlay is an adoption (0 -> 1/3), not an event | new `NC-3755000-adu-2010-none` |

**Events that go away:** with the blank fields filled from code text, three earlier D-079 events are no
longer grade changes:

- **Charlotte 2023:** the adopted UDO has ADUs as "PC" (by right) with a same-ownership clause, not an
  owner-occupancy one. That is grade 1, the same as the 2012 rule.
- **Wilmington 2024:** the pre-2021, 2021 and 2022 rules were all by right, with no occupancy clause. That is
  grade 1 throughout.
- **Durham:** grade 1 throughout the window. Owner occupancy was dropped in 2012, before the window.

So in NC the candidate events are Greensboro 2024, Cornelius 2021/23 and Raleigh 2020, against the five
D-079 found across MN and NC (Charlotte 2023, Raleigh 2021 and Wilmington 2024 among them).

## Per place

| Place | Versions in 2014–2025 (effective; what changed; grade) | Rows added | Searched / notes |
|---|---|---|---|
| Asheville 3702140 | 1997 UDO (by right) -> 2015-06-23 Ord. 4431 (sizes, parking); grade unchanged (owner_occ blank in both) | none (chain fixed: 1997 end_date; 2026a/2026 supersedes order) | City's adopted-changes table: no ADU amendment 2015-06 to 2026-01 (2025 Ord. 5128 dropped residential parking minimums only along corridors and in mixed-use districts; not coded). "2022 permit types" lead: no ordinance change found |
| Durham County unincorp. 37063 | 2012 (owner occupancy removed; 30% cap; 1 space) -> 2019-10-28 EHC (800 sq ft, no parking) -> 2024-01-01 SCAD (1,200 sq ft total); grade 1 throughout | `NC-37063-adu-2012`, `NC-37063-adu-2023` (SCAD was missing) | 2019 row filled (by right, no owner occupancy, 1/lot, no parking) from Attachment C |
| Cary 3710740 | pre-2019 rule (placeholder) -> 2025-06-02 ACT 32; grade 1 | none | When UDUs and the R-80/R-40/R-20 detached limit came in (2008–2017 candidates) is still open; no grade change either way |
| Chapel Hill 3711800 | 2003 LUMO -> 2023-06-21 O-6; grade unchanged (owner_occ blank in both) | none (end_dates set) | Town LUMO pages and news: no accessory-apartment amendment 2014–2022 found. A 2015 NC State staff table (secondary) says no owner occupancy and no parking; not used to fill |
| Charlotte 3712000 | 2012 Part A -> 2023-06-01 UDO -> **2024-06-17** 1,000 heated sq ft cap (found by comparing UDO versions); grade 1 throughout | `NC-3712000-adu-2024` | 2023 row: by_right True, owner_occ False filled from the adopted UDO text |
| Cornelius 3714700 | 2015 (earliest seen) Rental Cottage, owner-occupied -> removed 2021-06-21 -> 2023-01-17 ADU rule; **2/3 -> 1** | `NC-3714700-adu-2015` | 2018 Code Update (TA 01-18) text and the 2021–2023 rule not found (archive gaps); news says the pre-2023 code had no per-lot limit |
| Durham city 3719000 | as the county; city dates 2019-10-01 (EHC) and 2024-01-01 (SCAD) | `NC-3719000-adu-2012` | **Corrected:** 2019 effective date (2019-09-03 vote -> 2019-10-01) and SCAD (2023-11-20 vote -> 2024-01-01), both from the UDO amendment index; SCAD adu_max_sqft blank -> 1200 |
| Greensboro 3728000 | 2010 LDO rule (earliest seen) -> **2024-04-16**; **2/3 -> 1** | `NC-3728000-adu-2010` | LDO amendment list 2014–2024 shows no other ADU change (2021 separate meters only). The 1992 UDO was not checked |
| Huntersville 3733120 | pre-2024 Sec. 9.1 (R, TR, NR; GR related persons only) -> 2024-09-17; grade 1 throughout | `NC-3733120-adu-pre2024` (date placeholder) | First adoption of 9.1 not found (the ordinance dates from 1996-11-19). The 2010-01-01 placeholder is **not** proven by sources |
| Matthews 3741960 | UDO enacted 2014-04-01 -> 2016-04-11 Ord. 2141 (district list) | none | The 2014 text was not available to this coder (only Ben's local copy is cited). Coding it would mean guessing by_right, and a blank there would create a false fractional event in 2016. **To do:** read Matthews UDO.pdf for the 2014 Sec. 155.506.9 and the pre-UDO zoning ordinance |
| Mint Hill 3743480 | 2011 UDO (owner/family occupancy, not rented; grade 2/3); no change found | none | Web searches found no Mint Hill ADU amendment (hits were Hillsborough's) |
| Raleigh 3755000 | none (1970s–2019) -> 2019-05-20 overlay (1/3) -> 2020-07-07 by right (1) -> 2022-08-08 TC-20-21 | `NC-3755000-adu-2010-none` | Secondary sources (NC State, WRAL, IndyWeek); use tables not read. End dates set on the 2019 and 2020 rows |
| Wilmington 3774440 | pre-2021 Sec. 18-247/248 -> 2021-12-01 LDC (900 sq ft) -> **2022** O-2022-41/88 (50% or 1,200 sq ft) -> 2024-05-21 (detached minimum lot area dropped); grade 1 throughout | `NC-3774440-adu-2022` | **Corrected:** the pre-2021 cap 900 -> 1200 (code text: detached lesser of 35% or 1,200; attached lesser of 35% or 800); by_right and owner_occ filled on the pre-2021 and 2021 rows. The 1,200 sq ft cap dates from 2022, not 2024 as WHQR reported |

## Existing rows changed (all explained in each row's `coding_notes`, prefixed "D-086")

- **Fields corrected:**
  - `NC-3774440-adu-pre2021` adu_max_sqft 900 -> 1200.
  - `NC-3719000-adu-2019` effective_date 2019-09-03 -> 2019-10-01.
  - `NC-3719000-adu-2023` effective_date 2023-11-20 -> 2024-01-01.
- **Blanks filled from code text:**
  - Charlotte 2023: by_right, owner_occ.
  - Durham 2019, city and county: by_right, owner_occ, detached, per lot, parking.
  - Durham city 2023: adu_max_sqft.
  - Wilmington pre-2021 and 2021: by_right, owner_occ, detached.
  - Cornelius 2023: owner_occ.
- **Chain fixes** (end_date / supersedes):
  - Asheville 1997, 2015, 2026a and 2026.
  - Chapel Hill 2003 and 2023.
  - Raleigh 2019 and 2020.
  - Wilmington 2021 and 2024.
  - Greensboro 2024, Huntersville 2024 and Charlotte 2023.
  - Durham 2019 rows.
  - Superseded rows without an end_date stayed "live" next to their successors in `calibrate_adu`'s
    in-force check.

## Uncertain, for the second coder

- **Cornelius:** the event's year (2021 or 2023) and what the code said from 2021-06-21 to 2023-01-17. Also
  whether the 2018 Code Update changed the Rental Cottage rule.
- **Durham 2012 row:** the amendment's exact date is unknown, so 2012-01-01 is a placeholder (tagged
  `[predates]`). Parking is left blank because the 2017 removal's date was not found (TC17-05 Omnibus 11 was
  not read).
- **Huntersville pre-2024:** the start date is a placeholder.
- **Greensboro 2010:** the start is the LDO date, `[earliest-known]`.
- **Wilmington 2022:** which ordinance (O-2022-41 on 2022-06-07 or O-2022-88 on 2022-11-01) raised the cap.
  Tagged `DATE UNCONFIRMED`.
- **Charlotte 2024:** the petition number (2024-033 likely) was not read. The date is from the UDO version
  label.
- **Durham SCAD cap:** the 1,200 sq ft cap is attributed to SCAD from the current code. The analysis document's
  red "not approved" marks cannot be seen in the text copy.
- **Raleigh "no ADUs":** rests on secondary sources.
- **Owner_occ blank** remains on Asheville and Chapel Hill. Grade is constant there, so no event either way.
- **Wilmington 2024** source PDF: the city site blocks scripted downloads, so it was read through a fetch
  tool.

## Main sources

- **Greensboro:** the Feb. 28, 2024 Sec. 30-8-11.2 ordinance (Wayback), the city's ADU page and the LDO
  amendment list.
- **Durham:** UDO Art. 5 as amended 11/17/2014 (Wayback), the EHC Proposed Concepts and Attachment C (2018–19),
  the UDO text amendment index (durham.municipal.codes, Wayback 2024-05-26), current UDO Sec. 5.4.2 and the
  SCAD Detailed Analysis.
- **Charlotte:** UDO versions on charlotteudo.org (Aug 2022, Jan, May and June 2024, Sep 2024, Feb and June
  2025).
- **Wilmington:** old Chapter 18 (Zoneomics), LDC Art. 3, Supp. 1 Update 1 and Supp. 4 (Municode library
  PDFs), and LDC-7-424.
- **Huntersville:** TA25-08 draft (municipalcodeonline) and Zoneomics.
- **Cornelius:** LDC Ch. 6 (9/21/2015, Wayback), the 01-17-2023 combined LDC (Wayback) and Cornelius Today
  (Jan 2023).
- **Raleigh:** NC State AH+SC, WRAL and IndyWeek.
- NC State "Backyard Cottages in Six Cities" (2015), as a secondary cross-check.
