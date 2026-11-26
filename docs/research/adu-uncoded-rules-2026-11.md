# ADU rules for the largest uncoded places, Minnesota and Ohio (2026-11-15)

Follow-up to the ADU gut check (`reports/adu-gut-check/`), which found that places with no coded ADU rule produce
about 73% of Ohio's and 52% of Minnesota's predicted added ADUs. Ben asked for the biggest of them to be coded ("Code
the rules for the largest uncoded places"). **This change touches rule rows in `config/reforms/{mn,oh}.csv` only**,
plus the place whitelist in two reform tests (see "Tests" below). No code, parameters, fits or model runs; the ADU
session refits afterwards.

Conventions follow `docs/research/adu-coverage-fix-2026-11.md` (PR #440). Every new row carries
`[uncoded-rules 2026-11-15]` in `coding_notes`, a source URL, section and short verbatim quote, and `coder` = claude.
`verified_by` says what the independent second pass found for that row (see "How this was checked").

## Result

| | Ohio | Minnesota |
|---|---|---|
| Places coded | 20 | 20 (incl. the Blaine fix) |
| Rows added | 20 | 24 (+1 existing Blaine row changed) |
| Their share of the state's **uncoded** `adu_permits_added_mean` | 182.4 of 775.9 = **23.5%** | 128.8 of 418.6 = **30.8%** |
| … of the state's total added ADUs | 17.1% | 16.0% |
| Places researched and skipped | 19 (18 county remainders, Solon) | 2 (Itasca County, Chaska) |

Ohio's share is lower because 18 of its 26 largest uncoded places are county unincorporated areas, and in most of
them no single zoning code governs the land (see below). Those 18 skipped counties alone hold 206 of Ohio's 776
uncoded added ADUs.

**Most coded places turn out to have no ADU rule.** Of the 40 places, 27 have an explicit "no ADU" row
(`adus_per_lot` 0) for all or part of the period (17 in Ohio, 10 in Minnesota), 6 of them because the only accessory
unit is limited to family or guests (see the Fort Worth heading). Akron, the largest
uncoded place in Ohio, has no ADU use at all. For the model this means today's-rules baselines in these places
fall to zero and the Handbook reform's added ADUs rest on the reform alone.

## Blaine (MN, 2706382): why it read as uncoded, and the fix

Blaine had two rows: the 2021 rule (Ord. 21-2489, ending 2025-05-19) and the 2025 moratorium row
(`MN-2706382-adu-2025`), whose `status` was **`suspended`**. Every engine and fit filter keeps `status == "in_force"`
only (`scenarios/adu.py::_live`, `calibrate_adu.py`, `estimate_adu.py`), so after 2025-05-19 no Blaine row was
live and the place read as uncoded at the 2025 origin.

Fix:
- `MN-2706382-adu-2025` (moratorium, Ord. 25-2577): `status` suspended → **in_force**, `adus_per_lot` 1 → **0**
  (no ADU application could be filed or approved), `end_date` → **2026-03-16**. Old values are in the row's note.
- New `MN-2706382-adu-2026` (Ord. 26-2601, adopted 2026-03-16, supersedes the moratorium row): attached ADUs only,
  by administrative permit, in R-1, R-1A, R-1AA, R-1B, RE, FR, DF; owner-occupied; lesser of 50% of the house or
  960 sq ft (1,200 in RE/FR); home + ADU need 3 off-street spaces. Detached ADUs removed (news on the ordinance:
  "removes detached units from all districts"; the Zoneomics R-1A listing for detached ADUs predates it).

**Decision for Ben:** coding a moratorium as an explicit no-ADU rule is a new convention. The alternative (status
`suspended`, the place reads as uncoded) is what produced the gap. Blaine's baseline at the 2025 origin is now 0.

## Ohio: places coded (20)

Ranked by `adu_permits_added_mean` (per year) in the gut check. "No ADU" = `adus_per_lot` 0, `by_right` False.
"from 2016" = date basis earliest-known (text unchanged in the oldest copy found).

| Place (geoid) | Added | Rows | Rule |
|---|---|---|---|
| Akron (3901000) | 40.8 | `-2016-none` | No ADU. Ch. 153 has no ADU use; U1: "only one building including accessory structures" per lot; 2023 form-based code (mapped areas) has no ADU use; the 2026 ADU/duplex proposal is not on council's passed list as of 2026-11-09. |
| Franklin Co. uninc. (39049) | 15.1 | `-2016-none` | County zoning resolution (10 townships, ~58% of unincorporated homes). Granny-flat accessory apartment: CUP, Rural district only, internal, occupied only by the owner's family → no ADU (family-only). |
| Lima (3943554) | 14.1 | `-2016-none` | No ADU: single-family districts allow one single-family house; no ADU use. |
| Grove City (3932592) | 12.6 | `-2016-none` | No ADU: "permitted uses are exclusive and noncumulative"; no ADU use. |
| Westerville (3983342) | 9.3 | `-2024` | ADU (attached or detached) by zoning certificate, **only within the Olde Westerville overlay** (read as limited area). Weak: start date 2024-07-25 is earliest-known; owner occupancy reported but not seen at source (blank); 2016-2024 not coded. |
| Mason (3948188) | 8.4 | `-2016-none` | No ADU: R-1 to R-4 "used only for" single-family. |
| Strongsville (3975098) | 7.6 | `-2016-none` | No ADU: "not more than one, one-family or one, two-family dwelling" per lot. |
| Avon (3903352) | 7.1 | `-2016-none` | No ADU: unlisted uses prohibited; one dwelling per lot. |
| Westlake (3983622) | 6.5 | `-2016-none` | No ADU: one principal use by right; "accessory living accommodations" have no cooking. |
| Macedonia (3945976) | 6.0 | `-2016-none` | No ADU: R-1 accessory uses are home occupations and roadside stands only. |
| Powell (3964486) | 5.9 | `-2017-none` | No ADU from Ord. 2017-60 (recodification): one principal building; "Rear dwellings shall be prohibited". 2016-2017 not coded. |
| Pepper Pike (3961686) | 5.8 | `-2016-none` | No ADU: "A residence in an accessory building is not permitted." |
| Delaware (3921434) | 5.8 | `-2025` | Ord. 25-38 (passed 2025-07-14): one ADU, attached or detached, by staff certificate, in all districts allowing 1-2 family homes; owner-occupied; detached 900 sq ft. The pre-2025 rule rested on an unverifiable snippet and is not coded. |
| Miami Co. uninc. (39109) | 5.7 | `-2016` | County zoning resolution (8 of 12 townships, ~75%). A second one-family dwelling or mobile home as a CUP in A-2 only (`coverage_zones` A-2). It is a second full house, not a subordinate unit. |
| Mentor (3949056) | 5.5 | `-2025-none` | Living quarters for servants or family (no rent), detached only for guests/servants on >1 acre → no ADU (family-only). Row starts at the latest amendment (Ord. 24-O-072, 2025-03-18). |
| Parma (3961000) | 5.4 | `-2016-none` | No ADU: single-family districts allow nothing "other than single-family detached dwellings". |
| Avon Lake (3903464) | 5.4 | `-2022-none` | No ADU from the 2022 code (unlisted uses prohibited). 2016-2021 not coded (old code not readable). |
| Violet Twp (3904580206) | 5.3 | `-2016-none` | Accessory dwelling only as a guest house or for relatives or household staff → no ADU (family-only). A 2022-25 amendment dropped detached garage apartments; same coding. |
| Mansfield (3947138) | 5.1 | `-2016-none` | No ADU: one principal building; unlisted uses prohibited. |
| Vermilion (3979716) | 5.0 | `-2016-none` | No ADU: exclusive district use lists. |

## Ohio: places skipped (19)

**County unincorporated areas: not codable as one rule.** Shares are Census 2020 housing units in each township's
unincorporated part (a stand-in for single-family lots).

| County (geoid) | Added | Why |
|---|---|---|
| Delaware (39041) | 24.6 | 15 of 18 townships zone themselves; county zoning ~2%. Largest: Orange ~24%. |
| Hamilton (39061) | 23.1 | County code covers Columbia, Harrison, most of Green and Miami: ≤ ~28%. Colerain ~21%, Anderson, Springfield, Delhi zone themselves. |
| Montgomery (39113) | 17.6 | Washington ~30%, Miami ~27%, plus Jackson, German, Jefferson zone themselves. |
| Warren (39165) | 16.7 | County code 5 townships ~28%; Deerfield ~33% (own code since 1997), Hamilton ~19%. |
| Butler (39017) | 16.7 | County code 6 townships ~19%; West Chester ~36%, Liberty ~22%. |
| Clermont (39025) | 13.8 | No county zoning; largest Union ~29%. |
| Stark (39151) | 10.2 | No county zoning found; largest Jackson ~22%. |
| Medina (39103) | 9.5 | No county zoning found; largest Montville ~14%. |
| Summit (39153) | 9.4 | No county zoning; largest Copley ~28%. |
| Greene (39057) | 8.2 | 12 township resolutions; largest Sugarcreek ~26%. |
| Lake (39085) | 7.8 | Townships zone themselves; Concord ~36%, Painesville ~33%. |
| Geauga (39055) | 7.5 | 16 township codes; largest Auburn ~10%. |
| Portage (39133) | 7.5 | 18 township codes; largest Ravenna Twp ~13%. |
| Lucas (39095) | 7.2 | Sylvania ~35%, Springfield ~30%, Monclova ~16%, each its own code. |
| Union (39159) | 7.1 | Township codes; largest Jerome ~24%. |
| Wayne (39169) | 7.1 | No county zoning, much of it unzoned; largest Chippewa ~13%. |
| Licking part (39089) | 6.4 | 20 of 26 townships zone themselves, 6 unzoned; largest Etna ~14%. |
| Wood (39173) | 5.6 | No county zoning; largest Perrysburg Twp ~34%. |

**Solon (3972928, 5.7):** code text not reachable (American Legal only, blocked; no other copy).

Researched past the 20 but not added (kept for a later round in the shared notes folder): Massillon (no ADU),
Aurora (no ADU), Stow (ADUs by right from 2026-02-09, pre-2026 unknown), North Ridgeville (no ADU), North Olmsted
(no ADU). Unsettled: Canton, Fairfield (code not reachable), Pickerington, Reynoldsburg (ADU defined but not listed
in any district).

## Minnesota: places coded (20)

| Place (geoid) | Added | Rows | Rule |
|---|---|---|---|
| Mankato (2739878) | 15.3 | `-2016-none` | No ADU: R-1 allows one-family homes only; no ADU use anywhere (implicit: no "unlisted uses prohibited" clause found). |
| Blaine (2706382) | 12.7 | fix + `-2026` | See above. |
| Moorhead (2743864) | 10.9 | `-2016-none` | No ADU, explicit: "Dwelling unit, accessory" row blank in every district, "Blank = Prohibited". |
| Crow Wing Co. uninc. (27035) | 8.6 | `-2016` | Guest cottage/quarters (may have a kitchen) permitted with a land use permit in all districts allowing single-family homes; 1 per lot; 700 sq ft shoreland, 900 off shoreland (coded 700). |
| Prior Lake (2752594) | 6.8 | `-2016-none` | Accessory apartment limited to immediate family or caregivers → no ADU (family-only). |
| Oak Grove (2747690) | 6.7 | `-2016-none`, `-2022` | No ADU until Ord. 22-05 (2022-10-10): one internal or detached ADU ≤ 700 sq ft, building permit only, owner-occupied, +1 space, in A, LG-1, LG-2, MPGCC, SFR. |
| Otsego (2749138) | 6.6 | `-2016`, `-2021` | Internal secondary unit by administrative permit in R-4A, R-4, R-5, R-6; from 2021-05-24 also detached in A-1/A-2 (5+ acres, ≤ 1,200 sq ft). A 2022 Ramsey peer-city memo says "ADU's not allowed"; the code text is used. |
| Minnetrista (2743306) | 6.5 | `-2016-none` | Guest apartments / guest homes for the household, unpaid guests or domestic staff only; renting prohibited → no ADU (no-rental). |
| Lino Lakes (2737322) | 6.2 | `-2016` | Internal accessory apartment by staff permit in all single-family districts; owner-occupied; 40% or 960 sq ft. |
| Lake Elmo (2734244) | 5.6 | `-2016` | Secondary dwelling by CUP in GCC, LDR, MDR, HDR, V-LDR, VMX, MU-C, MU-BP; owner-occupied; detached 1,000 sq ft; not in rural districts (the A district's "secondary dwelling" is a separate house on its own parcel). |
| Victoria (2767036) | 5.4 | `-2017` | ADU by CUP in R-1, R-1A, R-2; detached allowed; +1 space. From 2017-05-22 (Ord. 415); 2016 not coded. |
| Sherburne Co. uninc. (27141) | 4.8 | `-2016-none`, `-2025` | No ADU until Ord. 284 (2025-04-26): ADU permitted in A and GR, owner's or relative's homestead. Ord. 292 (2026) reportedly extends it to more districts; only the draft was readable, so not coded. |
| Shoreview (2759998) | 4.6 | `-2016` | Internal accessory apartment in an owner-occupied house, approved by the city manager, RE and R1; 800 sq ft / 30%. |
| North Mankato (2747068) | 4.5 | `-2016-none` | No ADU: R-1, R1-S single-family only. |
| Corcoran (2713168) | 4.1 | `-2021` | ADU by administrative permit in all residential districts (Ord. 445, 2021-12-22); owner-occupied; 960 sq ft; detached allowed; +2 spaces. Pre-2021 not coded. |
| St. Louis Co. uninc. (27137) | 4.1 | `-2016-none` | Ord. 62 accessory dwelling may not be used for rental → no ADU (no-rental). 2025-26 amendments not readable. |
| Mahtomedi (2739428) | 3.9 | `-2019` | ADU by CUP in RR and R-1; lot ≥ 10,000 sq ft; < 960 sq ft and ≤ 33%; +1 space. From 2019-09-18 (earliest Wayback copy). |
| St. Michael (2757346) | 3.9 | `-2024-none` | No ADU (Ord. 2402, 2024-12-10): accessory buildings and basements may not be separate dwelling units. 2016-2024 not coded. |
| Cass Co. uninc. (27021) | 3.7 | `-2016`, `-2016a` | Guest quarters with a permit on large lots (2.5 ac off shoreland) until 2016-09-02; then an ADU permitted on any conforming lot (700 sq ft shoreland). Second pass could not reach the county site. |
| Elk River (2718674) | 3.7 | `-2022` | ADU a listed accessory use in R-1a to R-1d with a building permit; owner-occupied; 1,000 sq ft; +1 space. Standards from a 2022 Ramsey peer-city memo (code site blocked). |

## Minnesota: places skipped (2)

| Place (geoid) | Added | Why |
|---|---|---|
| Itasca Co. uninc. (27061) | 5.7 | Not settled: "guest cottage" is defined but listed in no district; in shoreland unlisted uses are prohibited, elsewhere they go to a CUP. |
| Chaska (2710972) | 4.3 | Zoning district chapter not reachable; a city FAQ says "Generally, no" except in Clover Ridge. |

Also researched (kept in the shared notes folder for a later round): Isanti Co. (ADUs from 2022-03-15), Wright Co.
(no ADU), Douglas Co. (guest cottage without cooking: no ADU), Owatonna (internal ADUs by right from 2019),
Independence (relatives only: family-only), Brooklyn Center (ADUs from 2022-12-12), Waconia (R-2 internal only),
East Bethel (not settled), Todd and Kandiyohi counties (ordinances not reachable).

## Family-only coded as no-ADU (Fort Worth convention)

At the ADU session's request, a unit that only family, guests or household staff may occupy, or that may not be
rented, is coded `adus_per_lot` 0 with `by_right` False, following `TX-4827000-adu-2010` (Fort Worth): the engine
reads Handbook ADUs as rentable units. Each row is tagged `[family-only]` or `[no-rental]`, quotes the restriction,
and records in its notes the fields the text gives if the unit were counted, so the convention can be revisited as a
whole.

| Row | Place | Restriction |
|---|---|---|
| OH-39049-adu-2016-none | Franklin County (county zoning) | Granny flat occupied only by the owner's family (Sec. 302.039) |
| OH-3949056-adu-2025-none | Mentor | Quarters for servants or family, no consideration charged (§1157.02) |
| OH-3904580206-adu-2016-none | Violet Township | Guest house, relatives of the owner or household servants (Sec. 3AA4-05) |
| MN-2752594-adu-2016-none | Prior Lake | Immediate family or caregivers |
| MN-2743306-adu-2016-none | Minnetrista | Household, unpaid guests or domestic staff; renting prohibited |
| MN-27137-adu-2016-none | St. Louis County | Not for commercial or rental purposes (Ord. 62) |

## How this was checked

- **Research:** seven research passes (Claude subagents) read the current codes on Zoneomics mirrors, city and
  county PDFs, American Legal and Municode where reachable, and older text on the Wayback Machine. Bot checks,
  CAPTCHAs and sign-ins were not bypassed; American Legal and several county sites refused automated reads, which
  is why some places are skipped and some rows start late.
- **Second pass:** an independent pass re-opened every row's source and checked the quote and the key coding. Ohio:
  20 of 23 rows confirmed; corrections applied (Mentor family-only; Delaware pre-2025 row dropped; Westerville
  owner occupancy blanked). Minnesota: corrections applied to Blaine (detached → False), Crow Wing (900 → 700 sq
  ft), Lino Lakes (unverified parking blanked), Otsego (parking count blanked; detached only in A districts),
  Sherburne (draft-only 2026 row dropped), Lake Elmo (zone list completed after reading every use table), and the
  family/no-rental rows above. Rows the second pass could not reach (Oak Grove 2016, Sherburne, St. Louis, Cass) say
  so in `verified_by`.
- **County shares:** Census 2020 DHC housing units for each township's unincorporated part, pulled with the
  project's Census API key into the session scratchpad (nothing in the repo).
- **Engine read:** with the new rows, all 40 places have a live ADU row at 2025-12-31 and at 2026-11-15
  (`scenarios.adu._live`).
- `pytest tests -k reform`: 99 passed. `python compliance_check.py`: 0 FAIL.

### Coverage audit (`scripts/archive/adu_coverage_audit.py`, rerun into `reports/adu-coverage-audit/`)

| | Before | After |
|---|---|---|
| ADU rows | 582 | 626 |
| blank | 4 | 4 (the same rows; **no new blank rows**) |
| area_text_citywide | 106 | 110 |
| zones_switch | 31 | 29 |
| strong | 32 | 32 |

The +4 `area_text_citywide` come from five new rows that name their districts while covering every single-family
district (Cass 2016a, Crow Wing, Corcoran, Lino Lakes, Delaware), minus Blaine's moratorium row. The −2
`zones_switch` are Blaine's two rows: the moratorium row is now an explicit no-ADU rule.

### Tests

Two reform tests guard which places may appear: `tests/states/oh/test_reforms.py` lists Ohio's coded places (a new
`UNCODED_2026_11` set is added), and `tests/states/mn/test_reforms.py` only allowed 7- and 10-digit geoids (now also
5-digit county remainders, as NC and OR already have). No test logic changed.

## Open for the ADU session and Ben

1. The moratorium-as-no-ADU convention (Blaine).
2. The family-only convention, applied to six rows here.
3. Rows that start after 2016 because the earlier rule couldn't be read: Westerville 2024, Powell 2017, Avon Lake
   2022, Mentor 2025, Delaware 2025, Victoria 2017, Corcoran 2021, Mahtomedi 2019, St. Michael 2024, Elk River 2022.
   Those places read as uncoded before their first row.
4. Ohio's county remainders: 18 of them hold 206 added ADUs a year and can't be one rule. Splitting them into
   township places would be a geography change, not a coding one.
