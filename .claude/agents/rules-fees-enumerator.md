---
name: rules-fees-enumerator
description: Fees rule agent, step 1. For one state and a list of places, lists every body that can charge a new home a development fee (city, county, water/sewer utility or authority, regional sewer, park or school district, state surcharge) and which fee components each one covers. Writes places.jsonl in the run folder. Use only from /rules-fees.
tools: Read, Grep, Glob, Bash, Write, WebSearch, WebFetch
model: sonnet
---

# Fees enumerator: places and levying bodies

Read `docs/build/rule-agents/fees/AGENT_RULES.md` first and follow it.

**Input (in your prompt):** state, run folder, the places (name, GEOID, 2020 population) and the state's
existing rows file `config/fees/<st>.csv` (read it: it tells you which bodies earlier coders found).

**Job:** for each place, list the bodies that charge a typical new house, duplex, fourplex or ADU, by
component. A missing body is the most common silent error in our fee table (Eagan and Eden Prairie had only the
regional SAC coded, so their water/sewer looked complete and their totals fell; LESSONS T3).

Check, for every place:
- **Building permits:** does the city issue them, or the county (NC counties often issue for small towns:
  Cabarrus for Concord, New Hanover for Wilmington; Mecklenburg LUESA for Charlotte)? Is there a state
  surcharge (MN Stat. 326B.148; OR 12% surcharge; OH ORC 3781.102)?
- **Water and sewer:** who serves the place? City department, a separate utility or authority (Charlotte
  Water, CFPUA, WSFCU, SAWS, EWEB, GCWW, Cleveland Water), a regional sewer district (Met Council SAC, MSD,
  NEORSD, MWMC)? Some places have two (city water, regional sewer).
- **Impact fees / SDCs:** parks, transportation, schools, fire, stormwater; by the city, the county or a
  special district (Bend Park & Recreation District). State law decides whether school impact fees exist (NC
  and TX cities generally cannot levy them; Oregon has school construction excise taxes, which are taxes, not
  fees: list them as `other` with a note).

Use the state's law and the place's own website; at most 2 web searches per place. Do not read fee amounts.

**Output:** `<run>/places.jsonl`, one object per place:
```json
{"place_geoid": "2701900", "place_name": "Apple Valley", "pop_2020": 56374,
 "bodies": [
   {"levying_body": "City of Apple Valley", "body_kind": "city", "components": ["permit", "water_sewer", "impact", "planning"], "evidence_url": "https://...", "note": ""},
   {"levying_body": "Metropolitan Council (SAC)", "body_kind": "regional", "components": ["water_sewer"], "evidence_url": "https://...", "note": "city collects SAC at permit"},
   {"levying_body": "State of Minnesota (permit surcharge)", "body_kind": "state", "components": ["permit"], "evidence_url": "https://www.revisor.mn.gov/statutes/cite/326B.148", "note": ""}
 ]}
```
Report back in at most 10 lines: places done, bodies per place, any place where you could not tell who serves
water or sewer.
