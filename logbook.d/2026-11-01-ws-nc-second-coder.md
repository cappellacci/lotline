### LB-NNN · 2026-11-01 · data/NC · Which NC rule rows need a second coder, and what should they check?

**Question.** None of the 66 local NC rule rows has a second coder. Ben will hand them to a second agent for review.

**Outputs.** `docs/research/ordinances/nc-second-coder-2026-11-01.csv` (66 lines: 28 priority 1, 31 priority 2, 7 priority 3), in the Texas worksheet's format; README entry.

**How Claude worked and checked.** Generated from `config/reforms/nc.csv` on main at f9d9624: one line per row not from S.L. 2026-59, with what was coded, a check list built from each row's flags (`[earliest-known]` dates, rows resting on Ben's search-summary lookups, rows contradicting a lookup) and the source with the local file name. No rule rows changed.
