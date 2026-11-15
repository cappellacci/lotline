# D-094: a place-effect variance per place type

Built by `scripts/dev/adu_type_spread.py` (offline, St. Paul excluded, checked rule rows, 64 places, 491
place-years, 16 core cities). Page: `results.html` (`scripts/dev/adu_type_spread_page.py`), published at
https://claude.ai/artifact/1QRuqXpv5b1rrYFDPBszR9.

Forms: A + P (base), A + P + S (core cities' own variance, α_core = α_sub e^λ), A + S (reported only).

| File | What |
|---|---|
| `fits.csv`, `spreads.csv` | every fit (full, each state left out, each new place left out, 2016-20); α_sub, α_core, λ and its 90% interval |
| `heldout_log_scores.csv` | tier-1 held-out log score per place (D-049) |
| `tiers.csv` | D-075's data tiers |
| `test_a.csv`, `test_b.csv`, `test_d_*.csv` | tests A, B, D |
| `heldout_places.csv`, `heldout_coverage.csv`, `state_width_parts.csv` | the range coverage check's measures for each form |
| `summary.json`, `run-log.txt` | decision and summary; run log |

**Result:** λ̂ −0.89 (−1.59 to −0.16): α_core 1.01, α_sub 2.45. Held-out log-score gain over A + P −0.1 (2 SE 2.9);
same claim tier (1), useful states and tests A–B; test D −0.9 (2 SE 3.7). D-088's rule keeps A + P. Without
Minnesota, λ̂ is +0.51 (−0.63 to +1.60). State-total P90 ÷ P10 would narrow (NC ×24 → ×11, TX ×25 → ×13, OR ×27 →
×18, MN ×9.2 → ×9.4), but the place-level score shows no gain in accuracy.

The first run's width split left α_core on when place luck was switched off; `adu_range_coverage.decompose`
was fixed and the whole run repeated (same seeds; fits, scores and decision identical).
