### LB-NNN · 2026-10-21 · Build: NC OneMap parcels beyond the ten largest counties (NC thread 10, S1–S2)
- **Question:** how many of NC's other 90 counties can feed real parcel counts, and does the statewide eligible
  table still hold together (no double counting) when they do?
- **What I did:**
  - Listed every county's land-use codes with statistics queries (`code_inventory`, no parcel download).
  - Wrote a keyword drafter (`onemap_codes`) and validated it on three hand-made crosswalks: it agreed on
    100% (Guilford), 99.7% (Forsyth) and 98.5% (Gaston) of parcels after aligning with their conventions.
  - Reviewed every drafted residential or vacant code with 300+ parcels and the non-residential codes with
    2,000+; fixed four misreadings. Downloaded 54 counties (Ben approved), then checked parcels coded
    single-family against ACS one-unit homes and left out nine counties outside 0.6–1.4.
  - Rebuilt parcels, jurisdictions and eligible parcels; checked duplicates and single-source overlap.
- **Inputs:** NC1Map_Parcels (2026 roll), ACS 2020–2024 B25024, the hand crosswalks.
- **Outputs:** `src/lotline/adapters/states/nc/onemap_codes.py`, `onemap_parcels.code_inventory` and
  `sale_date`, 35 new `config/crosswalks/nc_land_use_<county>.csv`, `nc_land_use_counties.csv`,
  `scripts/dev/nc_onemap_crosswalks.py`, `reports/nc/onemap_county_check.md`, tests.
- **Findings:**
  - 37 counties send no land-use code at all; 46 in all have nothing usable. 45 counties now feed 3,686,630
    parcels (1.63M before).
  - 194 jurisdictions count from parcels (79 before); tiers 113 / 81 / 247 (54 / 32 / 236 before); eligible
    lots from rolls: 1.54M for ADUs, 1.91M for missing middle.
  - 161 places BPS files under their county (Wilmington, Statesville …) are now jurisdictions of their own
    (`in_bps` False), as Charlotte and the Mecklenburg towns already were; D-020 keeps their parcels out of the
    county rows.
  - Every parcel-counted place still has one denominator year (S13, open).
- **Decisions:** proposed: the 0.6–1.4 ACS acceptance band for drafted counties.
- **AI:** Claude Code (Opus 5.5) built the drafter, reviewed its output and ran the checks above; hand-worked
  tests cover every rule named in the drafter's docstring.
- **Open / next:** S13 (denominator history); WS-ENGINE to check the new local-only places in the baseline.
