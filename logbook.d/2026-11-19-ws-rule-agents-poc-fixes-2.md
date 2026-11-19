### LB-NNN · 2026-11-19 · rule-agents · What else broke on real Vermont towns?

**Question.** After the first fixes (#494), the three rule swarms ran on Burlington (dead links after a site
redesign) and South Burlington, VT (a working CivicPlus site), in a throwaway data folder with no import. What
still breaks before the agents go into the multi-state setup guide?

**Outputs.**
- `common/docstore.py` `sniff_ext`: documents are typed by their first bytes, so a PDF from a link with no
  `.pdf` (CivicPlus `DocumentCenter/View/<n>/<name>`) is stored and read as a PDF (was `.html`, raw bytes).
- `common/fetch.py`: a login page, bot challenge or code-host shell is recorded as a blocker and never stored
  (a news site's login page had been stored as a fee schedule and offered as "already held").
- `common/handoff.py`: a dead-link tip gives the exact Wayback address.
- Fees CLI: `reconcile` with no second-coder file, a `rows.csv` with its header when there are no rows (import
  reports 0 instead of failing), one task per place/body/component/page; command uses `find` not a glob.
- ADU: `worklist` no longer crashes for a state with no settings file (holdouts); scout, coder and second coder
  record fetches/searches in the ledger and `coded_at`; only the orchestrator records tokens (ADU's ledger
  had counted some twice).
- MM command: skip the verifier on a final with no rules.
- Tests for each.

**How Claude did it and how it was checked.** Claude (Opus 5.5) ran five test sessions (MM, ADU and fees on
one place each), read their bug reports, reproduced the PDF and empty-run failures, wrote the fixes in a
separate worktree so running tests were not disturbed, and added regression tests; rule-agent tests pass,
ruff clean, compliance 0 FAIL. South Burlington's ADU run proposed one schema-valid row with page-cited quotes.
