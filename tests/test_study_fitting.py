"""Least-absolute-deviation fitting, intervals and error metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import fitting


def design_from(x: list) -> pd.DataFrame:
    months = pd.period_range("2015-01", periods=len(x), freq="M")
    return pd.DataFrame({"intercept": 1.0, "x": x}, index=months)


def test_exact_fit_recovers_the_generating_line():
    """Points on a line have zero absolute deviation, so the fit must be exact."""
    design = design_from([0.0, 1.0, 2.0, 3.0])
    target = pd.Series([2.0, 5.0, 8.0, 11.0], index=design.index)
    fit = fitting.fit_lad(design, target)

    assert fit.as_series()["intercept"] == pytest.approx(2.0, abs=1e-8)
    assert fit.as_series()["x"] == pytest.approx(3.0, abs=1e-8)
    assert np.allclose(fit.residuals, 0.0, atol=1e-8)


def test_absolute_deviation_ignores_a_single_outlier():
    """Median regression is unmoved by one extreme point; least squares is not."""
    design = design_from([0.0, 1.0, 2.0, 3.0, 4.0])
    clean = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0], index=design.index)
    contaminated = clean.copy()
    contaminated.iloc[-1] = 100.0

    lad = fitting.fit_lad(design, contaminated).as_series()["x"]
    least_squares = np.polyfit(design["x"], contaminated, 1)[0]

    assert lad == pytest.approx(1.0, abs=1e-6)
    assert least_squares > 5.0


def test_weights_move_the_fit_toward_the_weighted_points():
    design = design_from([0.0, 1.0, 2.0])
    target = pd.Series([0.0, 10.0, 0.0], index=design.index)
    heavy = pd.Series([1.0, 100.0, 1.0], index=design.index)

    unweighted = fitting.fit_lad(design, target)
    weighted = fitting.fit_lad(design, target, heavy)

    assert abs(weighted.residuals.iloc[1]) < abs(unweighted.residuals.iloc[1]) + 1e-9
    assert weighted.weighted is True
    assert unweighted.weighted is False


def test_non_positive_weights_are_rejected():
    design = design_from([0.0, 1.0])
    target = pd.Series([0.0, 1.0], index=design.index)
    with pytest.raises(ValueError, match="finite and positive"):
        fitting.fit_lad(design, target, pd.Series([1.0, 0.0], index=design.index))


def test_empirical_interval_brackets_the_prediction_by_residual_quantiles():
    design = design_from([0.0, 1.0, 2.0, 3.0])
    target = pd.Series([0.0, 1.0, 2.0, 3.0], index=design.index)
    fit = fitting.fit_lad(design, target)
    fit.residuals = pd.Series([-2.0, -1.0, 1.0, 2.0], index=design.index)

    prediction = pd.Series([10.0], index=[design.index[0]])
    interval = fitting.empirical_interval(fit, prediction, level=0.50)

    low, high = np.quantile([-2.0, -1.0, 1.0, 2.0], [0.25, 0.75])
    assert interval.loc[design.index[0], "lower"] == pytest.approx(10.0 + low)
    assert interval.loc[design.index[0], "upper"] == pytest.approx(10.0 + high)


def test_laplace_interval_widens_when_a_month_is_less_certain():
    design = design_from([0.0, 1.0])
    target = pd.Series([0.0, 1.0], index=design.index)
    fit = fitting.fit_lad(design, target)
    fit.laplace_scale = 1.0
    prediction = pd.Series([0.0, 0.0], index=design.index)

    narrow = fitting.laplace_interval(fit, prediction, 0.90, pd.Series([0.0, 0.0], index=design.index))
    wide = fitting.laplace_interval(fit, prediction, 0.90, pd.Series([0.0, 5.0], index=design.index))

    assert wide.loc[design.index[1], "upper"] > narrow.loc[design.index[1], "upper"]
    assert wide.loc[design.index[0], "upper"] == pytest.approx(narrow.loc[design.index[0], "upper"])


def test_laplace_interval_is_symmetric_about_the_prediction():
    design = design_from([0.0, 1.0])
    fit = fitting.fit_lad(design, pd.Series([0.0, 1.0], index=design.index))
    fit.laplace_scale = 2.0
    prediction = pd.Series([7.0, 7.0], index=design.index)
    interval = fitting.laplace_interval(fit, prediction, 0.90)

    width_below = interval["prediction"] - interval["lower"]
    width_above = interval["upper"] - interval["prediction"]
    assert np.allclose(width_below, width_above)


def test_coverage_counts_observations_inside_their_interval():
    index = pd.period_range("2015-01", periods=4, freq="M")
    interval = pd.DataFrame({"lower": [0.0] * 4, "upper": [1.0] * 4}, index=index)
    observed = pd.Series([0.5, 0.5, 2.0, -1.0], index=index)
    assert fitting.coverage(interval, observed) == 0.5


def test_bias_sign_means_observed_minus_predicted():
    """A prediction below the observation must give a positive bias."""
    index = pd.period_range("2015-01", periods=2, freq="M")
    observed = pd.Series([1.0, 1.0], index=index)
    under = pd.Series([0.5, 0.5], index=index)
    over = pd.Series([1.5, 1.5], index=index)

    assert fitting.error_metrics(observed, under)["bias_log_obs_minus_pred"] > 0
    assert fitting.error_metrics(observed, over)["bias_log_obs_minus_pred"] < 0
    assert fitting.BIAS_CONVENTION == "observed minus predicted"


def test_error_metrics_on_a_hand_computed_case():
    """Log residuals of +ln2 and -ln2 give a mean absolute error of ln2."""
    index = pd.period_range("2015-01", periods=2, freq="M")
    observed = pd.Series([np.log(2.0), np.log(2.0)], index=index)
    predicted = pd.Series([0.0, np.log(4.0)], index=index)
    metrics = fitting.error_metrics(observed, predicted)

    assert metrics["n"] == 2
    assert metrics["mae_log"] == pytest.approx(np.log(2.0))
    assert metrics["bias_log_obs_minus_pred"] == pytest.approx(0.0)
    # On the flux scale the errors are 2-1 = 1 and 2-4 = -2.
    assert metrics["mae_flux"] == pytest.approx(1.5)
    assert metrics["bias_flux_obs_minus_pred"] == pytest.approx(-0.5)


def test_back_transform_undoes_the_logarithm():
    index = pd.period_range("2015-01", periods=1, freq="M")
    interval = pd.DataFrame(
        {"prediction": [np.log(10.0)], "lower": [np.log(5.0)], "upper": [np.log(20.0)]}, index=index
    )
    flux = fitting.back_transform(interval)
    assert flux.loc[index[0], "prediction"] == pytest.approx(10.0)
    assert flux.loc[index[0], "lower"] == pytest.approx(5.0)
