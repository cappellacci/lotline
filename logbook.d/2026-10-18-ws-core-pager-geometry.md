### LB-NNN · 2026-10-18 · Build: Pager geometry modes and retries on ArcGIS error pages
- **Question:** Can the ArcGIS pager fetch polygon boundaries (for placing parcels in cities and townships) and parcel centroids without polygons, and survive servers that fail deep pages intermittently (WS-OH request)?
- **What I did:** `download_layer(geometry=...)` now takes `False`, `True`/`"point"` (unchanged queries, so existing caches still hit), `"centroid"` (label points only, polygon layers whose server advertises `supportsReturningGeometryCentroid`) and `"polygon"` (a `rings` column). ArcGIS error bodies are retried with exponential backoff (`retries=3`) before raising; error pages are never kept. The object-ID field is always requested (added only when `out_fields` lacks it).
- **Inputs:** WS-OH round-1 report; TIGERweb Places/County Subdivisions MapServer; Ohio Statewide Parcels FeatureServer.
- **Outputs:** `src/lotline/io/arcgis.py`, `tests/core/test_arcgis.py`.
- **Findings:** Live: TIGERweb ACS 2025 Incorporated Places returned Columbus (256 rings, 18,250 vertices) and Toledo as polygons in 2.6 s. TIGERweb's MapServer silently ignores `returnCentroid` (it doesn't advertise the capability), so centroid mode now refuses such servers instead of returning empty coordinates. On the Ohio parcels layer, centroid mode returned 13,218 Vinton County parcels, 99.8% with a point (78 s). Requesting `out_fields` without the object-ID field used to crash the overlap check; no existing adapter did that.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) wrote the change and 7 tests (382 pass); live checks in scratch data folders.
- **Open / next:** the place/township assignment helper that uses polygon mode.
