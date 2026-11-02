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
    note. Its 14 downloaded PDFs moved to `LOTLINE_DATA_DIR/manual/mn/second_coder_2026-11-02/` (as NC); `docs/research/ordinances/*.pdf` is gitignored.
  - **AI:** Claude Code (Opus 5.5) compared each reviewer row with `mn.csv` and drafted the recommendations;
    the Hugo recommendation was corrected after finding it would overwrite Ben's own lookup (Ord. 2011-460).
- **Decisions applied (2026-11-02, same PR):** Ben accepted all 62 recommendations.
  - `scripts/dev/mn_second_coder_decisions_2026_11_02.py` (idempotent): 60 rows adjudicated, 2 deleted (Hopkins
    2024, Grant 2016), Forest Lake recoded as `MN-2721770-adu-2023`; 3 `[predates]`, 31 DATE UNCONFIRMED; 36
    lookups written to `docs/research/ordinances/mn-second-coder-lookups-2026-11-02.csv`.
  - Recount (`mn_readiness_counts.py`): D-025 has 72 places (44 changes, 28 controls). Of the 51 event rows,
    31 are DATE UNCONFIRMED; only 16 places have an event on a confirmed date. D-024 events unchanged
    (Minneapolis 2020, St. Louis Park 2025, both now confirmed).
  - Updated the readiness report (new §6), the MN rows of `docs/data_availability.md` and thread 8's closing.
  - `tests/states/mn/test_reforms.py` now allows adjudicated rows, drops Forest Lake from the "no ADUs" set
    and pins Inver Grove Heights' filled `by_right`.
  - **AI:** a first run appended action text that named tags ("tag [predates]"), which the counts script would
    have read as real tags (Cottage Grove). Caught in a tag count, fixed by stripping the markers, rerun from
    the committed file.
- **HANDOFF decision (Ben, 2026-11-02, accepted as option 1):** `DATE UNCONFIRMED` in `coding_notes` marks a dated event with no signed
  ordinance or effective-date record. It still counts as an event; engines run with and without such rows.
- **Lookups applied (2026-11-02, same PR):** Ben's agent answered the 36 lookups; 33 repeat the second coder.
  Ben accepted four changes (`scripts/dev/mn_lookups_2026_11_02.py`, idempotent): Forest Lake 2023 becomes an
  event (Ord. 719), Fridley 2022 loses `[predates]`, Mounds View Ord. 1045 added as `-2025b` (Ord. 1042 row
  renamed `-2025a`), Burnsville 2020 deleted. Recount: D-025 74 places (46 changes, 28 controls); 32 of 53
  event rows DATE UNCONFIRMED; 17 places with a confirmed-date event.
  - Fixed on the way: `mn_readiness_counts.py` matched the bare word `earliest-known` (it appears in decision
    text); it now matches the `[earliest-known]` tag. The decisions script no longer overwrites the lookup file.
- **Hugo, Rochester and round 2 (2026-11-02, same PR):** Ben's own lookups settle Hugo (Ord. 2011-459,
  2011-10-03) and Rochester (R-1 one home per lot since 1998). His agent's second pass confirmed six adoption
  dates from official records (Lakeville, Medina 2011, Minnetonka, Vadnais Heights, Oakdale, Cottage Grove
  re-dated to 2023-01-01). Recount: 26 of 53 D-025 event rows DATE UNCONFIRMED; 23 places with a confirmed-date
  event. Ben then approved deleting Medina 2024 (Ord. 733 is a height rule) and adding Roseville Ord. 1418
  (2011-10-10, conditional to permitted) as `MN-2755852-adu-2011`. Final recount: 25 of 53 event rows
  DATE UNCONFIRMED; 24 places with a confirmed-date event.
- **Open / next:** the 25 unconfirmed dates; M6–M8.
