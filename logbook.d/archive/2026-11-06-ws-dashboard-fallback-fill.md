### LB-NNN · 2026-11-06 · dashboard · Counties on the Census fallback are shown as estimated, not blank

- **Question:** Oregon's map looked mostly empty after RLIS covered only Metro's three counties. Ben worried
  this would raise questions about data completeness, and chose to shade the fallback counties honestly
  (option 1, 2026-11-06).
- **Outputs:**
  - `lotline.dashboard.summarize.lots_estimated` and a county field `lots_estimated`: the number of
    jurisdictions whose eligible ADU lots come from the Census fallback (`acs_sf_fallback`, D-017).
  - `src/lotline/dashboard/template.html`: on the three parcel measures, a county with no parcel roll but
    estimated lots gets a hatched fill. It has a legend entry ("No parcel roll: lots estimated from Census
    housing counts"), a tooltip line with the estimate, and a note under the map. Plain grey now means no
    parcels and no estimate.
  - A test in `tests/dashboard/test_dashboard.py`.
- **Finding:** this is not only an Oregon issue.
  - Minnesota has 49 of 87 counties on the fallback, North Carolina 52 of 100 and Oregon 31 of 34.
  - Every county without parcels has an estimate, except Sherman and Wheeler (OR). Neither has a
    BPS-listed jurisdiction, so they stay grey.
- **What Claude did and how it was checked:** rebuilt the dashboard from the shared data directory and
  counted the fill classes per state. Viewed Oregon's map in the browser. Ran the dashboard tests, ruff and
  `compliance_check.py`.
