"""Where a model's error sits, and whether it concentrates or spreads.

A shortfall in an annual total can arise two ways. It can be spread across the
year, which points to a mis-specified seasonal response, or it can sit in one or
two months, which points to episodes the covariates do not describe. Irvin et
al. (2021) note that episodic fluxes, ebullition among them, are often missed by
gap-filling models and replaced with averages for comparable conditions. The two
have different implications, so they are worth separating.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import targets


def monthly_comparison(observed_flux: pd.Series, predicted_flux: pd.Series) -> pd.DataFrame:
    """Observed against predicted flux per month, with each month's mass contribution.

    Contributions are in grams of carbon per square meter, so a month's share of
    an annual shortfall can be read directly.
    """
    months = observed_flux.index.intersection(predicted_flux.index)
    frame = pd.DataFrame(
        {"observed": observed_flux.reindex(months), "predicted": predicted_flux.reindex(months)}
    )
    seconds = np.array([p.days_in_month * 86400 for p in frame.index], dtype=float)
    factor = seconds * 1e-9 * targets.MOLAR_MASS_CH4 * targets.C_PER_CH4
    frame["observed_g_C"] = frame["observed"] * factor
    frame["predicted_g_C"] = frame["predicted"] * factor
    frame["shortfall_g_C"] = frame["observed_g_C"] - frame["predicted_g_C"]
    frame["ratio"] = frame["predicted"] / frame["observed"]
    return frame


def concentration(comparison: pd.DataFrame, column: str = "shortfall_g_C") -> dict[str, object]:
    """How much of the total shortfall the largest few months carry.

    A shortfall concentrated in one or two months is an episode problem. One
    spread evenly is a seasonal-response problem.
    """
    values = comparison[column]
    total = float(values.sum())
    ranked = values.sort_values(ascending=False)
    positive = ranked[ranked > 0]
    out: dict[str, object] = {
        "total_shortfall_g_C": total,
        "n_months": int(len(values)),
        "n_months_under_predicted": int((values > 0).sum()),
    }
    for k in (1, 2, 3):
        if len(ranked) >= k:
            out[f"top_{k}_share_of_total_pct"] = round(100 * float(ranked.iloc[:k].sum()) / total, 1) if total else float("nan")
    out["largest_month"] = str(ranked.index[0])
    out["largest_month_g_C"] = round(float(ranked.iloc[0]), 3)
    out["sum_of_positive_shortfalls_g_C"] = round(float(positive.sum()), 3)
    return out


def covariate_anomaly(
    covariates: pd.DataFrame,
    target_months: pd.PeriodIndex,
    reference_months: pd.PeriodIndex,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    """How a period's covariates differ from a reference period, in native and standard units."""
    records = []
    for column in columns:
        target = covariates.loc[target_months, column].dropna()
        reference = covariates.loc[reference_months, column].dropna()
        spread = reference.std(ddof=1)
        records.append(
            {
                "covariate": column,
                "period_mean": round(float(target.mean()), 3),
                "reference_mean": round(float(reference.mean()), 3),
                "difference": round(float(target.mean() - reference.mean()), 3),
                "standardized": round(float((target.mean() - reference.mean()) / spread), 2) if spread else np.nan,
                "period_max": round(float(target.max()), 3),
                "reference_max": round(float(reference.max()), 3),
            }
        )
    return pd.DataFrame.from_records(records)


def extreme_months(
    observed_flux: pd.Series, reference: pd.Series, n: int = 5
) -> pd.DataFrame:
    """Months whose flux stands furthest above the same calendar month elsewhere."""
    frame = pd.DataFrame({"flux": observed_flux})
    frame["month_of_year"] = [p.month for p in frame.index]
    climatology = reference.groupby([p.month for p in reference.index])
    frame["reference_mean"] = frame["month_of_year"].map(climatology.mean())
    frame["reference_sd"] = frame["month_of_year"].map(climatology.std(ddof=1))
    # A calendar month with one reference observation, or several identical ones,
    # has no spread to standardize by; leave those undefined rather than infinite.
    spread = frame["reference_sd"].where(frame["reference_sd"] > 0)
    frame["standardized"] = (frame["flux"] - frame["reference_mean"]) / spread
    out = frame.nlargest(n, "standardized")[["flux", "reference_mean", "reference_sd", "standardized"]]
    out.index = out.index.astype(str)
    return out.round(3)


# --------------------------------------------------------------------------
# What distribution the errors follow, against the one the estimator assumes
# --------------------------------------------------------------------------

#: The two the estimator choice was made between. Least absolute deviations is
#: maximum likelihood under Laplace error; least squares is maximum likelihood
#: under Gaussian. Each is fitted to the residuals by maximum likelihood, so the
#: reference on a quantile plot is the line of equality rather than a fitted one.
FAMILIES = ("Laplace", "Gaussian")


