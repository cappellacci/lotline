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

Optional: `MANIFEST_SOURCES`, the manifest ids a build step reads (default `[SOURCE]`).
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
    from lotline.adapters.national import acs, bps, fhfa, fred
    from lotline.build import jurisdictions

    return [
        Source("acs", acs, "acs_geo_year", None),
        Source("bps", bps, "bps_place_year", None),
        Source("fhfa", fhfa, "market_geo_year", None),
        Source("fred", fred, "market_geo_year", None),
        Source("jurisdictions", jurisdictions, "jurisdictions", None),
    ]


def documented_only() -> list[ModuleType]:
    """Modules that download data (so need provenance) but aren't run by `lotline fetch` on their own."""
    from lotline.adapters.national import bps_state, decennial

    return [bps_state, decennial]


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
