### LB-NNN · 2026-11-25 · Review · App: smaller usability fixes from the usability judge (US-04, US-05, US-06; US-08 measured)

- **Question:** Can the app's smaller usability findings (two "gap" figures on the need card, funnel bars and
  yearly charts without a stated scale, internal terms on the page) be fixed without touching engine numbers,
  and what makes the published page slow to load?
- **Outputs:** `src/lotline/app/template.html` (need-card bar label, funnel scale note, y-axis titles, slider
  readout, chart legends, AMI spelled out, "Source and range" with a plain note first and the config keys in a
  "Technical detail" fold); `src/lotline/app/knobs.yaml` (`source_note` per factor and scenario);
  `tests/app/test_build.py`, `tests/app/test_ami_strip.py`. Findings from
  `reports/judging/2026-11-25-1656-30cfd38b/judge-usability.md` (gitignored run).
- **Decision:** Ben, 2026-11-25: "Can you spin up a PR to fix these? Smaller usability items". Not changed, by
  Ben's earlier choices: the fee section's default (real local fees), the single-number headline, the slider
  range and slider note (open PR #539).
- **What Claude did and how it was checked:** Claude Code confirmed each finding in the current template first.
  US-04: the sentence's gap is need minus homes built anyway; the bar's figure also takes off the reforms'
  midpoints. The bar now reads "Still short after the reforms" and the details say how the two differ. US-05:
  the funnel bars were already on one log scale, but the scale was stated only in a folded note; each "How we
  get these numbers" list now says so on the page, with the width a tenfold change takes, and the ADU card uses
  the shared bar helper. The two yearly charts have y-axis titles. US-06: the slider readout says "likely … to …"
  and "Set lower/higher: …, about 3 times the engine's estimate" in place of "P10–P90", "P100" and "×27.64";
  chart legends say "likely range"; each slider's source opens with a plain sentence and keeps the config keys
  and raw citations one fold deeper. A new test requires a plain note for every cited scenario. US-08 was
  measured only (sizes in the PR). Checked: `pytest tests/app` (76 passed); the app built from the ZZ fixture,
  both inline scripts and the state file pass `node --check`; a headless Chrome render of the built page shows
  the new labels; ruff check and format pass.
