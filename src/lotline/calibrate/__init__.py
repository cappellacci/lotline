"""`lotline calibrate`: every fitted number in config/params/ traced to one calibration step (phase 1).

`steps.STEPS` declares the steps; this module checks them against config and keeps a lock file,
`config/calibration.lock.json`, that records each produced value (a sha256 for whole files and tables). The
lock is to calibration what `uv.lock` is to packages: a value that changes in config without its step being
re-run and the lock rewritten fails `--check`, so a fitted number can't drift from its fit unnoticed.

    lotline calibrate --list         # the steps in run order, with what each produces and how
    lotline calibrate --check        # registry, config and lock agree (no data needed; runs in CI)
    lotline calibrate --write-lock   # after re-running a step on purpose: record config's values
    lotline calibrate --run [--step NAME] [--quick] [--write]   # recompute ported steps; compare or write

Running (phases 2-4): a step with a `runner` ("module:function") is recomputed from the fetched data. The
function takes a `RunContext` (the data store, quick or full, the step's seed and draws) and returns
{params file: {key: value or {value, low, high}}}. `run` compares each value with config (relative
difference) and, with `write`, puts it into the YAML `value:` (and `low:`/`high:`) lines, leaving comments and
sources untouched, then rewrites the lock. Steps not yet ported are listed as such. Runners for different
chains live in different modules (`lotline.calibrate.data_steps`, `.mm_steps`, `.adu_steps`), so they can be
ported in parallel.

What `--check` proves:
1. every step's `after` names a known step and the steps have no cycle;
2. every key a step produces exists in its params file, and no key is produced by two steps;
3. every parameter whose source says "Estimated" is produced by some step (coverage);
4. the lock lists exactly the produced values, and each equals what config holds now.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

import yaml

from lotline.calibrate.steps import STEPS, Step
from lotline.config import CONFIG_DIR

LOCK = "calibration.lock.json"


def _raw(file: str, config_dir: Path) -> dict:
    return yaml.safe_load((config_dir / "params" / f"{file}.yaml").read_text(encoding="utf-8")) or {}


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def order(steps: tuple[Step, ...] = STEPS) -> list[Step]:
    """The steps in a run order (each after the steps it needs); raises on an unknown step or a cycle."""
    by = {s.name: s for s in steps}
    for s in steps:
        missing = [a for a in s.after if a not in by]
        if missing:
            raise ValueError(f"step {s.name} runs after unknown step(s) {missing}")
    try:
        names = list(TopologicalSorter({s.name: set(s.after) for s in steps}).static_order())
    except CycleError as e:
        raise ValueError(f"calibration steps form a cycle: {e.args[1]}") from e
    return [by[n] for n in names]


def produced(steps: tuple[Step, ...] = STEPS, config_dir: Path = CONFIG_DIR) -> dict[str, str]:
    """`file:key` (or `file.csv` for a whole table) -> the step that produces it, with "*" expanded."""
    out: dict[str, str] = {}
    clashes = []
    for s in steps:
        names = [f"{f}" for f in s.tables]
        for file, keys in s.produces.items():
            keys = tuple(_raw(file, config_dir)) if keys == ("*",) else keys
            names += [f"{file}:{k}" for k in keys]
        for n in names:
            if n in out:
                clashes.append(f"{n} is produced by both {out[n]} and {s.name}")
            out[n] = s.name
    if clashes:
        raise ValueError("; ".join(clashes))
    return out


def current_values(config_dir: Path = CONFIG_DIR, steps: tuple[Step, ...] = STEPS) -> dict[str, object]:
    """What config holds now for every produced value: the number for a scalar parameter, a sha256 for a table
    entry or a whole file."""
    values: dict[str, object] = {}
    cache: dict[str, dict] = {}
    for name in sorted(produced(steps, config_dir)):
        if ":" not in name:
            values[name] = hashlib.sha256((config_dir / "params" / name).read_bytes()).hexdigest()
            continue
        file, key = name.split(":", 1)
        entry = cache.setdefault(file, _raw(file, config_dir)).get(key)
        if isinstance(entry, dict) and "value" in entry and not entry.get("table"):
            values[name] = entry["value"]
        else:
            values[name] = _digest(entry)
    return values


def lock_document(config_dir: Path = CONFIG_DIR, steps: tuple[Step, ...] = STEPS) -> dict:
    by_step: dict[str, dict] = {}
    owner = produced(steps, config_dir)
    for name, value in current_values(config_dir, steps).items():
        by_step.setdefault(owner[name], {})[name] = value
    meta = {
        s.name: {"decision": s.decision, "how": s.how, "status": s.status, "script": s.script} for s in steps
    }
    return {
        "about": "Fitted values in config/params/ by calibration step. Rewrite with `lotline calibrate "
        "--write-lock` only after re-running the step that produces them (src/lotline/calibrate).",
        "steps": {n: {**meta[n], "values": by_step.get(n, {})} for n in [s.name for s in order(steps)]},
    }


def write_lock(config_dir: Path = CONFIG_DIR, steps: tuple[Step, ...] = STEPS) -> Path:
    path = config_dir / LOCK
    path.write_text(json.dumps(lock_document(config_dir, steps), indent=1) + "\n", encoding="utf-8")
    return path


def check(config_dir: Path = CONFIG_DIR, steps: tuple[Step, ...] = STEPS) -> list[str]:
    """Every way registry, config and lock disagree, in plain words; empty when they agree."""
    problems: list[str] = []
    try:
        order(steps)
        owner = produced(steps, config_dir)
    except ValueError as e:
        return [str(e)]
    for s in steps:
        for file, keys in s.produces.items():
            raw = _raw(file, config_dir)
            problems += [f"step {s.name}: {file}.yaml has no {k}" for k in keys if k != "*" and k not in raw]
        problems += [f"step {s.name}: config/params/{t} is missing" for t in s.tables
                     if not (config_dir / "params" / t).exists()]  # fmt: skip
    for path in sorted((config_dir / "params").glob("*.yaml")):
        for key, entry in _raw(path.stem, config_dir).items():
            if isinstance(entry, dict) and str(entry.get("source", "")).lstrip().startswith("Estimated"):
                if f"{path.stem}:{key}" not in owner:
                    problems.append(f"{path.stem}:{key} is estimated but no calibration step produces it")
    lock_path = config_dir / LOCK
    if not lock_path.exists():
        return problems + [f"config/{LOCK} is missing: run `lotline calibrate --write-lock`"]
    locked = {
        k: v for s in json.loads(lock_path.read_text())["steps"].values() for k, v in s["values"].items()
    }
    now = current_values(config_dir, steps)
    for name in sorted(set(now) | set(locked)):
        if name not in locked:
            problems.append(f"{name} is produced by {owner[name]} but not in the lock")
        elif name not in now:
            problems.append(f"{name} is in the lock but no step produces it")
        elif locked[name] != now[name]:
            problems.append(
                f"{name} changed in config ({locked[name]} -> {now[name]}) without its step "
                f"({owner[name]}) being re-run and the lock rewritten"
            )
    return problems


@dataclass(frozen=True)
class RunContext:
    """What a runner gets: the data store, whether this is a quick run, and the step's own seed and draws (a
    quick run may scale its draws down; the full run must use the step's own)."""

    store: object
    quick: bool
    seed: int | None
    draws: int | None


