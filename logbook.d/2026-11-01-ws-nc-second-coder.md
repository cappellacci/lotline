### LB-NNN · 2026-11-01 · data/NC · Which NC rule rows need a second coder, and what should they check?

**Question.** None of the 66 local NC rule rows has a second coder. Ben will hand them to a second agent for review.

**Outputs.** `docs/research/ordinances/nc-second-coder-2026-11-01.csv` (66 lines: 28 priority 1, 31 priority 2, 7 priority 3), in the Texas worksheet's format; README entry.

**How Claude worked and checked.** Generated from `config/reforms/nc.csv` on main at f9d9624: one line per row not from S.L. 2026-59, with what was coded, a check list built from each row's flags (`[earliest-known]` dates, rows resting on Ben's search-summary lookups, rows contradicting a lookup) and the source with the local file name. No rule rows changed.

**Update (2026-11-01, thread 13).** Added a `panel_event` column and sorted the 24 D-024/D-025 event rows to the top (11 of them rest on `[earliest-known]` dates). Removed a `.venv` symlink that had been committed by mistake and broke CI (`uv sync` could not create `.venv`); `.gitignore` now also ignores a `.venv` symlink, since `.venv/` matches only directories.

**Review applied (same day).** Ben's second agent (Codex) reviewed all 66 rows plus 5 supplemental ones: 8 yes, 44 partly, 14 no. Claude filled the reviewer columns of the worksheet, applied agreements and notes (`scripts/dev/nc_second_coder_2026_11_01.py`, idempotent), and wrote `nc-second-coder-decisions-2026-11-01.csv` (20 items). Claude checked the disputed claims against the sources: Raleigh 2019 and Thomasville were already coded the way the reviewer describes; the reviewer's Thomasville 2017 ADU source is Thomasville, Georgia; Mint Hill's code contradicts itself on duplexes (use table SR, dimensional table conditional zoning); the reviewer's Goldsboro and New Bern geoids were wrong (3726880, 3746340). Most "no" verdicts say a coded date is a recodification and the rule is older: proposed `[predates]` tag.
