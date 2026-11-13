# ADU place-effect covariate screen (D-083), run 2026-11-13

**What this is.** This run asks which place factors that the ADU model does not use explain how much places
differ: the place-effect variance α. It is run as pre-registered in D-083, which Ben accepted on 2026-11-13
("Accept D-083").
- **Model:** the D-079 refit's Form A as kept (m_o 1.0, m_x 0.4), on its fit set of 64 places and 395
  place-years.
- **What it changes:** nothing in the model or config. It finds candidates for a later method entry.

- **Command:** `uv run python scripts/dev/adu_covariate_screen.py --out reports/adu-covariate-screen`. It
  ran offline from cached tables in 11 minutes.
- **Code:**
  - `src/lotline/model/adu_screen.py`, with hand-worked tests in `tests/model/test_adu_screen.py`;
  - thresholds in `config/params/adu_screen.yaml`.
- **Holdouts:**
  - St. Paul is out of the fit set.
  - ACS stock tables went through `holdout.apply_acs`.
  - BPS went through `holdout.apply`.
  - Parcel rolls went through `holdout.apply(snapshot=True)`.
  - No `--unblind`.
- **Files:**
  - `factors.csv`: each place's factor values.
  - `screen.csv`: one row per factor and version.
  - `summary.json`: availability and candidates.

## Result

**Two candidates pass all three of D-083's bars, both narrowly on the p-value bar:**

| Factor | Within-state β per SD (90%) | Holm p | α falls | Sign holds without each state | Pooled β (α falls) |
|---|---|---:|---:|:-:|---|
| **X1 Owner-occupied share** | **−0.71 (−1.17, −0.25)** | 0.083 | 16% (1.43 → 1.20) | yes (MN, NC, OR, TX) | −0.81 (26%) |
| **X2 Homes built before 1960** | **+0.59 (+0.18, +1.03)** | 0.095 | 11% (1.43 → 1.27) | yes | +0.24, not significant (1%) |
| X3 Detached single-family share | −0.32 (−0.69, +0.05) | 0.76 | 7% | yes | −0.30 |
| X4 New houses per 1,000 lots, 2013–15 | −0.19 (−0.57, +0.21) | 1.00 | 2% | no | +0.15 |
| X5 Median eligible lot size | +0.35 (−0.05, +0.75) | 0.76 | 4% | yes (MN, NC only) | +0.18 |
| R1 Place size, reference | −0.26 (−0.67, +0.20) | 1.00 | 2% | yes | +0.32 |
| R2 Home value, reference | +0.17 (−0.16, +0.50) | 1.00 | 2% | yes | +0.14 |

**Not screened, under the availability rule:**
- X6, HOA share: no state's parcel roll carries an HOA field.
- X7, homestead share: only Minnesota's rolls carry it, so 42 of 64 places (66%), below the 75% bar.

**Places without the ACS factors:** 7 of 64 have no ACS place rows. Six are Minnesota townships (ACS files
them as county subdivisions); the seventh is unincorporated Durham County.

## What it says, in plain language

1. **Places with more renters build more ADUs per eligible lot.** One standard deviation of owner share is
   about 15 points. A place 15 points more owner-occupied builds about half as many ADUs per eligible lot
   (e^−0.71 ≈ 0.49), with the same rules and market.
   - This is the opposite of the "owners build ADUs" story. Owner share most likely stands in for how urban
     a place is and how much rental demand an extra unit meets: core cities against outer suburbs and
     townships.
   - **It is the one factor that also explains differences between states.** In the pooled version α falls
     26%, and Minnesota's places are the most owner-occupied (mean 0.74, against 0.45–0.59 elsewhere). So a
     negative β pulls Minnesota's predictions down and the other states' up, the same direction as the
     D-079 misses: MN over-predicted, NC, OR and TX under-predicted.
   - That direction is read from the factor means only. Whether the leave-one-state-out medians actually
     move was not rerun.
2. **Places with older housing build more.** One standard deviation of pre-1960 share is about 17 points.
   A place that much older builds about 1.8 times as many ADUs per eligible lot (e^0.59).
   - Older neighbourhoods have the garages, alleys and lot layouts that make an ADU easy.
   - This works only within a state. Pooled, it explains almost nothing.
3. **The two candidates overlap.** Their correlation is −0.40 (older places have more renters). A joint fit
   is the next step, and D-083 reports it only descriptively.
4. **New-house building, lot size and the two references do nothing measurable.**
   - For new-house building: the co-built rule (D-041) already removes most of that channel where parcel IDs
     allow, and the Met Council places show no sign of it either.
   - D-045's flags on home value and place size don't reproduce in this model form, which already carries
     h1 and state rates.
5. **Both candidates pass narrowly.** Holm-adjusted p is 0.083 and 0.095 against a 0.10 bar. They are
   candidates, not findings.

## Leave-one-place-out check (D-083 addition, 2026-11-13)

This check was asked for by Ben ("Run the check") and pre-registered in D-083 before it ran. Command:

```bash
uv run python scripts/dev/adu_covariate_screen.py --out reports/adu-covariate-screen --influence
```

Each of the 57 places was dropped in turn and β refitted, within-state. Outputs are `influence.csv` and
`influence.json`.

| Candidate | Full β | β over 57 drops | Sign kept | p < 0.10 | Reading | Largest moves |
|---|---:|---|---:|---:|---|---|
| Owner-occupied share | −0.71 | −0.83 to −0.55 | 57 / 57 | 57 / 57 | **robust** | Fridley −0.55; Hopkins and Orono −0.83 |
| Pre-1960 housing | +0.59 | +0.43 to +0.70 | 57 / 57 | 57 / 57 | **robust** | Asheville +0.43 (p 0.075); Burnsville +0.70 |

**What it shows:**
- **No single place carries either effect.** Dropping Minneapolis, Durham, Portland or Bend barely moves β.
- **The largest moves come from small Minnesota suburbs, and from Asheville for housing age.**
- **One caveat:** the bar is the unadjusted p, as pre-registered. With Asheville out, housing age's p is 0.075.
  With the screen's Holm factor applied, that would no longer pass. Housing age is the weaker of the two.

## What would come next (needs Ben)

- **A method entry that adds owner share to the model**, and perhaps housing age, written before any fit and
  scored on D-075's tests and the data-tier test. It would say how owner share enters for a place without ACS
  place rows: townships would take their county subdivision's rows.
- **Done (see above):** the leave-one-place-out check. Both candidates are robust.
- **HOAs and homestead remain untested.** No roll carries an HOA field. Homestead is Minnesota only.

## Deviations

None. The screen ran as D-083 is written.
- **2016 eligible lots:** these come from the `eligible_parcels` table, the same one the fit uses, rather
  than recomputed. This was the reading of "as in the fit".
- **Lot size:** taken from each place's earliest roll on file.
