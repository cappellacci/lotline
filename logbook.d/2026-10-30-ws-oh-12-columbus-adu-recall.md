### LB-NNN · 2026-10-30 · WS-OH · Count more of Columbus's ADUs (recall over precision)

**Question.** The Franklin County Auditor's descriptions found 14 of the 57 ADU permits Columbus reports for 2019
to Sep 2025. On 2026-10-28 Ben chose to bias towards counting more ADUs and approved both routes: a Council
variance source and looser flag rules.

**Outputs.**
- `src/lotline/adapters/states/oh/columbus_variances.py`: new source `columbus_variances`, with tests in
  `tests/states/oh/test_columbus_variances.py`.
- `src/lotline/adapters/states/oh/franklin_permits.py`: recall rules, with tests in
  `tests/states/oh/test_franklin_permits.py`.
- `config/states/oh.yaml`, `docs/data_availability.md`, `docs/disclosures.md` (Legistar API) and
  `docs/data_provenance.md` (Ohio sections only).
- Rebuilt the processed Ohio `permits` tables.

**What changed.**
- **Council variances.** Before Ord. 2526-2025, a Columbus ADU needed a Council use variance. The adapter fetches
  all 1,742 variance ordinances: 2 pages from the public Legistar Web API, through the IO layer. Named rules on
  each title's purpose clause keep 183 ADU approvals, 121 of them for 2019 to Sep 2025. The city reports 110
  approved variances for that period.
- **Recall rules.**
  - A new carriage house no longer needs living-space words, unless it is described as a garage.
  - A new in-law suite counts.
  - Trade permits doing ADU work mark the project permit they cite.
  - New guards drop repair and trade permit numbers and multi-unit "carriage houses".
- **Effect.** Franklin flags rose from 35 to 72. Columbus permits flagged for 2019 to Sep 2025 rose from 14 to 34.
  `observed_adu_counts` keeps the larger source each year, so Columbus now counts 15–22 a year from 2019, up from
  0–5. These are approvals: an upper bound on built ADUs, about 2× the city's permit pace.

**How Claude worked and checked.**
- Claude (Claude Code) grouped the rejected candidates by the rule that dropped them, then loosened three rules.
- Claude read all 39 newly flagged descriptions, plus 2 that dropped out, by hand. Three of the drops were the
  same ADU under another permit; the fourth was a genuine loss, which a narrower guard fixed.
- The five clear false positives found became guards: two repair permits, a trade permit and two multi-unit
  buildings.
- Claude read samples of the variance titles for each rule and each exclusion, and checked the 2019 to Sep 2025
  count against the city's 110.
- Tests cover each rule and exclusion on synthetic titles and descriptions.
