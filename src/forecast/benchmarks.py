"""Benchmarks a forecasting method has to beat before it has shown anything.

A method that cannot outperform a naive rule on a strongly seasonal series has
demonstrated nothing, so these are built and scored before any model is fitted.
All four take only the training window and produce forecasts for named target
months, so nothing they use is unavailable at the moment a forecast is made.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

PERIOD = 12


def _targets(train: pd.Series, horizons: Sequence[int]) -> pd.PeriodIndex:
    """The months a forecast made at the end of `train` is asked about."""
    origin = train.index[-1]
    return pd.PeriodIndex([origin + h for h in horizons], freq=train.index.freq)


def seasonal_naive(train: pd.Series, horizons: Sequence[int], period: int = PERIOD) -> pd.Series:
    """This month equals the same month one year earlier.

    The last observed value at the target's month of year is used, so a gap in
    the previous year falls back to the year before rather than to nothing.
    """
    out = {}
    for target in _targets(train, horizons):
        same_month = train[(train.index.month == target.month) & train.notna()]
        out[target] = float(same_month.iloc[-1]) if len(same_month) else np.nan
    return pd.Series(out, name="seasonal naive")


def naive(train: pd.Series, horizons: Sequence[int]) -> pd.Series:
    """Every future month equals the last observed value."""
    observed = train.dropna()
    value = float(observed.iloc[-1]) if len(observed) else np.nan
    return pd.Series({t: value for t in _targets(train, horizons)}, name="naive")


def climatology(train: pd.Series, horizons: Sequence[int]) -> pd.Series:
    """Every month equals its month-of-year mean over the training window.

    This is the benchmark that matters most here. If it wins, the series is
    predictable from its seasonal average and little else, which is a finding
    about the peatland rather than a baseline to clear.
    """
    means = train.dropna().groupby(train.dropna().index.month).mean()
    out = {t: float(means.get(t.month, np.nan)) for t in _targets(train, horizons)}
    return pd.Series(out, name="climatology")


def seasonal_naive_drift(
    train: pd.Series, horizons: Sequence[int], period: int = PERIOD
) -> pd.Series:
    """Seasonal naive, plus the average year-on-year change per month.

    Drift is the mean of the annual differences over the training window,
    divided across the twelve months separating them, so a series trending
    upward is not forecast flat.
    """
    observed = train.dropna()
    annual = observed - observed.shift(period)
    drift = float(annual.dropna().mean()) / period if annual.notna().any() else 0.0

    base = seasonal_naive(train, horizons, period)
    origin = train.index[-1]
    steps = pd.Series({t: (t - origin).n for t in base.index})
    return (base + drift * steps).rename("seasonal naive with drift")


#: Every benchmark, in the order they are reported.
BENCHMARKS = {
    "seasonal naive": seasonal_naive,
    "naive": naive,
    "climatology": climatology,
    "seasonal naive with drift": seasonal_naive_drift,
}
