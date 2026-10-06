# WS-OH · Ohio ingestion and transport-only run

**Start:** week 3 (Oct 28). **V0 by Nov 10**; V1 + statewide run + V7 by Dec 1.
**Owns:** `src/lotline/adapters/states/oh/`, `config/states/oh.yaml`, `config/reforms/oh.csv`, `config/crosswalks/oh_*.csv`, `tests/states/oh/`, `reports/oh/`.
**Role:** the **sparse-evidence state**. No in-state reform is old enough to estimate an effect. The tool has to rely on the mechanism prong and evidence transported from other states, and say so clearly. That is exactly the situation most states are in, which makes Ohio a demonstration of the sparse-data bonus (Rules §8).

## Read first
`docs/research/lotline-data-catalog.csv` (rows `state=OH`), validation plan V7, BUILD_PLAN §5.

## Sources

| Key | Source | Access | Feeds | Notes |
|---|---|---|---|---|
| `oh_parcels` | Ohio Statewide Parcels public view | ArcGIS FeatureServer (2,000/query) | `parcels` (tier 2) | Only `StateLUC` (DTE codes; 510 = SF) + `LandArea`. The 2022 vintage is token-gated; skip it. |
| `franklin_auditor` | Franklin County Auditor FTP: shapefiles (archived to 2002) + CSVs (monthly since 2014: parcel, dwelling, sales, permits, transfers) | Bulk download | `parcels` (Columbus, tier 1), prices, history | Best Ohio parcel history; enables a Columbus V2 |
| `columbus_permits` | Columbus Building Permits (CC0) | ArcGIS REST | `permits` | 2010–present, UNITS, demolitions; ADU from sub-type/description |
| `cincy_permits` | Cincinnati Building Permits (`uhjb-xac9`) + combo permits (`thvx-5mem`) | Socrata | `permits` | Public domain; UNITS, CO date |
| `cle_permits` | Cleveland issued permits | ArcGIS REST | `permits` | **ODbL share-alike: runtime fetch only, never redistribute derived tables.** Has a form-based-code-area flag. |
| `columbus_zoning` | Columbus base zoning (CC0) | ArcGIS REST | SF-only identification | |
| `oh_fees` | Columbus water capacity charges | PDF | `fees` | $335–397: far below the $50k Handbook value |

## Tasks
- [ ] Adapters + contract tests; DTE `StateLUC` crosswalk.
- [ ] `jurisdictions` incl. townships. Townships often permit via county or state building departments, so check BPS coverage.
- [ ] `config/reforms/oh.csv`, each row sourced:
  - Cincinnati Connected Communities (June 2024);
  - Columbus Zone In (2024);
  - Columbus ADU (Nov 2025);
  - Cleveland form-based code pilot areas.
- [ ] **V0:** Columbus and Cincinnati permits vs BPS; Franklin parcel coverage; statewide `StateLUC` coverage.
- [ ] **V1:** baseline (BPS) for Ohio places.
- [ ] **V2 (optional, if time):** Columbus mechanism test on Franklin monthly archives.
- [ ] **V7:**
  - overlap diagnostics of Ohio places vs the calibration set;
  - low-confidence flags where Ohio sits outside the comparables;
  - a statewide run that shows its evidence-prong range is wider and the mechanism prong carries the weight.
- [ ] **Early signal (not a test):** Cincinnati Connected Communities 2024–25 permits vs prediction, labeled descriptive.

## Gotchas
- ODbL obligations for Cleveland.
- Ohio's 88 county auditor systems differ, so don't try to harmonize sales statewide. Franklin is the tier-1 county.
