# D-082 run 3: lots that gained a 2–4 unit building between two parcel rolls (2026-11-12)

**What this is.** This is the observed side of test B (D-082 §2, §7). We take two county or city tax rolls a few
years apart and look at every lot that held one house, or nothing, on the first roll. We count how many of those
lots hold **one building with 2–4 homes** on the second roll. Test B then compares these counts with what the
model predicts (run 5). **Nothing was fitted. Nothing was written to config.** No data was downloaded: the Wake,
Minneapolis and Met Council rolls are the processed tables, and Franklin uses the cached auditor spreadsheets.

- **Go-ahead:** Ben, 2026-11-12 ("Can we get close to having a finalized model over night?").
- **Command:** `uv run python scripts/dev/mm_counts_d082.py --rolls --out reports/mm-d082/run3-rolls`.
- **Holdouts:** every roll went through `mm_counts.blind`. The Met Council roll lost 754,645 rows, which are all
  of Ramsey County, St. Paul included. Nothing was unblinded.
- **Rule** (`mm_counts.diff_rolls_24`, committed with a synthetic test before any diff was run):
  - A lot counts on roll 1 if it was a **single dwelling** (one dwelling building with one unit) or **vacant
    residential** land.
  - It **gained** if, on roll 2, it holds one dwelling building with 2–4 units.
  - Lots that grew more than 20% in area (**merges**) and parcel IDs retired by roll 2 (**splits**) are reported
    and left out.
  - The share has a 95% Wilson interval.

## Result (main reading)

| Area | Rolls | Lots counted | Gained a 2–4 building | Share (95% interval) | Merges | Splits |
|---|---|---:|---:|---|---:|---:|
| Wake (all towns) | 2019-11 → 2023-12 | 289,700 | 38 | 0.013% (0.010–0.018%) | 485 | 1,588 |
| — Raleigh only | | 90,122 | 19 | 0.021% (0.013–0.033%) | 76 | 389 |
| Franklin (all) | 2016-12 → 2024-12 | 354,999 | 149 | 0.042% (0.036–0.049%) | 117 | 2,016 |
| — Columbus only | | 216,560 | 133 | 0.061% (0.052–0.073%) | 57 | 55 |
| Minneapolis | 2017 → 2024 | 77,234 | 275 | 0.36% (0.32–0.40%) | 163 | 259 |
| Met Council (outside Ramsey) | 2021 → 2025 | 649,905 | 359 | 0.055% (0.050–0.061%) | 2,053 | 2,614 |
| — Met Council, units as coded | | 195,380 | 14 | 0.007% (0.004–0.012%) | 220 | 1,509 |

The per-place rows (GEOID, counts, share and interval) are in `roll_gains_by_place.csv`. Area totals are in
`roll_gains_by_area.csv`, and the rolls used and data fill are in `rolls_meta.csv`.

## What the numbers say, in plain language

1. **A house lot rarely becomes a duplex, triplex or fourplex.** Even in Minneapolis, the city with the
   broadest three-unit rule since 2020, about 1 in 280 house lots did it over seven years. Elsewhere it is 1 in
   1,600 (Columbus) to 1 in 7,600 (all of Wake).
2. **Minneapolis stands out.** Its share is about 6 times Columbus's and about 17 times Raleigh's. The roll window
   (2017 → 2024) spans its 2020 change. Within Met Council, the Minneapolis place row (2021 → 2025) is
   0.28%, still far above any suburb.
3. **These counts are lower bounds on new 2–4 building.** They see only lots that were one house or vacant on
   roll 1 and are one building on roll 2. A new subdivision, where the parcel is split before building, shows
   up as a **split** and is left out (Wake: 1,588; Franklin: 2,016). So are lots that end with two buildings.
4. **Met Council depends on how missing unit counts are read.** The Met Council roll has unit counts on only
   about a third of house parcels. The main reading fills a missing count from the land use (house 1, duplex 2,
   triplex/fourplex 3). Read as coded, it finds 14 gains instead of 359.

## Choices not in D-082's text (made by Claude Code, for Ben to confirm)

- **Minneapolis: 2017 → 2024, not 2026.** The 2025 and 2026 vintages have unit counts on about 1% of house
  parcels, against 100% through 2024.
- **Franklin: 2016-12-22 → 2024-12-30.** These are the cached auditor dates that have both dwelling cards and
  parcel rows. The processed `oh_parcels` table has no units. Dwelling cards give buildings and units
  (`franklin_roll_diff.summarize`, read through `mm_counts.roll_from_cards`). Only land-use code 500
  (residential vacant land) counts as vacant. Each parcel's place comes from every vintage of the Ohio roll,
  since only 2023 carries Columbus: 99.1% of parcels matched, and the rest are county (39049).
- **Met Council: missing units read from land use** (`roll_from_parcels(impute_units=True)`). The plain reading
  is reported beside it.
- **A house-coded parcel with 2+ units is ambiguous** (house plus ADU, or a miscoded duplex). It is neither a
  single dwelling nor one 2–4 building, so its building count is NA. This applies to every parcel-based roll.
- **Merge rule:** lot area up more than 20% (D-082). Wake uses `lot_sqft` from the roll. Franklin uses acres
  × 43,560.

## Not done in this run

- **The model side of test B** (predicted gains per area) and the pass/fail verdict belong to run 5.
- **Permit matching** (whether each gain has a 2–4 permit) is not part of this run.
