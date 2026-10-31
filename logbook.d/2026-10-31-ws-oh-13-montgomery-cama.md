### LB-NNN · 2026-10-31 · WS-OH · Montgomery CAMA (Dayton off the ACS fallback) and Warren County land use

**Question.** Dayton sat on the ACS fallback (18.6% unknown land use) and Warren County was 44% unknown. Can the
county files Ben downloaded fix that?

**Outputs.**
- `src/lotline/adapters/states/oh/oh_parcels.py`: Montgomery CAMA join, drop rule, yearly rolls and Warren join.
  The Franklin yearly-roll code is generalized to `county_roll` and `county_yearly_rolls`.
- `tests/states/oh/test_oh_parcels.py`.
- `config/states/oh.yaml`, `docs/disclosures.md` and `docs/data_provenance.md` (Ohio sections).
- Data: 9 CAMA zips (2011–2026) and the Warren geodatabase, all registered with `lotline manifest register`.
- Rebuilt processed Ohio `parcels`, `jurisdictions` and `eligible_parcels`.

**What changed.**
- **The Montgomery drop rule.** 16,089 of Dayton's 16,270 unknown parcels are in no CAMA roll from 2011 to 2026.
  They are old-lot and retired polygons, so they are dropped (Ben approved this after the check, 2026-10-30).
  Unknown land use falls to 0.2–1.6% by year.
- **Dayton.** It leaves the ACS fallback and gets 10 real roll years from 2011 to 2026, the other years scaled
  (D-035). Its counts are 0–6% below the ACS estimates. It moves from tier 3 to tier 2.
- **Tier 1.** 72 → 81 places: Kettering, Centerville, Miamisburg and others gain year built.
- **Warren.** Lebanon goes from 34% to 5% unknown; Franklin city from 100% to 6%. Middletown improves from 15.2%
  to 12.1% but stays on ACS under the kept 10% gate. Parcels in its Warren part were renumbered after 2023.
- Kettering (98.7% in Montgomery) keeps one roll year under the 99% rule.

**How Claude worked and checked.**
- Claude checked every zip's integrity, tracked Dayton's unknown parcels through all CAMA years, and matched
  Warren's PARNUM to the roll (81%).
- After rebuilding, Claude diffed the eligible table against a backup. Only Montgomery, Warren and places
  reaching into Warren changed.
- The first rebuild failed: the 2011–2025 zips keep their tables at the root, not in a folder. The fix is tested
  with both layouts.
- Only parcel ID, land use and year built are read. No owner or address fields are read.
