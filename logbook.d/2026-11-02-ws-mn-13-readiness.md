### LB-NNN · 2026-11-02 · Validation: Minnesota data readiness (thread 13, M5)
- **Question:** for every model input across Minnesota's 1,053 jurisdictions, what is real and what is a
  fallback? What does Minnesota add to the D-024 and D-025 panels, and what is left open?
- **What I did:**
  - Counted the rebuilt processed tables (after #261) and the rule rows (with #260) with a read-only script.
    Every outcome table is filtered for the holdout first, and rolls with the snapshot rule.
  - Wrote the MN second-coder sheet, panel-event rows first.
  - Refreshed the MN rows of `docs/data_availability.md` and wrote thread 8's closing section.
- **Inputs:** `~/lotline-data/processed/mn` (rebuilt 2026-11-02), `config/reforms/mn.csv`,
  `config/fees/mn.csv`.
- **Outputs:**
  - `docs/build/mn-readiness.md`;
  - `scripts/dev/mn_readiness_counts.py` and `scripts/dev/mn_second_coder_sheet.py`;
  - `docs/research/ordinances/mn-second-coder-2026-11-02.csv`;
  - `docs/data_availability.md` (MN rows);
  - the closing section of `docs/build/handoffs/08-minnesota-data-complete.md`.
- **Findings:**
  - 539 jurisdictions count from parcels (86% of the population).
  - D-025 has 74 MN places (45 changes, 29 controls), plus 109 covered places with no rule. D-024 has 100
    places of 10,000+, with 2 in-window events.
  - All 109 rule rows are single-coder.
- **Decisions:**
  - Ben, 2026-11-02: seasonal cabins (class 4c12) stay out of eligibility. The lake-township undercount
    against ACS is accepted, and Aitkin, Cass and Cook stay on ACS.
  - Proposed: "none" rows are controls, never events, in panel counts.
- **AI:** Claude Code (Opus 5.5) wrote the scripts and docs. Every count comes from the script's output. An
  early draft counted Rochester's one-home row as an event; that was caught and fixed before writing. No model
  run.
- **Open / next:** Ben's second-coder pass and lookups; M6–M8.
