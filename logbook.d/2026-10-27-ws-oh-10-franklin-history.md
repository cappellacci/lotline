### LB-NNN · 2026-10-27 · WS-OH · Does D-035's scaled eligible-lot history match real parcel rolls? (S6a)

**Question.** Ohio's eligible-lot history outside the roll year is ACS scaled to one roll (D-035). The Franklin
County Auditor keeps yearly parcel files: how close is the scaled history to real counts?

**Outputs.** `scripts/dev/oh_franklin_history.py`; `tests/states/oh/test_franklin_history.py`;
`docs/build/oh-franklin-history-check.md`. Ten year-end `Parcel.xlsx` files (2016–2025, about 450 MB) were downloaded
through the IO layer into `LOTLINE_DATA_DIR` (Ben approved the S6a downloads on 2026-10-23 and again on 2026-10-27).
No processed table changed.

**Findings.** The roll year matches the archive (median −0.6%). For 12 single-county places, 2016–2024, 68% of
place-years are within 5% and 96% within 10%; summed, within 3% each year. Trends follow ACS, not parcels:
built-out suburbs show 3–10% growth that the parcels don't (Worthington, Gahanna), and Columbus is about 4–5% low
before 2020. Level offsets are absorbed by place fixed effects; the drift slightly understates reform effects.
Proposed (not done): real yearly Franklin counts in place of the scaled years.

**How Claude worked and checked.** Claude (Claude Code) wrote the script and tests, ran it, and found that
multi-county places (Dublin, Westerville, Reynoldsburg) looked 25–37% off even in the roll year. The gap matched
1 / (their Franklin share of houses), so Claude limited the direct comparison to places ≥ 99% inside the county
and gave the others an approximate gap. The tests check, on synthetic rows worked by hand, the ID matching, the
district fallback at the 95% edge, the gap arithmetic and the county share.
