"""D-079 joint refit: hand-worked tests for the fit set's inputs, Form B's dose and events, the data tiers,
the scores and the pre-registered rules (claim rule, tests A-C, decision rule)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr
from lotline.model import undercount as uc
from lotline.model.scenarios import adu

# ---------------------------------------------------------------------------------------------------------
# place_years: k-scaled counts stay fractional; out-of-fit sources and dropped rows leave the fit
# ---------------------------------------------------------------------------------------------------------

GEO = "9900001"


def _store(permits: pd.DataFrame):
    from lotline.build import eligible

    tables = {
        "market_geo_year": pd.DataFrame(
            {
                "geo": ["national:US"] * 3,
                "year": [2023, 2024, 2025],
                "cpi_u": [100.0] * 3,
                "mortgage_rate": [6.0] * 3,
            }
        ),
        "acs_geo_year": pd.DataFrame(
            {
                "geo": [f"place:{GEO}"] * 2,
                "end_year": [2024, 2024],
                "variable": ["B25064_001", "B25077_001"],
                "estimate": [1500.0, 400_000.0],
            }
        ),
        "jurisdictions": pd.DataFrame({"geoid": [GEO], "name": ["Test city"], "kind": ["place"]}),
        "eligible_parcels": pd.DataFrame(
            {
                "jurisdiction_geoid": [GEO],
                "year": [2024],
                "theme": ["adu"],
                "rule_version": [eligible.RULE_VERSION],
                "eligible_parcels": [10_000],
            }
        ),
        "permits": permits,
    }

    class Store:
        def read(self, state, table):
            return tables[table]

    return Store()


def _permits(rows):
    """rows: (source, year, type)."""
    return pd.DataFrame(
        {
            "jurisdiction_geoid": [GEO] * len(rows),
            "source": [r[0] for r in rows],
            "issue_year": [r[1] for r in rows],
            "building_type_std": [r[2] for r in rows],
            "adu_type": [None] * len(rows),
            "parcel_id": [None] * len(rows),
        }
    )


@pytest.fixture
def one_rule(monkeypatch):
    reforms = pd.DataFrame(
        {
            "reform_id": ["T1"],
            "state": ["MN"],
            "jurisdiction_geoid": [GEO],
            "theme": ["adu"],
            "status": ["in_force"],
            "effective_date": pd.to_datetime(["2020-01-01"]),
            "end_date": pd.NaT,
            "supersedes": [None],
            "by_right": [True],
            "owner_occ": [False],
            "adu_detached_allowed": [True],
            "adu_max_sqft": [800.0],
            "parking": ["none"],
            "parking_min_per_unit": [0.0],
            "adus_per_lot": [1],
            "coverage": ["Citywide"],
        }
    )
    monkeypatch.setattr(adu, "load_reforms", lambda st: reforms if st == "MN" else reforms.iloc[0:0])


def _factors(source: str, k: float) -> uc.Factors:
    row = uc.Row(source, "x", "parser", k, k, k, None, None, None, False, False, False)
    return uc.Factors([row], [k])


def test_k_scaled_counts_are_not_truncated(one_rule):
    """D-078: k scales the count in the fit. A count of 1 with k = 0.78 is 0.78 and 3 with k = 1.07 is 3.21,
    not int() of them (0 and 3), which undid k on small counts."""
    p = _permits([("city", 2024, "ADU"), ("city", 2025, "ADU"), ("city", 2025, "ADU"), ("city", 2025, "ADU")])
    low = cal.place_years("MN", _store(p), [GEO], [2024], undercount=_factors("city", 0.78))
    assert low["adu_permits"].tolist() == pytest.approx([0.78])
    high = cal.place_years("MN", _store(p), [GEO], [2025], undercount=_factors("city", 1.07))
    assert high["adu_permits"].tolist() == pytest.approx([3.21])


def test_out_of_fit_source_never_enters(one_rule):
    """D-081 item 4: Dallas's rows are `fit: false`, so a place-year counted only by it is not checkable."""
    assert "dallas_permits" in uc.out_of_fit()
    p = _permits([("dallas_permits", 2025, "ADU"), ("dallas_permits", 2025, "SFD")])
    rows = cal.place_years("MN", _store(p), [GEO], [2025], undercount=None)
    assert rows.empty
    both = _permits([("dallas_permits", 2025, "ADU"), ("dallas_permits", 2025, "ADU"), ("city", 2025, "ADU")])
    rows = cal.place_years("MN", _store(both), [GEO], [2025], undercount=None)
    assert rows["adu_permits"].tolist() == [1.0]  # the other source's count, not Dallas's 2


