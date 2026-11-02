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
- **More of Ben's lookups (same PR):** St. Louis Park lead (Council likely 2020-10-05) noted; Richfield ADU
  re-dated to 2015-07-01 `[earliest-known]`; Richfield Bill No. 2023-2 added as a D-024 event (duplexes by right
  in R, passed 2023-01-24), so D-024 now has 3 in-window events; Eagan's ADU ordinance noted as Ord. 528;
  Crystal confirmed (Ord. 2017-07, the UDC: adopted 2018-01-02, effective 2018-02-10). Now 24 of 53 D-025 event
  rows DATE UNCONFIRMED; 25 places with a confirmed-date event. Rosemount confirmed (Ord. 2024-04, 2024-06-04,
  a new authorization per Dakota County) and its fields filled: 23 unconfirmed, 26 confirmed places. Wayzata
  confirmed (Ord. 811, adopted 2022-06-21, effective 2022-06-30) and filled: 22 unconfirmed, 27 confirmed places. Plymouth
  confirmed (Ord. 2023-12, 2023-09-12; expanded the 2002 above-garage rule): 21 unconfirmed, 28 confirmed places. White
  Bear Lake confirmed (Ord. 25-07-2080, CUP to by right, effective 2025-08-20): 20 unconfirmed, 29 confirmed.
  Stillwater's 2017 date is Ord. 1093 (short-term rentals); ADUs date from the late 1990s, so the row is
  `[predates]`: D-025 73 places (45 changes, 28 controls), 19 of 52 event rows unconfirmed, 29 confirmed places.
  Mound confirmed (Ord. No. 7-2024, adopted 2024-10-22, effective 2024-11-03): 18 unconfirmed, 30 confirmed.
  Ramsey confirmed (Ord. 22-04, adopted 2022-02-08, effective 2022-03-14): 17 unconfirmed, 31 confirmed.
  Rogers: effective 2020-05-26 confirmed by the official code, adoption unknown, `[earliest-known]` (the prior
  chapter was not found): 16 unconfirmed, 32 confirmed; 7 `[earliest-known]` event rows.
  Golden Valley confirmed (adopted 2022-11-01, effective 2022-11-11; Ord. 745 vs 746 noted): 15 unconfirmed,
  33 confirmed. Inver Grove Heights 2015 confirmed (Ord. 1305, adopted 2015-08-24, effective
  2015-11-02): 14 unconfirmed. Andover confirmed (signed Ord. 463, 2016-06-21): 13 unconfirmed, 34
  confirmed. Roseville 2021 confirmed (Ord. 1606, 2021-11-08); the 2011 row's cap corrected
  to 600 sq ft: 12 unconfirmed.
- **Open / next:** the 12 unconfirmed dates; whether Stillwater's 2021 RA expansion was adopted; R's two-family rule before 2023 (to confirm Richfield is a change);
  M6–M8.
