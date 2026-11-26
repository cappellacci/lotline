"""Source registry: every data source `lotline fetch` can run and `lotline provenance` can document.

National sources are listed here. **State sources are discovered**: any module in
`lotline/adapters/states/<st>/` that defines the four names below is a source for that state, with the module
name as its CLI id (`lotline fetch --state MN --source metc_permits`). State workstreams add sources without
touching CORE code.

A source module must define:

- `SOURCE`: manifest source id (unique across all sources), the `source=` it passes to `fetch()`
- `TABLE`: the canonical table it builds (a key of `lotline.schemas.TABLES`)
- `PROVENANCE`: dict with `title`, `landing_url`, `table`, `cleaning` (list), `limitations` (list), and
  optionally `attribution`
- `load(state, store, *, refresh=False) -> DataFrame`: returns the validated table, holdouts already removed

Optional: `MANIFEST_SOURCES`, the manifest ids a build step reads (default `[SOURCE]`). For the run order of
a plain `lotline fetch` (`fetch_order`): `READS`, the canonical tables `load` reads from the store, so it runs
after the sources that build them; `RERUN_AFTER`, tables whose later rebuild means this source runs once more
(the jurisdictions list takes its data tiers from the parcels, whose readers need the list first); and
`RUN_LAST` (place_inputs, which reads every table).
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from types import ModuleType

from lotline.schemas import TABLES

REQUIRED = ("SOURCE", "TABLE", "PROVENANCE", "load")
PROVENANCE_KEYS = ("title", "landing_url", "table", "cleaning", "limitations")
STATES_PACKAGE = "lotline.adapters.states"


class RegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class Source:
    name: str  # CLI id
    module: ModuleType
    table: str
    states: tuple[str, ...] | None  # None: national, runs for every configured state

    @property
    def manifest_sources(self) -> list[str]:
        return list(getattr(self.module, "MANIFEST_SOURCES", [self.module.SOURCE]))


def _national() -> list[Source]:
    from lotline.adapters.national import acs, bps, fhfa, fred, hud_il
    from lotline.build import demand, eligible, jurisdictions, place_inputs

    return [
        Source("acs", acs, "acs_geo_year", None),
        Source("bps", bps, "bps_place_year", None),
        Source("fhfa", fhfa, "market_geo_year", None),
        Source("fred", fred, "market_geo_year", None),
        Source("hud_il", hud_il, "market_geo_year", None),
        Source("demand", demand, "market_geo_year", None),
        Source("eligible", eligible, "eligible_parcels", None),
        Source("jurisdictions", jurisdictions, "jurisdictions", None),
        Source("place_inputs", place_inputs, "place_inputs", None),  # last: reads every table above
    ]


def documented_only() -> list[ModuleType]:
    """Modules that download data (so need provenance) but aren't run by `lotline fetch` on their own."""
    from lotline.adapters.checks import houston_permits, rlis_housing
    from lotline.adapters.national import bps_state, cbp, cbsa, decennial, geoparts, pep, tiger_boundaries

    return [bps_state, cbp, cbsa, decennial, geoparts, pep, tiger_boundaries, houston_permits, rlis_housing]


def check_module(module: ModuleType) -> None:
    """Raise RegistryError unless `module` meets the source contract above."""
    missing = [n for n in REQUIRED if not hasattr(module, n)]
    if missing:
        raise RegistryError(f"{module.__name__}: missing {', '.join(missing)}")
    if module.TABLE not in TABLES:
        raise RegistryError(f"{module.__name__}: TABLE {module.TABLE!r} is not a canonical table")
    prov = module.PROVENANCE
    absent = [k for k in PROVENANCE_KEYS if not prov.get(k)]
    if absent:
        raise RegistryError(f"{module.__name__}: PROVENANCE lacks {', '.join(absent)}")
    if not isinstance(prov["cleaning"], list) or not isinstance(prov["limitations"], list):
        raise RegistryError(f"{module.__name__}: PROVENANCE cleaning and limitations must be lists")


def discover_state_sources(package: str = STATES_PACKAGE) -> list[Source]:
    """Source modules under adapters/states/<st>/ (helper modules without the contract names are skipped)."""
    found = []
    states_pkg = importlib.import_module(package)
    for st in pkgutil.iter_modules(states_pkg.__path__):
        if not st.ispkg:
            continue
        state_pkg = importlib.import_module(f"{package}.{st.name}")
        for mod in pkgutil.iter_modules(state_pkg.__path__):
            module = importlib.import_module(f"{package}.{st.name}.{mod.name}")
            if not any(hasattr(module, n) for n in ("SOURCE", "TABLE", "PROVENANCE")):
                continue  # a helper module, not a source
            check_module(module)  # half-defined sources are errors, not silently skipped
            found.append(Source(mod.name, module, module.TABLE, (st.name.upper(),)))
    return found


def all_sources(package: str = STATES_PACKAGE) -> list[Source]:
    sources = _national() + discover_state_sources(package)
    names = [s.name for s in sources]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise RegistryError(f"duplicate source names: {dupes}")
    ids = [s.module.SOURCE for s in sources if hasattr(s.module, "SOURCE")]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    if dup_ids:
        raise RegistryError(f"duplicate manifest SOURCE ids: {dup_ids}")
    return sources


def sources_for(state: str, package: str = STATES_PACKAGE) -> dict[str, Source]:
    """CLI id -> Source for every source that runs for `state` (national + that state's own)."""
    st = state.upper()
    return {s.name: s for s in all_sources(package) if s.states is None or st in s.states}


def provenance_modules(package: str = STATES_PACKAGE) -> dict[str, ModuleType]:
    """Manifest source id -> module carrying its PROVENANCE, for docs/data_provenance.md."""
    modules = [s.module for s in all_sources(package)] + documented_only()
    return {m.SOURCE: m for m in modules if hasattr(m, "PROVENANCE")}


def fetch_order(available: dict[str, Source]) -> list[str]:
    """The order a plain `lotline fetch` runs a state's sources: each after the sources building the tables it
    `READS`, otherwise by name, `RUN_LAST` sources at the end. A source with `RERUN_AFTER` tables runs again
    right after the last source building one of them, and its readers wait for that second run.

    Raises RegistryError on a dependency loop, naming the sources in it.
    """
    attr = lambda n, a: tuple(getattr(available[n].module, a, ()))  # noqa: E731
    makers: dict[str, set[str]] = {}
    for n, src in available.items():
        makers.setdefault(src.table, set()).add(n)
    needs = {n: {m for t in attr(n, "READS") for m in makers.get(t, ()) if m != n} for n in available}
    for n in available:  # readers of a rerun source wait for what triggers the rerun, except those triggers
        later = {m for t in attr(n, "RERUN_AFTER") for m in makers.get(t, ()) if m != n}
        for r in set(available) - later - {n}:
            if available[n].table in attr(r, "READS"):
                needs[r] |= later
    last = {n for n in available if getattr(available[n].module, "RUN_LAST", False)}
    for n in last:
        needs[n] |= set(available) - last

    order: list[str] = []
    todo = set(available)
    while todo:
        ready = sorted(n for n in todo if not needs[n] & todo)
        if not ready:
            raise RegistryError(f"fetch sources depend on each other in a loop: {', '.join(sorted(todo))}")
        order.append(ready[0])
        todo.remove(ready[0])

    for n in [n for n in order if attr(n, "RERUN_AFTER")]:
        triggers = [i for i, m in enumerate(order) if available[m].table in attr(n, "RERUN_AFTER") and m != n]
        if triggers and max(triggers) > order.index(n):
            order.insert(max(triggers) + 1, n)
    return order
