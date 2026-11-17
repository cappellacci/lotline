# D-092 deviation (b), runs 9–11: φ, the refit and the §7 tests with lumpy years (2026-11-15)

**What this is:** the pre-registered follow-through of run 8.
- **Run 9** estimates φ, the per-year negative binomial spread, on both origins.
- **Run 10** refits M and C4 with that φ.
- **Run 11** reruns §7's tests unchanged: the same bars, draws (20,000) and seed (20261112).

**Nothing was written to config.**

- **Go-ahead:** Ben, 2026-11-15, "Yes, code and refit".
- **Commands:**

  ```bash
  uv run python scripts/dev/mm_kappa_d092.py --form year --out reports/mm-d092/run9-phi
  uv run python scripts/dev/calibrate_mm_d092.py --phi 13.633 --out reports/mm-d092/run10-refit-phi
  uv run python scripts/dev/mm_tests_d092.py --phi 13.633 --run4 reports/mm-d092/run10-refit-phi \
      --run3 reports/mm-d092/run3-rolls --out reports/mm-d092/run11-tests-phi
  ```

  The refit took 44 min and the tests 5.5 min, on cached tables only. St. Paul and Ramsey are not in the panel,
  and nothing was unblinded.

## Run 9: φ

| Fit | φ̂ | 90% interval | Pseudo-forecasts |
|---|---:|---|---:|
| **Both origins (used)** | **13.63** | 12.85–14.48 | 941 |
| 2021 origin only | 17.46 | 16.15–18.89 | 468 |
| MN / NC / OH | 7.4 / 8.1 / 8.1 | | 186 / 80 / 289 |
| TX | 20.0 | at the search's upper edge | 386 |

## Run 10: the refit (M and C4)

| | Runs 4–5 (Poisson baseline) | Run 10 (lumpy years, φ 13.6) |
|---|---|---|
| θ (M), per 1,000 eligible lots a year at maturity | 0.63 (0.36–1.32) | **1.68 (0.12–21.9)** |
| Five-year rate r5 (M) | 0.00048 (0.00027–0.00099) | **0.00027 (0.00007–0.00076)** |
| Ramp half-life | 1.0 yr | 4.5 yr (1.0–6.0) |
| α, the place spread | 7.9 | about 0: the per-year spread absorbs it |
| θ without Oregon | 0.034 | **1.08** |
| M against "no reform effect", held out | +186 (SE 63) | **+5.0 (SE 3.4)** |
| C4 against M | +4.1 (SE 1.4) | +1.05 (SE 0.21) |

The sensitivities each move θ by under 6%: S excluded, S at dose 1, and dropping the earliest-known or unconfirmed
rows.

## Run 11: §7's tests

| Test | Run 5 (M) | **Run 11 (M)** | Run 11 (C4) | Bar |
|---|---|---|---|---|
| A: new places (Houston only) | fail | fail | fail | ≥ 60% inside and median within ×2 |
| B: roll check | fail | **pass** | **pass** | Wake, Franklin, Minneapolis all inside |
| C: no-reform floor | fail (37% inside) | **fail, narrowly (79% inside; MN total missed)** | same | ≥ 70% inside and every state total inside |
| Leave one state out | fail (OR missed) | **pass** | pass | no state with ≥ 3 places "missed" |
| Placebo | fail | fail | — | placebo r5 upper bound < main r5 |
| Place coverage | 0.44 | **0.84** | 0.78 | 0.60–0.95 |
| Tests A–C passed | 0 | **1** | 1 | |

- **The pre-registered success criteria:**
  - Coverage inside 0.60–0.95: **met** (0.84).
  - Test C: **missed**, on one rule only. 79% of places are inside, against a bar of 70%, but Minnesota's three
    no-reform places built 32 against a P90 of 13. Ohio's and Texas's totals, which missed in run 5, are now inside.
- **Test A** fails because its single place, Houston, has a median forecast of 0 against 21 observed. That is
  inside P10–P90 (0–31), but no finite ratio exists.
- **§5's rule picks C4** (both pass 1 test; C4 beats M by 5 SE). As in run 5, this is a decision for Ben: θ_C4
  is 1.04 against M's 1.68.

## What it says, in plain language

1. **The ranges are honest now.** Coverage is 0.84, and Oregon, Ohio and Texas fall inside. Runs 4–5 failed
   because the no-reform path was treated as certain. Treating each year as lumpy fixes that.
2. **Honest ranges are wide.**
   - θ's 90% interval spans 0.12–21.9, a factor of about 180.
   - Oregon held out gets 459–9,968 buildings, against 703 observed.
   - Texas's no-reform places get 1,701–7,183, against 4,515 observed.
3. **The reform effect is no longer clearly detected.** Once the baseline can swing as much as real places do:
   - M beats "no reform effect" by only 1.5 SE;
   - moving every event three years early gives a larger five-year rate (0.00045) than the real dates (0.00027).

   The cap rises in this data may raise 2–4 unit building, but these counts can't show it apart from the
   project-to-project noise.
4. **Oregon and the other four states now agree much better:** θ 1.08 without Oregon against 1.68 with it. Run 4
   had a gap of about 20×. That gap was mostly the over-sure baseline.

## What this means for the next step (for Ben; not done)

- **Place types are next, as decided.** A core city, suburb or town term (ADU D-088) could explain part of the
  per-year spread. That would narrow the ranges for every place without any extra data.
- **The lumpiness might be counted directly.** Projects are the real unit: buildings per permit date at one
  parcel or developer. Run 1 found permit tables with parcel IDs for about 11 sources. Counting projects instead of
  buildings would make the noise model fit the mechanism.
- **Config:** nothing changes until Ben chooses. The current tool still runs D-059's θ of 0.12.
