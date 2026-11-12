"""D-082 (proposed): standards events, the level component, challengers C1, C3, C4 and §5's choosing rule do
what the analysis plan says (hand-worked examples and simulated places; no real data)."""

import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from lotline.config import CONFIG_DIR, load_params
from lotline.model import calibrate_mm as cal
from lotline.model import rule_tags
from lotline.model.scenarios import adu

COLUMNS = list(pd.read_csv(CONFIG_DIR / "reforms" / "mn.csv", nrows=0).columns)


def _rules(*rows: dict) -> pd.DataFrame:
    df = pd.DataFrame([{c: r.get(c, np.nan) for c in COLUMNS} for r in rows], columns=COLUMNS)
    for col in ("announced_date", "adoption_date", "effective_date", "end_date"):
        df[col] = pd.to_datetime(df[col])
    df["jurisdiction_geoid"] = df["jurisdiction_geoid"].astype(str)
    return df


def _row(rid, effective, cap, notes="", **kw):
    return {"reform_id": rid, "state": "TX", "jurisdiction_geoid": "1", "theme": "missing_middle",
            "status": "in_force", "adoption_date": effective, "effective_date": effective, "unit_cap": cap,
            "coding_notes": notes, **kw}  # fmt: skip


def _houston_like(tag="[standards] "):
    return rule_tags.apply(
        _rules(
            _row("pre", "2010-01-01", 2, "[predates] duplex is single-family"),
            _row("mur", "2023-11-27", 4, f"{tag}optional MUR route"),
        )
    )


COV = {"pre": 1.0, "mur": 1.0}


# ---------------------------------------------------------------------------------------------------------
# Dose class S (§1b)
# ---------------------------------------------------------------------------------------------------------


def test_standards_classes_by_hand():
    assert cal.standards_classes(2, 4) == ("bldgs_3_4",)  # Houston's MUR
    assert cal.standards_classes(1, 2) == ("bldgs_2",)
    assert cal.standards_classes(4, 4) == ("bldgs_2", "bldgs_3_4")  # the cap doesn't rise: all it covers
    assert cal.standards_classes(2, 2) == ("bldgs_2",)


def test_classify_event_by_hand():
    r = _houston_like()
    assert cal.standards_year(r) == 2024
    e = cal.classify_event(r, 2024, COV)
    assert e == cal.Event(2024, 2, 4, "S")
    assert e.classes == ("bldgs_3_4",)
    plain = cal.classify_event(_houston_like(tag=""), 2024, COV)
    assert plain == cal.Event(2024, 2, 4, "cap") and plain.classes == ("bldgs_3_4",)
    assert np.isnan(cal.standards_year(_houston_like(tag="")))
    assert cal.classify_event(r, 2023, COV) is None  # nothing new on 1 July 2023
    capless = rule_tags.apply(_rules(_row("ld", "2022-06-30", np.nan)))
    assert cal.classify_event(capless, 2023, {"ld": 1.0}) is None


def test_houston_row_is_tagged_standards_in_config():
    tx = adu.load_reforms("TX")
    h = tx[tx["jurisdiction_geoid"].astype(str) == "4835000"]
    h = rule_tags.apply(h[(h["theme"] == "missing_middle") & (h["status"] == "in_force")])
    assert rule_tags.flags(h).loc[h["reform_id"] == "TX-4835000-missing_middle-2023", "standards"].all()
    cov = {rid: 1.0 for rid in h["reform_id"]}
    e = cal.classify_event(h, int(cal.standards_year(h)), cov)
    assert e.dose_class == "S" and e.prior_cap == 2 and e.classes == ("bldgs_3_4",)


def _panel():
    rows = []
    for gid in ("a", "s"):
        for yr in range(2018, 2026):
            rows.append(dict(place=gid, name=gid, state="TX", status="treated", year=yr, T=1990.0,
                             y_buildings=3.0, eligible=1000.0, dose=0.3 if yr < 2024 else 0.9, pcr=1.15,
                             units_1=50.0, units_5p=5.0))  # fmt: skip
    return pd.DataFrame(rows)


def _classes(places=("a", "s")):
    idx = pd.MultiIndex.from_product([list(places), range(2018, 2026)], names=["geoid", "year"])
    return pd.DataFrame({"bldgs_2": 5.0, "bldgs_3_4": 1.0}, index=idx)


