"""D-092 deviation 2026-11-15: the place-level rate multiplier w ~ Gamma(mean 1, variance κ) on the
missing-middle rate, y_t ~ Poisson(w (B_t + θ u k_t)). Each piece against a hand-worked or brute-force
example; κ = 0 must give runs 4-5 exactly."""

import math

import numpy as np
import pytest

from lotline.calibrate.mm import calibrate_mm as cal


def _place(gid="a", y=(3, 5), B=(4.0, 4.0), kr=(0.0, 0.0), kappa=0.0):
    n = len(y)
    return cal.Place(
        geoid=gid,
        name=gid,
        T=2021,
        beta=float(B[0]),
        years=np.arange(2021, 2021 + n),
        y=np.asarray(y, float),
        g=np.asarray(B, float) / float(B[0]),
        kr=np.asarray(kr, float),
        age=np.arange(n) + 0.5,
        eligible=np.full(n, 1000.0),
        kappa=kappa,
    )


def _brute(y, mu, kappa, n=200_001):
    """log ∫ Π Poisson(y; w μ) Gamma(w; mean 1, var κ) dw by the trapezoid on ln w, Σ log y! dropped."""
    r = 1 / kappa
    v = np.linspace(-30, 6, n)
    w = np.exp(v)
    log_g = r * math.log(r) - math.lgamma(r) + r * v - r * w  # density of ln w
    ll = sum(yi * np.log(wi_mu) - wi_mu for yi, wi_mu in ((yi, w * m) for yi, m in zip(y, mu, strict=True)))
    f = log_g + ll
    m = f.max()
    return float(m + math.log(np.trapezoid(np.exp(f - m), v)))


def test_w_mixed_by_hand():
    # one year, μ = 2, y = 1, κ = 1 (r = 1): ln 2 + 0 + lnΓ(2) − lnΓ(1) − 2 ln 3 = ln(2/9)
    assert cal._w_mixed(math.log(2.0), 2.0, 1.0, 1.0) == pytest.approx(math.log(2 / 9))


def test_w_mixed_is_poisson_at_kappa_zero():
    assert cal._w_mixed(3 * math.log(2.0), 2.0, 3.0, 0.0) == pytest.approx(3 * math.log(2.0) - 2.0)
    # and converges to it from above zero
    assert cal._w_mixed(3 * math.log(2.0), 2.0, 3.0, 1e-7) == pytest.approx(3 * math.log(2.0) - 2.0, abs=1e-5)


@pytest.mark.parametrize("kappa", [0.05, 0.5, 2.0])
def test_w_mixed_matches_brute_force(kappa):
    y, mu = [3.0, 0.0, 7.0], [2.0, 1.5, 4.0]
    closed = cal._w_mixed(sum(a * math.log(b) for a, b in zip(y, mu, strict=True)), sum(mu), sum(y), kappa)
    assert closed == pytest.approx(_brute(y, mu, kappa), abs=1e-6)


def test_place_loglik_kappa_zero_unchanged():
    y, B, k = [2.0, 4.0], [1.5, 2.0], [100.0, 200.0]
    for alpha in (1e-9, 0.7):
        assert cal.place_loglik(y, B, k, 0.01, alpha, 0.0) == cal.place_loglik(y, B, k, 0.01, alpha)


def test_place_loglik_with_w_poisson_u_matches_brute_force():
    # α -> 0 (u = 1): the mean is w (B + θ k)
    y, B, k, theta, kappa = [2.0, 4.0], [1.5, 2.0], [100.0, 200.0], 0.01, 0.4
    mu = [b + theta * kk for b, kk in zip(B, k, strict=True)]
    assert cal.place_loglik(y, B, k, theta, 1e-9, kappa) == pytest.approx(_brute(y, mu, kappa), abs=1e-6)


def test_place_loglik_with_w_and_u_matches_nested_brute_force():
    # u ~ Gamma(1, α) on a fine grid outside, w in closed form inside
    y, B, k, theta, alpha, kappa = [1.0, 3.0], [1.0, 1.0], [100.0, 100.0], 0.01, 0.5, 0.3
    r = 1 / alpha
    v = np.linspace(-20, 5, 20_001)
    u = np.exp(v)
    log_g = r * math.log(r) - math.lgamma(r) + r * v - r * u
    inner = np.array(
        [
            cal._w_mixed(
                sum(a * math.log(b + theta * ui * kk) for a, b, kk in zip(y, B, k, strict=True)),
                sum(B) + theta * ui * sum(k),
                sum(y),
                kappa,
            )
            for ui in u
        ]  # fmt: skip
    )
    f = log_g + inner
    m = f.max()
    brute = float(m + math.log(np.trapezoid(np.exp(f - m), v)))
    assert cal.place_loglik(y, B, k, theta, alpha, kappa) == pytest.approx(brute, abs=1e-3)