def _resolve(runner: str):
    module, _, name = runner.partition(":")
    return getattr(importlib.import_module(module), name)


def _fmt(v) -> str:
    return str(v) if isinstance(v, int) and not isinstance(v, bool) else repr(float(v))


def set_values(file: str, values: dict[str, object], config_dir: Path = CONFIG_DIR) -> None:
    """Write each key's new numbers into `config/params/<file>.yaml`: a number sets `value:`; a dict may set
    `value`, `low` and `high` (a fitted interval). Every other line (comments, sources, units) stays as it is.
    Raises if a key or one of its lines isn't found."""
    path = config_dir / "params" / f"{file}.yaml"
    lines = path.read_text(encoding="utf-8").split("\n")
    for key, new in values.items():
        fields = new if isinstance(new, dict) else {"value": new}
        start = next((i for i, ln in enumerate(lines) if ln == f"{key}:"), None)
        if start is None:
            raise KeyError(f"{file}.yaml has no top-level {key}")
        tops = [i for i in range(start + 1, len(lines)) if lines[i] and not lines[i].startswith((" ", "#"))]
        end = tops[0] if tops else len(lines)
        for name, v in fields.items():
            hit = next((i for i in range(start + 1, end) if re.match(rf"^\s+{name}:\s*\S", lines[i])), None)
            if hit is None:
                raise KeyError(f"{file}.yaml: {key} has no {name} line")
            lines[hit] = re.sub(rf"^(\s+{name}:\s*).*$", lambda m, v=v: m.group(1) + _fmt(v), lines[hit])
    path.write_text("\n".join(lines), encoding="utf-8")


def run(
    names: list[str] | None = None,
    *,
    quick: bool = False,
    write: bool = False,
    store=None,
    config_dir: Path = CONFIG_DIR,
    steps: tuple[Step, ...] = STEPS,
) -> list[dict]:
    """Recompute the ported steps (all, or `names`) in run order. One row per value: step, name, config value,
    new value and relative difference; a step with no runner gives one row saying so. With `write` (full runs
    only), new values go into config and the lock is rewritten."""
    if write and quick:
        raise ValueError(
            "a quick run uses fewer draws, so it can't write config; run without --quick to write"
        )
    if store is None:
        from lotline.io import DataStore

        store = DataStore()
    chosen = [s for s in order(steps) if names is None or s.name in names]
    unknown = sorted(set(names or []) - {s.name for s in steps})
    if unknown:
        raise ValueError(f"unknown step(s) {unknown}")
    rows: list[dict] = []
    for s in chosen:
        if s.runner is None:
            rows.append({"step": s.name, "name": None, "status": "not ported yet"})
            continue
        out = _resolve(s.runner)(RunContext(store, quick, s.seed, s.draws))
        for file, values in out.items():
            raw = _raw(file, config_dir)
            for key, out_value in values.items():
                new = out_value["value"] if isinstance(out_value, dict) else out_value
                old = (raw.get(key) or {}).get("value")
                rel = abs(new - old) / abs(old) if old not in (None, 0) else None
                rows.append(
                    {"step": s.name, "name": f"{file}:{key}", "config": old, "new": new, "rel_diff": rel}
                )
            if write:
                set_values(file, values, config_dir)
    if write:
        write_lock(config_dir, steps)
    return rows
