"""Monthly aggregation of sub-daily values, retaining the weight behind each mean.

Every aggregate carries the observation count, standard deviation and standard
error alongside the mean, so months resting on a handful of observations stay
distinguishable from months resting on hundreds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STATS = ("mean", "n", "sd", "se")


def monthly_stats(
    frame: pd.DataFrame,
    value_column: str,
    timestamp_column: str = "timestamp_start",
    prefix: str | None = None,
) -> pd.DataFrame:
    """Aggregate a sub-daily series to a monthly mean, count, deviation and error.

    Indexed by month. The standard deviation is the sample deviation and is
    undefined for counts below two; the standard error is that deviation
    divided by the square root of the count.
    """
    prefix = prefix if prefix is not None else value_column.lower()
    values = frame[[timestamp_column, value_column]].dropna(subset=[value_column])
    month = values[timestamp_column].dt.to_period("M")

    grouped = values.groupby(month)[value_column]
    out = pd.DataFrame(
        {
            f"{prefix}_mean": grouped.mean(),
            f"{prefix}_n": grouped.size().astype("int64"),
            f"{prefix}_sd": grouped.std(ddof=1),
        }
    )
    out[f"{prefix}_se"] = out[f"{prefix}_sd"] / np.sqrt(out[f"{prefix}_n"])
    out.index.name = "month"
    return out


def monthly_stats_all_columns(
    frame: pd.DataFrame,
    value_columns: tuple[str, ...],
    timestamp_column: str = "timestamp_start",
) -> pd.DataFrame:
    """Aggregate several value columns independently and join them on month.

    Each column is summarized on its own; no coalescing between columns occurs.
    """
    parts = [
        monthly_stats(frame, column, timestamp_column=timestamp_column)
        for column in value_columns
    ]
    return pd.concat(parts, axis=1).sort_index()


def observation_count_distribution(stats: pd.DataFrame, count_column: str) -> pd.Series:
    """Summarize the distribution of observation counts across months."""
    counts = stats[count_column].dropna()
    described = counts.describe()
    for threshold in (10, 30, 100):
        described[f"months_under_{threshold}"] = int((counts < threshold).sum())
    return described


def month_grid(start: str, end: str) -> pd.PeriodIndex:
    """Regular monthly index, so months without data remain present as NaN rows."""
    return pd.period_range(start=start, end=end, freq="M")
