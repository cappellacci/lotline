### LB-NNN · 2026-11-09 · `app` · The app goes live on GitHub Pages (release app-2026-11-09)
- **Question:** can the static app be published from this machine's results so a judge can open it without
  running anything?
- **Decided by:** Ben, 2026-11-09 ("merge and push the release").
- **Outputs:**
  - PR #334 merged (deploy workflow and `scripts/publish_app.py`). Pages was already set to deploy from
    GitHub Actions.
  - The five bundles were rebuilt at main 39d1b08: run E numbers, the baseline part and D-068.
  - Release https://github.com/cappellacci/lotline/releases/tag/app-2026-11-09: five bundles and the data
    dashboard summary of 2026-11-05.
  - Pages run 42643820577 succeeded, so the app is live at https://cappellacci.github.io/lotline/.
  - `challenge.toml` `tool_url` now holds that address (D1).
- **What Claude did and how it was checked:**
  - Ran the publish script in check-only mode, then with `--go`, and watched the workflow to success.
  - Opened the live page in the in-app browser: the Results tab shows the MN figures and the baseline card,
    the provenance footer is there, a TX deep link (`#data?state=TX`) loads the data tab with the
    dashboard, and the console shows no errors.
- **Open:**
  - D3 and the README still ask for a check of the page in a private window. Ben should do that.
  - The ubuntu-latest runner label moves to Ubuntu 26, per a workflow annotation; no action is needed yet.
