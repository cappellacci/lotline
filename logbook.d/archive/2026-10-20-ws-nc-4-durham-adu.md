### LB-NNN · 2026-10-20 · Fix: Durham's ADU-eligible count of 5 (sliver rolls)
- **Question:** Why does Durham city have 5 ADU-eligible parcels on main?
- **What I did:** Traced it to `eligible_parcels`: Durham had two rolls, NC OneMap 2026 (67,180 eligible) and the
  Wake December 2023 roll, which holds only the 363 Durham parcels in Wake County (5 single-family). Panels carry
  the 2023 value forward to 2025, so every origin before 2026 saw 5. `single_source` did not catch it because the
  two rolls have different vintages and NC had no `parcel_sources`. The same mechanism gave slivers in OneMap for
  places mostly outside the ten loaded counties (Chapel Hill 6.6%, Burlington 2.8%, Clayton 0%, Angier 8.4%).
- **Fix (adapters and NC config only):**
  - `wake_realestate` leaves out cities with under half their 2020 housing units in Wake (Durham 0.1%, Angier
    8.4%, Clayton 0%; shares in `nc_land_use_wake_jurisdictions.csv` from cached Census 2020 DHC parts);
  - `onemap_parcels` leaves out places with under half their 2020 housing units in the loaded counties
    (11 places, 4,342 rows); they fall back to ACS;
  - `parcel_sources` in `config/states/nc.yaml`: Wake places and the Wake remainder from the Wake roll, Charlotte
    from the translation layer, everyone else from OneMap: one roll per jurisdiction.
- **Checked:** in memory on the current processed tables (nothing shared was overwritten): Durham 67,180, Raleigh
  87,835, Greensboro 71,813; no jurisdiction has more than one roll year. Tests for each rule.
- **AI:** Claude (WS-NC) diagnosed and fixed; synthetic tests.
- **Open / next:** rebuild `parcels` (OneMap, Wake once Ben registers the roll) and `eligible_parcels` after merge.