@pytest.mark.parametrize("alpha", [1e-9, 0.6, 3.0])
def test_stacked_loglik_is_the_sum_of_places(alpha):
    ps = cal.with_kappa(
        [
            _place("a", (3, 5), (4.0, 4.0), (500.0, 600.0)),
            _place("b", (0, 1, 9), (2.0, 2.5, 3.0), (0, 300, 900)),
        ],
        0.35,
    )
    total = sum(cal.place_loglik(p.y, p.B, p.k(2.0), 0.004, alpha, p.kappa) for p in ps)
    assert cal.loglik(ps, 0.004, alpha, 2.0) == pytest.approx(total, rel=1e-9)


def test_stack_refuses_mixed_kappa():
    with pytest.raises(ValueError):
        cal.Stack.of([_place("a", kappa=0.1), _place("b", kappa=0.2)])


def test_no_effect_log_score_with_w():
    p = _place(y=(3, 5), B=(4.0, 4.0), kappa=0.5)
    assert cal.no_effect_log_score(p) == pytest.approx(_brute([3, 5], [4.0, 4.0], 0.5), abs=1e-6)
    assert cal.no_effect_log_score(_place(y=(3, 5), B=(4.0, 4.0))) == pytest.approx(
        3 * math.log(4) + 5 * math.log(4) - 8
    )


def test_fit_kappa_zero_when_no_extra_spread():
    # y equal to B everywhere: the Poisson fits best, κ̂ = 0
    ps = [_place(str(i), y=(4, 4), B=(4.0, 4.0)) for i in range(10)]
    assert cal.fit_kappa(ps).kappa == 0.0


def test_fit_kappa_recovers_a_known_spread():
    rng = np.random.default_rng(5)
    kappa, n = 0.5, 400
    w = rng.gamma(1 / kappa, kappa, size=n)
    ps = [_place(str(i), y=tuple(rng.poisson(20.0 * wi, size=5)), B=(20.0,) * 5) for i, wi in enumerate(w)]
    f = cal.fit_kappa(ps)
    assert f.low < kappa < f.high
    assert 0.4 < f.kappa < 0.62
    assert f.loglik > f.loglik_poisson


def test_benchmark_variance_follows_total_variance():
    # B = 10 a year for 2 years, κ = 0.25: mean 20, Var = 20 + 0.25 × 20² = 120
    p = _place(y=(0, 0), B=(10.0, 10.0), kappa=0.25)
    tot = cal.benchmark_places([p], 0.0, 1.0, draws=200_000, seed=4)["a"].sum(axis=1)
    assert tot.mean() == pytest.approx(20.0, rel=0.01)
    assert tot.var() == pytest.approx(120.0, rel=0.03)


def test_kappa_zero_draws_are_unchanged():
    a = _place(y=(0, 0), B=(10.0, 10.0), kr=(100.0, 100.0))
    before = cal.predict_places([a], 0.01, 0.3, 0.5, 2.0, draws=500, seed=9)["a"]
    rng = np.random.default_rng(9)
    th = np.exp(rng.normal(math.log(0.01), 0.3, size=500))
    import zlib

    r = np.random.default_rng([9, zlib.crc32(b"a")])
    u = r.gamma(2.0, 0.5, size=500)
    direct = r.poisson(a.B[None, :] + (th * u)[:, None] * a.k(2.0)[None, :])
    assert np.array_equal(before, direct)


# ---- D-092 deviation (b): the per-year negative binomial (form Ny) and the baseline scores ----


def test_nb_year_by_hand():
    # y = 1, μ = 2, φ = 1 (r = 1): lnΓ(2) − lnΓ(1) + ln(1/3) + ln(2/3) = ln(2/9)
    assert cal.nb_year_terms([1.0], [2.0], 1.0)[0] == pytest.approx(math.log(2 / 9))


def test_nb_year_is_poisson_at_zero():
    y, mu = np.array([0.0, 3.0]), np.array([1.5, 2.0])
    assert np.allclose(cal.nb_year_terms(y, mu, 0.0), y * np.log(mu) - mu)
    assert np.allclose(cal.nb_year_terms(y, mu, 1e-8), y * np.log(mu) - mu, atol=1e-6)


