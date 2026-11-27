### LB-NNN · 2026-10-27 · Build: StratMap statewide parcels loaded (file geodatabase reader, Texas plan S2a, S2b, S3)
- **Question:** can Lotline read the StratMap statewide parcel files Ben downloaded, with no new dependency,
  and how much of Texas then counts eligible parcels from real rolls instead of the ACS fallback?
- **What I did:**
  - Found that all five statewide zips (2019-03, 2022-07, 2024-02, 2025-06, 2026-09) are Esri file
    geodatabases, not shapefiles. Checked pyogrio's wheels: they statically link GEOS (LGPL-2.1) and SpatiaLite
    (MPL/GPL/LGPL), so Ben turned it down. Wrote `filegdb.py`, a numpy-only reader, from Even Rouault's
    published FGDB-Spec (no code taken from GDAL or any reader): fields, null bits, row offsets, varint shape
    buffers, centroids and areas by the shoelace formula, chunked and vectorised.
  - Measured land-use coverage per release (share of parcels with a state land-use code): 2019 60%, 2022 0,
    2024 35%, 2025 55%, 2026 0 (no land use or area units for any county). Read only 2019 and 2025 (`ROLLS`).
  - Fixes from the real files: one roll per release (the 2019 release mixes 2018 and 2019 tax years, which
    split cities across counties into partial rolls); tax year 0; the DEADBEEF marker counted in the field
    section (2022); 10-character field names (2019); empty shapes; lot size from the polygon on Web Mercator,
    corrected for latitude; PTAD categories C and X in the crosswalk (Comptroller Property Classification
    Guide, 96-313).
  - Added a completeness check (Ben, 2026-10-27): a county part with under 80% of the parcels the county has
    in the other release is left out, with every jurisdiction touching it (`config/params/parcels.yaml`).
  - Rebuilt Texas parcels, jurisdictions (tiers) and eligible parcels (data builds, not model runs).
- **Inputs:** StratMap Land Parcels 2019-03, 2022-07, 2024-02, 2025-06, 2026-09 (CC0, hand-downloaded and
  registered by Ben); FGDB-Spec; Comptroller 96-313; LB entries for S2a (2026-10-26).
- **Outputs:** `src/lotline/adapters/states/tx/filegdb.py`, `stratmap_parcels.py`, `projection.py`;
  `tests/states/tx/test_filegdb.py`, `test_stratmap_parcels.py`, `test_tcad_parcels.py`;
  `config/params/parcels.yaml`; `config/crosswalks/tx_ptad_land_use.csv`; `docs/disclosures.md`,
  `docs/data_provenance.md`, `docs/model_and_assumptions.md`; rebuilt tables in `~/lotline-data` (not in the
  repo): 21.0M parcels, 1,006 jurisdictions, 30,788 eligible-parcel rows.
- **Findings:**
  - Reader checked against the file itself: every polygon area equals the stored `SHAPE_Area`; 14.3M rows read
    in about 2 minutes; two statewide rolls load in 8 minutes at 5.2 GB peak.
  - Denominators: 530 of 1,006 Texas jurisdictions now count from parcels (439 places, 91 county remainders),
    up from 1; tiers 125 / 161 / 720 (tier 1 / 2 / 3), from 1 / 0 / 1,005. 2023 ADU-eligible counts sit near
    the ACS fallback: San Antonio 365,676 (ACS 357,081), Fort Worth 246,154 (236,037), Plano 72,080 (69,170),
    Dallas 230,547 (243,946), El Paso 182,489 (177,422).
  - Houston stays on ACS: Harris's 2019 extract has 66% of its 2025 parcels (dropped as partial) and its 2025
    roll has 85% known land use, under the 90% tier-2 gate (Harris's own Z codes are unmapped).
- **Decisions:** Ben: no pyogrio (LGPL bundles); the 80% county completeness rule. Proposed: read only
  2019-03 and 2025-06 (`ROLLS`); one roll per release at its release year.
- **AI:** Claude wrote the reader, adapter changes and tests (byte-by-byte synthetic geodatabases from the
  spec, hand-worked centroids, areas, varints and the completeness rule), measured coverage on the real files
  and compared rebuilt counts with the ACS fallback. The full suite (1,124 tests) and the compliance check
  pass.
- **Open / next:** readiness report refresh after #233 merges; Harris Z codes and county `loc_land_use`
  crosswalks (would bring Houston, Travis 2025, Williamson in); TCAD rebuild for the new C and X rows; ask
  TxGIO why the 2022 and 2026 releases carry no land use; per-vintage parcel files (WS-CORE) to read all five
  releases.
