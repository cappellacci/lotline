### LB-NNN · 2026-11-09 · Study design: fee scenario plan and Phase 0 decisions (D-065)
- **Question:** After the 2026-11-03 office hours, what should the fee model still build, and which pending fee
  choices (D-032 to D-034, dollar year, revenue toggle, real-fee scenario) must be settled first?
- **What I did:**
  - Compared the office-hours asks (A4, A5, A8) with what exists: `scenarios/fees.py` (handbook and local
    modes, feasibility and elasticity channels, single-family dose only), `config/params/fees.yaml`, and the
    coded fee tables in `config/fees/` (MN 13, NC 16, TX 6, OR 4 places; duplex and fourplex rows coded in
    MN, NC and OR).
  - Drafted a four-phase fee plan: 0 decide; 1 fee levels by building type (#247, deflation, fill rule);
    2 SFD/duplex/fourplex pencil-out table, dose by building type, stacking with ADU and missing middle,
    fee-increase sensitivity; 3 V6b (#49) and tornado, Carthage (#46) only if time; 4 results bundle,
    D4 limits, D6 paragraph, one state for the ~Nov 17 office hours.
  - Recorded Ben's Phase 0 choices as D-065 and marked D-032 to D-034 with their status.
- **Inputs:** `docs/research/office-hours-2026-11-03-tomasso-notes.md`, Granola notes for the same meeting,
  `docs/research/lotline-causal-diagram-fees.md`, `config/params/fees.yaml`, `config/fees/*.csv`,
  `docs/analysis_plan.md` D-010, D-032 to D-034.
- **Outputs:** `docs/analysis_plan.md` D-065 (and status lines on D-032, D-033, D-034);
  `config/params/fees.yaml` note on the Handbook fee's dollar year.
- **Findings:**
  - Coded single-family fees are roughly $3k–$19k per home in MN, NC and TX and $24k–$36k in Oregon, so the
    Handbook's $50,000 is high everywhere we coded (A4's caveat holds).
  - `local_fees` sums each schedule's own dollars without deflating to 2025 (Phase 1 task).
  - The fee dose comes from the single-family prototype for every building size; Amy's main ask (duplex and
    fourplex with per-unit connection fees) needs per-type fee levels and pro formas (Phases 1–2).
- **Decisions:** D-065 (Ben, 2026-11-09): D-032 adopted (revenue replaced by default; single-family dose
  interim), D-033 adopted, D-034 replaced by a component-wise fill (no $50k fallback in local scenarios);
  three labeled fee scenarios (benchmark, real fees halved, real fees cut by up to $25k); Handbook dollars read
  as 2025; fee-increase sensitivity; fee-structure scenario as a stretch after Phase 2. Proposed for HANDOFF in
  the PR.
- **AI:** Claude Code read the notes, code, configs and fee tables, drafted the plan, asked Ben the three open
  choices, and wrote D-065. Fee ranges were computed with a short script over `config/fees/*.csv` (rough sums
  of single-family rows across years, not the scenario's newest-year rule). No model was run; the parameter
  table check passed.
- **Open / next:** Ben to confirm D-065's component-level details (which components are filled, 5-place
  minimum, pooled median). Phase 1: per-type fee levels, deflation, fill rule, #247.
