# Official PDFs review (2026-10-14)

Ben added `rules and resources/` to the repo on 2026-10-14 with three PDFs: **Official Rules**, **Participant
Handbook**, and a new **Official Data List**. Read in full on 2026-10-14 (before the 9:01 a.m. ET Coding Period
start) and checked against `HANDOFF.md` §2–4, which was built from the web pages on 2026-09-29.

## 1. Rules and Handbook: what changed

**No conflicts with HANDOFF.** Dates, eligibility, the 1–5 team size, the seven deliverables, the
Model & Assumptions sections, the four licenses, the seven technical gates, the 30/25/20/15/10 weights and the
prizes all match. The Rules still say work must be created "during the Registration and/or Coding Periods"
(§7a) and still don't mention the Oct 7–14 gap, so the gap-week risk in LB-036/038 stands until the organizers
answer.

**Points HANDOFF didn't capture (new or under-weighted):**

| # | Source | Text (short) | Why it matters for Lotline |
|---|---|---|---|
| N1 | Handbook, *What to Avoid* | "**Parcel-level precision.** State- or region-level breadth and policy relevance will be prioritized over parcel-level granularity. Tools that sacrifice transparency for fine-grained precision will score lower." | Our engine counts parcels. That's fine as an *input*; the tool must not present lot-by-lot predictions as outputs. Report at state / region / place-type level, and say plainly that parcels are a counting device. Check the name "Lotline" doesn't oversell lot-level output in the deck. |
| N2 | Handbook, *Benchmark Scenarios* | For **each** scenario show: (a) change vs. baseline, (b) what drives it (assumptions, data, mechanics), (c) sensitivity to key inputs, (d) what the model can't tell policymakers. | A per-scenario checklist, not just one in the Policy Scenario Comparison. Make it the fixed template for each scenario panel in the tool and each scenario section in the docs. |
| N3 | Rules §8, Transparency | "A clear description of **what data was available in that state, what data was used**, and the model's underlying assumptions." | Needs a per-state "data available vs. used" table (our data tiers). Cheap to generate from the source registry + provenance. |
| N4 | Handbook, *Challenge* | "Precise forecasts are less important than tools that convey the likely **direction, magnitude, uncertainty, and drivers**." | Supports ranges + driver decomposition over a tuned point estimate. Keep the model simple (matches the Oct 5 webinar). |
| N5 | Handbook, *Data* | No sensitive/PII data; for aggregated data, "describe the method and any **re-identification or small-cell risk**." | Minneapolis/St. Paul permit layers carry applicant names and addresses (LB-036): request only needed fields, and add a small-cell note to provenance for any place-level permit counts. |
| N6 | Handbook, *Starter Materials* | Template repo (CI, CodeQL, Dependabot), a **reference example** tool that passes every gate, doc templates (Model & Assumptions, Policy Scenario Comparison, Data Provenance, Disclosures), a repo setup guide and a curated dataset list, all on the Challenge Platform. | Already planned (webinar notes item 6). Week-1 task: compare our repo with the template and the reference example; adopt their doc templates where they differ. Needs Platform access (E5). |
| N7 | Handbook, *Submission Checklist* | Lists the **SBOM** as a deliverable alongside the seven components. | Already gate T7; treat it as a deliverable too. |
| N8 | Handbook, *Scenarios* | State-specific extra scenarios encouraged "**with mentor guidance**". | Take the S7 idea (e.g. MN's existing reforms) to mentor office hours before building it. |

## 2. Official Data List (new)

Portal links for parcels, zoning and land use in **11 states: AZ, CT, OR, HI, PA, TN, UT, VA, WI, RI, NH**.
It is "a starting point"; teams "are not limited to these data sources" (subject to Rules §7(b)(iii)).

**None of our four states (MN, TX, NC, OH) is on it.** Nothing in the Rules requires using a listed state, and
our choice still stands on its merits. But the list hints at which states the organizers think are workable,
and judges will know it.

What the list offers, against our earlier scoring (`lotline-state-reassessment.md`, `lotline-data-availability.md`):

| State | Official list says | Our earlier read | Possible role |
|---|---|---|---|
| **WI** | Statewide parcel map + statewide zoning (SCO) + land cover | 29/45; 12 annual parcel vintages, but PROPCLASS 1 lumps all residential | **Strongest fit as a portability state**: borders MN, statewide parcels *and* zoning, both on the official list |
| **CT** | Statewide CAMA + parcel layer, zoning and land use inside CAMA | 24/45; CC0 parcels and prices; ADU opt-out (115 of 169 towns) is a natural experiment; city permits thin | Calibration/contrast case for ADUs (opt-out design) |
| **UT** | Statewide parcels; Housing Unit Inventory feature service | 28/45; LIR "no constraints"; non-disclosure (no prices); paid permit feed | Housing Unit Inventory may identify ADUs; worth one look |
| **NH** | Statewide parcels with geometry; no zoning | Already a weak-reform contrast in the ADU design | Sparse-data demonstration (Policy Insight bonus) |
| OR | Metro (RLIS) taxlots; partial statewide | Portland is already an ADU calibration site | Confirms Portland calibration path |
| AZ, HI, PA, TN, VA, RI | County-by-county, partial, or request form (TN) | Not prioritized | Low |

Data-list URLs extracted from the PDF are kept in the PDF itself (`rules and resources/`).

## 3. Proposed actions (for Ben to confirm)

1. **Output level (N1):** adopt as a design rule: "parcels in, regions out." No lot-level map of predicted units
   in the tool.
2. **Per-scenario template (N2):** every scenario panel and doc section answers the same four questions.
3. **Data-availability table (N3):** generate per state from the registry; put it in the tool and the
   Model & Assumptions Overview.
4. **Portability state:** consider **WI in place of (or in addition to) OH**. It's on the official list, borders
   MN and has statewide zoning; OH scored 30 vs. WI 29 before the list existed.
5. **Template merge (N6):** once Platform access arrives, diff our repo against the template and reference example.
6. **Keep the PDFs out of git:** done; `rules and resources/` added to `.gitignore` (third-party documents, not our work).
