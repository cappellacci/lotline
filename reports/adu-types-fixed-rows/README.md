# D-096: A + place types on the coverage-fixed rule rows

D-088's `adu_types_refit.py` and D-095's `adu_reform_ratio.py` (whose outputs are in
`reports/adu-reform-ratio-fixed-rows/`) were run through `scripts/dev/adu_refit_fixed_rows.py`. The wrapper
read PR #440's `config/reforms/*.csv` from its checkout and left out the `UNKNOWN-PLACEHOLDER` place-years
(Cottage Grove 2016–22, Maplewood 2016–23). The run was offline, with St. Paul excluded. The files are the same
as in `reports/adu-place-types-checked/`. Page: `results.html`, published at
https://claude.ai/artifact/XNZB6mCqWFQzzModq2oeLQ.

**Fit set:** 63 places and 446 place-years, down from 64 and 491. Rosemount leaves the fit, because before 2024
it is now an explicit no-ADU rule. Burnsville, Chanhassen and Vadnais Heights lose their no-ADU years.

**A + P, all states (checked rows → fixed rows):**

| | Checked rows | Fixed rows |
|---|---|---|
| θ | 0.200 | 0.240 per 1,000 |
| α | 1.70 | 1.44 |
| Core term | +1.84 | +1.67 (+1.06 to +2.32) |
| m_x | 0.8 | 0.7 |
| m_o | 1.0 | 1.0 |

**Tier-1 held-out ranges, P90 ÷ P10:**

| State | Checked rows | Fixed rows |
|---|---|---|
| MN | ×4.5 | ×4.5 |
| NC | ×24 | ×18 |
| TX | ×71 | ×49 |
| OR | ×22 | ×19 |

All four states stay useful.

**Decisions are unchanged:** D-088's rule keeps A over A + P because of tests A–B (College Station). A + P's
tier-1 gain is +12.0 (2 SE 7.2). A′ + P replaces A′.

**D-095 rerun:** 6 events, down from 10; the 4 placeholder artefacts are gone. The reading is still "not shown
either way": b is 1.25 (0.60 to 1.95), and the gain is +4.5 (2 SE 8.2).
