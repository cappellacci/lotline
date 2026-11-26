"""Benchmark and state-specific scenario definitions (Handbook definitions), and the scenario contract.

**The contract (modularity plan step 1, #554).** A scenario is one module in this package that defines:

- `NAME`: the model's id (e.g. `"missing_middle"`).
- `LABELS`: `{"title": ..., "definition": ..., "handbook": ...}`: a plain-language title, a one-line
  definition and the Handbook text it follows (None where it follows none).
- `VARIANTS`: `{bundle scenario name: variant}`, the runs it adds to the bundle. One entry for most models;
  the fee model has two (`{"fees": "handbook", "fees_local_half": "local_half"}`, D-065). Each variant can
  also be a dict with its own `"title"` (and `"definition"`) to label that run.
- `run(inputs, variant) -> ScenarioRun`: the five-year draws for one variant, in the one shape below.

Optional:

- `ORDER` (default 100): position in the bundle. The built-in scenarios keep the order they had (ADU 10,
  missing middle 20, fees 30), so the shared completion and displacement draws come out the same.
- `TABLES`: the extra bundle parts it fills (e.g. `("fee_types",)`); this is the capability the app reads.
- `extra_tables(run) -> dict[part, DataFrame]`: those parts for one run (without the `state` column).

The registry, `all()`, is discovered the way state data sources are (`lotline/registry.py`): every module
here that defines `NAME` must meet the contract, or discovery raises. Modules without `NAME` (the model code
in `adu.py`, `mm.py`, `fees.py`) are skipped. Tests add a scenario with `registered(module)`.

The `bundle_*.py` modules connect the three built-in models to the contract without changing their code.
"""

from __future__ import annotations

import contextlib
import importlib
import pkgutil
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd

REQUIRED = ("NAME", "LABELS", "VARIANTS", "run")
LABEL_KEYS = ("title", "definition", "handbook")
COMPLETION_CLASSES = (
    "single_family",
    "multifamily",
)  # config/params/aggregate.yaml completion_factor_<class>
_EXTRA: list[ModuleType] = []  # registered in tests only


class ScenarioError(RuntimeError):
    pass


@dataclass
class Inputs:
    """What every scenario of one bundle run shares: the state, the data store, the origin year and the number
    of draws, plus inputs more than one scenario reads, each built once (`shared`).

    `places` is the state's place table (`adu.places_from_store`): the eligible parcels and data tier the
    bundle's meta row describes. `data_tier` and `eligible_proxy` are set from it by `results.build_bundle`.
    """

    state: str
    store: Any
    origin: int
    draws: int
    places: pd.DataFrame | None = None
    data_tier: int = 3
    eligible_proxy: bool = False
    _shared: dict = field(default_factory=dict, repr=False)

    def shared(self, key: str, build: Callable[[], Any]) -> Any:
        """`build()` the first time `key` is asked for, the same object after that."""
        if key not in self._shared:
            self._shared[key] = build()
        return self._shared[key]


@dataclass
class ScenarioRun:
    """One variant's draws in the shape `results_draws` stores (one value per draw, or one for every draw).

    - `eligible`: the funnel's first stage by data tier (tiers 1, 2, 3): lots the reform opens, or for a
      reform that opens none (fees) the homes it acts on.
    - `theta`: five-year homes permitted added per pencil-out unit of that stage; `pencil_out_share`: the
      share of the first stage where building pays; `net_new_share`: the share of added homes that are net
      new.
    - `completion`: completion class (`COMPLETION_CLASSES`) -> that class's added homes per draw. Results
      draws one completion factor per class, in this order, and weights them by these homes; with one class
      the factor is used as drawn.
    - `year_shares`: draws x years, each draw's homes added by year as a share of its five-year total.
    - `raw`: the model's own output, for `extra_tables` and the bundle's context tables.
    - `scenario` (the bundle name of the variant run) and `completion_draws` (the factors results drew, class
      -> draws) are filled in after `run`, so `extra_tables` can label and reuse them.
    """

    eligible: tuple[Any, Any, Any]
    theta: Any
    pencil_out_share: Any
    net_new_share: Any
    completion: Mapping[str, np.ndarray]
    year_shares: np.ndarray
    raw: Any = None
    scenario: str = ""
    completion_draws: dict = field(default_factory=dict)

    @property
    def horizon(self) -> int:
        return int(np.asarray(self.year_shares).shape[1])


