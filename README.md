# Lotline

A transparent, open-source simulator of how state housing reforms (missing middle, ADUs, development fee cuts) change
housing production over five years, compared with a no-change baseline.

> Status (October 2026): building. Data adapters for Minnesota, North Carolina, Texas and Ohio and the
> baseline forecast are in place; the scenario engines, interactive tool and final documents are in progress.
> See `HANDOFF.md` and `docs/build/BUILD_PLAN.md`.

## Command contract

The three commands reviewers use to reproduce Lotline from a clean checkout. They need
[uv](https://docs.astral.sh/uv/getting-started/installation/) and nothing else (uv installs Python 3.12 if missing).

| Step  | Command | Notes |
| ----- | ------- | ----- |
| Setup | `uv sync --frozen` | Installs the exact pinned dependencies from `uv.lock` into `.venv/` |
| Run   | `uv run lotline --help` | Command-line tool for now; the interactive app arrives in Phase 5 and this row will name its command |
| Test  | `uv run pytest -q -n auto` | Runs every automated test in parallel (small synthetic fixtures, no downloads); about 12 minutes on a laptop. `uv run pytest -q -m "not slow" -n auto` is the 3-minute check that skips 40 long simulation-recovery fits |

Commands that download data need a `.env`: copy `.env.example` to `.env` and fill in the values (see [Data](#data)).

## Documentation

- [Model & Assumptions Overview](docs/model_and_assumptions.md): how the tool works and what it assumes
- [Policy Scenario Comparison](docs/policy_scenario_comparison.md): scenario ranking and what drives it
- [Data Provenance](docs/data_provenance.md): sources, licenses and preparation steps
- [Disclosures](docs/disclosures.md): AI tools, models, external services and dependency licenses
- [Data dictionary](docs/schemas.md) and [analysis plan](docs/analysis_plan.md)
- [Calibration](docs/calibration.md): where every fitted number comes from, and `lotline calibrate` to reproduce it
- [Adding local rules with the rule agents](docs/adding_local_rules_with_agents.md): research a state's
  missing-middle, ADU and fee rules with your own Claude account, then review and import them

## License

Licensed under the **Apache License 2.0** (Apache-2.0). See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Why Apache-2.0: it is permissive, so any state agency, researcher or vendor can reuse and adapt Lotline,
including in their own tools, without having to open their code; it adds an explicit patent grant and requires
that changes be noted, which suits public-sector reuse; and it is one of the licenses the Challenge accepts.

## Setup

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs Python 3.12 if missing). One command:

```bash
uv sync --frozen
```

This creates `.venv/` with the exact pinned versions in `uv.lock`. Then:

```bash
uv run lotline --version
```

### Data

Source data is never committed. Scripts download it into `LOTLINE_DATA_DIR` (default `~/lotline-data`, outside the
repo) and record each download in `manifest.jsonl` there. Copy `.env.example` to `.env` to set the directory or API
keys.

```bash
uv run python scripts/fetch_data.py --state MN --source bps
```

`uv run lotline sources` lists every source per state (national ones plus any in
`src/lotline/adapters/states/<st>/`). The ACS needs a free Census API key: sign up at
https://api.census.gov/data/key_signup.html, click the activation link Census emails you, and put the key in
`.env` as `CENSUS_API_KEY=...`. The key is sent with each request but never written to the download manifest.

To rebuild the processed tables after a code change without downloading anything, add `--offline`
(`uv run lotline fetch --state NC --offline`). Each source then reads the newest complete raw snapshot already
in `LOTLINE_DATA_DIR`, sends no request, and fails with a clear message if nothing usable is cached; a newer
snapshot with missing pages is skipped with a note. What each offline build read is appended to
`manifest.builds.jsonl`. Without `--offline`, ArcGIS and Socrata sources take a new dated snapshot each day.

`docs/data_provenance.md` is generated from the download manifest; regenerate it after fetching:

```bash
uv run lotline provenance --write
```

## The app

The app is one static page. Build it from the results under `reports/results/` (made by
`uv run lotline results --state XX`):

```bash
uv run python scripts/build_app.py
```

It writes `reports/app/index.html` and one `reports/app/states/<st>.js` per state. Open `index.html` straight
from disk in any browser; it needs no server or internet connection. Keep the `states/` folder next to it,
because the page loads a state's file when you pick that state. To try the page without data, build it from the
synthetic test bundle: `uv run python scripts/build_app.py --bundle tests/fixtures/results/zz/bundle.json`.

The published copy lives on GitHub Pages. No results are committed: `scripts/publish_app.py` checks that every
bundle renders, then with `--go` uploads the bundles as assets of a GitHub release tagged at the current
commit. It also starts `.github/workflows/pages.yml`, which rebuilds the page from that release with the code at
that tag and deploys it. Each release keeps the exact results behind one version of the published page.

```bash
uv run python scripts/publish_app.py
uv run python scripts/publish_app.py --go --tag app-2026-11-20
```

## Bring your own state

On the app's map, a grey state has no results yet and a light one rests mostly on national data. The engine
reads a state through its config and adapters, and national sources (building permits, the ACS) cover every
state. **The full step-by-step guide, with the data each model needs and the minimum that has tested well, is
[`docs/adding_a_state.md`](docs/adding_a_state.md).** The outline below is the short version; the app's
"Add a state" page walks through it in plain words.

1. Add `config/states/<st>.yaml` with the state's code, name, FIPS code and Census region; copy an existing file
   such as `config/states/or.yaml` as a template.
2. Fetch the national sources: `uv run python scripts/fetch_data.py --state XX`.
3. Optional, for a tighter range: add the state's own parcel, zoning or permit data as adapters in
   `src/lotline/adapters/states/<st>/`, with a land-use crosswalk in `config/crosswalks/`. Each source gets a
   row in `docs/data_provenance.md`.
4. Optional: code the state's local rules (missing middle, ADUs, fees) with the rule agents and import them
   ([guide](docs/adding_local_rules_with_agents.md)).
5. Run the engine and rebuild the page: `uv run lotline results --state XX`, then
   `uv run python scripts/build_app.py`.

With national data only, the engine estimates eligible lots from the ACS and the page labels the state
"National data only" (data tier 3), so its range is wider. Local parcel data, with the places it covers given
a better tier under `data_tiers` in the state's config, narrows the range and darkens the state on the map.

## Reproduce the fitted parameters

About 130 values in `config/params/` are fitted to our own data; every one belongs to a named calibration step
(`src/lotline/calibrate/steps.py`), and `config/calibration.lock.json` records the value each step last wrote.
Full detail is in [docs/calibration.md](docs/calibration.md).

```bash
uv run lotline calibrate --check               # seconds, no data: every fitted value is accounted for and matches the lock
uv run lotline calibrate --list                # the 22 steps in run order: what each produces and from which decision
uv run lotline calibrate --run --quick         # fewer draws: every runnable step re-derives its values (about 18 minutes)
uv run lotline calibrate --run                 # the full fits, same seeds and draws as config (several hours; the ADU joint fit dominates)
uv run lotline calibrate --run --step mm_c4    # one step (repeatable); add --write to update config and the lock
```

- **Data.** `--run` reads the tables `lotline fetch` builds (see [Data](#data)). It needs the same `.env` as
  fetch, because the eligible-proxy step checks `CENSUS_API_KEY` before reading its cached Census lookup.
- **What `--quick` shows.** On 2026-11-26 it reproduced every runnable value exactly except where quick mode
  uses a coarser grid:
  - the missing-middle ramp half-way point (4.0 on the quick grid against 4.5), with the mature rate that
    goes with it;
  - the τ probabilities, normalized over fewer τ values;
  - the partial-share grid (3 rows instead of 10).

  A full `--run` uses config's own grids.
- **What runs from code.** 18 of the 22 steps re-derive their values from the fetched tables.
  - Three are recorded values, each with the script that measured it in `scripts/dev/`: the completion
    factors (a judgment informed by measured ratios), the ADU undercount factors (one check per row) and two
    small ADU inputs (the survey report rate and the covariate centres).
  - The V5 Charlotte prior is frozen for its blind test.
- **Where things are.**
  - Library code: the fit sets (`lotline.calibrate.adu.adu_fit_set`, `lotline.calibrate.mm.mm_fitsets`) and the step runners
    (`lotline.calibrate`).
  - `scripts/dev/` keeps only scripts still in use ([its README](scripts/dev/README.md) says why each stays).
  - The one-off analyses behind each decision are in `scripts/archive/` with an index
    ([README](scripts/archive/README.md)).

## Tests

No data or keys are needed: the tests build small synthetic inputs.

```bash
uv run pytest -q -n auto                  # everything, in parallel (about 12 minutes on a laptop)
uv run pytest -q -m "not slow" -n auto   # a 3-minute check: skips the 40 long fits in tests/slow_tests.txt
```

Lint: `uv run ruff check .`

## Compliance

`python compliance_check.py` checks the repo against the challenge's Official Rules. See `HANDOFF.md`.
`python compliance_check.py --run` also runs the setup and test commands above.

## Security

Dependabot (`.github/dependabot.yml`) keeps dependencies and GitHub Actions current. Secret scanning, push protection,
Dependabot alerts and **CodeQL default setup** are turned on in the repository's Settings → Code security
(no CodeQL workflow file is needed). Private vulnerability reporting is on; see [`SECURITY.md`](SECURITY.md) to report
an issue.

## Team

- Ben Cappellacci (Team Leader)

All contributors agree to the Apache-2.0 license and the challenge's
[Official Rules](https://housingchallenge.turnout.rocks/rules.html).