def _laplace(values: np.ndarray) -> tuple[float, float]:
    """Location and scale of the maximum likelihood Laplace fit."""
    location = float(np.median(values))
    return location, float(np.abs(values - location).mean())


def _gaussian(values: np.ndarray) -> tuple[float, float]:
    return float(values.mean()), float(values.std(ddof=0))


def log_likelihood(values: np.ndarray, family: str) -> float:
    """Log likelihood of the residuals under the maximum likelihood fit."""
    n = len(values)
    if family == "Laplace":
        location, scale = _laplace(values)
        return -n * np.log(2 * scale) - float(np.abs(values - location).sum()) / scale
    location, scale = _gaussian(values)
    return (-0.5 * n * np.log(2 * np.pi * scale**2)
            - float(((values - location) ** 2).sum()) / (2 * scale**2))


def distribution_comparison(values: pd.Series) -> dict[str, float]:
    """Akaike information criterion for each family, and the gap between them.

    Two free parameters each, so the comparison is on log likelihood alone. The
    gap is positive when Laplace is preferred, matching the sign the ingestion
    layer reports for the analyzer differences.
    """
    array = np.asarray(values, dtype=float)
    scores = {family: 4.0 - 2.0 * log_likelihood(array, family) for family in FAMILIES}
    return {
        "n": len(array),
        "aic_laplace": scores["Laplace"],
        "aic_gaussian": scores["Gaussian"],
        "delta_aic": scores["Gaussian"] - scores["Laplace"],
    }


def _all_inside(low: np.ndarray, high: np.ndarray, n: int) -> float:
    """P(low[k] <= U(k) <= high[k] for every k), for n uniform order statistics.

    Followed through the counting process: the number of draws at or below a
    point. Between two bounds the count gains a binomial number of the draws not
    yet placed, and at a bound the counts that would violate it are dropped. The
    result is exact, so nothing here is simulated and no seed is involved.
    """
    from scipy import stats

    bounds = sorted([(t, True, k) for k, t in enumerate(high, 1)]
                    + [(t, False, k) for k, t in enumerate(low, 1)])
    counts = np.arange(n + 1)
    gained = counts[None, :] - counts[:, None]
    left = (n - counts)[:, None]

    state = np.zeros(n + 1)
    state[0] = 1.0
    at = 0.0
    for point, is_upper, k in bounds:
        if point > at:
            share = (point - at) / (1.0 - at)
            move = np.where(gained >= 0, stats.binom.pmf(gained, left, share), 0.0)
            state = state @ move
            at = point
        if is_upper:
            state[:k] = 0.0        # fewer than k draws this low: U(k) is above it
        else:
            state[k:] = 0.0        # k or more draws this low: U(k) is below it
        if not state.any():
            return 0.0
    return float(state.sum())


def local_level(n: int, overall: float = 0.05, tolerance: float = 1e-7) -> float:
    """The level each point needs so that the whole band holds at `overall`.

    Testing every point at the level wanted for the band is the mistake this
    exists to avoid: at 115 points, bounds drawn point by point at 0.05 are
    escaped by 57% of samples that follow the distribution exactly. The level is
    lowered until the chance of any point escaping is the level asked for, which
    is the equal local levels construction of Weine, McPeek and Abney (2023).
    """
    from scipy import stats

    k = np.arange(1, n + 1)

    def escapes(level: float) -> float:
        return 1.0 - _all_inside(stats.beta.ppf(level / 2, k, n - k + 1),
                                 stats.beta.ppf(1 - level / 2, k, n - k + 1), n)

    low, high = overall / (20 * n), overall
    while high - low > tolerance:
        middle = 0.5 * (low + high)
        if escapes(middle) < overall:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def quantile_comparison(values: pd.Series, family: str,
                        level: float | None = None) -> pd.DataFrame:
    """Ordered residuals against the quantiles the family puts them at.

    The band is the one every point has to stay inside for the figure to be read
    as agreement, rather than one each point holds on its own.
    """
    from scipy import stats

    array = np.sort(np.asarray(values, dtype=float))
    n = len(array)
    location, scale = _laplace(array) if family == "Laplace" else _gaussian(array)
    reference = stats.laplace(location, scale) if family == "Laplace" \
        else stats.norm(location, scale)

    k = np.arange(1, n + 1)
    if level is None:
        level = local_level(n)
    return pd.DataFrame({
        "expected": reference.ppf((k - 0.5) / n),
        "observed": array,
        "lowest": reference.ppf(stats.beta.ppf(level / 2, k, n - k + 1)),
        "highest": reference.ppf(stats.beta.ppf(1 - level / 2, k, n - k + 1)),
    })
