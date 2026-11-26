### LB-NNN · 2026-11-26 · review · Page years from the results, loud column changes, fetch order

**Question:** Would the app's wording, the readers and a plain `lotline fetch` stay right when the data moves
on a year or a source changes its layout?

**Outputs:**
- `src/lotline/app/build.py` (`page_years`) and `src/lotline/app/template.html`: the fixed text gets its years
  (origin, window, reform year, the in-between year, recent-pace years) from the bundles at build time. Five
  JS strings now read the bundle's window.
- `src/lotline/adapters/national/bps.py`: the header must end with the 24 count columns in the documented
  order, a row narrower than the header stops, and a blank count stops instead of becoming 0.
- `src/lotline/adapters/states/tx/stratmap_parcels.py` (`REQUIRED_FIELDS`) and `src/lotline/adapters/national/fhfa.py`:
  a missing or renamed column stops the read.
- `src/lotline/registry.py` (`fetch_order`), `src/lotline/cli.py` and `READS` / `RERUN_AFTER` on the
  jurisdictions, eligible and demand builds and on the parcel and permit adapters that read other tables.
  Order: Census permits → jurisdictions → parcels → jurisdictions again (data tiers) → eligible and demand
  → place inputs.
- `docs/adding_a_state.md`: new adapters declare `READS`.

**What Claude did:**
- Wrote the code and tests from the nightly review's items 1, 2 and 8 (2026-11-25).
- Left the unknown-2020-population item (`build/place_inputs.py:166`) for Ben and the ADU session. It sets
  the ADU size band of 18 real places (MN 6, OH 1, TX 5, WI 6), so it is a model choice, not a guard.

**Checked:**
- All 102 real BPS files (1992–2025) parse to the same 483,599 rows under the new header and blank checks;
  none has a blank count.
- Both StratMap rolls and all five FHFA files carry every column now required.
- Fetch order printed for all six states; the jurisdictions readers come after its second run.
- App built from the test bundle: the same sentences as before for origin 2025, no slot left unfilled, no
  console errors. A test bundle with origin 2026 moves every year.
- New unit tests; full suite with slow tests (see PR).
