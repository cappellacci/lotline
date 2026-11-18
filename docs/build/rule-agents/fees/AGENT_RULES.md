# Rules every fees agent follows

Every `rules-fees-*` agent reads this file first. Why each rule exists: `LESSONS.md` (codes in brackets).

## Hard rules (stop conditions)

1. **Store first, retrieval only through the helper.** Look in the shared document store before searching:
   `uv run python -m lotline.rule_agents docs find --geoid <G> --category fees` (and `--url <url>`). Download only with
   `uv run python -m lotline.rule_agents.fees fetch <run> <url> --geoid <G>`: it serves a held copy with no request, checks robots.txt and
   known refusals, makes one spaced request with Lotline's honest user agent (manifest), and prints the
   `doc_id` or a `blocker`. Read stored documents with `uv run python -m lotline.rule_agents outline <doc>`, `uv run python -m lotline.rule_agents excerpts <doc> fees` and
   `uv run python -m lotline.rule_agents docs text <doc> --page N`; use the Read tool only to look at a scanned page. [R2, R5, R6, R7]
2. **A block ends automated access to that host for the run.** If `fetch` prints a `blocker`
   (`robots_disallow`, `http_403_waf`, `login_required`, ...), or a page is a challenge or login page: write a human
   task for every source on that host and move on. **Never** retry with another user agent, `curl`, a browser
   tool, a proxy, a search engine cache or a mirror of the same page. [R1, R2, R3]
3. **No summariser numbers.** If you could only read a page through WebFetch or another summarising tool, you
   may use it to *find* the document, but any amount you copy from it gets `source_kind = "search_summary"`
   (`quote_status = "not_checked"`), and it will become a human check. Prefer downloading the file and reading it yourself. [R4]
4. **Never file requests or contact staff.** If a schedule is only available by public-records request, write a
   task with reason `records_request_only`: it becomes an optional, priority-3 task the user may file
   themselves or mark `no_usable_source`. Agents never file requests, email or call anyone. [R9]
5. **No arithmetic for the table.** Record what the source says (amount, basis, bracket numbers, share, units
   per dwelling, master-meter amount). `fees_tool build` prices it at the prototype home. [P2, P3]
6. **No guessing.** A value you cannot find is left out (it is filled from the state median later), never 0. A
   0 needs a quote that says the fee is waived, exempt or not charged. [T5]
7. **Fees only.** Never run engine, scenario or `scripts/dev/*run*` scripts, never open permit or outcome data,
   never write into `config/` or anywhere in the repo. Work only in the run folder you are given.
8. **Code schedules, never model rates.** An outside study or another state's fee survey is a check, never an
   input. Never recommend "use X%" or any model parameter. The output is a proposed fees table the user reviews
   and imports; agents never write `config/` or model code.
9. **Keys and headers.** Places are keyed by Census GEOID; rows keep the existing `fees` CSV headers
   (`docs/adding_a_state.md`).
10. **Held-back places.** Never open outcome data for places held back for testing.
11. **Budgets per place** are the shared ledger's (`common.budget`). After your work on a place, record your
    fetches and searches: `uv run python -m lotline.rule_agents ledger add <run> <geoid> <agent> --fetches N --searches N`. Before more
    searching, `uv run python -m lotline.rule_agents ledger status <run> <geoid>`; when it says `stop`, write a `budget_spent` task for what is
    left.

## Evidence for every amount

Each item with a number needs `url`, `retrieved_at` (today), `page_or_section` (page number, table name or
section), and `quote`: at most 300 characters copied **word for word** from the document, containing the
number and its row and column labels. Set `doc_id` to the id `fetch` or `docs find` printed: the document's
sha256 in the shared store, cited by every item read from the same bytes. A document a person saved by hand
goes in with `uv run python -m lotline.rule_agents docs add <file> --url <page> --by <initials> --geoid <G>`. `quote_status`: `verbatim` only
after `uv run python -m lotline.rule_agents.fees quotecheck` matched it in the stored text (HTML, text and PDF), `image_read` for a scanned page
you read by eye, `not_checked` otherwise. `source_kind` uses the shared list (`common.evidence.SOURCE_KINDS`):
`fee_schedule` (the levying body's adopted schedule, rate page or utility rules), `ordinance`, `code`,
`state_law`, `archive` (a dated Wayback copy: evidence of that date only), `mirror`, `city_page` (handout,
FAQ), `news`, `search_summary`. Only a primary source with a machine-found quote, confirmed by the blind second
coder, reaches high confidence (`common.evidence.max_confidence`). [R8, S2]

## What a fee item is

One line of a fee schedule, for one building type, written as one JSON object per line. Fields and allowed
values are in `src/lotline/rule_agents/fees/records.py` (`FeeItem`); the pricing rule for each `basis_kind` is
in `DESIGN.md`. Key choices:

- `pays_for` says **what the fee funds**, which decides the component: water, sewer, wastewater, tap, meter
  (→ water_sewer); parks, open_space, transportation, streets, schools, fire, police, library, stormwater,
  general_capacity (→ impact); building_permit, plan_review, trade_permit, inspection, state_surcharge,
  technology (→ permit); zoning, subdivision, site_plan, conditional_use, variance (→ planning). A Texas
  "water impact fee" pays for water. [T1]
- `building_type`: SFD (house), U2 (duplex unit), U3_4 (fourplex unit), ADU, or OTHER (applies to any type,
  priced at the house). Code each type the schedule distinguishes. A fourplex usually falls on the commercial
  (IBC) permit table. [N5]
- Per-meter fees: `basis_kind = per_meter`, `amount` = the smallest residential meter (5/8 or 3/4 inch); if the
  schedule allows one shared meter, put the shared-meter charge for the whole building in
  `master_meter_amount` and say which size you assumed. [N2]
- Per LUE/EDU/SAC unit: `units_per_dwelling` with the quote that gives it (a house is usually 1). [N3]
- Fees that vary by area, basin, tier or plat date: one item per row, all with the same `group_id` and
  `group_kind` (`area` or `plat_date`; `cohort_start` for plat dates). [D4]
- Conditional fees (CUP, rezoning, variance, subdivision-only, front footage where already assessed):
  `basis_kind = conditional` with `applies_when`. Escrows, deposits, minimums, totals: `excluded`. [T4, P6]
- Dates: `effective_date` (the date it took effect) and `adopted_date` separately; `schedule_label` as printed
  ("FY2027"); `fiscal_year_start` if only the fiscal year is known. Step schedules: one item per step. If an
  older schedule from one body is still current next to a newer row of the same component, set
  `in_force_through` to the newest year. [D1-D3]
- Fee waivers and exemptions for new housing (e.g. an SDC exemption) are reforms: list them under
  `reform_candidates` in your report, and still code the full schedule. [T6]

## Human tasks

When you stop on a source, append one JSON object per (place, levying body, component) to your tasks file
with the fields in `HANDOFF_FORMAT.md`: `state, place_name, place_geoid, levying_body, body_kind, component,
pays_for, building_types, reason, start_url, other_urls, look_for, priority, est_minutes` (and optionally
`fields_to_fill`, `done_when`). `look_for` names the exact table, column and row a person should copy, in
plain words. `priority` 1 = water/sewer or permit for a large place (moves totals most), 2 = impact fees,
3 = everything else.

## Report back

Your final message is at most 15 lines: files written, counts (items, tasks), hosts blocked, anything
surprising, and judgment calls you made (each in one plain sentence). Do not paste the items.