def test_retarget_events_s_dose_and_cap_unchanged():
    ev = {"a": cal.Event(2024, 2, 4, "cap"), "s": cal.Event(2024, 2, 4, "S")}
    r = cal.retarget_events(_panel(), _classes(), ev)
    s = r[r["place"] == "s"].set_index("year")
    assert (s.loc[:2023, "dose"] == 0).all() and np.allclose(s.loc[2024:, "dose"], 1 / 3)
    assert (s["y_buildings"] == 1.0).all() and (s["T"] == 2024).all()
    a = r[r["place"] == "a"].reset_index(drop=True)
    old = cal.retarget(_panel(), _classes(), {"a": (2024, 2)}).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, old)  # a cap event is exactly D-042's
    ev_x, d = cal.standards_variant(ev, "exclude")
    assert set(ev_x) == {"a"} and d == pytest.approx(1 / 3)
    ev_1, d1 = cal.standards_variant(ev, "dose1")
    r1 = cal.retarget_events(_panel(), _classes(), ev_1, d1)
    assert (r1.loc[(r1["place"] == "s") & (r1["year"] >= 2024), "dose"] == 1.0).all()
    with pytest.raises(ValueError):
        cal.standards_variant(ev, "half")


def test_config_constants_match_the_code():
    p = load_params("mm")
    assert p["mm_standards_dose_increase"].value == pytest.approx(cal.S_DOSE, abs=1e-4)
    assert p["mm_standards_dose_increase"].high == 1.0
    assert p["mm_level_pool_min_places"].value == cal.LEVEL_POOL_MIN
    assert p["mm_level_prior_widening"].value == cal.C4_WIDENING
    assert p["mm_challenger_se_margin"].value == cal.SE_MARGIN


# ---------------------------------------------------------------------------------------------------------
# Level component L (§1b)
# ---------------------------------------------------------------------------------------------------------


def _none_rows():
    rows = [("A", 2, "n1", 2.0), ("A", 2, "n2", 0.0), ("B", 2, "n3", 4.0)]
    rows += [("A", 3, f"m{i}", 1.0) for i in range(3)]
    return pd.DataFrame(
        [{"state": s, "band": b, "place": p, "year": 2020, "y_buildings": y, "eligible": 1000.0}
         for s, b, p, y in rows]
    )  # fmt: skip


def test_level_rate_pools_thin_bands_by_hand():
    assert cal.level_rate(_none_rows(), "A", 2) == {"rate": pytest.approx(0.002), "pool": "band", "places": 3}
    assert cal.level_rate(_none_rows(), "A", 3) == {
        "rate": pytest.approx(0.001),
        "pool": "state_band",
        "places": 3,
    }
    # no band-1 place anywhere: every none place, (2 + 0 + 4 + 3) / 6,000
    assert cal.level_rate(_none_rows(), "A", 1) == {"rate": pytest.approx(0.0015), "pool": "all", "places": 6}


def test_level_places_by_hand():
    panel = pd.DataFrame(
        [{"place": "L", "name": "L", "state": "A", "band": 3, "year": y, "y_buildings": 4.0,
          "eligible": 2000.0, "dose": 1 / 3, "pcr": 1.15} for y in (2019, 2020, 2021)]
    )  # fmt: skip
    (p,) = cal.level_places(panel, ["L"], _none_rows(), 0.15, 0.5, years=range(2020, 2022))
    assert list(p.years) == [2020, 2021]
    assert p.B == pytest.approx([2.0, 2.0])  # 0.001 × 2,000
    assert p.kr[0] == pytest.approx(2000 / 3 * 0.5 / 0.38993, rel=1e-4)
    assert p.k(0.5)[0] == pytest.approx(p.kr[0])  # mature: no ramp at any half-way point
    assert p.k(6.0)[0] == pytest.approx(p.kr[0])
    zero = panel.assign(dose=0.0)
    assert cal.level_places(zero, ["L"], _none_rows(), 0.15, 0.5, years=range(2020, 2022)) == []


def test_fit_level_recovers_a_known_level():
    rng = np.random.default_rng(4)
    theta, alpha = 0.003, 0.4
    places = []
    for i in range(60):
        yrs = np.arange(2016, 2026)
        E = np.full(len(yrs), float(rng.integers(2000, 15000)))
        p = cal.Place(str(i), str(i), 2016, 0.0005, yrs, np.zeros(10), E, E * 0.5,
                      np.full(10, cal.LEVEL_AGE), E)  # fmt: skip
        u = rng.gamma(1 / alpha, alpha)
        places.append(replace(p, y=rng.poisson(p.B + theta * u * p.kr).astype(float)))
    f = cal.fit_level(places)
    assert f.low < theta < f.high
    assert f.alpha_low < alpha < f.alpha_high


def test_level_prior_and_log_prior_term_by_hand():
    lf = cal.Fit(0.001, 0.0005, 0.002, 1.0, 0.5, 2.0, 0.5, 0.5, 0.5, 0.0, 1, 1, {})
    m, sd = cal.level_prior(lf)
    assert m == pytest.approx(math.log(0.001))
    assert sd == pytest.approx(2 * math.log(4) / (2 * cal.Z_95))  # 0.8427
    assert cal.log_prior_term(math.log(0.001 * math.e), (math.log(0.001), 0.5)) == pytest.approx(-2.0)
    assert cal.log_prior_term(1.0, None) == 0.0


