### LB-NNN · 2026-11-03 · Literature: missing-middle uptake anchor for the mechanism route (D-038, proposed)
- **Question:** what yearly uptake hazard and ramp should the missing-middle scenario use under D-037's route 1,
  and what external evidence supports them?
- **What I did:**
  - Compiled published by-right missing-middle production in a common unit: projects and homes per 1,000
    eligible parcels a year at maturity, plus the ramp. Places: Portland RIP, Houston, Auckland, Lower Hutt,
    SB 9, Oregon HB 2001 cities, Spokane, Arlington, Austin HOME and Edmonton.
  - Checked the key figures against the source PDFs: Portland's annual per-lot rates and 514 units; Houston's
    1,392 projects on 282,770 parcels; Auckland's 0.045 per parcel.
  - Proposed the anchor, units per project and ramp, and drafted D-038 before any missing-middle scenario number.
- **Inputs:** evidence register E001, E004, E021, E022, E024, E026–E028; D-014, D-019, D-030, D-037;
  `config/params/hazard.yaml`.
- **Outputs:**
  - `config/params/mm_hazard.yaml` (4 parameters);
  - `docs/research/mm-uptake-evidence.md`;
  - register rows E105–E113;
  - D-038 in `docs/analysis_plan.md`;
  - the parameter table in `docs/model_and_assumptions.md` (regenerated).
- **Findings:**
  - Only Portland and Houston publish an eligible-lot denominator.
    - Portland: 0.85 projects (2.9 homes) per 1,000 lots in 2023; 0.55 averaged over 2021–24.
    - Houston: 0.35 per 1,000.
  - Proposed central 0.5 per 1,000 (range 0.15–2.0) at Portland's market; ramp half-way at 2.5 years (1.5–5).
  - SB 9 sits below the range as a restricted rule, and Auckland above it as an extreme market.
- **Decisions:** D-038 proposed, for Ben.
  - It deviates from D-037's file choice: the parameters go in `mm_hazard.yaml`, because a new `hazard.yaml` key
    would shift the ADU draws.
  - Minneapolis, Durham and Raleigh (D-037 test places) set no value. No Charlotte, Mecklenburg or St. Paul
    outcomes were read.
- **AI:** Claude Code (Opus 5.5) did the work.
  - Three research subagents read the sources, and Claude chose the values.
  - Figures marked "derived" are Claude's arithmetic, shown in the evidence doc. Some yearly counts are read from
    charts.
  - No model, estimation or scenario code was run.
- **Open / next:** the Portland reference market script; a missing-middle feasibility dispersion; the
  current-rules increment; Portland's permit series by zone and year to replace the chart reads.
