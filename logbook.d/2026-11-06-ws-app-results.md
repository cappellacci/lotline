## LB-xxx · 2026-11-06 · WS-APP · App section 1 (Results): ranges, share of need, funnel, live sliders, parity test

**Question answered:** Can the page show the engine's results as ranges and let a policymaker move assumptions live, without any model arithmetic in the browser beyond re-adding the engine's own draws, and is that proven against `model/aggregate.py`?

**Outputs**
- `src/lotline/app/aggregate.js`: the browser's only model arithmetic, a line-for-line mirror of `aggregate.homes_from_draws`, numpy-linear percentiles, `shareOfNeed` (as `aggregate.share_of_need`) and the slider shift.
- `src/lotline/app/knobs.yaml`: plain-language label, "why it matters" and end words for each slider, plus pointers (`file:key`) to the parameters behind it. `build.knobs()` resolves every value, range, unit and source from `config/params/` at build time; an unknown key raises.
- Section 1 of `src/lotline/app/template.html`: the confidence (overlap) flag with its glyph and word; the headline range for the chosen scenario; range bars for every scenario in the bundle, with baseline drawn first and unrun scenarios named as "not yet run"; a "net statewide / in the places that build" toggle; share of housing need for each denominator kind (headline first, with source and denominator range); the Legal → Pays → Built funnel (log widths, said so); a placeholder for the pencil-out table, which is not in the bundle; and one slider per draws factor with its source and range.
- `tests/app/test_aggregate_parity.py`: the JS under node against `homes_from_draws` for every factor shifted to q = 0/10/50/90/100 and for combinations; the unpinned JS equals the bundle's own `totals` and `need`; a hand-worked shift; values kept within 1; numpy-linear percentiles; unknown columns refused.

**Decision proposed for HANDOFF:** Sliders *shift* a factor rather than pin it. Every draw's value is multiplied by P_q / P50 of that factor (kept within [0, 1]), so the slider's centre is exactly the engine. Pinning was tried first and rejected. θ is back-solved per draw and moves against pencil-out, so fixing θ at one value broke that link and widened the fixture's range from 13–21 to 19–58 homes.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) wrote the module, the template section and the tests. Checked by the parity tests above, `tests/app` (20 passed), ruff and `compliance_check.py`, and by driving the built fixture page in a browser: light and dark themes, desktop and 375 px width, sliders moved and reset by script.
