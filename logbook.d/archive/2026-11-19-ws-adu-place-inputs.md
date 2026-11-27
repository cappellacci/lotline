### LB-XXX · 2026-11-19 · WS-ADU · ADU reads its place inputs from place_inputs

**Question:** Can the ADU model read its shared per-place inputs from the `place_inputs` table (WS-SCALE, contract-change #455) without changing any result?

**Output:** `src/lotline/model/scenarios/adu.py` (`places_from_store`, `_place_input_rows`, `PLACE_INPUT_ADU`), `tests/model/test_adu_place_inputs.py`, `tests/model/test_adu_permit_remainder.py`, `tests/build/test_place_inputs.py` (docstring).

**What happened:** `adu.places_from_store` now takes eligible lots (nearest roll, D-020 overlap removed), ACS rent and value, the observed ADU floor (central k), the D-088 place type and the data tier from `place_inputs` at year == origin, and builds that year itself when the table is not stored. It keeps its own steps: coded rules (D-064, D-067), the county mix, and the per-undercount-row split of the observed floor; a non-default undercount recomputes the floor. The results.py drop of places with no rent or value stays until WS-SCALE's #489 (D-103) lands; adopting those rules is the next ADU PR.

**Claude's part and checks:** Claude (ADU session) made the change. Before and after on all five states at origin 2025: the same 1,051 / 453 / 945 / 168 / 1,003 places in the same order with every shared column equal, and `lotline results` bundles identical apart from `run_at` (same seed). New tests check the stored table is what ADU reads, that only the origin year is read, and the build-on-the-fly fallback.
