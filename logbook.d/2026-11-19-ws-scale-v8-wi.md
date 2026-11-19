### LB-NNN · 2026-11-19 · Validation: V8 Wisconsin, blind registered and setup recorded before any fetch (D-104)
- **Question:** Can an unseen state be onboarded from a state file and national data alone, with a prediction
  frozen before any of its outcomes are seen?
- **What I did:** `config/states/wi.yaml` with the statewide holdout `V8-WI-TRANSFER` (Wisconsin, 2020 on), and
  D-104 (origin 2019, 2021-2025 window, level 0, scoring rules), committed before the first Wisconsin fetch.
- **Outputs:** `config/states/wi.yaml`, `docs/analysis_plan.md` D-104.
- **Decisions:** Ben 2026-11-18 (via the Multi-state model setup guide session): keep the blind; download
  Wisconsin's national data.
- **AI:** Claude wrote the file and the entry.
- **Open / next:** fetch, run, freeze.
