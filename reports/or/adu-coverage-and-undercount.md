# Oregon ADU counts: coverage, the flag undercount, and more places (D-074 steps for Oregon)

*WS-OR data thread, 2026-11-10. Descriptive counts only; no engine, scenario, calibration or fit run. The V9
holdout (`V9-OR-TRANSFER`) was released on 2026-11-05; every permit table here is still read through
`holdout.apply`. Copies North Carolina's steps (D-074, cappellacci/lotline#358; Raleigh's k in
`reports/nc/wake-roll-adu-diff.md`; the parser hand check in `reports/nc/charlotte-adu-counts.md`).*

## Bottom line

- **Portland and Bend, the two places with ADU-flagged permits, hold 16.9% of Oregon's ADU-eligible lots**
  (197,137 of 1,164,771). Portland alone is 14.0%. The other 83% (Salem, Eugene, the county remainders, the
  Metro suburbs and every small city under SB 1051) has no ADU count yet.
- **The flag undercount k in Portland is 1.06 (90%: 1.05–1.07); 1.07 (1.06–1.08) as written.** The
  independent list is Metro's RLIS Housing inventory (ADUs found by the assessor, the address file, field
  checks), matched to Portland's flagged permits by tax lot (§2). It agrees with Raleigh's 1.07.
- **Two new places with open record-level permits: Salem (via the Mid-Willamette Valley COG) and Medford.**
  2021–23 flagged ADUs per 1,000 lots a year: Salem 0.87, Medford 1.75 (Portland 1.52, Bend 2.14). Coverage
  rises to 22.5%. Keizer and unincorporated Marion are only partly in the COG file. Salem's own permit data
  bars copying; Eugene's is behind a bot check and "all rights reserved"; Jackson County needs a city
  assignment (§3).
- **No open state ADU table by year.** DLCD's housing production survey is dashboard-only; one OHCS layer
  has ADUs by city for 68 cities but no year field (§3.5).

## 1. Coverage audit

`scripts/dev/or_adu_coverage.py`. Eligible lots are theme `adu` at the current rule version, taken the way
`adu.places_from_store` takes them for origin 2026: the newest count at or before 2026. That is the RLIS tax
roll (2026) for the 27 Metro jurisdictions and the ACS fallback (2024) for the other 141. The units are made
non-overlapping with `adu.non_overlapping`. In Oregon this removes nothing: every one of the 168 jurisdictions
is in BPS (`in_bps` True), so no county remainder holds a local-only place's homes (raw sum and
non-overlapping sum are both 1,164,771).

| Lots from | Jurisdictions | Eligible lots |
|---|---:|---:|
| RLIS parcels, 2026 (Metro) | 27 | 468,769 |
| ACS single-family fallback, 2024 | 141 | 696,002 |
| **All** | **168** | **1,164,771** |
| Covered by ADU-flagged permits (Portland, Bend) | 2 | 197,137 (16.9%) |

### The 25 largest places by eligible lots

