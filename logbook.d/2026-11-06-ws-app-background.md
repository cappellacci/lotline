## LB-xxx · 2026-11-06 · WS-APP · App page on paper-raised, cards on paper

**Question answered:** Ben (2026-11-06) found the page background washed out and chose option C from three token swatches: the page on `paper-raised` (#fffdf9) and cards on `paper` (#f7f4ee).

**Outputs**
- `src/lotline/app/template.html`: two app surface variables, `--app-page` and `--app-card`, used by the body, masthead line, menu bar, cards and table headers.
- `src/lotline/app/build.py`: the folded data dashboard follows the same mapping.
- The tokens and `STYLE_GUIDE.md` are unchanged. The guide still says "set every page on paper", so updating it is the identity owner's call.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) made the change. Checked by `tests/app` and `compliance_check.py`, and by looking at the built page in a browser.
