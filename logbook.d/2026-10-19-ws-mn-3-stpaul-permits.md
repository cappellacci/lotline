### LB-NNN · 2026-10-19 · Build: WS-MN St. Paul permits snapshot
- **Question:** Can we keep a dated copy of the St. Paul building-permit layer (a rolling window) without
  touching the V5 holdout, and is the layer still live?
- **What I did:**
  - Added `stpaul_permits` (ArcGIS pager, dated raw snapshot, explicit non-personal `FIELDS`; street address
    and contractor fields never requested, the work description kept in the raw snapshot only).
  - `to_permits` reads issue dates and calls `holdout.apply` before any other step; units derived only for
    new SFD (1) / duplex (2) and repairs (0), everything else null.
  - Freshness from `layer.json` only: `editingInfo.dataLastEditDate` = 2025-07-01.
- **Inputs:** City of Saint Paul `Building_Permits_` FeatureServer/0 (item cb618c6b5f8f46b696674e74a3fb5b2d).
- **Outputs:** `src/lotline/adapters/states/mn/stpaul_permits.py`, `tests/states/mn/test_stpaul_permits.py`,
  fixture `tests/states/mn/fixtures/stpaul_permits_synthetic.csv`, `config/states/mn.yaml`,
  `docs/data_provenance.md`; snapshot `raw/stpaul_permits/2026-10-19/`.
- **Findings:** 73,228 permits issued 2015-06-30 to 2023-12-31 kept (pre-2015-06 history already gone).
  The layer stopped updating on 2025-07-01. No unit counts, no demolitions; 1.1% lack a PIN. No MN manual
  exports exist in `~/lotline-data/manual/` (only `tcad`).
- **Decisions:** none new; St. Paul outcomes stay with Met Council permits.
- **AI:** Claude wrote the adapter and synthetic tests (including a test that the holdout filter runs before
  any derived column exists) and ran the real fetch; only pre-2024 rows were inspected.
- **Open / next:** ADU reading of the work description (38 pre-2024 descriptions name an ADU) if V5 needs it.
