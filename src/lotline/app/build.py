"""Build the Lotline app: one static, self-contained page from per-state results bundles (HANDOFF 2026-11-06).

Every `reports/results/<st>/bundle.json` (written by `lotline results --state XX`, schema `results_*`,
#310) is read back and validated with `model.results.read_bundle`, then embedded as JSON in
`template.html` next to this file. The page draws everything in the browser with plain SVG; it needs no
server and can be opened from disk. The build is state-agnostic: whatever bundles exist appear in the picker,
grouped by `meta.state_role`, with no state names in this code or the template.

The identity (docs/build/identity/tokens.css and the wordmark SVGs) is inlined at build time, so the page
and the style guide share one source.

    uv run python scripts/build_app.py                     # every bundle under reports/results/
    uv run python scripts/build_app.py --bundle tests/fixtures/results/zz/bundle.json
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import re
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = Path(__file__).with_name("template.html")
IDENTITY = REPO / "docs" / "build" / "identity"
RESULTS_DIR = REPO / "reports" / "results"
OUT_DIR = REPO / "reports" / "app"
PLACEHOLDERS = (
    "/*__LOTLINE_TOKENS__*/",
    "/*__LOTLINE_DATA__*/",
    "<!--__WORDMARK_LIGHT__-->",
    "<!--__WORDMARK_DARK__-->",
)

# Picker order and plain-language group labels for `results_meta.state_role` (#310 Q4).
ROLES = {
    "benchmark": "Benchmark state",
    "development": "Development states",
    "transfer": "Unseen-state transfer runs",
    "national_only": "National data only",
}


def find_bundles(results_dir: Path = RESULTS_DIR) -> list[Path]:
    """Every `<results_dir>/<st>/bundle.json`, sorted by path."""
    return sorted(Path(results_dir).glob("*/bundle.json"))


def load_bundle(path: Path) -> dict:
    """A bundle as the page embeds it: the JSON document, after `read_bundle` has validated every table."""
    from lotline.model.results import read_bundle

    path = Path(path)
    read_bundle(path)  # raises on any schema error, so a bad bundle never reaches the page
    return json.loads(path.read_text(encoding="utf-8"))


def order_states(bundles: Iterable[dict]) -> list[dict]:
    """Bundles in picker order: by role (ROLES order), then state code. One bundle per state."""
    bundles = list(bundles)
    states = [b["meta"]["state"] for b in bundles]
    dupes = sorted({s for s in states if states.count(s) > 1})
    if dupes:
        raise ValueError(f"more than one bundle for {dupes}")
    rank = {r: i for i, r in enumerate(ROLES)}
    return sorted(bundles, key=lambda b: (rank.get(b["meta"]["state_role"], len(rank)), b["meta"]["state"]))


def payload(bundles: Iterable[dict], generated: str | None = None) -> dict:
    """What the page embeds: the ordered bundles, role labels and the build time."""
    states = order_states(bundles)
    if not states:
        raise ValueError("no results bundles to show: run `lotline results --state XX` first")
    stamp = generated or dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"generated": stamp, "roles": ROLES, "states": states}


def _svg(name: str) -> str:
    """A wordmark as an `<img>` with a data URI, without its embedded provenance metadata.

    An `<img>` rather than inline SVG: each wordmark file carries a `<style>` with the same class names, and
    inline styles are page-global, so the dark copy would recolour the light one.
    """
    text = (IDENTITY / "wordmark" / name).read_text(encoding="utf-8")
    text = re.sub(r"<metadata>.*?</metadata>", "", text, flags=re.S).strip()
    uri = "data:image/svg+xml;base64," + base64.b64encode(text.encode()).decode()
    return f'<img src="{uri}" alt="Lotline" height="32">'


def render(data: dict, template: str | None = None) -> str:
    """The page HTML with `data` embedded. `</` is escaped so the JSON can't close its script tag."""
    page = template if template is not None else TEMPLATE.read_text(encoding="utf-8")
    missing = [p for p in PLACEHOLDERS if p not in page]
    if missing:
        raise ValueError(f"template is missing {missing}")
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    return (
        page.replace("/*__LOTLINE_TOKENS__*/", (IDENTITY / "tokens.css").read_text(encoding="utf-8"))
        .replace("<!--__WORDMARK_LIGHT__-->", _svg("lotline-wordmark-light.svg"))
        .replace("<!--__WORDMARK_DARK__-->", _svg("lotline-wordmark-dark.svg"))
        .replace("/*__LOTLINE_DATA__*/", blob)
    )


def build_app(
    bundles: Iterable[Path] | None = None,
    results_dir: Path = RESULTS_DIR,
    out_dir: Path = OUT_DIR,
    generated: str | None = None,
) -> Path:
    """Validate the bundles (default: every one under `results_dir`), write `<out_dir>/index.html`."""
    paths = list(bundles) if bundles is not None else find_bundles(results_dir)
    html = render(payload((load_bundle(p) for p in paths), generated))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    page = out / "index.html"
    page.write_text(html, encoding="utf-8")
    return page
