"""Direction of the model's error, and what it implies over the reconstruction period.

Bias throughout is observed minus predicted, on the logarithmic scale the model
fits. A positive value means the observation exceeded the prediction, so the
model predicted too low; a negative value means it predicted too high. Because
the scale is logarithmic, a bias converts to a multiplicative factor rather than
an additive offset.

The reconstruction period differs from the fit window on two axes at once, being
both earlier and wetter. Inside the fit window those axes are close to
independent, so their separate effects can be measured but their combination
cannot: no block of the record is both early and wet.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CONVENTION = "observed minus predicted"


def direction(bias_log: float, tolerance: float = 0.01) -> str:
    """Plain statement of which way a log-scale bias points."""
    if abs(bias_log) < tolerance:
        return "no material bias"
    return "model predicts low" if bias_log > 0 else "model predicts high"


def as_ratio(bias_log: float) -> dict[str, float]:
    """Convert a log-scale bias to the multiplicative error it represents."""
    predicted_over_observed = float(np.exp(-bias_log))
    return {
        "bias_log_obs_minus_pred": bias_log,
        "predicted_over_observed": predicted_over_observed,
        "prediction_error_pct": 100.0 * (predicted_over_observed - 1.0),
    }


def bias_table(records: list[dict[str, object]], key: str = "bias_log_obs_minus_pred") -> pd.DataFrame:
    """Bias for each experiment, with its direction and multiplicative size."""
    rows = []
    for record in records:
        value = float(record[key])
        rows.append(
            {
                "experiment": record["experiment"],
                "model": record["model"],
                "weighting": record["weighting"],
                **as_ratio(value),
                "direction": direction(value),
            }
        )
    return pd.DataFrame.from_records(rows)


def combine_additively(components: dict[str, float]) -> dict[str, float]:
    """Sum log-scale biases from separate experiments into a net expectation.

    Addition on the logarithmic scale is multiplication on the flux scale, so
    this treats the two effects as independent multiplicative factors. That
    independence is an assumption, not a measurement: the fit window contains no
    months that are both early and wet, so the joint effect cannot be observed.
    """
    net = float(sum(components.values()))
    out = {f"component_{name}": value for name, value in components.items()}
    out |= as_ratio(net)
    out["direction"] = direction(net)
    cancellation = 1.0 - abs(net) / sum(abs(v) for v in components.values())
    out["cancellation_share"] = float(cancellation)
    return out


def axis_independence(
    covariates: pd.DataFrame, months: pd.PeriodIndex, column: str
) -> dict[str, float]:
    """Correlation between calendar time and a covariate over the given months.

    A correlation near zero means the two axes vary independently there, so
    holdouts along one axis do not confound the other.
    """
    from scipy import stats

    ordinals = np.array([p.ordinal for p in months], dtype=float)
    values = covariates.loc[months, column].to_numpy(dtype=float)
    r, p = stats.pearsonr(ordinals, values)
    return {"covariate": column, "n": len(months), "correlation_with_time": float(r), "p_value": float(p)}


def bias_by_covariate_band(
    observed: pd.Series, predicted: pd.Series, covariate: pd.Series, n_bands: int = 3
) -> pd.DataFrame:
    """Split a holdout's bias by covariate level, to test whether it is uniform.

    If the bias measured on one axis is constant across bands of the other, the
    two effects are more plausibly separable, which is what combining them
    additively assumes.
    """
    frame = pd.DataFrame(
        {"residual": observed - predicted, "covariate": covariate.reindex(observed.index)}
    ).dropna()
    labels = [f"band {i + 1}" for i in range(n_bands)]
    frame["band"] = pd.qcut(frame["covariate"], n_bands, labels=labels, duplicates="drop")
    grouped = frame.groupby("band", observed=True)
    out = pd.DataFrame(
        {
            "n": grouped.size(),
            "covariate_mean": grouped["covariate"].mean(),
            "bias_log_obs_minus_pred": grouped["residual"].mean(),
        }
    )
    out["prediction_error_pct"] = 100.0 * (np.exp(-out["bias_log_obs_minus_pred"]) - 1.0)
    out["direction"] = out["bias_log_obs_minus_pred"].map(direction)
    return out.round(4)
