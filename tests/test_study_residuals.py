"""Monthly error decomposition and concentration."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import residuals, targets


def months(n: int, start: str = "2011-01") -> pd.PeriodIndex:
    return pd.period_range(start, periods=n, freq="M")


def test_monthly_comparison_converts_flux_to_carbon_mass():
    """A month of 10 nmol per square metre per second carries a known carbon mass."""
    index = pd.period_range("2011-01", periods=1, freq="M")
    observed = pd.Series([10.0], index=index)
    predicted = pd.Series([10.0], index=index)
    frame = residuals.monthly_comparison(observed, predicted)

    expected = 10.0 * 31 * 86400 * 1e-9 * targets.MOLAR_MASS_CH4 * targets.C_PER_CH4
    assert frame.loc[index[0], "observed_g_C"] == pytest.approx(expected)
    assert frame.loc[index[0], "shortfall_g_C"] == pytest.approx(0.0)
    assert frame.loc[index[0], "ratio"] == pytest.approx(1.0)


def test_shortfall_is_positive_when_the_model_predicts_low():
    index = months(1)
    frame = residuals.monthly_comparison(
        pd.Series([20.0], index=index), pd.Series([10.0], index=index)
    )
    assert frame.loc[index[0], "shortfall_g_C"] > 0
    assert frame.loc[index[0], "ratio"] == pytest.approx(0.5)


def test_concentration_detects_a_shortfall_carried_by_one_month():
    index = months(4)
    frame = pd.DataFrame(
        {"shortfall_g_C": [0.0, 0.0, 3.0, 0.0]}, index=index
    )
    out = residuals.concentration(frame)
    assert out["top_1_share_of_total_pct"] == pytest.approx(100.0)
    assert out["largest_month"] == str(index[2])
    assert out["n_months_under_predicted"] == 1


def test_concentration_detects_an_evenly_spread_shortfall():
    index = months(4)
    frame = pd.DataFrame({"shortfall_g_C": [1.0, 1.0, 1.0, 1.0]}, index=index)
    out = residuals.concentration(frame)
    assert out["top_1_share_of_total_pct"] == pytest.approx(25.0)
    assert out["n_months_under_predicted"] == 4


def test_covariate_anomaly_standardises_by_the_reference_spread():
    index = months(8, "2010-01")
    covariates = pd.DataFrame({"x": [0, 0, 0, 0, 2, 2, 2, 2]}, index=index, dtype=float)
    table = residuals.covariate_anomaly(
        covariates, index[4:], index[:4], ("x",)
    )
    assert table.loc[0, "difference"] == pytest.approx(2.0)
    # The reference has zero spread, so the standardised value is undefined.
    assert np.isnan(table.loc[0, "standardised"])


def test_extreme_months_ranks_by_departure_from_the_same_calendar_month():
    reference = pd.Series(
        [10.0, 14.0, 12.0, 12.0, 16.0, 10.0],
        index=pd.PeriodIndex(
            ["2012-07", "2012-08", "2013-07", "2013-08", "2014-07", "2014-08"], freq="M"
        ),
    )
    observed = pd.Series(
        [13.0, 40.0], index=pd.PeriodIndex(["2011-07", "2011-08"], freq="M")
    )
    table = residuals.extreme_months(observed, reference, n=2)
    assert table.index[0] == "2011-08"
    assert table.loc["2011-08", "standardised"] > table.loc["2011-07", "standardised"]


def test_extreme_months_leaves_a_spreadless_month_undefined():
    """One reference observation, or identical ones, gives no spread to divide by."""
    reference = pd.Series(
        [10.0, 10.0], index=pd.PeriodIndex(["2012-07", "2013-07"], freq="M")
    )
    observed = pd.Series([20.0], index=pd.PeriodIndex(["2011-07"], freq="M"))
    table = residuals.extreme_months(observed, reference, n=1)
    assert np.isnan(table.loc["2011-07", "standardised"])
