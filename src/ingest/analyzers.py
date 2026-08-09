"""Identification of the two methane analysers and comparison with published values.

The closed-path TGA-100A and the open-path LI-7700 both operated between 2015
and 2018 and appear as separate columns in the AmeriFlux BASE product.
Identification rests on deployment dates, retained observation counts and the
relative dispersion of the two series.

Paired-difference and regression statistics are sensitive to outliers, and the
BASE product does not carry the despiking applied by Deventer et al. (2019), so
regression results are produced across a range of outlier screens rather than at
a single setting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import site


def identification_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    """Deployment dates and observation counts distinguishing the two analysers."""
    records = []
    for column in (site.TGA_COLUMN, site.LI7700_COLUMN):
        stamps = frame.loc[frame[column].notna(), "timestamp_start"]
        records.append(
            {
                "column": column,
                "analyzer": site.ANALYZER_BY_COLUMN[column],
                "n_valid": len(stamps),
                "first_valid": stamps.min(),
                "last_valid": stamps.max(),
                "starts_before_2015_03": stamps.min() < pd.Timestamp("2015-03-01"),
                "n_vs_published_retained": len(stamps) - site.PUBLISHED_TGA_RETAINED,
            }
        )
    return pd.DataFrame.from_records(records)


def paired(frame: pd.DataFrame) -> pd.DataFrame:
    """Timestamps where both analysers reported, with their difference.

    The difference is TGA-100A minus LI-7700, the convention under which
    Deventer et al. (2019) report a positive median and positive skewness.
    """
    both = frame[site.TGA_COLUMN].notna() & frame[site.LI7700_COLUMN].notna()
    out = frame.loc[both, ["timestamp_start", site.TGA_COLUMN, site.LI7700_COLUMN]].copy()
    out["difference"] = out[site.TGA_COLUMN] - out[site.LI7700_COLUMN]
    return out.reset_index(drop=True)


def _laplace_scale_from_iqr(values: np.ndarray) -> float:
    """Laplace scale implied by the interquartile range, via IQR = 2 * scale * ln2."""
    iqr = float(np.subtract(*np.percentile(values, [75, 25])))
    return iqr / (2 * np.log(2))


def difference_statistics(differences: pd.Series, trim: float = 0.005) -> dict[str, float]:
    """Location, dispersion and shape of the paired differences.

    ``sigma_robust`` is the Laplace standard deviation implied by the
    interquartile range. It is reported alongside the raw second moment because
    the tail is heavier than Laplace, which inflates the raw moment and can
    reverse the sign of the raw skewness.
    """
    values = differences.to_numpy()
    scale = _laplace_scale_from_iqr(values)
    trimmed = stats.trimboth(np.sort(values), trim)
    return {
        "n": len(values),
        "median": float(np.median(values)),
        "mean": float(np.mean(values)),
        "iqr": float(np.subtract(*np.percentile(values, [75, 25]))),
        "laplace_scale_from_iqr": scale,
        "sigma_robust": scale * np.sqrt(2),
        "sd_raw_moment": float(np.std(values, ddof=1)),
        "skewness_raw": float(stats.skew(values)),
        "skewness_trimmed": float(stats.skew(trimmed)),
        "excess_kurtosis": float(stats.kurtosis(values)),
    }


def fit_laplace_vs_gaussian(differences: pd.Series) -> pd.DataFrame:
    """Compare Laplace and Gaussian fits to the paired differences.

    Reports log-likelihood, the Akaike information criterion and the
    Kolmogorov-Smirnov distance for each distribution.
    """
    values = differences.to_numpy()
    records = []
    for name, distribution in (("laplace", stats.laplace), ("norm", stats.norm)):
        params = distribution.fit(values)
        loglik = float(distribution.logpdf(values, *params).sum())
        records.append(
            {
                "distribution": name,
                "loc": params[0],
                "scale": params[1],
                "loglik": loglik,
                "aic": 2 * len(params) - 2 * loglik,
                "ks_statistic": float(stats.kstest(values, name, params).statistic),
            }
        )
    out = pd.DataFrame.from_records(records)
    out["delta_aic_vs_best"] = out["aic"] - out["aic"].min()
    return out


def reduced_major_axis(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Reduced major axis regression of y on x, with analytic standard errors.

    Reduced major axis treats both variables as carrying error, unlike ordinary
    least squares, which attributes all error to y.
    """
    r = float(np.corrcoef(x, y)[0, 1])
    slope = np.sign(r) * y.std(ddof=1) / x.std(ddof=1)
    intercept = y.mean() - slope * x.mean()
    slope_se = abs(slope) * np.sqrt((1 - r**2) / len(x))
    residual = y - (intercept + slope * x)
    intercept_se = np.sqrt(residual.var(ddof=2) / len(x) + (slope_se * x.mean()) ** 2)
    return {
        "n": len(x),
        "slope": float(slope),
        "slope_se": float(slope_se),
        "intercept": float(intercept),
        "intercept_se": float(intercept_se),
        "r": r,
    }


