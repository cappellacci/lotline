### LB-NNN · 2026-11-27 · Admin: commit the nightly logbook entries and archive the fragments they cover
- **Question:** why does the logbook on GitHub stop at LB-104 (Nov 5), and how do we bring it up to date without logging the same work twice?
- **What I did:**
  - Found that the nightly review had written LB-105 to LB-228 (Nov 6–27) into `LOGBOOK.md` in the main checkout but never committed them, while 426 fragments sat unfolded in `logbook.d/`.
  - Committed those nightly entries unchanged.
  - Moved the 411 fragments committed before the nightly's last scan (2026-11-27 08:38 UTC) to `logbook.d/archive/`, which `merge_logbook.py` ignores. The 15 fragments added after the scan stay in `logbook.d/` for the next fold.
- **Outputs:** `LOGBOOK.md`; `logbook.d/archive/` and its README; a note in `logbook.d/README.md`.
- **Decisions:** Ben chose to keep the nightly summaries and archive the fragments rather than fold all 426 as separate entries.
- **AI:** Claude Code found the gap, sorted fragments by the commit time that added them, and checked that the fold script's dry run reads only the 15 remaining fragments.
- **Open / next:** the main checkout's uncommitted `LOGBOOK.md` matches this PR, so after it merges that local edit can be discarded before pulling.
