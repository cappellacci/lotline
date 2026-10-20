### LB-NNN · 2026-10-20 · Build: WS-MN eligible parcels from real metro rolls
- **Question:** Do the metro parcel rolls give sensible ADU / missing-middle denominators, and how do they compare
  with the ACS fallback?
- **What I did:**
  - Set `parcel_sources` in `config/states/mn.yaml` (Minneapolis → assessor tables, else Met Council), applied by
    WS-CORE's `eligible.single_source` (#154, from #147); the shared rule `from_parcels` (1.1) is unchanged.
  - Compared 2023 ADU-eligible parcels with the ACS one-unit-detached fallback for the 20 largest metro cities.
  - Opened #147 (contract-change); WS-CORE answered with #154. A small helper
    `src/lotline/adapters/states/mn/denominators.py` reproduces the parcels-vs-ACS check.
- **Inputs:** processed `parcels` (metc_parcels, mpls_assessor_parcels), MN jurisdictions, ACS fallback rows.
- **Outputs:** `config/states/mn.yaml` (`parcel_sources`), the helper, `tests/states/mn/test_denominators.py`; issue #147.
- **Findings:** 186 metro jurisdictions per roll; ADU-eligible parcels 2023: 779,714 (ACS 764,258 for the same 185
  places). The 20 largest cities sum to 0.99 × ACS; outliers Blaine 1.31, Shakopee 1.29, Coon Rapids 1.25 (Anoka and
  Scott record no townhome/condo split, so attached homes count as single-family) and Minneapolis/St. Paul 0.90-0.91.
  St. Paul has parcel denominators for 2021-2023 only (V5).
- **Decisions:** Minneapolis from the assessor tables (pending Ben, decision 1); St. Paul from Met Council 2021-2023
  (pending Ben, decision 2).
- **AI:** Claude wrote the helper and synthetic tests and ran it on the processed MN parcels.
- **Open / next:** #147; Anoka/Scott attached-home split.
