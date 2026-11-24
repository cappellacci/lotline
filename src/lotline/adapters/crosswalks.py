"""The two crosswalk formats in `config/crosswalks/` and one reader for both (WS-SCALE task 7).

A crosswalk maps a source's own codes to the fixed vocabularies in `lotline.schemas`. There are two kinds,
each with one header, so a new state copies a file instead of learning a new layout.

**Land use** (`<st>_land_use_*.csv`, `oh_dte_luc.csv`, `tx_*_land_use.csv`, ...):

    field,code,description,land_use_std,notes,source_url[,pattern][,county][,refine_by_units][,confidence][,applied]

- `field`: the source column the code comes from (documentation; the adapter decides which column it reads).
- `code`: the source's value, matched exactly by the adapter. Blank on a `pattern` row.
- `pattern`: an ordered regular-expression rule instead of a code (MN, OR rolls whose labels vary by county).
  The adapter tries rules top to bottom and keeps the first match.
- `county`: the rule applies only in this county (`*` or blank: every county). The adapter says whether it
  holds a county name or GEOID.
- `refine_by_units` (`yes`/`no`), `confidence`, `applied` (`yes`/`no`): read by the adapters that use them.

**Building type** (`<st>_*_permit_types.csv`, `nc_gso_occupancy.csv`, `tx_fw_use.csv`, ...):

    field,code,description,building_type_std,role,derived_units,notes,source_url

- `code`: the permit's type, occupancy or use value. A code over two source fields joins them with `|`, and
  `field` names both the same way (Fort Worth: `Permit_Type|Use_Type`).
- `role`: what the permit does, in the adapter's own terms (dwelling, multi, adu, demolition, accessory, ...).
- `derived_units`: units to record when the source gives none; blank = none derived.

Every other file in the folder is an aliases file (`<st>_aliases.csv`, `lotline.geo.aliases`) or a registry,
a table of a state's counties or places with their own columns (`nc_land_use_counties.csv`,
`mn_mngeo_counties.csv`, `nc_land_use_wake_jurisdictions.csv`), or a one-off input listed in
`docs/adding_a_state.md`.
"""

from __future__ import annotations

import csv
from pathlib import Path

from lotline.schemas import BUILDING_TYPES, LAND_USES

LAND_USE = ("field", "code", "description", "land_use_std", "notes", "source_url")
LAND_USE_OPTIONAL = ("pattern", "county", "refine_by_units", "confidence", "applied")
BUILDING_TYPE = (
    "field",
    "code",
    "description",
    "building_type_std",
    "role",
    "derived_units",
    "notes",
    "source_url",
)

KINDS = {
    "land_use": (LAND_USE, LAND_USE_OPTIONAL, "land_use_std", LAND_USES),
    "building_type": (BUILDING_TYPE, (), "building_type_std", BUILDING_TYPES),
}


class CrosswalkError(ValueError):
    """A crosswalk file does not follow its format."""


def read(path: Path, kind: str) -> list[dict[str, str]]:
    """Rows of a crosswalk, in file order, after checking the header and the vocabulary.

    The header must start with the kind's required columns, in order; anything after them must be one of the
    kind's optional columns. Each row's standard value must be in the schema's vocabulary. A blank code is a
    value like any other (a blank source field); a `pattern` row leaves it blank.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}")
    required, optional, std, vocab = KINDS[kind]
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = tuple(reader.fieldnames or ())
        rows = list(reader)
    if header[: len(required)] != required:
        raise CrosswalkError(f"{path.name}: header must start {','.join(required)}; got {','.join(header)}")
    extra = set(header[len(required) :]) - set(optional)
    if extra:
        raise CrosswalkError(f"{path.name}: unknown columns {sorted(extra)} (allowed extras: {optional})")
    for i, r in enumerate(rows, start=2):
        if r[std].strip() not in vocab:
            raise CrosswalkError(f"{path.name}:{i}: {std} {r[std]!r} is not in the schema vocabulary")
    return rows


def by_code(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """code -> row (a later row with the same code wins, as a dict built from the rows would)."""
    return {r["code"]: r for r in rows}
