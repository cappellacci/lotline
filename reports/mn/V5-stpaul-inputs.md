# V5 St. Paul: inputs for the frozen prediction

*WS-MN, 2026-11-01 (thread 13, M1). For WS-ENGINE, which makes and freezes the prediction
(`results/frozen/V5-MN-STPAUL.json`, **by Nov 17**, #45). Nothing here reads a St. Paul outcome from
2024-01-01, or a St. Paul roll exported on or after that day. Every count comes from the pre-window roll and
zoning snapshots dated before the window, through `holdout.apply` (with `snapshot=True` for rolls).*

## What is being predicted

St. Paul's 1-4 unit reform (`MN-2758000-missing_middle-2023`, effective 2023-11-26) rezoned the former R1–R4,
RT1, RT2 and low-density PD districts to **H1 and H2**, allowing up to four homes per lot. The test predicts 2–4
unit (Met Council `DTQ`) and 5+ unit (`MF5`) homes permitted on H1/H2 lots in 2024–2026, from data up to 2023
(`docs/build/workstreams/WS-MN.md`; holdout `V5-MN-STPAUL` in `config/states/mn.yaml`, 2024-01-01 to
2026-12-31).

**Known exposure (D-013):** some post-reform St. Paul figures appeared in a research doc during scouting. They
are not repeated here and must not be used. The freeze file should disclose the exposure.

## Which lots were zoned H1 or H2

The city publishes dated snapshots of its principal zoning layer ("Principal Zoning Archive Over Time"):

| Snapshot | Sublayer | Used for |
|---|---|---|
| November 25, 2023 | 35 | The last day of R1–R4, RT1 and RT2 (check) |
| **November 26, 2023** | **36** | **H1 and H2 on the reform's effective date (used)** |

Both are dated before the window. The archive's own edit dates show its 2026 republication, so the module
reads each snapshot's date from its name and refuses one dated 2024-01-01 or later. The snapshots are real
dated copies: they differ from later ones (for example, the T2 district has 118 polygons in November 2023,
120 in June 2024 and 123 in October 2026).

Each parcel on St. Paul's newest pre-window roll is placed by its point. That roll is Met Council's "2023"
roll, whose St. Paul part Ramsey exported on 2023-12-26 (83,283 parcels, land use known for all but 10).

| District | Lots | Single-family houses | Vacant lots | **Eligible (rule 1.1)** | Median lot (sq ft) |
|---|---:|---:|---:|---:|---:|
| H1 | 42,436 | 37,199 | 541 | **37,695** | 6,098 (houses) |
| H2 | 21,482 | 17,307 | 319 | **17,574** | 5,227 (houses) |
| **All** | **63,918** | **54,506** | **860** | **55,269** | |

"Eligible" is the missing-middle rule 1.1 (D-014): a single-family house on one unit, or a vacant residential
lot. 97 houses fall below the lot floor or have more than one unit. The other H1/H2 lots already hold duplexes
(4,738), triplexes and fourplexes (521), townhouses, condominiums, apartments or other uses.

**Check against the reform row.** Parcels in R1–R4, RT1 and RT2 on November 25 are in H1 or H2 on November 26,
all but two (both went to T2). The former PD parcels that became H1 number 73. No former R1 parcel became RL in
this roll.

Reproduce with:

```bash
uv run python -c "from lotline.io import DataStore; from lotline.adapters.states.mn import stpaul_v5 as v; r = v.load(DataStore()); print(r['h_lots']); print(r['check'])"
```

The two snapshots are cached in `~/lotline-data/raw/stpaul_zoning_archive/` (manifest rows written
2026-11-02 UTC). They are not yet in `docs/data_provenance.md`: the registry has no way to document a state
helper that builds no canonical table (#258, contract-change). The module's `ARCHIVE_PROVENANCE` holds the row
that will be added. The host's robots.txt answers 403, as do the other `services*.arcgis.com` hosts already used
for St. Paul, Raleigh and Charlotte. Under RFC 9309, a 4xx answer means no rules apply.

## Files and columns for WS-ENGINE

| Input | File / call | Columns | Dated |
|---|---|---|---|
| H1/H2 lots and what they held | `lotline.adapters.states.mn.stpaul_v5.load(store)["h_lots"]` | `district`, `land_use_std`, `parcels`, `eligible`, `median_lot_sqft` | Roll exported 2023-12-26; zoning 2023-11-26 |
| Parcels behind it | `processed/mn/parcels/metc_parcels.parquet` via `stpaul_v5.roll_2023` | `jurisdiction_geoid == "2758000"`, `vintage == 2023`; `land_use_std`, `units`, `lot_sqft`, `year_built`, `lon`, `lat` | Snapshot filter applied |
| Reform rows | `config/reforms/mn.csv` | `MN-2758000-missing_middle-2023` (`unit_cap` 4), `MN-2758000-adu-2023` | Effective 2023-11-26 (one coder each) |
| Baseline permits (record level) | `processed/mn/permits/metc_permits.parquet`, through `holdout.apply` | `jurisdiction_geoid == "2758000"`, `building_type_std` (`DTQ`, `MF5`), `units_new`, `issue_year` | 2009–2023 after the filter |
| Baseline permits (BPS) | `processed/mn/bps_place_year/bps.parquet`, through `holdout.apply` | `geoid == "2758000"`, `units_2`, `units_3_4`, `units_5p` | 1992–2023 after the filter |
| Citywide denominator | `processed/mn/eligible_parcels/eligible.parquet` | `jurisdiction_geoid == "2758000"`, `theme == "missing_middle"` | 2021–2023 from parcels today. M3's rebuild adds D-035's scaled history for 2010–2020 |
| Market | `processed/mn/acs_geo_year/acs.parquet` (`place:2758000`), `market_geo_year/fhfa.parquet` (`county:27123`), `fred.parquet` | rent, value, HPI, rates, costs | **Use years ≤ 2023** |
| Demand | `processed/mn/market_geo_year/demand.parquet` | `geo == "place:2758000"` or `"county:27123"`, `demand_bartik_loo` | **Use years ≤ 2023** |
| Missing-middle effect | Whatever D-024 estimate or prior is on `main` at the freeze | — | State its source in the freeze file |

**Cap every annual input at 2023.** The holdout filter covers outcome tables only. ACS (to 2024) and FHFA (to
2025) run into the window for St. Paul and Ramsey County, and ACS 2024 counts homes built in 2024. This is the
holdout's own annual rule, as for Charlotte (`reports/nc/V5-charlotte-inputs.md`).

## What is missing

- **The St. Paul ADU flag.** `stpaul_permits` has none; Met Council flags 25 St. Paul ADUs from 2016 to 2023.
  Not needed for V5, which is about 2–4 and 5+ unit homes.
- **A second coder for the two 2023 St. Paul rows.** That's in the MN second-coder sheet (M5).
- **Outcomes for scoring after unblinding** (not before): Met Council's St. Paul permits from 2024 on are
  loaded only when the test is unblinded, after the freeze is on `main` (`holdout.check_unblind`). They carry a
  parcel number, so the same H1/H2 join can place them.
