"""The forecast stays apart from fitting and checks (modularity plan step 2, docs/build/modularity-plan.md).

`src/lotline/model/` holds only what a forecast runs: the modules reached by import from the results bundle
(`model.results` and every scenario module it discovers), the app and the data dashboard. Fitting code lives
in `src/lotline/calibrate/`, checks in `src/lotline/validation/`. The import graph is read from the source
with `ast`, so nothing is imported or run.

`MOVING` lists the modules still in `model/` that do not belong there, with the session that owns the move.
When an owner moves one, they delete its line; a line for a module no longer in `model/` fails, so the list
can only shrink.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"

# module (under lotline.model) -> owner of the move. Fitting code goes to calibrate/, checks to validation/.
MOVING = {
    # ADU ("ADU statewide prediction methodology")
    "adu_fit_set": "ADU",
    "adu_forecast": "ADU",
    "adu_new_rule": "ADU",
    "adu_profiles": "ADU",
    "adu_reform_check": "ADU",
    "adu_refit": "ADU",
    "adu_terms": "ADU",
    "adu_trend": "ADU",
    "calibrate_adu": "ADU",  # on the forecast path: adu_owner, adu_screen, adu_types use its helpers
    "calibrate_shape": "ADU",  # on the forecast path through adu_types
    "estimate_adu": "ADU",  # on the forecast path through pooled_adu
    "fit_audit": "ADU",
    "joint_refit": "ADU",
    "score": "ADU",
    # Missing middle ("Missing Middle Analysis refresh")
    "calibrate_mm": "MM",
    "estimate_mm": "MM",  # on the forecast path: scenarios/mm.py imports helpers from it
    "mm_counts": "MM",
    "mm_fitsets": "MM",
    "mm_routes": "MM",
    "mm_tests": "MM",
    "place_types": "MM",
    "project_size": "MM",
}


def _modules() -> dict[str, Path]:
    out = {}
    for p in (SRC / "lotline").rglob("*.py"):
        parts = p.with_suffix("").relative_to(SRC).parts
        out[".".join(parts[:-1] if parts[-1] == "__init__" else parts)] = p
    return out


MODULES = _modules()


def imports_of(name: str) -> set[str]:
    """The lotline modules `name` imports anywhere in its source (top level or inside functions)."""
    path = MODULES[name]
    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")[: len(package.split(".")) - node.level + 1]
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            found |= {mod} | {f"{mod}.{a.name}" for a in node.names}
    return {m for m in found if m in MODULES}


def reached(roots) -> set[str]:
    seen, todo = set(), list(roots)
    while todo:
        m = todo.pop()
        if m not in seen:
            seen.add(m)
            todo += imports_of(m)
    return seen


def forecast_roots() -> list[str]:
    """The results bundle (with every scenario module, found by discovery at run time), the app and the data
    dashboard."""
    return [
        m
        for m in MODULES
        if m in ("lotline.model.results", "lotline.app.build")
        or m.startswith(("lotline.model.scenarios.", "lotline.dashboard"))
    ]


def model_modules() -> set[str]:
    return {m.removeprefix("lotline.model.") for m in MODULES if m.startswith("lotline.model.")}


def test_reader_sees_relative_and_function_imports():
    assert "lotline.model.baseline" in imports_of("lotline.validation.backtest")
    assert "lotline.model.scenarios" in imports_of("lotline.model.results")


def test_model_never_imports_calibrate():
    """Fitting code may use the engine, never the other way round. (Importing `validation.holdout`, the
    holdout filter, is allowed: it guards data, it is not a check.)

    A module still in `MOVING` is fitting code on its way out, so it may import fitting code that has already
    moved; this lets the ADU and MM owners move in either order. Once `MOVING` is empty the rule is absolute.
    """
    bad = {m: sorted(i for i in imports_of(m) if i.startswith("lotline.calibrate")) for m in MODULES}
    bad = {
        m: v
        for m, v in bad.items()
        if v and m.startswith("lotline.model") and m.removeprefix("lotline.model.") not in MOVING
    }
    assert not bad, f"the forecast must not depend on fitting code: {bad}"


def test_every_model_module_is_on_the_forecast_path_or_moving():
    on_path = {m.removeprefix("lotline.model.") for m in reached(forecast_roots())}
    stray = sorted(model_modules() - on_path - set(MOVING))
    assert not stray, f"not used by a forecast; move to calibrate/ or validation/, or list in MOVING: {stray}"


def test_moving_list_only_shrinks():
    gone = sorted(set(MOVING) - model_modules())
    assert not gone, f"already moved out of model/; delete from MOVING: {gone}"


# Step 3: no engine module over about 600 lines. The fitting modules in MOVING are leaving model/ and are
# not counted. OVERSIZE lists the engine modules still over the limit, with the owner splitting them; the
# owner deletes the line when the split lands, and a stale line fails.
MAX_LINES = 620  # "about 600": scenarios/fees.py (604) fits
OVERSIZE = {
    "scenarios.adu": "ADU",
    "pooled_adu": "ADU",
}


def test_engine_modules_stay_small():
    lines = {m: len(MODULES[f"lotline.model.{m}"].read_text().splitlines()) for m in model_modules()}
    big = {m: n for m, n in lines.items() if n > MAX_LINES and m not in MOVING}
    assert set(big) <= set(OVERSIZE), f"over {MAX_LINES} lines; split by method step: {big}"
    stale = sorted(m for m in OVERSIZE if m in lines and lines[m] <= MAX_LINES or m not in lines)
    assert not stale, f"no longer over {MAX_LINES} lines (or gone); delete from OVERSIZE: {stale}"
