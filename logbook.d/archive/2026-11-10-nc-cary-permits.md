### LB-NNN · 2026-11-10 · Data (NC): Cary ADU permits
- **Question:** can Cary's record-level permits give ADU counts for the NC ADU panel (D-025)? NC's ADU rate
  rested on about 9% of eligible lots.
- **What I did:**
  - Scouted the Town of Cary open-data portal and found one permit source: "Building Permit Applications". It
    is CC0 on the dataset page (the portal terms say ODbL), has 88,219 applications since 2019-01, a Wake PIN,
    housing units and BPS-style permit types.
  - Found that robots.txt disallows `/api/` and downloads, so the source is registered by hand, as the Wake
    roll is. Ben exported and registered it. The first registration was overwritten in place by a second,
    complete export: I re-registered it and superseded the stale entry.
  - Wrote `src/lotline/adapters/states/nc/cary_permits.py` and `config/crosswalks/nc_cary_permit_types.csv`,
    with a Cary ADU rule (`adu_from_text`) that also reads Cary's pre-2025 "utility dwelling unit" (UDU).
  - Wrote 40 synthetic tests, 31 of them hand-worked phrasings.
  - Registered the source in `config/states/nc.yaml` and added the Cary row and section to
    `docs/data_provenance.md` (other rows left alone).
  - Ran `lotline fetch --state NC --source cary_permits`: 24,193 permits.
- **Inputs:** `raw/cary_permits/2026-11-10/permit-applications.csv` (sha256 a85a87e1…); Cary eligible lots
  (`eligible_parcels`, theme adu); Census BPS for the cross-check.
- **Outputs:** `reports/nc/cary-adu-scout.md` (sources, terms, counts, hand check, proposed rule rows, a
  records request draft); `processed/nc/permits/cary_permits.parquet` (outside the repo).
- **Findings:**
  - 43 ADU permits 2019–2026-11-09: about 3 a year to 2023, then 13, 6 and 11. That is 0.8 per 10,000
    eligible lots a year before 2024 and 1.5–3.3 since.
  - 19 of the 29 permits before ACT 32 say "UDU", not "ADU".
  - Detached share 17% before ACT 32 (2025-06-02) and 36% after.
  - Hand check: precision 43/43, and 0 of 30 random non-matches were ADUs. A targeted near-miss read found 2
    misses (now fixed) and puts recall at 73–98%.
  - One-unit homes match BPS within about 1% from 2020 once the Chatham side (jurisdiction CC) is included.
- **Decisions:** proposed for HANDOFF in the PR:
  - Cary ADUs count UDUs.
  - Add a `[predates]` pre-ACT 32 rule row and corrections to the ACT 32 row.
  - Hand-downloaded exports get a new file name each time.
- **AI:** Claude Code scouted, coded, tested and wrote the report. The rule history came from a research
  subagent and was checked against the American Legal LDO Ch. 5 text. All 43 matches, 30 random non-matches
  and 96 targeted near-misses were read by hand. Counts were checked against Census BPS.
- **Open / next:**
  - Ben to fold the proposed rows into `config/reforms/nc.csv`.
  - Match PINs with the Wake-roll ADU counts (`ws/nc-wake-roll-adu`).
  - Optional records request for 2005–2018 permits.
