# WS-OR · Oregon: transfer test first, then pool

**Start:** 2026-11-04. **Inputs ready for the freeze by Nov 17**; frozen prediction on `main` by ~Nov 20; unblind,
score and pool by Dec 1.
**Owns:** `src/lotline/adapters/states/or/` (see Gotchas on the package name), `config/states/or.yaml` (except
`holdouts`, which only Ben changes), `config/reforms/or.csv`, `config/fees/or.csv`, `config/crosswalks/or_*.csv`,
`tests/states/or/`, `reports/or/`, `docs/build/or-readiness.md`.
**Role:** the **high-uptake transfer state** (decision: Ben, 2026-11-04, `docs/build/or-assessment.md` option C,
lean scope). First, predict Oregon blind from the MN/NC/OH/TX calibration (validation plan V9). Then add Oregon to
the calibration, so the ADU and missing-middle fits get many more reform events and the high-rent end of the
market range.

## Read first
`docs/build/or-assessment.md`, validation plan V9, the `state=OR` rows of `docs/research/lotline-data-catalog.csv`,
`docs/build/oh-readiness.md` (the shape of the readiness report to produce), `config/states/or.yaml`.

## The blind rule (non-negotiable)
`V9-OR-TRANSFER` hides **every Oregon outcome from 2018-01-01**: BPS rows for all Oregon GEOIDs, permits, and
any parcel roll taken from 2018 on. Never pass `--unblind V9-OR-TRANSFER`, and never read Oregon permit files,
BPS West Region files or post-2018 rolls outside the pipeline (no "quick look" in a notebook or shell), until
`results/frozen/V9-OR-TRANSFER.json` is on `main` and Ben has asked for the unblinding. Steps 1–5 build inputs
only. Outcome adapters (step 7) may be written and tested on synthetic fixtures before the freeze, but not run
against real data.

## Sources (lean scope)

| Key | Source | Access | Feeds | Before freeze? | Notes |
|---|---|---|---|---|---|
| `bps` (national) | Census BPS, West Region place files | existing adapter | `bps_place_year` | runs, filtered | Rows from 2018 on are hidden by the holdout. A place that first reported after 2017 has no visible BPS row; list them in the readiness report |
| `rlis_parcels` | Oregon Metro RLIS Taxlots (Public), Multnomah, Washington, Clackamas | ArcGIS FeatureServer + quarterly ZIP archives | `parcels` (tier 1: land use, year built, values, sale price) | **pre-2018 archives only** | The current roll is hidden (snapshot rule). Find the oldest archive the DRC serves; if none before 2018, Metro uses the ACS fallback for the freeze and RLIS joins after unblinding. License: RLIS end-user agreement (ODbL-style); check share-alike before merging, like Cleveland |
| `or_zoning` | DLCD/ODOT statewide zoning (generalized classes) | ArcGIS FeatureServer | eligibility (optional) | yes | Classes are dated 2023 (post-HB 2001); use only to mark residential land, not allowed units |
| `or_ugb` | DLCD urban growth boundaries | ArcGIS / download | eligibility | yes | SB 1051 and HB 2001 apply inside UGBs. If eligibility needs a UGB rule in `build/eligible.py`, open a `contract-change` issue for WS-CORE rather than editing it |
| `portland_permits` | Portland residential permits (MapServer 89: `IS_ADU`, `NEW_UNITS`, `NEWTYPE`), demolitions (126), milestones (1263) | ArcGIS MapServer | `permits` | **no: outcome** | Did not answer on 2026-11-04 (timeouts); worked in October. No license stated |
| `bend_permits` | Bend permitting table (`HB2001ADU`, `HB2306Path`, units, finaled date, taxlot) | ArcGIS FeatureServer | `permits` | **no: outcome** | Custom license text; read it |

Not in lean scope: DLCD HB 4006 city production data (by request only; not requested), Eugene and Salem
permits, county parcel layers outside Metro, ORMAP statewide geometry.

