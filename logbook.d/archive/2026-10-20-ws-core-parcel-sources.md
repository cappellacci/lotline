### LB-NNN · 2026-10-20 · Build: One parcels source per jurisdiction; overlapping sources are an error (#147)
- **Question:** Can overlapping parcel sources (Minnesota: Met Council, Minneapolis assessor, Ramsey) be double-counted in eligible parcels?
- **What I did:** Yes: `eligible.load` stacked every parcels file. Added `parcel_sources` to the state config (GEOID → source, `"*"` default) and `eligible.single_source`, applied before counting; with no choice configured, any jurisdiction-roll covered by two sources raises an error instead of double-counting. Test added.
- **Inputs:** WS-MN's issue #147; processed parcels for MN, NC, OH, TX.
- **Outputs:** `src/lotline/config/__init__.py`, `src/lotline/build/eligible.py`, `tests/core/test_eligible.py`.
- **Findings:** On the local data, MN stops with 24 overlapping jurisdiction-rolls until its config names the sources; NC, OH and TX have no overlaps (NC's OneMap and Wake rolls are different years).
- **Decisions:** none (WS-MN's source choices are pending Ben in #148).
- **AI:** Claude Code (WS-CORE) wrote the change and test; all tests pass.
- **Open / next:** WS-MN moves its choices to `parcel_sources` in `config/states/mn.yaml`.
