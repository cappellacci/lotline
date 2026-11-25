### LB-NNN · 2026-11-25 · Review · Nightly deep inspection: judging panel plus brittleness review (thread 17)

- **Question:** What would the judges flag on `main` today, and what would break with future data releases,
  package versions or a new state?
- **Outputs:** judging run `reports/judging/2026-11-25-1656-30cfd38b/` (SCORECARD.md and six judge reports;
  gitignored); morning report https://claude.ai/artifact/HHLtadgzkoKieFfWgXkzf8; fix PR #534 (review row A31).
- **Decision:** none. Ben asked for the inspection ("Run as deep an inspection as you can"); every fix other than the
  regression in #534 is left for his choice.
- **What Claude did and how it was checked:** Claude Code ran the six-judge panel and a head judge on a clean clone of
  `main` (30cfd38b), plus three read-only subagents on packages and toolchain, data ingestion, and time bombs and
  the app. It re-read the top claims in the code before reporting them: the silent empty baseline when the origin
  year has no permit data, HTML error pages cached by `fetch`, `commit_sha` failing without git, the unpinned Python,
  the pandas 3.1 `.map().fillna()` pattern and the five open CodeQL alerts. Scored 69.4 today, 83.2 ceiling
  (64.9 on 2026-11-17).
