### LB-NNN · 2026-11-26 · review · Model page loads summary files, not every state's draws

**Question:** Does the Model page need every state's full results file?

**Outputs:**
- `src/lotline/app/build.py`: `model_file` / `model_script` write `states/<st>.model.js`, the bundle without its
  draws, next to each state's full file.
- `src/lotline/app/template.html`: `loadModel` reads those files for the Model page's comparisons (a state already
  loaded in full is reused); `loadState` and `loadModel` share one loader.
- `tests/app/test_build.py`: the model file equals the bundle less its draws.

**What Claude did:** Listed every bundle part the Model page's charts read (meta, totals, baseline, adu_baseline,
funnel, adu_place_types, observed): none reads draws, which are about 95% of each file. Built the app from six
real bundles: model files are 50 to 55 KB against 1.3 MB, so opening the Model page fetches about 320 KB instead
of about 7.7 MB.

**Checked:** `tests/app` 88 passed. Not yet checked in a browser (the in-app browser could not open the built
page from the scratch folder).
