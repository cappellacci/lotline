# Ohio data readiness (thread 11, step 3)

*WS-OH, 2026-11-01; replaces the draft of 2026-10-26. Plan: `docs/build/oh-data-plan.md` (#217). No model runs:
these are counts of the processed input tables in `~/lotline-data/processed/oh`, rebuilt on 2026-11-01 from
`main` at 6a70f9d (after #226, #239, #243 and #246), plus `config/reforms/oh.csv`. #252 (interpolating between
real rolls) is still open; §1 notes what it changes.*

**Bottom line.** Ohio runs end to end. All 952 jurisdictions have:
- an eligible-lot count and a data tier;
- BPS permits and market inputs;
- a rule, either coded or drawn under D-022.

Since the last draft:
- **95.5% of the population counted** (see §4) has an eligible-lot count from real parcels.
- **27 jurisdictions** (Franklin and Montgomery counties) have yearly real rolls.
- **The ADU panel has 15 Ohio places, up from 4**: 7 with an in-window rule change and 8 "no ADUs" controls.
- **The missing-middle panel has 2 treated places, up from 1**, among 156 places of 10,000+, plus 2 places already
  treated before 2010.

## 1. Coverage of each model input (952 jurisdictions: 567 places, 297 townships, 88 county remainders)

| Input | Real | Fallback | Open |
|---|---|---|---|
| **Eligible lots (denominator)** | **885 jurisdictions from parcels (95.5% of population)**, with D-035's scaled history. 27 of them have yearly real rolls (10 each): **14 in Franklin** (Franklin Auditor year-end files, 2016–2025) and **13 in Montgomery**, Dayton included (Treasurer CAMA, 2011–2026) | **67 on the ACS fallback** (D-017), 4.5% of population. Among the 40 largest places only **Hamilton** (10.4% unknown land use) and **Middletown** (12.1%, down from 15.2% with Warren land use) | Years between two real rolls are still scaled ACS. **#252** interpolates them instead: in Ohio only the Montgomery places change (for example, Dayton's 2020 count drops from 45,399 to 43,719) |
| Window | 894 jurisdictions have 2010–2024; 52 have more (yearly-roll places run to 2025–2026) | — | 6 have 1–13 years (no ACS anchor within 3 years; unchanged since the last draft) |
| Denominator quality | — | `low` everywhere | Zoning is unknown, so all land counts as single-family-only (the same as NC). Zoning layers would raise quality (not planned) |
| **Data tier** | **Tier 1: 85 places (32.7%)**, up from 72: Columbus, Dayton, Parma, Kettering, Cuyahoga Falls, Lakewood, Euclid, the Franklin suburbs and others. **Tier 2: 800 (62.8%)** | **Tier 3: 67 (4.5%)** | Tier 1 needs land use and year built on at least 80% of built parcels |
| Permits, all places | Census BPS for every permit-issuing place and township | — | — |
| **Permits with an ADU flag** | **Cincinnati**: 26 ADUs, 2017–2026. **Columbus**: 53 from permits and 183 Council variance approvals, the larger count kept each year. **Franklin suburbs**: 11 ADUs in 9 places. **Montgomery**: 7 ADUs in 4 places; 12 places count as covered | — | Montgomery and Franklin are undercounts: they find permits that name an ADU. There's no ADU data for Cleveland, Toledo, Akron or any other city |
| **ADU rules** | **29 places** with dated rows (37% of population), 38 rows. 22 rows were second-coded (Codex), 16 are single-coder | The rest draw a rule type (D-022) | Unresolved: Westerville, Reynoldsburg, Lorain, Canal Winchester, Akron, Parma and Canton. Cleveland Heights and Findlay are pending |
| **Missing-middle rules** | **4 places**: Cincinnati (2024) and Euclid (2024), in window; **Dayton** (2006) and **Grove City** (1979), before 2010 | The rest draw a rule type (D-022) | 3 of the 4 rows are single-coder |
| Fees | none (`config/fees/oh.csv` doesn't exist) | The Handbook prior of $50,000 (D-034) everywhere | S8 not started |
| Market (rent, value, rates, costs) | ACS, FHFA, FRED, statewide | — | — |
| Demand index | processed | — | — |
| Holdouts | none in Ohio | — | — |

## 2. What Ohio adds to the estimation panels

To count, a place needs a permit source that covers it and flags ADUs, a dated ADU rule (a "no ADUs" row counts)
and eligible lots. A place covered only by an ADU-only source (Franklin, Montgomery) has to be listed by the
panel's caller, because a year with no ADUs has no permit row.

| Panel | Ohio places | Who | What would add more |
|---|---|---|---|
| **ADU (D-025)** | **15** (4 in the last draft) | **7 rule changes in the window:** Cincinnati (2023-10-02), Columbus (2025-12-24), Bexley (2025-10-09), Dublin (2019), Gahanna (2024-05-01), Whitehall (2023 special use, then 2025 by right), Dayton (2023, conditional). **8 "no ADUs" controls:** Grandview Heights, Groveport, Hilliard, New Albany, Obetz, Upper Arlington, Worthington, Kettering | Rule rows for the covered places with no rule yet: Westerville, Reynoldsburg, Grove City (ADU), Canal Winchester, and Montgomery's Centerville, Miamisburg, Trotwood, Vandalia and others. Each would join the panel at once |
| **Missing middle (D-024)** | **156 places** of 10,000+ with BPS 2–4 unit permits; **2 treated in the window** (Cincinnati, Euclid) | Dayton and Grove City were already treated before 2010, so they don't count as in-window events | More dated missing-middle rows; none are queued |

## 3. Remaining gaps and what closes each

| Gap | Effect | What closes it | Owner |
|---|---|---|---|
| **Second coding of the 15 in-window ADU and missing-middle rows** | The rows that set the timing of treatment rest on one coder | A second coder (Ben merged #226 without this check) | Ben |
| Codex disclosure | `docs/disclosures.md` doesn't name the agent used for second coding | One disclosure line | Ben / WS-OH |
| #252 (interpolation) | Montgomery's gap years stay scaled ACS | Review and merge; it also moves Wake County (NC), 2020–2022 | Ben, then the NC thread |
| Hamilton, Middletown on the ACS fallback | ACS estimate for 2 of the 40 largest places | Keep the 10% gate (decided); Butler and Warren have no further land-use source | Settled |
| Unresolved ADU rules (7 places) | Fewer ADU-panel places; more D-022 draws | The tracker's `next_step` for each place | Ben's research agent |
| ADU undercounts (Franklin, Montgomery) | Counts are lower bounds | A measurement note in D-025 | WS-ENGINE |
| Fees | Handbook prior everywhere | S8: Columbus, Cincinnati, Cleveland water and sewer fees | WS-OH (not started) |
| Cleveland permits | Cleveland not in the ADU panel | S7: the `cle_permits` adapter. The ODbL license question is still open | Ben, then WS-OH |
| Zoning | Denominator quality stays `low` | Columbus base zoning (CC0), Montgomery `MC_ZONING.gdb` | Not planned |
| Statewide second roll (OGRIP 2022) | — | Dropped (2026-11-01) | — |

## 4. How these numbers were made

The rebuild ran `lotline fetch --state OH --source oh_parcels`, then `jurisdictions`, then `eligible`, with
`OH_PARCELS_VINTAGE=2026-10-19`, so the statewide snapshot came from the cache. The counts come from a short
read-only script over those tables and `config/reforms/oh.csv`.

- The ADU-panel count applies D-025's inclusion rule without running the estimator.
- "In window" means effective 2010-01-02 to 2025-12-31.
- Population shares use `pop_2020` in `jurisdictions`. That column totals 7.84 million: 6.82 million in places
  and 1.03 million in townships. Ohio's population is about 11.8 million, so township populations look partial.
  The shares are comparable with the last draft, but **the township population field should be checked** before
  it's used for weighting.
