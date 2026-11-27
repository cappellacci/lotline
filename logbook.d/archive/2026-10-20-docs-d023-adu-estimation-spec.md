### LB-NNN · 2026-10-20 · Methods: ADU effect re-specified as a staggered-adoption count model (D-023, pre-registered)
- **Question:** What statistical method estimates the ADU effect, consistent with the causal diagram and the protocol?
- **What I did:** Ben judged the D-019 calibration to be trend-chasing. Re-read the causal diagram (§3, §5), statistical protocol (§5.5–5.8) and methods review (§2b, §4), and wrote D-023 before any fit: PPML with place and year fixed effects, Wooldridge's extended TWFE for staggered adoption, event-time effects, pre-adoption effect modifiers (price-to-cost, home value, pre-reform permit rate, household growth), a rate × treatment term and an ADU↔missing-middle substitution term; wild cluster bootstrap plus randomization inference; falsification checks; an out-of-sample transport test on Austin, Raleigh and Durham with pass rules.
- **Inputs:** `docs/research/lotline-causal-diagram.md`, `lotline-statistical-protocol.md`, `lotline-methods-review.md`; Met Council permit coverage (186 metro places, ADU flags 2016–2025).
- **Outputs:** `docs/analysis_plan.md` (D-023).
- **Findings:** Only 25 metro places had dated ADU rules; an adoption-date run for the other 162 started the same day.
- **Decisions:** D-023 (Ben, 2026-10-20).
- **AI:** Claude Code (WS-CORE) wrote the specification from the project's research documents.
- **Open / next:** WS-ENGINE builds `model/estimate_adu.py` with simulation-recovery tests, then runs it once after the adoption dates are coded.
