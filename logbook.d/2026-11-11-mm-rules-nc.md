### LB-NNN · 2026-11-11 · RULES: NC missing-middle second-coder checks (predecessor codes)
- **Question:** for the six NC towns whose `[earliest-known]` code-rewrite dates carry the missing-middle fit
  (Wilson, Wake Forest, Morrisville, Sanford, Burlington, Garner), and for Durham's EHC rows, when did duplexes
  or 2–4 units first become allowed by right on single-family lots, and what did the code allow just before?
  This is step 1 of the sequence after the MM methodology review (#392).
- **What I did:** read each predecessor code's use table and the new code's district-conversion table, mostly
  from Wayback copies.
  - Wilson: 1961-based code districts (2008 city page) and the 2013 UDO.
  - Wake Forest: Ord. #77-01 as amended to 2010.
  - Morrisville: Zoning Ordinance v9.2, 2010.
  - Sanford: the pre-2024 joint UDO.
  - Burlington: §32.9 of the 1971 code.
  - Garner: the 2003 UDO.
  - Durham: found EHC's effective date in the county's 2019-10-28 agenda, and looked for EHC2.
  - Rules only: no permit or BPS outcome was read, no CSV was edited, no records requests were made and no staff
    were emailed.
- **Inputs:** public ordinances and agendas (archived URLs in the report); nothing downloaded to `LOTLINE_DATA_DIR`.
- **Outputs:** `reports/nc/mm-rule-checks-2026-11.md`.
- **Findings:**
  - Garner 2022-07-05 is a real event (old UDO: duplexes only in MF-1/MF-2).
  - Wilson is a real event on 2013-01-18 in SR6 only (former single-family-only RA-10S/RA-8S).
  - Wake Forest, Morrisville, Sanford and Burlington are `[predates]`. Morrisville's R-12 and Burlington's R-15
    pockets gained duplexes but can't be sized.
  - Sanford's 2018-11-19 is a land-use-plan date, not a UDO date.
  - Durham city took effect 2019-10-01, not on the vote.
  - No effective date was found for Durham County.
  - There is no EHC2. SCAD (2024-01-01) adds no missing-middle event.
- **Decisions:** proposed in the PR: accept the row changes in the report's "Proposed CSV changes" table; a
  follow-up edits `config/reforms/nc.csv`.
- **AI:** Claude Code ran four research sub-agents, then checked the weak points itself:
  - Wilson UDO and the 2008 district list;
  - Burlington's table, read from the rendered page;
  - Morrisville's Table 1.6.5.

  Evidence seen only in search snippets is marked as such and never carries a tag on its own.
- **Open / next:** the method D-entry (step 2) should say how `[predates]` places and narrowed coverage enter the
  fit. Durham's ordinance PDFs (403) would confirm the urban-tier district list. Wilson's old use table was not
  found online.
