"""Covariate transforms and the design matrix built from them."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from study import features


def covariate_frame(soil_f: list, wte: list, start: str = "2015-01") -> pd.DataFrame:
    months = pd.period_range(start, periods=len(soil_f), freq="M")
    return pd.DataFrame({"soil_temp_f": soil_f, "wte_m": wte}, index=months)


def test_fahrenheit_converts_at_known_points():
    values = features.fahrenheit_to_celsius(pd.Series([32.0, 212.0, 50.0]))
    assert list(values) == [0.0, 100.0, 10.0]


def test_clamp_bounds_come_from_the_named_months_only():
    cov = covariate_frame([40.0] * 4, [1.0, 2.0, 3.0, 99.0])
    bounds = features.clamp_bounds(cov, cov.index[:3], "wte_m")
    assert bounds == (1.0, 3.0)


def test_clamp_holds_values_at_the_edge():
    clamped = features.clamp(pd.Series([0.0, 2.0, 5.0]), (1.0, 3.0))
    assert list(clamped) == [1.0, 2.0, 3.0]


def test_design_clamps_the_holdout_to_the_training_range():
    """A month wetter than anything trained on must not push the term past the edge."""
    cov = covariate_frame([50.0, 50.0, 50.0], [1.0, 2.0, 9.0])
    train = cov.index[:2]
    bounds = features.clamp_bounds(cov, train, "wte_m")
    design = features.build_design(cov, cov.index, bounds, include_water_table=True)

    assert design.loc[cov.index[2], "water_table_clamped"] == 2.0
    assert list(design.columns) == ["intercept", "soil_temp_c", "water_table_clamped"]
    assert (design["intercept"] == 1.0).all()


def test_design_omits_the_water_table_term_when_asked():
    cov = covariate_frame([50.0, 50.0], [1.0, 2.0])
    design = features.build_design(cov, cov.index, None, include_water_table=False)
    assert list(design.columns) == ["intercept", "soil_temp_c"]


def test_design_requires_bounds_when_the_term_is_included():
    cov = covariate_frame([50.0], [1.0])
    with pytest.raises(ValueError, match="bounds are required"):
        features.build_design(cov, cov.index, None, include_water_table=True)


def test_q10_and_slope_are_inverses():
    assert features.q10_from_slope(features.slope_from_q10(2.9)) == pytest.approx(2.9)
    # A Q10 of 2.9 means log flux rises by ln(2.9) over ten degrees.
    assert features.slope_from_q10(2.9) == pytest.approx(math.log(2.9) / 10)


def test_log_target_rejects_non_positive_flux():
    monthly = pd.DataFrame(
        {"fch4_mean": [1.0, 0.0]}, index=pd.period_range("2015-01", periods=2, freq="M")
    )
    with pytest.raises(ValueError, match="strictly positive"):
        features.log_target(monthly, monthly.index)


def test_log_standard_error_is_the_relative_error():
    monthly = pd.DataFrame(
        {"fch4_mean": [10.0, 50.0], "fch4_se_across_days": [1.0, 5.0]},
        index=pd.period_range("2015-01", periods=2, freq="M"),
    )
    scale = features.log_standard_error(monthly, monthly.index)
    assert list(scale) == [0.1, 0.1]


def test_log_target_matches_numpy():
    monthly = pd.DataFrame(
        {"fch4_mean": [2.0, 20.0]}, index=pd.period_range("2015-01", periods=2, freq="M")
    )
    assert list(features.log_target(monthly, monthly.index)) == [np.log(2.0), np.log(20.0)]


def test_warming_limb_marks_rising_soil_temperature():
    """The limb follows the sign of the change from the preceding month."""
    months = pd.period_range("2015-01", periods=4, freq="M")
    cov = pd.DataFrame({"soil_temp_f": [30.0, 40.0, 50.0, 45.0], "wte_m": [1.0] * 4}, index=months)
    limb = features.warming_limb(cov, months)

    assert bool(limb.iloc[0]) is False   # no preceding month
    assert bool(limb.iloc[1]) is True
    assert bool(limb.iloc[2]) is True
    assert bool(limb.iloc[3]) is False


def test_hysteresis_adds_an_interaction_only_when_requested():
    months = pd.period_range("2015-01", periods=3, freq="M")
    cov = pd.DataFrame({"soil_temp_f": [30.0, 40.0, 50.0], "wte_m": [1.0] * 3}, index=months)
    plain = features.build_design(cov, months, (1.0, 1.0), True, include_hysteresis=False)
    split = features.build_design(cov, months, (1.0, 1.0), True, include_hysteresis=True)

    assert "soil_temp_c_warming" not in plain.columns
    assert list(split.columns)[-2:] == ["warming_limb", "soil_temp_c_warming"]
    # On a cooling month the interaction is zero; on a warming month it equals the slope term.
    assert split.iloc[0]["soil_temp_c_warming"] == 0.0
    assert split.iloc[1]["soil_temp_c_warming"] == pytest.approx(split.iloc[1]["soil_temp_c"])
