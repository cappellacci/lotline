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
    """A place whose post-reform outcomes stay hidden until a frozen prediction is on main."""

    test_id: str = Field(pattern=r"^V\d-[A-Z]{2}-[A-Z0-9_-]+$")
    place: str
    geoid: str = Field(pattern=r"^\d{7}(\d{3})?$")
    outcome_from: dt.date
    outcome_until: dt.date
    reason: str

    @model_validator(mode="after")
    def _ordered(self) -> Holdout:
        if self.outcome_until < self.outcome_from:
            raise ValueError(f"{self.test_id}: outcome_until is before outcome_from")
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


def load_params(name: str, config_dir: Path = CONFIG_DIR) -> dict[str, Parameter]:
    """Load config/params/<name>.yaml: parameter name -> {value, low, high, unit, source, notes}."""
    raw = yaml.safe_load((config_dir / "params" / f"{name}.yaml").read_text()) or {}
    return {key: Parameter.model_validate(spec) for key, spec in raw.items()}
