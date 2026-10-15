### LB-NNN · 2026-10-15 · Validation: Holdout guard covers parcel rolls
- **Question:** Can a parcel roll leak held-out outcomes, and does the central guard catch it?
- **What I did:** Found that the central leak check (`assert_no_leak`, run after every `lotline fetch`) covered only `permits` and `bps_place_year`. A parcel roll of a held-out place taken after the window opens shows what was built there (land use, units, year built). Added `snapshot=True` to `held_out_mask`/`apply`: a roll dated on or after `outcome_from` is held out with no end date, and a roll with only a year is held out from that year on (strict when unsure). Registered `parcels` with the central guard (`vintage_date`, falling back to `vintage`).
- **Inputs:** `src/lotline/validation/holdout.py`; holdouts in `config/states/{mn,nc}.yaml`.
- **Outputs:** `src/lotline/validation/holdout.py`, `tests/core/test_holdout.py`.
- **Findings:** No parcels table has been built yet, so nothing on disk needed re-checking. Consequence for adapters: St. Paul parcels can come only from rolls of 2023 or earlier, and Charlotte parcels only from a roll dated before 2023-06-01; a current roll has no St. Paul or Charlotte rows.
- **Decisions:** none (proposal: parcel adapters for MN and NC call `holdout.apply(..., snapshot=True)`; round-3 briefs say so).
- **AI:** Claude Code (WS-CORE) spotted the gap while drafting the MN/NC round-3 briefs, wrote the change and 3 tests; 378 tests pass.
- **Open / next:** the same snapshot rule may be needed for `eligible_parcels` if it is ever built from a roll directly rather than from `parcels`.
