"""Comparison of covariate distributions between two periods."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import stationarity


def seasonal_frame(years: int = 4, shift: float = 0.0) -> pd.DataFrame:
    months = pd.period_range("2000-01", periods=12 * years, freq="M")
    cycle = np.tile(np.cos(np.linspace(0, 2 * np.pi, 12, endpoint=False)), years)
    step = np.where(np.arange(len(months)) >= len(months) // 2, shift, 0.0)
    return pd.DataFrame({"x": cycle * 10 + step}, index=months)


def test_deseasonalise_removes_a_pure_seasonal_cycle():
    frame = seasonal_frame(4)
    anomalies = stationarity.deseasonalise(frame["x"])
    assert np.allclose(anomalies, 0.0, atol=1e-9)


def test_compare_detects_a_level_shift():
    frame = seasonal_frame(4, shift=5.0)
    half = len(frame) // 2
    early, late = frame.index[:half], frame.index[half:]
    table = stationarity.compare_periods(frame, late, early, ("x",)).iloc[0]

    assert table["mean_difference"] == pytest.approx(-5.0)
    assert table["mann_whitney_p"] < 0.05


def test_compare_finds_nothing_when_periods_match():
    frame = seasonal_frame(4)
    half = len(frame) // 2
    table = stationarity.compare_periods(frame, frame.index[half:], frame.index[:half], ("x",)).iloc[0]

    assert table["mean_difference"] == pytest.approx(0.0)
    assert table["mann_whitney_p"] > 0.05
    assert table["cliffs_delta"] == pytest.approx(0.0, abs=1e-9)


def test_deseasonalised_comparison_survives_uneven_month_composition():
    """Comparing whole years against summer months alone is a seasonal artifact."""
    frame = seasonal_frame(4)
    summer = pd.PeriodIndex([p for p in frame.index if p.month in (6, 7, 8)], freq="M")
    winter = pd.PeriodIndex([p for p in frame.index if p.month in (12, 1, 2)], freq="M")

    raw = stationarity.compare_periods(frame, winter, summer, ("x",)).iloc[0]
    adjusted = stationarity.compare_periods(frame, winter, summer, ("x",), deseasonalised=True).iloc[0]

    assert abs(raw["mean_difference"]) > 1.0
    assert adjusted["mean_difference"] == pytest.approx(0.0, abs=1e-9)


def test_annual_means_carry_their_month_count():
    frame = seasonal_frame(2)
    partial = frame.index[:15]
    table = stationarity.annual_means(frame, ("x",), partial)

    assert table.loc[2000, "n_months"] == 12
    assert table.loc[2001, "n_months"] == 3


def test_early_late_contrast_reports_the_difference_between_named_spans():
    frame = seasonal_frame(4, shift=5.0)
    table = stationarity.early_late_contrast(
        frame, ("x",), ("2000-01", "2001-12"), ("2002-01", "2003-12")
    ).iloc[0]
    assert table["difference"] == pytest.approx(5.0)
