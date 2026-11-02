# V5 Charlotte: inputs for the frozen prediction

*WS-NC, 2026-10-21 (thread 10, S8). For WS-ENGINE, which makes and freezes the prediction
(`results/frozen/V5-NC-CHARLOTTE.json`, **by Nov 17**, #45). Nothing here reads a Charlotte or Mecklenburg
outcome from 2023-06-01: the counts come from the pre-window zoning roll (data last edited 2023-05-31) and
from the six Mecklenburg towns, which are not held out.*

## What is being predicted

Duplex and triplex units permitted on lots that became N1 when Charlotte's UDO took effect (2023-06-01),
June 2023 to 2025 (`docs/research/lotline-validation-plan.md`, V5).

## Lots that became N1

UDO §3.2 Table 3-1 translates the conventional districts R-3 → N1-A, R-4 → N1-B, R-5 → N1-C, R-6 and R-8 →
N1-D, UR-1 → N1-E (`config/crosswalks/nc_clt_udo_n1.csv`, checked against the City's PDF on 2026-10-21,
p. 3-1). Conditional districts such as "R-5(CD)" keep their approved plans and are not N1.

| N1 district | Pre-UDO district | Charlotte lots (2023-05-31) | Median lot (sq ft) |
|---|---|---:|---:|
| N1-A | R-3 | 88,243 | 15,483 |
| N1-B | R-4 | 53,270 | 11,319 |
| N1-C | R-5 | 22,485 | 9,197 |
| N1-D | R-6, R-8 | 5,079 | 7,045 |
| N1-E | UR-1 | 237 | 8,774 |
| **All** | | **169,314** | |

Reproduce with `lotline.adapters.states.nc.clt_v5.n1_lots` on the processed `clt_udo_translation` parcels.

## What the lots held before June 2023 (option b, a prior)

Charlotte's pre-window roll has no land use, and the current roll may not be read for Charlotte (snapshot
holdout rule). Ben approved option (b) on 2026-10-21: take the shares from the six other Mecklenburg towns,
among the parcels an N1 district would hold, with homes built from 2023 counted as vacant lots.

| Town | Parcels kept | Single-family house | Vacant lot |
|---|---:|---:|---:|
| Cornelius | 11,665 | 0.745 | 0.067 |
| Davidson | 5,715 | 0.657 | 0.125 |
| Huntersville | 26,980 | 0.717 | 0.142 |
| Matthews | 10,146 | 0.812 | 0.074 |
| Mint Hill | 12,031 | 0.784 | 0.149 |
| Pineville | 3,549 | 0.515 | 0.135 |
| **Pooled (used)** | **70,086** | **0.732** (range 0.515–0.812) | **0.119** (range 0.067–0.149) |

Parameters `n1_sf_share` and `n1_vacant_share` in `config/params/v5_charlotte.yaml`. Applied to 169,314 N1
lots, that is about 124,000 single-family lots (87,000–137,000) and about 20,000 vacant lots
(11,000–25,000), so about 144,000 lots eligible under rule 1.1 (D-014).

**Known bias:** the towns are suburban and grew fast; Charlotte's older inner neighbourhoods (much of N1-C
to N1-E) probably have fewer vacant lots and more non-house uses. The prediction should carry the range, not
only the central value. If Mecklenburg County sends an archived roll before about Nov 10 (option a), the
counts replace the prior.

## Still needed for the prediction (WS-ENGINE)

- **The missing-middle effect.** D-024's one run (#196) found no credible estimate; the frozen prediction
  uses whatever D-024 prior or range is on `main` at freezing, stated as such.
- **Baseline for Charlotte.** BPS files Charlotte under Mecklenburg County (37119), held out from 2023-06-01
  (D-012); the baseline must use 37119's rows before the window, or Charlotte's ACS-based denominator.
- **Other inputs** (ACS, FHFA, FRED, the demand index) are dated before the window or are not Charlotte
  outcomes.
- **Scoring after unblinding.** Mecklenburg's permit service blocks scripts (Cloudflare); Ben may download it
  by hand after the freeze. Otherwise V5 is scored on BPS 37119 (county level, disclosed).

## Input check for the freeze (2026-11-01, thread 13)

Checked on `main` at f9d9624 against the processed tables. Every input below is on `main` (code and config) or
in `~/lotline-data/processed/nc`, and none reads a Charlotte or Mecklenburg outcome from 2023-06-01.

