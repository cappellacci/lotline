### LB-NNN · 2026-11-02 · [engine] · Can the four-state data support D-024 and D-025, and what will the reruns be?
- **Question:** thread 14, tasks 2 and 3 (first half). Panel counts on the four states' data, checked against
  the readiness reports; then the dated D-024 and D-025 amendment entries, pushed before any estimate.
- **What I did:**
  - Ran both smoke counts (`estimate_mm.py --smoke`, `estimate_pooled_adu.py --smoke`) with the tag helper.
  - Pooled Texas into the D-025 panel (Ben, 2026-10-30), each city over the years its source counts ADUs in
    full; found Austin's ADU flag stops with HOME (2024) and cut Austin at 2023.
  - Found that Texas's "allowed before the window" placeholder (earliest-known, dated 2010-01-01) made El
    Paso a 2010 adopter; fixed in `rule_tags` on #264, with a test.
  - Added the one tag sensitivity (firm dates only) to both run scripts, and wrote the two amendment entries.
- **Inputs:** processed tables in `~/lotline-data` (OH and TX eligible tables rebuilt after #252);
  `config/reforms/*.csv`.
- **Outputs:** `reports/engine14/panel_counts.md`; the 2026-11-02 entries under D-024 and D-025 in
  `docs/analysis_plan.md`; `scripts/dev/estimate_mm.py`, `scripts/dev/estimate_pooled_adu.py`.
- **Findings:** D-024: 560 places, 27 treated, 20 adopting in 2010–2025; matches the readiness reports
  (differences explained: 16 Ohio townships, Monroe's permit-only rule). D-025: 80 places (MN 76, TX 4), 31
  treated, 3,192 ADU permits; MN matches the report's 43 + 28 exactly.
- **Decisions:** Ben, 2026-11-02: run the engine; keep the tag sensitivities light (one: firm dates only).
  Proposed in the entries, for Ben to confirm: NC and Ohio stay out of D-025 for now; Fort Worth's
  non-rental ADUs count; a dropped place leaves the panel entirely.
- **AI:** Claude Code (Opus 5.5) ran the counts, wrote the code changes, the report and the entries. Every
  count comes from the scripts' output. No estimate was run before the entries were pushed.
