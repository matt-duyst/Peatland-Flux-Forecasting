"""Held-out experiments that test extrapolation inside the observed record.

Each experiment withholds a block of months chosen to resemble the reconstruction
problem, fits on what remains, and predicts the withheld block. The wettest-decile
split is the closest available analogue: it asks the model to predict water table
conditions above anything it was fitted on, which is what the pre-2009 period
requires of it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import features, fitting, support

WATER_TABLE = features.WATER_TABLE
SOIL_TEMP = features.SOIL_TEMP


def wettest_decile(covariates: pd.DataFrame, months: pd.PeriodIndex, share: float = 0.10) -> pd.PeriodIndex:
    """Months with the highest water table, the direction the reconstruction extrapolates."""
    values = covariates.loc[months, WATER_TABLE].dropna().sort_values(ascending=False)
    return pd.PeriodIndex(values.index[: max(1, int(round(share * len(values))))], freq="M").sort_values()


def coldest_decile(covariates: pd.DataFrame, months: pd.PeriodIndex, share: float = 0.10) -> pd.PeriodIndex:
    """Months with the lowest soil temperature."""
    values = covariates.loc[months, SOIL_TEMP].dropna().sort_values()
    return pd.PeriodIndex(values.index[: max(1, int(round(share * len(values))))], freq="M").sort_values()


def earliest_years(months: pd.PeriodIndex, n_years: int = 3) -> pd.PeriodIndex:
    """The first whole years of the record, held out to test backward transfer."""
    years = sorted({m.year for m in months})[:n_years]
    return pd.PeriodIndex([m for m in months if m.year in years], freq="M").sort_values()


def latest_years(months: pd.PeriodIndex, n_years: int = 3) -> pd.PeriodIndex:
    """The last whole years of the record, held out to test forward transfer."""
    years = sorted({m.year for m in months})[-n_years:]
    return pd.PeriodIndex([m for m in months if m.year in years], freq="M").sort_values()


def _distance(covariates: pd.DataFrame, train: pd.PeriodIndex, test: pd.PeriodIndex,
              columns: tuple[str, ...]) -> dict[str, float]:
    """Joint distance from the holdout to its training set, as used in preparation."""
    table = support.joint_support(covariates, train, test, columns).set_index("group")
    held = table.loc["reconstruction months to nearest fit month"]
    trained = table.loc["fit months to nearest other fit month"]
    return {
        "train_nn_median": float(trained["median"]),
        "train_nn_p95": float(trained["p95"]),
        "holdout_nn_median": float(held["median"]),
        "holdout_nn_max": float(held["max"]),
        "holdout_beyond_train_p95": int(held["n_beyond_fit_p95"]),
    }


def run_experiment(
    name: str,
    covariates: pd.DataFrame,
    monthly: pd.DataFrame,
    train: pd.PeriodIndex,
    test: pd.PeriodIndex,
    columns: tuple[str, ...],
    include_water_table: bool,
    weights: pd.Series | None = None,
    level: float = 0.90,
    include_hysteresis: bool = False,
) -> dict[str, object]:
    """Fit on the training months and score the held-out months.

    The water table clamp is set from the training months alone, so the holdout
    cannot widen the range the model treats as observed.
    """
    bounds = features.clamp_bounds(covariates, train, WATER_TABLE)
    design_train = features.build_design(covariates, train, bounds, include_water_table, include_hysteresis)
    design_test = features.build_design(covariates, test, bounds, include_water_table, include_hysteresis)
    y_train = features.log_target(monthly, train)
    y_test = features.log_target(monthly, test)

    fit = fitting.fit_lad(design_train, y_train, weights)
    fit.water_table_bounds = bounds
    predicted = fit.predict(design_test)

    empirical = fitting.empirical_interval(fit, predicted, level)
    observation_scale = features.log_standard_error(monthly, test)
    laplace = fitting.laplace_interval(fit, predicted, level, observation_scale)

    record: dict[str, object] = {
        "experiment": name,
        "model": ("with water table" if include_water_table else "without water table")
        + (" + hysteresis" if include_hysteresis else ""),
        "weighting": "inverse variance" if weights is not None else "unweighted",
        "n_train": len(train),
        "n_test": len(test),
        "q10": features.q10_from_slope(float(fit.as_series()["soil_temp_c"])),
        "laplace_scale_log": fit.laplace_scale,
        "train_medae_log": float(np.median(np.abs(fit.residuals))),
    }
    record |= fitting.error_metrics(y_test, predicted)
    record |= {
        "coverage_empirical": fitting.coverage(empirical, y_test),
        "coverage_laplace": fitting.coverage(laplace, y_test),
        "nominal_level": level,
    }
    record |= _distance(covariates, train, test, columns)
    record["fit"] = fit
    return record


def build_splits(
    covariates: pd.DataFrame, fit_months: pd.PeriodIndex
) -> list[tuple[str, pd.PeriodIndex]]:
    """The four held-out blocks, each named for what it withholds."""
    return [
        ("wettest decile", wettest_decile(covariates, fit_months)),
        ("coldest decile", coldest_decile(covariates, fit_months)),
        ("earliest three years", earliest_years(fit_months)),
        ("latest three years", latest_years(fit_months)),
    ]


def summarize(records: list[dict[str, object]], columns: list[str] | None = None) -> pd.DataFrame:
    """Table of experiment results with the model objects dropped."""
    frame = pd.DataFrame([{k: v for k, v in r.items() if k != "fit"} for r in records])
    return frame if columns is None else frame[columns]


def holdout_covariate_contrast(
    covariates: pd.DataFrame, train: pd.PeriodIndex, test: pd.PeriodIndex, columns: tuple[str, ...]
) -> pd.DataFrame:
    """How far each holdout covariate sits outside the training range."""
    records = []
    for column in columns:
        tr = covariates.loc[train, column].dropna()
        te = covariates.loc[test, column].dropna()
        outside = ((te < tr.min()) | (te > tr.max())).sum()
        records.append(
            {
                "covariate": column,
                "train_min": round(float(tr.min()), 3),
                "train_max": round(float(tr.max()), 3),
                "holdout_min": round(float(te.min()), 3),
                "holdout_max": round(float(te.max()), 3),
                "n_holdout_outside": int(outside),
                "pct_holdout_outside": round(100 * outside / len(te), 1),
            }
        )
    return pd.DataFrame.from_records(records)


def analogue_strength(
    covariates: pd.DataFrame,
    fit_months: pd.PeriodIndex,
    reconstruction: pd.PeriodIndex,
    splits: list[tuple[str, pd.PeriodIndex]],
    column: str = WATER_TABLE,
) -> pd.DataFrame:
    """How far each holdout extrapolates, against how far the reconstruction does.

    A holdout drawn from inside the record can only reach the edge of that
    record, so it tests a milder extrapolation than the reconstruction demands.
    This states the gap rather than leaving the analogue to stand unqualified.
    """
    fit_values = covariates.loc[fit_months, column].dropna()
    recon = covariates.loc[reconstruction, column].dropna()
    recon_excess = float(max(recon.max() - fit_values.max(), fit_values.min() - recon.min(), 0.0))

    records = []
    for name, test in splits:
        train = fit_months.difference(test)
        train_values = covariates.loc[train, column].dropna()
        held = covariates.loc[test, column].dropna()
        excess = float(
            max(held.max() - train_values.max(), train_values.min() - held.min(), 0.0)
        )
        records.append(
            {
                "experiment": name,
                "train_range": round(float(train_values.max() - train_values.min()), 3),
                "max_excess": round(excess, 3),
                "reconstruction_max_excess": round(recon_excess, 3),
                "share_of_reconstruction_excess": (
                    round(excess / recon_excess, 2) if recon_excess else float("nan")
                ),
            }
        )
    return pd.DataFrame.from_records(records)
