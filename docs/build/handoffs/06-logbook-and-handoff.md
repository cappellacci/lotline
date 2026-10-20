# Thread 6: Fold logbook fragments; refresh HANDOFF (WS-CORE-HOUSEKEEPING)

**Goal:** bring `LOGBOOK.md` and `HANDOFF.md` up to date. HANDOFF is stale (judging-panel gatekeeper finding), and about 60 `logbook.d/` fragments are waiting.

**Read first:** `LOGBOOK.md` (template, story-so-far table, last entry LB-086); `logbook.d/README.md`; `scripts/dev/merge_logbook.py`; `HANDOFF.md`; `docs/analysis_plan.md` D-001 to D-023.

**Deliver (one PR):**
1. **Logbook fold:** run `scripts/dev/merge_logbook.py` (dry run first).
   - **Numbering:** fragments get LB numbers in chronological order. Check for duplicates of LB-083 to LB-086, which the nightly review already wrote directly. Keep the earlier entry and fold the fragment's extra detail into a new "addendum" entry referencing it; never rewrite old entries.
   - **Story so far:** update the table for the new phase (scenario engines, ordinance research).
2. **HANDOFF refresh:**
   - **Status:** current status per workstream.
   - **Decisions log:** add Ben's decisions of 2026-10-19/20, by D-number and PR, from the analysis plan and PR descriptions.
   - **Open items:** Ben's manual list (Wake files, Mecklenburg request, ordinance PDFs, adoption-date lookups, gatekeeper checklist E1/E6, Handbook wording, `prereg-v1`).
   - **Dates:** Nov 17 freezes, Dec 16 deadline.
   - **Remove** the "repo not created yet" text and update the §3 checklist ticks that are verifiably done.
   - Facts only, each traceable to a PR or doc.

**Done when:** PR open with green CI; `merge_logbook.py` leaves `logbook.d/` empty except README.
