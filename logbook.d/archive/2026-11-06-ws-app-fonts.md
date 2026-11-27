## LB-xxx · 2026-11-06 · WS-APP · Brand fonts committed and inlined (no Google Fonts)

**Question answered:** Ben (2026-11-06): bundle the brand fonts in the repo and serve them locally instead of from Google Fonts.

**Outputs**
- `docs/build/identity/fonts/`: nine unmodified `.woff2` files, 488 KB in all:
  - Public Sans 400/500/600/700, from v2.001 (github.com/uswds/public-sans)
  - IBM Plex Mono 400/500, from @ibm/plex-mono@2.5.0 (github.com/IBM/plex)
  - Source Serif 4 400, 400 italic and 600, from 4.005R (github.com/adobe-fonts/source-serif)
- Each family's SIL OFL 1.1 licence file sits beside its fonts, and `fonts.css` holds the `@font-face` rules.
- `src/lotline/app/build.py`: `font_faces()` inlines the faces the app uses (Public Sans, Plex Mono) as data URIs, so the page stays one file with no font host. The embedded data dashboard gets the same faces.
- `src/lotline/app/template.html`: the Google Fonts links are removed.
- `docs/disclosures.md`: the app-page entry now names the committed fonts, their sources and the OFL.
- `tests/app/test_build.py`:
  - the page has no external script or stylesheet, and carries six inlined faces
  - Source Serif is left out of the page
  - every font file is listed in `fonts.css`, and each family has an OFL licence file

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) downloaded the three official release archives with Ben's OK (about 23 MB, kept in the scratchpad) and committed only the files above. Checked by `tests/app` (28 passed) and `compliance_check.py`, and in a browser: all six faces loaded from the page itself, no request went to a font host, and the dashboard panel used Public Sans.
