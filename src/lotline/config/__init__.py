"""Config loaders: state configs and model parameters, validated on read.

State configs live in config/states/<st>.yaml; parameters in config/params/*.yaml (value, low, high, unit,
source, notes). The code never hard-codes a parameter (CLAUDE.md).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Holdout(_Model):
    """A place whose post-reform outcomes stay hidden until a frozen prediction is on main.

    `geoid` is a place (7 digits) or township (10 digits). A 2-digit state FIPS holds out the whole state:
    every row whose GEOID starts with it (places, townships, county remainders and the state total), as for a
    transfer test that predicts a state from the others before any of its outcomes are seen.
    """

    test_id: str = Field(pattern=r"^V\d-[A-Z]{2}-[A-Z0-9_-]+$")
    place: str
    geoid: str = Field(pattern=r"^(\d{2}|\d{7}(\d{3})?)$")
    outcome_from: dt.date
    outcome_until: dt.date
    reason: str
    # Other GEOIDs whose rows contain this place's outcomes, e.g. the county BPS files a place's permits under
    # (Charlotte's are reported under Mecklenburg County, 37119). They are held out over the same window.
    reporting_geoids: list[str] = Field(default_factory=list)
    reporting_reason: str | None = None
    # Set by Ben once the test is scored: from this date the filter no longer hides the outcomes, so the full
    # data can be built and pooled. The test stays in the registry (scoring still reruns with `unblind`), and
    # a release is refused unless the frozen prediction is in the repo.
    released_on: dt.date | None = None
    released_note: str | None = None

    @property
    def statewide(self) -> bool:
        return len(self.geoid) == 2

    @property
    def geoids(self) -> list[str]:
        """The place plus every GEOID its outcomes are reported under."""
        return [self.geoid, *self.reporting_geoids]

    @model_validator(mode="after")
    def _ordered(self) -> Holdout:
        if self.outcome_until < self.outcome_from:
            raise ValueError(f"{self.test_id}: outcome_until is before outcome_from")
        if self.reporting_geoids and not self.reporting_reason:
            raise ValueError(f"{self.test_id}: reporting_geoids need a reporting_reason")
        if self.released_on and not self.released_note:
            raise ValueError(f"{self.test_id}: released_on needs a released_note")
        if self.released_on and self.released_on < self.outcome_from:
            raise ValueError(f"{self.test_id}: released before its outcome window opened")
        return self


class Source(_Model):
    name: str
    url: str
    license: str
    access: str  # e.g. arcgis, socrata, ckan, file
    cadence: str | None = None
    notes: str | None = None


class StateConfig(_Model):
    state: str = Field(pattern=r"^[A-Z]{2}$")
    name: str
    fips: str = Field(pattern=r"^\d{2}$")
    bps_region: str
    holdouts: list[Holdout] = []
    sources: list[Source] = []
    land_use_crosswalk: str | None = None
    train_until: dict[str, dt.date] = {}  # geoid -> last date usable for fitting
    data_tiers: dict[str, int] = {}  # geoid -> data tier (1 best, 3 national data only); default 3
    # Where parcel sources overlap: jurisdiction GEOID -> the one parcels source to count it from, with "*" as
    # the default for the rest (build/eligible.single_source). Without it, overlapping sources are an error.
    parcel_sources: dict[str, str] = {}
    township_permits: bool = False  # townships (county subdivisions) issue permits and get their own rows
    zip3_ranges: list[tuple[int, int]] = []  # USPS 3-digit ZIP prefixes (inclusive) that belong to the state
    # D-068: the state's ADU law is coded row by row for every place it covers (config/reforms/<st>.csv), so a
    # place with no ADU row is outside the law and takes the prior of states without such a law.
    adu_state_law_rows_complete: bool = False


class Parameter(_Model):
    value: float
    low: float
    high: float
    unit: str
    source: str
    notes: str = ""

    @model_validator(mode="after")
    def _in_range(self) -> Parameter:
        if not self.low <= self.value <= self.high:
            raise ValueError(f"value {self.value} outside [{self.low}, {self.high}]")
        return self


def load_state(state: str, config_dir: Path = CONFIG_DIR) -> StateConfig:
    path = config_dir / "states" / f"{state.lower()}.yaml"
    cfg = StateConfig.model_validate(yaml.safe_load(path.read_text()))
    if cfg.state != state.upper():
        raise ValueError(f"{path}: state is {cfg.state}, expected {state.upper()}")
    return cfg


def all_states(config_dir: Path = CONFIG_DIR) -> list[str]:
    return sorted(p.stem.upper() for p in (config_dir / "states").glob("*.yaml"))


def load_fees(state: str, config_dir: Path = CONFIG_DIR):
    """Hand-coded development fees for a state (config/fees/<st>.csv), validated against the `fees` schema.

    Rows come from each city's official fee schedule (the city-ordinance pipeline or a manual lookup), with a
    citation. Returns None when the state has no fee file yet.
    """
    import pandas as pd

    from lotline.schemas import validate

    path = config_dir / "fees" / f"{state.lower()}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, dtype={"jurisdiction_geoid": str})
    for col in ("effective_date", "verified_date"):
        if col in df:
            df[col] = pd.to_datetime(df[col])
    for col in ("year", "dollar_year", "in_force_through"):
        if col in df:
            df[col] = df[col].astype("Int64")
    return validate(df, "fees")


def load_params(name: str, config_dir: Path = CONFIG_DIR) -> dict[str, Parameter]:
    """Load config/params/<name>.yaml: parameter name -> {value, low, high, unit, source, notes}.

    An entry marked `table: true` (e.g. `adu_flag_undercount`) is a table with its own loader and is left out.
    """
    raw = yaml.safe_load((config_dir / "params" / f"{name}.yaml").read_text()) or {}
    return {
        key: Parameter.model_validate(spec)
        for key, spec in raw.items()
        if not (isinstance(spec, dict) and spec.get("table"))
    }


UNDERCOUNT_KINDS = ("field", "parser", "floor", "none")


class UndercountRow(_Model):
    """One permit source's ADU flag undercount k (D-078). `value` is the median, `low`-`high` the two-sided
    `interval`. A field row with `prior: true` takes the table's prior; a parser row with no value has no hand
    check yet (k = 1); floor and none rows are k = 1. Field k >= 1; a parser k is precision / recall
    (D-081) and may be below 1."""

    source: str
    place: str
    kind: str
    value: float | None = None
    low: float | None = None
    high: float | None = None
    interval: float | None = None
    prior: bool = False
    first_year: int | None = None
    last_year: int | None = None
    low_recall: bool = False
    report: str
    notes: str = ""

    @model_validator(mode="after")
    def _check(self) -> UndercountRow:
        if self.kind not in UNDERCOUNT_KINDS:
            raise ValueError(f"{self.source}: kind {self.kind!r} not in {UNDERCOUNT_KINDS}")
        given = [x is not None for x in (self.value, self.low, self.high, self.interval)]
        if any(given) and not all(given):
            raise ValueError(f"{self.source}: value, low, high and interval go together")
        if self.prior and (self.kind != "field" or any(given)):
            raise ValueError(f"{self.source}: only a field row without its own k takes the prior")
        if self.kind == "field" and not (self.prior or all(given)):
            raise ValueError(f"{self.source}: a field row needs its own k or prior: true")
        if self.kind in ("floor", "none") and any(given):
            raise ValueError(f"{self.source}: a {self.kind} row has no k (it is 1)")
        if all(given):
            # A field k counts roll-confirmed ADUs the flags missed, so it is >= 1. A parser k is precision /
            # recall (D-081), which falls below 1 when false positives outnumber misses.
            if self.kind == "field" and self.low < 1.0:
                raise ValueError(f"{self.source}: a field row needs low >= 1")
            if self.low <= 0.0:
                raise ValueError(f"{self.source}: need low > 0")
            if not self.low <= self.value <= self.high:
                raise ValueError(f"{self.source}: need low <= value <= high")
            if not 0.0 < self.interval < 1.0:
                raise ValueError(f"{self.source}: interval must be in (0, 1)")
        if self.first_year and self.last_year and self.first_year > self.last_year:
            raise ValueError(f"{self.source}: first_year after last_year")
        return self

    @property
    def measured(self) -> bool:
        return self.value is not None

    @property
    def floor(self) -> bool:
        return self.kind == "floor"

    def covers(self, year: int) -> bool:
        return (self.first_year is None or year >= self.first_year) and (
            self.last_year is None or year <= self.last_year
        )


class UndercountPrior(_Model):
    low: float
    interval: float
    source: str


class UndercountTable(_Model):
    table: bool
    unit: str
    source: str
    prior: UndercountPrior
    rows: list[UndercountRow]

    @model_validator(mode="after")
    def _no_overlap(self) -> UndercountTable:
        by: dict[str, list[UndercountRow]] = {}
        for r in self.rows:
            by.setdefault(r.source, []).append(r)
        for src, rows in by.items():
            for i, a in enumerate(rows):
                for b in rows[i + 1 :]:
                    lo = max(a.first_year or -9999, b.first_year or -9999)
                    hi = min(a.last_year or 9999, b.last_year or 9999)
                    if lo <= hi:
                        raise ValueError(f"{src}: two rows cover {lo}")
        return self


def load_undercount(config_dir: Path = CONFIG_DIR, key: str = "adu_flag_undercount") -> UndercountTable:
    """The ADU flag undercount table by permit source (params/adu.yaml `adu_flag_undercount`, D-078)."""
    raw = yaml.safe_load((config_dir / "params" / "adu.yaml").read_text()) or {}
    return UndercountTable.model_validate(raw[key])
