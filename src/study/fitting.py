"""Least-absolute-deviation fitting and prediction intervals without a normal assumption.

Minimising absolute deviations is maximum likelihood under Laplace errors, which
Deventer et al. (2019) established for fluxes at this site and which the
ingestion layer reproduced. The fit is expressed as a linear program and solved
exactly, so nothing here is stochastic.

Intervals come from the empirical quantiles of the training residuals, which
assume no distributional form at all. A Laplace variant is also provided, with
each month's own aggregation uncertainty folded in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import linprog


@dataclass
class Fit:
    """A fitted model, its training residuals, and the scale of those residuals."""

    columns: list[str]
    coefficients: np.ndarray
    residuals: pd.Series
    laplace_scale: float
    weighted: bool
    water_table_bounds: tuple[float, float] | None = None
    extras: dict = field(default_factory=dict)

    def as_series(self) -> pd.Series:
        return pd.Series(self.coefficients, index=self.columns)

    def predict(self, design: pd.DataFrame) -> pd.Series:
        return pd.Series(design[self.columns].to_numpy() @ self.coefficients, index=design.index)


def fit_lad(design: pd.DataFrame, target: pd.Series, weights: pd.Series | None = None) -> Fit:
    """Fit by minimising the sum of absolute deviations, optionally weighted.

    Solved as a linear program in the coefficients and the positive and negative
    parts of each residual, which gives the exact optimum rather than an
    iterative approximation.
    """
    X = design.to_numpy(dtype=float)
    y = target.to_numpy(dtype=float)
    n, k = X.shape
    w = np.ones(n) if weights is None else weights.reindex(target.index).to_numpy(dtype=float)
    if not np.isfinite(w).all() or (w <= 0).any():
        raise ValueError("weights must be finite and positive")
    w = w / w.mean()

    cost = np.concatenate([np.zeros(k), w, w])
    equality = np.hstack([X, np.eye(n), -np.eye(n)])
    bounds = [(None, None)] * k + [(0, None)] * (2 * n)

    solution = linprog(cost, A_eq=equality, b_eq=y, bounds=bounds, method="highs")
    if not solution.success:
        raise RuntimeError(f"least absolute deviation fit failed: {solution.message}")

    coefficients = solution.x[:k]
    residuals = pd.Series(y - X @ coefficients, index=target.index)
    scale = float(np.average(np.abs(residuals - residuals.median()), weights=w))
    return Fit(
        columns=list(design.columns),
        coefficients=coefficients,
        residuals=residuals,
        laplace_scale=scale,
        weighted=weights is not None,
    )


def empirical_interval(fit: Fit, prediction: pd.Series, level: float = 0.90) -> pd.DataFrame:
    """Interval from the quantiles of the training residuals, assuming no shape.

    The residuals already contain both model error and the error in each observed
    monthly mean, so the interval covers a future observed monthly mean.
    """
    tail = (1.0 - level) / 2.0
    low, high = np.quantile(fit.residuals.to_numpy(), [tail, 1.0 - tail])
    return pd.DataFrame(
        {"prediction": prediction, "lower": prediction + low, "upper": prediction + high}
    )


def laplace_interval(
    fit: Fit,
    prediction: pd.Series,
    level: float = 0.90,
    observation_scale: pd.Series | None = None,
) -> pd.DataFrame:
    """Laplace interval, widened by each month's own aggregation uncertainty.

    A Laplace distribution of scale b has variance 2b squared. Model and
    observation variances are added and converted back to an effective scale.
    The sum of two Laplace variables is not itself Laplace, so this matches the
    variance rather than the exact shape.
    """
    tail = (1.0 - level) / 2.0
    variance = 2.0 * fit.laplace_scale**2
    if observation_scale is not None:
        variance = variance + observation_scale.reindex(prediction.index).fillna(0.0) ** 2
    effective = np.sqrt(np.asarray(variance) / 2.0)

    def quantile(p: float) -> np.ndarray:
        sign = np.sign(p - 0.5)
        return -effective * sign * np.log(1.0 - 2.0 * np.abs(p - 0.5))

    return pd.DataFrame(
        {
            "prediction": prediction,
            "lower": prediction + quantile(tail),
            "upper": prediction + quantile(1.0 - tail),
        }
    )


def back_transform(interval: pd.DataFrame) -> pd.DataFrame:
    """Return an interval on the logarithmic scale to flux units."""
    return interval.apply(np.exp)


def coverage(interval: pd.DataFrame, observed: pd.Series) -> float:
    """Share of observations falling inside their interval."""
    inside = (observed >= interval["lower"]) & (observed <= interval["upper"])
    return float(inside.mean())


#: Every residual and bias in this package is observed minus predicted. A
#: positive bias therefore means the observation exceeded the prediction, so the
#: model predicted too low. A negative bias means the model predicted too high.
BIAS_CONVENTION = "observed minus predicted"


def error_metrics(observed: pd.Series, predicted: pd.Series, log_space: bool = True) -> dict[str, float]:
    """Error on both the fitted scale and the flux scale.

    Median absolute error is reported alongside the mean because the flux
    distribution is skewed and a single large month moves the mean considerably.
    Bias follows BIAS_CONVENTION: observed minus predicted, so a positive value
    means the model predicted below the observation.
    """
    residual = observed - predicted
    metrics = {
        "n": int(len(observed)),
        "mae_log": float(np.mean(np.abs(residual))),
        "medae_log": float(np.median(np.abs(residual))),
        "bias_log_obs_minus_pred": float(np.mean(residual)),
    }
    if log_space:
        obs, pred = np.exp(observed), np.exp(predicted)
        native = obs - pred
        metrics |= {
            "mae_flux": float(np.mean(np.abs(native))),
            "medae_flux": float(np.median(np.abs(native))),
            "bias_flux_obs_minus_pred": float(np.mean(native)),
            "mape_pct": float(100 * np.mean(np.abs(native / obs))),
        }
    return metrics
