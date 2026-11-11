### LB-NNN · 2026-11-11 · Study design: missing-middle methodology review (WS-MM-REVIEW step 1)
- **Question:** can the adopted missing-middle method (D-054 (b), adopted by D-055) give an accurate statewide
  number, and what would the ADU-style rebuild (D-074 to D-081) take for missing middle?
- **What I did:**
  - Read the MM D-entries (D-014 to D-071), the causal diagram, the uptake evidence, the MM params, code and
    reports, and the ADU rebuild entries and reports.
  - Inventoried the permit and roll sources on disk from column names and vocabularies only: no outcome counts,
    and no St. Paul or Ramsey file opened.
  - Listed every coded MM reform in the five states, with its tags and fit status.
  - Answered the brief's nine questions, each with options, costs and a recommendation.
- **Inputs:** `docs/analysis_plan.md`, `docs/research/lotline-causal-diagram-mm.md`,
  `docs/research/mm-uptake-evidence.md`, `docs/build/nc-readiness.md`, `config/params/mm_hazard.yaml`,
  `config/reforms/*.csv`, `reports/mm-d0*/`, `reports/v9-oregon-d055/`, `reports/v5-charlotte/`, the ADU rebuild
  reports, and `docs/data_provenance.md`.
- **Outputs:** `docs/research/mm-methodology-review-2026-11.md`.
- **Findings:**
  - The fit's signal rests on six NC towns whose events are `[earliest-known]` code-rewrite dates. The NC
    readiness doc warned not to use them until predecessor codes are compared. Without NC, θ falls from 0.12 to
    0.013 per 1,000.
  - Oregon (up to 65 places with a 2016–23 cap rise, 268 of 275 rows second-coded) is the largest untapped source.
  - About 11 permit sources on disk carry unit counts and parcel IDs, and four areas have paired rolls. That
    makes permit-level counts, a roll check and a within-city design possible without new downloads.
  - The ADU/MM overlap is not coded: `overlap_share` is always NaN, and duplex/ADU class boundaries can
    double-count.
- **Decisions:** none. The options and the proposed sequence are for Ben. Pre-registration (a D-entry) follows
  his picks.
- **AI:** Claude (Opus 5.5) wrote the review. Three read-only subagents did the source inventory, the
  treated-place list and the ADU-template summary. Key claims were spot-checked against the files: the
  `nc-readiness.md` §2 warning, `rule_tags.py`, `results.py` `overlap_share`, `scenarios/mm.py:254`, and the 69
  place-years in `reports/mm-d042/places.csv`. Nothing was run, fitted or downloaded.
- **Open / next:**
  - Ben picks options.
  - Rules sessions for the 13 event checks.
  - A method-only D-entry.
  - Per-state counting sessions.
