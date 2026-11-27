### LB-NNN · 2026-11-24 · Review · Clearing the open pull requests and republishing the app (thread 17, part B)

- **Question:** Which open pull requests still belong on `main`, and does the public app show the results
  after D-060's port?
- **Outputs:**
  - `reports/review/2026-11-code-review.md`, B1 outcome.
  - Release `app-2026-11-24e` on https://cappellacci.github.io/lotline/.
  - No open pull requests remain.
- **Decisions (Ben, 2026-11-24):**
  - "Close the PRs then republish the app".
  - "close out the other 6 PRs, get this to be as close to deliverable as possible".
- **What Claude did and how it was checked:**
  - Claude Code merged twelve PRs only after their CI passed, and closed seven more, each with a reason in
    a comment. #507's test conflict was resolved by keeping both tests; the 74 app tests pass.
  - Dependabot's rebases moved pandera to 0.36.0 and ruff to 0.17.6, both MIT.
  - Built six state bundles from a clean checkout of `main`, one at a time. They match the D-060
    before/after run exactly.
  - Published with `scripts/publish_app.py --go` using the previous release's data summary.
  - Checked the live page: six states on the map, MN's ADU P50 at 601.
