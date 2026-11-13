# ADU Form A′, owner-occupied share as a place term (D-084), run 2026-11-13

**What this is.** One run, as D-084 pre-registers it. Ben accepted D-084 on 2026-11-13 ("Accept D-084").
- **The challenger:** Form A′ is Form A × exp(β_o z). z is the place's ACS 2011–15 owner-occupied share,
  standardized with D-084's fixed center (0.6727) and scale (0.1544).
- **The comparison:** it is scored against Form A on D-079's tests, under D-084's decision rule.

**How it ran**
- **Command:** `uv run python scripts/dev/adu_owner_refit.py --out reports/adu-owner-share --workers 7`.
- **Commit:** `7760ee5e`, where the code and the "Built" note in D-084 were committed before any fit.
- **Offline,** with seed 20261111 and 20,000 draws.

**A first start stopped.** It stopped after its fits, before any tier or test was scored, because the
worktree had no `CENSUS_API_KEY`.
- The tier-0 lot builder reads cached Census county shares but checks that the key is set.
- The rerun loaded the main checkout's `.env`. Nothing was fetched.
- The first start's log is in `run-log-stopped.txt`. Its fit values match the rerun's.

**Holdouts:** St. Paul (MN V5) is out of every fit and score. ACS rows went through `holdout.apply_acs`. No
`--unblind`.

**Code:**
- `src/lotline/model/adu_owner.py`, with hand-worked tests in `tests/model/test_adu_owner.py`;
- β_o draws in `joint_refit.GlobalsA`;
- constants in `config/params/adu_owner.yaml`;
- the page builder, `scripts/dev/adu_owner_page.py`.

## Headline

- **D-084's rule picks Form A′, narrowly.**
  - Neither form passes D-075's claim rule at any tier. A′ has 1 useful state at each tier; A has none.
  - So the rule falls to the score comparison. A′'s tier-1 held-out log score beats A's by **+5.0** over 52
    places, against a bar of 2 paired SE = **4.1**.
  - Tests A–B: each form passes **1**. A passes test A in Texas; A′ passes test A in North Carolina.
- **Every held-out state moves toward its observed count** at every tier, and CRPS improves in every state.
  But Texas and Oregon stay under-predicted at about ×2.4–2.6, and Minnesota is over-predicted ×1.7–2.1.
- **Nothing is written to config.** Adopting A′, and its values, is Ben's call.

## Fits (all 64 places, 395 place-years)

| | Form A | Form A′ |
|---|---|---|
| θ per 1,000 eligible lots (90%) | 0.756 (0.554–1.112) | 0.654 (0.483–0.917), at z = 0 |
| α, place-effect variance | 1.918 | 1.558 (−19%) |
| β_o per SD of owner share (90%) | 0 | **−0.546 (−0.877 to −0.221)** |
| m_o, m_x | 1.0, 0.4 | 1.0, 0.4 |
| log-likelihood | −1,347.71 | −1,344.00 (LR 7.4) |

- **Form A here equals D-079's** to four figures: θ 0.7563, α 1.918, log-lik −1,347.71. The fitter takes
  40 seconds instead of 35 minutes.
- **β_o, leaving out each state:** MN −0.42 (interval crosses 0), NC −0.46, OH −0.58, TX −0.55, OR −0.44.
  The sign holds every time.
- **β_o, leaving out each new place (test A's fits):** −0.48 to −0.59.

**β_o is weaker than the screen's −0.81.** This check is descriptive and was not pre-registered. It was run
after the result, at (1.0, 0.4).

| Places | β_o (pooled) |
|---|---|
| The 57 with place rows (D-083's set) | −0.81 |
| All 64 places but the six Minnesota townships | −0.76 |
| All 64 places | −0.55 |

The townships, about 95% owner-occupied, account for most of the drop.

## Data-tier test (leave one state out; target 2021–2024)

Each cell gives observed ÷ P50. **Bold** is useful: inside P10–P90 and within ×2.

| State (observed) | A t0 | A t1 | A t2 | A′ t0 | A′ t1 | A′ t2 |
|---|---|---|---|---|---|---|
| MN (46) | 0.36 | 0.30 | 0.37 | **0.60** | 0.48 | **0.59** |
| NC (607) | 7.5 | 2.7 | 2.9 | 5.2 | **1.81** | 2.03 |
| TX (364) | 15 | 5.9 | 5.9 | 4.6 | 2.4 | 2.5 |
| OR (527) | 3.6 | 3.6 | 2.7 | 2.6 | 2.6 | 2.2 |
| OH | not scorable | | | | | |

Useful states per tier: A 0/0/0, A′ 1/1/1. The claim rule needs 4. Every range, for both forms, holds the
observed total except Form A's MN tiers 1–2 and NC tier 0. `tiers.csv` has P10/P50/P90, CRPS and log scores.

## Tests A–C

**Test A (new places).** In `test_a.csv`.
- **NC passes under A′** (6/7 inside, median ratio 1.86). It failed under A (median 3.3). Durham goes from
  4.7 to 2.5, Wilmington from 5.0 to 2.2, and Charlotte from 1.5 to 0.97.
- **TX fails under A′.** College Station, the most renter-heavy place (z −2.1), goes from ratio 0.91 to 0.25.
- **OR:** Medford now lands inside its range, but both Oregon cities still sit above ×2.
- **MN:** Rochester is unchanged at 0.19.

**Test B (roll towns).** Both forms fail in NC (Wake) and OH (Franklin). A′ narrows the gap: Wake's median is
69 against 5 counted, down from 83.

**Test C** was not run for A′, as fixed in the Built note. The engine has no place term, and D-079 leaves C
out of the count.

## Sensitivities (reported, not used to choose)

- **Owner share from 2016–20:** β_o −0.45 (−0.77 to −0.13), α 1.64. Useful states 1/1/1 (MN t0 and t2, NC
  t1). No claim tier.
- **β_o within states** (one θ per state): −0.37 (−0.77 to +0.03). α goes from 1.41 to 1.29. Most of owner
  share's work is between states.
- **A′ plus pre-1960 share (outlook):** β_age +0.18. The LR against A′ is 0.56 (p 0.45). Housing age adds
  nothing once owner share is in.
- **Vintage check:** between 2011–15 and 2020–24, over the 64 places, r = 0.982 (Spearman 0.973), and the mean
  change is +0.3 points.

## Owner-share sources

`owner_share.csv` holds every fit place and roll town.
- 57 fit places read their own place rows.
- 6 Minnesota townships read their county subdivision's rows.
- Durham County unincorporated reads the county less the places whose county it is.
- No place needed z = 0.
- The Wake and Franklin unincorporated areas (test B only) read the same way.

## Files

- `run-log.txt` and `run-log-stopped.txt`;
- `summary.json`, `fits.csv`, `tiers.csv`, `tiers_2016_20.csv` and `logscores_tier1.csv`;
- `test_a.csv`, `test_b.csv` and `test_b_towns.csv`;
- `owner_share.csv`;
- `results.html`.
