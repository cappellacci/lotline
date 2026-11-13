# D-082 run 2: uplift ratios for what BPS can't see (2026-11-12)

**What this is.** Census BPS counts new 2–4 unit buildings. D-082 §3 asks how much other housing comes with
them on the same kind of lot:
- **r56:** 5–6 unit buildings on single-family-zoned lots;
- **rTH:** townhouses on single-family-zoned lots;
- **rCV:** existing buildings converted to 2–4 units;
- **s_td:** the share of new 2–4 unit buildings that replaced a house (a teardown).

Each ratio is measured against new 2–4 unit buildings in the strong permit sources from run 1, over 2016–2025.
**Nothing was fitted. Nothing was written to config.** The headline stays "2–4 only" unless Ben adopts the
uplift in a separate config PR.

- **Go-ahead:** Ben, 2026-11-12 ("Can we get close to having a finalized model over night?").
- **Command:** `uv run python scripts/dev/mm_counts_d082.py --ratios --out reports/mm-d082/run2-ratios`. It
  uses cached tables only. Raleigh's prior roll needs the PIN↔REID crosswalk from the registered Wake roll
  spreadsheets, which are read offline and use no personal column.
- **Holdouts:** every table went through `mm_counts.blind`. Nothing was unblinded.
- **Shared classifier (D-082 §6):** every permit gets one theme from `build.permit_theme` (#405) before
  counting. A U2/U3_4 row whose theme is not `mm_2_4` or `conversion` is recoded to OTHER, so the 2–4 collapse
  never counts it. These rows are ADUs filed in a 2-unit class, alterations adding no home, and demolitions.
  Demolitions stay flagged for s_td (`mm_counts.apply_themes`).
- **Two source sets:**
  - **split-strong** (main): Raleigh, Durham, Columbus, College Station and Bend, with the per-permit split
    collapse (the D-082 deviation of 2026-11-12);
  - **prereg-strong**: Raleigh, Austin and Bend, with the pre-registered collapse.

  Minneapolis is not strong. It is shown as a side figure because r56 is defined only there.

## Result

| Ratio | split-strong: pooled (range over sources) | prereg-strong: pooled (range) | Status |
|---|---|---|---|
| **s_td** (teardown share) | **0.20** (0.11–0.43) | 0.38 (0.09–0.54) | measured |
| **rCV** (conversions) | **0.023** (0–0.085) | 0.029 (0–0.115) | measured, but only Bend records any (see 3) |
| **r56** (5–6 on SF lots) | not measured | not measured | no roll has single-family zoning |
| **rTH** (townhouses on SF lots) | not measured | not measured | no roll has single-family zoning |

Pooled = Σ numerators ÷ Σ denominators (building-weighted). The range is the lowest and highest source on at
least 50 buildings. Every source here has at least 50.

**Per source (main collapse, 2016–2025):**

| Source | New 2–4 buildings | s_td | Teardown evidence | rCV |
|---|---:|---|---|---|
| Raleigh | 184 | 0.24 (44 of 182 with a parcel ID) | Wake roll 2019/2023 + demolitions (90 had no earlier roll row) | 0 |
| Durham | 209 | 0.11 | demolitions only | 0 |
| Columbus | 501 | 0.14 (70 of 483) | Ohio roll + demolitions (444 had no earlier roll row) | 0 |
| College Station | 287 | 0.43 (121 of 279) | demolitions only | 0 |
| Bend | 433 | 0.14 | demolitions only | 0.085 (37) |
| *Austin (prereg set)* | 779 | 0.54 (prereg collapse) | demolitions only | 0 |
| *Minneapolis (side)* | 163 | 0.43 | demolitions only | 0.53 (86) |

All rows, with both collapses, are in `ratios_by_source.csv`. The pooled rows are in `ratios_pooled.csv`.

## What the numbers say, in plain language

1. **About one new 2–4 unit building in five replaced a house** across the main sources, between 1 in 10
   (Durham) and 2 in 5 (College Station). This is the first measured value for the teardown share, which
   until now was a judgment (`mm_teardown_share_scale`). It is likely a **lower bound**:
   - most sources have no prior roll, so only demolition permits within ±2 years count;
   - where a roll exists, many parcels had no earlier roll row (Raleigh 90 of 182, Columbus 444 of 483);
   - Columbus's parcels appear in the Ohio roll mainly from 2023.
2. **The collapse rule moves s_td a lot** (College Station 0.43 split vs 0.82 pre-registered; Austin 0.37 vs
   0.54). Small infill projects tend to be merged parcel-years under the pre-registered rule, so the split
   reading counts more non-teardown buildings.
3. **Conversions are coded so differently across sources that rCV isn't comparable.** Only Bend (37) records
   conversions on 2–4 unit permits. Minneapolis records many (86 against 163 new buildings), but it is not a
   strong source. A broad count over every permit the classifier calls a conversion is kept per source
   (`rCV_broad`) and is **not pooled**: Bend flags thousands of remodels of houses (`RE|SFD`, one unit) as
   conversions, and Austin's 141 conversions add no counted home.
4. **r56 and rTH can't be measured yet.** Both need to know whether a lot was zoned single-family only on the
   prior roll (`sf_only_zoned`). No processed roll has that, and inventing a zoning join was out of scope.
   Minneapolis has 37 collapsed 5–6 unit buildings over 2016–2025 (29 under the pre-registered collapse). If all
   were on single-family lots, r56 would be at most 37 ÷ 163 = 0.23 there.
5. **The classifier finds almost no ADUs filed as 2-unit permits** in these sources: 2 of 1,544 Austin U2 rows
   and 0 elsewhere (`two_unit_adu_share.csv`). So the ADU/2–4 overlap is not a material correction for BPS
   places, on this evidence.

## Choices not in D-082's text (made by Claude Code, for Ben to confirm)

- **Theme recode:** described above (`apply_themes`). The run-1 coverage screen did not use the classifier.
- **Parcel keys:**
  - Raleigh's 10-digit PIN is mapped to the Wake roll's REID through both registered roll spreadsheets
    (`wake_crosswalk`).
  - Columbus's 9-digit parcel becomes `39049DDD-DDDDDD` (`franklin_key`).
- **s_td's prior roll:** Wake for Raleigh and the Ohio roll for Columbus, as in #408 choice 9. All other
  sources are demolition-only.
- **rCV numerator:** collapsed 2–4 buildings with an `is_conversion` permit, as coded in #408. The broad count
  is a diagnostic only, as explained in 3.
- **Minneapolis r56 is "not measured", not 0,** because there is no zoning flag.

## Not done in this run

- `sf_only_zoned` on any roll, which blocks r56 and rTH.
- The h ratios (homes per building by type).
- Conversion coding across adapters: Bend's `is_conversion` flag on remodels is an adapter issue for its
  workstream.
