### LB-NNN · 2026-11-15 · ADU · Refit on the coverage-fixed rule rows (D-096)

- **Question:** after PR #440 corrected 33 rule rows, does A + place types change, and do the tests still hold?
  Ben: "Yes, fix then refit".
- **Outputs:**
  - D-096 in `docs/analysis_plan.md` (method committed before the fit, then the result);
  - `scripts/dev/adu_refit_fixed_rows.py` and `scripts/dev/adu_fixed_rows_page.py`;
  - `reports/adu-types-fixed-rows/` and `reports/adu-reform-ratio-fixed-rows/`;
  - page https://claude.ai/artifact/XNZB6mCqWFQzzModq2oeLQ.
- **Result:**
  - Place luck shrinks (α 1.70 → 1.44); m_x is 0.7 and the core term +1.67.
  - Held-out state ranges narrow (NC ×24 → ×18, TX ×71 → ×49), and the same decisions hold.
  - The reform check now has 6 real events; its reading is still "not shown".
  - Config is unchanged.
- **What Claude did:** reviewed PR #440 (spot checks of Charlotte, Forest Lake, Rosemount and Portland), wrote
  D-096, ran D-088's and D-095's scripts on that branch's rows without merging, and built the page.
- **How it was checked:**
  - inputs dry-run first: the placeholder years were cut, and a first attempt where they were not was caught
    and fixed;
  - two wrapper bugs (patch order, worker arguments) were found and fixed before any result was read;
  - ruff passes.
