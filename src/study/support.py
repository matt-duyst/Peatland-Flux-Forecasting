"""Whether the reconstruction period lies inside the range the fit period covers.

A model fitted on one period and applied to another interpolates only where the
second period's covariates fall inside the first period's range. Months outside
that range are extrapolation, and nothing in the fitted relationship constrains
the answer there.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def distribution_comparison(
    covariates: pd.DataFrame,
    fit: pd.PeriodIndex,
    reconstruction: pd.PeriodIndex,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    """Range and center of each covariate over both windows, with the share outside."""
    records = []
    for column in columns:
        f = covariates.loc[fit, column].dropna()
        r = covariates.loc[reconstruction, column].dropna()
        below = (r < f.min()).sum()
        above = (r > f.max()).sum()
        records.append(
            {
                "covariate": column,
                "fit_min": f.min(),
                "fit_max": f.max(),
                "fit_mean": f.mean(),
                "recon_min": r.min(),
                "recon_max": r.max(),
                "recon_mean": r.mean(),
                "mean_shift": r.mean() - f.mean(),
                "n_below_fit_min": int(below),
                "n_above_fit_max": int(above),
                "n_outside": int(below + above),
                "pct_outside": round(100 * (below + above) / len(r), 1),
            }
        )
    return pd.DataFrame.from_records(records)


def out_of_range_months(
    covariates: pd.DataFrame,
    fit: pd.PeriodIndex,
    reconstruction: pd.PeriodIndex,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    """Every reconstruction month holding a covariate outside the fit range."""
    records = []
    for column in columns:
        f = covariates.loc[fit, column].dropna()
        low, high = f.min(), f.max()
        r = covariates.loc[reconstruction, column].dropna()
        outside = r[(r < low) | (r > high)]
        for month, value in outside.items():
            records.append(
                {
                    "month": str(month),
                    "covariate": column,
                    "value": value,
                    "direction": "below" if value < low else "above",
                    "fit_min": low,
                    "fit_max": high,
                    "excess": (low - value) if value < low else (value - high),
                }
            )
    out = pd.DataFrame.from_records(
        records, columns=["month", "covariate", "value", "direction", "fit_min", "fit_max", "excess"]
    )
    return out.sort_values(["month", "covariate"]).reset_index(drop=True)


def months_with_any_covariate_outside(out_of_range: pd.DataFrame, n_reconstruction: int) -> dict[str, object]:
    """How much of the reconstruction period is extrapolation on at least one axis."""
    months = sorted(set(out_of_range["month"]))
    return {
        "n_months_any_outside": len(months),
        "pct_of_reconstruction": round(100 * len(months) / n_reconstruction, 1),
        "months": months,
    }


def joint_support(
    covariates: pd.DataFrame,
    fit: pd.PeriodIndex,
    reconstruction: pd.PeriodIndex,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    """Distance from each reconstruction month to its nearest fit month.

    Distances are Euclidean in covariate space standardized by the fit-window
    mean and standard deviation. Falling inside every covariate's range
    separately does not put a month inside the region the fit window actually
    occupies, so this reports the joint picture the per-covariate ranges miss.
    """
    f = covariates.loc[fit, list(columns)].dropna()
    r = covariates.loc[reconstruction, list(columns)].dropna()
    # A covariate that never varies over the fit window carries no distance
    # information; dividing by its spread would yield undefined distances and
    # silently report every month as supported.
    usable = [c for c in columns if f[c].std(ddof=1) > 0]
    if not usable:
        raise ValueError("no covariate varies over the fit window")
    f, r = f[usable], r[usable]
    center, scale = f.mean(), f.std(ddof=1)

    fz = ((f - center) / scale).to_numpy()
    rz = ((r - center) / scale).to_numpy()

    def nearest(points: np.ndarray, reference: np.ndarray, exclude_self: bool) -> np.ndarray:
        d = np.sqrt(((points[:, None, :] - reference[None, :, :]) ** 2).sum(axis=2))
        if exclude_self:
            np.fill_diagonal(d, np.inf)
        return d.min(axis=1)

    recon_nn = nearest(rz, fz, exclude_self=False)
    fit_nn = nearest(fz, fz, exclude_self=True)
    threshold = np.quantile(fit_nn, 0.95)

    return pd.DataFrame(
        [
            {
                "group": "fit months to nearest other fit month",
                "n": len(fit_nn),
                "median": float(np.median(fit_nn)),
                "p95": float(threshold),
                "max": float(fit_nn.max()),
                "n_beyond_fit_p95": 0,
            },
            {
                "group": "reconstruction months to nearest fit month",
                "n": len(recon_nn),
                "median": float(np.median(recon_nn)),
                "p95": float(np.quantile(recon_nn, 0.95)),
                "max": float(recon_nn.max()),
                "n_beyond_fit_p95": int((recon_nn > threshold).sum()),
            },
        ]
    )


def out_of_range_runs(out_of_range: pd.DataFrame) -> pd.DataFrame:
    """Collapse the out-of-range months into contiguous runs per covariate.

    A month-by-month listing of a hundred-odd rows obscures the shape of the
    problem, which is that the excursions cluster into a few long stretches.
    """
    records = []
    for covariate, group in out_of_range.groupby("covariate"):
        months = pd.PeriodIndex(sorted(group["month"]), freq="M")
        ordinals = months.astype("int64")
        breaks = [0, *(i for i in range(1, len(months)) if ordinals[i] != ordinals[i - 1] + 1)]
        for start, end in zip(breaks, [*breaks[1:], len(months)]):
            run = months[start:end]
            values = group.set_index("month").loc[[str(m) for m in run]]
            records.append(
                {
                    "covariate": covariate,
                    "from": str(run[0]),
                    "to": str(run[-1]),
                    "n_months": len(run),
                    "direction": values["direction"].iloc[0],
                    "max_excess": round(float(values["excess"].max()), 3),
                }
            )
    return pd.DataFrame.from_records(records).sort_values(["covariate", "from"]).reset_index(drop=True)