| # | Place | GEOID | Eligible lots | Share | Cumulative | Lots from | ADU-flagged permits? |
|---:|---|---|---:|---:|---:|---|---|
| 1 | Portland city | 4159000 | 163,638 | 14.0% | 14.0% | parcels 2026 | **yes** (`IS_ADU`) |
| 2 | Washington County Unincorporated Area | 41067 | 66,712 | 5.7% | 19.8% | parcels 2026 | no |
| 3 | Clackamas County Unincorporated Area | 41005 | 49,439 | 4.2% | 24.0% | parcels 2026 | no |
| 4 | Salem city | 4164900 | 41,427 | 3.6% | 27.6% | ACS 2024 | no |
| 5 | Eugene city | 4123850 | 41,188 | 3.5% | 31.1% | ACS 2024 | no |
| 6 | Lane County Unincorporated Area | 41039 | 34,201 | 2.9% | 34.1% | ACS 2024 | no |
| 7 | Bend city | 4105800 | 33,499 | 2.9% | 36.9% | ACS 2024 | **yes** (`BldgUse` ADU) |
| 8 | Deschutes County Unincorporated Area | 41017 | 30,317 | 2.6% | 39.5% | ACS 2024 | no |
| 9 | Douglas County Unincorporated Area | 41019 | 26,451 | 2.3% | 41.8% | ACS 2024 | no |
| 10 | Hillsboro city | 4134100 | 25,571 | 2.2% | 44.0% | parcels 2026 | no |
| 11 | Gresham city | 4131250 | 24,404 | 2.1% | 46.1% | parcels 2026 | no |
| 12 | Klamath County (remainder) | 41035 | 23,691 | 2.0% | 48.1% | ACS 2024 | no |
| 13 | Medford city | 4147000 | 23,399 | 2.0% | 50.1% | ACS 2024 | no |
| 14 | Jackson County Unincorporated Area | 41029 | 20,467 | 1.8% | 51.9% | ACS 2024 | no |
| 15 | Beaverton city | 4105350 | 20,345 | 1.7% | 53.6% | parcels 2026 | no |
| 16 | Marion County Unincorporated Area | 41047 | 20,286 | 1.7% | 55.4% | ACS 2024 | no |
| 17 | Josephine County Unincorporated Area | 41033 | 16,427 | 1.4% | 56.8% | ACS 2024 | no |
| 18 | Tigard city | 4173650 | 15,664 | 1.3% | 58.1% | parcels 2026 | no |
| 19 | Springfield city | 4169600 | 14,497 | 1.2% | 59.4% | ACS 2024 | no |
| 20 | Albany city | 4101000 | 13,624 | 1.2% | 60.5% | ACS 2024 | no |
| 21 | Coos County Unincorporated Area | 41011 | 13,115 | 1.1% | 61.7% | ACS 2024 | no |
| 22 | Lake Oswego city | 4140550 | 12,221 | 1.0% | 62.7% | parcels 2026 | no |
| 23 | Corvallis city | 4115800 | 12,140 | 1.0% | 63.8% | ACS 2024 | no |
| 24 | Grants Pass city | 4130550 | 11,752 | 1.0% | 64.8% | ACS 2024 | no |
| 25 | Oregon City city | 4155200 | 10,964 | 0.9% | 65.7% | parcels 2026 | no |

Caveats. (1) The ACS fallback counts single-family homes, not lots; the RLIS count is tax lots. The two
are not the same measure, so the shares mix them. (2) Klamath County's remainder includes Klamath Falls,
which is not in the BPS universe (`docs/build/or-readiness.md` §1). (3) A county remainder covers only the
land the county permits (outside city limits); most of it is outside urban growth boundaries, where HB 4031
§7 limits the state ADU rule.

### ADU-flagged permits in the covered places (context, not new)

ADU-flagged permits by issue year, per 1,000 eligible lots (the 2026 lots above, so early years are
approximate). 2026 is partial (to the 2026-09-12 Portland extract and the 2026-11-05 Bend download).

| Year | Portland | per 1,000 lots | Bend | per 1,000 lots |
|---|---:|---:|---:|---:|
| 2016 | 549 | 3.35 | 45 | 1.34 |
| 2017 | 518 | 3.17 | 47 | 1.40 |
| 2018 | 593 | 3.62 | 59 | 1.76 |
| 2019 | 341 | 2.08 | 66 | 1.97 |
| 2020 | 241 | 1.47 | 56 | 1.67 |
| 2021 | 251 | 1.53 | 68 | 2.03 |
| 2022 | 275 | 1.68 | 84 | 2.51 |
| 2023 | 221 | 1.35 | 63 | 1.88 |
| 2024 | 178 | 1.09 | 37 | 1.10 |
| 2025 | 160 | 0.98 | 51 | 1.52 |
| 2026 (partial) | 78 | 0.48 | 27 | 0.81 |

Both are far above NC's flagged rates (D-074: Durham 0.73, Raleigh 0.47 per 1,000 a year, 2021–24).

## 2. The flag undercount k in Portland (D-074 step 1)

### 2.1 Is there an independent list?

- **No second RLIS roll.** Metro publishes only the current tax-lot roll (2026). The quarterly "Taxlots Change"
  layer holds geometry changes only, university geoportals hold 2001 and 2006 snapshots, and the state's
  2017–2021 taxlot files are internal. So NC's two-roll diff can't be copied.
- **Multnomah County's assessor files** (DART improvements and land) are sold, and PortlandMaps' taxlot layer
  has a `UNITS` field but no license and only the current vintage. Not usable openly.
- **Portland's own ADU lists** (the BDS "Residential ADU Permit" layer, accessorydwellings.org totals) are
  built from the same permits, so they can't check them.
