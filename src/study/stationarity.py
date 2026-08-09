"""Whether covariate distributions differ between the reconstruction and fit periods.

A relationship fitted on recent conditions transfers backward only if the earlier
period resembles the later one. Raw monthly values carry a strong seasonal cycle,
so a difference between two multi-year periods can arise from their month
composition alone; tests are therefore run twice, on raw values and on anomalies
from the month-of-year mean.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def deseasonalise(series: pd.Series) -> pd.Series:
    """Subtract the month-of-year mean, taken over every month the series holds."""
    clean = series.dropna()
    climatology = clean.groupby(clean.index.month).mean()
    return clean - clean.index.month.map(climatology)


def _compare(earlier: np.ndarray, later: np.ndarray) -> dict[str, float]:
    """Location and shape comparison of two samples, with a rank effect size."""
    u, p_u = stats.mannwhitneyu(earlier, later, alternative="two-sided")
    ks, p_ks = stats.ks_2samp(earlier, later)
    # Cliff's delta from the Mann-Whitney statistic: the probability that a value
    # drawn from the earlier sample exceeds one from the later, rescaled to [-1, 1].
    delta = 2 * u / (len(earlier) * len(later)) - 1
    pooled = np.sqrt(
        ((len(earlier) - 1) * earlier.var(ddof=1) + (len(later) - 1) * later.var(ddof=1))
        / (len(earlier) + len(later) - 2)
    )
    return {
        "recon_mean": float(earlier.mean()),
        "fit_mean": float(later.mean()),
        "mean_difference": float(earlier.mean() - later.mean()),
        "standardised_difference": float((earlier.mean() - later.mean()) / pooled) if pooled else np.nan,
        "cliffs_delta": float(delta),
        "mann_whitney_p": float(p_u),
        "ks_statistic": float(ks),
        "ks_p": float(p_ks),
    }


def compare_periods(
    covariates: pd.DataFrame,
    fit: pd.PeriodIndex,
    reconstruction: pd.PeriodIndex,
    columns: tuple[str, ...],
    deseasonalised: bool = False,
) -> pd.DataFrame:
    """Compare each covariate's reconstruction-period values against its fit values."""
    records = []
    for column in columns:
        series = covariates[column]
        if deseasonalised:
            series = deseasonalise(series)
        earlier = series.reindex(reconstruction).dropna().to_numpy()
        later = series.reindex(fit).dropna().to_numpy()
        record = {"covariate": column, "n_recon": len(earlier), "n_fit": len(later)}
        record.update(_compare(earlier, later))
        records.append(record)
    return pd.DataFrame.from_records(records)


def annual_means(
    covariates: pd.DataFrame, columns: tuple[str, ...], months: pd.PeriodIndex
) -> pd.DataFrame:
    """Annual means over the given months, for inspecting drift within a period.

    The month count is carried alongside, because a year represented by only its
    winter months has a mean that is not comparable with a complete year.
    """
    frame = covariates.loc[months, list(columns)].copy()
    frame["year"] = frame.index.year
    grouped = frame.groupby("year")
    out = grouped.mean().round(3)
    out.insert(0, "n_months", grouped.size())
    return out


def early_late_contrast(
    covariates: pd.DataFrame,
    columns: tuple[str, ...],
    early: tuple[str, str],
    late: tuple[str, str],
) -> pd.DataFrame:
    """Contrast two named sub-periods, following the comparison Olson et al. (2013) drew."""
    early_months = pd.period_range(early[0], early[1], freq="M")
    late_months = pd.period_range(late[0], late[1], freq="M")
    records = []
    for column in columns:
        a = covariates[column].reindex(early_months).dropna().to_numpy()
        b = covariates[column].reindex(late_months).dropna().to_numpy()
        if len(a) == 0 or len(b) == 0:
            continue
        records.append(
            {
                "covariate": column,
                f"{early[0]}..{early[1]}": round(float(a.mean()), 3),
                f"{late[0]}..{late[1]}": round(float(b.mean()), 3),
                "difference": round(float(b.mean() - a.mean()), 3),
                "mann_whitney_p": round(float(stats.mannwhitneyu(a, b, alternative="two-sided")[1]), 4),
            }
        )
    return pd.DataFrame.from_records(records)