## Tasks
- [ ] **1. Config and geography.** Fill `sources` in `config/states/or.yaml` as adapters land; `lotline fetch
      --state OR` for national sources; `jurisdictions` (no townships; county remainders). Confirm the holdout
      filter hides Oregon BPS rows from 2018 (`tests/core/test_holdout.py` has the statewide cases).
- [ ] **2. Parcels.** `rlis_parcels` adapter + contract tests on a synthetic fixture; crosswalk
      `config/crosswalks/or_rlis_land_use.csv`; pre-2018 vintage only for the freeze. Everyone outside Metro on
      the ACS fallback (D-017).
- [ ] **3. Rules: `config/reforms/or.csv`.** State-law rows read from the statutes, not memory: SB 1051 (2017;
      ADUs, cities over 2,500 and counties over 15,000, inside UGBs), HB 2001 (2019; duplexes in cities
      10,000–25,000 outside Metro; all middle types in cities over 25,000 and Metro cities, by the compliance
      dates), SB 458 (2021; land divisions), HB 2138 (2025). Coverage depends on city size and the UGB, which one
      statewide row can't express: generate one row per covered place from 2020 population (a script under
      `scripts/dev/`, rows cite the statute) unless WS-CORE adds a coverage rule. Local rows: Portland (ADU
      history and the 2010 SDC waiver, RIP 2021, RIP2 2022), Bend, and Metro cities that adopted early or late
      (DLCD compliance tracking). Second coder on every dated row; `[predates]` and `[earliest-known]` tags as in
      NC.
- [ ] **4. Fees: `config/fees/or.csv`.** SDC schedules for Portland, Bend, Eugene, Salem (water, sewer,
      transportation, parks), per unit for a single-family house, an ADU and a fourplex unit. League of Oregon
      Cities 2025 survey and the OHCS 2022 study as checks. Report how close Oregon comes to the Handbook's $50k.
- [ ] **5. Housing need (office hours A2).** Oregon Housing Needs Analysis (state-published need by city):
      source and vintage to WS-ENGINE for `config/params/` (engine owns the file).
- [ ] **6. Readiness report and handover for the freeze.** `docs/build/or-readiness.md` in the OH format:
      coverage of each input, what is blind, what the freeze will predict. WS-ENGINE runs the prediction with
      Oregon **not** in `REFORM_STATES` (`model/scenarios/adu.py`) and commits the frozen file.
- [ ] **7. Outcome adapters** `portland_permits`, `bend_permits` with synthetic-fixture tests (ADU flag, units,
      demolitions, finals; no names or addresses requested: add `PERSONAL` field checks like Columbus). Run on
      real data only after the unblinding.
- [ ] **8. After unblinding.** Score V9 in `reports/or/V9.md` before any refit; then add OR to `REFORM_STATES`
      and the D-019 / D-024 / D-025 panels (engine), and switch Metro to the current RLIS roll.
- [ ] Every dataset gets a `docs/data_provenance.md` row and an Oregon section in `docs/data_availability.md`.

## Gotchas
- **`or` is a Python keyword.** `importlib.import_module("lotline.adapters.states.or")` works (the registry loads
  packages this way), but `from lotline.adapters.states.or import x` is a syntax error. Tests must import adapter
  modules with `importlib`, or WS-CORE maps the state to a different package name (e.g. `oregon`). Settle this
  first.
- Portland is the hazard's reference place (`config/params/hazard.yaml`). That stays fixed. But once Oregon is
  pooled, Portland's published counts (E044, E046) are no longer independent checks: note it in D-037.
- Oregon's statewide mandates leave few untreated Oregon places. Don't promise an Oregon difference-in-differences.
- Amy's caveat: if the frozen prediction misses, report it with the rent and value context. Don't tune before
  the write-up.
- Logbook: write fragments to `logbook.d/`, never edit `LOGBOOK.md` or `HANDOFF.md`.
