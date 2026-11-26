"""The steps to add a state, as data, and the functions an app or agent calls on them (WS-SCALE task 13).

`config/onboarding/steps.yaml` lists the steps of `docs/adding_a_state.md`, in order. This module reads that
file and gives three things for each step:

- `commands(step, state)`: the built-in commands for the step, with `XX` replaced (empty when the step is
  manual or agent-only). The caller runs them; nothing here runs a command or downloads anything.
- `check(step, state, store)`: whether the step is done for the state, with a plain-language detail. It looks
  only at files: the state's config files and which processed tables exist. It reads no table contents,
  except `no_unlisted_geoids`, which reads the state's permits and parcels.
- `import_action(step, state)`: for the steps the app's rule agents can do (rules, fees), the "review and
  import" action: the proposed table's schema, where it is imported to, and the check that must then pass.

`plan(state, store)` puts it together for one state, and `render_short_path()` / `render_table()` write the
guide's generated blocks, so the guide and the app show the same steps.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from lotline.config import CONFIG_DIR

STEPS_FILE = CONFIG_DIR / "onboarding" / "steps.yaml"
REPO = CONFIG_DIR.parent
MODES = ("manual", "built_in", "agent")
NATIONAL_TABLES = (
    "acs_geo_year",
    "bps_place_year",
    "market_geo_year",
    "jurisdictions",
    "eligible_parcels",
    "place_inputs",
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AgentService(_Model):
    """How the app's rule agents do a step: they propose a table (`reforms` or `fees` rows, the existing CSV
    header, keyed by GEOID); the user reviews it and imports it to `import_to`. The step's `check` then
    validates the imported file exactly as it would a hand-made one. The agents never write config."""

    proposes: str = Field(pattern=r"^(reforms|fees)$")  # the schema table the proposal follows
    import_to: str  # repo path, `xx` = the state code in lower case
    owner: str
    note: str = ""


class Step(_Model):
    id: str = Field(pattern=r"^[a-z_]+$")
    title: str
    time: str
    level: int | None = Field(default=None, ge=0, le=3)  # None: every level
    short_path: bool
    inputs: list[str]
    outputs: list[str]
    modes: list[str] = Field(min_length=1)
    commands: list[list[str]]
    check: str | None
    done_when: str
    agent: AgentService | None = None


@dataclass(frozen=True)
class Status:
    done: bool | None  # None: no automatic check (a person decides)
    detail: str


def steps(path: Path = STEPS_FILE) -> list[Step]:
    """Every step, in the guide's order, validated."""
    out = [Step.model_validate(s) for s in yaml.safe_load(path.read_text())["steps"]]
    ids = [s.id for s in out]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path.name}: duplicate step ids")
    for s in out:
        if set(s.modes) - set(MODES):
            raise ValueError(f"{s.id}: modes must be among {MODES}")
        if ("built_in" in s.modes) != bool(s.commands):
            raise ValueError(f"{s.id}: a built_in step has commands, and only a built_in step does")
        if ("agent" in s.modes) != (s.agent is not None):
            raise ValueError(f"{s.id}: an agent step has an `agent` entry, and only an agent step does")
        if s.check is not None and s.check not in CHECKS:
            raise ValueError(f"{s.id}: unknown check {s.check!r}")
    return out


def step(step_id: str) -> Step:
    for s in steps():
        if s.id == step_id:
            return s
    raise KeyError(f"no onboarding step {step_id!r}")


def commands(s: Step | str, state: str) -> list[list[str]]:
    """The step's built-in commands for `state` (argument lists, `XX` and `xx` replaced)."""
    s = step(s) if isinstance(s, str) else s
    st = state.upper()
    return [[a.replace("XX", st).replace("xx", st.lower()) for a in cmd] for cmd in s.commands]


# ---- checks: each takes (state, store) and returns a Status ----------------------------------------------


def _file(path: Path, what: str) -> Status:
    rel = path.relative_to(REPO) if path.is_relative_to(REPO) else path
    return Status(True, f"{rel} exists") if path.exists() else Status(False, f"no {rel} yet ({what})")


def _has_table(store, state: str, table: str) -> bool:
    if store is None:
        return False
    folder = store.processed(state, table)
    return folder.is_dir() and any(folder.glob("*.parquet"))


def _assessment_written(state, store):
    return _file(REPO / "docs" / "build" / f"{state.lower()}-assessment.md", "the assessment")


