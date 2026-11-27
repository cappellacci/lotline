## LB-xxx · 2026-11-08 · WS-APP · Publishing the app to GitHub Pages

**Question answered:** How does the app reach a public URL when results are built from downloaded data that can't be committed, and that CI can't rebuild?

**Outputs**
- `scripts/publish_app.py` (new) validates every `reports/results/<st>/bundle.json` and stages it as `<st>.bundle.json`, with the data dashboard summary staged as `data-summary.json`. It builds the page once from exactly those files. With `--go`, it creates a GitHub release at the current pushed commit with those files as assets, then starts the Pages workflow.
- `.github/workflows/pages.yml` (new, manual trigger with a `tag` input) checks out the release's tag, downloads its assets, runs `scripts/build_app.py --from-release release --out site` and deploys with `actions/upload-pages-artifact@v5` and `actions/deploy-pages@v5` (GitHub's own actions, MIT).
- In `src/lotline/app/build.py`, `stage_release()` copies each bundle byte for byte, names it by the bundle's own state code, refuses duplicates and clears stale assets. `release_inputs()` reads a downloaded release folder. `scripts/build_app.py` gains `--from-release DIR`.
- `README.md` has a new "The app" section covering how to open the page from disk and how to publish it. `tests/app/test_build.py` has 4 new tests.

**Why this route:** CI has no data and can't run the engine, and committing results (even to a `gh-pages` branch) would break the no-committed-data rule. Release assets aren't commits. Each release pins the exact results and code behind one published version, which helps replicability. Building at the tag keeps the template and schemas matched to the run.

**Not done:** Pages isn't enabled on the repo yet: Settings → Pages → Source "GitHub Actions" is a one-time step for Ben. There are no real results bundles yet, so nothing is deployed and `challenge.toml` `tool_url` stays empty until the first deploy works. It will be `https://cappellacci.github.io/lotline/`. Opening the deployed page in a private window still needs doing after the first deploy.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) wrote it. Checks:
- `tests/app` passed, 40 tests.
- `compliance_check.py` ran.
- `scripts/build_app.py --from-release` was run on a folder holding the fixture.
- `scripts/publish_app.py` was run without `--go` on a results folder holding the fixture; it staged `zz.bundle.json` and built the page.
- The workflow itself hasn't run, because it needs Pages enabled and a release.

**Proposed HANDOFF decision:** the published app is built in CI from a GitHub release of results bundles (made by `scripts/publish_app.py`). No results are committed.
