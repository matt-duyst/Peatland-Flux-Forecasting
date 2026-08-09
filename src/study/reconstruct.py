"""Project the fitted model backward, carrying what each year rests on.

The projection is a vehicle for a demonstration rather than an estimate to be
defended. Three variants of the water table term are run: clamped at the fitted
range, continued linearly beyond it, and omitted. Their spread is a sensitivity
range showing how much the answer depends on an assumption the stability test
rejects. It is not a confidence interval and must not be read as one.

Every year carries the number of months whose covariates leave the fitted range,
its joint distance from the fit window, an explicit inside-or-outside verdict,
and the direction the wet-end bias bands expect it to err.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import bias, features, fitting, support, targets

VARIANTS = ("clamped", "unclamped", "reduced")


def fit_variant(
    covariates: pd.DataFrame,
    monthly: pd.DataFrame,
    fit_months: pd.PeriodIndex,
    variant: str,
    weights: pd.Series | None = None,
) -> tuple[fitting.Fit, tuple[float, float]]:
    """Fit one water table variant on the fit window."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; expected one of {VARIANTS}")
    bounds = features.clamp_bounds(covariates, fit_months, features.WATER_TABLE)
    design = features.build_design(
        covariates, fit_months, bounds, include_water_table=variant != "reduced"
    )
    fit = fitting.fit_lad(design, features.log_target(monthly, fit_months), weights)
    fit.water_table_bounds = bounds
    return fit, bounds


def predict_variant(
    fit: fitting.Fit,
    covariates: pd.DataFrame,
    months: pd.PeriodIndex,
    variant: str,
    bounds: tuple[float, float],
) -> pd.Series:
    """Predict flux over the given months under one variant.

    The clamped and reduced variants use the same design as they were fitted on.
    The unclamped variant reuses the clamped coefficients but lets the water
    table term run past the fitted range, which is what makes it the aggressive
    end of the sensitivity range.
    """
    wide = (covariates.loc[months, features.WATER_TABLE].min() - 1.0,
            covariates.loc[months, features.WATER_TABLE].max() + 1.0)
    design = features.build_design(
        covariates,
        months,
        wide if variant == "unclamped" else bounds,
        include_water_table=variant != "reduced",
    )
    return np.exp(fit.predict(design))


def monthly_reconstruction(
    covariates: pd.DataFrame,
    monthly: pd.DataFrame,
    fit_months: pd.PeriodIndex,
    target_months: pd.PeriodIndex,
    weights: pd.Series | None = None,
    level: float = 0.90,
) -> pd.DataFrame:
    """Monthly flux under each variant, with an interval on the primary one."""
    frame = pd.DataFrame(index=pd.PeriodIndex(target_months, freq="M"))
    primary, bounds = fit_variant(covariates, monthly, fit_months, "clamped", weights)
    for variant in VARIANTS:
        fit = primary if variant != "reduced" else fit_variant(
            covariates, monthly, fit_months, "reduced", weights
        )[0]
        frame[variant] = predict_variant(fit, covariates, target_months, variant, bounds)

    log_prediction = np.log(frame["clamped"])
    interval = fitting.empirical_interval(primary, log_prediction, level)
    frame["lower"] = np.exp(interval["lower"])
    frame["upper"] = np.exp(interval["upper"])
    return frame


def year_support(
    covariates: pd.DataFrame,
    fit_months: pd.PeriodIndex,
    target_months: pd.PeriodIndex,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    """Per year, how far outside the fitted range its months lie."""
    outside = support.out_of_range_months(covariates, fit_months, target_months, columns)
    distances = _joint_distance_by_month(covariates, fit_months, target_months, columns)

    records = []
    for year, months in _group_years(target_months):
        flagged = outside[outside["month"].isin([str(m) for m in months])]
        n_outside = flagged["month"].nunique()
        records.append(
            {
                "year": year,
                "n_months": len(months),
                "n_months_outside_range": int(n_outside),
                "pct_months_outside": round(100 * n_outside / len(months), 0),
                "covariates_outside": ", ".join(sorted(set(flagged["covariate"]))),
                "joint_distance_median": round(float(distances.reindex(months).median()), 3),
                "joint_distance_max": round(float(distances.reindex(months).max()), 3),
                "support": "outside" if n_outside else "inside",
            }
        )
    return pd.DataFrame.from_records(records)


def _group_years(months: pd.PeriodIndex) -> list[tuple[int, pd.PeriodIndex]]:
    frame = pd.Series(months, index=months)
    return [(int(year), pd.PeriodIndex(group, freq="M")) for year, group in frame.groupby(months.year)]


def _joint_distance_by_month(
    covariates: pd.DataFrame,
    fit_months: pd.PeriodIndex,
    target_months: pd.PeriodIndex,
    columns: tuple[str, ...],
) -> pd.Series:
    """Distance from each target month to its nearest fit month, standardised on the fit."""
    f = covariates.loc[fit_months, list(columns)].dropna()
    t = covariates.loc[target_months, list(columns)].dropna()
    usable = [c for c in columns if f[c].std(ddof=1) > 0]
    if not usable:
        raise ValueError("no covariate varies over the fit window")
    f, t = f[usable], t[usable]
    centre, scale = f.mean(), f.std(ddof=1)
    fz = ((f - centre) / scale).to_numpy()
    tz = ((t - centre) / scale).to_numpy()
    d = np.sqrt(((tz[:, None, :] - fz[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    return pd.Series(d, index=t.index)


def annual_reconstruction(
    reconstruction: pd.DataFrame,
    support_table: pd.DataFrame,
    expected_bias_log: float,
) -> pd.DataFrame:
    """Annual budgets with the sensitivity range, support verdict and bias expectation.

    ``expected_bias_log`` is the wet-end directional expectation, carried as a
    stated direction and magnitude rather than applied as a correction.
    """
    annual = {}
    for variant in VARIANTS:
        annual[variant] = targets.monthly_flux_to_annual(reconstruction[variant])["g_C_m2"]
    for edge in ("lower", "upper"):
        annual[edge] = targets.monthly_flux_to_annual(reconstruction[edge])["g_C_m2"]
    frame = pd.DataFrame(annual)

    frame["sensitivity_low"] = frame[list(VARIANTS)].min(axis=1)
    frame["sensitivity_high"] = frame[list(VARIANTS)].max(axis=1)
    frame["sensitivity_span_pct"] = (
        100 * (frame["sensitivity_high"] - frame["sensitivity_low"]) / frame["clamped"]
    ).round(0)

    ratio = bias.as_ratio(expected_bias_log)["predicted_over_observed"]
    frame["bias_expectation"] = bias.direction(expected_bias_log)
    frame["if_corrected"] = (frame["clamped"] / ratio).round(2)

    merged = support_table.set_index("year").join(frame.round(2))
    ordered = [
        "n_months", "support", "n_months_outside_range", "pct_months_outside",
        "covariates_outside", "joint_distance_max",
        "clamped", "lower", "upper",
        "sensitivity_low", "sensitivity_high", "sensitivity_span_pct",
        "bias_expectation", "if_corrected",
    ]
    return merged[ordered].reset_index()
