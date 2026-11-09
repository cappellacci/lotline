### LB-NNN · 2026-11-09 · Build: building-permit fees for the places that borrowed Minnesota's
- **Question:** what does each of the 23 places in manual-fee-lookups.md priority 2 charge to permit and inspect a new
  house, duplex and fourplex, so the fee model stops filling them with the pooled (mostly Minnesota) median?
- **What I did:**
  - Found who issues permits in each place (e.g. Winston-Salem/Forsyth combined department; New Hanover County for
    Wilmington; Cabarrus County for Concord) and coded the issuer's adopted schedule under the place's GEOID.
  - One row per fee item (building, plan review, trade permits, surcharges) for SFD, U2 and U3_4 at the model's
    prototypes (2,150 sq ft / $354,750; 2 x 1,000 / $330,000; 4 x 1,000 / $660,000), written by
    `scripts/dev/permit_fees_2026_11_09.py` from `scripts/dev/permit_fees_2026_11_09_rows.json` (idempotent, each file
    validated with `load_fees` before it is written).
  - Two existing test fixtures (`tests/states/or/test_fees.py`, `tests/states/tx/test_fee_rule.py`) check SDC/impact
    hand sums; they now leave out the new permit rows (tagged "Permit lookup 2026-11-09" in notes).
- **Inputs:** Ben's local copies in `~/lotline-data/manual/nc_fees/`; official city/county schedules (URLs in `source`).
- **Outputs:** `config/fees/{mn,nc,or,tx}.csv` (+201 permit rows), the script and its rows file,
  `docs/research/fee-levels-vs-handbook.md` (regenerated, 2025 dollars).
- **Findings:**
  - Coded permit fees are well below the $4,355 pooled fill in NC and TX (house $840–$3,760; most NC places under
    $1,000), and near or above it in Oregon (Portland $5,883, Bend $8,213) and Brooklyn Park ($4,801).
  - 20 of 24 places coded. No rows: Wilson (schedule link not found), Buncombe County (site blocked to the session's
    proxy; scanned PDF), Cabarrus County and Concord (county issues Concord's permits; adopted schedule not found).
    Those four now fill from the NC state median (about $930) instead of the pooled $4,355.
  - Fourplexes go to the commercial (IBC) schedule almost everywhere; per unit they usually pay about the same as or
    less than a house, except Fuquay-Varina ($1,750 vs $838), Johnston County ($1,518 vs $895) and Asheville (see below).
- **Decisions:** none recorded; propose in the PR that Ben confirm the Asheville trade-permit reading and whether NC
  places without a schedule should take the NC state median.
- **AI:** Claude (Cowork) ran six research subagents on the official schedules, then checked every `source_quote`
  against the local PDF text where a local copy existed (53 rows matched word for word). Quotes read only through a
  web-fetch tool are flagged in notes as not yet matched; paraphrased quotes were left blank (NC) or the row dropped
  (OR, where every row must carry a quote). Arithmetic checked in Python; tests and `compliance_check.py` pass.
- **Open / next:** a checker should re-open the sources (most direct downloads were blocked to the session) and fill
  `verified_by`; missing items: Durham mechanical, Greensboro plumbing/mechanical and plex trades, Houston and Fort
  Worth trade permits, Portland plumbing/mechanical and the Oregon 12% surcharge for Portland and Salem, Salem trades.