def _state_config_loads(state, store):
    from lotline.config import load_state

    path = CONFIG_DIR / "states" / f"{state.lower()}.yaml"
    if not path.exists():
        return Status(False, f"no config/states/{state.lower()}.yaml yet")
    try:
        load_state(state)
    except Exception as e:  # noqa: BLE001 - shown to the user as the reason
        return Status(False, f"config/states/{state.lower()}.yaml does not load: {e}")
    return Status(True, "the state file loads")


def config_problems(state: str) -> list[str]:
    """What is wrong with a state file beyond its own shape: GEOIDs outside the state, missing named files,
    parcel sources that are not sources. The same checks as tests/config/test_state_schema.py."""
    from lotline.config import load_state
    from lotline.registry import sources_for

    cfg = load_state(state)
    fips, out = cfg.fips, []

    def bad(g: str, lengths=(7, 10)) -> bool:
        return not (g.isdigit() and len(g) in lengths and g.startswith(fips))

    for h in cfg.holdouts:
        if (h.geoid != fips) if h.statewide else bad(h.geoid):
            out.append(f"holdout {h.test_id}: GEOID {h.geoid} is not in the state")
    for name, geoids, lengths in (
        ("local_jurisdictions", cfg.local_jurisdictions, (7, 10)),
        ("data_tiers", cfg.data_tiers, (5, 7, 10)),
        ("train_until", cfg.train_until, (7, 10)),
        ("parcel_sources", [g for g in cfg.parcel_sources if g != "*"], (5, 7, 10)),
    ):
        out += [f"{name}: GEOID {g} is not in the state" for g in geoids if bad(g, lengths)]
    if cfg.parcel_sources:
        known = {getattr(s.module, "SOURCE", None) for s in sources_for(state).values()}
        out += [f"parcel_sources: {v} is not a source" for v in set(cfg.parcel_sources.values()) - known]
    if cfg.land_use_crosswalk and not (REPO / cfg.land_use_crosswalk).is_file():
        out.append(f"land_use_crosswalk: {cfg.land_use_crosswalk} does not exist")
    return out


def _state_config_consistent(state, store):
    first = _state_config_loads(state, store)
    if not first.done:
        return first
    problems = config_problems(state)
    return Status(not problems, "; ".join(problems) or "the state file agrees with the repo")


def _reforms_coded(state, store):
    from lotline.model.scenarios.adu import load_reforms
    from lotline.schemas import validate

    path = CONFIG_DIR / "reforms" / f"{state.lower()}.csv"
    if not path.exists():
        return Status(False, f"no config/reforms/{state.lower()}.csv yet")
    try:
        rows = validate(load_reforms(state), "reforms")
    except Exception as e:  # noqa: BLE001 - shown to the user as the reason
        return Status(False, f"config/reforms/{state.lower()}.csv does not pass the reforms schema: {e}")
    n = rows["jurisdiction_geoid"].nunique()
    return Status(True, f"{n} places coded in config/reforms/{state.lower()}.csv")


def _fees_coded(state, store):
    from lotline.config import load_fees

    fees = load_fees(state)
    if fees is None:
        return Status(False, f"no config/fees/{state.lower()}.csv yet")
    n = fees["jurisdiction_geoid"].nunique()
    return Status(n >= 5, f"{n} places have fees (the guide asks for at least 5)")


def _national_tables_built(state, store):
    missing = [t for t in NATIONAL_TABLES if not _has_table(store, state, t)]
    return Status(not missing, f"missing: {', '.join(missing)}" if missing else "all national tables built")


def _results_bundle_written(state, store):
    return _file(REPO / "reports" / "results" / state.lower() / "bundle.json", "run `lotline results`")


def _parcels_built(state, store):
    ok = _has_table(store, state, "parcels")
    return Status(ok, "parcels table built" if ok else "no parcels table (optional: level 3)")


def _permits_built(state, store):
    ok = _has_table(store, state, "permits")
    return Status(ok, "permits table built" if ok else "no permits table (optional: level 2)")


def _no_unlisted_geoids(state, store):
    from lotline.build.jurisdictions import config_orphans, unlisted

    if store is None:
        return Status(False, "no data directory")
    df = unlisted(state, store)
    orphans = config_orphans(state, store)
    bad = orphans[orphans["blocking"]]
    if not bad.empty:
        where = ", ".join(sorted(set(bad["where"])))
        return Status(
            False, f"{bad['geoid'].nunique()} GEOIDs named in config ({where}) are not jurisdictions"
        )
    if df.empty:
        return Status(True, "every GEOID in the local data and the config lists is a jurisdiction")
    return Status(False, f"{df['geoid'].nunique()} GEOIDs in the local data are not jurisdictions yet")