- **Metro's RLIS Housing inventory is usable.** `Housing/FeatureServer/11` is "an inventory of all housing
  units in the tri-county region", one row per tax lot and unit type, with `UNIT_TYPE` = ADU, the tax lot
  (`TLID`), `JURIS_CITY` and, for each row, the `DATASOURCE` it was built from (updated 2026-10-31). License:
  the RLIS Open Database EULA, the same terms as `rlis_parcels` (attribution only). Most of its ADU rows come
  from sources other than permits: the Multnomah County Assessor, RLIS tax lots, Metro's Master Address File,
  field checks, other cities. Those rows are the independent list R. It is a **cross-section** (the stock in
  October 2026), not a diff of two rolls, so the comparison runs over the whole permit history.
- What was seen before this rule was written: the layer's field list, its distinct `DATASOURCE`,
  `CONFIDENCE`, `UNIT_SUBTY` and `UNIT_TYPE` values, three sample rows, and the source scout's aggregate counts
  of Portland ADU rows by `YEARBUILT` and by `DATASOURCE` (4,991 Portland ADU rows; 1,818 from "City of
  Portland Building Permits"). **No match between the inventory and Portland's permits had been counted.**
  The three sample rows show that `YEARBUILT` is sometimes the main house's year (1928 on an assessor ADU
  row), so the rule does not use it to set a window.

### 2.2 Detection rule (written and committed before any count)

