### LB-NNN · 2026-11-27 · review · Republished the live site (app-2026-11-27)

**Question:** Does the public page show the reviewed code and the corrected missing-middle ranges?

**Outputs:**
- Release `app-2026-11-27`, built from main a42ba317 (after #570–#581) and deployed to
  https://cappellacci.github.io/lotline/.
- `README.md`: a "Try it" link at the top. `challenge.toml`: the tool_url comment names the new release.

**What Claude did:**
- From a clean checkout of main, ran `lotline run --offline`, which rebuilt every state's tables from the
  cache (no downloads), then ran results and the page.
- Two sources had no complete cache and kept their stored tables: `rochester_permits` (MN) and
  `clt_udo_translation` (NC).
- NC reran once the Census key was found (the clean checkout had no `.env`).
- Checked the bundles against app-2026-11-24f:
  - Fees fell in MN and OR (the feasibility channel off, A17).
  - Missing middle rose 0–8% in MN, NC, OH, OR and TX.
  - Wisconsin's missing middle fell 50% (dose pools, A13) and its ADU fell 15% (rule priors, A5). The MM
    and ADU sessions traced both to their analysis_plan entries.
- `publish_app.py --go`, then Pages deploy run 46017503371.

**Checked:** on the live page:
- the new wording is there, with no internal note;
- the chart caption shows;
- the Minnesota headline reads 1,730 homes.

Every bundle carries schemas 1.26, commit a42ba317, a clean tree and its input hashes. Compliance 0 FAIL.
