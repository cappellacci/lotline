# Manual fee lookups (fee plan Phase 1 gaps, 2026-11-09)

What the fee model is missing after D-065/D-066, in priority order. Everything listed here is currently **filled
from a prior or borrowed from the house rows**. The per-place detail is in
`docs/research/fee-levels-vs-handbook.md`; its "What was filled" and "(from SFD)" markers are the source of this
list.

**How to record.** One row per fee component and building type in `config/fees/<st>.csv`, with the columns in
`config/fees/README.md`: `amount_usd` as the schedule states it, `amount_per_unit_usd` for one dwelling unit
(say the conversion in `notes`), `dollar_year`, `source` (the schedule's URL), `source_section` and a short
verbatim `source_quote`. Use `building_type_std` `U2` for a duplex, `U3_4` for a triplex or fourplex, `ADU` for an
accessory unit. If a fee varies by area or plat date, put the typical value in `amount_per_unit_usd` and the range in
`amount_per_unit_low_usd` / `amount_per_unit_high_usd`. If an older schedule is still in force next to a newer
row of the same component, set `in_force_through`. Can't find it: leave it out (it stays filled), never enter 0.
An explicit 0 means "the place charges nothing" (as Dallas's utility impact fee).

---

## Priority 1: how duplexes and fourplexes pay for water and sewer

Amy's point (office hours, A5): per-unit connection fees are often why missing middle doesn't pencil. Phase 2's
SFD / duplex / fourplex table needs the real rule. In the places below, the model currently **assumes the house fee
is charged again for every unit**. For each place, answer one question and code the amount:

> For a new **duplex** and a new **fourplex** (one building, one lot), is the water and sewer
> connection / capacity / impact fee charged **per dwelling unit**, **per meter** (and how many meters), or **by meter
> size**? What is the total for the building?

| State | Places |
|---|---|
| NC | Raleigh, Wilson, Apex, Brunswick County, Forsyth County, Greensboro (duplex only), Johnston County, Winston-Salem, New Hanover County, Wilmington, Durham |
| TX | Austin, San Antonio, Fort Worth, Houston, Dallas |
| OR | Portland, Bend, Salem (duplex only; their fourplex rows are coded) |
| MN | St. Cloud, St. Paul (water/sewer for plexes) |

Also for MN metro cities: the Met Council SAC charges by SAC units (a house is 1; check the units for a duplex
unit and a fourplex unit in the current SAC Procedure Manual) and code them as `U2` / `U3_4` rows where a city's
SAC is coded.

## Priority 2: building permit fees (23 places borrow Minnesota's)

No building permit or plan review fee is coded for these places, so each gets the pooled median of about $4,000,
almost all from Minnesota valuation tables. One row per place is enough: the **building permit plus plan review for
a new 2,150 sq ft house** (the model's prototype; valuation about $355,000). If the schedule is valuation-based,
record the table in `notes` and the amount at that valuation, as the Minnesota rows do.

- **NC (16):** Raleigh, Wilson, Apex, Asheville, Brunswick County, Buncombe County, Cabarrus County, Forsyth County,
  Fuquay-Varina, Greensboro, Johnston County, Winston-Salem, New Hanover County, Wilmington, Durham, Concord. Several
  are already in `~/lotline-data/manual/nc_fees/` (Apex, Asheville, Brunswick, Cabarrus): the PDFs likely have the
  building fee table too.
- **TX (4):** San Antonio, Fort Worth, Houston, Dallas.
- **OR (3):** Portland, Bend, Salem.
- **MN (1):** Brooklyn Park.

## Priority 3: incomplete or old entries

| Place | What's missing | Why it matters |
|---|---|---|
| **Eugene, OR** | Stormwater SDC (general vs LID capacity) and whether new ADUs get the 100% transportation reduction (Admin Order 58-25-05-F; city Transportation SDC page). Then fill `amount_per_unit_usd` on the Eugene rows | Eugene now takes the pooled median ($6,981), below its known lower bound of $14,442 (D-066) |
| **Minneapolis, MN** | City SAC/WAC and the Met Council SAC ($2,485 per unit in 2026). Permit rows are from 2019: a current permit table | Minneapolis's water/sewer is filled from the state median |
| **Met Council SAC** for Apple Valley, Bloomington, Burnsville, St. Louis Park | Confirm the city collects the regional SAC and add the row ($2,485 per unit, 2026). Coon Rapids, Lakeville, Maple Grove, Brooklyn Park and St. Paul already have it | Every sewered metro city pays it; four coded cities leave it out |
| **Corpus Christi, TX** | Its lot fees have no per-unit amount (conditional). Water and wastewater tap or connection fees for a new house, and the building permit | Corpus Christi has no usable rows and takes the Texas median |
| **Bloomington, MN** | Permit table is from 2018 (still posted). Is there a newer one? | Old dollars |
| **Durham, NC** | Water/sewer capacity fees are FY2024. Is there an FY2026 or FY2027 schedule? | Old dollars |

## Priority 4: coverage (places with no fee rows at all)

These places take their state's median. Coding the biggest ones moves the state totals most. Rows are by 2020
population.

- **Ohio: nothing is coded** (no `config/fees/oh.csv`). Every Ohio place takes the pooled median of the other
  states. Start with Columbus, Cleveland, Cincinnati, Toledo, Akron, Dayton. Akron, Canton and Parma already have
  fee instructions in `docs/build/manual-ordinance-lookups.md`. Cleveland's water and NEORSD's sewer charges cover
  many Cuyahoga County suburbs, so one regional row each goes a long way.
- **NC:** Charlotte (a holdout for outcomes; its fees are inputs and can be coded), Fayetteville, Cary, High Point,
  Greenville, Gastonia.
- **TX:** El Paso, Arlington, Plano, Lubbock, Irving, Laredo.
- **MN:** Plymouth, Woodbury, Blaine, Eagan, Eden Prairie, Minnetonka.

For each: water and sewer connection or capacity fee for a new house (and the duplex/fourplex rule from priority 1),
impact fees if any, and the building permit.

## Not needed

- Impact, park, planning and other fees that a place doesn't list: the model counts them as zero, which is right
  when the place charges none. Code them only where you know the place charges one.
- Fees for 5+ unit buildings: not used by any scenario.
