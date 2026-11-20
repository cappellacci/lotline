### LB-NNN · 2026-11-19 · Validation: V8 Wisconsin, blind registered and setup recorded before any fetch (D-104)
- **Question:** Can an unseen state be onboarded from a state file and national data alone, with a prediction
  frozen before any of its outcomes are seen?
- **What I did:** `config/states/wi.yaml` with the statewide holdout `V8-WI-TRANSFER` (Wisconsin, 2020 on), and
  D-104 (origin 2019, 2021-2025 window, level 0, scoring rules), committed before the first Wisconsin fetch.
- **Outputs:** `config/states/wi.yaml`, `docs/analysis_plan.md` D-104.
- **Decisions:** Ben 2026-11-18 (via the Multi-state model setup guide session): keep the blind; download
  Wisconsin's national data.
- **AI:** Claude wrote the file and the entry.
- **Then (same day):**
  - Fetched Wisconsin's national data into the shared data directory. The tables hold Census permits to
    2019 only, with no ACS housing stock from 2020 on; the leak check passes.
  - V0 passes on 2010-2019.
  - Ran `lotline results --state WI --origin 2019` with no code change and froze it
    (`results/frozen/V8-WI-TRANSFER.json`; a rebuild is identical). Baseline 2021-2025: 75,347 permits
    (53,126-103,715), overlap low.
- **Open / next:** merge the freeze to main (Ben), then Ben unblinds and the baseline is scored per D-104.
