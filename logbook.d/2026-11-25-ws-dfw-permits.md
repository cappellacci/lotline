### LB-NNN · 2026-11-25 · Review · Dallas permit ids kept as text; Fort Worth dating checked (thread 17, A29)

- **Question:** Does the Dallas adapter drop non-numeric permit numbers, and should Fort Worth date permits by issue
  rather than filing?
- **Outputs:** `src/lotline/adapters/states/tx/dallas_permits.py`; test in `tests/states/tx/test_dallas_permits.py`;
  review row A29 in `reports/review/2026-11-code-review.md`.
- **Decision:** Ben, 2026-11-25: "Yes, do A29". No HANDOFF decision.
- **What Claude did and how it was checked:** Claude Code measured both on the cached 2026-11-11 snapshots with the
  network blocked. Dallas has no non-numeric or zero-led ids, so the fix (keep any other id as text) is a guard: the
  built table is identical to `main`'s (134,124 rows, compared frame for frame). Fort Worth keeps an Issued status
  date for only 7,924 of 297,818 permits, so switching would mix two date rules; the documented filing-year rule was
  kept and the reason logged.
