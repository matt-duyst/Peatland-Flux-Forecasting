"""Bias direction, its multiplicative reading, and the separability checks."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import bias


def test_direction_labels_follow_the_convention():
    assert bias.direction(0.5) == "model predicts low"
    assert bias.direction(-0.5) == "model predicts high"
    assert bias.direction(0.001) == "no material bias"


def test_ratio_converts_a_log_bias_to_a_multiplicative_error():
    """A bias of ln(2) means the prediction sat at half the observation."""
    out = bias.as_ratio(np.log(2.0))
    assert out["predicted_over_observed"] == pytest.approx(0.5)
    assert out["prediction_error_pct"] == pytest.approx(-50.0)


def test_zero_bias_is_no_multiplicative_error():
    out = bias.as_ratio(0.0)
    assert out["predicted_over_observed"] == pytest.approx(1.0)
    assert out["prediction_error_pct"] == pytest.approx(0.0)


def test_opposite_components_cancel_completely():
    combined = bias.combine_additively({"a": 0.3, "b": -0.3})
    assert combined["bias_log_obs_minus_pred"] == pytest.approx(0.0)
    assert combined["cancellation_share"] == pytest.approx(1.0)


def test_same_sign_components_compound_without_cancelling():
    combined = bias.combine_additively({"a": 0.2, "b": 0.1})
    assert combined["bias_log_obs_minus_pred"] == pytest.approx(0.3)
    assert combined["cancellation_share"] == pytest.approx(0.0)
    assert combined["direction"] == "model predicts low"


def test_partial_cancellation_is_reported_as_a_share():
    """Components of +0.2 and -0.1 leave 0.1 of a summed magnitude of 0.3."""
    combined = bias.combine_additively({"a": 0.2, "b": -0.1})
    assert combined["bias_log_obs_minus_pred"] == pytest.approx(0.1)
    assert combined["cancellation_share"] == pytest.approx(2 / 3)


def test_axis_independence_detects_a_trend_and_its_absence():
    months = pd.period_range("2010-01", periods=36, freq="M")
    covariates = pd.DataFrame(
        {"trending": np.arange(36.0), "flat": np.tile([1.0, 2.0, 3.0], 12)}, index=months
    )
    trending = bias.axis_independence(covariates, months, "trending")
    flat = bias.axis_independence(covariates, months, "flat")

    assert trending["correlation_with_time"] == pytest.approx(1.0)
    assert abs(flat["correlation_with_time"]) < 0.2


def test_band_split_exposes_a_bias_that_varies_with_the_covariate():
    """A residual rising with the covariate must not read as one uniform bias."""
    months = pd.period_range("2010-01", periods=9, freq="M")
    observed = pd.Series(np.arange(9.0), index=months)
    predicted = observed - np.linspace(-1.0, 1.0, 9)
    covariate = pd.Series(np.arange(9.0), index=months)

    table = bias.bias_by_covariate_band(observed, pd.Series(predicted, index=months), covariate, 3)
    assert len(table) == 3
    assert table["bias_log_obs_minus_pred"].iloc[0] < 0
    assert table["bias_log_obs_minus_pred"].iloc[-1] > 0
    assert table["direction"].iloc[0] == "model predicts high"
    assert table["direction"].iloc[-1] == "model predicts low"
