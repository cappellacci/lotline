### LB-NNN · 2026-11-25 · Review · App first load: the data dashboard loads only when the Data tab opens

- **Question:** Why is the page 4.7 MB, and how can the first load shrink without changing what it shows?
- **Outputs:** `src/lotline/app/build.py` (`DASHBOARD_FILE`, written next to the page); `src/lotline/app/template.html`
  (`loadDashboard`); `tests/app/test_build.py`.
- **Decision:** Ben, 2026-11-25 (overnight): fix what needs no decision; usability judge US-08.
- **What Claude did and how it was checked:** the usability helper measured the published page: 3.98 MB of the 4.66 MB
  `index.html` was the embedded data dashboard. It is now `dashboard.js` beside the page, loaded by script tag (so the
  page still works from disk) the first time the Data tab opens; the page keeps only a flag. Tests check the flag,
  the file, and that a rebuild without a summary removes it. App tests pass.
