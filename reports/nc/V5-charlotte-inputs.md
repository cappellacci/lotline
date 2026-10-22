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