- **R (independent ADU list).** RLIS Housing rows with `UNIT_TYPE` = `ADU` and `JURIS_CITY` = `Portland`
  whose `DATASOURCE` is **not** permit-based. Permit-based sources: "City of Portland Building Permits" and
  "METRO - Building permit data". "METRO - Accesory Dwelling Unit Study" (the source's spelling) is of unknown
  origin; it stays in R, and a sensitivity drops it. Counted by tax lot (a lot with two ADU rows counts once).
- **P (flagged permits).** Portland ADU-flagged permits (`adu_type` set in `portland_permits`), issued
  1995-01-01 to 2025-12-31. 2026 permits are left out for completion lag (the inventory is dated 2026-10-31).
  Counted by tax lot.
- **Matching key.** Both sides use the map-and-taxlot number. RLIS `TLID` (`1S2E22BA  -03305`) and Portland's
  `PROPGISID1` (`1S1E21DC 13300`) become `MAP-LOT`: upper case, spaces and hyphens dropped, the map part
  (township, range, section, quarter, quarter-quarter: `1S2E22BA`) kept, and the lot number's leading zeros
  stripped (`3305`). A key that doesn't fit the pattern is dropped and counted.
- **Groups.** For each lot in R but not in P:
  - **(a) permitted but unflagged:** the lot has a Portland permit for new residential building (any row of
    `portland_permits`, which holds only permits that create units) issued 1995–2025 that is not ADU-flagged.
    **Central:** only house-type permits (SFD, TH, OTHER, UNKNOWN) count. Duplexes and multi-unit permits
    (U2, U3_4, MF5) are rebuilds into two or more units, not ADUs, and are left out, as in NC's deviation.
    **As written:** every unflagged permit counts.
  - **(b) unpermitted or not found:** no such permit. Reported, not used in k. It includes ADUs older than
    the permit file (1995) and any ADU filed under a permit that creates no unit.
- **Reported:** |R|, |P|, |P ∩ R|, |a| (central and as written), |b|, |P \ R|, k =
  (|P ∩ R| + |a|) / |P ∩ R| with the 90% Wilson interval (`wake_roll_diff.k_undercount`), and the Chapman total
  (`wake_roll_diff.chapman`) as a lower-bound check.
- **Sensitivities, fixed now:** (i) R without the "ADU Study" rows; (ii) R restricted to rows with
  `CONFIDENCE` HIGH; (iii) R and P restricted to 2016–2025 by permit issue year on the P side and to rows with
  `YEARBUILT` 2016 or later on the R side (shown though `YEARBUILT` is unreliable).
- **Known weaknesses.** (1) The inventory is not fully independent of permits: the Master Address File gets
  new addresses when permits are issued, so an ADU found through it is more likely to also have a permit. k
  and the Chapman total are therefore lower bounds. (2) Tax lots split or renumbered since a permit was issued
  won't match (inflates P \ R and |b|). (3) The permit layer holds only permits that create units, so an ADU
  filed as an alteration without a new unit is in (b), not (a).

### 2.3 Results

*Rule committed in ba8a8b7d (pushed) before the first count. Counts from `uv run python
scripts/dev/or_portland_adu_k.py` (aggregates in `reports/or/portland-adu-k.json`; no tax-lot table is
written). Functions and tests: `src/lotline/adapters/checks/rlis_housing.py`,
`tests/adapters/test_rlis_housing.py`. The inventory was downloaded on 2026-11-10 through the IO layer (6,077
ADU rows in the three counties; 4,991 in Portland).*

**Portland's k is 1.06 (90%: 1.05–1.07); as written, 1.07 (1.06–1.08).** Both lower bounds are above 1, so
D-074 step 4 triggers for Oregon as it did for NC. Raleigh's central k was 1.07 (1.02–1.21): the two cities
agree, and Portland's interval is much narrower because it rests on about 2,000 matched lots instead of 30.

| | Central | No "ADU Study" rows | HIGH confidence only | 2016 on |
|---|---:|---:|---:|---:|
| R: lots with an ADU from a non-permit source | 2,978 | 2,958 | 1,056 | 2,184 |
| P: lots with a flagged ADU permit (window) | 4,576 | 4,576 | 4,576 | 3,143 |
| P ∩ R | 1,949 | 1,932 | 590 | 1,628 |
| (a) permitted but unflagged, house types (central) | 114 | 114 | 42 | 59 |
| (a) as written (any unflagged new-unit permit) | 138 | 138 | 59 | 60 |
| (b) unpermitted or not found | 891 | 888 | 407 | 496 |
| P \ R | 2,627 | 2,644 | 3,986 | 1,515 |
| **k central (90%)** | **1.06 (1.05–1.07)** | 1.06 (1.05–1.07) | 1.07 (1.06–1.09) | 1.04 (1.03–1.05) |
| k as written (90%) | 1.07 (1.06–1.08) | 1.07 (1.06–1.08) | 1.10 (1.08–1.13) | 1.04 (1.03–1.05) |
| Chapman total (95%) | 6,991 (6,853–7,129) | 7,005 | 8,185 | 4,216 |

Window: P is flagged permits issued 1995–2025; the "2016 on" column uses permits issued 2016–2025 and R rows
with `YEARBUILT` 2016 or later. Lots that could not be keyed: 129 Portland inventory rows (123 with a blank
`TLID`, 6 with a malformed one) and 244 Portland permit rows (54 blank, the rest map numbers missing the range
direction, e.g. `1S124DC`). Both are left out, as the rule says.

What the groups say:
- **Group (a), 114 lots.** Lots with a non-permit ADU in the inventory and a new house-type permit that is not
  flagged. Some are ADUs the flag missed; some are a new main house on a lot whose ADU came earlier or without
  a permit. Only 24 more lots have just a duplex or multi-unit permit (as-written minus central).
- **Group (b), 891 lots (30% of R).** Inventory ADUs with no permit at all in the file. These are ADUs built
  before 1995, conversions filed under permits that create no unit, and unpermitted units. D-074 reports them
  and doesn't add them to k: the model's outcome is permits, and A12's formalization share covers the rest. A
  share this large is worth its own entry if the formalization share is revisited.
- **P \ R, 2,627 lots.** 1,705 of them are in the inventory through its permit-based rows, as expected. **922
  flagged lots (20% of P) are not in the inventory at all**: permits never built or not yet finished, ADUs
  the inventory missed, or tax lots renumbered since the permit.
- **The Chapman total is not a lower bound here.** NC's two-list total was a lower bound because the roll and
  the permits are positively dependent. Here R was built by *excluding* the inventory's permit-sourced rows,
  so a permitted ADU is less likely to be in R: the dependence is negative and the Chapman total (about 1.5
  ADUs per flagged lot) overstates. It is shown only because D-074 asks for it.

**Caveats.** (1) Same as NC: k corrects only for ADU permits the flag misses. (2) The Master Address File
gains an address when a permit is issued, so some "independent" rows trace back to permits; that pushes
P ∩ R up and k down. (3) `IS_ADU` is a field flag, so Portland's k is a field-flag k, like Raleigh's.

**A second check on the flag, from Portland's own text.** Before the count above, the permit file's
descriptions (`FOLDER_DES`, read in memory and not kept) were run through Cary's ADU rule
(`cary_permits.adu_from_text`) for 2016–2025: 3,188 permits are both flagged and named as ADUs in the text,
141 are flagged without the text naming one, and **80 name an ADU but are not flagged** (2.4% of the 3,268
named). Most of the 80 are new-house permits that cite the separate ADU permit by number ("DETACHED ADU
19-172508-RS"), which is itself flagged; a few are real misses (basement conversions, townhouses with an
attached ADU). So within the file the flag misses at most about 2%, in line with k.

## 3. More places (D-074 step 2)

### 3.1 What was found

Scouted on 2026-11-10 (ArcGIS REST metadata and count queries; no bulk download except the two adapters
below). For each of the uncovered places in §1's top 25:

| Place (rank) | Source | Verdict |
|---|---|---|
| **Salem (4)** | **MWVCOG "Residential Building Permits since 1998"** (source: Mid-Willamette Valley Council of Governments) (`Permits_online/FeatureServer/0`): 19,332 permits for Salem, Keizer, Turner and unincorporated Marion and Polk, with the COG's own ADU type from 2018 | **Adapter built** (`mwvcog_permits`). No license stated |
| Salem (4) | City of Salem "Structure Permits" (`Structure_Permits/FeatureServer/0`) | **Blocked by its terms**: "copying and selling the data is prohibited". It also holds only a rolling year (669 rows from 2025-11-25). Not used |
| **Medford (13)** | **City of Medford TRAKiT export** (`TRAKiTPermits_service/FeatureServer/1`): 28,063 permits since 2020, ADU subtypes, tax lot | **Adapter built** (`medford_permits`). No license stated; hub disclaimer only |
| Medford (13) | City of Medford "Housing Production" layer (2,428 rows, `HOUSING_TYPE` ADU) | City-derived count; used as a check below |
| Keizer, Marion County remainder (16) | In the MWVCOG file | Partly covered (below) |
| Jackson County remainder (14) | Jackson County "Permits - Building" (252,636 rows since 1989, weekly) | **Scouted, not built.** No ADU type (text only, 154 rows naming an ADU, trade permits included) and no jurisdiction field: the county also permits several small cities, and only the street address says which. Placing permits would mean reading addresses or joining coordinates to city limits. Worth doing in a later pass |
| Eugene (5) | Permit reports with an Excel export on pdd.eugene-or.gov; the site says "All rights reserved"; eugene-or.gov is behind a bot check | **Blocked** (terms and bot check). A request to the city would be needed; Ben doesn't file records requests |
| Hillsboro (10), Gresham (11), Beaverton (15), Tigard (18), Springfield (19), Albany (20), Lake Oswego (22), Corvallis (23), Grants Pass (24), Oregon City (25) | Monthly PDFs (Hillsboro), web lookups (Gresham), a down server with two years of active permits (Tigard), a "Data Services Agreement" (Springfield), or nothing found | **No open record-level source** |
| Washington (2), Clackamas (3), Lane (6), Deschutes (8), Douglas (9), Klamath (12), Josephine (17), Coos (21) county remainders | Lane's Accela layer returns 0 rows; Deschutes' CivicData packages are listed but their files return "not found"; the others have nothing open | **No open record-level source** |

**A note on terms.** Neither new source states a license; neither restricts reuse. That is the same footing
as Portland's permits (`config/states/or.yaml`). The records stay in `LOTLINE_DATA_DIR`; only counts are
published. MWVCOG's file holds Salem's permits, whose own city layer bars copying; the COG is a different
publisher and states no such term.

**MWVCOG terms, checked 2026-11-10 (Ben's decision: keep Salem's counts).** The ArcGIS Online item
(`a790b37ed6554a78957df0084f04b45b`, owner `ksapunar_MWVCOG`, public) has an empty `licenseInfo`, and its
`accessInformation` is only "www.mwvcog.org". mwvcog.org shows a Cloudflare bot check, so Claude did not read
it; Ben checked the site by hand the same day and found no terms of use. **Status: no license and no
restriction, the same footing as Portland's and Medford's permits.** Salem's numbers carry attribution to the
Mid-Willamette Valley Council of Governments wherever they are shown. Salem's ADU rule date (§4) stays DATE
UNCONFIRMED.

### 3.2 Checks of the new sources

- **Salem against Census BPS.** MWVCOG's new single-family houses in Salem match BPS one-unit permits within
  2% in 11 of the 14 years 2010–2023 (2015: 202 vs 271; 2017: 227 vs 319; 2023: 396 vs 360). **2024 and 2025
  are incomplete** (219 and 258 vs 392 and 364): about 170 rows of 2024 have no city, office or permit
  number, and are dropped.
- **Keizer and the Marion County remainder are only partly in the file.** Keizer's houses run at 30–90% of
  BPS, and the Marion remainder's at 10–50% (the COG file seems to cover the Salem-Keizer urban area, not the
  whole county). Their counts below are floors, and **neither enters the panel**: the adapter keeps only
  Salem by default (`mwvcog_permits.KEEP`), so the processed table holds Salem's 13,923 permits and nothing
  else, and the floors below come from `build(raw, keep=None)` in the report script.
