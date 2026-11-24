# Why Wisconsin's forecast starts below 2019 (V8 diagnosis, D-106)

Diagnosis only. V8 is not rescored, the frozen file does not change and the result stays a fail (D-105).
Numbers come from `scripts/dev/v8_baseline_diagnosis.py`. It reads only the blind tables, which end at 2019.

## In plain words

Wisconsin issued permits for 17,308 homes in 2019. The baseline's 2021 forecast is 15,316 (median), about 12%
lower. The forecast is meant to "keep building at the recent pace", so it should start near 17,000.

**Nearly all of the drop comes from one step: pulling each place toward its county's average ("shrinkage").**
- The step is meant to stop a small township with one lucky subdivision year from being forecast to repeat
  it.
- But it is lopsided. When a busy place is pulled down toward a quieter county, the homes it loses are not
  given back to anyone.
- For apartments (5+ units), 114 places were pulled down, losing 1,795 homes a year. 717 places were pulled
  up, gaining only 564. The statewide total drops 21%.
- The biggest losers are the places that actually build apartments:

  | Place | Own pace (5+ units a year) | After shrinkage |
  |---|---:|---:|
  | Madison | 1,429 | 1,113 |
  | Wauwatosa | 172 | 103 |
  | Hobart | 141 | 25 |
  | Oak Creek | 140 | 59 |
  | Middleton | 128 | 64 |
  | Menomonee Falls | 115 | 59 |

## Step by step (homes a year, the 1,131 places forecast)

| Size | 2019 observed | 2015-19 average | Own pace (step 1) | After shrinkage (step 2) | Cycle start | 2021 mean |
|---|---:|---:|---:|---:|---:|---:|
| 1 unit | 10,831 | 10,233 | 10,381 | 9,927 | ×1.06 | 10,515 |
| 2 units | 962 | 709 | 717 | 570 | ×1.36 | 776 |
| 3-4 units | 105 | 120 | 122 | 122 | ×0.87 | 106 |
| 5+ units | 5,067 | 5,798 | 5,857 | 4,626 | ×0.87 | 4,063 |
| **All** | **16,965** | **16,860** | **17,077** | **15,245** | | **15,460** |

- **Own pace (step 1):** 17,077, close to 2019.
- **Shrinkage (step 2):** removes 1,832 homes a year (−11%), mostly duplexes (−20%) and apartments (−21%).
- **Cycle start (D-029):** adds 215 net. The random walk starts from each size class's own 2019 level, and
  2019 was a dip year for apartments (×0.87), so this cuts apartments further.
- **Median vs mean:** the 2021 median (15,316) sits 144 below the mean (15,460), because the range is skewed
  upward.

## It is not only Wisconsin

The same step lowers the total in every state at origin 2019 (total after shrinkage vs before):

| State | 1 unit | 2 units | 3-4 units | 5+ units |
|---|---:|---:|---:|---:|
| WI | −4% | −20% | +0% | −21% |
| MN | −4% | −1% | −0% | −13% |
| NC | −2% | −31% | −42% | −20% |
| OH | −5% | −22% | −21% | −12% |
| OR | −3% | −11% | −1% | −4% |
| TX | −4% | −20% | −26% | −7% |

Possible reason it went unnoticed (not checked here): the V1 backtest scores places one at a time, where
shrinkage helps, and not statewide totals, where it biases down.

## How much of the V8 miss this explains

- Holding 2019's pace for five years gives about 86,500 homes. The frozen median was 75,347; Wisconsin
  actually permitted 112,166.
- So the low start accounts for roughly 11,000 of the 37,000-home gap, under a third.
- The rest is real growth after 2019, mostly apartments (about 9,000 a year in 2021-2025, against 5,067 in
  2019). A baseline that holds the recent pace cannot see that kind of growth coming.

## Proposed fix (for later runs; a separate decision for Ben)

**Keep the totals after shrinking ("benchmarking", standard practice in small-area estimation).**
- After step 2, scale the shrunk paces in each county group (or the state, where a place falls back to it)
  so the group's total equals the total at its places' own paces.
- Each place's pull toward its neighbours is kept; only the lost homes are put back, in proportion.
- In Wisconsin this would raise the starting point by about 11-12% for every size class combined, to near
  2019's level.
- It changes every state's baseline, so it needs:
  - a dated analysis plan entry;
  - the V1 backtest rerun on all states (place errors and statewide totals);
  - before-and-after bundles.
- It does not rescore V8.
