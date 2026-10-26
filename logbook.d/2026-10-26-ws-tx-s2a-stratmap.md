### LB-NNN · 2026-10-26 · Build: StratMap statewide parcels adapter, ahead of the download (Texas plan S2a)
- **Question:** can the Texas parcel adapter be ready before Ben's browser download of the StratMap zips, with
  no new dependency?
- **What I did:**
  - Wrote a standard-library shapefile reader (`.shp` polygon centroids and areas by the shoelace formula,
    `.dbf` selected fields only, streamed in chunks) and a `.prj`-driven inverse projection (geographic,
    ellipsoidal Albers equal-area, Web Mercator) in the WS-TX adapter folder.
  - Wrote `stratmap_parcels`: registered zips only (the host blocks scripts), PTAD state codes through the
    existing crosswalk, lot size from the stated areas or an equal-area polygon, jurisdiction by centroid with
    `lotline.geo`, county remainder otherwise. `parcel_sources` keeps TCAD for Austin.
  - Tests write shapefiles byte by byte from the ESRI and dBASE layouts and check hand-worked centroids and
    areas (square, square with a hole, L shape), the Albers origin, round trips and privacy.
- **Inputs:** Texas data plan (S2a, approved 2026-10-23); StratMap field list from the TxGIO service metadata.
- **Outputs:** `src/lotline/adapters/states/tx/{stratmap_parcels,shapefile,projection}.py`,
  `tests/states/tx/test_stratmap_parcels.py`, `config/states/tx.yaml` (source and `parcel_sources`).
- **Findings:** about 55,000 synthetic parcels a second (14M in minutes). Not yet known until the zip is
  opened: shapefile or file geodatabase, the coordinate system, the area-unit values and which counties fill
  `stat_land_use`.
- **Decisions:** proposed: Austin keeps TCAD (`parcel_sources`), so its Williamson and Hays parts stay
  uncounted for now.
- **AI:** Claude wrote the readers, adapter and tests; nothing was downloaded.
- **Open / next:** run on Ben's registered download; if it is a geodatabase, Ben decides on pyogrio or the
  per-county zips. Texas place boundaries (TIGERweb) download on first run.
