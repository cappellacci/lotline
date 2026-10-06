# Lotline: Disclosures

<!-- Rules §7c. Keep this current as the project changes. -->

## AI code-generation tools
- Claude (Anthropic), used for planning, code and documentation. All AI-assisted code is reviewed, tested and explained.
- Claude Code (Anthropic's coding agent CLI), used to write and test code in this repo through pull requests that Ben reviews.
  Each PR records what Claude did and how it was checked in a `logbook.d/` fragment, folded into `LOGBOOK.md`.

## Pretrained models, weights or embeddings
- None so far.

## External APIs and hosted services
- None so far.

## Third-party code, dependencies and datasets
- Dependencies: see the SBOM (`sbom.spdx.json`) and the license scan. Exceptions (non-permissive licenses) are listed here with a justification.

### Dependency license exceptions

| Package | License | Pulled in by | Justification |
|---|---|---|---|
| certifi | MPL-2.0 | httpx | CA certificate bundle only, used unmodified as a runtime dependency; not copied into or distributed with our code. MPL-2.0 is file-level copyleft and places no obligations on our Apache-2.0 code. |

Note: numpy (BSD-3-Clause) bundles a few small components under 0BSD, MIT, Zlib and CC0-1.0, all permissive. CC0 is barred only as the license of our own code (Rules §7b), not for dependencies.
- Datasets: see `data_provenance.md`.

## Pre-existing work
- None. All code was written on or after 2026-09-14.
