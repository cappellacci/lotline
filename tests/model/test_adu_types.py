"""D-088 Form P and Part 1: each step against a hand-worked example or the base form (synthetic data only)."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.calibrate.adu import calibrate_adu as cal
from lotline.calibrate.adu import joint_refit as jr
from lotline.model import adu_owner as ao
from lotline.model import adu_screen as scr
from lotline.model import adu_types as ty

T_OWNER, T_OTHER, T_HB = 1, 2, 4
GRID = (0.2, 0.4, 0.7, 1.0)


def _pl(geoid, y, base, typ=T_HB, start=2016, state="MN"):
    n = len(y)
    return cal.PlaceData(
        state,
        geoid,
        geoid,
        np.arange(start, start + n),
        np.asarray(y, dtype=float),
        np.asarray(base, dtype=float),
        np.full((1, n, 1), typ),
        np.ones((n, 1)),
        np.array([1.0]),
        None,
        {"parcels": np.full(n, 1000.0)},
    )


def test_assign_types_hand_worked():
    j = pd.DataFrame(
        {
            "geoid": ["A", "B", "C", "D", "E"],
            "cbsa_code": ["M", "M", "M", "m", None],
            "cbsa_type": ["metro", "metro", "metro", "micro", None],
            "units": [300, 120, 90, 50, 10],
        }
    )
    got = ty.assign_types(j)
    assert got.to_dict() == {"A": "core", "B": "core", "C": "suburb", "D": "town", "E": "town"}


def test_merge_small_hand_worked():
    rows = (
        [("MN", "core")] * 4
        + [("NC", "core")] * 3
        + [("TX", "core")] * 3
        + [(s, "suburb") for s in ("MN", "NC", "TX", "OR") for _ in range(8)]
        + [("MN", "town")] * 3
        + [("NC", "town")] * 2
    )
    df = pd.DataFrame(rows, columns=["state", "type"])
    mapping, notes = ty.merge_small(df)
    assert mapping == {"core": "core", "suburb": "suburb", "town": "suburb"} and len(notes) == 1
    mapping2, _ = ty.merge_small(df[df["type"] != "core"])
    assert mapping2["core"] == "suburb" and mapping2["town"] == "suburb"


def test_indicators_and_scaled_hand_worked():
    assert list(ty.indicators("core")) == [1, 0]
    assert list(ty.indicators("suburb")) == [0, 0]
    assert list(ty.indicators("town")) == [0, 1]
    pl = ty.with_types(_pl("a", [0], [100.0]), ty.indicators("core"))
    assert ty.typed_scaled(pl, 0.0, np.array([math.log(2), 0.0])).base == pytest.approx([200.0])


def test_globals_place_scale_with_types():
    cv = cal._cvals(1, 1)
    pl = ao.with_z(ty.with_types(_pl("a", [0], [1.0]), ty.indicators("town")), 1.0)
    g = jr.GlobalsA(
        np.array([2.0, 2.0]),
        1.0,
        cv,
        beta=np.array([math.log(3), 0.0]),
        type_beta=np.array([[0.0, math.log(5)], [1.0, 0.0]]),
    )
    assert g.place_scale(pl) == pytest.approx([2 * 3 * 5, 2.0])
    ref = ty.with_types(_pl("b", [0], [1.0]), ty.indicators("suburb"))
    assert g.place_scale(ref) == pytest.approx([2.0, 2.0])
    assert jr._take(g, np.array([1])).type_beta.shape == (1, 2)


def test_form_p_loglik_equals_base_on_scaled_places():
    pl = ty.with_types(_pl("a", [3, 0, 5], [2.0, 1.0, 4.0]), ty.indicators("core"))
    cv = cal._cvals(1.0, 1.0)
    tb = np.array([[0.4, 0.0], [-0.7, 0.0]])
    g = jr.GlobalsA(np.array([0.5, 1.5]), 1.3, cv, type_beta=tb)
    for j in range(2):
        want = jr.place_loglik(ty.typed_scaled(pl, 0.0, tb[j]), jr.GlobalsA(g.scale[j : j + 1], 1.3, cv))[0]
        assert jr.place_loglik(pl, g)[j] == pytest.approx(want)


def _synthetic(b_core, b_town, beta=0.0, n=48, years=6, alpha=0.4, seed=5):
    rng = np.random.default_rng(seed)
    out = []
    kinds = ("core", "suburb", "town")
    for i in range(n):
        z = float(rng.normal())
        kind = kinds[i % 3]
        typ = T_OWNER if i % 2 else T_OTHER
        c = 1.0 if typ == T_OWNER else 0.4
        base = np.full(years, float(rng.uniform(500, 3000)))
        u = rng.gamma(1 / alpha, alpha)
        f = math.exp(beta * z + (b_core if kind == "core" else 0) + (b_town if kind == "town" else 0))
        y = rng.poisson(0.02 * f * u * c * base)
        out.append(ty.with_types(ao.with_z(_pl(str(i), y, base, typ), z), ty.indicators(kind)))
    return out


def test_fit3_types_without_terms_reproduces_fit3_term():
    places = _synthetic(0.0, 0.0, beta=-0.5, n=24)
    want = ao.fit3_term(places, estimate_beta=True, grid=GRID)
    got = ty.fit3_types(places, estimate_beta=True, terms=(), grid=GRID)
    assert (got.m_owner, got.m_other) == (want.m_owner, want.m_other)
    assert got.loglik == pytest.approx(want.loglik, abs=1e-3)
    assert got.theta == pytest.approx(want.theta, rel=1e-3)
    assert got.alpha == pytest.approx(want.alpha, rel=1e-2)
    assert got.beta == pytest.approx(want.beta, abs=1e-3)
    assert got.beta_low == pytest.approx(want.beta_low, abs=5e-3)
    assert got.low == pytest.approx(want.low, rel=1e-2) and got.high == pytest.approx(want.high, rel=1e-2)
    assert ty.type_draws(got, 5, 1) is None


def test_fit3_types_recovers_planted_terms():
    places = _synthetic(1.0, -1.0, n=60)
    fit = ty.fit3_types(places, estimate_beta=False, grid=GRID)
    (lc, lt), (hc, ht) = fit.type_low, fit.type_high
    assert lc < 1.0 < hc and lc > 0
    assert lt < -1.0 < ht and ht < 0
    d = ty.type_draws(fit, 4000, 1)
    assert d.std(axis=0) == pytest.approx(fit.type_se(), rel=0.1)


def test_fit3_types_holds_an_empty_type_at_zero():
    places = [p for p in _synthetic(0.5, 0.0, n=30) if ty.type_d(p)[1] == 0]  # no towns
    fit = ty.fit3_types(places, estimate_beta=False, grid=GRID)
    assert fit.type_estimated == (True, False) and fit.type_beta[1] == 0.0


def test_variance_share_hand_worked():
    g = pd.DataFrame({"g": ["a", "a", "b", "b"]})
    assert ty.variance_share([1, 3, 5, 7], [1, 1, 1, 1], g) == pytest.approx(0.8)
    # weights: a place with weight 0 does not count
    assert ty.variance_share([1, 3, 5, 7, 100], [1, 1, 1, 1, 0], pd.DataFrame({"g": list("aabbb")})) == (
        pytest.approx(0.8)
    )


def test_reading_rule_hand_worked():
    assert ty.reading({"state": 0.3, "type": 0.4, "source": 0.1}, True) == "types matter"
    assert ty.reading({"state": 0.3, "type": 0.1, "source": 0.4}, True) == "counting matters"
    assert ty.reading({"state": 0.4, "type": 0.1, "source": 0.1}, False) == "states differ"
    assert ty.reading({"state": 0.4, "type": 0.35, "source": 0.1}, False) == "mixed"


def test_decide_hand_worked():
    assert ty.decide(None, None, 10, 4, 1, 1, -3, 2).types
    assert not ty.decide(None, None, 7, 4, 1, 1, -3, 2).types
    assert not ty.decide(None, None, 10, 4, 1, 0, -3, 2).types
    assert not ty.decide(None, None, 10, 4, 1, 1, -5, 2).types
    assert ty.decide(2, 1, -50, 1, 1, 1, 0, 1).types


def test_config_mirrors_type_rules():
    """config/params/adu_place_types.yaml holds D-088's typing rules; the module's defaults must agree."""
    import inspect

    from lotline.config import load_params

    p = load_params("adu_place_types")
    assert p["adu_type_core_share"].value == pytest.approx(ty.CORE_SHARE, abs=1e-4)
    sig = inspect.signature(ty.merge_small).parameters
    assert p["adu_type_min_fit_places"].value == sig["min_places"].default
    assert p["adu_type_min_fit_states"].value == sig["min_states"].default


def test_config_town_prior_follows_core_term():
    """D-089: the town prior's s is |β̂_core| / z_90, from the configured core term."""
    from lotline.config import load_params
    from lotline.validation import adu_profiles as pr

    p = load_params("adu_place_types")
    s = pr.town_sd(p["adu_types_core_log_multiplier"].value)
    assert p["adu_types_town_prior_sd"].value == pytest.approx(s, abs=5e-4)