def _readiness_written(state, store):
    return _file(REPO / "docs" / "build" / f"{state.lower()}-readiness.md", "the readiness report")


CHECKS: dict[str, Callable] = {
    "assessment_written": _assessment_written,
    "state_config_loads": _state_config_loads,
    "state_config_consistent": _state_config_consistent,
    "reforms_coded": _reforms_coded,
    "fees_coded": _fees_coded,
    "national_tables_built": _national_tables_built,
    "results_bundle_written": _results_bundle_written,
    "parcels_built": _parcels_built,
    "permits_built": _permits_built,
    "no_unlisted_geoids": _no_unlisted_geoids,
    "readiness_written": _readiness_written,
}


def check(s: Step | str, state: str, store=None) -> Status:
    """Whether one step is done for `state`. `store` is a DataStore (None: data-directory checks say no)."""
    s = step(s) if isinstance(s, str) else s
    if s.check is None:
        return Status(None, "no automatic check: a person decides")
    return CHECKS[s.check](state.upper(), store)


def import_action(s: Step | str, state: str) -> dict | None:
    """For an agent step: what the app's "review and import" action needs. The proposed table's schema,
    the file to write once the user accepts it, and the check that must pass afterwards (the manual
    path's own)."""
    s = step(s) if isinstance(s, str) else s
    if s.agent is None:
        return None
    return {
        "proposes": s.agent.proposes,
        "import_to": s.agent.import_to.replace("xx", state.lower()),
        "check": s.check,
        "owner": s.agent.owner,
    }


def plan(state: str, store=None) -> list[dict]:
    """Every step for one state: what it is, how it can be done, its commands and whether it is done."""
    out = []
    for n, s in enumerate(steps(), start=1):
        status = check(s, state, store)
        out.append(
            {
                "n": n,
                "id": s.id,
                "title": s.title,
                "level": s.level,
                "time": s.time,
                "done_when": s.done_when,
                "modes": list(s.modes),
                "commands": commands(s, state),
                "agent": s.agent.model_dump() if s.agent else None,
                "import": import_action(s, state),
                "done": status.done,
                "detail": status.detail,
            }
        )
    return out


# ---- the guide's generated blocks --------------------------------------------------------------------------

LEVEL = {None: "any", 0: "0 national", 1: "1 rules", 2: "2 permits", 3: "3 parcels"}


def _cmd(cmd: list[str]) -> str:
    return " ".join(cmd)


def render_short_path() -> str:
    """The one-page short path: the steps marked `short_path`, numbered as in the guide."""
    lines = []
    short = [(n, s) for n, s in enumerate(steps(), start=1) if s.short_path]
    for k, (n, s) in enumerate(short, start=1):
        lines.append(f"{k}. **{s.title}** (step {n}, {s.time}).")
        if s.commands:
            lines += ["   ```bash", *[f"   {_cmd(c)}" for c in s.commands], "   ```"]
    return "\n".join(lines) + "\n"


def render_table() -> str:
    """Every step in one table: level, time, how it can be done and what says it is done."""
    rows = ["| Step | Level | Time | Ways to do it | Done when |", "|---|---|---|---|---|"]
    for n, s in enumerate(steps(), start=1):
        ways = ", ".join(m.replace("_", "-") for m in s.modes)
        done = s.done_when + ("" if s.check else " (a person decides)")
        rows.append(f"| {n}. {s.title} | {LEVEL[s.level]} | {s.time} | {ways} | {done} |")
    return "\n".join(rows) + "\n"


GUIDE = REPO / "docs" / "adding_a_state.md"
BLOCKS = {
    "short-path": render_short_path,
    "steps-table": render_table,
}


def sync_guide(text: str) -> str:
    """The guide with its generated blocks (between `<!-- name:begin ... -->` and `<!-- name:end -->`)
    rewritten from the steps file. Hand-written text outside the blocks is kept as is."""
    import re

    for name, render in BLOCKS.items():
        pattern = re.compile(rf"(<!-- {name}:begin[^>]*-->\n)(.*?)(<!-- {name}:end -->)", re.S)
        if not pattern.search(text):
            raise ValueError(f"the guide has no {name} block")
        text = pattern.sub(lambda m, r=render: m.group(1) + r() + m.group(3), text)
    return text


if __name__ == "__main__":  # uv run python -m lotline.onboarding: rewrite the guide's generated blocks
    GUIDE.write_text(sync_guide(GUIDE.read_text()))
