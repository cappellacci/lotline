### LB-NNN · 2026-10-14 · Build: Permit-text parser reads "wreck/wrecking" as demolition
- **Question:** Does the shared parser recognise Minneapolis's demolition wording?
- **What I did:** Verified a bug reported by WS-MN (#89): "Wrecking a single family dwelling" parsed as a *new* single-family home with 1 unit, and "WRECK garage and house" wasn't recognised. Added `wreck`, `wrecks`, `wrecked`, `wrecking` to the demolition rule (rule 7), with tests.
- **Inputs:** WS-MN round-2 report.
- **Outputs:** `src/lotline/parse/permit_text.py`, `tests/core/test_permit_text.py`.
- **Findings:** "demo" and "raze" already worked; only "wreck" was missing.
- **Decisions:** none.
- **AI:** The WS-MN agent found the bug; Claude Code (WS-CORE) verified and fixed it.
- **Open / next:** none.
