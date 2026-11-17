# Human lookup tasks: format

When the swarm cannot read a source, it writes a task for a person instead of guessing. Tasks are built by
`src/lotline/rule_agents/fees/handoff.py` and land in the run folder as:

- `human_tasks.md`: a checklist to read, highest priority first;
- `human_tasks.csv`: the same tasks with empty `answer_*` columns to fill in.

## One task

One task covers one **place × levying body × component** (e.g. "Fort Worth · Fort Worth Water · water_sewer").

| Column | What it holds |
|---|---|
| `task_id` | `FEES-<ST>-<geoid>-<nn>`, stable within a run |
| `state`, `place_name`, `place_geoid` | where |
| `levying_body`, `body_kind` | who charges the fee (city, county, utility, regional, special_district, school_district, state) |
| `component`, `pays_for` | `water_sewer` / `impact` / `permit` / `planning` / `other`, and what the fee funds |
| `building_types` | which of SFD, U2, U3_4, ADU to answer for |
| `reason` | why a person: one of the codes below |
| `start_url`, `other_urls` | where to open |
| `look_for` | in plain words: the document, table, row and column to copy |
| `fields_to_fill` | the exact `answer_*` columns this task needs |
| `done_when` | the acceptance rule (below, unless the task says more) |
| `priority` | 1 = water/sewer or permit for a large place; 2 = impact fees; 3 = the rest |
| `est_minutes` | the swarm's guess |
| `status` | `open` → `done` (answered) or `no_usable_source` (looked, nothing official online) |

**Reasons** (`handoff.REASONS`): `robots_disallow`, `http_403_waf`, `login_required`, `scanned_pdf`,
`buried_document`, `not_found`, `summariser_only`, `coders_disagree`, `verify_low`, `budget_exhausted`.
There is deliberately **no** reason for emailing staff, phoning or filing a records request: Ben does not do
those, so a source available only that way is closed as no usable source and listed in the run report.

## Answer columns

| Column | Fill with |
|---|---|
| `answer_fee_type` | the fee's name as the schedule prints it |
| `answer_building_type` | SFD, U2, U3_4, ADU or OTHER (one row per type if they differ: copy the task row) |
| `answer_basis_kind` | `per_unit`, `per_building`, `per_meter`, `per_lue`, `per_sqft`, `pct_of_value`, `conditional` (for a valuation table, enter the fee at the valuation `look_for` gives, as `per_building`) |
| `answer_amount` | the number as printed, no `$` or commas; `0` only if the page says the fee is not charged |
| `answer_units_per_dwelling` | for `per_lue`: units a dwelling counts as (a house is usually 1) |
| `answer_effective_date` | the date the schedule took effect, `YYYY-MM-DD` |
| `answer_url`, `answer_page_or_section` | the page you read and where on it |
| `answer_quote` | the line with the number, copied word for word, at most 300 characters |
| `answered_by`, `answered_date` | your initials, today |
| `answer_notes` | anything odd (other columns, conditions, which meter size) |

**Done when:** the amount is copied from the adopted schedule (not a guide or news), the quote is word for word,
and the effective date is when it took effect (not when it was adopted). Then set `status = done`.

## Back into the swarm

```bash
uv run python -m lotline.rule_agents.fees ingest-tasks "$RUN/human_tasks.csv" --out "$RUN/items.human.jsonl"
cat "$RUN/items.final.jsonl" "$RUN/items.human.jsonl" > "$RUN/items.with_human.jsonl"
uv run python -m lotline.rule_agents.fees build "$RUN/items.with_human.jsonl" --out "$RUN/with_human"
```

Answered tasks become items with `coder = human:<initials>` and go through the same pricing, grouping and
schema checks as agent items.

## Example (`human_tasks.md`)

> ## FEES-MN-2717288-01 · Eagan · City of Eagan · water_sewer (priority 1, ~10 min)
> - **Open:** https://www.cityofeagan.com/… (fee schedule PDF)
> - **Why a person:** the site refuses automated readers (HTTP 403 or a bot check); it usually opens in a browser.
> - **Look for:** In the 2026 fee schedule, the "Utility connection charges" table: the water and sewer
>   connection (trunk/availability) charge per residential unit, and whether a duplex unit pays the same.
> - **Building types:** SFD U2 U3_4 ADU
> - **Fill:** answer_amount, answer_basis_kind, answer_effective_date, answer_page_or_section, answer_quote
> - **Done when:** …