**Reproduced today.** `clt_v5.n1_lots` on the processed layer still gives **169,314 N1 lots**. The layer's
`vintage_date` is 2023-05-31, so it predates the window. `clt_v5.town_prior` on today's OneMap roll gives the
same shares to three decimals (pooled 0.732 single-family, 0.119 vacant). The towns' parcel counts moved by a
few parcels after the 2026-10-23 OneMap rebuild (Matthews 10,142, Mint Hill 12,028), so the YAML stands.

**Files and columns for WS-ENGINE.**

| Input | File | Columns / call | Dated |
|---|---|---|---|
| N1 lots by district | `processed/nc/parcels/clt_udo_translation.parquet` via `lotline.adapters.states.nc.clt_v5.n1_lots` | `jurisdiction_geoid == "3712000"`, `zoning_raw` → `n1` (`config/crosswalks/nc_clt_udo_n1.csv`), `parcel_id`, `lot_sqft` | Layer last edited 2023-05-31 |
| What N1 lots held (option b prior) | `config/params/v5_charlotte.yaml` | `n1_sf_share` (0.732; 0.515–0.812), `n1_vacant_share` (0.119; 0.067–0.149) | The six towns' current roll; the towns are not held out |
| Eligible N1 lots | N1 lots × (`n1_sf_share` + `n1_vacant_share`) | about 144,000 (central) | — |
| Baseline denominator (citywide) | `processed/nc/eligible_parcels/eligible.parquet` | `jurisdiction_geoid == "3712000"`, `theme == "missing_middle"`, `rule_version == "1.1"`, `eligible_parcels`; `denominator_source` is `acs_sf_fallback` | **Use years ≤ 2022 only** (see below) |
| Baseline permits | `processed/nc/bps_place_year/bps.parquet`, through `holdout.apply` | `geoid == "37119"` (BPS files Charlotte under the county), `units_2`, `units_3_4`, `units_1`, `year` | The filter leaves 1992–2022 |
| Pre-window Charlotte permits (optional) | `processed/nc/permits/meck_permits.parquet`, through `holdout.apply` | `jurisdiction_geoid == "3712000"`, `building_type_std` (`U2`, `U3_4`), `units_new`, `issue_date` | To 2023-05-31 (filtered at query time and again on read) |
| Market | `processed/nc/acs_geo_year/acs.parquet` (`geo == "place:3712000"`), `market_geo_year/fhfa.parquet` (`county:37119`, `cbsa:16740`), `fred.parquet` (national) | rent, value, HPI, mortgage rate, construction-cost index | **Use years ≤ 2022** |
| Demand | `processed/nc/market_geo_year/demand.parquet` | `geo == "county:37119"` or `"place:3712000"`, `demand_bartik_loo` | **Use years ≤ 2022** |
| Missing-middle effect | whatever D-024 estimate or prior is on `main` at the freeze (`reports/mm-d024*`, `config/params/mm.yaml`) | — | State its source in the freeze file |

**Cap every annual input at 2022.** The holdout filter covers the outcome tables (BPS, permits, parcel rolls).
It doesn't cover inputs, and four of them run past the window opening for Charlotte:
- ACS (and so the ACS-fallback denominator) runs to 2024;
- FHFA runs to 2025;
- the demand index runs to 2023.

ACS 5-year estimates for 2023 and 2024 count homes built after 2023-06-01, so their one-unit housing stock
partly reflects the outcome. FHFA and the demand index for 2023 on aren't Charlotte outcomes, but they are
dated after the window opens. The clean rule is the holdout's own annual rule: **a year that touches the window
is out, so annual inputs stop at 2022.** WS-ENGINE should record this in the freeze file.

**Open item: option (a).** If Mecklenburg County sends an archived roll dated between January 2022 and
2023-05-31 by **Tue Nov 10**, WS-NC counts the N1 lots that held a house or were vacant, and those counts
replace the two shares in `v5_charlotte.yaml`, with the same file and column names. If nothing has arrived by
Nov 10, the freeze uses option (b) as above.

**For unblinding (after the freeze, not before).** The Mecklenburg legacy permit file thins out in 2025 as the
county moved to Accela: the six towns' permits fall from about 3,000 a year to 1,569 in 2025. So Charlotte's
2023–2025 outcomes will need the Accela file, or BPS 37119 at county level, disclosed as such. The legacy file
carries `zonecode` (as `zoning_raw`), which the validation plan uses to find N1 permits; check that the Accela
file has an equivalent field before relying on it.
