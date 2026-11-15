# D-095: the engine's ADU reform ratio, checked on in-window rule changes

Built by `scripts/dev/adu_reform_ratio.py` (offline, St. Paul excluded, checked rule rows; code in
`lotline.model.adu_reform_check`, tests in `tests/model/test_adu_reform_check.py`). Page: `results.html`
(`scripts/dev/adu_reform_ratio_page.py`), published at https://claude.ai/artifact/JggHUyaPLYuJxwMFBvMk6j.

| File | What |
|---|---|
| `events.csv` | D-079's events on the checked rows (10 in MN, NC, TX) |
| `events_scored.csv` | per event: counts and exposure before and after, the engine's and the refitted ratio, the observed ratio, M's P10/P50/P90, log scores of P, M and M′ (with and without drift) |
| `b_profile.csv` | summed log score of ratio^b on the grid −2 to 3 |
| `summary.json`, `run-log.txt`, `inputs.json` | gains, b intervals, reading; run log; config values used |

**Result:** reading "not shown either way". M over P +4.2 (2 SE 7.9); b 1.3 (0.55–2.05), which includes 1 and
excludes 0. Refitted ratio M′ +2.4 (2 SE 6.7), b 1.3 (0.55–2.2). Raleigh 2021 (2 → 201 ADUs; observed ×29,
engine ×9.4) carries most of it. Five Minnesota suburbs built none before or after. Without drift (sensitivity)
the rule reads "contradicted", with a paired SE of 172 dominated by Raleigh and Minneapolis.