- **Medford against BPS.** New houses (SFD + TH) are 75–85% of BPS one-unit permits in 2020–2025. The rest are
  probably master-plan houses with unmapped subtypes; ADUs are unaffected.
- **Medford against the city's own Housing Production layer** (ADU units by issue year, read from the
  scout): 8, 31, 37, 47, 38, 24 for 2020–2025, against this adapter's 6, 32, 37, 54, 52, 32. The city's layer
  seems to count completed ADUs; ours counts issued permits, including expired ones.
- **Salem's ADU type starts in 2018.** No MWVCOG row is typed ADU before 2018, so Salem's ADUs before 2018 are
  unknown, not zero (Salem may have filed them as NSFD or not allowed them; see §4).

### 3.3 Hand check of the ADU flags (30 matches, 30 non-matches)

Both new sources use a field flag, not a parser, so D-074's k_parser doesn't apply; the hand check tests the
flag's precision and whether non-flagged permits hide ADUs.

- **Medford.** First sample (30 flagged, 30 not flagged from new, remodel and remodel-addition permits): all
  30 non-flagged were not ADUs. Of the 30 flagged, 28 were new ADUs; 2 were remodels of an existing ADU
  (a fire repair, a car-crash repair). The look-up also showed that "master with ADU" permits are a house
  plus an ADU, not an ADU alone. **The rule was changed after this sample** (a remodel or addition permit
  with an ADU subtype is not a new ADU; master-with-ADU permits are split into two rows), and a second sample
  of 30 flagged permits drawn after the change was **30 of 30 new ADUs** (some legalize an existing unit,
  which counts as a permit). Text scan of every non-flagged Medford permit with Cary's rule: 18 hits, 15 of
  them the house half of a split permit (expected), 1 a solar permit on an ADU, 1 a life-safety inspection,
  and **1 a real miss** ("legally recognize as an ADU" under a special-inspection permit).
