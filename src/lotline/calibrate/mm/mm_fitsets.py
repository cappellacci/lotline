"""Missing middle: the fit sets and panels behind each fitted parameter (calibration phase 3).

`calibrate_mm` holds the likelihoods and `mm_routes` the two-ramp fit. This module holds what
used to live only in `scripts/dev`: which places each fit uses, built from the D-024 panel and the coded rule
rows. `lotline.calibrate.mm_steps` calls it to re-derive the values in `config/params/mm_hazard.yaml`, and the
scripts in `scripts/dev` import it, so both build the same sets.

- **D-038 / D-042 lists** (`D038_PLACES`, `PREREGISTERED_D042`): the places named in advance.
- **Homes per building** (`units_per_building`, D-038): Census BPS 2-4 unit homes over buildings, 2016-2025,
  on D-038's named places; the range is the lowest and highest state ratio, Minnesota left out (10 buildings;
  Ben, 2026-11-08).
- **D-092 fit set** (`events_d092`, `build_m`): every place with a cap rise or standards event in 2013-2025,
  less the test places, the excluded places and the holdouts; M's own-growth baseline with D-058's zero floor
  (D-059 (b'), the "C0" baseline run 8 kept).
- **Level set** (`level_set`, D-092 §1b): always-allowed places with no event, and the coded "none" places
  that give each state and size band its no-rule level; C4's prior on θ comes from its fit.
- **Year-spread places** (`spread_ids`, `pseudo_places`, D-092 deviation (b)): uncoded places no fit or test
  uses, as no-reform pseudo-forecasts at origins 2016 and 2021.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

import pandas as pd

from lotline.calibrate.mm import calibrate_mm as cal

STATES = ("MN", "NC", "OH", "TX", "OR")  # D-092's five states
TESTS = {"2743000": "Minneapolis", "3719000": "Durham city", "37063": "Durham County", "3755000": "Raleigh"}
HOLDOUTS = {  # kept out of every D-092 fit, released or not (D-100 adds St. Paul back on purpose)
    "2758000": "St. Paul",
    "27123": "Ramsey County",
    "3712000": "Charlotte",
    "37119": "Mecklenburg County",
}
EXCLUDE = {  # out of the fit, the targets and the level set
    "4845000": "Lubbock",  # D-059: no usable source for its pre-UDC rule
    "2754214": "Richfield",  # D-092 §1b: no cap rise, and its effective date is unresolved
}
FIRST, LAST = 2013, 2025  # D-042's event window
LEVEL_YEARS = range(2016, 2026)  # the level model's years: the D-054 fit's outcome years
HORIZON = 5  # years a held-out place is scored over (D-054)

PREREGISTERED_D042 = frozenset({  # D-042's fit list, by short name
    "Wilson", "Morrisville", "Wake Forest", "Sanford", "Burlington", "Mooresville", "Garner", "League City",
    "Lewisville", "Lubbock", "Cincinnati", "Euclid", "Richfield", "St. Louis Park", "Austin", "Houston",
})  # fmt: skip
D038_PLACES = {  # D-038's sixteen named fit places, by state
    "NC": ("Wilson", "Morrisville", "Wake Forest", "Sanford", "Burlington", "Mooresville", "Garner"),
    "TX": ("League City", "Lewisville", "Austin", "Houston", "Lubbock"),
    "OH": ("Cincinnati", "Euclid"),
    "MN": ("Richfield", "St. Louis Park"),
}
UNITS_YEARS = range(2016, 2026)
UNITS_LEFT_OUT = ("MN",)  # 10 buildings; left out of the range by Ben, 2026-11-08

SPREAD_STATES = ("MN", "NC", "OH", "TX")  # Oregon out: HB 2001 reaches most places (D-037)
SPREAD_ORIGINS = (2016, 2021)
FRANKLIN = "39049"  # test C's Franklin County places


def short(name: str) -> str:
    """A place name without its Census suffix: "Wake Forest town" -> "Wake Forest"."""
    for suffix in (" city", " town", " village"):
        name = name.removesuffix(suffix)
    return name


def horizon(places: Iterable[cal.Place], years: int = HORIZON) -> list[cal.Place]:
    """Each place cut to its first `years` years from T (a held-out place's scored window)."""
    return [p.upto(p.T + years - 1) for p in places]


def params() -> dict:
    """The fixed inputs every D-092 fit reads from config."""
    from lotline.config import load_params

    pm = load_params("mm")
    return {
        "margin": load_params("proforma")["developer_margin"].value,
        "sigma": load_params("mm_hazard")["mm_feasibility_dispersion"].value,
        "s_dose": pm["mm_standards_dose_increase"].value,
        "s_dose_high": pm["mm_standards_dose_increase"].high,
        "pool_min": int(pm["mm_level_pool_min_places"].value),
        "widening": pm["mm_level_prior_widening"].value,
        "se_margin": pm["mm_challenger_se_margin"].value,
    }


# ---- homes per building (D-038) ------------------------------------------------------------------------


def named_geoids(jurisdictions: pd.DataFrame, names: Sequence[str]) -> dict[str, str]:
    """name -> geoid for incorporated places matched by short name; raises unless each matches exactly one."""
    places = jurisdictions[jurisdictions["kind"] == "place"]
    out = {}
    for n in names:
        hit = places[places["name"].map(short) == n]
        if len(hit) != 1:
            raise ValueError(f"{n}: {len(hit)} places match")
        out[n] = str(hit["geoid"].iloc[0])
    return out


def units_ratio(bps: pd.DataFrame, geoids: Iterable[str], years: Iterable[int] = UNITS_YEARS) -> tuple:
    """(homes, buildings) in 2-4 unit buildings for `geoids` over `years`, from a BPS place-year table."""
    b = bps[bps["geoid"].astype(str).isin(set(geoids)) & bps["year"].isin(list(years))]
    homes = float(b["units_2"].sum() + b["units_3_4"].sum())
    return homes, float(b["bldgs_2"].sum() + b["bldgs_3_4"].sum())


def units_per_building(by_state: Mapping[str, tuple[float, float]], left_out=UNITS_LEFT_OUT) -> dict:
    """value: pooled homes / buildings; low and high: the lowest and highest state ratio, `left_out` states
    excluded. By hand: NC (216, 106), OH (162, 59), MN (40, 10) -> 418 / 175 = 2.389; low 2.038, high
    2.746."""
    homes = sum(h for h, _ in by_state.values())
    bldgs = sum(b for _, b in by_state.values())
    ratios = [h / b for s, (h, b) in by_state.items() if s not in left_out and b > 0]
    return {"value": homes / bldgs, "low": min(ratios), "high": max(ratios)}


def d038_units(store) -> dict:
    """`units_per_building` on D-038's named places, from the stored jurisdictions and BPS tables."""
    by_state = {}
    for st, names in D038_PLACES.items():
        ids = named_geoids(store.read(st, "jurisdictions"), names)
        by_state[st] = units_ratio(store.read(st, "bps_place_year"), ids.values())
    return units_per_building(by_state)


# ---- the D-092 panel, events and fit set ---------------------------------------------------------------


def panel(store, include: Sequence[str] = ()) -> pd.DataFrame:
    """D-092's panel over its five states, every listed holdout dropped except `include` (D-100: St. Paul)."""
    from lotline.calibrate.mm import estimate_mm as mm

    data = mm.build_panel(store, states=STATES, include=tuple(include)).data
    return data[~data["place"].isin(set(HOLDOUTS) - set(include))]


def bps_classes(store, places: set[str], states: Sequence[str] = STATES) -> pd.DataFrame:
    """BPS buildings and homes by class, indexed (geoid, year), for `places` only."""
    cols = ["bldgs_2", "bldgs_3_4", "units_2", "units_3_4"]
    out = []
    for st in states:
        b = store.read(st, "bps_place_year")
        b = b[b["geoid"].isin(places)]
        out.append(b.groupby(["geoid", "year"])[cols].sum(min_count=1))
    return pd.concat(out).sort_index()


def rule_rows(store, states: Sequence[str] = STATES) -> dict:
    """Per state: raw in-force missing-middle rows, the same after `rule_tags.apply`, and their coverage."""
    from lotline.calibrate.mm import estimate_mm as mm
    from lotline.config import load_params
    from lotline.model import rule_tags
    from lotline.model.scenarios import adu

    pa = {k: v.value for k, v in load_params("adu").items()}
    out = {}
    for st in states:
        raw = adu.load_reforms(st)
        raw = raw[(raw["theme"] == "missing_middle") & (raw["status"] == "in_force")]
        applied = rule_tags.apply(raw)
        out[st] = {"raw": raw, "applied": applied, "cov": mm._mm_coverage(st, store, applied, pa)}
    return out


def events_d092(panel: pd.DataFrame, rules: Mapping) -> tuple[dict[str, cal.Event], dict]:
    """geoid -> Event for every panel place with a D-092 event in the window (the first cap rise or standards
    row at or after its first in-window dose change, `calibrate_mm.first_event`); and the places with a dose
    change but no event (geoid -> (year, prior cap, cap after) at that first change)."""
    events, no_event = {}, {}
    for st, d_st in panel.groupby("state"):
        r = rules[st]
        for g, d in d_st.groupby("place"):
            mine = r["applied"][r["applied"]["jurisdiction_geoid"].astype(str) == g]
            E = cal.event_year(d["T"].iloc[0], d.set_index("year")["dose"].to_dict(), FIRST, LAST)
            Es = cal.standards_year(mine, FIRST, LAST)
            cands = [x for x in (E, Es) if pd.notna(x)]
            if not cands:
                continue
            ev, misses = cal.first_event(mine, min(cands), r["cov"], LAST)
            if ev is None:
                no_event[g] = misses[0]
            else:
                events[g] = ev
    return events, no_event


def split_events(events: Mapping[str, cal.Event]) -> tuple[dict, dict]:
    """(fit events, test events): usable events (an outcome class) split into the fit set and the test places;
    excluded places are in neither."""
    usable = {g: e for g, e in events.items() if e.classes}
    fit = {g: e for g, e in usable.items() if g not in TESTS and g not in EXCLUDE}
    return fit, {g: e for g, e in usable.items() if g in TESTS}


def build_m(panel, classes, events, p: Mapping, s_dose: float):
    """M's places (D-059 (b'), run 8's C0 baseline): own-growth baseline, fixed window, zero floor; standards
    events at dose `s_dose`. Returns (places with no year noise, the retargeted panel)."""
    rp = cal.retarget_events(panel, classes, events, s_dose)
    return cal.place_inputs(rp, list(events), p["margin"], p["sigma"], growth="own", zero_floor=True), rp


def level_set(panel: pd.DataFrame, rules: Mapping, events: Mapping, p: Mapping) -> tuple[list, list, set]:
    """(level places, level geoids, "none" geoids): always-allowed places with no event, fitted on the level
    model against the no-rule level of coded "none" places in the same state and size band (D-092 §1b)."""
    from lotline.model import rule_tags

    ids = set(panel["place"])
    always = set().union(*(rule_tags.always_allowed_places(r["raw"]) for r in rules.values()))
    level_ids = sorted((always & ids) - set(events) - set(TESTS) - set(EXCLUDE) - set(HOLDOUTS))
    none_ids = set().union(*(rule_tags.none_places(r["raw"]) for r in rules.values()))
    none_ids = (none_ids & ids) - set(TESTS) - set(HOLDOUTS)
    none_rows = panel[panel["place"].isin(none_ids) & panel["year"].isin(LEVEL_YEARS)]
    lv = cal.level_places(panel, level_ids, none_rows, p["margin"], p["sigma"], LEVEL_YEARS, p["pool_min"])
    return lv, level_ids, none_ids


# ---- year spread (D-092 deviation (b)) -----------------------------------------------------------------


def spread_ids(panel: pd.DataFrame, rules: Mapping, franklin: set[str]) -> tuple[list[str], dict]:
    """The uncoded places φ is learned from, and how many each reason removed (reasons overlap): uncoded
    places of the four spread states, minus every place with an event or a dose, the test places, test C's
    places (coded "none", and Franklin County's `franklin`), the level set, the excluded places and
    holdouts."""
    from lotline.model import rule_tags

    events, _ = events_d092(panel, rules)
    none_ids = set().union(*(rule_tags.none_places(r["raw"]) for r in rules.values()))
    always = set().union(*(rule_tags.always_allowed_places(r["raw"]) for r in rules.values()))
    max_dose = panel.groupby("place")["dose"].max().fillna(0.0)
    status = panel.groupby("place")["status"].first()
    state = panel.groupby("place")["state"].first()
    pool = sorted(g for g in status.index if status[g] == "uncoded" and state[g] in SPREAD_STATES)
    drop = {
        "event": set(events),
        "dose": {g for g in pool if max_dose.get(g, 0.0) > 0},
        "tests": set(TESTS),
        "test_c": none_ids | set(franklin),
        "level_set": always,
        "excluded": set(EXCLUDE),
        "holdouts": set(HOLDOUTS),
    }
    removed = {k: len(set(pool) & v) for k, v in drop.items()}
    return [g for g in pool if not any(g in v for v in drop.values())], removed


def franklin_places(store) -> set[str]:
    oh = store.read("OH", "bps_place_year")
    return set(oh.loc[oh["county_geoid"].astype(str) == FRANKLIN, "geoid"].dropna().astype(str))


def pseudo_places(panel: pd.DataFrame, ids: Sequence[str], origin: int, p: Mapping) -> list[cal.Place]:
    """Test C's no-reform baseline at `origin` (own growth, zero floor, no reform term), scored over
    origin ... origin + 4."""
    sub = panel[panel["place"].isin(ids)].copy()
    sub["T"], sub["dose"] = float(origin), 0.0
    sub["eligible"] = sub["eligible"].where(sub["eligible"] > 0, 1.0)
    out = cal.place_inputs(sub, list(ids), p["margin"], p["sigma"], growth="own", zero_floor=True)
    return [q for q in (q.upto(origin + HORIZON - 1) for q in out) if len(q.years)]
