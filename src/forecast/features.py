"""Predictors for a direct forecast, built so none of them is unknown at the origin.

Forecasts here are direct: a separate model per horizon, whose features are all
lagged by at least the horizon relative to the month being predicted. A model
asked about twelve months ahead therefore never sees a value from eleven months
ahead, which an iterated one-step model would need and would have to invent.

Seasonal terms follow Irvin et al. (2021) and Li et al. (2026): a yearly sine and
cosine, plus a decimal position in the year. Lag depth follows the partial
autocorrelation of each series, which is significant at one and two months for
methane and one to three for carbon dioxide, and Li's one and two month
convention for covariates, adjusted for the horizon.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

#: Terms describing where in the year a month falls. Always available, whatever
#: the horizon, because they are properties of the calendar rather than of data.
SEASONAL_TERMS = ("sin_year", "cos_year", "year_fraction")

#: Recent-history lags at a one-month horizon, from the partial autocorrelation:
#: significant at one and two months for methane, one to three for carbon dioxide.
RECENT_LAGS = (1, 2, 3)

#: The annual lag is a different kind of predictor from the recent ones. It means
#: "the same month a year earlier" rather than "n months back from what is known",
#: so it is placed absolutely rather than shifted with the horizon.
SEASONAL_LAG = 12

#: Covariate lags at a one-month horizon, following Li et al. (2026).
BASE_COVARIATE_LAGS = (1, 2)


def seasonal_terms(index: pd.PeriodIndex) -> pd.DataFrame:
    """Yearly harmonics and the decimal position in the year."""
    month = np.asarray(index.month, dtype=float)
    fraction = (month - 1) / 12.0
    return pd.DataFrame(
        {
            "sin_year": np.sin(2 * np.pi * month / 12),
            "cos_year": np.cos(2 * np.pi * month / 12),
            "year_fraction": fraction,
        },
        index=index,
    )


def horizon_lags(lags: Sequence[int], horizon: int) -> tuple[int, ...]:
    """Recent-history lags for a direct model at `horizon`.

    The most recent value available at the origin is `horizon` months before the
    target, so a base lag of one means that value. Shifting the whole set keeps
    the spacing the partial autocorrelation identified rather than collapsing
    several lags onto one.
    """
    return tuple(sorted({lag + horizon - 1 for lag in lags}))


def annual_lag(horizon: int, period: int = SEASONAL_LAG) -> int:
    """The nearest whole year back that is still known at the forecast origin.

    At horizons up to a year this is twelve months, which is the origin month
    itself when the horizon is twelve. Beyond a year it steps to twenty-four.
    """
    multiple = period
    while multiple < horizon:
        multiple += period
    return multiple


def flux_lags_for(horizon: int, recent: Sequence[int] = RECENT_LAGS) -> tuple[int, ...]:
    """Every flux lag a direct model at `horizon` may use, recent and annual."""
    return tuple(sorted(set(horizon_lags(recent, horizon)) | {annual_lag(horizon)}))


def lagged(series: pd.Series, lags: Sequence[int], name: str) -> pd.DataFrame:
    """One column per lag, named so the horizon it survives is legible."""
    return pd.DataFrame({f"{name}_lag{lag}": series.shift(lag) for lag in lags})


def build_design(
    target: pd.Series,
    horizon: int,
    exogenous: pd.DataFrame | None = None,
    recent_lags: Sequence[int] = RECENT_LAGS,
    covariate_lags: Sequence[int] = BASE_COVARIATE_LAGS,
) -> pd.DataFrame:
    """Predictors indexed by the month being predicted.

    Every column is a value from at least `horizon` months before its row, so a
    row can be used to predict its own month without any of the predictors
    having been observed after the forecast was made.
    """
    frame = seasonal_terms(target.index)
    frame = frame.join(lagged(target, flux_lags_for(horizon, recent_lags), "flux"))
    if exogenous is not None:
        lags = horizon_lags(covariate_lags, horizon)
        for column in exogenous.columns:
            frame = frame.join(lagged(exogenous[column], lags, column))
    return frame
