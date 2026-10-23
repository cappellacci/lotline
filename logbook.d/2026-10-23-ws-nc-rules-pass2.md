### LB-NNN · 2026-10-23 · data/NC · What ADU and missing-middle rules do nine more NC towns have, and since when?

**Question.** Ben sent ordinance documents for nine of the eleven NC places under 50,000 that the dev run (PR #213) drew rules for: Wilson, Indian Trail, Salisbury, Monroe, Fuquay-Varina, Cornelius, Sanford, Morrisville and Statesville (Goldsboro and New Bern still missing). Code their ADU and missing-middle rules from the primary text.

**Outputs.**
- `config/reforms/nc.csv`: 15 rows (9 ADU, 6 missing middle). No ADU row for Monroe (ADUs only in the Concord Avenue overlay); no missing-middle row for Fuquay-Varina or Indian Trail (duplexes not allowed in their single-family districts).
- `config/fees/nc.csv`: Wilson water and sewer system development fees ($1,407 + $2,425 per home, 3/4-inch meter) and tap fees (not in the per-unit total, as Raleigh's), schedule as of 2026-07-01. Goldsboro's fee sheet lists only planning application fees: no row.

**Findings worth knowing.**
- Statesville does allow ADUs (UDC Sec. 5.02(C): one per lot, lesser of 50% or 1,000 sq ft, owner-occupied), contradicting Ben's search summary.
- Statesville's 2026-06-01 amendment allows 2-4 attached units by right in R-8 and R-5 districts on lots of record before 2026-05-11.
- Salisbury's ADUs need a special use permit in its main residential districts (by right only in mixed-use districts).
- Wilson and Sanford's chapters carry no dates; their dates come from Ben's 2026-10-21 lookups and are marked as such. Most other dates are `[earliest-known]` (the ordinance's adoption date).

**How Claude worked and checked.** PDFs (in `~/lotline-data/manual/nc_udos/`, downloaded by Ben) were converted to text with pypdf. Three Claude subagents each coded three towns into candidate rows, reading use tables by cell position where the text lost the layout. Claude then checked every `source_quote` verbatim against the text, spot-checked the Statesville, Indian Trail and Salisbury ADU terms by hand, fixed the undated rows, noted every disagreement with Ben's lookups in `coding_notes`, and ran the NC and core tests and `compliance_check.py`. All rows are single-coder; none verified by a second person.
