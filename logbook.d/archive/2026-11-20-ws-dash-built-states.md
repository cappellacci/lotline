### LB-NNN · 2026-11-20 · App: the data tab shows only states with results
- **Question:** why did the published data dashboard list Wisconsin, a state with no results on the page?
- **What I did:** the app build now cuts the data dashboard summary to the states it has results bundles for (`build.built_states_only`), so a state whose data is fetched but is not fully built (a blind test, a state part-way through onboarding) stays out of the data tab, its totals and the folded dashboard. Republished the page (release app-2026-11-20).
- **Outputs:** `src/lotline/app/build.py`, `tests/app/test_build.py` (`test_data_tab_shows_only_states_with_results`).
- **Decision:** Ben, 2026-11-20: "The dashboard should only show states we have the data for/have been fully built."
- **AI:** Claude Code made the change and the test; app tests pass; the preview's data tab lists the five states only.
