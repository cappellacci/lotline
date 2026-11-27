### LB-NNN · 2026-11-17 · Build: WS-SCALE tasks 11 and 13, short path and onboarding steps as data
- **Question:** Can the adding-a-state steps live in one data file that both the guide and the app read, with
  each step doable by hand, by a built-in command or by an agent?
- **What I did:**
  - `config/onboarding/steps.yaml`: the guide's 14 steps. Each has a level, time, inputs, outputs, ways to do
    it, commands, a check, `done_when` and an agent brief.
  - `src/lotline/onboarding.py`: `steps`, `commands`, `check`, `plan` and `config_problems`. They read only
    config files and which processed tables exist.
  - `lotline onboard --state XX [--json]`.
  - The guide's one-page short path and section 5 step table are generated from the file. Step 3 ("clear
    the blockers", now empty) became "Check the state file".
  - Task 13 design written into the brief.
- **Outputs:** the files above, `src/lotline/cli.py`, `docs/adding_a_state.md`,
  `docs/build/workstreams/WS-SCALE.md`, `tests/core/test_onboarding.py`.
- **Check:** tests tie guide headings and generated blocks to the steps file. `lotline onboard --state OR`
  marks 9 of 14 steps done on the real data directory, read-only.
- **Decisions:** none. The app UI is the "UI/UX Workflow" session's, and swarm briefs belong to the "Local
  rules agent swarm design" session.
- **AI:** Claude designed and wrote the steps file, module, command and tests.
- **Open / next:** swarm briefs for `rules` and `fees`; the app reading `plan()`.
