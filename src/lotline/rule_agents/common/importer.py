"""Import a reviewed proposal from a rule-agent run into the app's rules for a state.

The agents never write the app's configuration; they leave a proposed table in the run folder
(`docs/build/rule-agents/PRINCIPLES.md`). This is the user's step: preview what the proposal would add or
change in `config/reforms/<st>.csv` or `config/fees/<st>.csv`, then write it.

How rows are matched (each key is unique in every state's file today):

- `reforms`: `reform_id`.
- `fees`: jurisdiction, year, fee component, the source's fee name, building type and basis.

Rules: rows are compared and written as text, so existing rows keep their exact formatting. A proposal row
whose key is new is **added**; one whose key exists but whose values differ is **changed** and replaces the
old row only with `replace_changed=True` (otherwise it is listed and skipped); nothing is ever deleted. The
proposal must use the file's own column headers (blank columns are fine; an unknown column stops the
import). The merged table is validated against the schema before anything is written.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

KEYS = {
    "reforms": ("reform_id",),
    "fees": ("jurisdiction_geoid", "year", "fee_component", "fee_type", "building_type_std", "basis"),
}
_DATES = {
    "reforms": ("announced_date", "adoption_date", "effective_date", "end_date", "verified_date"),
    "fees": ("effective_date", "verified_date"),
}
_INTS = {"reforms": (), "fees": ("year", "dollar_year", "in_force_through")}


class ImportError_(ValueError):
    """The proposal cannot be imported as it stands (unknown columns, missing keys, schema errors)."""


@dataclass
class Plan:
    table: str
    target: Path
    header: list[str]
    added: list[dict] = field(default_factory=list)
    changed: list[tuple[dict, dict, list[str]]] = field(
        default_factory=list
    )  # (old, new, columns that differ)
    unchanged: int = 0

    def summary(self) -> str:
        lines = [
            f"{self.target}: {len(self.added)} new row(s), {len(self.changed)} changed, "
            f"{self.unchanged} already the same"
        ]
        for r in self.added:
            lines.append(f"  + {_key_text(self.table, r)}")
        for old, new, cols in self.changed:
            diffs = "; ".join(f"{c}: {_short(old.get(c, ''))} -> {_short(new.get(c, ''))}" for c in cols[:4])
            more = f" (+{len(cols) - 4} more)" if len(cols) > 4 else ""
            lines.append(f"  ~ {_key_text(self.table, new)}: {diffs}{more}")
        return "\n".join(lines)


def _short(v: str, n: int = 60) -> str:
    """A value for the preview: long notes show their end, where an edit usually is."""
    v = (v or "").strip()
    return repr(v) if len(v) <= n else repr("..." + v[-(n - 3) :])


def _key(table: str, row: dict) -> tuple:
    return tuple((row.get(k) or "").strip() for k in KEYS[table])


def _key_text(table: str, row: dict) -> str:
    return " / ".join(v for v in _key(table, row) if v)


def _read(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        r = csv.DictReader(fh)
        return list(r.fieldnames or []), [dict(row) for row in r]


def target_path(table: str, state: str, config_dir: Path) -> Path:
    if table not in KEYS:
        raise ImportError_(f"table must be one of {sorted(KEYS)}")
    return Path(config_dir) / table / f"{state.lower()}.csv"


def plan(proposal: Path, table: str, state: str, config_dir: Path) -> Plan:
    """Compare a proposal with the state's file. By hand: the file holds A (cap 3) and B; the proposal holds
    A (cap 4) and C -> added [C], changed [A: unit_cap '3' -> '4'], unchanged 0 (B is not in the proposal and
    stays as it is)."""
    target = target_path(table, state, config_dir)
    p_header, p_rows = _read(Path(proposal))
    if target.exists():
        header, rows = _read(target)
    else:
        from lotline.schemas import columns

        header, rows = list(columns(table)), []
    unknown = [c for c in p_header if c not in header]
    if unknown:
        raise ImportError_(f"the proposal has columns the {table} file does not: {unknown}")
    missing = [k for k in KEYS[table] if k not in p_header]
    if missing:
        raise ImportError_(f"the proposal lacks key column(s) {missing}")
    if "state" in p_header and any((r.get("state") or "").upper() != state.upper() for r in p_rows):
        raise ImportError_(f"the proposal has rows for a state other than {state.upper()}")
    existing = {_key(table, r): r for r in rows}
    seen: set[tuple] = set()
    out = Plan(table, target, header)
    for r in p_rows:
        k = _key(table, r)
        if not all(k):
            raise ImportError_(f"a proposal row has a blank key: {r}")
        if k in seen:
            raise ImportError_(f"the proposal repeats a key: {_key_text(table, r)}")
        seen.add(k)
        full = {c: (r.get(c) or "") for c in header}
        old = existing.get(k)
        if old is None:
            out.added.append(full)
            continue
        diff = [c for c in header if (old.get(c) or "").strip() != full[c].strip()]
        if diff:
            out.changed.append((old, full, diff))
        else:
            out.unchanged += 1
    return out


def merged_text(p: Plan, *, replace_changed: bool = False) -> str:
    """The state's file after the import, as CSV text: existing rows in place (changed ones replaced only when
    asked), new rows at the end."""
    rows: list[dict] = []
    if p.target.exists():
        _, rows = _read(p.target)
    repl = {_key(p.table, new): new for _, new, _ in p.changed} if replace_changed else {}
    rows = [repl.get(_key(p.table, r), r) for r in rows] + p.added
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=p.header, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in p.header})
    return buf.getvalue()


def validate_text(text: str, table: str) -> None:
    """Schema-validate a whole state file given as CSV text (raises ImportError_ listing the problems)."""
    import pandas as pd

    from lotline.schemas import validate

    df = pd.read_csv(io.StringIO(text), dtype={"jurisdiction_geoid": str})
    for c in _DATES[table]:
        if c in df:
            df[c] = pd.to_datetime(df[c])
    for c in _INTS[table]:
        if c in df:
            df[c] = df[c].astype("Int64")
    try:
        validate(df, table)
    except Exception as exc:  # noqa: BLE001 - pandera / contract errors: report them all to the user
        raise ImportError_(f"the merged {table} table fails the schema:\n{exc}") from None


def apply(p: Plan, *, replace_changed: bool = False) -> Path:
    """Validate, then write the merged file."""
    text = merged_text(p, replace_changed=replace_changed)
    validate_text(text, p.table)
    p.target.parent.mkdir(parents=True, exist_ok=True)
    p.target.write_text(text, encoding="utf-8")
    return p.target