def test_drop_sources_by_hand():
    """drop [("a", None, 2021)] removes a's rows up to 2021 only."""
    p = pd.DataFrame({"source": ["a", "a", "b"], "issue_year": [2021, 2022, 2021]})
    out = cal.drop_sources(p, [("a", None, 2021)])
    assert list(zip(out["source"], out["issue_year"], strict=True)) == [("a", 2022), ("b", 2021)]


def test_drop_removes_place_years_and_require_counts_keeps_them(one_rule):
    """The low-recall 'without' run drops a source's years; `require_counts=False` (test B's roll towns) keeps
    a place-year with no flagging source, with a missing count."""
    p = _permits([("city", 2024, "ADU"), ("city", 2025, "ADU")])
    kept = cal.place_years("MN", _store(p), [GEO], [2024, 2025], undercount=None, drop=[("city", None, 2024)])
    assert kept["year"].tolist() == [2025]
    roll = cal.place_years(
        "MN", _store(_permits([("other", 2025, "SFD")])), [GEO], [2025], undercount=None, require_counts=False
    )
    assert len(roll) == 1 and math.isnan(roll["adu_permits"].iloc[0])


def test_out_of_fit_rows_have_no_k():
    from lotline.config import UndercountRow

    with pytest.raises(ValueError):
        UndercountRow(
            source="s",
            place="p",
            kind="parser",
            value=1.2,
            low=1.0,
            high=1.4,
            interval=0.9,
            fit=False,
            report="r",
        )


def test_field_rows_at_a_shared_z():
    """D-079's undercount refits: field rows at one shared z, parser rows at their medians."""
    rows = [
        uc.Row("f1", "x", "field", 1.1, 1.0, 1.3, 0.9, None, None, False, False, False),
        uc.Row("p1", "x", "parser", 1.5, 1.2, 2.0, 0.9, None, None, False, False, False),
    ]
    table = None
    f = uc.Factors(rows, [float(rows[0].quantile(1.645)), float(rows[1].quantile(0.0))])
    assert f.get("f1", 2020) == pytest.approx(1.3, rel=1e-3)  # the 95th percentile of a 90% interval
    assert f.get("p1", 2020) == pytest.approx(1.5)
    real = uc.at_field_z(1.645, table)
    for r, k in zip(real.rows, real.k, strict=True):
        if r.kind != "field":
            assert k == pytest.approx(r.value)


# ---------------------------------------------------------------------------------------------------------
# Form B: dose, events and the identification rule
# ---------------------------------------------------------------------------------------------------------


def _pl(state, geoid, years, y, base, no_br, owner, w=(1.0,), types=None):
    """A place with one rule per year; no_br/owner per (combination, year)."""
    no_br = np.asarray(no_br, dtype=bool).reshape(len(w), len(years), 1)
    owner = np.asarray(owner, dtype=bool).reshape(len(w), len(years), 1)
    t = np.full(no_br.shape, adu.TYPES.index("handbook")) if types is None else np.asarray(types)
    n = len(years)
    extra = {
        "rent": np.full(n, 1500.0),
        "home_value": np.full(n, 300_000.0),
        "rate": np.full(n, 5.0),
        "parcels": np.full(n, 10_000.0),
        "report": np.ones(n),
        "cov": np.ones((n, 1)),
        "age": np.arange(n, dtype=float)[:, None],
        "no_detached": np.zeros(no_br.shape, dtype=bool),
        "no_by_right": no_br,
        "owner": owner,
    }
    return cal.PlaceData(
        state,
        geoid,
        geoid,
        np.asarray(years),
        np.asarray(y, float),
        np.asarray(base, float),
        t,
        np.ones((n, 1)),
        np.asarray(w, float),
        None,
        extra,
    )


def test_rule_dose_by_hand():
    assert jr.rule_dose([True, False, False], [True, True, False]).tolist() == pytest.approx(
        [1 / 3, 2 / 3, 1]
    )


