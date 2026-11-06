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
AGGREGATE_JS = Path(__file__).with_name("aggregate.js")
KNOBS = Path(__file__).with_name("knobs.yaml")
IDENTITY = REPO / "docs" / "build" / "identity"
RESULTS_DIR = REPO / "reports" / "results"
DATA_SUMMARY = REPO / "reports" / "data_dashboard" / "summary.json"
OUT_DIR = REPO / "reports" / "app"
PLACEHOLDERS = (
    "/*__LOTLINE_TOKENS__*/",
    "/*__LOTLINE_DATA__*/",
    "<!--__WORDMARK_LIGHT__-->",
    "<!--__WORDMARK_DARK__-->",
    "<!--__MARK_LIGHT__-->",
    "<!--__MARK_DARK__-->",
    "__FAVICON__",
)

# Picker order and plain-language group labels for `results_meta.state_role` (#310 Q4).
ROLES = {
    "benchmark": "Benchmark state",
    "development": "Development states",
    "transfer": "Unseen-state transfer runs",
    "national_only": "National data only",
}


# The Handbook's names for the reforms (STYLE_GUIDE "Voice"), in the fixed colour-slot order. Stacked pairs
# share the neutral `ink-muted`; `combined` (all three) is full ink.
SCENARIOS = {
    "adu": ("ADUs", "--scenario-adu"),
    "missing_middle": ("Missing middle", "--scenario-missing-middle"),
    "fees": ("Fee reduction", "--scenario-fees"),
    "adu+missing_middle": ("ADUs + missing middle", "--ink-muted"),
    "adu+fees": ("ADUs + fee reduction", "--ink-muted"),
    "missing_middle+fees": ("Missing middle + fee reduction", "--ink-muted"),
    "combined": ("Combined (all three)", "--scenario-combined"),
}


def knobs(path: Path = KNOBS) -> list[dict]:
    """The sliders: labels from knobs.yaml, every number and citation resolved from config/params/.

    Each `params` entry `file:key` becomes {key, value, low, high, unit, source}; an unknown key raises, so a
    renamed parameter can't silently drop a citation from the page.
    """
    import yaml

    from lotline.config import load_params

    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    out = []
    for column, k in spec.items():
        params = {}
        for scenario, refs in (k.get("params") or {}).items():
            rows = []
            for ref in refs:
                file, key = ref.split(":")
                p = load_params(file)[key]
                rows.append({"file": file, "key": key, **p.model_dump()})
            params[scenario] = rows
        out.append({"column": column, **{f: k[f] for f in k if f != "params"}, "params": params})
    return out


def sources_table(state: str, summary_state: dict | None) -> list[dict]:
    """Section 2's "available vs used" rows for one state (Rules §8: data available vs. used).

    Available = every source the registry runs for the state (national plus its own adapters), with its
    title and the canonical table it builds. Used, for parcel rolls, comes from the data dashboard summary:
    the parcels each source supplies after the one-source-per-jurisdiction rule. Other sources are listed
    as available; the bundle does not yet record which of them each scenario read.
    """
    from lotline.registry import sources_for

    parcels = {p["source"]: p for p in (summary_state or {}).get("parcel_sources", [])}
    rows = []
    for name, src in sources_for(state).items():
        prov = getattr(src.module, "PROVENANCE", {}) or {}
        sid = getattr(src.module, "SOURCE", name)
        p = parcels.get(name) or parcels.get(sid)
        rows.append(
            {
                "source": name,
                "title": prov.get("title", name),
                "url": prov.get("landing_url"),
                "table": src.table,
                "scope": "national" if src.states is None else "state",
                "parcels_on_file": p["parcels_latest"] if p else None,
                "parcels_used": p["parcels_used"] if p else None,
                "vintages": p["vintages"] if p else None,
            }
        )
    return rows


