### LB-NNN · 2026-11-10 · Data (NC): Winston-Salem ADU permits scout
- **Question:** can Winston-Salem's (3775000) record-level ADU permits go into Lotline, to widen NC's ADU evidence
  beyond Raleigh, Durham, Greensboro and the Mecklenburg towns?
- **What I did:**
  - Scouted city, county (MapForsyth) and ArcGIS Online sources. The only open bulk layer is MapForsyth's
    `Planning_Inspection/Development_And_Permits/FeatureServer/0` ("Permits Issued", since 2013). Its host
    `maps.co.forsyth.nc.us` refused or timed out from this network and the fetch proxy on 2026-11-10, so the
    fields, terms and counts could not be read. BuildIT is a one-record lookup portal (not used). The city's
    ArcGIS Online orgs have no permit layer. `www.cityofws.org` serves a Cloudflare check (not bypassed).
  - Read the ADU rule history from primary documents on the Legistar Web API: kinship-limited ADUs to 2017;
    UDO-267 (2017-09-05) required Special Use District rezoning (2 ADUs in 4.4 years); UDO-CC15, Ordinance
    #21-0667, by right from 2022-02-07 (UDO §5.3.4B/C, no added parking, no owner occupancy). The city's own
    count: 10 ADUs permitted 2022-02-07 to 2023-02 (3 attached, 7 detached; matter 23-0026).
- **Inputs:** Legistar matters 2046, 15232, 13075, 18107, 19071 (attachments read in a scratch folder, not kept);
  `eligible.parquet` (Winston-Salem ADU lots 2022: 62,798).
- **Outputs:** `reports/nc/winston-salem-adu-scout.md`, with proposed `nc.csv` rows (not applied) and a
  drafted records request.
- **Findings:**
  - Verdict: no usable source today; no adapter.
  - About 1.5 ADUs per 10,000 eligible lots in the first year of by-right ADUs, against about 0.08 a year
    before.
  - The existing row `NC-3775000-adu-2022` is right on its date, but its second-coder note gives a wrong 2021
    date.
- **Decisions:** proposed in the PR: add `NC-3775000-adu-2017` (special use rezoning, superseded) so the 2022
  event reads as special-use to by-right; correct the 2022 row's coding note.
- **AI:** Claude Code did the scouting, document reading and report. Checked by reading the ordinance text and
  Legistar action histories directly; network failures were re-tried by two routes.
- **Open / next:** Ben checks the layer from another network, or sends the records request or the short ADU-list
  request in the report's §4.