def test_dose_path_takes_the_strongest_rule_and_averages_blank_combinations():
    years = [2018, 2019]
    # two rules in force each year: permit-only and by right with owner occupancy -> 2/3
    no_br = np.array([[[True, False], [True, False]]])
    owner = np.array([[[False, True], [False, True]]])
    pl = _pl("MN", "A", years, [0, 0], [1, 1], np.zeros((1, 2, 1)), np.zeros((1, 2, 1)))
    pl = cal.PlaceData(
        **{
            **pl.__dict__,
            "types": np.full((1, 2, 2), 4),
            "cr": np.ones((2, 2)),
            "extra": {**pl.extra, "age": np.zeros((2, 2)), "no_by_right": no_br, "owner": owner},
        }
    )
    assert jr.dose_path(pl).tolist() == pytest.approx([2 / 3, 2 / 3])
    # a blank field makes the rule permit-only in one of two equal combinations -> (1/3 + 1) / 2
    pl2 = _pl(
        "MN", "B", years, [0, 0], [1, 1], [[True, True], [False, False]], [[False] * 2] * 2, w=(0.5, 0.5)
    )
    assert jr.dose_path(pl2).tolist() == pytest.approx([2 / 3, 2 / 3])


def test_events_need_two_years_each_side():
    years = [2018, 2019, 2020, 2021]
    a = _pl("MN", "A", years, [0] * 4, [1] * 4, [True, True, False, False], [False] * 4)
    b = _pl("NC", "B", years, [0] * 4, [1] * 4, [True, False, False, False], [False] * 4)
    ev = jr.events([a, b])
    assert ev[["geoid", "year"]].values.tolist() == [["A", 2020]]
    assert ev["dose_before"].iloc[0] == pytest.approx(1 / 3) and ev["dose_after"].iloc[0] == pytest.approx(1)


def test_g_identified_by_hand():
    ev = pd.DataFrame({"state": ["MN"] * 4 + ["NC"] * 3 + ["OR"]})
    assert jr.g_identified(ev)  # 8 events, 3 states
    assert not jr.g_identified(ev.iloc[:7])  # 7 events
    assert not jr.g_identified(pd.DataFrame({"state": ["MN"] * 5 + ["NC"] * 5}))  # 2 states


def test_design_b_adds_dose_columns():
    years = [2018, 2019, 2020, 2021]
    pl = _pl("MN", "A", years, [0] * 4, [1] * 4, [True, True, False, False], [False] * 4)
    x0, off0 = jr.design_b(pl, with_dose=False)
    x1, off1 = jr.design_b(pl, with_dose=True)
    assert x0.shape == (4, 8) and x1.shape == (4, 10)
    assert x1[:, 8].tolist() == pytest.approx([1 / 3, 1 / 3, 1, 1])
    assert x1[:, 9].tolist() == pytest.approx([2 / 3] * 4)
    assert off0.tolist() == pytest.approx(off1.tolist())


