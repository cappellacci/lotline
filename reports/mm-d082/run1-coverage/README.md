# D-082 run 1: permit coverage screen and k_src (2026-11-12)

**What this is.** This is the first of D-082's six runs (§9). It asks one question for each permit source that
might feed the missing-middle counts: *do the city's own permit records see about the same number of new
2–4 unit buildings as the Census Building Permits Survey (BPS) does, in the years before the reform?* A source
that does (0.8 ≤ k ≤ 1.25) and passes the other three tests is "strong." Strong sources feed runs 2–4: the
uplift ratios, the roll check and challenger C2. **Nothing was fitted. Nothing was written to config.**

- **Approved by:** Ben approved D-082 on 2026-11-12 ("Approve D-082"). The go-ahead for this run was "Yes, start
  run 1", which also accepted the 13 counting choices in PR #408.
- **Command:** `uv run python scripts/dev/mm_counts_d082.py --coverage --out reports/mm-d082/run1-coverage`.
  It uses cached processed tables only, with no download, and takes about 2 minutes.
- **Holdouts:** every table went through `mm_counts.blind`. That function drops St. Paul and all of Ramsey
  County, then applies `holdout.apply`. No unblinding was done. Mecklenburg was not screened (see below).
- **Files:**
  - `coverage.csv` has one row per source and every number below.
  - `coverage_by_year.csv` has permit and BPS buildings by place and year inside each source's window.

## Result

| Source | Window (pre-event) | Permit bldgs | BPS bldgs | **k** (90% range) | Enters? | Strong? | k if merged buildings are split (range) |
|---|---|---:|---:|---|:-:|:-:|---|
| Raleigh | 2013–2025 (no event) | 162 | 199 | **0.81** (0.68–0.97) | yes | **yes** | 0.92–1.02 |
| Austin | 2013–2023 (event 2024) | 968 | 1,057 | **0.92** (0.85–0.99) | yes | **yes** | 1.34–1.70 |
| Bend | 2013–2021 (event 2022) | 254 | 252 | **1.01** (0.87–1.17) | yes | **yes** | 1.09–1.15 |
| Medford | 2020–2021 (event 2022) | 10 | 9 | 1.11 (0.53–2.33) | yes | no: 2 pre-years, needs 3 | 1.11 |
| Minneapolis | 2017–2019 (event 2020) | 62 | 44 | 1.41 (1.02–1.95) | no: too high | no | 1.50–1.59 |
| Cincinnati | 2013–2025 (no event) | 49 | 79 | 0.62 (0.46–0.84) | no | no | 0.72–0.78 |
| Portland | 2013–2021 (event 2022) | 280 | 510 | 0.55 (0.49–0.62) | no | no | 0.63–0.69 |
| College Station | 2013–2025 (no event) | 188 | 356 | 0.53 (0.46–0.61) | no | no | 0.85–1.12 |
| Durham (city + county) | 2013–2019 (event 2020) | 16 | 39 | 0.41 (0.25–0.67) | no | no | 0.95–1.44 |
| Columbus | 2013–2025 (no event) | 255 | 787 | 0.32 (0.29–0.36) | no | no | 0.72–1.09 |
| Mecklenburg | — | — | — | not screened | — | — | — |

**As pre-registered, three sources are strong: Raleigh, Austin and Bend.** Every source passes the units test,
and every source has parcel IDs on at least 92% of rows. The failures come from coverage, plus Medford's short
pre-period.

## What the numbers say, in plain language

1. **The missing street address is the biggest uncertainty in this run.** The permit tables carry no address
   (#406). Two or more buildings on one parcel in one year therefore collapse into one "building" whose units
   add up to 5 or more. Pre-registered choice 1 drops these. The last column instead counts each one as
   between ⌈units/4⌉ and ⌊units/2⌋ buildings. That moves several sources across the line in both directions:
   - Durham (0.41 → 0.95–1.44), Columbus (0.32 → 0.72–1.09) and College Station (0.53 → 0.85–1.12) could pass.
   - Austin (0.92 → 1.34–1.70) could fail on the high side.
   - Raleigh, Bend, Portland, Cincinnati and Minneapolis keep their verdicts.

   The entry rule uses the pre-registered k. The split column is a sensitivity only.
2. **Most out-of-range "buildings" are not new construction.** Minneapolis, Columbus and Cincinnati have 799, 630
   and 930 out-of-range buildings. Nearly all of them sum to 0 units: they are 2–4 unit permits with
   `units_new = 0`. In Columbus, about 580 of the 630 are zeros, and most of the rest are merged buildings. These are repairs
   and alterations to existing duplexes and triplexes, so leaving them out is correct. It is not a collapse
   error.
3. **Durham's units are often unknown.** 390 of 598 collapsed buildings have no unit count. Under choice 3
   they are left out, not imputed. That is a large part of why Durham's k is low.
4. **Minneapolis is high on small numbers.** The window is only 2017–2019 (62 against 44). Its lower bound
   (1.02) is inside the band. Its permits likely include conversions that BPS does not count, which is why
   the screen has an upper bound.
5. **Portland is low under either reading** (at most 0.69). Its permits see about 55–69% of BPS's 2–4
   buildings before RIP.
6. **The long window (back to 1992) is a sensitivity.** It changes one verdict: Austin, at 0.68 over
   1992–2023, against 0.92 over 2013–2023. Austin's older records are thinner. Raleigh rises to 1.15. See
   `long_*` in `coverage.csv`.

## Run-1 choices (not in D-082's text; made by Claude Code, for Ben to confirm)

- **Event years.** These come from D-082's event rule on the accepted rule rows
  (`calibrate_mm_d082.events_d082`). Raleigh, Columbus, Cincinnati and College Station have no event in
  2013–2025, so all of their window is "before the event." Raleigh is a test place. Its 2021 text change does
  not meet the cap-rise rule under the accepted rows, so its window runs to 2025.
- **Window start.** The window starts in 2013 (D-042's first event year) or the source's first full year,
  whichever is later. The long window back to BPS's first year (1992) is reported as a sensitivity.
- **Full years only.** A source's first year counts if its first permit is on or before 15 January. Its last
  year counts if its last permit is on or after 15 December. No year past 2025, BPS's last year, is used.
- **Several places in one source.** Each place is counted over its own pre-event years, and one k is formed
  from the totals (`mm_counts.area_coverage`, with a hand-worked test). Only Durham (city plus unincorporated
  county, both with a 2020 event) uses this.
- **Mecklenburg was not screened.** BPS has no place rows for Charlotte or the Mecklenburg towns, which are
  94% of the source's rows, and the D-082 panel keeps Mecklenburg out. A county-only k would describe the
  wrong area.
- **The pre-years test counts full years inside the source's span.** Minneapolis's December 2016 does not
  count, so it has exactly 3 pre-years.

## Not done in this run

- **The 30-building hand check per source (§2) has not been done.** It needs the raw records, so the sample
  stays outside the repo. It is the next step before the collapse error can be stated.
- **Runs 2–6** (ratios, roll diffs, the joint refit, the tests and the results page) each wait for their own
  go-ahead.

## Recommendation

Do the address fix (#406) before run 2. The split sensitivity shows that the collapse key, not the screen,
decides which sources are strong. Once the processed permit tables carry an address or `site_key`, rerunning
this screen takes about 2 minutes. If Ben prefers to go ahead now, run 2 uses Raleigh, Austin and Bend as
pre-registered, and states the address caveat.
