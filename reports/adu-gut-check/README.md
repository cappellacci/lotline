# ADU gut check (2026-11-15)

Page: `results.html` (`scripts/dev/adu_gut_check_page.py`), published at
https://claude.ai/artifact/GTSTVZFmMr7gdwJsV52KXq. Ben asked for a visual breakdown to sanity-check the model:
how well it predicts ADUs within a state, and what it predicts for 2027 onward.

**Inputs:**
- D-091's within-state forecasts (`reports/adu-drift/`);
- D-096's leave-one-state-out test (`reports/adu-types-fixed-rows/`);
- D-097's engine runs (`reports/adu-mx-engine/`);
- two files made here, both through `adu_refit_fixed_rows.py` on PR #440's rule rows with the D-096 config:
  - `place_years.csv`: counted ADUs by place and year, from `adu_gut_check_data.py`;
  - `places.csv`: per-place engine results with m_x drawn, from `adu_gut_check_places.py`.

**Flags it raises (no change made):**
1. **Dallas and Fort Worth give 46% of Texas's added ADUs.** Neither allows ADUs today, so they take the full
   core-city rate. Dallas's Handbook rate is about 2.3 a year per 1,000 lots, as high as Asheville, the
   busiest place counted.
2. **The no-reform mean runs above recent counts in own-count places** (MN ×2.9). The causes are the drift
   term's mean of 1.7 times its median, and the half-count prior on places that counted none.
3. **74% of Oregon's lots carry a coded rule with some conditions uncoded.**
4. **Austin gains under the bill** because its zone list covers 64% of its lots.
