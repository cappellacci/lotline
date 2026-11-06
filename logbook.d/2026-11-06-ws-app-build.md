## LB-xxx · 2026-11-06 · WS-APP · The app page build: one static page from results bundles

**Question answered:** Can the app be built as one self-contained page from whatever results bundles exist, with no server, no network and no state names in the code?

**Outputs**
- `src/lotline/app/build.py`: finds `reports/results/<st>/bundle.json`, validates each with `model.results.read_bundle`, orders states by role, embeds them as JSON and inlines the identity (`docs/build/identity/tokens.css`, the wordmark as data-URI images) into `src/lotline/app/template.html`; writes `reports/app/index.html` (gitignored).
- `scripts/build_app.py` (`--bundle` for named files, e.g. the synthetic fixture; `--results`, `--out`). `lotline.app.build.build_app()` is the function `lotline results --all` calls.
- `src/lotline/app/template.html`: masthead, state picker grouped by role, the three sections (Results, The data, How well does it hold up?) as shells, and a provenance footer (commit, run time, engine and schema versions, config hash, draws, build time) with the one regenerate command.
- `tests/app/test_build.py`: builds from the committed fixture and finds every section; embedded bundle equals the file; role order with three made-up states; invalid and duplicate bundles refused; JSON can't close its script tag; no external scripts or styles; no configured state code in app code.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) wrote the build, template and tests against WS-ENGINE's fixture on `ws/engine-results-schema` (PR #311), without editing its files. Checked by the tests above, ruff, `compliance_check.py`, and by opening the built page in a browser (light theme; caught and fixed the two wordmark SVGs' shared `<style>` recolouring each other when inlined).
