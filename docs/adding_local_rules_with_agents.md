# Adding a state's local rules with the rule agents

Lotline estimates how state reforms change housing production. To do that for a state it needs the state's
**local rules**: where and when cities allowed duplexes to fourplexes on single-family lots (missing middle),
accessory dwelling units (ADUs), and what they charge in development fees. Collecting these by hand takes weeks.
The rule agents do most of it for you and hand you a short list of what they could not reach.

You run them yourself, with your own Claude account, from your copy of this repository. They propose; you
review and import. Nothing changes in the app until you import.

## What you need

- This repository, set up as in the [README](../README.md#setup) (`uv sync`).
- [Claude Code](https://claude.com/claude-code), signed in with your own account. The agents' research runs on
  that account; a state with 50 places is a few million tokens per category.
- The state set up in the app (`config/states/<st>.yaml`, see the README's "Bring your own state").

Check that everything is in place:

```bash
uv run python -m lotline.rule_agents doctor XX --category mm
```

It says "Ready." or lists what to fix (for example a missing places table for the state).

## Run one category

Open Claude Code in the repository folder and type one of:

| Command | Codes | Output table |
|---|---|---|
| `/rules-mm XX` | when 2–4 homes became allowed on single-family lots, where, by right or not | `reforms` |
| `/rules-adu XX` | ADU rules: allowed, attached/detached, size, owner occupancy, parking, dates | `reforms` |
| `/rules-fees XX` | impact, permit, plan-review, utility and other development fees by year | `fees` |

Useful options: `--limit 10` (largest 10 places first, a good first run), `--only <GEOID> ...`,
`--budget 250000` (tokens per place, all agents together; this is the default, and a well-documented place
needs most of it; each agent gets a fixed share of it, so the second coder's check is never squeezed out), `--jurisdictions places.csv` (a state the app has no places table for: a CSV with
`geoid,name,pop_2020`, Census GEOIDs).

The agents work place by place:

1. find the documents (current code, adopting ordinance, minutes, fee schedule), checking first whether any
   earlier run already downloaded them;
2. read short passages of them and code each value, with a word-for-word quote and the page;
3. on the places that matter most, a second agent codes the same place without seeing the first's work, and
   a third settles any disagreement;
4. check every quote against the stored document by machine.

They respect every site's robots.txt and stop at bot walls, logins and forms. They never file records
requests or contact anyone.

## What you get

In the run folder (the command prints its path, under your data folder):

- **The proposed table** (`out/...csv`), in the app's own format, places keyed by Census GEOID.
- **A lookup list** (`out/human-lookups.md` to read, `.csv` to answer): one task per source the agents could
  not reach, most important first. Each task gives the link, a browser tip for that site, what to look for,
  the exact fields to fill and when it counts as done. Tasks marked *optional* can only be answered by a
  public-records request; file one if you want, or mark it `no_usable_source`.
- **A run report** in plain words: what was found and how sure, disagreements and how they were settled, and
  what the run cost.

## Do the lookups (optional, but it fills the gaps)

Open each task's link in your browser, find the value, and fill the task's row in the CSV: `result` (`found`,
`not_found` or `no_usable_source`), the listed fields, `source_url` and a word-for-word `quote`. If you save
the document, put the file in the `rule_docs/inbox/` folder in your data folder and write its name in
`saved_file`. Then ask Claude Code to finish those places (the command's "When the user answers" step), or
run the ingest step it names.

No Claude account? You can still fill the lookup CSV for any place by hand and import it the same way.

## Review and import

Preview what the proposal would add or change in the app's rules for the state; nothing is written:

```bash
uv run python -m lotline.rule_agents import <run folder>/out/<proposed>.csv reforms XX
```

It lists new rows (`+`) and rows that differ from what the state already has (`~`, with the values that
change). When you are happy, write it:

```bash
uv run python -m lotline.rule_agents import <run folder>/out/<proposed>.csv reforms XX --yes
```

Changed rows are only replaced if you add `--replace-changed`; existing rows are never deleted. The merged
table is checked against the app's data model before anything is written. Then rebuild the state's results
as the README describes.

## Where the documents are

Every document the agents read is kept once in your data folder (`rule_docs/`), with its text by page. You
can search it:

```bash
uv run python -m lotline.rule_agents docs find --geoid <GEOID> --text "accessory dwelling"
uv run python -m lotline.rule_agents docs text <doc id> --page 12
```

`docs catalog --write <file>` writes a list of the documents (ids, links, dates, no text) that others can use
to fetch and check the same documents.

More detail: [what the agents are for and never do](build/rule-agents/PRINCIPLES.md) ·
[design of the shared core](build/rule-agents/CORE.md).
