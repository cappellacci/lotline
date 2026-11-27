### LB-NNN · 2026-10-19 · Validation: Charlotte holdout covers Mecklenburg County BPS rows (D-012)
- **Question:** Does the Charlotte holdout hide every row that carries Charlotte's post-UDO outcomes?
- **What I did:** Checked WS-NC's finding (#123): the processed NC BPS table has no Charlotte place rows, but Mecklenburg County (37119) rows through 2025, because BPS files Charlotte's permits under the county. Added `reporting_geoids` (with a required reason) to holdouts, held out over the same window; Charlotte names 37119. Holdout places and places that appear only in permits or parcels are now always jurisdictions (`jurisdictions.local_geoids`). Rebuilt NC BPS (37119 now ends in 2022) and NC jurisdictions (Charlotte present, `in_bps=False`). Logged D-012.
- **Inputs:** #123; `config/states/nc.yaml`; processed NC BPS (GEOIDs and years only; no values read).
- **Outputs:** `src/lotline/config/__init__.py`, `src/lotline/validation/holdout.py`, `src/lotline/build/jurisdictions.py`, `config/states/nc.yaml`, `docs/analysis_plan.md` (D-012), `tests/core/test_holdout.py`, `tests/core/test_jurisdictions.py`.
- **Findings:** The 2023–2025 37119 rows entered the V1 NC backtests in aggregate; no Charlotte- or Mecklenburg-specific figure was printed, plotted or reported, and V0 skipped NC 2023+ by date. St. Paul is unaffected (BPS has a St. Paul place row, ending in 2023 after the filter).
- **Decisions:** D-012 (Ben, 2026-10-19: fix and disclose).
- **AI:** Claude Code (WS-CORE) confirmed the leak by listing GEOIDs and years only, wrote the fix and 4 tests (511 pass), and rebuilt the NC tables.
- **Open / next:** re-run NC V1 on the rebuilt table (WS-ENGINE's baseline PR re-runs the backtest); `meck_permits` can start once this is on main.
