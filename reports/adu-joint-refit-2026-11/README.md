# ADU joint refit, five states (D-079), run 2026-11-12

One run, as D-079 pre-registers it. Code: `scripts/dev/adu_joint_refit.py` and `lotline.model.joint_refit`
(PR #409), run on `main` at `1c7ad001` (the merge of #409), offline, seed 20261111, 20,000 draws. The year
windows are the pre-registered ones, confirmed by Ben on 2026-11-12 (D-079 "Built" note). An earlier start on
the same commit was stopped before any fit when Ben asked to review the windows; its output was discarded
unread. Nothing was changed after any score was read.

Holdouts stayed blind: St. Paul (MN V5) is out of every fit and every score, and no `--unblind` was passed.

## Headline

- **Form A (D-048) is kept.** Neither form passes D-075's claim rule at any data tier, so D-079's rule keeps
  Form A and the tool shows tier-2 ranges (D-075 §5).
- **No tier passes for either form.** The claim rule needs 4 of 5 held-out states with the observed
  2021–2024 total inside P10–P90 and within ×2 of the median. Ohio cannot be scored (its one fit place is its
  tier-2 city), so all four other states had to pass.
  - Form A: 0 states at every tier. Its ranges hold the observed total in 2–3 states per tier, but its median
    is never within ×2: Minnesota is over-predicted about 2.7×, North Carolina, Oregon and Texas are
    under-predicted 2.7× to 15×.
  - Form B: 2 states at tier 0 (MN, NC), 1 at tier 1 (NC), 0 at tier 2. Its ranges are very wide
    (MN tier 0: 7–862 against 46 built; NC: 17–5,374 against 607).
- **Tests A–C:** Form A passes 1 of the state-by-state tests (test A in Texas); Form B passes none. Test C,
  run for Form A only, fails in all five states.
- **Tie-breaker (not needed):** B's tier-1 held-out log score is 14.8 below A's (paired SE 18.7) over 52 places.
- The sensitivities do not change the decision: no tier passes for either form at the field k's 5th or 95th
  percentile or without the low-recall rows.

## Refit values, Form A, all five states (central k)

| | Value | 90% profile interval |
|---|---|---|
| θ (ADU permits per 1,000 eligible lots, reference market) | 0.756 | 0.554–1.112 |
| α (place-effect variance) | 1.92 | |
| m_o (owner-occupancy rule share) | 1.0 | grid |
| m_x (other partial rules share) | 0.4 | grid |
| Fit | 64 places, 395 place-years | log-lik −1,347.7 |

Leave one state out (θ per 1,000): without MN 1.567, NC 0.723, OH 0.767, TX 0.717, OR 0.609. Leaving out
Minnesota doubles θ; the other four agree within 20%. D-053's adopted θ was 0.308 with m_x 1.0; the new fit
set (11 new places), the k-scaled counts and the int-truncation fix all enter here, so the two are not a
like-for-like comparison. **These values are not written to config;** that is a decision for Ben (below).

Form B (approach 3; g held at 0 because there are only 5 events in 2 states): log-lik −1,136.3, α 1.26.
The state-intercept spread s used at tier 0 is 1.79 (MN out), 2.00 (NC), 0.44 (OH), 1.79 (TX), 0.98 (OR).

## Data-tier test (leave one state out; target 2021–2024, tier-2 city left out)

Central k. "Useful" = inside P10–P90 and observed ÷ P50 within ×2.

| State (places) | Form | Tier | Observed | P10 | P50 | P90 | Inside | Obs ÷ P50 | Useful |
|---|---|---|---|---|---|---|---|---|---|
| MN (36) | A | 0 | 46 | 43 | 127 | 354 | yes | 0.36 | no |
| | A | 1 | 46 | 59 | 155 | 395 | no | 0.30 | no |
| | A | 2 | 46 | 54 | 126 | 255 | no | 0.37 | no |
| | B | 0 | 46 | 7 | 80 | 862 | yes | 0.58 | **yes** |
| | B | 1 | 46 | 9 | 103 | 1,096 | yes | 0.45 | no |
| | B | 2 | 46 | 10 | 121 | 246 | yes | 0.38 | no |
| NC (11) | A | 0 | 607 | 7 | 81 | 592 | no | 7.5 | no |
| | A | 1 | 607 | 37 | 227 | 1,183 | yes | 2.7 | no |
| | A | 2 | 607 | 41 | 209 | 908 | yes | 2.9 | no |
| | B | 0 | 607 | 17 | 330 | 5,374 | yes | 1.8 | **yes** |
| | B | 1 | 607 | 19 | 377 | 6,513 | yes | 1.6 | **yes** |
| | B | 2 | 607 | 40 | 148 | 436 | no | 4.1 | no |
| OR (3) | A | 0 | 527 | 28 | 145 | 529 | yes | 3.6 | no |
| | A | 1 | 527 | 28 | 145 | 529 | yes | 3.6 | no |
| | A | 2 | 527 | 44 | 195 | 698 | yes | 2.7 | no |
| | B | 0 | 527 | 1 | 20 | 170 | no | 26 | no |
| | B | 1 | 527 | 1 | 20 | 169 | no | 26 | no |
| | B | 2 | 527 | 1 | 14 | 66 | no | 38 | no |
| TX (2) | A | 0 | 364 | 0 | 25 | 542 | yes | 15 | no |
| | A | 1 | 364 | 3 | 62 | 460 | yes | 5.9 | no |
| | A | 2 | 364 | 4 | 62 | 400 | yes | 5.9 | no |
| | B | 0 | 364 | 5 | 82 | 1,075 | yes | 4.4 | no |
| | B | 1 | 364 | 7 | 112 | 1,508 | yes | 3.2 | no |
| | B | 2 | 364 | 18 | 115 | 736 | yes | 3.2 | no |
| OH (0) | both | all | – | | | | | | not scorable |

Useful states by tier (claim needs 4):

| Variant | A t0 | A t1 | A t2 | B t0 | B t1 | B t2 |
|---|---|---|---|---|---|---|
| central | 0 | 0 | 0 | 2 | 1 | 0 |
| field k 5th pct | 0 | 0 | 0 | 2 | 1 | 0 |
| field k 95th pct | 0 | 0 | 0 | 2 | 1 | 0 |
| without low-recall rows | 0 | 0 | 0 | 2 | 3 | 1 |

Findings from the table, reported, not acted on:
- **Tier 2 rarely helps Form A.** Updating on the state's largest city narrows A's range but moves its
  median little, so a state that is off at tier 1 stays off.
- **Form B's tier-2 update collapses.** Its effective sample size after reweighting is 1.0–2.6 draws in MN, NC
  and OR (Form A: 15,600–18,900 of 20,000). B's shared draws are so spread out that one city's counts pick
  out a single draw. B's tier-2 ranges are therefore not reliable.
- **Oregon's tier 0 equals tier 1 for Form A** because Oregon's state law rows set the rule in every city,
  so borrowed and own local rules give the same rule in force.

## Tests A–C (D-074 §3, state by state)

**Test A, new places** (not in D-053's fit set; each predicted with a new place effect). Pass: ≥60% inside
P10–P90 and median obs ÷ P50 within ×2.

| State | New places | Form A inside, median ratio | A | Form B inside, median ratio | B |
|---|---|---|---|---|---|
| MN | Rochester | 1/1, 0.18 | fail | 1/1, 0.23 | fail |
| NC | Asheville, Cary, Chapel Hill, Charlotte, Durham, Raleigh, Wilmington | 6/7, 3.3 | fail | 6/7, 2.6 | fail |
| TX | College Station | 1/1, 0.91 | **pass** | 1/1, 0.16 | fail |
| OR | Medford, Salem | 1/2, 5.7 | fail | 2/2, 2.2 | fail |
| OH | none | | n/a | | n/a |

**Test B, roll counts** (towns with an accepted rule, the k-setting city left out). Pass: roll total inside
P10–P90.

| State | Towns, years | Roll count | Form A P10–P50–P90 | A | Form B P10–P50–P90 | B |
|---|---|---|---|---|---|---|
| NC (Wake) | 7, 2020–2023 | 5 | 28–83–218 | fail | 14–35–77 | fail |
| OH (Franklin) | 3, 2020–2024 | 1 | 2–19–102 | fail | 2–9–29 | fail |

Both forms predict far more ADUs in the suburban towns than the rolls show.

**Test C, the no-reform floor** (Form A only; Form B has no scenario engine). Pass: in every counted place, the
engine's no-reform median a year ≥ the counted ADUs a year (k applied). **Fails in all five states.** 43 of
73 places fall short. Most are places with under one ADU a year, where the median of a small count is a
fraction (ratio about 0.75). But larger places also fall 2–20% short: Durham, Asheville, Wilmington and New
Hanover County (NC), Columbus (OH), San Antonio and Fort Worth (TX), and Medford and Salem (OR).

**Count of tests passed** (D-079's decision input): Form A 1, Form B 0.

## Rule-change events (the check on g, which is held at 0)

| Place | Year | Dose | Predicted step | Observed step |
|---|---|---|---|---|
| Inver Grove Heights | 2019 | 0.61 → 0.71 | 1.28× | 3.43× |
| Minneapolis | 2021 | 0.67 → 1.00 | 1.11× | 0.50× |
| Charlotte | 2023 | 1.00 → 0.82 | 2.07× | 3.08× |
| Raleigh | 2021 | 0.33 → 1.00 | 6.59× | 37.6× |
| Wilmington | 2024 | 0.82 → 0.87 | 1.23× | 3.21× |

## Sensitivities

- **Field k at its 5th and 95th percentiles:** θ 0.735 and 0.786 per 1,000. Claim tiers are unchanged: none.
- **Without the low-recall rows** (Asheville before 2022; Austin's inferred rule has no counts in the table,
  so only Asheville's 6 place-years leave): θ 0.747. No tier passes. Form B reaches 3 useful states at
  tier 1, which is still short of 4. Form B passes test A in Oregon. Tests passed: A 1, B 1. The log-score
  gain is −22.0 (SE 24.3). Form A is still kept.
- **Fort Worth's no-kitchen count** (not in the fit): 2015–2026 central 64, no-kitchen 108; 2023–2025 central
  27, no-kitchen 43.

## Not saved

- τ's four-state profile (Form A's tier-0 state effect) was computed and used but not written out. The run log
  and summary do not give τ̂. Getting it needs a rerun of `cal.tau_profile` on the saved fits, a read-only
  step that touches no score.

## Files

`run-log.txt` · `summary.json` · `fits.csv` (every fit, every variant) · `tiers.csv` · `logscores_tier1.csv` ·
`test_a.csv` · `test_b.csv` · `test_b_towns.csv` · `test_c.csv` · `event_check.csv` · `fit_set.csv`,
`events.csv` (written before any fit) · `results.html` (the results page).
