"""Seasonal adjustment, fitted on training months and applied to later ones.

Makridakis et al. (2018) deseasonalize where a significant autocorrelation at the
seasonal lag exists, and detrend where a trend test fires. Both gases here show a
significant lag-12 autocorrelation and neither shows a trend, so the first step is
applied and the second is not: running a step whose diagnostic did not fire would
remove something that is not there.

The month-of-year means come from the training window alone. Fitting them on the
whole record would let a model see the level of the months it is being scored on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class SeasonalAdjustment:
    """Month-of-year means, learned from one window and applied to another."""

    def __init__(self) -> None:
        self.means: pd.Series | None = None
        self.overall: float = np.nan

    def fit(self, series: pd.Series) -> "SeasonalAdjustment":
        observed = series.dropna()
        self.means = observed.groupby(observed.index.month).mean()
        self.overall = float(observed.mean())
        return self

    def _expected(self, index: pd.PeriodIndex) -> np.ndarray:
        if self.means is None:
            raise RuntimeError("fit the adjustment on a training window first")
        return np.array([self.means.get(month, self.overall) for month in index.month])

    def transform(self, series: pd.Series) -> pd.Series:
        """Remove the seasonal level, leaving what the seasonal mean does not explain."""
        return series - self._expected(series.index)

    def inverse(self, values: pd.Series) -> pd.Series:
        """Put the seasonal level back, so predictions are on the original scale."""
        return values + self._expected(values.index)
