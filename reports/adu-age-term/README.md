# ADU Form A″: housing age as a second place term (D-087), run 2026-11-14

**What this is:** one run, as D-087 pre-registers it. Ben accepted D-087 on 2026-11-14 ("Let's try D-087").

**The three forms:**
- **Form A:** today's ADU form.
- **Form A′:** A × exp(β_o z_owner) (D-084).
- **Form A″:** A′ × exp(β_a z_age).

**Inputs:**
- z_age is the place's ACS 2011–15 share of homes built before 1960 (B25034), standardized with D-087's fixed center (0.2045) and scale (0.1669).
- z_owner is as in D-084.

**How they are compared:** all three are refitted on the checked rule rows, by one fitter, and scored on D-079's tests. The decision is two steps under D-084's rule (`adu_owner.decide`):
1. A′ against A.
2. A″ against the base in use.

**Results page:** https://claude.ai/artifact/34Yor5h8wn51dDAT3PoXaf (built by `scripts/dev/adu_age_page.py`).

## How it ran

- **Command:** run from the main checkout, so it loads `.env`:
  `PYTHONPATH=<worktree>/src .venv/bin/python <worktree>/scripts/dev/adu_age_refit.py --out <worktree>/reports/adu-age-term --workers 7`.
- **Commit:** `52d4ef2a`. The code and D-087's "Built" note were committed at `84ba6b4f`, before any fit.
- **Setup:** offline, 20,000 draws, D-084's seed. It took 1 h 40 min (19:50 to 21:30 UTC). Log: `run-log.txt`.
- **A smoke run came first.**
  - It used `--smoke`: a 2 × 2 (m_o, m_x) grid and 500 draws. It checked the code path end to end before the full run.
  - Its outputs were overwritten by this run.
  - I saw its two decision lines before the full run started. Both picked Form A, on the toy grid.
  - Nothing in the code or the rule changed between the smoke run and this run. The only commit between them added the `--smoke` flag itself.
- **Holdouts:** St. Paul (MN V5) is out of every fit and score. ACS rows went through `holdout.apply_acs`. No `--unblind`.
- **Nothing is written to config.**