def test_nb_year_matches_gamma_mixture():
    # NB(mean μ, var μ + φμ²) is a Poisson with a Gamma(mean 1, variance φ) multiplier on that one year
    for y, mu, phi in ((0.0, 2.0, 0.7), (5.0, 1.5, 2.0), (12.0, 9.0, 0.3)):
        assert cal.nb_year_terms([y], [mu], phi)[0] == pytest.approx(_brute([y], [mu], phi), abs=1e-6)


def test_baseline_scores_forms():
    a = _place("a", y=(3, 5), B=(4.0, 4.0))
    b = _place("b", y=(0, 9, 1), B=(2.0, 2.5, 3.0))
    w = cal.baseline_scores([a, b], "w", 0.5)
    assert w[0] == pytest.approx(_brute([3, 5], [4.0, 4.0], 0.5), abs=1e-6)
    yr = cal.baseline_scores([a, b], "year", 0.5)
    assert yr[1] == pytest.approx(float(np.sum(cal.nb_year_terms([0, 9, 1], [2.0, 2.5, 3.0], 0.5))))
    with pytest.raises(ValueError):
        cal.baseline_scores([a], "month", 0.5)


def test_fit_noise_w_equals_fit_kappa():
    rng = np.random.default_rng(3)
    ps = [
        _place(str(i), y=tuple(rng.poisson(10.0 * rng.gamma(2.0, 0.5), size=4)), B=(10.0,) * 4)
        for i in range(200)
    ]
    assert cal.fit_noise(ps, "w").kappa == pytest.approx(cal.fit_kappa(ps).kappa, rel=1e-6)


def test_fit_noise_year_recovers_phi():
    rng = np.random.default_rng(6)
    phi = 0.8
    ys = rng.poisson(15.0 * rng.gamma(1 / phi, phi, size=(500, 5)))
    f = cal.fit_noise([_place(str(i), y=tuple(y), B=(15.0,) * 5) for i, y in enumerate(ys)], "year")
    assert f.low < phi < f.high


