### LB-NNN · 2026-10-23 · data/NC · Why do four NC places look wrong against ACS in the dev run?

**Question.** The 2026-10-22 dev run (PR #213) flagged four places whose parcel counts sit far from ACS: unincorporated Bladen (0.42), Troutman (2.50), unincorporated Union (0.46) and Princeville (2.13). Data errors or real?

**Outputs.**
- `src/lotline/adapters/states/nc/onemap_codes.py`: new `rural_home` keyword rule ("RURAL IMPROVED", "IMPROVED RURAL", "OCCUPIED RURAL" → SF_DETACHED), ahead of the agricultural rule; tests in `tests/states/nc/test_onemap_codes.py`.
- `config/crosswalks/nc_land_use_{bladen,madison,columbus}.csv`: those classes now read as houses.
- `reports/nc/onemap_county_check.md`: Bladen 0.70 → 1.24, Madison 0.72 → 1.03, Columbus 0.99 → 1.00 (parcels coded SF detached / ACS B25024_002).

**Findings.**
- Bladen (and Madison, same coding): a crosswalk error, fixed. "RURAL IMPROVED" (a rural parcel with a building) was read as farmland.
- Troutman: real. 73% of its single-family homes were built since 2015, so scaling today's parcel count back in time (`parcels_scaled_acs`, D-035) overstates its past. A year-built backcast would fix it; suggested to WS-CORE, not done here.
- Union: geography. 13 towns are local-only and de-overlapped from the remainder (D-020); acceptable.
- Princeville: Edgecombe files mobile homes under "Single Family Residential" (ACS mobile homes 359 ± 106). Noted, not changed.

**How Claude worked and checked.** Claude diagnosed each case from the parcel and ACS tables, wrote the rule and crosswalk edits, rebuilt OneMap parcels, jurisdictions and eligible parcels, and checked the three counties against ACS (all inside the 0.6–1.4 band). NC tests, ruff and `compliance_check.py` run before commit. No model runs.