**Deviations from D-087 as written** (also in D-087's "Built" note):
1. **The rule rows are #419's head (`ef37063f`), merged into this branch.** #413, #417 and #419 are not yet on `main`.
2. **Test D is not run.** D-085's code is on the unmerged #420.
3. **Step 2's base is step 1's winner,** because A′ is not adopted on `main` (#418 is open).

## Headline

- **The rule keeps Form A in both steps.** The pick depends on single places (see "How fragile" below).
  - **No form passes D-075's claim rule at any tier.** Useful states at tiers 0, 1 and 2:
    - A: 0, 0, 0;
    - A′: 1, 2, 2;
    - A″: 1, 1, 1.
  - **Step 1, A′ against A:**
    - A′'s tier-1 held-out log score beats A's by **+7.74** over 56 places, against a bar of 2 paired SE = **7.37**.
    - But A′ passes **1** of tests A–B and A passes **2**. So the rule keeps A.
  - **Step 2, A″ against A:**
    - A″ beats A by **+7.89**, against a bar of **5.62**.
    - Tests A–B: A″ passes 1, A passes 2. So the rule keeps A.
- **Housing age adds nothing held-out on top of owner share.**
  - A″ against A′: +0.15 log score, against 2 SE of 3.57.
  - In-sample, A″ against A′: likelihood-ratio statistic 3.34 on 1 degree of freedom.
- **Between states the signal is owner share; within states it is housing age.**
  - With one θ per state (the within-state sensitivity):
    - β_o falls to −0.09 (SE 0.28);
    - β_a rises to +0.87 (SE 0.26).

## Fits (all 64 places, 491 place-years; m_o 1.0, m_x 0.8 for all three)

| | Form A | Form A′ | Form A″ |
|---|---|---|---|
| θ per 1,000 eligible lots (90%) | 0.503 (0.359–0.784) | 0.379 (0.278–0.553) | 0.367 (0.271–0.531) |
| α, place-effect variance | 2.648 | 1.844 (−30%) | 1.769 (−33%) |
| β_o per SD of owner share (90% Wald) | 0 | −0.78 (−1.10 to −0.46) | −0.70 (−1.02 to −0.38) |
| β_a per SD of housing age (90% Wald) | 0 | 0 | +0.44 (+0.03 to +0.84) |
| log-likelihood | −1,418.63 | −1,411.50 (LR 14.3 vs A) | −1,409.83 (LR 3.3 vs A′) |

- **The checked rows move Form A.**
  - On D-079's rows, Form A had θ 0.756, α 1.918, m_x 0.4.
  - Here it has θ 0.503, α 2.648, m_x 0.8.
  - These rows also add 96 place-years over D-084's 395.
- **Corr(β_o, β_a)** in A″ is 0.22. Owner share and age correlate −0.39 across the 64 places.
- **β, leaving out each state (A″):**
  - β_o stays below zero, with an interval clear of zero, in every fold.
  - β_a stays above zero in every fold. Its interval crosses zero only without North Carolina (−0.18 to +0.84).
- **β, leaving out each new place (test A's fits):**
  - β_o ranges from −0.65 to −0.74.
  - β_a ranges from +0.32 to +0.47. Its interval crosses zero without Asheville or College Station.

## Tests A–C

| Test | State | A | A′ | A″ |
|---|---|---|---|---|
| A | MN | fail | fail | fail |
| A | NC | fail | fail | fail |
| A | TX | **pass** | fail | fail |
| A | OR | fail | fail | fail |
| B | NC | fail | fail | fail |
| B | OH | pass | pass | pass |
| | **passed** | **2** | **1** | **1** |

- **Test A in Texas is one place, College Station.**
  - Observed: 5.4 ADUs over 4 years.
  - Predicted medians: A 6, A′ 37, A″ 21.
  - College Station is the most renter-heavy place in the fit.
- **Test A in North Carolina fails for every form.** Its median observed ÷ P50 over 7 places:
  - A: 5.0;
  - A′: 2.22;
  - A″: 2.69.

  The bar is 2.
- **Cary's predicted median dropped.** It is 4 under A and A′, against 22 to 23 in D-084's run. I have not traced which input change moved it.
- **Test C** is run for Form A only (the scenario engine has no place terms). It passes in all five states at D-082's tolerance. File: `test_c_form_a.csv`.

## How fragile the pick is (after the result; does not change the decision)

**Without College Station:** the tests count ties at 1 each. Step 1 would then pick A′: gain +8.07 against a bar of 7.31 over 55 places.

**Step 1's score margin is thin:** +7.74 against a bar of 7.37.

## Sensitivities (reported, not used to choose)

- **A″ within states** (one θ per state):
  - β_o −0.09 (SE 0.28);
  - β_a +0.87 (SE 0.26);
  - α 1.26, against 1.80 for the same model with both β's set to 0.
- **Age without owner share** (Form A × exp(β_a z_a)):
  - β_a +0.61 (+0.17 to +1.06);
  - α 2.39;
  - LR 5.5 against A.
- **At m_x 0.4** (D-079's value):
  - A″: β_o −0.59, β_a +0.46;
  - A′: β_o −0.68.

  The β's barely move. m_x's change comes from the rows, not from the terms.

## Files

| File | What |
|---|---|
| `owner_share.csv`, `housing_age.csv` | Inputs per place, with source and vintage check |
| `fits.csv` | Every fit: central, folds, sensitivities |
| `tiers.csv` | D-075 data tiers by held-out state and form |
| `logscores_tier1.csv` | Tier-1 held-out log score per place and form |
| `test_a.csv`, `test_b.csv`, `test_b_towns.csv` | D-074 tests A and B |
| `test_c_form_a.csv` | Test C, Form A |
| `summary.json` | Decisions, test counts, LR statistics, sensitivities |
| `results.html` | The results page |
| `run-log.txt` | The run's log |
