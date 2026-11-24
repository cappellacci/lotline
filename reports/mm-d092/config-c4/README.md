# C4 to config: what changes in the missing-middle scenario (2026-11-15)

Ben chose D-092's C4 fit for `config/params/mm_hazard.yaml` ("C4 (θ 1.04)", 2026-11-15; analysis plan,
"Decision 2026-11-15: C4 to config"). This compares the Handbook scenario's statewide five-year added 2–4 unit
buildings and net homes, origin 2025, under D-055's values and C4's, with the same places, seed and draws.
No permits are read.

    uv run python scripts/dev/mm_config_compare.py reports/mm-d092/config-c4/compare.json

| State | Net homes, D-055 (P10 / P50 / P90) | Net homes, C4 (P10 / P50 / P90) | Median ratio |
|---|---|---|---|
| MN | 176 / 696 / 2,875 | 255 / 1,758 / 12,353 | 2.5× |
| NC | 301 / 1,204 / 5,286 | 461 / 3,078 / 21,906 | 2.6× |
| OH | 266 / 1,071 / 4,271 | 390 / 2,621 / 18,769 | 2.4× |
| TX | 1,152 / 4,747 / 20,518 | 1,774 / 12,066 / 86,570 | 2.5× |
| OR | 20 / 96 / 442 | 37 / 256 / 1,853 | 2.7× |

- **Medians rise about 2.5×**, as the five-year rates say (0.24 against 0.10 per 1,000 lots a year).
- **The upper ends rise about 4×.** θ's interval is wide (×147), so the ranges are honest but wide.
- **The effect comes late.** With the half-way point at 4 years, year 5 carries 57% of the five-year total
  (24% under D-055). The effect is still growing at year 5, so a five-year total understates the long run.
- **Means sit far above medians** (TX 39,580 against 12,066): a few draws with a large θ carry them. Headlines
  should quote the median and the P10–P90 range.
- Oregon is small here because its coded places already allow most of the Handbook rule (HB 2001): the
  lot-weighted gap left for the scenario is 0.33.

`compare.json` holds the numbers, including buildings and means. Page: `results.html` (`scripts/dev/mm_config_page.py`), https://claude.ai/artifact/1BzpK5S9isRk9eptDaBKDR