def data_section(states: Iterable[str], summary: dict | None) -> dict:
    """Per state: coverage totals from the data dashboard summary (None without one) and the sources table."""
    by = {s["state"]: s for s in (summary or {}).get("states", [])}
    out = {}
    for st in states:
        s = by.get(st)
        out[st] = {
            "name": s.get("name") if s else None,
            "totals": s.get("totals") if s else None,
            "sources": sources_table(st, s),
        }
    generated = (summary or {}).get("generated")
    return {"summary_generated": generated, "by_state": out, "overall": overall(summary)}


def overall(summary: dict | None) -> dict | None:
    """Totals across every state in the data dashboard summary, for the data tab's opening summary.

    Sums per-state counts (states never overlap): coded reforms, places with a coded reform, parcels on file,
    jurisdictions; permit years run from the earliest first year to the latest last year. None without one.
    """
    states = [s for s in (summary or {}).get("states", []) if s.get("totals")]
    if not states:
        return None
    t = [s["totals"] for s in states]
    years = [x["permit_years"] for x in t if x.get("permit_years")]
    return {
        "states": [s["state"] for s in states],
        "reforms": sum(x.get("reforms") or 0 for x in t),
        "reform_places": sum(x.get("reform_places") or 0 for x in t),
        "parcels": sum(x.get("parcels") or 0 for x in t),
        "jurisdictions": sum(x.get("jurisdictions") or 0 for x in t),
        "permit_first": min(y[0] for y in years) if years else None,
        "permit_last": max(y[1] for y in years) if years else None,
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


def payload(bundles: Iterable[dict], generated: str | None = None, summary: dict | None = None) -> dict:
    """What the page embeds: the ordered bundles, role labels, sliders, section 2's tables and build time."""
    states = order_states(bundles)
    if not states:
        raise ValueError("no results bundles to show: run `lotline results --state XX` first")
    stamp = generated or dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    scenarios = {k: {"label": v[0], "color": v[1]} for k, v in SCENARIOS.items()}
    data = data_section([b["meta"]["state"] for b in states], summary)
    from lotline.config import load_params

    agg = load_params("aggregate")
    overlap = {k: agg[f"overlap_flag_{k}_distance"].value for k in ("medium", "low")}
    return {
        "overlap_thresholds": overlap,
        "generated": stamp,
        "roles": ROLES,
        "scenarios": scenarios,
        "knobs": knobs(),
        "data": data,
        "states": states,
    }


def _data_uri(name: str) -> str:
    """An identity SVG as a base64 data URI, without its embedded provenance metadata."""
    text = (IDENTITY / "wordmark" / name).read_text(encoding="utf-8")
    text = re.sub(r"<metadata>.*?</metadata>", "", text, flags=re.S).strip()
    return "data:image/svg+xml;base64," + base64.b64encode(text.encode()).decode()


def _svg(name: str, height: int = 32) -> str:
    """A wordmark or mark as an `<img>` with a data URI, without its embedded provenance metadata.

    An `<img>` rather than inline SVG: each wordmark file carries a `<style>` with the same class names, and
    inline styles are page-global, so the dark copy would recolour the light one.
    """
    return f'<img src="{_data_uri(name)}" alt="Lotline" height="{height}">'


# Folds the data dashboard into section 2 (Ben, 2026-11-06: part of the data tab, not a link): its own header
# and state bar are hidden (the app's picker drives it), and its colours are mapped onto the identity tokens.
FOLD_CSS = """
<style id="lotline-fold">
body > header, #state-bar { display: none !important; }
:root:not(#lotline-fold) {
  --surface-0: var(--paper); --surface-1: var(--paper-raised); --surface-2: var(--paper-sunken);
  --border: var(--rule); --grid: var(--rule); --text-primary: var(--ink); --text-secondary: var(--ink-muted);
  --text-muted: var(--ink-faint); --accent: var(--survey);
}
body { background: transparent !important; font-family: var(--font-sans) !important; }
main { max-width: none !important; padding: 0 !important; }
</style>
"""


APP_FONT_FAMILIES = ("Public Sans", "IBM Plex Mono")  # Source Serif 4 is for the written reports only


def font_faces(families: tuple[str, ...] = APP_FONT_FAMILIES) -> str:
    """The `@font-face` rules from docs/build/identity/fonts/fonts.css for `families`, each file inlined as a
    base64 data URI, so the page needs no font host. An unknown file raises."""
    css = (IDENTITY / "fonts" / "fonts.css").read_text(encoding="utf-8")
    out = []
    for rule in re.findall(r"@font-face\s*\{[^}]*\}", css):
        family = re.search(r'font-family:\s*"([^"]+)"', rule).group(1)
        if family not in families:
            continue
        name = re.search(r'url\("([^"]+)"\)', rule).group(1)
        data = base64.b64encode((IDENTITY / "fonts" / name).read_bytes()).decode()
        out.append(rule.replace(f'url("{name}")', f'url("data:font/woff2;base64,{data}")'))
    return "\n".join(out)


def fold_dashboard(html: str) -> str:
    """The data dashboard's page restyled to sit inside section 2 (tokens + FOLD_CSS before `</head>`)."""
    if "</head>" not in html:
        raise ValueError("dashboard page has no </head>")
    tokens = (IDENTITY / "tokens.css").read_text(encoding="utf-8")
    return html.replace("</head>", f"<style>{font_faces()}\n{tokens}</style>{FOLD_CSS}</head>", 1)


def _json(x) -> str:
    return json.dumps(x, separators=(",", ":"), ensure_ascii=False, allow_nan=False).replace("</", "<\\/")


def render(data: dict, template: str | None = None, dashboard: str | None = None) -> str:
    """The page HTML with `data` embedded. `</` is escaped so the JSON can't close its script tag.

    `dashboard` is the data dashboard's own page (lotline.dashboard.render), embedded as a JSON string and
    loaded into a frame only when the reader opens it.
    """
    page = template if template is not None else TEMPLATE.read_text(encoding="utf-8")
    missing = [p for p in PLACEHOLDERS if p not in page]
    if missing:
        raise ValueError(f"template is missing {missing}")
    blob = _json(data)
    styles = font_faces() + "\n" + (IDENTITY / "tokens.css").read_text(encoding="utf-8")
    return (
        page.replace("/*__LOTLINE_TOKENS__*/", styles)
        .replace("<!--__WORDMARK_LIGHT__-->", _svg("lotline-wordmark-light.svg"))
        .replace("<!--__WORDMARK_DARK__-->", _svg("lotline-wordmark-dark.svg"))
        .replace("<!--__MARK_LIGHT__-->", _svg("lotline-mark-light.svg", 24))
        .replace("<!--__MARK_DARK__-->", _svg("lotline-mark-dark.svg", 24))
        .replace("__FAVICON__", _data_uri("lotline-mark-favicon.svg"))
        .replace("/*__LOTLINE_AGGREGATE__*/", AGGREGATE_JS.read_text(encoding="utf-8"))
        .replace("/*__LOTLINE_DASHBOARD__*/", _json(dashboard))
        .replace("/*__LOTLINE_DATA__*/", blob)
    )


def build_app(
    bundles: Iterable[Path] | None = None,
    results_dir: Path = RESULTS_DIR,
    out_dir: Path = OUT_DIR,
    generated: str | None = None,
    data_summary: Path | None = DATA_SUMMARY,
) -> Path:
    """Validate the bundles (default: every one under `results_dir`), write `<out_dir>/index.html`.

    `data_summary` is the data dashboard's summary.json (scripts/build_data_dashboard.py); when it is missing
    section 2 lists sources without coverage counts and says how to build it.
    """
    paths = list(bundles) if bundles is not None else find_bundles(results_dir)
    summary = None
    if data_summary is not None and Path(data_summary).exists():
        summary = json.loads(Path(data_summary).read_text(encoding="utf-8"))
    dashboard = None
    if summary is not None:
        from lotline.dashboard.render import render as render_dashboard

        dashboard = fold_dashboard(render_dashboard(summary))
    html = render(payload((load_bundle(p) for p in paths), generated, summary), dashboard=dashboard)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    page = out / "index.html"
    page.write_text(html, encoding="utf-8")
    return page
