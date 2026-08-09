"""Inverse-variance weighting of the monthly series."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import weights


def monthly(se: list, days: list | None = None, flux: list | None = None) -> pd.DataFrame:
    months = pd.period_range("2015-01", periods=len(se), freq="M")
    n = len(se)
    return pd.DataFrame(
        {
            "fch4_mean": flux if flux is not None else [10.0] * n,
            "fch4_days": days if days is not None else [20] * n,
            "fch4_halfhours": [400] * n,
            "fch4_sd_across_days": [s * 4 for s in se],
            "fch4_se_across_days": se,
        },
        index=months,
    )


def test_weight_is_the_reciprocal_of_squared_standard_error():
    frame = monthly([1.0, 2.0])
    w = weights.inverse_variance_weights(frame)
    assert list(w) == [1.0, 0.25]


def test_a_month_without_a_standard_error_gets_no_weight():
    """Null rather than zero, so it cannot be silently included."""
    frame = monthly([1.0, np.nan, 0.0])
    w = weights.inverse_variance_weights(frame)
    assert w.iloc[0] == 1.0
    assert pd.isna(w.iloc[1])
    assert pd.isna(w.iloc[2])


def test_concentration_reports_effective_sample_size():
    """Equal weights give an effective sample size equal to the count."""
    frame = monthly([1.0] * 10)
    table = weights.weight_concentration(frame, frame.index).set_index("group")
    row = table.loc["effective sample size, sum(w)^2 / sum(w^2)"]
    assert row["share_of_total_weight_pct"] == pytest.approx(10.0)


def test_unequal_weights_reduce_the_effective_sample_size():
    frame = monthly([1.0, 1.0, 1.0, 10.0])
    table = weights.weight_concentration(frame, frame.index).set_index("group")
    effective = table.loc["effective sample size, sum(w)^2 / sum(w^2)", "share_of_total_weight_pct"]
    assert effective < 4.0


def test_least_influential_picks_the_largest_standard_error():
    frame = monthly([1.0, 5.0, 2.0])
    table = weights.least_influential(frame, frame.index, n=1)
    assert table.index[0] == "2015-02"
    assert table.iloc[0]["relative_weight_pct"] < table.iloc[0]["equal_weight_pct"]


def test_most_influential_picks_the_smallest_standard_error():
    frame = monthly([1.0, 5.0, 2.0])
    table = weights.most_influential(frame, frame.index, n=1)
    assert table.index[0] == "2015-01"


def test_seasonal_balance_shows_weight_moving_away_from_noisy_months():
    """A precise winter month and a noisy summer month must not share weight equally."""
    frame = monthly([0.5, 5.0], flux=[10.0, 80.0])
    table = weights.seasonal_weight_balance(frame, frame.index)
    january, february = table.loc[1], table.loc[2]

    assert january["weight_share_pct"] > january["equal_share_pct"]
    assert february["weight_share_pct"] < february["equal_share_pct"]
    assert table["weight_share_pct"].sum() == pytest.approx(100.0)


def test_summary_covers_every_month_in_the_window():
    frame = monthly([1.0, 2.0, 3.0])
    described = weights.weight_summary(frame, frame.index)
    assert described.loc["count", "standard_error"] == 3.0
