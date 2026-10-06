# Webinar notes: "Housing data challenge: tools, sources, and portability" (Oct 5, 2026)

Speakers: John Dziurlaj (Turnout, Sr. Solutions Architect), Dr. James Houghton, Grace Gordon, Brian Guayante. Second and last pre-challenge webinar. These are **recommendations**; the Official Rules control.

## What they said

**Data sources.** Starter materials will include a curated provider list (Census, BLS, FHFA, USPS, National Transit Database, USGS/NASA land cover). State/local open data portals for parcels, zoning, assessment; quality varies a lot.

**Data quality / GIS pitfalls.** Check CRS, invalid geometries, layer alignment. Don't mix very different geographic resolutions carelessly. Vintages will differ (parcels vs. ACS vs. zoning): document and justify. Every spatial join is a methodological assumption: report overlaps, gaps, boundary mismatches. Spot-check outputs against other trusted sources; acknowledge uncertainty.

**Licensing.** Software and data licenses are separate; each dataset has its own terms. Avoid non-commercial, proprietary and paid data. Test: will judges and future users be able to get it free, without special agreements, indefinitely? No confidential, restricted-use or PII data; explain prep of any aggregated/de-identified data.

**Portability (stated challenge goal).** Build a **normalization layer**: keep jurisdiction-specific rules and field mappings separate from core logic, translate local values into a common structure, **preserve the original values** for transparency, make onboarding new regions easy. Showing it works in more than one jurisdiction "sends a powerful signal to judges."

**Ben's Q — will end users bring their own data?** Yes: users (legislators, policy analysts) will bring different datasets of unknown shape, so mapping is "very important." Advice: look at how several states publish parcels, base maps, rooftop centroids.

**Tools.** Free GitHub Copilot (VS Code / CLI, open-weight and frontier models) via Microsoft; instructions at coding start. AI use optional and not scored either way, but **AI code generation must be disclosed**.

**Starter package (at kickoff).** GitHub **template repository** with required workflows, submission checklists, documentation templates (data provenance, policy comparison, model & assumptions overview), plus guidance on security, dependency management, code scanning, SBOMs.

**Modeling sophistication (James Houghton).** "The simplest approach that you can use is always best." Must understand and explain every assumption and its implications to non-technical users. Complex economic models are fine only if you can justify and explain them plainly.

**Scoring weights confirmed:** Transparency 30 / Replicability 25 / Usability 20 / Methodology 15 / Policy insight 10. "At least 3 of the 5" scenarios.

**Ben's Q — will technical experts review models/data methods?** Yes, during weekly mentor office hours (schedule TBD). Mentors: a GWU public policy professor, the founder/ED of the Center for Land Economics, a UCLA urban planning & public policy professor, and a VP for policy & partnerships at i3 Innovations.

**Hosting.** Can host anywhere for your own use, but **judges evaluate only the submission** and must be able to **run it on their own computer** from instructions (Docker or setup scripts that build databases/environment). Submit through the challenge platform. Unclear whether GitHub is mandatory per that speaker — but Rules §7 requires a public GitHub repo, so no change.

**Dates restated:** registration closes **Oct 7**, kickoff **Oct 14**.

## Implications for Lotline

1. **Normalization layer = explicit architecture.** Per-state adapters (field maps, land-use/zoning code crosswalks) feeding one canonical parcel schema, with `raw_*` columns kept. The MN/TX/NC/OH four-state plan is exactly the "more than one jurisdiction" signal they described. Consider a documented "bring your own parcels" path (mapping template + validator) for end users.
2. **Local-run is the deliverable.** The interactive tool must launch from one command on a judge's machine (Docker or scripted). Any hosted URL is a convenience only. Revisit D1 wording in HANDOFF.
3. **Data license audit.** Every dataset in `lotline-data-catalog*.csv` needs a perpetual-free-access check; drop or flag any commercial parcel aggregators (e.g., Regrid/ATTOM-type sources). Ties to T11/D7.
4. **GIS QA as tests.** Add automated checks: CRS consistency, geometry validity, spatial-join match/overlap/gap rates, vintage recorded per dataset. These double as Transparency evidence.
5. **Keep the model simple.** Pro forma + calibrated uptake curve is the right level; keep any econometrics in the calibration step and explain it in plain language.
6. **Template repo arrives at kickoff (Oct 14).** Our WS-00 bootstrap should be easy to merge with it — don't over-invest in custom checklists/doc templates that the official template will supersede; plan a merge step in week 1.
7. **Office hours.** Bring the validation plan and calibration/transport design to the first mentor session.
8. **AI disclosure.** Already covered by D8; applies to Claude-generated code regardless of Copilot.
