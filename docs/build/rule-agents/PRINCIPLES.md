# Rule agents in the app: what they are for

*2026-11-17 (Ben): the rule agents are a service inside Lotline. A user who wants to add a state switches
them on, names the state, and gets back the local rules the model needs. They are not an internal workflow for
the people who built Lotline.*

**What the user gets** for one category (missing middle, ADUs or fees) and one state:

1. A **proposed rules table** in the app's data model: `reforms` rows (MM, ADU) or `fees` rows, schema-valid,
   with the existing column headers, places keyed by Census GEOID, every value backed by a quote and a page in
   a stored document.
2. A **lookup list** for a person: one task per source the agents could not read, with the link, what to look
   for, the fields to fill and when it counts as done. Answers (and any file the person saves) go back in, and
   the agents finish those places.
3. A **run report** in plain words: what was found, how sure, where the two coders disagreed, what it cost.
4. The **documents** themselves, in the local document store, with a catalogue anyone can re-check by hash.

**What the agents never do**

- Write into the app's own configuration. The table is a proposal; the user reviews it and imports it.
- Produce model rates or parameters ("use X%"). They code what local law says; the model's own calibration
  turns rules into housing estimates.
- Work around a site that refuses them (robots.txt, bot walls, logins), use another user agent, or fill forms.
  A refusal becomes a lookup task.
- Open outcome data (permit counts, staff reports flagged `may_contain_outcomes`) for a place that the app
  holds back for validation, when the state has such holdouts.
- Show coders the state's existing coded rows: those are used only to compare with afterwards.

**Kept small on purpose:** a state is many places, so every run is budgeted per place (`ledger`), documents are
fetched once and reused across all three categories, and coders read short page-cited passages, never whole
codes (`CORE.md`, "Cutting token use").
