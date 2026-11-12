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

**Main collapse: per-permit split** (D-082 deviation, 2026-11-12, chosen by Ben after the first pass of this
run: "Per-permit split rule"). With no address, one parcel × issue year whose units sum above 4, and whose
permits are **each** 2–4 units, counts each permit as its own building. Groups with a sub-2 permit (one permit
per duplex side) stay merged. The pre-registered collapse is kept as `prereg_k`. The bounds from the first pass
(⌈u/4⌉–⌊u/2⌋) are kept as `split_lo_k` and `split_hi_k`.

| Source | Window (pre-event) | Permit bldgs | BPS bldgs | **k** (90% range) | Strong? | k, pre-registered collapse | Bounds |
|---|---|---:|---:|---|:-:|---|---|
| Raleigh | 2013–2025 (no event) | 192 | 199 | **0.96** (0.82–1.14) | **yes** | 0.81 (strong) | 0.92–1.02 |
| Durham (city + county) | 2013–2019 (event 2020) | 39 | 39 | **1.00** (0.69–1.45) | **yes** | 0.41 | 0.95–1.44 |
| Columbus | 2013–2025 (no event) | 648 | 787 | **0.82** (0.75–0.90) | **yes** | 0.32 | 0.72–1.09 |
| College Station | 2013–2025 (no event) | 359 | 356 | **1.01** (0.89–1.14) | **yes** | 0.53 | 0.85–1.12 |
| Bend | 2013–2021 (event 2022) | 280 | 252 | **1.11** (0.96–1.28) | **yes** | 1.01 (strong) | 1.09–1.15 |
| Austin | 2013–2023 (event 2024) | 1,628 | 1,057 | 1.54 (1.44–1.64): too high | no | 0.92 (strong) | 1.34–1.70 |
| Medford | 2020–2021 (event 2022) | 10 | 9 | 1.11 (0.53–2.33) | no: 2 pre-years | 1.11 | 1.11 |
| Minneapolis | 2017–2019 (event 2020) | 66 | 44 | 1.50 (1.09–2.06): too high | no | 1.41 | 1.50–1.59 |
| Cincinnati | 2013–2025 (no event) | 57 | 79 | 0.72 (0.54–0.96): too low | no | 0.62 | 0.72–0.78 |
| Portland | 2013–2021 (event 2022) | 339 | 510 | 0.66 (0.59–0.75): too low | no | 0.55 | 0.63–0.69 |
| Mecklenburg | — | — | — | not screened | — | — | — |

**Five sources are strong under the main collapse: Raleigh, Durham, Columbus, College Station and Bend.**
Under the pre-registered collapse there were three: Raleigh, Austin and Bend. Two sources are strong under
both: Raleigh and Bend. Austin moves above the band. Its duplex permits on one parcel are often each recorded as
2 units, so splitting them roughly doubles its count (1,924 buildings came from splits). Run 2 reports its
ratios on both source sets.

## What the numbers say, in plain language

1. **Without the address, the collapse decides the verdicts.** The split rule is the closest offline stand-in
   for "one building per address." It lands inside the first pass's bounds for every source except Austin,
   which comes out at 1.54, inside 1.34–1.70.
2. **Most out-of-range "buildings" are not new construction.** Minneapolis, Columbus and Cincinnati had 799,
   630 and 930 out-of-range buildings under the first collapse. Nearly all sum to 0 units: they are 2–4 unit
   permits with `units_new = 0`, meaning repairs and alterations to existing duplexes and triplexes. They are
   correctly left out.
3. **Durham's units are often unknown.** 390 of its collapsed buildings have no unit count and are left out
   (choice 3), yet k still reaches 1.00.
4. **Minneapolis is high on small numbers** (66 against 44 over 2017–2019). Its permits likely include
   conversions that BPS does not count.
5. **Portland stays low** (at most 0.75). Its permits see about two thirds of BPS's 2–4 unit buildings
   before RIP.
6. **The long window (back to 1992) is a sensitivity** (`long_*` in `coverage.csv`). Using it would change
   several verdicts, so the 2013 start matters.

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

## Recommendation (first pass; superseded)

Do the address fix (#406) before run 2. The split sensitivity shows that the collapse key, not the screen,
decides which sources are strong. Once the processed permit tables carry an address or `site_key`, rerunning
this screen takes about 2 minutes. If Ben prefers to go ahead now, run 2 uses Raleigh, Austin and Bend as
pre-registered, and states the address caveat.

**Outcome:** Ben chose the per-permit split ("Per-permit split rule", 2026-11-12). The addresses cannot be added
offline: every adapter excludes them as personal fields, so a re-download would be needed, and the brief rules
that out.
