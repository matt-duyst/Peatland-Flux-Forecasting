"""Rolling-origin evaluation, and the error measures the comparison is scored on.

Every forecast is made from a training window that ends before the month it
predicts, so nothing is scored on data the method could have seen. The scale in
the denominator of the scaled error comes from the training window alone, for the
same reason.

Forecasts from neighboring origins overlap heavily, so the count of forecasts
overstates the information behind a score. `origin_summary` reports the number
of origins and of distinct target months alongside every distribution.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd

HORIZONS = (1, 3, 6, 12)
MIN_TRAIN = 60
PERIOD = 12


def mase_scale(train: pd.Series, period: int = PERIOD) -> float:
    """Mean absolute error of the seasonal naive forecast on the training window.

    This is the denominator of the mean absolute scaled error, and it is
    computed on training data only. A scaled error above one means the method
    did worse than seasonal naive managed in sample.
    """
    observed = train.dropna()
    differences = (observed - observed.shift(period)).dropna()
    if differences.empty:
        return np.nan
    scale = float(differences.abs().mean())
    # A perfectly periodic training window leaves nothing to scale against, and
    # would make every scaled error infinite. The test is relative to the series
    # magnitude rather than against exact zero, because a periodic series built
    # in floating point differs from itself by about 1e-14 rather than by 0.
    magnitude = float(observed.abs().mean())
    if scale <= 1e-10 * max(magnitude, 1.0):
        return np.nan
    return scale


def origins(series: pd.Series, min_train: int = MIN_TRAIN,
            horizons: Sequence[int] = HORIZONS) -> list[pd.Period]:
    """Every month that can serve as a forecast origin.

    An origin qualifies when the window up to and including it holds at least
    `min_train` observations and at least one target month lies inside the
    record. The window expands rather than slides, so later origins are better
    informed, which is what a forecaster would actually have.
    """
    out = []
    last = series.index[-1]
    for position, month in enumerate(series.index):
        window = series.iloc[: position + 1]
        if window.notna().sum() < min_train:
            continue
        if any(month + h <= last for h in horizons):
            out.append(month)
    return out


def rolling_forecasts(
    series: pd.Series,
    methods: dict[str, Callable[..., pd.Series]],
    min_train: int = MIN_TRAIN,
    horizons: Sequence[int] = HORIZONS,
    period: int = PERIOD,
) -> pd.DataFrame:
    """One row per origin, method and horizon, with the forecast and its target.

    Rows whose target month was never observed are dropped and counted by the
    caller: a gap in the record is not a forecast failure.
    """
    rows = []
    for origin in origins(series, min_train, horizons):
        train = series.loc[:origin]
        scale = mase_scale(train, period)
        for name, method in methods.items():
            forecast = method(train, horizons)
            for horizon, (target, value) in zip(horizons, forecast.items()):
                actual = series.get(target, np.nan)
                rows.append(
                    {
                        "origin": origin, "method": name, "horizon": horizon,
                        "target": target, "forecast": value, "actual": actual,
                        "train_n": int(train.notna().sum()), "mase_scale": scale,
                    }
                )
    frame = pd.DataFrame(rows)
    frame["error"] = frame["actual"] - frame["forecast"]
    frame["scaled"] = frame["error"].abs() / frame["mase_scale"]
    return frame


def score(frame: pd.DataFrame) -> pd.DataFrame:
    """Error measures per method and horizon, over the forecasts that could be scored.

    Percentage errors are deliberately absent. They are undefined for a series
    crossing zero, which carbon dioxide does, and they are dominated by the
    smallest values for methane, whose winters run near zero.
    """
    usable = frame.dropna(subset=["actual", "forecast", "mase_scale"])
    grouped = usable.groupby(["method", "horizon"])
    out = pd.DataFrame(
        {
            "n": grouped.size(),
            "MASE": grouped["scaled"].mean(),
            "MASE_median": grouped["scaled"].median(),
            "MASE_q25": grouped["scaled"].quantile(0.25),
            "MASE_q75": grouped["scaled"].quantile(0.75),
            "MAE": grouped["error"].apply(lambda e: e.abs().mean()),
            "RMSE": grouped["error"].apply(lambda e: np.sqrt((e ** 2).mean())),
            "share_beating_snaive": grouped["scaled"].apply(lambda s: (s < 1).mean()),
        }
    )
    return out.reset_index()


def relative_to(frame: pd.DataFrame, reference: str = "seasonal naive") -> pd.DataFrame:
    """Each method's error as a ratio to one benchmark, over the same target months.

    The scaled error divides by a benchmark computed on the *training* window,
    which makes it comparable across methods within a series but not across
    series: a gas whose training period is harder than its test period carries a
    deflated scaled error. This ratio uses the benchmark measured on the same
    months being scored, so it is comparable across gases.
    """
    usable = frame.dropna(subset=["actual", "forecast"])
    mae = usable.assign(absolute=usable["error"].abs()).groupby(
        ["method", "horizon"])["absolute"].mean().unstack(0)
    out = mae.div(mae[reference], axis=0)
    out.columns.name = None
    return out.reset_index()


def origin_summary(frame: pd.DataFrame) -> dict[str, int]:
    """What the scores actually rest on, as against how many rows there are."""
    usable = frame.dropna(subset=["actual", "forecast", "mase_scale"])
    return {
        "origins": usable["origin"].nunique(),
        "distinct target months": usable["target"].nunique(),
        "scored forecasts": len(usable),
        "dropped, target never observed": int(frame["actual"].isna().sum()),
    }


def per_origin(frame: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Scaled error by origin for one horizon, for showing the spread."""
    usable = frame[(frame["horizon"] == horizon)].dropna(subset=["scaled"])
    return usable.pivot_table(index="origin", columns="method", values="scaled")
