"""The ADU anchor's fit set (D-079, D-084, D-088, D-096), in library code for `lotline calibrate`.

These builders used to live only in development scripts that loaded one another by file path
(`adu_mx_grid` → `adu_types_refit` → `adu_trend_refit` → `adu_owner_refit` → `adu_joint_refit`), with
`adu_refit_fixed_rows.py` wrapping two of them to cut `UNKNOWN-PLACEHOLDER` years. They are moved here
unchanged in what they compute; the scripts now import them.

- `fit_set` / `all_places` (D-079): every place with a coded ADU rule in force, eligible lots and ADU-flagged
  permits, 2016-2025, from D-053's places plus any place with 1,000+ permits in one ADU-flagging permit
  source. St. Paul never enters. Austin stops at 2023 and San Antonio starts in 2021 (`YEAR_LIMITS`).
- `unknown_years` (D-096): place-years under a rule row marked `UNKNOWN-PLACEHOLDER` are left out.
- `owner_table` / `age_table` (D-084, D-083): a place's owner-occupied share (ACS B25003) or pre-1960 share
  (B25034), by the order of sources in `share_rows`.
- `d096_places`: the D-096/D-097 inputs (fit set, unknown years cut, owner z, merged place types), as the
  joint fit, the m_x grid, the calibration range and D-099 read them.
- `slope_places`: the same fit set built with the transport at other parameter values, typed by D-088's
  merge over the central fit places, as the anchor slopes (D-030) read them.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.calibrate.adu import adu_terms as at
from lotline.calibrate.adu import calibrate_adu as cal
from lotline.calibrate.adu import estimate_adu
from lotline.calibrate.adu import joint_refit as jr
from lotline.config import CONFIG_DIR, load_params
from lotline.model import adu_owner as ao
from lotline.model import adu_types as ty
from lotline.model import undercount as uc
from lotline.model.scenarios import adu
from lotline.validation import holdout

STATES = ("MN", "NC", "OH", "TX", "OR")
WINDOW = range(2016, 2026)
ST_PAUL, ROCHESTER = "2758000", "2754880"
MIN_PERMITS = 1000  # D-074 step 2
YEAR_LIMITS = {
    "4805000": (2016, 2023),
    "4865000": (2021, 2025),
}  # Austin's R-102 flag stops; San Antonio's file starts
# D-053's fit set (D-039's four states plus Portland and Bend): the places that are not "new" for test A.
D053 = {
    "TX": {"4805000", "4865000"},
    "NC": {"3743480", "3741960", "3714700", "3733120", "3728000", "37063"},
    "OH": {"3915000"},
    "OR": {"4159000", "4105800"},
}
PLACEHOLDER = "UNKNOWN-PLACEHOLDER"
LATEST = 2024  # the newest ACS 5-year vintage ending at or before the 2025 data origin
SENS_END = 2020  # D-084 sensitivity: the 2016-20 vintage
OLD_HOMES = ("1950 to 1959", "1940 to 1949", "1939 or earlier")
ROLLS = CONFIG_DIR / "validation" / "adu_roll_counts.csv"


# ---------------------------------------------------------------------------------------------------------
# The fit set (D-079)
# ---------------------------------------------------------------------------------------------------------


def d053_places(st: str, reforms: pd.DataFrame | None = None) -> set[str]:
    """D-053's places in a state. Minnesota: every coded place but St. Paul and Rochester (whose permit source
    came after D-053, #367: D-053's MN fit held 42 places)."""
    if st == "MN":
        r = adu.load_reforms("MN") if reforms is None else reforms
        return set(r.loc[r["theme"] == "adu", "jurisdiction_geoid"].astype(str)) - {ST_PAUL, ROCHESTER}
    return set(D053.get(st, set()))


def big_sources(permits: pd.DataFrame, min_permits: int = MIN_PERMITS) -> set[str]:
    """Places with `min_permits`+ permits (of any kind) in one ADU-flagging permit source. By hand: source S
    flags ADUs and holds 1,000 rows for place A and 999 for B -> {A}; a source that flags none counts for
    nobody."""
    flagging = permits.loc[adu._is_adu(permits), "source"].unique()
    q = permits[permits["source"].isin(flagging) & permits["jurisdiction_geoid"].notna()]
    n = q.groupby(["jurisdiction_geoid", "source"]).size()
    return {str(g) for (g, _), v in n.items() if v >= min_permits}