@dataclass(frozen=True)
class Scenario:
    name: str  # the model's NAME
    module: ModuleType

    @property
    def order(self) -> int:
        return int(getattr(self.module, "ORDER", 100))

    @property
    def variants(self) -> dict[str, str]:
        """Bundle scenario name -> the variant `run` takes."""
        return {k: (v["variant"] if isinstance(v, Mapping) else v) for k, v in self.module.VARIANTS.items()}

    @property
    def tables(self) -> tuple[str, ...]:
        return tuple(getattr(self.module, "TABLES", ()))

    def labels(self, bundle_name: str) -> dict[str, str | None]:
        """The model's labels with the variant's own title and definition, where it has them."""
        v = self.module.VARIANTS[bundle_name]
        own = {k: v[k] for k in ("title", "definition") if isinstance(v, Mapping) and k in v}
        return {**{k: self.module.LABELS.get(k) for k in LABEL_KEYS}, **own}

    def run(self, inputs: Inputs, bundle_name: str) -> ScenarioRun:
        out = self.module.run(inputs, self.variants[bundle_name])
        if not isinstance(out, ScenarioRun):
            raise ScenarioError(f"{self.name}.run must return a ScenarioRun, not {type(out).__name__}")
        out.scenario = bundle_name
        return out

    def extra_tables(self, run: ScenarioRun) -> dict[str, pd.DataFrame]:
        fn = getattr(self.module, "extra_tables", None)
        out = dict(fn(run)) if fn else {}
        stray = set(out) - set(self.tables)
        if stray:
            raise ScenarioError(f"{self.name}.extra_tables returned {sorted(stray)}, not declared in TABLES")
        return out


def check_module(module: ModuleType) -> None:
    """Raise ScenarioError unless `module` meets the contract above."""
    missing = [n for n in REQUIRED if not hasattr(module, n)]
    if missing:
        raise ScenarioError(f"{module.__name__}: missing {', '.join(missing)}")
    if not isinstance(module.NAME, str) or not module.NAME.isidentifier():
        raise ScenarioError(f"{module.__name__}: NAME must be a lower-case identifier, not {module.NAME!r}")
    if not module.LABELS.get("title") or not module.LABELS.get("definition"):
        raise ScenarioError(f"{module.__name__}: LABELS needs a title and a definition")
    if not module.VARIANTS:
        raise ScenarioError(f"{module.__name__}: VARIANTS is empty")
    for name, v in module.VARIANTS.items():
        if not name.isidentifier() or (isinstance(v, Mapping) and "variant" not in v):
            raise ScenarioError(f"{module.__name__}: bad variant {name!r}")


def _discover(package: str = __name__) -> list[ModuleType]:
    pkg = importlib.import_module(package)
    found = []
    for info in pkgutil.iter_modules(pkg.__path__):
        module = importlib.import_module(f"{package}.{info.name}")
        if hasattr(module, "NAME"):
            check_module(module)  # a half-defined scenario is an error, not silently skipped
            found.append(module)
    return found


def all() -> list[Scenario]:  # noqa: A001 (the plan's name, like the registry of sources)
    """Every scenario, in bundle order (`ORDER`, then name). Raises on duplicate model or variant names."""
    found = _discover()
    modules = found + [m for m in _EXTRA if m not in found]
    out = sorted((Scenario(m.NAME, m) for m in modules), key=lambda s: (s.order, s.name))
    names = [s.name for s in out]
    variants = [v for s in out for v in s.variants]
    dupes = sorted({n for n in names if names.count(n) > 1} | {v for v in variants if variants.count(v) > 1})
    if dupes:
        raise ScenarioError(f"duplicate scenario names: {dupes}")
    return out


def bundle_names() -> tuple[str, ...]:
    """Every bundle scenario name (`results_draws.scenario`), in bundle order."""
    return tuple(v for s in all() for v in s.variants)


def get(name: str) -> Scenario:
    """The scenario whose model NAME or bundle variant is `name`."""
    for s in all():
        if name == s.name or name in s.variants:
            return s
    raise KeyError(name)


@contextlib.contextmanager
def registered(module: ModuleType) -> Iterator[ModuleType]:
    """Add a scenario module (one outside this package, e.g. a test fixture) for the duration of a block."""
    check_module(module)
    _EXTRA.append(module)
    try:
        yield module
    finally:
        _EXTRA.remove(module)


def year_shares_of(by_year) -> np.ndarray:
    """Each draw's homes by year as a share of its five-year total (draws x years in, draws x years out)."""
    by_year = np.asarray(by_year, dtype=float)
    tot = by_year.sum(axis=1, keepdims=True)
    return np.divide(by_year, tot, out=np.zeros_like(by_year), where=tot > 0)
