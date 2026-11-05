"""Write the data dashboard: one self-contained HTML page with the summary embedded as JSON.

The page loads d3, topojson-client and the us-atlas county boundaries from cdn.jsdelivr.net (all ISC
licensed, listed in docs/disclosures.md); everything else is inline, so the file can be opened locally,
attached, or published as-is.
"""

from __future__ import annotations

import json
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html")
PLACEHOLDER = "/*__LOTLINE_DATA__*/"


def render(summary: dict, template: str | None = None) -> str:
    """The dashboard HTML with `summary` embedded. `</` is escaped so the JSON can't close its script tag."""
    page = template if template is not None else TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in page:
        raise ValueError("template has no data placeholder")
    payload = json.dumps(summary, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return page.replace(PLACEHOLDER, payload)


def write(summary: dict, out_dir: Path) -> Path:
    """Write index.html and summary.json to `out_dir`; returns the HTML path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    html = out_dir / "index.html"
    html.write_text(render(summary), encoding="utf-8")
    return html
