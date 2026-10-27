# Franklin County: D-035's scaled history against real yearly parcel rolls (OH S6a)

*WS-OH, 2026-10-27. Script: `scripts/dev/oh_franklin_history.py` (tests:
`tests/states/oh/test_franklin_history.py`). A check, not an input: no processed table changes.*

**Question.** Ohio has one parcel roll per jurisdiction (Franklin County: the 2023 statewide snapshot), so every
other year of `eligible_parcels` is the jurisdiction's ACS one-unit-detached series scaled to that roll
(`parcels_scaled_acs`, D-035). How close is that to a real count?

**Data.** The Franklin County Auditor's `Parcel.xlsx` (parcel ID and DTE land-use code) from the last appraisal
snapshot of each year, 2016–2025 (10 files, 450 MB, in `raw/franklin_auditor/<snapshot>/`, manifest entries
under `dev.oh_franklin_history`). The archive has no appraisal snapshots before 2016.

**Method.** Each archive parcel is counted the way `build.eligible.classify` counts a roll parcel: ADU =
SF_DETACHED land use; missing middle = SF_DETACHED or VACANT_RESIDENTIAL (zoning unknown). It takes the
jurisdiction of the same parcel in the 2023 roll, else its taxing district's if 95% of the district lies in one
jurisdiction (at most 70–280 eligible parcels a year are left unplaced). Twelve jurisdictions with 1,000+
eligible lots lie wholly in Franklin County and are compared directly. Five cross into other counties (the
archive sees only their Franklin part), so for them the archive count is divided by their Franklin share of
houses, an approximation.

## Results (ADU denominator; missing middle is within 0.5 points of it throughout)

**The definitions match.** In the roll year itself the two sources agree to a median −0.6% (the roll is
September 2023, the archive December 2023).

**Levels: close.** Across the 12 single-county places, 2016–2024:

- 68% of place-years are within 5% of the real count, and 96% within 10% (median absolute gap 3.2%);
- summed over the 12 places the gap is at most 3% in any year (−0.7% in 2016, +2.9% in 2021);
- the largest misses are small, fast-growing places early in the window: Obetz −22% in 2016 and New Albany −11%.

**Trends: inherited from ACS, not from the parcels.** The scaled series rises and falls with ACS. Built-out
inner suburbs gained almost no houses, but their scaled series grows:

| 2016 → 2023 | Real parcels | Scaled (D-035) |
|---|---|---|
| Worthington | −0.2% | +8.7% |
| Gahanna | +0.6% | +9.7% |
| Upper Arlington | −0.1% | +3.3% |
| Hilliard | +7.6% | +2.7% |
| New Albany | +11.6% | +22.7% |
| Obetz | +29.9% | +54.5% |
| Unincorporated Franklin | +3.6% | −2.3% |

The multi-county places, read approximately: **Columbus's scaled count is 4–5% low in 2016–2019** and within 1%
from 2021 on. Reynoldsburg is 8–12% low before 2021, Dublin 4–8% low before 2020, and Westerville within 1% of
the real count except in 2020 (+4%). Canal Winchester is 6% low in 2016 and 8–14% high from 2020 on.

## What it means for the panels

- **The mostly level offsets are absorbed** by place fixed effects in the D-024 and D-025 estimators. What reaches
  the estimates is the within-place drift: a pre-period denominator a few percent low makes pre-period rates a
  few percent high, which slightly *understates* a reform's effect. For Columbus that is about 4–5% before
  2020, small next to the ADU count's own measurement error (about 1 in 4 ADUs found).
- **The scaled series should not be read as a growth measure** for a single place (for example, "lots grew 9%
  in Gahanna"). Its year-to-year change is ACS's, with ACS's sampling noise.
- **Option for Ben (not done):** for Franklin County places, real yearly counts 2016–2025 could replace the
  scaled years (a `franklin_auditor` roll per year, `denominator_source = "parcels"`). That would make the
  Franklin ADU-panel places (Columbus, Dublin, Gahanna and any suburb coded from the rules tracker) use real
  denominators. It changes the eligible table, so it needs a decision (and it leaves 2010–2015 scaled, since
  the archive starts in 2016).

## Reproduce

```bash
uv run python scripts/dev/oh_franklin_history.py --csv franklin_history.csv
```

It needs the processed Ohio `parcels`, `jurisdictions` and `eligible_parcels` tables (built with #232) and
downloads the 10 files on first run.