def candidates(st: str, store) -> tuple[list[str], set[str]]:
    """(candidate GEOIDs, D-053 places): D-053 places plus `big_sources` over fit-eligible sources."""
    p = cal.drop_sources(store.read(st, "permits"), [(s, None, None) for s in uc.out_of_fit()])
    old = d053_places(st)
    return sorted((big_sources(p) | old) - {ST_PAUL}), old


def unknown_years(states=adu.REFORM_STATES, load=adu.load_reforms) -> dict[str, set[int]]:
    """{geoid: years} under an ADU rule row marked `UNKNOWN-PLACEHOLDER` (D-096): from its effective year to
    the year of the day before its end date. By hand: effective 2016-01-01, end 2023-01-01 -> 2016-2022; no
    end date -> to 2100."""
    out: dict[str, set[int]] = {}
    for st in states:
        r = load(st)
        r = r[(r["theme"] == "adu") & r["coding_notes"].fillna("").str.contains(PLACEHOLDER)]
        for row in r.itertuples():
            y0 = pd.Timestamp(row.effective_date).year
            end = pd.Timestamp(row.end_date) if pd.notna(row.end_date) else pd.Timestamp("2100-01-01")
            y1 = (end - pd.Timedelta(days=1)).year
            out.setdefault(str(row.jurisdiction_geoid), set()).update(range(y0, y1 + 1))
    return out


def limit_years(pl: cal.PlaceData | None, unknown: Mapping[str, set[int]] | None = None):
    """The place on its own fit years (`YEAR_LIMITS`, else `WINDOW`), less its `unknown` years; None if none
    are left. By hand: Austin 2016-2025 -> 2016-2023; a place with 2018 and 2019 unknown -> those cut."""
    if pl is None:
        return None
    lo, hi = YEAR_LIMITS.get(pl.geoid, (min(WINDOW), max(WINDOW)))
    pl = jr.subset_years(pl, range(lo, hi + 1))
    gone = (unknown or {}).get(pl.geoid) if pl is not None else None
    if gone:
        pl = jr.subset_years(pl, [y for y in pl.years if int(y) not in gone])
    return pl


def fit_set(st: str, store, undercount="table", drop=(), unknown=None, params=None):
    """(places, new GEOIDs): the state's fit places (`candidates`, `limit_years`) and those not in D-053."""
    geoids, old = candidates(st, store)
    pls = cal.place_data(
        st,
        store,
        geoids,
        WINDOW,
        params=params,
        counts=cal.count_settings(),
        undercount=undercount,
        drop=drop,
    )
    pls = [q for q in (limit_years(pl, unknown) for pl in pls) if q is not None and q.geoid != ST_PAUL]
    return pls, {pl.geoid for pl in pls if pl.geoid not in old}


def all_places(store, undercount="table", drop=(), unknown=None, params=None):
    """`fit_set` over the five states, in `STATES` order."""
    out, new = [], set()
    for st in STATES:
        pls, nw = fit_set(st, store, undercount, drop, unknown, params)
        out += pls
        new |= nw
    return out, new


def acs_lots(st: str, store, pl: cal.PlaceData) -> np.ndarray:
    """Tier 0's lots (D-075): ACS one-unit detached homes (`eligible.from_acs`, remainders permit-level) each
    fit year, the newest vintage <= the year, else the earliest later one."""
    juris = store.read(st, "jurisdictions")
    rows = estimate_adu.permit_acs_rows(st, store, juris)
    rows = rows[(rows["theme"] == "adu") & (rows["jurisdiction_geoid"] == pl.geoid)]
    if rows.empty:
        raise ValueError(f"{pl.name}: no ACS lots")
    out = []
    for y in pl.years:
        r = rows.assign(after=rows["year"] > y, gap=(rows["year"] - y).abs()).sort_values(["after", "gap"])
        out.append(float(r["eligible_parcels"].iloc[0]))
    return np.asarray(out)


# ---------------------------------------------------------------------------------------------------------
# Owner share (D-084) and housing age (D-083)
# ---------------------------------------------------------------------------------------------------------


def _part_total(a: pd.DataFrame, part: pd.Series, total: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "owner": a[part].groupby(["geo", "end_year"])["estimate"].sum(),
            "total": a[total].groupby(["geo", "end_year"])["estimate"].sum(),
        }
    ).dropna()


