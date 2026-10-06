# Lotline: Analysis plan (pre-registration)

**Status: DRAFT, not yet pre-registered.** Per the validation plan (§2, integrity rule 1), §3 of
`docs/research/lotline-validation-plan.md` (tests and pass/fail criteria) is copied here, reviewed by Ben, committed
and tagged `prereg-v1` **before any V3 outcome model runs**. Until then this file only records decisions made
ahead of pre-registration, so they aren't lost.

## Decisions and deviations log

Dated, append-only. Each entry says what changed from the research documents, why, and who decided.

### D-001 · 2026-10-06 · V0 BPS reconciliation tolerance
- **Was (validation plan §3, V0, proposed):** "BPS totals match exactly."
- **Now:** our BPS place sums must be **within 1% of Census's state total in every compared year**; years outside
  1% are listed in the V0 report for explanation. Exact matches are still counted and reported.
- **Why:** Census revises state and county totals after the annual survey with late reports and corrections that
  the place files don't always carry (Census BPS methodology), so exact agreement isn't achievable even with a
  correct pipeline. First run (2026-10-06): exact match MN 10/32, NC 28/31, OH 20/34, TX 6/34 years; within 1%
  MN 30/32, NC 29/31, OH 34/34, TX 21/34. The check is read as directional evidence that the pipeline counts what
  Census counts.
- **Decided by:** Ben, 2026-10-06 (PR #66).
- **Open:** Texas 2003–2014 runs 1–2% high (Denton County unincorporated, 2014); for WS-TX to explain.
