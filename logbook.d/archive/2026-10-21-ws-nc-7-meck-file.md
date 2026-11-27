### LB-NNN · 2026-10-21 · Build: Mecklenburg permits from Ben's hand download (NC thread 10, S7b)
- **Question:** can the Mecklenburg building permits (blocked to scripts by Cloudflare) be loaded from a hand
  download without exposing the V5 Charlotte holdout?
- **What I did:**
  - Ben downloaded the county's "Building Permits - Winchester" GeoPackage from its Open Data Viewer
    (https://maps.mecklenburgcountync.gov/opendata-viewer) in a browser, from Europe through a US VPN; it was
    registered unopened (sha256 4c96b59d…, data dated 2026-10-12).
  - `meck_permits` reads it with the same holdout-first filter as the live layer, inside the SQL query, so
    Charlotte and unincorporated rows from 2023-06-01 are never read; owner fields are never selected.
  - Wrote `stateplane.to_lonlat` (EPSG:2264 inverse Lambert, numpy): tests on its defining points and a round
    trip; on real data the permit points sit a median 7 m from the same parcels' pre-UDO centroids.
  - Found and fixed two adapter faults the live layer had hidden: a missing-code comparison that crashed, and
    four county item codes missing from the crosswalk (102 townhouses, 112 mobile homes, 114/115 condos).
  - Re-registered the Wake Dec 2023 roll under the adapter's documented vintage (2023-12-31) so the adapter
    finds a hand-registered copy; superseded the automated entry (identical file).
- **Inputs:** the GeoPackage; processed `clt_udo_translation` (projection check); NC BPS 37119 (pre-2023 only).
- **Outputs:** `src/lotline/adapters/states/nc/meck_permits.py`, `stateplane.py`,
  `config/crosswalks/nc_meck_usdc_codes.csv`, `config/states/nc.yaml`, tests, `docs/data_provenance.md`.
- **Findings:**
  - 449,925 permits kept; Charlotte and county rows end 2023-05-31; `holdout.assert_no_leak` passes.
  - New one-unit homes countywide are 0.88-1.02 of BPS 37119 in 2012-2022 (were about 0.65-0.7 before the
    townhouse code was added); 1.2-1.3 in 2010-2011; apartments 0.5-1.6 by year.
  - The six towns' legacy permits run to 2026-10; the county's newer Accela permit file is not loaded.
- **Decisions:** none.
- **AI:** Claude Code (Opus 5.5) wrote the reader, projection and tests and ran every check on aggregates only
  (Charlotte and the county before 2023-06-01; towns any year). No held-out row was opened or counted.
- **Open / next:** the Accela permit file (towns after 2025; Charlotte only after the Nov 17 freeze).