def _choice_module():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "mm_baseline_choice_d092.py"
    spec = importlib.util.spec_from_file_location("mm_baseline_choice_d092", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_choice_rule_prefers_simpler_within_two_se():
    import pandas as pd

    m = _choice_module()
    base = np.zeros(100)
    alt = np.where(np.arange(100) % 2 == 0, 1.03, -0.97)  # paired differences: mean 0.03, sd ≈ 1
    # C3-year leads by Σ 3.0 with paired SE ≈ 1 × √100 = 10: within 2 SE, so C0-w (earlier in the
    # order) is chosen
    scores = pd.DataFrame({"C0-w": base, "C3-year": alt})
    table = pd.DataFrame({"candidate": ["C0-w", "C3-year"], "heldout": scores.sum().to_list()})
    pick = m.choose(table, scores)
    assert pick["best_score"] == "C3-year"
    assert pick["chosen"] == "C0-w"
    # a clear lead (Σ 503 against SE ≈ 10) wins even though C3-year is later in the order
    scores2 = pd.DataFrame({"C0-w": base, "C3-year": alt + 5.0})
    table2 = pd.DataFrame({"candidate": ["C0-w", "C3-year"], "heldout": scores2.sum().to_list()})
    assert m.choose(table2, scores2)["chosen"] == "C3-year"


# ---- the per-year NB (φ) inside the main likelihood and the draws ----


def test_place_loglik_phi_poisson_u_is_nb_sum():
    y, B, k, theta, phi = [2.0, 0.0, 7.0], [1.5, 2.0, 1.0], [100.0, 200.0, 300.0], 0.01, 0.6
    mu = np.array(B) + theta * np.array(k)
    expected = float(np.sum(cal.nb_year_terms(y, mu, phi)))
    assert cal.place_loglik(y, B, k, theta, 1e-9, phi=phi) == pytest.approx(expected)


def test_place_loglik_phi_with_u_matches_nested_brute_force():
    y, B, k, theta, alpha, phi = [1.0, 3.0], [1.0, 1.0], [100.0, 100.0], 0.01, 0.5, 0.4
    r = 1 / alpha
    v = np.linspace(-20, 5, 20_001)
    u = np.exp(v)
    log_g = r * math.log(r) - math.lgamma(r) + r * v - r * u
    inner = np.array(
        [float(np.sum(cal.nb_year_terms(y, np.array(B) + theta * ui * np.array(k), phi))) for ui in u]
    )
    f = log_g + inner
    m = f.max()
    brute = float(m + math.log(np.trapezoid(np.exp(f - m), v)))
    assert cal.place_loglik(y, B, k, theta, alpha, phi=phi) == pytest.approx(brute, abs=1e-3)


@pytest.mark.parametrize("alpha", [1e-9, 0.6, 3.0])
def test_stacked_loglik_phi_is_the_sum_of_places(alpha):
    ps = cal.with_phi(
        [
            _place("a", (3, 5), (4.0, 4.0), (500.0, 600.0)),
            _place("b", (0, 1, 9), (2.0, 2.5, 3.0), (0, 300, 900)),
        ],
        0.9,
    )
    total = sum(cal.place_loglik(p.y, p.B, p.k(2.0), 0.004, alpha, phi=p.phi) for p in ps)
    assert cal.loglik(ps, 0.004, alpha, 2.0) == pytest.approx(total, rel=1e-9)


def test_both_noise_forms_refused():
    with pytest.raises(ValueError):
        cal.place_loglik([1.0], [1.0], [1.0], 0.01, 0.5, kappa=0.3, phi=0.3)
    with pytest.raises(ValueError):
        cal.loglik([cal.replace(_place(kappa=0.3), phi=0.3)], 0.01, 0.5, 2.0)


def test_no_effect_log_score_with_phi():
    p = cal.with_phi([_place(y=(3, 5), B=(4.0, 4.0))], 0.5)[0]
    assert cal.no_effect_log_score(p) == pytest.approx(
        float(np.sum(cal.nb_year_terms([3, 5], [4.0, 4.0], 0.5)))
    )


def test_benchmark_variance_per_year_nb():
    # B = 10 a year for 2 years, φ = 0.25, years independent: Var = Σ (μ + φ μ²) = 2 × (10 + 25) = 70
    p = cal.with_phi([_place(y=(0, 0), B=(10.0, 10.0))], 0.25)[0]
    tot = cal.benchmark_places([p], 0.0, 1.0, draws=200_000, seed=4)["a"].sum(axis=1)
    assert tot.mean() == pytest.approx(20.0, rel=0.01)
    assert tot.var() == pytest.approx(70.0, rel=0.03)


def test_phi_zero_draws_are_unchanged():
    a = _place(y=(0, 0), B=(10.0, 10.0), kr=(100.0, 100.0))
    before = cal.predict_places([a], 0.01, 0.3, 0.5, 2.0, draws=500, seed=9)["a"]
    after = cal.predict_places(cal.with_phi([a], 0.0), 0.01, 0.3, 0.5, 2.0, draws=500, seed=9)["a"]
    assert np.array_equal(before, after)


# ---- D-092 deviation (c): φ by place type ----


@pytest.mark.parametrize("alpha", [1e-9, 0.6, 3.0])
def test_stacked_loglik_phi_by_place_is_the_sum_of_places(alpha):
    ps = cal.with_phi_by(
        [
            _place("a", (3, 5), (4.0, 4.0), (500.0, 600.0)),
            _place("b", (0, 1, 9), (2.0, 2.5, 3.0), (0, 300, 900)),
            _place("c", (2,), (1.0,), (100.0,)),
        ],
        {"a": 0.9, "b": 4.0, "c": 0.9},
    )
    total = sum(cal.place_loglik(p.y, p.B, p.k(2.0), 0.004, alpha, phi=p.phi) for p in ps)
    assert cal.loglik(ps, 0.004, alpha, 2.0) == pytest.approx(total, rel=1e-9)


def test_stack_phi_by_place_lays_out_per_year():
    ps = cal.with_phi_by([_place("a", (3, 5)), _place("b", (0, 1, 9), (2.0, 2.5, 3.0), (0, 0, 0))],
                         {"a": 0.5, "b": 2.0})  # fmt: skip
    assert cal.Stack.of(ps).phi.tolist() == [0.5, 0.5, 2.0, 2.0, 2.0]


def test_stack_refuses_phi_mixed_with_poisson():
    with pytest.raises(ValueError):
        cal.Stack.of(cal.with_phi([_place("a")], 0.5) + [_place("b")])


def test_lg_by_hand_per_element():
    # φ = 1 (r = 1): lnΓ(3) − lnΓ(1) = ln 2; φ = 0.5 (r = 2): lnΓ(2) − lnΓ(2) = 0
    assert cal._lg(np.array([2.0, 0.0]), np.array([1.0, 0.5])) == pytest.approx([math.log(2), 0.0])
