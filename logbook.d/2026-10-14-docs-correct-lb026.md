### LB-NNN · 2026-10-14 · Admin: Correction to LB-026 (Carthage amicus towns unverified)
- **Question:** Is the list of seven towns recorded in LB-026 as amicus filers in *Quality Built Homes v. Town of Carthage* supported by the opinion?
- **What I did:** Corrects LB-026. That entry said "Amicus municipalities were Apex, Concord, Holly Springs, Jacksonville, Kannapolis, Surf City and Winston-Salem". The claim came from a web-search tool's summary on 2026-10-06, not from the opinion. On 2026-10-14 the WS-NC agent read the 2016 opinion (369 N.C. 15) and found no municipal amici listed. Claude Code then searched for any source tying those towns to an amicus filing and found none; the opinion pages (Justia, CourtListener) didn't serve readable text to automated fetches.
- **Inputs:** LB-026; WS-NC day-1 report (PR #83); web searches 2026-10-14.
- **Outputs:** this entry. `config/reforms/nc_carthage_towns.csv` (PR #83) already marks those seven rows low confidence.
- **Findings:** Treat the seven-town list as **unverified**. The UNC EFC rate tables (2006, 2009, Jan 2015) do show capacity fees for those towns, so they remain candidates, but not as amici.
- **Decisions:** none.
- **AI:** Claude Code recorded an unverified search summary as fact in LB-026; this entry corrects it. Lesson applied: legal and factual claims are checked against the primary document before logging.
- **Open / next:** Ben chooses the V6a treatment-list source (WS-NC decision 3).
