### LB-NNN · 2026-10-19 · Data feasibility: a Charlotte parcel roll dated before the UDO (V5 denominator)
- **Question:** Is there a Mecklenburg parcel roll dated before 2023-06-01 that can count Charlotte's N1 lots without
  touching held-out data?
- **What I did:**
  - Surveyed county, city, NC OneMap and NCSU sources; checked dates from layer metadata and statistics queries only.
  - Confirmed the City of Charlotte "UDO Zoning Translation" layer is dated 2023-05-31 (data last edited; max edit
    2023-05-24; max rezoning 2023-05-15) with 324,180 parcels carrying pre-UDO and UDO districts.
- **Inputs:** layer JSON of the city and county ArcGIS services; UDO Table 3-1 (text amendment 2023-174).
- **Outputs:** `reports/nc/charlotte_pre_udo_parcels.md`.
- **Findings:** zoning before the UDO is available on a provably pre-window layer; parcel land use and year built
  before 2023-06-01 are not (current CAMA would break the snapshot rule; no public archive found).
- **Decisions:** proposed: fetch the translation layer as a dated source; ask Mecklenburg County for an archived
  pre-2023-06-01 CAMA extract; no use of current CAMA for Charlotte.
- **AI:** Claude (WS-NC) and a research subagent searched and read metadata; nothing was downloaded.
- **Open / next:** Ben's decision on the land-use gap (options a/b/c in the note).
