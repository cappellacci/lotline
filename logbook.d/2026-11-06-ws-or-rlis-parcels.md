### LB-NNN · 2026-11-06 · Build: Oregon Metro parcels from RLIS tax lots
- **Question:** Can Metro's RLIS tax lots replace the ACS fallback (D-017) as the eligible-lot denominator for
  the Portland-area jurisdictions, and how much does Portland's count change?
- **What I did:**
  - Checked RLIS terms: the RLIS Open Database EULA (Feb 2023) needs attribution only, no account; it is
    compatible with CC BY 4.0 and ODC-By and has no share-alike clause. RLIS Discovery publishes only the
    current tax-lot roll (no dated archives), so there is one vintage (2026-11-05, the layer's last data edit).
  - Wrote `src/lotline/adapters/states/or/rlis_parcels.py`. It reads the `Taxlots (Public)` FeatureServer
    through the IO layer, by county and FID range, taking label points and only the listed fields (no site
    addresses). Land use comes from the DOR property class via `config/crosswalks/or_rlis_land_use.csv`;
    the jurisdiction comes from Metro's `JURIS_CITY`, else the county remainder.
  - Tests: `tests/states/or/test_rlis_parcels.py` (29, synthetic rows worked by hand: crosswalk, ids,
    jurisdiction, lot size, sales, eligible counts, tiers).
  - Rebuilt OR `parcels` → `jurisdictions` → `eligible_parcels` and the local data dashboard.
- **Inputs:** RLIS Taxlots (Public), layer 3 (648,079 features); OR jurisdictions; ACS B25024 (fallback).
- **Outputs:** the adapter, crosswalk and tests above; `config/states/or.yaml` source entry; provenance row in
  `docs/data_provenance.md`; issue #304.
- **Findings:**
  - 646,554 tax lots across the three counties. All 27 Metro jurisdictions in the table now count from
    parcels (24 tier 1, 3 tier 2, up from tier 3). The three counties shade at tier 1 on the dashboard.
  - Portland ADU-eligible lots: 163,638 (2026 roll) vs 160,807 from the ACS fallback (2024), +1.8%.
    Missing middle: 171,025 (adds 7,387 vacant residential lots). Quality stays `low` because RLIS has no
    unit counts or zoning.
  - Across Metro: +3.3% for ADU (468,769 vs 453,705). Newer suburbs run higher (Hillsboro 1.26×, Happy
    Valley 1.29×), because DOR class 101 includes townhouses on their own lots. Rural county remainders run
    lower (Clackamas 0.84×), because rural homes on farm or forest class land aren't counted as houses.
  - A first run missed Oregon City and King City: the name match stripped "city" from RLIS's bare names
    too. Fixed, with a test, before the final rebuild.
- **Decisions:** none recorded. Proposed for HANDOFF: Metro jurisdictions use the RLIS roll as their
  denominator (D-017 fallback elsewhere in Oregon); a refit of the ADU calibration on it needs its own
  analysis-plan entry and Ben's approval.
- **AI:** Claude Code wrote the adapter, crosswalk and tests, ran the download and rebuild, and compared
  counts with the ACS fallback. Checked by hand-worked fixture tests, ruff, the full suite,
  `compliance_check.py` (0 FAIL), and per-jurisdiction comparison with ACS.
- **Open / next:** a zoning join (Metro's regional zoning layer) to set `sf_only_zoned`; a townhouse split of
  class 101 (no field for it in RLIS); refit ADU on RLIS lots (Ben's call; `config/params/*` untouched).