def test_raw_types_hand_worked():
    """Metro M: places A 300 and B 90, township T 500 (not ranked: only places can be core); micro place D;
    county remainder R with no area -> A core, B suburb (90 < 100), T suburb, D town, R town."""
    u = pd.DataFrame(
        {
            "geoid": ["A", "B", "T", "D", "R"],
            "kind": ["place", "place", "township", "place", "county_unincorporated"],
            "cbsa_code": ["M", "M", "M", "m", None],
            "cbsa_type": ["metro", "metro", "metro", "micro", None],
            "units": [300, 90, 500, 50, 20],
        }
    )
    assert ty.raw_types(u).to_dict() == {"A": "core", "B": "suburb", "T": "suburb", "D": "town", "R": "town"}


def test_config_units_vintage_matches_module():
    from lotline.config import load_params

    assert load_params("adu_place_types")["adu_type_units_end_year"].value == ty.UNITS_END


# ---------------------------------------------------------------------------------------------------------
# D-094: a place-effect variance per type (Form S)
# ---------------------------------------------------------------------------------------------------------


def test_screen_loglik_alpha_per_place_hand_worked():
    # one year, y = 2, k = 1, rate 1: α = 1 -> NB(r 1, p 1/2) at 2 = 1/8; α -> 0 -> Poisson(1) at 2 = e^-1 / 2
    pls = [_pl("a", [2], [1.0]), _pl("b", [2], [1.0])]
    p = scr.prepare(pls, cal._cvals(1.0, 1.0))
    got = scr.place_loglik(p, np.ones(2), np.array([1.0, 0.0]))
    assert got == pytest.approx([math.log(1 / 8), -1.0 - math.log(2)])
    assert scr.place_loglik(p, np.ones(2), np.array([1.0, 1.0])) == pytest.approx(
        scr.place_loglik(p, np.ones(2), 1.0)
    )


