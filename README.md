# Lotline

Lotline is an open-source simulator of how state housing reforms change homebuilding over five years, compared
with a baseline where nothing changes. It covers three reforms: missing middle, ADUs and development fee cuts.

**Try it: [cappellacci.github.io/lotline](https://cappellacci.github.io/lotline/)** (no install; results for Minnesota,
North Carolina, Ohio, Oregon, Texas and Wisconsin).

> Status (November 2026): the baseline, the three reforms and the interactive page run for Minnesota, North
> Carolina, Ohio, Texas, Oregon and Wisconsin. Final documents are in review.

## Command contract

Three commands reproduce Lotline from a clean checkout. They need
[uv](https://docs.astral.sh/uv/getting-started/installation/) and nothing else (uv installs Python 3.12 if missing).

| Step  | Command | Notes |
| ----- | ------- | ----- |
| Setup | `uv sync --frozen` | Installs the exact pinned dependencies from `uv.lock` into `.venv/` |
| Run   | `uv run lotline run --state MN` | Fetches the state's data (needs `.env`, see [Data](#data)), runs every reform and builds the page at `reports/app/index.html`. A first Minnesota fetch is about 4.5 GB; later runs reuse the cache. `uv run lotline --help` lists every command |
| Test  | `uv run pytest -q -n auto` | Runs every automated test in parallel (small synthetic fixtures, no downloads); about 12 minutes on a laptop. `uv run pytest -q -m "not slow" -n auto` is the 3-minute check that skips 40 long simulation-recovery fits |

Commands that download data need a `.env`. Copy `.env.example` to `.env` and fill in the values (see [Data](#data)).

## Documentation

- [Model & Assumptions Overview](docs/model_and_assumptions.md): how the tool works and what it assumes
- [Policy Scenario Comparison](docs/policy_scenario_comparison.md): how the scenarios rank and what drives the ranking
- [Data Provenance](docs/data_provenance.md): sources, licenses and preparation steps
- [Disclosures](docs/disclosures.md): AI tools, models, external services and dependency licenses
- [Data dictionary](docs/schemas.md) and [analysis plan](docs/analysis_plan.md)
- [Calibration](docs/calibration.md): where every fitted number comes from, and how `lotline calibrate` reproduces it
- [Adding local rules with the rule agents](docs/adding_local_rules_with_agents.md): research a state's
  missing-middle, ADU and fee rules with your own Claude account, then review and import them

## License

Lotline is licensed under the **Apache License 2.0** (Apache-2.0). See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

We chose Apache-2.0 because it is permissive. Any state agency, researcher or vendor can reuse and adapt Lotline
in their own tools without opening their code. It also adds an explicit patent grant and asks that changes be
noted, which suits public-sector reuse, and it is one of the licenses the Challenge accepts.

## Setup

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs Python 3.12 if it is
missing. The app tests (`tests/app`) also run the page's JavaScript under [Node](https://nodejs.org/) 22; without
Node they are skipped on a laptop.

```bash
uv sync --frozen            # creates .venv/ with the exact pinned versions in uv.lock
uv run lotline --version
```

Then one command fetches a state's data, runs every reform and builds the page:

```bash
uv run lotline run --state MN
```

Add `--offline` to use only data already downloaded, `--skip-fetch` to reuse the tables already built, or
`--draws N` to set the model runs per reform. Without `--state` it runs every configured state.

If you want to run each step yourself, `lotline run` does the same as these three commands:

```bash
uv run lotline fetch --state MN     # download the data and build its tables
uv run lotline results --state MN   # run every reform; writes reports/results/mn/bundle.json
uv run lotline app                  # build the page and its data tab from the results
```

### Data

Source data is never committed. Lotline downloads it into `LOTLINE_DATA_DIR` (default `~/lotline-data`, outside
the repo) and records each download in `manifest.jsonl` there. Copy `.env.example` to `.env` to set the
directory or API keys.

The ACS needs a free Census API key. Sign up at https://api.census.gov/data/key_signup.html, click the
activation link Census emails you, and put the key in `.env` as `CENSUS_API_KEY=...`. The key is sent with each
request but never written to the download manifest.

`uv run lotline sources` lists every source per state: the national ones plus any in
`src/lotline/adapters/states/<st>/`. To fetch one source, name it:

```bash
uv run lotline fetch --state MN --source bps
```

`scripts/fetch_data.py` takes the same options (`uv run python scripts/fetch_data.py --state MN --source bps`).

To rebuild the processed tables after a code change without downloading anything, add `--offline`
(`uv run lotline fetch --state NC --offline`). Each source then reads the newest complete raw snapshot already
in `LOTLINE_DATA_DIR` and sends no request. It fails with a clear message if nothing usable is cached, and skips
a newer snapshot with missing pages with a note. What each offline build read is appended to
`manifest.builds.jsonl`. Without `--offline`, ArcGIS and Socrata sources take a new dated snapshot each day.

`docs/data_provenance.md` is generated from the download manifest. Regenerate it after fetching:

```bash
uv run lotline provenance --write
```

## The app

The app is one static page, built from the results under `reports/results/`. `uv run lotline run` builds it at
the end, and `uv run lotline app` rebuilds it from the results already written (`--no-data-tab` skips the data
tab, which is faster).

It writes `reports/app/index.html` and one `reports/app/states/<st>.js` per state. Open `index.html` straight
from disk in any browser. It needs no server or internet connection. Keep the `states/` folder next to it,
because the page loads a state's file when you pick that state. To try the page without data, build it from the
synthetic test bundle: `uv run python scripts/build_app.py --bundle tests/fixtures/results/zz/bundle.json`.

The published copy lives on GitHub Pages, and no results are committed. `scripts/publish_app.py` checks that
every bundle renders. With `--go` it uploads the bundles as assets of a GitHub release tagged at the current
commit, and starts `.github/workflows/pages.yml`, which rebuilds the page from that release with the code at
that tag and deploys it. Each release keeps the exact results behind one version of the published page.

```bash
uv run python scripts/publish_app.py
uv run python scripts/publish_app.py --go --tag app-2026-11-27
```

## Bring your own state

Lotline works for any state, because the engine reads a state through its config and adapters, and national
sources (building permits, the ACS) cover every state. On the app's map, a grey state has no results yet and a
light one rests mostly on national data. **The full step-by-step guide, with the data each model needs and the
minimum that has tested well, is [`docs/adding_a_state.md`](docs/adding_a_state.md).** The app's "Add a state"
page walks through the same steps in plain words, and `uv run lotline onboard --state XX` shows what is done and
what comes next.

1. Add `config/states/<st>.yaml` with the state's code, name, FIPS code and Census region. Copy an existing file
   such as `config/states/or.yaml` as a template.
2. Optional, for a tighter range: add the state's own parcel, zoning or permit data as adapters in
   `src/lotline/adapters/states/<st>/`, with a land-use crosswalk in `config/crosswalks/`. Each source gets a
   row in `docs/data_provenance.md`.
3. Optional: code the state's local rules (missing middle, ADUs, fees) with the rule agents and import them
   ([guide](docs/adding_local_rules_with_agents.md)).
4. Fetch the data, run the engine and rebuild the page: `uv run lotline run --state XX`.

With national data only, the engine estimates eligible lots from the ACS and the page labels the state
"National data only" (data tier 3), so its range is wider. Local parcel data narrows the range and darkens the
state on the map, once the places it covers are given a better tier under `data_tiers` in the state's config.

## Reproduce the fitted parameters

We fitted 132 values in `config/params/` to our own data. Each one belongs to a named calibration step
(`src/lotline/calibrate/steps.py`), and `config/calibration.lock.json` records the value each step last wrote.
[docs/calibration.md](docs/calibration.md) has the full detail.

```bash
uv run lotline calibrate --check               # seconds, no data: every fitted value is accounted for and matches the lock
uv run lotline calibrate --list                # the 23 steps in run order: what each produces and from which decision
uv run lotline calibrate --run --quick         # fewer draws: every runnable step re-derives its values (about 18 minutes)
uv run lotline calibrate --run                 # the full fits, same seeds and draws as config (several hours; the ADU joint fit dominates)
uv run lotline calibrate --run --step mm_c4    # one step (repeatable); add --write to update config and the lock
```

`--run` reads the tables `lotline fetch` builds (see [Data](#data)). It needs the same `.env` as fetch, because
the eligible-proxy step checks `CENSUS_API_KEY` before reading its cached Census lookup.

On 2026-11-26 `--quick` reproduced every runnable value exactly, except where quick mode uses a coarser grid.
The missing-middle ramp's half-way point came out at 4.0 on the quick grid against 4.5, and the mature rate
moved with it. The τ probabilities were normalized over fewer τ values, and the partial-share grid had 3 rows
instead of 10. A full `--run` uses config's own grids.

18 of the 23 steps re-derive their values from the fetched tables. Four are recorded values, each with the
script that measured it in `scripts/dev/`: the completion factors (a judgment informed by measured ratios), the
ADU undercount factors (one check per row), the ADU survey report rate and the ADU covariate centres. The last
step, the V5 Charlotte prior, is frozen for its blind test.

The fit sets are library code (`lotline.calibrate.adu.adu_fit_set`, `lotline.calibrate.mm.mm_fitsets`), as are
the step runners (`lotline.calibrate`). `scripts/dev/` keeps only scripts still in use, and
[its README](scripts/dev/README.md) says why each stays. The one-off analyses behind each decision are in
`scripts/archive/`, with an index in [its README](scripts/archive/README.md).

## Reproduce the published numbers

Anyone should be able to check that a number on the live page came from this code. Each published page comes
from a GitHub release (`app-<date>`) whose files are the state results bundles. Every bundle's `meta` records
what produced it:

- `commit_sha` and `tree_clean` identify the code;
- `config_hash` covers every file under `config/`;
- `input_tables` and `input_hash` (from schemas 1.26) hold a sha256 of each processed data table the state had;
- `seed` and `n_draws` fix the random draws.

To rerun a state, check out that commit, run `uv sync --frozen`, then `uv run lotline run --state MN`. With the
same commit, config and input hashes, the numbers come out the same, because every random draw is seeded.

Your data may still differ, because sources change. An online `lotline fetch` saves each download in a folder
named for the day it ran, and city permit layers keep adding records. So a later fetch can give different input
hashes and different numbers with the same code. Compare your bundle's `input_tables` with the published one to
see which tables changed. If every hash matches but the numbers don't, the difference is in the code or config.

## Validation

We test the model against what actually happened. `uv run lotline validate` lists the validation steps and the
blind tests, with the commit each prediction was frozen at and where it was scored. Two of the steps run from
the command line: `uv run lotline validate --step V0 --state MN` compares a state's permits with the Census
permit survey, and `--step V1` forecasts held-out years from earlier ones. The plan is in
[docs/research/lotline-validation-plan.md](docs/research/lotline-validation-plan.md).

## Tests

The tests need no data or keys, because they build small synthetic inputs. The app tests in `tests/app` need
Node (see [Setup](#setup)).

```bash
uv run pytest -q -n auto                  # everything, in parallel (about 12 minutes on a laptop)
uv run pytest -q -m "not slow" -n auto   # a 3-minute check: skips the 40 long fits in tests/slow_tests.txt
```

Lint: `uv run ruff check .`

## Compliance

`python compliance_check.py` checks the repo against the challenge's Official Rules, and
`python compliance_check.py --run` also runs the setup and test commands above. `HANDOFF.md` has the full
checklist.

## Security

Dependabot (`.github/dependabot.yml`) keeps dependencies and GitHub Actions current. Secret scanning, push
protection, Dependabot alerts and CodeQL default setup are turned on in the repository's Settings → Code
security, so no CodeQL workflow file is needed. Private vulnerability reporting is on. See
[`SECURITY.md`](SECURITY.md) to report an issue.

## Team

- Ben Cappellacci (Team Leader)

All contributors agree to the Apache-2.0 license and the challenge's
[Official Rules](https://housingchallenge.turnout.rocks/rules.html).
