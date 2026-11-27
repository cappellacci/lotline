# Adding a state's local rules with the rule agents

Lotline needs a state's local rules to say what a state reform would add. For each city it needs to know
whether and where duplexes to fourplexes are allowed on single-family lots (missing middle), what it allows for
accessory dwelling units (ADUs), and what it charges in development fees. Collecting these by hand takes weeks.
The rule agents do most of the work and give you a short list of what they could not reach.

You run the agents yourself, with your own Claude account, from your copy of this repository. They propose a
table and you review it before importing it. Nothing changes in the app until you import.

## What you need

- This repository, set up as in the [README](../README.md#setup) (`uv sync`).
- [Claude Code](https://claude.com/claude-code), signed in with your own account. The agents' research runs on
  that account. A state with 50 places costs a few million tokens per category.
- The state set up in Lotline (`config/states/<st>.yaml`, see the README's "Bring your own state" and
  [adding a state](adding_a_state.md)).

Check that everything is in place:

```bash
uv run python -m lotline.rule_agents doctor XX --category mm
```

It prints "Ready." or lists what to fix, for example a missing places table for the state. Use
`--category adu` or `--category fees` for the other two.

## Run one category

Open Claude Code in the repository folder and type one of these commands:

| Command | What it codes | Output table |
|---|---|---|
| `/rules-mm XX` | When 2–4 homes became allowed on single-family lots, where, and whether by right | `reforms` |
| `/rules-adu XX` | ADU rules: allowed or not, attached or detached, size, owner occupancy, parking, dates | `reforms` |
| `/rules-fees XX` | Impact, permit, plan-review, utility and other development fees by year | `fees` |

Each command works on the largest places first. A first run of about 10 places is a good test:

- `/rules-mm XX --limit 10`, or `--only <GEOID> ...` for chosen places;
- `/rules-adu XX --places 10` (10 is the default), or `--geoids <GEOID>,<GEOID>`;
- `/rules-fees XX --max 5` (5 is the default), or `--places <GEOID>,<GEOID>`.

All three take `--budget 250000`, the tokens per place for all agents together. That is the default, and a
well-documented place needs most of it. Each agent gets a fixed share, so the second coder's check is never
squeezed out. For a state Lotline has no places table for yet, pass `--jurisdictions places.csv`, a CSV with
`geoid,name,pop_2020` using Census GEOIDs.

The agents work place by place:

1. They find the documents (the current code, the adopting ordinance, minutes, the fee schedule). They first
   check whether an earlier run already downloaded them.
2. They read short passages and code each value with a word-for-word quote and its page.
3. On the places that matter most, a second agent codes the same place without seeing the first agent's work.
   A third agent settles any disagreement.
4. A script checks every quote against the stored document.

The agents respect every site's robots.txt and stop at bot walls, logins and forms. They never file records
requests or contact anyone.

## What you get

The command prints the path of its run folder, which sits in your data folder. In it you will find:

- **The proposed table**, in Lotline's own CSV format, with places keyed by Census GEOID.
- **A lookup list**, a Markdown file to read and a CSV to answer. It has one task per source the agents could
  not reach, most important first. Each task gives the link, a browser tip for that site, what to look for,
  the fields to fill and when the task counts as done. Tasks marked *optional* can only be answered by a
  public-records request. File one if you want, or mark the task `no_usable_source`.
- **A run report** in plain words. It says what was found and how sure the agents are, which disagreements
  came up and how they were settled, and what the run cost.

## Do the lookups (optional)

The lookups fill the gaps the agents left. Open each task's link in your browser and find the value. Then fill
the task's row in the CSV: `result` (`found`, `not_found` or `no_usable_source`), the listed fields,
`source_url` and a word-for-word `quote`. If you save the document, put the file in the `rule_docs/inbox/`
folder of your data folder and write its name in `saved_file`. Then ask Claude Code to finish those places, or
run the ingest step the command names.

Without a Claude account you can still fill the lookup CSV for any place by hand and import it the same way.

## Review and import

First preview what the proposal would add to or change in the state's rules. This writes nothing:

```bash
uv run python -m lotline.rule_agents import <run folder>/out/<proposed>.csv reforms XX
```

It lists new rows (`+`) and rows that differ from what the state already has (`~`, with the values that
change). For a fee proposal, use `fees` in place of `reforms`. When you are happy with it, write it:

```bash
uv run python -m lotline.rule_agents import <run folder>/out/<proposed>.csv reforms XX --yes
```

Changed rows are replaced only if you add `--replace-changed`. Existing rows are never deleted. The merged
table is checked against Lotline's data model before anything is written. Then rebuild the state's results
with `uv run lotline run --state XX --skip-fetch`.

## Where the documents are

Every document the agents read is kept once in your data folder (`rule_docs/`), with its text by page. You
can search it:

```bash
uv run python -m lotline.rule_agents docs find --geoid <GEOID> --text "accessory dwelling"
uv run python -m lotline.rule_agents docs text <doc id> --page 12
```

`uv run python -m lotline.rule_agents docs catalog --write <file>` writes a list of the documents (ids, links
and dates, no text). Others can use it to fetch and check the same documents.

More detail: [what the agents are for and what they never do](build/rule-agents/PRINCIPLES.md) and
[the design of their shared core](build/rule-agents/CORE.md).