def ols_regression(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Ordinary least squares of y on x, with t-statistics against the identity line."""
    fit = stats.linregress(x, y)
    return {
        "n": len(x),
        "slope": fit.slope,
        "slope_se": fit.stderr,
        "t_slope_vs_1": (fit.slope - 1) / fit.stderr,
        "intercept": fit.intercept,
        "intercept_se": fit.intercept_stderr,
        "t_intercept_vs_0": fit.intercept / fit.intercept_stderr,
        "r2": fit.rvalue**2,
    }


def _screens(pairs: pd.DataFrame) -> list[tuple[str, np.ndarray]]:
    """Candidate outlier screens, from no screening to combined magnitude limits."""
    absolute_difference = pairs["difference"].abs().to_numpy()
    tga = pairs[site.TGA_COLUMN].to_numpy()
    li = pairs[site.LI7700_COLUMN].to_numpy()
    screens: list[tuple[str, np.ndarray]] = [("none", np.ones(len(pairs), bool))]
    for q in (0.99, 0.98, 0.95, 0.90):
        screens.append(
            (f"|diff| <= q{q:g}", absolute_difference <= np.quantile(absolute_difference, q))
        )
    for limit in (200, 100, 50):
        screens.append((f"|flux| < {limit}", (np.abs(tga) < limit) & (np.abs(li) < limit)))
    screens.append(
        (
            "|flux| < 100 & |diff| <= q0.98",
            (np.abs(tga) < 100)
            & (np.abs(li) < 100)
            & (absolute_difference <= np.quantile(absolute_difference, 0.98)),
        )
    )
    return screens


def regression_sweep(pairs: pd.DataFrame) -> pd.DataFrame:
    """Run both regressions of LI-7700 on TGA-100A under every candidate screen."""
    records = []
    for label, mask in _screens(pairs):
        x = pairs.loc[mask, site.TGA_COLUMN].to_numpy()
        y = pairs.loc[mask, site.LI7700_COLUMN].to_numpy()
        rma = reduced_major_axis(x, y)
        ols = ols_regression(x, y)
        records.append(
            {
                "screen": label,
                "n": rma["n"],
                "rma_slope": rma["slope"],
                "rma_slope_se": rma["slope_se"],
                "rma_intercept": rma["intercept"],
                "rma_intercept_se": rma["intercept_se"],
                "ols_slope": ols["slope"],
                "ols_t_vs_1": ols["t_slope_vs_1"],
                "ols_intercept": ols["intercept"],
                "ols_t_vs_0": ols["t_intercept_vs_0"],
                "r": rma["r"],
            }
        )
    return pd.DataFrame.from_records(records)


def published_agreement(sweep: pd.DataFrame) -> pd.DataFrame:
    """Flag which screens place the regression inside the published error bars."""
    target = site.PUBLISHED_RMA
    slope_low = target["slope"] - target["slope_se"]
    slope_high = target["slope"] + target["slope_se"]
    intercept_low = target["intercept"] - target["intercept_se"]
    intercept_high = target["intercept"] + target["intercept_se"]

    out = sweep[["screen", "n", "rma_slope", "rma_intercept"]].copy()
    out["slope_in_published_range"] = out["rma_slope"].between(slope_low, slope_high)
    out["intercept_in_published_range"] = out["rma_intercept"].between(
        intercept_low, intercept_high
    )
    out["both"] = out["slope_in_published_range"] & out["intercept_in_published_range"]
    return out