def b25003(acs_geo_year: pd.DataFrame) -> pd.DataFrame:
    """Owner-occupied (`owner`) and occupied homes (`total`) per (geo, end_year)."""
    a = acs_geo_year[acs_geo_year["table_id"] == "B25003"]
    v = a["variable"].astype(str)
    return _part_total(a, v == "B25003_002", v == "B25003_001")


def b25034(acs_geo_year: pd.DataFrame) -> pd.DataFrame:
    """Units built before 1960 (named `owner`, so `share_rows` reads it) and all units per (geo, end_year)."""
    a = acs_geo_year[acs_geo_year["table_id"] == "B25034"]
    lab = a["label"].astype(str).str.replace(":", "", regex=False).str.strip().str.lower()
    old = lab.map(lambda s: any(k in s for k in OLD_HOMES))
    return _part_total(a, old, lab.isin(["total", "estimate!!total"]))


def share_rows(geoid: str, kind: str, county: str, acs: pd.DataFrame, juris: pd.DataFrame):
    """({end_year: share}, source) for one jurisdiction, by D-084's order of sources: a place reads its place
    rows, a Minnesota township its county-subdivision rows, an unincorporated county area its county's rows
    less the places in that county; otherwise none."""

    def shares(frame: pd.DataFrame) -> dict[int, float]:
        f = frame[frame["total"] > 0]
        return {int(y): float(o / t) for y, o, t in zip(f.index, f["owner"], f["total"], strict=True)}

    def at_geo(geo: str) -> pd.DataFrame:
        return acs.xs(geo, level="geo") if geo in acs.index.get_level_values("geo") else acs.iloc[:0]

    if kind == "place" and not at_geo(f"place:{geoid}").empty:
        return shares(at_geo(f"place:{geoid}")), "place"
    if kind == "township" and not at_geo(f"cousub:{geoid}").empty:
        return shares(at_geo(f"cousub:{geoid}")), "county subdivision"
    if kind == "county_unincorporated" and not at_geo(f"county:{county}").empty:
        inside = juris[(juris["county_geoid"].astype(str) == county) & (juris["kind"] == "place")]
        rest = at_geo(f"county:{county}").copy()
        for g in inside["geoid"].astype(str):
            p = at_geo(f"place:{g}")
            rest = rest.sub(p.reindex(rest.index).fillna(0.0))
        return shares(rest), "county less its places"
    return {}, "none"


def _share_table(store, items, reader, z_of, vintages, flag: str) -> pd.DataFrame:
    rows = []
    for st in sorted({s for s, _, _ in items}):
        acs = reader(holdout.apply_acs(store.read(st, "acs_geo_year"), st))
        juris = store.read(st, "jurisdictions")
        info = juris.set_index(juris["geoid"].astype(str))
        for s, g, name in items:
            if s != st:
                continue
            kind = str(info.at[g, "kind"]) if g in info.index else "place"
            county = str(info.at[g, "county_geoid"]) if g in info.index else ""
            by_year, source = share_rows(g, kind, county, acs, juris)
            row = {"state": st, "geoid": g, "name": name, "kind": kind, "source": source}
            for tag, end in vintages:
                share, year = ao.vintage_share(by_year, end)
                row[f"share_{tag}"], row[f"vintage_{tag}"] = share, year
                row[f"z_{tag}"] = 0.0 if share is None else z_of(share)
            row["flag"] = flag if row["share_fit"] is None else ""
            rows.append(row)
    return pd.DataFrame(rows)


def owner_table(store, items: list[tuple[str, str, str]]) -> pd.DataFrame:
    """One row per (state, geoid, name): owner share and vintage at the fit end year, the latest and the
    sensitivity vintage, and each one's z (`adu_owner.owner_z`, adu_owner.yaml's center and scale)."""
    p = {k: v.value for k, v in load_params("adu_owner").items()}
    center, scale, fit_end = (
        p["adu_owner_share_center"],
        p["adu_owner_share_scale"],
        int(p["adu_owner_fit_end_year"]),
    )
    vintages = (("fit", fit_end), ("latest", LATEST), ("sens", SENS_END))
    return _share_table(
        store, items, b25003, lambda s: ao.owner_z(s, center, scale), vintages, "no owner share: z = 0"
    )


