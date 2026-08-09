"""Inverse-variance weights for the monthly methane series, and what they will do.

Each monthly mean carries the count of days behind it and the dispersion across
those days, so months resting on little evidence can be down-weighted rather
than treated as equal to months resting on much. These functions describe the
weights; nothing here fits anything.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SE_COLUMN = "fch4_se_across_days"
DAYS_COLUMN = "fch4_days"
HALFHOURS_COLUMN = "fch4_halfhours"


def inverse_variance_weights(monthly: pd.DataFrame, se_column: str = SE_COLUMN) -> pd.Series:
    """Weight each month by the reciprocal of its squared standard error.

    Months with an undefined standard error, which arises when a month rests on
    a single day, receive no weight and are returned as null rather than zero so
    that they cannot be silently included.
    """
    se = pd.to_numeric(monthly[se_column], errors="coerce")
    weights = 1.0 / se.pow(2)
    return weights.where(se.notna() & (se > 0))


def weight_summary(monthly: pd.DataFrame, months: pd.PeriodIndex) -> pd.DataFrame:
    """Distribution of the evidence behind each monthly mean over the given months."""
    frame = monthly.loc[monthly.index.isin(months)]
    weights = inverse_variance_weights(frame)
    relative = weights / weights.sum()
    described = pd.DataFrame(
        {
            "days_per_month": frame[DAYS_COLUMN],
            "halfhours_per_month": frame[HALFHOURS_COLUMN],
            "sd_across_days": frame["fch4_sd_across_days"],
            "standard_error": frame[SE_COLUMN],
            "relative_weight_pct": 100 * relative,
        }
    ).describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])
    return described.round(4)


def weight_concentration(monthly: pd.DataFrame, months: pd.PeriodIndex) -> pd.DataFrame:
    """How much of the total weight the most and least influential months carry."""
    frame = monthly.loc[monthly.index.isin(months)]
    weights = inverse_variance_weights(frame).dropna().sort_values(ascending=False)
    relative = weights / weights.sum()
    n = len(relative)
    records = []
    for share in (0.10, 0.25, 0.50):
        k = max(1, int(round(share * n)))
        records.append(
            {
                "group": f"top {int(share * 100)}% of months by weight",
                "n_months": k,
                "share_of_total_weight_pct": round(100 * relative.iloc[:k].sum(), 1),
            }
        )
        records.append(
            {
                "group": f"bottom {int(share * 100)}% of months by weight",
                "n_months": k,
                "share_of_total_weight_pct": round(100 * relative.iloc[-k:].sum(), 1),
            }
        )
    records.append(
        {
            "group": "effective sample size, sum(w)^2 / sum(w^2)",
            "n_months": n,
            "share_of_total_weight_pct": round(
                float(weights.sum() ** 2 / (weights**2).sum()), 1
            ),
        }
    )
    return pd.DataFrame.from_records(records)


def least_influential(monthly: pd.DataFrame, months: pd.PeriodIndex, n: int = 12) -> pd.DataFrame:
    """The months carrying least weight, which inverse-variance weighting will discount."""
    frame = monthly.loc[monthly.index.isin(months)].copy()
    frame["weight"] = inverse_variance_weights(frame)
    frame["relative_weight_pct"] = 100 * frame["weight"] / frame["weight"].sum()
    frame["equal_weight_pct"] = 100 / len(frame)
    columns = [
        "fch4_mean", DAYS_COLUMN, HALFHOURS_COLUMN, "fch4_sd_across_days",
        SE_COLUMN, "relative_weight_pct", "equal_weight_pct",
    ]
    out = frame.nsmallest(n, "weight")[columns].round(4)
    out.index = out.index.astype(str)
    return out


def most_influential(monthly: pd.DataFrame, months: pd.PeriodIndex, n: int = 6) -> pd.DataFrame:
    """The months carrying most weight, for contrast against the least."""
    frame = monthly.loc[monthly.index.isin(months)].copy()
    frame["weight"] = inverse_variance_weights(frame)
    frame["relative_weight_pct"] = 100 * frame["weight"] / frame["weight"].sum()
    columns = ["fch4_mean", DAYS_COLUMN, "fch4_sd_across_days", SE_COLUMN, "relative_weight_pct"]
    out = frame.nlargest(n, "weight")[columns].round(4)
    out.index = out.index.astype(str)
    return out


def seasonal_weight_balance(monthly: pd.DataFrame, months: pd.PeriodIndex) -> pd.DataFrame:
    """Weight by month of year, since weighting can tilt a seasonal fit."""
    frame = monthly.loc[monthly.index.isin(months)].copy()
    frame["weight"] = inverse_variance_weights(frame)
    frame["month_of_year"] = frame.index.month
    grouped = frame.groupby("month_of_year")
    out = pd.DataFrame(
        {
            "n_months": grouped.size(),
            "mean_flux": grouped["fch4_mean"].mean(),
            "mean_se": grouped[SE_COLUMN].mean(),
            "weight_share_pct": 100 * grouped["weight"].sum() / frame["weight"].sum(),
            "equal_share_pct": 100 * grouped.size() / len(frame),
        }
    )
    return out.round(3)
