# Charlotte pre-UDO parcels: options for a roll dated before 2023-06-01

*WS-NC research note, 2026-10-19 (round 3, task 4). Nothing was downloaded for this note: every date and count
below comes from layer metadata (`?f=json`), a `returnCountOnly` query or a statistics query on a layer that is
itself dated before the holdout window. A decision from Ben is needed before any fetch.*

## Why it matters

V5 (the Charlotte blind test) needs the number of lots that became N1 under the UDO, as they stood before the
UDO took effect on 2023-06-01. Charlotte (`3712000`) outcomes from 2023-06-01 are held out, and the snapshot
rule (#100) hides any Charlotte parcel roll dated on or after that day. The NC OneMap roll used by
`onemap_parcels` is from 2026 (Mecklenburg transform date 2026-01-07), so it has **no Charlotte rows** after the
holdout filter, as expected.

## What V5 needs from the roll

1. The parcel's zoning before the UDO (R-3, R-4, R-5, R-6, R-8 → N1-A … N1-D; UR-1 → N1-E).
2. Whether the lot held a single-family house, was vacant, or held something else, before 2023-06-01.
3. Lot size (for any lot-size floor in the eligibility rule).

## Options, ranked

| # | Option | As-of date (how verified) | Gives | Gaps | Licence | Effort |
|---|---|---|---|---|---|---|
| 1 | **City of Charlotte "UDO Zoning Translation"** parcel layer ([REST](https://services.arcgis.com/9Nl857LBlQVyzq54/arcgis/rest/services/Unified_Development_Ordinance_Zoning_Translation/FeatureServer/193), item `3e5bae72162f4dc8aa26679f2a4994d5`) | **Before 2023-06-01, provable**: `editingInfo.dataLastEditDate` 2023-05-31 18:29 UTC; max `last_edited_date` 2023-05-24, max `created_date` 2023-05-18, max `RezoneDate` 2023-05-15 (statistics query, 2026-10-19) | 324,180 parcel polygons; `taxpid`, `OldZoneDes` (pre-UDO district), `ZoneDes` (UDO district), `OldOverlay`/`Overlay`, `ZonePetition`, `RezoneDate`; polygon area for lot size | No land use, year built or units, so (2) is missing | "Custom": City of Charlotte disclaimer, no use restriction stated | Low: `download_layer` (2,000 per page) |
| 2 | Current Mecklenburg CAMA ([ParcelsLandUse](https://meckags.mecklenburgcountync.gov/server/rest/services/Parcels/ParcelsLandUse/MapServer/0); [CAMA metadata](https://maps.mecklenburgcountync.gov/metadata/item/tax-parcels-with-cama-data/)) joined on `taxpid`, backdating with `yearbuilt` < 2023 | **Current (weekly)**: after 2023-06-01 | Land use, year built, units | **Breaks the snapshot rule for Charlotte**: a current roll shows what was built after the reform. Not usable without an explicit holdout decision | County metadata mentions a waiver form and no resale | Medium |
| 3 | City of Charlotte "Pre UDO Zoning" districts ([REST](https://services.arcgis.com/9Nl857LBlQVyzq54/arcgis/rest/services/Pre_UDO_Zoning/FeatureServer/0)) | Described as zoning "prior to the implementation of the UDO", but `dataLastEditDate` is 2023-07-13: **not provable** from metadata | District polygons (zoning only) | No parcels; public view item is CC BY-NC-SA 4.0 (non-commercial) | Non-commercial: conflicts with the permissive-only rule | Low; cross-check only |
| 4 | UDO §3.2 Table 3-1 translation ([text amendment PDF, p. 49](https://www.charlottenc.gov/files/sharedassets/city/v/1/growth-and-development/planning-and-zoning/rezoning/documents/2023-petitions/revised-site-plans/2023_174_textamendment_rev_2024_02_12.pdf)) | Ordinance text | Rule: R-3→N1-A, R-4→N1-B, R-5→N1-C, R-6 and R-8→N1-D, UR-1→N1-E; conditional districts keep legacy rules | Not data | Public | Config row only |
| 5 | Ask Mecklenburg County GIS (or NC OneMap support) for an archived CAMA/parcel extract dated 2022 or Jan–May 2023 | Would be provable from the file date | Everything (land use, year built, units, values) | Archive existence unverified; NC OneMap publishes no historical extracts; NCSU's Mecklenburg archive stops at 2014 and is campus-only | Unknown until received | High, slow |
| 6 | Census/ACS for Charlotte (V0-style fallback denominator) | 2018–2022 ACS 5-year | 1-unit detached structures by tract | Not parcel-level; no zoning | Public domain | Low; already in the pipeline |

Not useful: NC OneMap (current only, no units, no archive found), NCSU archive (≤ 2014), Polaris "2022 Sales"
(sales only), Regrid/ReportAll (commercial licences), Quality of Life Explorer (neighbourhood aggregates).

## Recommendation

- **Fetch option 1** as source `clt_udo_translation` (a dated pre-window roll, so the snapshot rule keeps it:
  `vintage_date` 2023-05-31). It answers (1) and (3) for every Charlotte parcel.
- **For (2), choose one** (decision for Ben):
  - **(a)** Request an archived pre-2023-06-01 CAMA extract from Mecklenburg County (option 5): the clean way;
    meanwhile V5 counts all lots zoned R-3…R-8/UR-1 on 2023-05-31, with no vacancy split.
  - **(b)** Use the **Mecklenburg outside-Charlotte** share of vacant and single-family parcels from the
    current roll as a prior for the Charlotte split, labelled as an assumption with a range.
  - **(c)** Treat current CAMA year built as allowed for Charlotte (option 2). **Not recommended**: it reads a
    post-window roll of the held-out place, which the snapshot rule forbids; it would need a written holdout
    exception in HANDOFF before any fetch.
- Add the Table 3-1 translation to `config/` with its source (option 4), and use option 3 only as a cross-check
  if the licence question is settled.

## Not verified

- Whether every Charlotte parcel is in option 1 (324,180 features suggests nearly all; a comparison with a
  county count needs a pre-window county roll).
- Whether Mecklenburg County keeps dated CAMA archives.
- Terms of use of the county REST services.
