import pandas as pd
import pytest

from lotline.model import completion


def test_annual_totals_keeps_complete_years_only():
    idx = pd.date_range("2020-01-01", periods=15, freq="MS")  # 2020 complete, 2021 has 3 months
    out = completion.annual_totals(pd.Series([1.0] * 15, index=idx))
    assert out.to_dict() == {2020: 12.0}


def test_completion_ratio_hand_worked():
    """Permits 2010-2012: 100 + 100 + 100 = 300. With a 1-year lag, completions 2011-2013:
    90 + 95 + 100 = 285. Ratio = 285 / 300 = 0.95. Completions in 2010 (60) belong to earlier permits."""
    permits = pd.Series({2010: 100.0, 2011: 100.0, 2012: 100.0, 2013: 100.0})
    completions = pd.Series({2010: 60.0, 2011: 90.0, 2012: 95.0, 2013: 100.0})
    assert completion.completion_ratio(completions, permits, 2010, 2012, lag=1) == pytest.approx(0.95)


def test_completion_ratio_needs_every_year():
    permits = pd.Series({2010: 100.0, 2011: 100.0})
    completions = pd.Series({2011: 90.0})
    with pytest.raises(ValueError, match="missing years"):
        completion.completion_ratio(completions, permits, 2010, 2011, lag=1)


def test_factor_by_building_type_and_scenario():
    from lotline.config import load_params

    params = load_params("aggregate")
    assert completion.factor_key("ADU") == completion.factor_key("SFD") == "completion_factor_single_family"
    assert completion.factor_key("TH") == "completion_factor_single_family"  # Census counts townhouses as SF
    assert completion.factor_key("DTQ") == completion.factor_key("MF5") == "completion_factor_multifamily"
    assert completion.factor_key("UNKNOWN") == completion.factor_key("OTHER") == "completion_factor_all"
    assert completion.factor_key(scenario="missing_middle") == "completion_factor_multifamily"
    for key in {*completion.FACTOR_BY_TYPE.values(), *completion.FACTOR_BY_SCENARIO.values()}:
        assert key in params  # every mapped factor exists, with a source
    with pytest.raises(ValueError):
        completion.factor_key("SFD", scenario="adu")