def _sim_events(n=6, seed=5, theta=0.002):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        yrs = np.arange(2020, 2024)
        kr = np.full(4, 5000.0)
        p = cal.Place(str(i), str(i), 2020, 1.0, yrs, np.zeros(4), np.ones(4), kr, yrs - 2020 + 0.5, kr)
        out.append(replace(p, y=rng.poisson(p.B + theta * p.k(0.5)).astype(float)))
    return out


def test_c4_prior_pulls_theta_toward_the_level():
    ps = _sim_events()
    plain = cal.fit(ps, halves=(0.5,))
    assert cal.fit(ps, halves=(0.5,), log_prior=None) == plain
    tight = cal.fit(ps, halves=(0.5,), log_prior=(math.log(0.02), 0.01))  # a 10x prior, nearly fixed
    assert tight.theta == pytest.approx(0.02, rel=0.05)
    loose = cal.fit(ps, halves=(0.5,), log_prior=(math.log(0.02), 1.0))
    assert plain.theta < loose.theta < 0.02


# ---------------------------------------------------------------------------------------------------------
# C1 and C3 (§5)
# ---------------------------------------------------------------------------------------------------------


def test_not_yet_treated_series_by_hand():
    panel = pd.DataFrame(
        [{"place": p, "state": "OR", "year": y, "eligible": 1000.0} for p in ("a", "b") for y in (2021, 2022)]
        + [{"place": "x", "state": "OR", "year": 2021, "eligible": 1000.0}]
    )  # fmt: skip
    idx = pd.MultiIndex.from_tuples([("a", 2021), ("a", 2022), ("b", 2021), ("b", 2022), ("x", 2021)],
                                    names=["geoid", "year"])  # fmt: skip
    classes = pd.DataFrame({"bldgs_2": [4.0, 9.0, 2.0, 3.0, 50.0], "bldgs_3_4": 0.0}, index=idx)
    s = cal.not_yet_treated_series(
        panel, classes, ["bldgs_2"], {"a": 2022.0, "b": np.nan}, "OR", exclude=["x"]
    )
    assert s == {2021: pytest.approx(0.003), 2022: pytest.approx(0.003)}  # a leaves in 2022
    assert cal.growth_index(s, 2022, [2021]) == pytest.approx(1.0)


def test_conditional_z_centres_on_the_fit_set():
    z = cal.conditional_z({"a": 0.0, "b": math.e - 1, "c": math.e**2 - 1, "d": np.nan}, ["a", "b"])
    assert z == {"a": pytest.approx(-0.5), "b": pytest.approx(0.5), "c": pytest.approx(1.5), "d": 0.0}


# ---------------------------------------------------------------------------------------------------------
# §5's choosing rule
# ---------------------------------------------------------------------------------------------------------


def test_select_model_by_hand():
    scores = pd.DataFrame({"ls_M": [0.0, 0.0, 0.0], "ls_C1": [1.0, 2.0, 3.0], "ls_C3": [5.0, -1.0, 2.0],
                           "ls_C4": [3.0, 3.5, 4.0]})  # fmt: skip
    out = cal.select_model(scores, {"M": 2, "C1": 2, "C3": 3, "C4": 1})
    t = out["table"].set_index("model")
    assert t.loc["C1", "delta"] == 6.0 and t.loc["C1", "paired_se"] == pytest.approx(math.sqrt(3))
    assert t.loc["C1", "beats_by_margin"] and t.loc["C1", "replaces"]
    assert not t.loc["C3", "beats_by_margin"]  # Σ 6, SE 3 × √3 = 5.2: under 2 SE
    assert t.loc["C4", "beats_by_margin"] and not t.loc["C4", "replaces"]  # passes fewer tests
    assert out["chosen"] == "C1"
    none = cal.select_model(scores, {"M": 3, "C1": 2, "C3": 3, "C4": 1})
    assert none["chosen"] == "M"  # C1 beats M but passes fewer of A-C
    both = cal.select_model(scores, {"M": 1, "C1": 1, "C4": 1})
    assert both["chosen"] == "C4"  # both qualify: the larger Σ (10.5) wins


def test_first_event_scans_to_the_first_cap_rise():
    bend = rule_tags.apply(
        _rules(
            _row("pre", "2019-09-11", 3, "[predates] existing table rows"),
            _row("r16", "2016-12-06", 3),
            _row("r21", "2021-11-05", 4),
        )
    )
    cov = {"pre": 1.0, "r16": 1.0, "r21": 1.0}
    ev, misses = cal.first_event(bend, 2017, cov)
    assert ev == cal.Event(2022, 3, 4, "cap") and ev.classes == ("bldgs_3_4",)
    assert misses == [(2017, 3, 3)]
    ev, misses = cal.first_event(bend.iloc[[0, 1]], 2017, cov)
    assert ev is None and misses == [(2017, 3, 3)]
    assert cal.first_event(bend, np.nan, cov) == (None, [])
    assert cal.first_event(_houston_like(), 2024, COV)[0].dose_class == "S"
