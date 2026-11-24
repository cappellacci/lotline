### LB-NNN · 2026-11-24 · Scope · Which state is the official benchmark? (issue #40)

- **Question:** HANDOFF had left the benchmark state open since 2026-10-04, with MN recommended.
  Compliance check S5 warned that `challenge.toml` named no state.
- **Decision:** Ben, 2026-11-24: Minnesota ("Yes let's settle it"). Reasons put to him:
  - the best data of the five states (tier 1, Met Council permit-level ADU counts 2009–2024);
  - the highest state-reassessment score (MN 37, TX 34, NC 32, OH 30 of 45);
  - real reforms to test against (Minneapolis, St. Paul).
  - Texas has the largest numbers but thinner data. NC, OH, TX, OR and Wisconsin carry the "thin data"
    story.
- **Outputs:**
  - `challenge.toml` (`state = "MN"`).
  - `docs/model_and_assumptions.md` ("Which states").
  - Minnesota's app bundle rebuilt with `--role benchmark` and republished.
  - HANDOFF decision proposed in the PR for thread 6 to fold in.
- **What Claude did and how it was checked:** Claude Code made the edits, checked that `compliance_check.py`
  S5 now passes, and confirmed the live page labels Minnesota as the benchmark state.