def age_table(store, items: list[tuple[str, str, str]]) -> pd.DataFrame:
    """As `owner_table`, for the pre-1960 share (`adu_terms.age_share_z`, adu_age.yaml's center and scale)."""
    pa = {k: v.value for k, v in load_params("adu_age").items()}
    fit_end = int(load_params("adu_owner")["adu_owner_fit_end_year"].value)
    center, scale = pa["adu_age_share_center"], pa["adu_age_share_scale"]
    vintages = (("fit", fit_end), ("latest", LATEST))
    return _share_table(
        store, items, b25034, lambda s: at.age_share_z(s, center, scale), vintages, "no housing age: z = 0"
    )


def roll_towns(path=ROLLS) -> pd.DataFrame:
    """The roll-check towns (test B): rows of config/validation/adu_roll_counts.csv that do not set k."""
    r = pd.read_csv(path, dtype={"geoid": str})
    return r[~r["sets_k"]]


def owner_inputs(store, unknown=None):
    """(fit places, new GEOIDs, owner table over the fit places and the roll-check towns): D-084's inputs."""
    places, new = all_places(store, unknown=unknown)
    items = [(p.state, p.geoid, p.name) for p in places] + [
        (r.state, r.geoid, r.name) for r in roll_towns().itertuples()
    ]
    return places, new, owner_table(store, list(dict.fromkeys(items)))


# ---------------------------------------------------------------------------------------------------------
# Place types (D-088) and the D-096 inputs
# ---------------------------------------------------------------------------------------------------------


def type_table(store, states=STATES) -> pd.DataFrame:
    """Every jurisdiction's units and raw type (`adu_types.raw_types`): only Census places can be a core
    city; townships and unincorporated county areas in a metro are suburbs."""
    out = []
    for st in states:
        u = ty.units_table(store, st.lower())
        u["type_raw"] = u["geoid"].astype(str).map(ty.raw_types(u))
        out.append(u)
    return pd.concat(out, ignore_index=True)


def attach(places, types: Mapping[str, str], terms=ty.TERMS):
    """Each place with its type indicators (a place with no type is the reference type, a suburb)."""
    return [ty.with_types(p, ty.indicators(types.get(p.geoid, ty.REFERENCE), terms)) for p in places]


def d096_places(store, unknown=None):
    """The D-096/D-097 inputs: the fit set with unknown years cut (`unknown_years` when not given), each place
    carrying its owner z and its type, small types merged over the fit places (`adu_types.merge_small`)."""
    unknown = unknown_years() if unknown is None else unknown
    pls, _new, own = owner_inputs(store, unknown)
    z = dict(zip(own["geoid"], own["z_fit"], strict=True))
    tt = type_table(store)
    ids = {p.geoid for p in pls}
    ft = tt[tt["geoid"].isin(ids)][["state", "geoid", "type_raw"]].rename(columns={"type_raw": "type"})
    mapping, _ = ty.merge_small(ft)
    tt["type"] = tt["type_raw"].map(mapping)
    return attach([ao.with_z(p, z[p.geoid]) for p in pls], dict(zip(tt["geoid"], tt["type"], strict=True)))


def slope_types(store, central_places) -> dict[str, str]:
    """Raw types for every jurisdiction (`adu_types.jurisdiction_types`), merged by D-088's rule over the
    central fit places, as the anchor slopes read them."""
    raw = pd.concat([ty.jurisdiction_types(store, st) for st in STATES])
    fit_t = pd.DataFrame(
        [{"state": p.state, "geoid": p.geoid, "type": raw.get(p.geoid)} for p in central_places]
    )
    mapping, _ = ty.merge_small(fit_t)
    return {g: mapping[t] for g, t in raw.items()}


def slope_places(store, params=None, unknown=None):
    """The anchor slopes' fit places (D-030 on D-088's set): `all_places` with the transport at `params`
    (None: central), unknown years cut, no owner z attached."""
    unknown = unknown_years() if unknown is None else unknown
    return all_places(store, unknown=unknown, params=params)[0]


def typed(places, types: Mapping[str, str]):
    """(places with type indicators, the design matrix of the type columns some place has)."""
    pz = attach(places, types)
    dmat = np.array([ty.type_d(p) for p in pz])
    return pz, dmat[:, [j for j in range(dmat.shape[1]) if dmat[:, j].any()]]
