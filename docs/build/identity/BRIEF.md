# Lotline visual identity brief

2026-11-06 · Ben Cappellacci · living copy: https://claude.ai/artifact/21FhKZdVH2axzz3nQFThtA · design system built from it: https://claude.ai/artifact/XW95915mHhn65atvgS5Vye

## The ask

We need a complete visual identity for **Lotline**: a wordmark, a colour palette, typography, and a visual style that works across a browser-based policy tool (app and data dashboard), a 30-slide PDF deck, a 5-minute demo video, and two written reports. Everything ships by mid-December 2026, so the identity must be decided and in our hands by early December. Lotline is an entry in a national housing-policy competition judged largely on transparency and usability, so the identity has one job: make a technical, uncertainty-heavy model feel clear, credible and calm to a non-technical policymaker.

## About the project

Lotline is an open-source simulator that estimates how three state housing reforms would change housing production over five years, compared with a no-change baseline. It is our entry in the Housing Data and Technology Innovation Challenge, run by Arnold Ventures and The Turnout (rules: https://housingchallenge.turnout.rocks/rules.html, handbook: https://housingchallenge.turnout.rocks/handbook.html). Teams build a working tool that projects the effect of benchmark zoning and fee reforms for one U.S. state; prizes are $20K, $12K and $6K, and the top five present remotely to judges in January 2027.

The judges score on five criteria: transparency and explainability 30% (and the tie-breaker), replicability 25%, usability 20%, methodological soundness 15%, policy insight 10%. Two of the top three criteria are about whether a non-technical reader can see what the model does and trust it.

What makes Lotline different: it is built to be portable. It learns from places that already passed these reforms (Portland, California, Seattle, Minneapolis and others) and transfers what it learned to states that have not, using whatever data a state has, however thin. Minnesota is the worked example; Texas, North Carolina, Ohio and probably Wisconsin are additional runs on the same code. Every result is a range, never a single number, and every place is flagged for how far it sits from the evidence the model was trained on.

| Milestone | Date |
| --- | --- |
| Interface build starts | Nov 18, 2026 |
| Identity needed in hand | early Dec 2026 |
| Target first full submission | early Dec 2026 |
| Hard submission deadline | Dec 16, 2026, 11:59 p.m. ET |
| Finalist demo (top 5) | Jan 20, 2027 |

## What Lotline does

A user picks a state, picks one or more reforms, and sees how many net new homes the state would likely gain over five years beyond the baseline, shown as a low-to-high range with the middle marked. Plain-language sliders let them test the assumptions and watch the range move. The three reforms: **ADUs** (one accessory dwelling unit of at least 600 sq ft on every single-family lot, no extra parking); **Missing middle** (2 to 6 homes, up to three stories, on lots currently limited to one house); **Fee reduction** (development fees halved from a $50,000-per-unit baseline).

The tool is a single static web page in three sections: Results (legislators, staff, press), The data (judges, analysts), How well does it hold up? (judges, skeptical staff). Around it sit a 30-slide PDF deck, a 5-minute demo video, a 25-page Model & Assumptions Overview, a 4-page Policy Scenario Comparison, the public GitHub repository and a "bring your own state" guide. The Lotline name comes from the lot (parcel) as the model's basic unit; the shift from one lot to a whole state is the visual story.

## Audience and tone

Seen first by housing-policy judges, then legislators and staff, advocates, journalists and planners. Most are not technical and are wary of models that promise more precision than they can deliver. It should feel like a civic instrument: calm, exact, open about uncertainty, quietly confident. Three words: **clear, honest, grounded.**

Avoid: real-estate and proptech clichés (house icons, keys, rooftops, skylines, stock photos); startup gradients, neon, glassy UI; anything that reads as advocacy or partisanship (no political reds and blues as primaries); false precision (a single figure with no range is off-brand); dark "housing crisis" imagery. The identity should make honesty about uncertainty look like rigour, not a hedge.

## Deliverables

1. Wordmark, with an optional compact mark; works at 16 px, in one colour, light and dark. SVG, PNG 1x/2x/4x.
2. Colour palette: primary, neutrals for light and dark mode, one accent, a data-visualisation set; contrast ratios documented. Hex and CSS custom properties.
3. Typography: heading and body faces, open-licensed (Google Fonts / SIL OFL), tabular figures for numbers; type scale for web and print.
4. Visual style guide, 6 to 10 pages.
5. App and dashboard theme: styled examples of the three sections, light and dark; a CSS variables file.
6. Slide templates (16:9): title, divider, content, chart, two-column, callout, closing.
7. Video assets: title card, lower-third, section card, end card, corner bug (1080p).
8. Document templates: letterhead and report template for the two written deliverables.
9. GitHub and social: README header (1280 × 320), social preview (1280 × 640), favicon set.

Everything is published under an open licence in a public repository, so fonts, icons and imagery must be OFL, MIT, CC BY or similar, with sources noted.

## Design direction and constraints

**The name.** A lot line is the legal boundary of a parcel on a plat map. The wordmark should play on the plat-map line, the lot as a unit, or the line that connects many small things into one. Typographic or near-typographic; no house pictogram.

**Concepts worth exploring:** the drawn boundary of a lot or a subtle plat-map grid as texture; one lot becoming a row, a block, a state; the range bar itself (a horizontal line with a marked midpoint) as a recurring motif; the quiet precision of survey and cadastral documents.

**Colour.** The prototype dashboards use a mid blue (#3987e5 / #2a78d6) on warm off-white neutrals, an orange accent and a green, with light and dark modes. A starting point, not a constraint; keep the warm paper-like neutral ground. Avoid saturated red and blue as co-primaries.

**Data visualisation is half the brand.** The palette must include: a range style (low-to-high bar with a marked middle, used everywhere a number appears); fixed scenario colours for Baseline, ADUs, Missing middle, Fee reduction and Combined, colour-blind-safe and greyscale-safe; a 3-to-5-step sequential ramp for the US map plus a grey for "no data yet"; a three-state confidence flag (inside, edge, outside) that pairs colour with a shape or label and is not green/amber/red; a funnel style for "legally eligible, pencils out, built".

**Accessibility and technical.** WCAG AA in both themes. The app is static HTML with SVG and d3, so the theme must be deliverable as CSS custom properties and plain hex, with no effects that print badly. Fonts must be committable. Must look right at 1366 px and on a projector.

## References and existing assets

Two working prototype dashboards; the public repository at https://github.com/cappellacci/lotline; the competition's own site. Tone references: U.S. Census data explorer, ONS and GOV.UK design system, Our World in Data, The Pudding, FT Visual Journalism, Urban Institute, Brookings; county plat books and cadastral maps for the survey idea. If anything here conflicts with the competition rules, the rules win.

## Process, timeline and handoff

| Round | What we see | By |
| --- | --- | --- |
| 1. Directions | 2 or 3 wordmark directions, each with a palette swatch and type pairing on one mock results card | Nov 17 |
| 2. Refinement | One direction worked up: wordmark, palette with contrast checks, data-viz set, one slide and one app section in light and dark | Nov 26 |
| 3. Templates and guide | All deliverables plus the style guide | Dec 4 |

Feedback from Ben within 48 hours of each round. The CSS variables, fonts and SVG wordmark are needed earliest (app build starts Nov 18). Handoff: one shared folder with sources, exported assets, a `fonts/` folder with licence files, `tokens.css`, and the style guide PDF; plain file names; licence noted on every third-party element.

## Status (2026-11-06)

Round 1 was produced with Claude Design the same day: see the design system link at the top. This folder holds the hand-off files from it: `tokens.json`, `tokens.css`, `STYLE_GUIDE.md` and `wordmark/`. The scenario, confidence and map-tier palettes were validated colour-blind-safe with the dataviz palette validator in both themes.
