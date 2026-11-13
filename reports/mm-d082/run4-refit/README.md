# D-082 run 4: joint refit of M and its challengers (2026-11-12)

**What this is.** This is run 4 of D-082 §9. It fits the main missing-middle uptake model and its challengers on
the D-082 event rows and BPS counts, then scores each one on states it did not see (leave one state out).

| Model | What it is |
|---|---|
| M | D-059 (b′) |
| C1 | Oregon's not-yet-treated places as controls |
| C3 | uptake scaled by the conditional z |
| C4 | M with the always-allowed level L as a prior |
| L | level fitted on the always-allowed places |

C2 (within-city lots) was not built; see run 5. **Nothing was written to config.**

- **Go-ahead:** Ben's overnight request on 2026-11-12, "Can we get close to having a finalized model over
  night?", taken as the go-ahead for runs 2–6 in order.
- **Command:** `uv run python scripts/dev/calibrate_mm_d082.py --out reports/mm-d082/run4-refit`. It reads the
  cached processed tables and downloads nothing. Wall time was 2 h 39 min.
- **Holdouts:** St. Paul and Ramsey County are dropped before fitting. The scored test places (Minneapolis,
  Durham city and Durham County) are scored, never fitted. No `--unblind`.
- **Files:**
  - `fits.csv`: every fit, with its sensitivities and the leave-one-state-out folds.
  - `place_scores.csv`: held-out log scores by place and model.
  - `structure.csv`: each place's role, event, dose class and level pool.
  - `summary.json`: everything below.

## Result

θ is new 2–4 unit buildings per 1,000 eligible parcels per year at maturity. The range is the 90% profile
interval.

| Model | θ per 1,000 | Range | α (place spread) | Ramp half-life | Places |
|---|---:|---|---:|---:|---:|
| **M** | **0.63** | 0.36–1.32 | 7.9 | 1.0 yr | 93 |
| C1 | 0.57 | 0.25–1.66 | 14.9 | 2.0 yr | 93 |
| C3 | 0.84 | 0.43–1.69 | 8.8 | 1.0 yr | 93 (slope c = 1.0) |
| C4 | 0.63 | 0.36–1.32 | 7.9 | 1.0 yr | 93 |
| L (level) | 0.87 | 0.11–135 | 54.6 | — | 15 always-allowed places |

M's five-year rate r5 is 0.00048 per eligible parcel, with a range of 0.00027–0.00099.

**Held-out scores, each challenger against M** (Σ log-score difference over 93 places, with its paired SE):

| Challenger | Σ vs M | Paired SE | Beats M by > 2 SE? |
|---|---:|---:|:-:|
| C1 | −422 | 210 | no (worse) |
| C3 | −20.8 | 8.1 | no (worse) |
| C4 | +4.1 | 1.4 | **yes (2.9 SE)** |

M beats "no reform effect" by 186, with a paired SE of 63.

## What the numbers say, in plain language

1. **Oregon is the fit.** 86 of the 93 fit places are in Oregon. The other four states add 7 places:
   - St. Louis Park
   - Garner
   - Wilson
   - Euclid
   - Austin
   - Houston
   - Lewisville

   **Without Oregon, θ falls to 0.034 per 1,000** (0.004–0.75). That is about 1/20 of the full fit and below
   the 0.12 adopted for D-059.
2. **θ is about 5 times D-059's adopted 0.12.** This follows from the change of fit set: D-082's event rule
   brings in 86 Oregon places with HB 2001 events. Without Oregon the figure is in D-059's range.
3. **C4 barely differs from M.** The level prior is very wide (log-SD 4.3, after doubling), so it hardly
   moves θ (0.633 against 0.632). Its 2.9-SE edge is real by the §5 rule but small in size.
4. **The sensitivities move θ by at most a fifth:**
   - S excluded: 0.74
   - S dose 1: 0.63
   - drop earliest-known event rows: 0.55
   - drop unconfirmed rows: 0.70
   - without TX: 0.76

   The one large move is dropping Oregon.

## Run-4 choices (made by Claude Code, for Ben to confirm)

- Lubbock and Richfield are excluded, as in `calibrate_mm_d082.EXCLUDE`, carried over from D-059.
- The fit uses BPS 2–4 unit buildings for every place (D-082 §1: BPS is the outcome everywhere). Runs 1–3 feed
  the tests, not the fit.
