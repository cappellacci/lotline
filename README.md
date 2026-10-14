# Lotline

A transparent, open-source simulator of how state housing reforms (missing middle, ADUs, development fee cuts) change
housing production over five years, compared with a no-change baseline.

> Status: early setup (Phase 0). See `HANDOFF.md` and `docs/build/BUILD_PLAN.md`.

## License

Licensed under the **Apache License 2.0** (Apache-2.0). See [`LICENSE`](LICENSE).

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
(no CodeQL workflow file is needed).
