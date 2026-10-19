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
| Test  | `uv run pytest -q` | Runs the automated tests (small synthetic fixtures, no downloads needed) |

Commands that download data need a `.env`: copy `.env.example` to `.env` and fill in the values (see [Data](#data)).

## Documentation

- [Model & Assumptions Overview](docs/model_and_assumptions.md): how the tool works and what it assumes
- [Policy Scenario Comparison](docs/policy_scenario_comparison.md): scenario ranking and what drives it
- [Data Provenance](docs/data_provenance.md): sources, licenses and preparation steps
- [Disclosures](docs/disclosures.md): AI tools, models, external services and dependency licenses
- [Data dictionary](docs/schemas.md) and [analysis plan](docs/analysis_plan.md)

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

`docs/data_provenance.md` is generated from the download manifest; regenerate it after fetching:

```bash
uv run lotline provenance --write
```

## Tests

```bash
uv run pytest -q
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
