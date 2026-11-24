# ruff: noqa: E501  (plain-language strings and notes)
"""Fee component from what a fee pays for (LESSONS T1), with the fee's name as a cross-check.

Names mislead: a Texas "water impact fee" pays for water capacity (`water_sewer`), an Oregon parks SDC is an
`impact` fee, and Met Council SAC is `water_sewer`. The coder states `pays_for` with its quote; this module
maps it. `name_hint` reads only the name; when the two disagree the item is flagged, never overridden.
"""

from __future__ import annotations

import re

PAYS_FOR = {
    "water_sewer": {"water", "sewer", "wastewater", "reuse", "water_sewer", "tap", "meter"},
    "impact": {
        "parks",
        "open_space",
        "transportation",
        "streets",
        "schools",
        "fire",
        "police",
        "library",
        "stormwater",
        "general_capacity",
    },
    "permit": {
        "building_permit",
        "plan_review",
        "trade_permit",
        "inspection",
        "state_surcharge",
        "technology",
        "certificate_of_occupancy",
    },
    "planning": {"zoning", "rezoning", "subdivision", "site_plan", "conditional_use", "variance", "platting"},
}
_LOOKUP = {p: comp for comp, ps in PAYS_FOR.items() for p in ps}

# Name keywords in priority order: water/sewer words win ("Sewer permit fee" is water_sewer, as Columbus is coded)
_HINTS = [
    (
        "water_sewer",
        r"\b(water|sewer|wastewater|sanitary|SAC|WAC|tap|meter|capital recovery|capacity charge)\b",
    ),
    (
        "impact",
        r"\b(park|parkland|open space|thoroughfare|transportation|street|traffic|school|fire|police|"
        r"library|storm ?water|impact)\b",
    ),
    ("planning", r"\b(rezoning|zoning|subdivision|plat|site plan|conditional use|CUP|variance)\b"),
    (
        "permit",
        r"\b(permit|plan review|inspection|surcharge|plumbing|mechanical|electrical|technology|"
        r"certificate of occupancy)\b",
    ),
]


def component(pays_for: str) -> str:
    """`fees.fee_component` for a `pays_for` value; unknown values are `other`."""
    return _LOOKUP.get(pays_for.strip().lower().replace(" ", "_"), "other")


def name_hint(fee_type: str) -> str | None:
    """The component the fee's name suggests, or None when the name says nothing."""
    for comp, pattern in _HINTS:
        if re.search(pattern, fee_type, flags=re.IGNORECASE):
            return comp
    return None


def check(pays_for: str, fee_type: str) -> tuple[str, str | None]:
    """(component, flag). The flag explains a disagreement between purpose and name, else None."""
    comp = component(pays_for)
    hint = name_hint(fee_type)
    if hint is None or hint == comp:
        return comp, None
    # an "impact fee" that pays for water or sewer is water_sewer by design (T1): not a disagreement
    if comp == "water_sewer" and hint == "impact":
        return comp, None
    return comp, f"pays_for '{pays_for}' -> {comp}, but the name suggests {hint}"
