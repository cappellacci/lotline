### LB-NNN · 2026-10-19 · Deliverables: Gate fixes from the judging panel (D8 services, stricter doc checks)
- **Question:** Which of the judging panel's cheap gate findings can be closed now?
- **What I did:** Listed every external service the adapters call in `docs/disclosures.md` (it said "None so far"). Made `compliance_check.py` stricter: D4/D6 sections need at least 30 words each, D7 must cover per-state data available vs. used and re-identification/small-cell risk, and D8 must name every external service found in `src/` (WARN while `stage = "build"`, FAIL at submission). Updated the README status and added why Apache-2.0. Removed the unused `duckdb` dependency. Added holdout window edge tests (last day hidden, next day not).
- **Inputs:** judging run 2026-10-19-0518 (gatekeeper D8 and checker audit; replicability RS-03, RS-08, RS-09; transparency TR-05).
- **Outputs:** `docs/disclosures.md`, `compliance_check.py`, `README.md`, `pyproject.toml`, `uv.lock`, `tests/core/test_holdout.py`.
- **Findings:** The stricter checker now reports D4 (7 stub sections), D6 (4 stub sections) and D7 (2 missing topics) as WARN; D8 passes. Against the old disclosures text it reports all six services undisclosed.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) wrote the changes; checked the new checker functions against the old and new texts; all tests pass; compliance 0 FAIL, 8 WARN.
- **Open / next:** write D4 (Model & Assumptions) and the D7 per-state table so the WARNs clear.
