### LB-NNN · 2026-11-03 · [engine] · How can anyone look at, and compare, an estimation run's results?
- **Question:** Ben asked for a dashboard to apply after any run: compare runs side by side, and show for each a
  brief description of the statistical method, the data scope and the configuration used.
- **What I did:**
  - A run manifest, `run.yaml`, in every run folder: model and plan entry, a short method text, data scope
    (states, years, outcome, places, place-years, treated), configuration, commit, command, status and the
    reading. `estimate_mm.py --full` and `estimate_pooled_adu.py --full` now write it when they start and
    update it when they finish (status `completed` or `no_estimate`), with new `--title` and `--plan-entry`
    options. Manifests for the five existing runs were written by hand from their logs, CSVs and plan
    entries (each says so).
  - `src/lotline/model/runs.py` reads either model's CSVs into one shape. `src/lotline/model/dashboard.py`
    and `dashboard.html` make one self-contained page (plain SVG and JavaScript; no new dependency, no
    network).
  - `scripts/dev/results_dashboard.py` writes `reports/dashboard/index.html` for every run under `reports/`.
  - The page lets you pick up to three runs and shows: run cards (method, scope, configuration, reading),
    overall-effect tiles with randomization inference, effect terms, a checks matrix, robustness fits, the
    randomization distributions, leave one out, out-of-sample tests and added homes. Each chart has a table
    view; light and dark modes; works at phone width.
- **Inputs:** the committed run folders under `reports/` (no data read).
- **Outputs:** `src/lotline/model/runs.py`, `src/lotline/model/dashboard.py`,
  `src/lotline/model/dashboard.html`, `scripts/dev/results_dashboard.py`, `tests/model/test_runs.py`
  (13 tests); `run.yaml` in `reports/mm-d024`, `reports/mm-d024-nb`, `reports/mm-d024-4state`,
  `reports/adu-d025/corrected-2026-10-21`, `reports/adu-d025-4state`; `reports/dashboard/index.html`;
  hooks in `scripts/dev/estimate_mm.py` and `scripts/dev/estimate_pooled_adu.py`.
- **Decisions:** a static page over a Streamlit view: no new dependency, opens from a file, and leaves
  WS-APP's policymaker app separate. The readings in the hand-written manifests repeat the analysis plan;
  the November D-024 reading is still marked for Ben to confirm.
- **AI:** Claude Code (Opus 5.5) wrote the code, tests and manifests. Checked with tests on synthetic run
  folders (a test caught place codes turning into floats, fixed). The manifest hooks were run with stubbed
  fits (no model run), and the page was checked in a browser in light and dark modes, at desktop and phone
  widths, with a mixed D-024/D-025 comparison and a run that has no estimate.
