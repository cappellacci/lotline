## LB-xxx · 2026-11-06 · WS-APP · App: one page per section, a shorter masthead, an intro line

**Question answered:** Should the three sections be one long scroll or separate pages? Ben's call (2026-11-06): separate pages, with a shorter masthead line and a plain-language intro under the tabs.

**Outputs**
- `src/lotline/app/template.html`:
  - Each tab shows one section at a time (`#results`, `#data`, `#trust`, with `?state=XX`), so a link opens on that page and state. Switching state keeps the current page.
  - The masthead line is now "Housing Reform Model".
  - The intro paragraph under the tabs follows Ben's draft. "A highly accurate estimate" became "estimates ... over five years, as a range", to keep to the style guide's rule of a range, never a single number.
  - The "Section N" eyebrows are gone, because the tabs carry the numbers.
- `tests/app/test_build.py`: the intro and masthead line are on the page; only Results is visible at load; each tab links to its page.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) made the change at Ben's request. Checked by `tests/app` (26 passed), `compliance_check.py`, and in a browser at desktop and 375 px width: tab clicks, the state switch keeping the page, a deep link opening on `#data?state=ZZ`, and the tornado drawing when its page opens.

Follow-up the same day (Ben): tab 3 and its heading were renamed from "How well does it hold up?" to "The model".

Second follow-up (Ben approved, 2026-11-06): the page loads the brand fonts Public Sans and IBM Plex Mono (SIL OFL 1.1) from Google Fonts, with the tokens' system fallbacks when offline. Source Serif 4 is left out because the style guide uses it only in the written reports. Disclosed in `docs/disclosures.md`. Checked in a browser: all six weights load (`document.fonts`). The test now allows only the Google Fonts stylesheet as an external resource.

Third follow-up (Ben, 2026-11-06): the state picker moved from the masthead to the right end of the menu bar, followed by the compact Lotline mark (`docs/build/identity/wordmark/lotline-mark-{light,dark}.svg`, 24 px, linking back to Results). The style guide allows the mark on a different line from the wordmark. Below 640 px the picker and mark sit on their own row above the tabs. Checked in a browser: desktop, 375 px, light and dark (the mark swaps), and the state switch from its new place.

Fourth follow-up (Ben, 2026-11-06): the menu-bar mark is the Mondrian mark Ben chose in the identity session. That session's last edits were committed in their own PR (#320: mark, favicon cut, missing middle green / fee reduction vermilion) and merged into the app branches, so the page picks them up from `docs/build/identity/` with no app code change. The page now also uses `lotline-mark-favicon.svg` as its tab icon. Checked in a browser: new mark, swapped scenario colours, favicon present.
