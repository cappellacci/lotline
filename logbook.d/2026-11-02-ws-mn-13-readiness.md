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
- **Second-coder return (2026-11-02, same PR):** Ben's second agent (Codex) filled all 109 rows: 8 yes, 92
  partly, 9 no. It also wrote over the sheet's left-hand columns; our coding as sent is the sheet at 54e9727.
  - `scripts/dev/mn_second_coder_2026_11_02.py` appends each finding to `coding_notes` and marks the 8 agreed
    rows `agree`; no coded value changes (idempotent; `test_reforms` now allows agreed rows).
  - `docs/research/ordinances/mn-second-coder-decisions-2026-11-02.csv`: 62 recommended actions for Ben
    (delete Hopkins 2024 and Grant 2016, date fixes for Mounds View, Burnsville and Columbia Heights, field fixes
    for Chanhassen, Richfield and Oakdale, `[predates]` for Fridley, Forest Lake and Rochester MM, and
    DATE UNCONFIRMED tags with lookups for rows the reviewer could not confirm).
  - The agent's other files are committed: research tracker, evidence register, PDF inventory and issues
    note. Its 17 downloaded PDFs are kept locally; `docs/research/ordinances/*.pdf` is now gitignored.
  - **AI:** Claude Code (Opus 5.5) compared each reviewer row with `mn.csv` and drafted the recommendations;
    the Hugo recommendation was corrected after finding it would overwrite Ben's own lookup (Ord. 2011-460).
- **Open / next:** Ben's decisions on the 62 rows, then a decisions script and a readiness recount; lookups;
  M6–M8.