- **Salem (MWVCOG).** The file has no description (only the type code), so a text check isn't possible. The
  type is the COG's own coding from Salem's permits. The BPS match above is the check on the file.

### 3.4 ADU permits per 1,000 eligible lots

`scripts/dev/or_adu_new_places.py` (through each adapter's `load`, so `holdout.apply`). Lots are §1's. "Not
co-built" applies D-041's rule (an ADU on a lot with a new house the same or next year is dropped); it needs a
tax lot, so it is computed for Medford only. Field-flagged, so Portland's k (§2) would apply if Ben extends it.

| Year | Salem (41,427 lots) | per 1,000 | Medford (23,399 lots) | not co-built | per 1,000 | Keizer (9,696) floor | Marion rem. (20,286) floor |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 8 | 0.19 | — | — | — | 0 | 1 |
| 2019 | 12 | 0.29 | — | — | — | 1 | 1 |
| 2020 | 67 | 1.62 | 6 | 6 | 0.26 | 2 | 0 |
| 2021 | 24 | 0.58 | 32 | 28 | 1.37 | 2 | 0 |
| 2022 | 28 | 0.68 | 37 | 36 | 1.58 | 2 | 1 |
| 2023 | 56 | 1.35 | 54 | 39 | 2.31 | 2 | 0 |
| 2024 (Salem partial) | 21 | 0.51 | 52 | 35 | 2.22 | 4 | 1 |
| 2025 (Salem partial) | 46 | 1.11 | 32 | 15 | 1.37 | 5 | 2 |
| 2026 (to Nov) | — | — | 23 | 21 | 0.98 | — | — |

Medford's file starts in January 2020, so before 2020 it is unknown. **2021–2023, flagged ADUs per 1,000 lots a
year: Salem 0.87, Medford 1.75**, against Portland 1.52 and Bend 2.14 over the same years (§1). Under one
statewide law (SB 1051), two mid-sized cities outside Portland land in the same range as the two places with
the strongest local ADU programs. Both qualify under D-074 step 2's 1,000-permit test (Salem 13,923 permits,
Medford 5,504).

