### LB-NNN · 2026-11-13 · `Rules` · WS-ADU-RULES: ADU rule details for the 65 fit places, 2016-2025
- **Question:** for each place on the WS-ADU-RULES worklist (64 fit places plus St. Paul, rules only), what were the
  ADU rules in each year 2016-2025, and when did they change? The fields are by right, owner occupancy, extra
  parking, detached allowed, ADUs per lot, maximum size and minimum lot size.
- **What I did:**
  - First-coder agents, one per group of places, read the existing rows and earlier research. They opened the
    code, adopted ordinances and Wayback copies, and wrote one record per rule version with verbatim quotes of at
    most 25 words and their section numbers.
  - A fresh second-coder agent re-opened every cited source and rated each (version, field) value. A value
    resting on a mirror, draft, guide or news report was rated at most "partly".
  - One browser agent re-checked values whose official page refuses scripts against the official code. It
    stopped on any challenge.
  - Scripts assembled the filled worklist, the proposed `reforms` rows and the README section from the agents'
    records.
- **Inputs:** the WS-ADU-RULES brief and worklist (#413), `config/reforms/*.csv` (read only), earlier research
  records in `docs/research/ordinances/`, and official code and ordinance pages and PDFs. PDFs were saved to
  `~/lotline-data/manual/adu-rules-2026-11/<state>/`, outside the repo, each logged in `downloads.jsonl`.
- **Outputs:**
  - `docs/research/ordinances/adu-fit-rules-todo-2026-11-12.csv`: the worklist, filled.
  - `docs/research/ordinances/adu-fit-rules-proposed-2026-11.csv`: proposed rows, one per rule version.
  - `docs/research/ordinances/README.md`, section "WS-ADU-RULES": method, coverage, decisions, incidents, the
    rule changes and the conflicts with existing rows.
- **Findings:**
  - Most places changed their ADU rules at least once in the window. Each dated change is a candidate
    before-and-after event, listed in the README.
  - Many existing rows have blank or slightly wrong fields. The conflicts list proposes fills and corrections; none
    is applied.
- **Decisions:**
  - Six coding conventions were agreed with the coordinating session on 2026-11-12, provisionally; they are listed
    in the README.
  - Ben ruled on seven judgment calls on 2026-11-13: Raleigh, Bloomington, Cincinnati, Bend, Orono, New Brighton
    and Durham. They are applied and marked "decided by Ben, 2026-11-13".
  - Wayzata before 2022 and the conflicts with existing rows are still open for Ben.
  - No HANDOFF decision is proposed yet. Accepting rows into `config/reforms` needs a dated script and Ben's sign-off.
- **AI:**
  - Claude Opus 5.5 ran the whole workstream: first coders, second coders, the browser check and the assembly
    scripts. It was checked by the independent second-coder pass and the browser check against official code.
  - Coding stayed blind to outcomes: no permit counts, refit results or `reports/` were opened.
  - Three process incidents are recorded plainly in the README:
    - Medford: a refused fetch was retried with curl; that copy was deleted.
    - Scott County: one refused retry; nothing was saved.
    - A St. Paul staff report on ADUs was downloaded for a Stillwater comparison. It was not opened by the St. Paul
      coders and is flagged for possible deletion.
- **Open / next:**
  - Ben reviews the proposed rows, the open judgment call and the conflicts.
  - A dated script in `scripts/dev/` would apply the accepted rows.
  - Places marked `manual_needed` need a person to open the official page.
  - A model version with rule-detail effects needs its own pre-registration.