def test_alphas_and_is_core_hand_worked():
    assert ty.alphas(0.0, math.log(0.5), np.array([1.0, 0.0])) == pytest.approx([0.5, 1.0])
    assert ty.alphas(math.log(2.0), 3.0, None) == pytest.approx(2.0)
    pls = [
        ty.with_types(_pl(str(i), [0], [1.0]), ty.indicators(k))
        for i, k in enumerate(("core", "suburb", "town"))
    ]
    assert list(ty.is_core(pls + [_pl("x", [0], [1.0])])) == [1.0, 0.0, 0.0, 0.0]


def test_spread_at_lambda_zero_is_form_p():
    places = _synthetic(0.8, 0.0, n=24)
    p = scr.prepare(places, cal._cvals(0.4, 0.4))
    zm = np.column_stack([ty.is_core(places)])
    core = ty.is_core(places)
    for lt, la, b in ((-4.0, 0.2, (0.5,)), (-3.5, -1.0, (1.2,))):
        assert ty._ll(p, zm, lt, la, b, core, 0.0) == pytest.approx(ty._ll(p, zm, lt, la, b))


def _synthetic_spread(alpha_core, alpha_sub, n=150, years=6, seed=11):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        kind = "core" if i % 3 == 0 else "suburb"
        a = alpha_core if kind == "core" else alpha_sub
        base = np.full(years, float(rng.uniform(1000, 4000)))
        u = rng.gamma(1 / a, a)
        y = rng.poisson(0.02 * u * base)
        out.append(ty.with_types(_pl(str(i), y, base, T_HB), ty.indicators(kind)))
    return out


def test_fit3_types_spread_recovers_planted_alphas():
    places = _synthetic_spread(0.1, 1.2)
    fit = ty.fit3_types(places, estimate_beta=False, terms=(), grid=(1.0,), spread=True)
    assert fit.alpha_core < fit.alpha  # core cities vary less, as planted
    assert fit.lam_low < math.log(0.1 / 1.2) < fit.lam_high and fit.lam_high < 0
    assert fit.alpha_core == pytest.approx(fit.alpha * math.exp(fit.lam))
    plain = ty.fit3_types(places, estimate_beta=False, terms=(), grid=(1.0,))
    assert fit.loglik > plain.loglik and plain.alpha_core is None


def test_globals_alpha_per_type_draws_and_switch_off():
    cv = cal._cvals(1.0, 1.0)
    core = ty.with_types(_pl("c", [1, 2], [50.0, 50.0]), ty.indicators("core"))
    sub = ty.with_types(_pl("s", [1, 2], [50.0, 50.0]), ty.indicators("suburb"))
    g1 = jr.GlobalsA(np.full(4000, 0.1), 1.5, cv)
    g2 = jr.GlobalsA(np.full(4000, 0.1), 1.5, cv, alpha_core=1.5)
    assert g2.place_alpha(core) == 1.5 and g2.place_alpha(sub) == 1.5
    for a, b in zip(
        jr.predict([core, sub], g1, 3).values(), jr.predict([core, sub], g2, 3).values(), strict=True
    ):
        assert np.array_equal(a, b)  # α_core = α reproduces one α exactly
    g3 = jr.GlobalsA(np.full(4000, 1.0), 1.5, cv, alpha_core=0.2)
    assert g3.place_alpha(core) == 0.2 and g3.place_alpha(sub) == 1.5
    # Var(Y) of a one-year total under rate 50: μ + α μ², by type
    d = jr.predict([core, sub], g3, 3)
    assert d["c"][:, 0].var() == pytest.approx(50 + 0.2 * 2500, rel=0.15)
    assert d["s"][:, 0].var() == pytest.approx(50 + 1.5 * 2500, rel=0.15)
    assert jr.place_loglik(core, g3)[0] != pytest.approx(jr.place_loglik(core, g1)[0])
