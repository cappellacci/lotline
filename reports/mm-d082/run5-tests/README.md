# D-082 run 5: the §7 tests and model selection (2026-11-12)

**What this is.** This is run 5 of D-082 §9. It puts each run-4 model (M, C1, C3, C4) through D-082 §7's tests,
then applies §5's selection rule. **Nothing was written to config.**

- **Command:**

  ```bash
  uv run python scripts/dev/mm_tests_d082.py --run4 reports/mm-d082/run4-refit --run3 reports/mm-d082/run3-rolls --out reports/mm-d082/run5-tests
  ```

  It uses 20,000 draws with seed 20261112 and takes about 3 minutes. Nothing is downloaded.
- **Holdouts:** St. Paul and Ramsey County are not in the panel; the script asserts this. No `--unblind`.
- **Pass rules:** these live in `src/lotline/model/mm_tests.py`, with a hand-worked test for each. The
  thresholds are in `config/params/mm.yaml` (`mm_test_*`, `mm_loso_min_places`, `mm_placebo_shift_years`,
  `mm_place_coverage_*`).
- **Files:**

  | File | What it holds |
  |---|---|
  | `loso_states.csv` | leave one state out |
  | `test_a_places.csv` | test A |
  | `test_b_areas.csv` | test B |
  | `test_c_places.csv`, `test_c_states.csv` | test C |
  | `summary.json` | everything, including the selection table |

## Result: no model passes; the rule's mechanical pick is C4

| Test (§7) | M | C1 | C3 | C4 | Bar |
|---|:-:|:-:|:-:|:-:|---|
| A: new places (1 place: Houston, now class S) | fail | fail | fail | fail | ≥ 60% inside P10–P90 and median obs/P50 within 2× |
| B: roll check (Wake, Franklin, Minneapolis) | fail | fail | fail (Minneapolis inside) | fail | all three areas inside P10–P90 |
| C: no-reform floor (43 places) | fail | fail | fail | fail | ≥ 70% inside, and every state total inside |
| **Tests A–C passed** | **0** | **0** | **0** | **0** | |
| Leave one state out | fail (OR missed) | fail | fail | fail | no state with ≥ 3 fit places "missed" |
| Placebo (event 3 years early) | fail | — | — | — | placebo r5 upper bound < main r5 |
| Place coverage (share of PITs in 0.1–0.9) | 0.44 ⚑ | 0.44 ⚑ | 0.43 ⚑ | 0.46 ⚑ | target 0.60–0.95 |
| Held-out score vs M (Σ, paired SE) | — | −422 (210) | −20.8 (8.1) | **+4.1 (1.4)** | > 2 SE |

**§5's rule picks C4.** Every model passes the same number of tests (0), and C4 beats M by 2.9 paired SE.
C4's θ is 0.633 per 1,000, against M's 0.632. **This pick should not be adopted as it stands.** With every
model failing every test, the rule has nothing to choose between. It is a decision for Ben (see below).

## Why the tests fail, in plain language

1. **The no-reform baseline is far too sure of itself. This is the main finding.**
   - The baseline for a place is its own pre-period level and growth, B, and the draws treat B as known:
     Poisson noise on B, with no uncertainty in B itself (`calibrate_mm.benchmark_places`;
     `predict_places` adds a place spread to the reform effect only).
   - Places with no reform still move a lot:
     - Reynoldsburg: 5 observed against a 144–176 baseline
     - Abilene: 307 against 100–127
     - Edinburg: 593 against 938–1,018
     - Dallas: 545 against 725–795
   - Only 37% of the 43 no-reform places land inside their P10–P90. The MN, OH and TX totals all miss.
   - The same narrow baseline causes test B's Wake and Franklin misses: their predictions are pure baseline,
     identical for every model. It also causes the low place coverage (0.44).
2. **Oregon and the other four states disagree by about 20×.**
   - Without Oregon, θ is 0.034 per 1,000.
   - With Oregon held out, every model predicts 803–1,593 or more Oregon buildings (P10) against 703 observed:
     a "missed". With a θ that small, the prediction is almost all baseline, so the baseline alone over-predicts
   Oregon.
3. **The placebo fails.** Moving every event 3 years early still gives an r5 of 0.00032 (upper bound
   0.00073), two thirds of the main r5 (0.00048). Part of what M calls "reform effect" was already happening
   before the reform. This fits point 1: if the baseline misses a place's upward drift, the reform term
   absorbs it.
4. **Test A has one place.** Houston (class S) is 21 observed against P10–P90 of 2–175 and a P50 of 7. It is
   inside, but 3× the median. One place cannot carry this test.
5. **Test B compares unlike things.** The prediction counts all new 2–4 unit buildings (BPS). The roll diff
   counts lots that gained a 2–4 unit building between two rolls.
   - In Franklin, 785 predicted buildings against 142 lots gained says most BPS 2–4 buildings in Columbus
     land on lots the roll already coded as 2–4, or are not caught by the roll codes.
   - Minneapolis goes the other way: 275 lots gained against a P50 of 77. Conversions show up in the roll
     but not in BPS.
   - Test B can't separate model error from this mismatch until the two counts are lined up.

## What would fix it (for Ben to decide; not done)

- **Give the baseline its own uncertainty.** For example, a place-level spread on B, fitted from the
  no-reform places' own year-to-year moves. Then refit, and rerun tests C, LOSO and placebo. This is a
  method change to D-059 (b′), so it needs a dated deviation entry and Ben's go-ahead.
- **Decide what Oregon is allowed to teach.** Two options:
  - fit θ on Oregon and accept the transport risk, shown as a wide range;
  - or take the four-state θ (0.034) as the main value and treat Oregon as an outside check, in line with
    D-037 / route one (*uptake calibrated on our own four states*).
- **Line up test B's two counts**, or drop test B from selection and report it as descriptive.

## Not done in this run

- **Data-tier test (§7):** not run. Too few strong permit sources (five, from run 1) have post-event years to
  compare tiers.
- **C2 (within-city lots):** not built. It needs addresses in the permit tables, and the adapters drop
  addresses as personal fields (run 1).
- **The 30-building hand check (§2):** still open (run 1).
