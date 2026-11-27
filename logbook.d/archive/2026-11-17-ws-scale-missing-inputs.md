### LB-NNN · 2026-11-17 · Analysis: WS-SCALE tasks 9 and 10, what local data is worth and what a new state borrows
- **Question:** How far do a state's results move when parcels, zoning rules or permits drop to their
  fallback? What does a state with no reform history borrow, and do the Rules expect causal identification?
- **What I did:**
  - `scripts/dev/missing_input_matrix.py` runs NC four times in one process, offline, same seed: as is, no
    parcels, no coded rules, no permits. Tables are hidden by a `DataStore` subclass, and nothing is written
    to the data directory or unblinded.
  - Wrote the table into `docs/adding_a_state.md` §2.
  - Wrote §8 (borrowed parameters), after a Claude subagent read the Rules and Handbook pages in full.
- **Findings (NC, five-year net homes):**
  - No coded rules: ADU median +251%, range ×4.9; middle housing +51%, ×1.5.
  - No parcels: ADU −4%; middle housing −18%, range ×0.79 (narrower).
  - No permits: ADU +4%; the rest unchanged.
  - Neither the Rules nor the Handbook uses "causal" or "identification". The Handbook is
    methodology-agnostic and accepts assumptions that are "clearly described and justified".
- **Decisions:** none. For Ben: the data-tier ladder does not widen every range. Dropping parcels narrows the
  middle-housing range, which the brief's target ("each step down widens the range") does not expect.
- **AI:** Claude wrote the script and the sections, and ran the matrix twice (scratch harness, then the
  saved script).
- **Open / next:** the same matrix on a second state; whether the ladder should add width where it now
  narrows.
