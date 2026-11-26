# ADU coverage fix: rule rows corrected after the coverage audit (2026-11-15)

Follow-up to D-095 and the coverage audit (`reports/adu-coverage-audit/`, PR #437). Ben approved fixing the
flagged coding rows and then refitting ("Yes, fix then refit"). **This change touches rule rows in
`config/reforms/{mn,nc,or,tx}.csv` only.** No code, parameters, fits or model runs; the refit happens in the
ADU session.

Every edited row carries a `[coverage fix 2026-11-15]` note in `coding_notes` with the reason, the source and
each old → new value. Rows whose values changed also get `verified_by` = `claude (coverage fix 2026-11-15, D-095
audit)` and `verified_date` 2026-11-15. A new source is appended to `source_url` where the change rests on one.

## What changed

61 rows were touched: 33 had a coded value changed, 26 got a note only (flagged, but coded correctly) and 2 blank
placeholders were marked `UNKNOWN-PLACEHOLDER` with the sources tried.
Order of work: fit places first, larger places first.

### 1. Blank placeholder rows → explicit "no ADUs" (#164)

| Row | Place | Before | After | Source |
|---|---|---|---|---|
| MN-2708794-adu-2016 | Burnsville | blank (read: allowed, all fields unknown) | `adus_per_lot` 0, `by_right` False, `NO ADU RULE` | PLN 20-032 report: 2018 amendments made "to allow accessory dwelling units"; § 10-7-52 created by Ord. 1456 |
| MN-2755726-adu-2016 | Rosemount | blank | `adus_per_lot` 0, `by_right` False, `NO ADU RULE` | Dakota County ADU guide (2023-12-20), "Cities that do not currently allow for ADUs" |
| MN-2710918-adu-none | Chanhassen | a "none" row without `adus_per_lot` 0 (read as a partial rule) | `adus_per_lot` 0, `NO ADU RULE` | § 20-56: no ADU use in any district |
| MN-2766460-adu-2016 | Vadnais Heights | blank | `adus_per_lot` 0, `by_right` False, `NO ADU RULE` | SEH memo to the 2024-04-23 Planning Commission: the study "encouraged the City to consider updating their zoning code to allow for Accessory Dwelling Units"; its review of the old code lists no ADU use in R-1 to R-3; the 2024 draft adds a new ADU definition |

### 2. Zone lists that cover every single-family district → citywide (0.75 → 1.0)

Each list named every district that allows single-family detached homes, so the 0.75 judgment for an unmeasured
zone list understated coverage and made the place's rows step for no change in the rule.

| Row(s) | Place | Old `coverage_zones` | Read coverage before → after | Why it is every single-family district |
|---|---|---|---|---|
| NC-3712000-adu-2012 | Charlotte | R-3 … B-2 (22 districts) | 0.75 → 1.0 | Sec. 12.407: ADUs "accessory to any single family detached dwelling unit"; now matches the 2023 UDO row |
| NC-3755000-adu-2020, -2022 | Raleigh | R-1;R-2;R-4;R-6;R-10 | 0.75 → 1.0 | TC-16-19 (UDO 2.1.3.C): one ADU on any lot with a Detached House; R-1 to R-10 are all residential districts, mixed-use districts listed too |
| NC-3733120-adu-2024, -2025 | Huntersville | R;TR;GR;NR | 0.75 → 1.0 | Art. 3.2: "accessory dwelling" a permitted accessory use in every residential district (R, TR, GR, NR, NC, TC, TND, TOD-R) |
| NC-3714700-adu-2023 | Cornelius | RP;GR;NR;NMX | 0.75 → 1.0 | Table of Uses: "Dwelling, Single-Family" is P only in RP, GR, NR, NMX; the 2015 row (same districts) read 1.0 |
| MN-2743000-adu-2023 | Minneapolis | UN1-3;RM1-3;CM1-4 | 0.94 (parcels) → 1.0 | City ADU summary: permitted "on lots where single- and two-family homes are allowed … throughout the City"; same scope as 2014-2021 rows (1.0) |
| MN-2743252-adu-2021 | Minnetonka | R-1;R-1A;R-2 | 0.75 → 1.0 | R-3 to R-5 allow attached or multifamily only (§300.11-300.13) |
| MN-2744530-adu-2025b | Mounds View | R-1;R-2;R-3;R-4 | 0.75 → 1.0 | All residential districts except R-5 (mobile home park) |
| MN-2755726-adu-2024 | Rosemount | A-2;RR;R-1;R-2 | 0.75 → 1.0 | Table 3.1: single-unit dwellings PS in A-1, A-2, RR, R-1, R-2; only A-1 (40-acre agricultural) left out |
| MN-2713456-adu-2023 | Cottage Grove | R-1;R-2;R-3;R-4 | 0.75 → 1.0 | R-1 to R-4 are every residential district permitting single-family detached (§11-7-4(B)(1)); only AG-1/AG-2 left out |
| OR-4105800-adu-2016, -2019, -2021, -2025 | Bend | RL;RS;RM-10;RM;RH;UAR | 0.75 → 1.0 | The only other single-family district, SR 2 1/2, had no land in the city (staff memo 19-0597, 2019); the 2016a row read 1.0 |
| OR-4159000-adu-2021, -2022 | Portland | R7;R5;R2.5 / R20…R2.5 | 0.77 / 0.85 (parcels) → 1.0 | The list named where a **second** ADU is allowed; one ADU is allowed with a house in every single-dwelling zone (RF, R20-R2.5) and in multi-dwelling, C and EX zones |

Where the zone list was cleared, the coverage text was reworded to begin "All single-family districts" (or "All
districts allowing …") and checked not to trip the engine's limited-area wording.

### 3. Limited areas read as citywide → zone list (1.0 → 0.75 judgment, or lower with a lot minimum)

| Row(s) | Place | New `coverage_zones` | Before → after | Single-family districts left out |
|---|---|---|---|---|
| MN-2721770-adu-2004 | Forest Lake | A;RR;C;AP | 1.0 → 0.75 | Text: rural districts only, "not allowed in the urban single-family districts" |
| OR-4147000-adu-2016 | Medford | SFR-00;SFR-2;SFR-4;SFR-6;SFR-10 | 1.0 → 0.75 | Text: SFR zones only; multi-family and commercial zones added in 2018 |
| MN-2708794-adu-2018, -2020 | Burnsville | R-1;R-1A | 0.97 → 0.73; 1.0 → 0.75 | R-2, R-3, R-4 permit single-family detached (§10-5-3 to 10-5-5) |
| MN-2706616-adu-2016, -2019 | Bloomington | R-1;RS-1 | 0.79 → 0.59; 1.0 → 0.75 | R-1A, RM-12 (§21.209(c)); now matches the 2022 and 2025 rows, which already had the list |
| MN-2717288-adu-2014 | Eagan | E;R-1 | 1.0 → 0.75 | A, R-1S |
| MN-2731076-adu-2018 | Inver Grove Heights | A;E-1;E-2;R-1A;R-1B;R-1C | 1.0 → 0.75 | R-2, R-3A (§10-6-1 matrix) |
| MN-2706382-adu-2021 | Blaine | R-1;R-1A;R-1AA;R-1B;RE;FR;DF | 1.0 → 0.75 | AG, R-2 (§109-237(2), §109-20(2)) |
| MN-2757220-adu-2020, -2025 | St. Louis Park | R-1;R-2;R-3 / N-1;N-2 | 1.0 → 0.75 | R-4 (§36-166(b)(6)); 2025: N-3/N-4, which replaced R-3/R-4 |
| MN-2766460-adu-2024 | Vadnais Heights | R-1;R-2 | 1.0 → 0.75 | R-3 (§38-155(a)(2), §38-105) |

The 0.75 is the engine's judgment for any unmeasured zone list (`adu_rule_zoned_coverage_share`): it is blunt for
Forest Lake (rural districts only) and Medford, where the true share is probably lower. That is a parameter
question for the ADU session, not a coding one.

### 4. Strong-flag rows checked and left citywide (note only)

The 35 "strong" rows were all read. These stay citywide, each with a note saying why:

- Scott County townships (Cedar Lake, Helena, Jackson, St. Lawrence; 12 rows): the listed districts are all of the
  townships' agricultural, rural and residential districts.
- Durham city and county (7 rows): the UDO allows ADUs "In Residential Districts and on Properties Devoted to
  Residential Use"; "only" refers to one-dwelling lots.
- Baytown (all residential/agricultural districts), Rochester 2023 (AG, R-1 to R-4, R-2x, all MX), Inver Grove
  Heights 2015 ("all single-family zoning districts"), Chanhassen 2025 (A2, RR, RSF, R-4, RLM are every
  single-family district), Crystal 2018 (single-family detached is P in R-1 and R-2 only), Huntersville 2016,
  College Station 2023 (the flag came from the word "Overlay" in a list of other ordinances).

## Flag counts, before → after

`PYTHONPATH=src python scripts/archive/adu_coverage_audit.py` on the edited rows (fit rows / fit places in brackets):

| Flag | Before | After |
|---|---|---|
| blank | 7 (5 / 5) | 4 (2 / 2) |
| zones_switch | 55 (34 / 15) | 31 (10 / 5) |
| area_text_citywide | 103 (73 / 41) | 106 (76 / 38) |
| strong | 35 (35 / 20) | 32 (32 / 18) |

How coverage is read, over the 582 ADU rows: citywide 467 → 474; zone list at the 0.75 judgment 75 → 71 (+15 →
17 with a measured lot minimum); lot minimum measured 11 → 9; limited area 11 → 11; zones measured on parcels 3 → 0.

**The audit's text flags can't settle these rows by themselves.** A row reworded to "All single-family districts
(R-1 to R-4) …" still names districts, so it is now flagged `area_text_citywide` (that is why that count rose by
3), and some notes add words like "overlay" or "only". Every remaining strong row was read by hand; the list is in
section 4 and below.

What is left in the fit, and why:

- **zones_switch (10 rows, 5 places)** are real changes in where ADUs are allowed: Blaine 2021 list → 2025
  citywide moratorium; Inver Grove Heights 2015 (all single-family districts, per council minutes) → 2018 (R-2,
  R-3A left out); Plymouth 2009 (new subdivisions only) → 2023 list; Medford 2016 (SFR only) → 2018 (all zones);
  Asheville 2015 list → the 2027 state-law row.
- **Lists kept on purpose:** Asheville 2015 (RS2…RM16; the row's own text excludes Urban Residential, and the
  2023 use table shows single-family homes allowed in office, business and Resort districts too); Plymouth 2023
  (RSF-4 permits single-family detached and is left out).

## Rows left unchanged, and why

| Row | Place | Why |
|---|---|---|
| MN-2722814-adu-2022 | Fridley | Could not read the use table (image only); the city ADU page names R-1, R-2, R-3, S-1, which may be all. Left citywide. |
| MN-2745430-adu-2024 | New Brighton | No readable copy of the code found. Left citywide. |
| MN-2744530-adu-2016 | Mounds View | "R-1 lots only" comes from an undated handout (lead only), and the row's start date is itself unconfirmed. |
| MN-2743252-adu-1986 | Minnetonka | "Residential districts; exact districts not confirmed". |
| MN-2741480-adu-2011, -2024 | Medina | Attached ADUs by CUP in every single-family district; detached only in AG, RR, RR-UR. Coverage 1.0 is right for the attached form. |
| TX-4865000-adu-2010 | San Antonio | Excludes FR (farm and ranch) only: a fringe district with few single-family lots. Filling a list would cut coverage by 25% to drop a sliver. |
| MN-2716315688-adu-2019 | Denmark Twp | Excludes Ag Preserve only (same reasoning). |
| NC-SL2026-59-* | NC cities | State law effective 2027-01-15, after the window; "areas zoned residential" is the statute's own scope. |
| 43 rows outside the fit | NC, OH, OR, TX | Not in the fit; not changed. Two Ohio blanks (OH-3916014-adu-2026, OH-3927048-adu-2027) are `pending`, so the engine does not read them. |

## `UNKNOWN-PLACEHOLDER` rows (for the ADU session to leave out of the fit)

| Row | Place | Years | What the public sources show |
|---|---|---|---|
| MN-2713456-adu-2016 | Cottage Grove | 2016-01-01 to 2023-01-01 | The pre-2023 code (Wayback 2022-05-25, §11-1-3) already defined "accessory apartment", which leans toward "allowed", but no archived residential-district section shows where it was a use. |
| MN-2740382-adu-2016 | Maplewood | 2016-01-01 to 2023-12-11 | The 2040 plan (2019) says an ADU policy "is also needed" and the 2023 update "added" ADU standards, which leans toward "not allowed", but nothing says ADUs were prohibited; the old Municode text is behind a bot check (not bypassed). |

Both rows are otherwise unchanged (still blank, so the engine still reads them as "allowed, every field unknown"
until the ADU session drops them). The two Ohio blanks are `pending` rows outside the fit and need nothing.

## How this was checked

- Every changed value rests on the row's own cited text or on a public code page cited in the row. District
  lists for 20 places were checked against current codes (Zoneomics mirrors of Municode/American Legal, city
  PDFs, Wayback copies); district names were assumed unchanged over the row's dates unless noted.
- Edits were applied by a small script that writes the CSVs byte-for-byte except the changed cells (checked by a
  no-change round trip), records old → new values in `coding_notes`, and leaves `verified_by` alone on Ben's and
  pipeline rows.
- Coverage before and after was computed with `scenarios.adu.coverage_map` (offline) for every changed row.
- `pytest tests -k reform`: 99 passed. `python compliance_check.py`: 0 FAIL.
