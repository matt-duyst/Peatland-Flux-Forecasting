"""Benchmarks and the rolling-origin harness, on synthetic monthly series."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecast import benchmarks, evaluation


def seasonal(n: int = 96, amplitude: float = 10.0, level: float = 20.0, slope: float = 0.0):
    months = pd.period_range("2000-01", periods=n, freq="M")
    t = np.arange(n)
    return pd.Series(level + slope * t + amplitude * np.sin(2 * np.pi * t / 12), index=months)


def noisy(n: int = 96, seed: int = 0):
    """A seasonal series with noise, so year-on-year differences are not zero."""
    rng = np.random.default_rng(seed)
    return seasonal(n) + rng.normal(0, 2.0, n)


def test_seasonal_naive_repeats_the_same_month_a_year_earlier():
    s = seasonal()
    out = benchmarks.seasonal_naive(s.iloc[:60], [1, 12])
    assert out.iloc[0] == pytest.approx(s.iloc[60 - 12])
    assert out.iloc[1] == pytest.approx(s.iloc[59])


def test_climatology_is_the_training_month_of_year_mean():
    s = seasonal()
    train = s.iloc[:60]
    out = benchmarks.climatology(train, [1])
    target = train.index[-1] + 1
    assert out.iloc[0] == pytest.approx(train[train.index.month == target.month].mean())


def test_drift_follows_a_trending_series_where_seasonal_naive_stays_flat():
    s = seasonal(slope=0.5)
    train = s.iloc[:60]
    flat = benchmarks.seasonal_naive(train, [12]).iloc[0]
    drifted = benchmarks.seasonal_naive_drift(train, [12]).iloc[0]
    assert drifted > flat


def test_a_gap_in_the_previous_year_falls_back_rather_than_failing():
    s = seasonal()
    s.iloc[48] = np.nan                      # the month seasonal naive would reach for
    train = s.iloc[:60]
    out = benchmarks.seasonal_naive(train, [12])
    assert np.isfinite(out.iloc[0])


def test_the_scaled_error_denominator_uses_training_data_only():
    """MASE is defined against the training window, never the test window."""
    s = noisy()
    train = s.iloc[:60]
    assert evaluation.mase_scale(train) == pytest.approx(
        (train - train.shift(12)).abs().mean())
    assert evaluation.mase_scale(train) != pytest.approx(evaluation.mase_scale(s))


def test_a_perfectly_periodic_window_has_no_scale_to_divide_by():
    """Zero would make every scaled error infinite, so the origin is unscorable."""
    assert np.isnan(evaluation.mase_scale(seasonal()))


def test_no_forecast_is_made_from_a_window_reaching_its_own_target():
    """The leakage guard: every origin must precede every month it predicts."""
    s = seasonal()
    frame = evaluation.rolling_forecasts(s, benchmarks.BENCHMARKS)
    assert (frame["target"] > frame["origin"]).all()
    assert (frame["horizon"] == (frame["target"] - frame["origin"]).map(lambda d: d.n)).all()


def test_origins_respect_the_minimum_training_window():
    s = seasonal()
    got = evaluation.origins(s, min_train=60, horizons=(1,))
    assert min(evaluation.rolling_forecasts(s, benchmarks.BENCHMARKS)["train_n"]) >= 60
    assert len(got) == len(s) - 60          # every later month, save those without a target


def test_a_target_never_observed_is_dropped_rather_than_scored():
    s = seasonal()
    s.iloc[70] = np.nan
    frame = evaluation.rolling_forecasts(s, benchmarks.BENCHMARKS)
    scored = frame.dropna(subset=["actual"])
    assert s.index[70] not in set(scored["target"])
    assert evaluation.origin_summary(frame)["dropped, target never observed"] > 0


def test_scores_carry_no_percentage_measure():
    """Undefined for a series crossing zero, and dominated by near-zero months."""
    s = seasonal()
    table = evaluation.score(evaluation.rolling_forecasts(s, benchmarks.BENCHMARKS))
    assert not any("MAPE" in c.upper() or "PERCENT" in c.upper() for c in table.columns)
    assert {"MASE", "MAE", "RMSE"} <= set(table.columns)


def test_persistence_degrades_with_horizon_while_a_seasonal_rule_does_not():
    s = noisy()
    table = evaluation.score(evaluation.rolling_forecasts(s, benchmarks.BENCHMARKS))
    naive = table[table["method"] == "naive"].set_index("horizon")["MASE"]
    clim = table[table["method"] == "climatology"].set_index("horizon")["MASE"]
    assert naive[6] > naive[1]
    assert clim[6] == pytest.approx(clim[1], abs=0.05)
