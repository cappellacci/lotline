### LB-NNN · 2026-10-20 · Build: Mecklenburg permits adapter, holdout-first (V5)
- **Question:** How can Mecklenburg permits enter `permits` without any Charlotte (or, under D-012, county)
  outcome from 2023-06-01 being downloaded, opened or counted?
- **What I did:**
  - Found the county layer (ArcGIS item fc9d171ecd4d44a58c7dad840cd58aa2; 482,376 records per its Hub metadata)
    and read its field schema from ArcGIS Online metadata only: it does carry `numunits`, plus `usdcdesc`,
    `typeofbldg`, `zonecode`, `taxjuris` and owner fields (excluded).
  - Wrote `meck_permits`: a server-side `where` built from the holdout config (only permits before the window, or
    later in a non-held-out town), then `holdout.apply` on the point-based place before anything is written, and a
    check that stops the run if no town permits come back (a wrong `taxjuris` spelling loses rows, never leaks).
  - Units from the Census item code (`config/crosswalks/nc_meck_usdc_codes.csv`, from census.gov items.txt),
    `numunits` when it fits, then the shared description parser (`inferred`).
- **Outputs:** `src/lotline/adapters/states/nc/meck_permits.py`, the two crosswalks, tests, source entry.
- **Findings:** the server (meckgis.mecklenburgcountync.gov) answers this network with a Cloudflare browser
  challenge (HTTP 403), so no permit data was downloaded; I did not try to get around it. Correction to the #121
  write-up: Matthews is 3741960 and Mint Hill 3743480 (the data were right; only my labels were swapped).
- **AI:** Claude (WS-NC) wrote the adapter and synthetic tests (holdout, D-012, units, town check, privacy).
- **Open / next:** access to the county server (or a county export Ben downloads and registers); verify the
  `taxjuris` spellings on first read.