def _sim_b(seed, g, n_places=40, years=8, alpha=0.1):
    """Places whose dose steps from 1/3 to 1 halfway (half of them) with log rate -7 + g × dose."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_places):
        step = i % 2 == 0
        no_br = [not (step and t >= years // 2) for t in range(years)]
        u = rng.gamma(1 / alpha, alpha)
        dose = np.where(no_br, 1 / 3, 1.0)
        mu = 10_000 * math.exp(-7) * np.exp(g * dose) * u
        pl = _pl(
            ["MN", "NC", "OR"][i % 3],
            f"P{i}",
            list(range(2016, 2016 + years)),
            rng.poisson(mu),
            np.ones(years),
            no_br,
            [False] * years,
        )
        out.append(pl)
    return out


def test_fit_form_b_recovers_g():
    """With rule changes inside places, g is recovered (the place effect is gamma; d̄ absorbs levels)."""
    places = _sim_b(3, g=1.2)
    assert jr.g_identified(jr.events(places))
    b = jr.fit_form_b(places, with_dose=True, starts=2)
    g_hat, se = b.fit.beta[8], math.sqrt(b.fit.cov[8, 8])
    assert abs(g_hat - 1.2) < 3 * se + 0.15


def test_state_shift_and_spread_by_hand():
    assert jr.shift_spread([-1, 0, 1, 2]) == pytest.approx(np.std([-1, 0, 1, 2], ddof=1))
    places = _sim_b(4, g=0.0, n_places=12)
    b = jr.fit_form_b(places, with_dose=False, starts=1)
    # doubling every count moves the state's intercept up by about log 2
    doubled = [cal.PlaceData(**{**p.__dict__, "y": p.y * 2}) for p in places]
    assert jr.state_shift(doubled, b) - jr.state_shift(places, b) == pytest.approx(math.log(2), abs=0.05)


# ---------------------------------------------------------------------------------------------------------
# Tiers: lots, borrowed rules, prediction and the tier-2 update
# ---------------------------------------------------------------------------------------------------------


def _fit3(theta=0.002, alpha=0.2, se=0.0):
    hi = theta * math.exp(se * 1.645)
    return cal.Fit3(
        theta,
        theta / math.exp(se * 1.645),
        hi,
        alpha,
        0.5,
        0.3,
        (0.5, 0.5),
        (0.3, 0.3),
        False,
        False,
        0.0,
        1,
        1,
    )


def test_quantile_types_by_hand():
    p = np.array([[0.5, 0, 0, 0, 0.5]] * 2)
    assert jr.quantile_types(p, 4).tolist() == [[0, 0], [0, 0], [4, 4], [4, 4]]


def test_borrowed_rules_halve_the_expected_count():
    """p_local (0.5 none, 0.5 Handbook) -> E[k] = base × c(Handbook) / 2."""
    pl = _pl("MN", "A", [2021, 2022], [0, 0], [100.0, 100.0], [False] * 2, [False] * 2)
    b = jr.with_borrowed_rules(pl, np.array([[0.5, 0, 0, 0, 0.5]] * 2), np.array([3.0, 4.0]))
    cv = cal._cvals(0.5, 0.3)
    k = (b.w[:, None] * b.k(cv)).sum(axis=0) / b.w.sum()
    assert k.tolist() == pytest.approx([50.0, 50.0])
    assert jr.dose_path(b).tolist() == pytest.approx([0.5, 0.5])  # none 0, Handbook 1


def test_borrowed_rules_with_a_state_law_take_the_stronger():
    """A Handbook state law in force in the second year lifts the 'none' half to Handbook that year."""
    pl = _pl("OR", "A", [2017, 2018], [0, 0], [100.0, 100.0], [False] * 2, [False] * 2)
    law = np.array([[np.nan] * 5, [0, 0, 0, 0, 1.0]])
    b = jr.with_borrowed_rules(
        pl, np.array([[0.5, 0, 0, 0, 0.5]] * 2), np.array([3.0, 4.0]), law, np.array([np.nan, 0.5])
    )
    k = (b.w[:, None] * b.k(cal._cvals(0.5, 0.3))).sum(axis=0) / b.w.sum()
    assert k.tolist() == pytest.approx([50.0, 100.0])


def test_with_lots_scales_base():
    pl = _pl("MN", "A", [2021], [0], [10.0], [False], [False])
    assert jr.with_lots(pl, np.array([5_000.0])).base.tolist() == pytest.approx([5.0])


def test_subset_years_cuts_every_input():
    pl = _pl("MN", "A", [2020, 2021, 2022], [1, 2, 3], [1, 1, 1], [True, False, False], [False] * 3)
    s = jr.subset_years(pl, [2021, 2022])
    assert s.y.tolist() == [2, 3] and s.types.shape[1] == 2 and s.extra["no_by_right"].shape[1] == 2
    assert s.extra["age"].shape == (2, 1) and s.extra["rent"].shape == (2,)
    assert jr.subset_years(pl, [1999]) is None


def test_predictions_center_on_the_mean():
    pl = _pl("MN", "A", [2021, 2022], [0, 0], [1000.0, 1000.0], [False] * 2, [False] * 2)
    g = jr.globals_a(_fit3(theta=0.01, alpha=0.0), 0.0, 20_000, 1)
    d = jr.predict([pl], g, 2)["A"]
    assert d.mean(axis=0) == pytest.approx([10.0, 10.0], rel=0.03)


def test_place_loglik_matches_frailty_loglik():
    pl = _pl("MN", "A", [2021, 2022], [3, 1], [1000.0, 1000.0], [False] * 2, [False] * 2)
    g = jr.GlobalsA(np.array([0.002, 0.004]), 0.5, cal._cvals(0.5, 0.3))
    want = [cal.frailty_loglik_place(pl.y, pl.base, s, 0.5) for s in (0.002, 0.004)]
    assert jr.place_loglik(pl, g).tolist() == pytest.approx(want)


def test_tier2_update_moves_the_state_effect_toward_the_city():
    """A city with 4× the expected count pulls the shared state multiplier up; the target follows."""
    city = _pl("MN", "C", list(range(2016, 2025)), [40] * 9, [1000.0] * 9, [False] * 9, [False] * 9)
    target = _pl("MN", "T", [2021, 2022], [0, 0], [1000.0] * 2, [False] * 2, [False] * 2)
    g = jr.globals_a(_fit3(theta=0.01, alpha=0.05), 1.0, 20_000, 5)
    before = jr.predict([target], g, 7)["T"].sum(axis=1)
    g2, ess = jr.update(g, city, 9)
    after = jr.predict([target], g2, 7)["T"].sum(axis=1)
    assert ess > 50
    assert np.median(after) > 2.5 * np.median(before)


def test_form_b_predict_and_update_run():
    places = _sim_b(6, g=0.0, n_places=12)
    b = jr.fit_form_b(places, with_dose=False, starts=1)
    g = jr.globals_b(b, 0.5, 2_000, 1)
    d = jr.predict(places[:2], g, 3)
    assert d[places[0].geoid].shape == (2_000, len(places[0].y))
    g2, ess = jr.update(g, places[2], 4)
    assert 1 <= ess <= 2_000
    assert math.isfinite(jr.held_out_log_score(places[3], g2))


def test_borrowed_by_band_by_hand():
    donors = pd.DataFrame(
        {"population": [1_000] * 5 + [100_000], **{c: [0.0] * 6 for c in adu.P_COLS}, "rule_age": [1.0] * 6}
    )
    donors.loc[:1, "p_none"] = 1.0
    donors.loc[2:, "p_handbook"] = 1.0
    out = jr.borrowed_by_band(donors, [10_000, 50_000], 5).set_index("band")
    assert out.loc[0, "p_none"] == pytest.approx(0.4) and out.loc[0, "p_handbook"] == pytest.approx(0.6)
    assert out.loc[2, "source"] == "all bands"  # one donor in band 2 < 5


# ---------------------------------------------------------------------------------------------------------
# Scores and the pre-registered rules
# ---------------------------------------------------------------------------------------------------------


def test_crps_by_hand():
    assert jr.crps([0, 2], 1) == pytest.approx(0.5)
    assert jr.crps([3, 3, 3], 3) == pytest.approx(0.0)


def test_log_score_by_hand():
    assert jr.log_score([3, 3, 4], 3) == pytest.approx(math.log(3 / 4))
    assert jr.log_score([3, 3, 4], 9.2) == pytest.approx(math.log(1 / 4))


def test_score_flags_by_hand():
    d = np.arange(1, 101)
    s = jr.score(50, d)
    assert s["inside"] and s["within_2x"] and s["useful"]
    s = jr.score(5, d)  # below P10 (10.9)
    assert not s["inside"] and not s["within_2x"]


def test_claim_rule_by_hand():
    r = pd.DataFrame(
        {
            "state": list("ABCDE") * 3,
            "tier": [0] * 5 + [1] * 5 + [2] * 5,
            "useful": [1, 1, 1, 0, 0] + [1, 1, 1, 1, 0] + [1] * 5,
        }
    )
    assert jr.claim_tier(r) == 1
    assert jr.claim_tier(r[r["tier"] == 0]) is None


def test_test_a_by_hand():
    rows = pd.DataFrame({"inside": [True, True, False], "obs_over_p50": [0.8, 1.5, 3.0]})
    assert jr.test_a_pass(rows)
    assert not jr.test_a_pass(rows.assign(inside=[True, False, False]))
    assert not jr.test_a_pass(rows.assign(obs_over_p50=[2.5, 3.0, 4.0]))
    assert jr.test_a_pass(rows.iloc[0:0]) is None


def test_test_b_and_c_by_hand():
    assert jr.test_b_pass(50, np.arange(1, 101)) and not jr.test_b_pass(95, np.arange(1, 101))
    assert jr.test_c_pass([1.0, 1.4]) and not jr.test_c_pass([1.2, 0.9]) and jr.test_c_pass([]) is None


def test_test_c_tolerance_d082():
    # D-082: a shortfall under 1% passes (Tonka Bay 0.991 in the refit), a larger one fails
    assert jr.test_c_pass([0.991, 1.2]) and jr.test_c_pass([0.99, 1.0])
    assert not jr.test_c_pass([0.989, 1.2])
    assert not jr.test_c_pass([0.991], tolerance=0.0)


def test_tests_passed_counts_state_by_state():
    assert jr.tests_passed({"A": {"MN": True, "NC": False, "OH": None}, "B": {"NC": True}}) == 2


def test_decision_rule_by_hand():
    assert jr.decide(None, 1, 0, 1, 3, 3).form == "B"
    assert jr.decide(1, 1, 10, 4, 3, 3).form == "B"
    assert jr.decide(1, 1, 10, 4, 3, 2).form == "A"
    assert jr.decide(1, 1, 7, 4, 3, 3).form == "A"
    assert jr.decide(None, None, 100, 1, 0, 9).form == "A"
    assert jr.decide(2, 1, -5, 1, 2, 2).form == "B"
    assert jr.decide(1, 2, 50, 1, 2, 9).form == "A"
