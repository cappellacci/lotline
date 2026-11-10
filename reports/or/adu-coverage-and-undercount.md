# Oregon ADU counts: coverage, the flag undercount, and more places (D-074 steps for Oregon)

*WS-OR data thread, 2026-11-10. Descriptive counts only; no engine, scenario, calibration or fit run. The V9
holdout (`V9-OR-TRANSFER`) was released on 2026-11-05; every permit table here is still read through
`holdout.apply`. Copies North Carolina's steps (D-074, cappellacci/lotline#358; Raleigh's k in
`reports/nc/wake-roll-adu-diff.md`; the parser hand check in `reports/nc/charlotte-adu-counts.md`).*

## Bottom line

- **Portland and Bend, the two places with ADU-flagged permits, hold 16.9% of Oregon's ADU-eligible lots**
  (197,137 of 1,164,771). Portland alone is 14.0%. The other 83% (Salem, Eugene, the county remainders, the
  Metro suburbs and every small city under SB 1051) has no ADU count yet.
- __K_LINE__
- __PLACES_LINE__
- __STATE_LINE__

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
