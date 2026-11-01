### LB-NNN · 2026-10-27 · Data feasibility: Texas readiness after the StratMap load (plan S8, S9)
- **Question:** with StratMap loaded (#238) and #233 merged, how much of Texas runs on real data, and what is
  still missing?
- **What I did:**
  - Merged #233 (Ben's request), then counted denominator sources, tiers, roll years and population shares
    from the rebuilt `jurisdictions` and `eligible_parcels` tables, restricted to the 1,006 jurisdictions.
  - Refreshed `docs/build/tx-readiness.md` (in short, coverage rows, gaps) and the Texas rows of
    `docs/data_availability.md` (parcels, year built, lot size, parcel history, prices, fees, reform rows,
    biggest gaps).
- **Inputs:** processed Texas tables in `~/lotline-data` (StratMap 2019 and 2025, rebuilt 2026-10-27);
  `config/reforms/tx.csv`, `config/fees/tx.csv`.
- **Outputs:** `docs/build/tx-readiness.md`, `docs/data_availability.md`.
- **Findings:**
  - 458 of 1,006 jurisdictions count eligible parcels from real rolls (439 places with 67% of the people in
    Texas places, 19 county remainders); 546 stay on ACS; 2 have neither. 193 have both rolls, 173 only
    2019, 91 only 2025. 32 of the 40 places of 100,000+ count from parcels; Houston, Amarillo, League City,
    Mesquite, Pearland, Round Rock, Tyler and Wichita Falls do not.
  - **Correction to the #238 fragment (2026-10-27, StratMap reader):** it gave 530 jurisdictions on parcels
    (91 county remainders). That count included 72 county-remainder rows for counties that are not Texas
    jurisdictions; the right figures are 458 and 19.
- **Decisions:** none.
- **AI:** Claude computed every figure from the processed tables (scripts run in the session, not saved) and
  rechecked the roll-year counts after finding the over-count.
- **Open / next:** local land-use crosswalks (Harris Z codes, `loc_land_use`) for Houston, Travis 2025 and
  Williamson; leave non-jurisdiction county remainders out in `resolve_jurisdictions`; TCAD rebuild for the
  C and X crosswalk rows; Ben's rule and fee lookups.
