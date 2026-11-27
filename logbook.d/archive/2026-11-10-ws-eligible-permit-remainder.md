### LB-NNN · 2026-11-10 · WS-CORE: a permit-level county-remainder denominator (D-074 step 2)
- **Question:** what eligible-lot denominator should a county remainder take when its ADU rate is measured
  from record-level permits, and which counties need it?
- **What I did:**
  - Added `remainder="permits"` to `eligible.allocate_homes`, `from_acs` and `load`. A county remainder
    then also loses its local-only places and townships (`in_bps` False). The default stays `"bps"`, so the
    stored table and every BPS outcome are unchanged.
  - Added `eligible.permit_level(stored, acs_rows, jurisdictions)`. It replaces only ACS-fallback county
    remainder rows. Remainders counted from a parcel roll, or scaled or interpolated from one, never overlap
    a place, so they are kept.
  - Checked all five states' processed `jurisdictions` and `eligible_parcels` for local-only members inside
    ACS-fallback remainders.
- **Inputs:** processed `jurisdictions`, `acs_geo_year` and `eligible_parcels` (NC, MN, OH, TX, OR); cached
  Census 2020 place-by-county parts.
- **Outputs:** `src/lotline/build/eligible.py`; `tests/core/test_eligible.py` (two hand-worked tests).
- **Findings (read-only, from processed tables; no engine or fit run):**
  - Unincorporated Mecklenburg (37119), ADU lots: 2021 268,509 → 18,670; 2024 275,566 → 20,086. NC OneMap's
    2026 roll has about 21,812 single-family detached parcels there.
  - The same pattern holds in 21 more NC counties (e.g. Cabarrus 37025 71,518 → 16,213; Gaston 37071
    50,375 → 26,805) and 2 MN counties (Scott 27139 7,930 → 1,978; Carver 27019 3,712 → 0, since its
    townships cover the rest of the county). OH (Urbana township sits in a parcel-scaled remainder), TX and
    OR have none.
  - Rebuilding the stored ACS rows in `"bps"` mode gives the stored values exactly (NC, MN, OH).
- **Decisions:** none new. The method is D-074 step 2's; the PR proposes that the joint refit (D-075 step 3)
  read permit-level denominators for county remainders whose ADU counts come from local permit files.
- **AI:** Claude Code designed and wrote the change and tests. It checked them by hand-worked examples, the
  full test suite, `compliance_check.py`, and the read-only before/after comparison above.
- **Open / next:** wire `permit_level` into the ADU panel builders (`estimate_adu`, `calibrate_adu`) in the
  refit PR; no schema change was needed.