### 3.5 State ADU reporting

- **DLCD's Housing Production Survey** (HB 4006 / ORS 197A.110, cities of 10,000+, from 2018; ADUs a separate
  category in its definitions) is published only through OHCS's Tableau and ArcGIS dashboards. DLCD's
  reporting page shows "under construction"; no CSV or spreadsheet by city and year was found. PSU's AHUPS
  survey replaced it in 2025.
- **One open layer exists:** OHCS's `OHNA_Cities_production_data_periods_1_2` (ArcGIS, 1,219 rows, 68 cities)
  has separate ADU rows by city ("Accessory Dwelling Unit to Single Detatched" and "... to Other"), but **no
  year field**: the values look like one survey period. Until the period is known, it can't be used as a
  count by year. If OHCS or DLCD confirms the periods (or publishes the yearly table), it would cover every
  city over 10,000 at once, including Eugene, Hillsboro, Gresham and Beaverton. That is the single most
  useful next step for Oregon, and it needs someone to ask OHCS; it is not a records request.

## 4. Proposed ADU rule rows (for Ben's review; `config/reforms/or.csv` not edited)

The state rows (`OR-<geoid>-adu-2018` SB 1051 and `-adu-2020` HB 2001) already exist for Salem, Medford,
Keizer and the Marion County remainder, so every new place has an accepted state rule. Local rows proposed:

| reform_id | Place | Theme | What | Dates | Source | Status |
|---|---|---|---|---|---|---|
| OR-4164900-adu-2021-local | Salem | adu | Salem's own ADU code (SRC 700.007; one ADU per lot, attached or detached) | Adopted May 2021 per a secondary source; effective date unconfirmed | Salem zone tables citing SRC 700.007 (https://www.cityofsalem.net/business/building-in-salem/middle-housing); secondary: https://www.northshorerealtors.com/news/salem-adu-ordinance-survey | **DATE UNCONFIRMED.** MWVCOG has ADU permits from 2018, so Salem allowed ADUs before May 2021 (under SB 1051 at least). Ben's agent should find the first ADU ordinance and the 2021 one |
| OR-4147000-fees-2020 | Medford | fees | ADU SDC Reduction Program: city parks, sewer, storm and street SDCs reduced for ADUs | Council Bill 2020-139, adopted 2020-11-19; in effect 2020-12-01 to 2023-06-30 | https://www.medfordoregon.gov/Government/Departments/Planning/ADU-SDC-Reduction | Partly verified (city page). `fee_change_usd` not known: the reduction share in 2020 isn't stated |
| OR-4147000-fees-2022 | Medford | fees | Extension: city SDCs for ADUs cut 50% (Council Bill 2022-44), the other 50% paid from ARPA funds (Council Bill 2022-43) | Adopted 2022-05-19; end 2023-06-30 unless renewed | same | Renewal after June 2023 unknown; the permit file still uses the "ADU REDUCED SDC" subtype in 2024–2026, which suggests it was renewed |

Medford's ADU zoning rules (MMC 10.821) and Keizer's own ADU code were not researched.

## 5. What this changes and what is open

- **k for Oregon.** Portland's k (1.06, 1.05–1.07) agrees with Raleigh's (1.07, 1.02–1.21). If Ben accepts it,
  the pooled field-flag k for the five-state refit could use both cities. MN, OH and TX are being measured by
  sibling sessions.
- **Coverage.** With Salem and Medford, ADU-flagged permits cover 261,963 of 1,164,771 eligible lots
  (**22.5%**, up from 16.9%). Every new place is outside Portland and under the statewide rule.
- **Open:** Salem's ADU rule dates, Jackson County (needs a city assignment), the OHCS
  production layer's survey period, and Eugene (no open source).
