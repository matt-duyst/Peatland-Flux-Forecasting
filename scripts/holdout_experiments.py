"""Test whether the model predicts conditions it was not fitted on.

Withholds four blocks of the fit window in turn, each chosen to resemble the
reconstruction problem, and reports error, interval coverage and the joint
covariate distance from the training set. Reconstructs nothing.

Run: .venv/bin/python scripts/holdout_experiments.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import covariates  # noqa: E402
from study import features, fitting, holdout, weights as weighting, windows  # noqa: E402

RULE = "=" * 78
LEVEL = 0.90


def heading(text: str) -> None:
    print(f"\n{RULE}\n{text}\n{RULE}")


def state_window(built) -> None:
    """Say which fit window the numbers below rest on, every time."""
    excluded = ", ".join(str(m) for m in built["excluded"]) or "none"
    print(f"  Fit window: {len(built['fit'])} months "
          f"(nominal {len(built['fit_nominal'])}, excluded as instrument artifacts: {excluded})")


def main() -> None:
    pd.set_option("display.width", 240)
    cov = covariates.load_all()
    monthly = pd.read_csv(
        Path(__file__).resolve().parents[1] / "data/processed/monthly_fch4_from_daily.csv"
    )
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    monthly = monthly.set_index("month")

    columns = windows.RECONSTRUCTION_COVARIATES
    built = windows.build_windows(cov, monthly.index, columns)
    fit_months = built["fit"]
    state_window(built)
    inverse_variance = weighting.inverse_variance_weights(monthly).reindex(fit_months).dropna()

    heading("MODEL FORM")
    print("  Target      log of the monthly mean flux")
    print("  Soil temp   degrees Celsius, linear on log flux, so the response is a")
    print("              first-order exponential and the slope is a Q10")
    print("  Water table clamped to the training range, holding flat beyond it")
    print("  Estimator   least absolute deviations, maximum likelihood under Laplace error")
    print("  Intervals   empirical quantiles of training residuals, and a Laplace")
    print("              variant widened by each month's own standard error")
    print(f"  Level       {LEVEL:.0%}")
    print(f"  Bias        {fitting.BIAS_CONVENTION}: positive means the model predicted")
    print("              below the observation, negative means it predicted above")
    print("\n  Nothing in the fit is stochastic: the estimator is a linear program solved")
    print("  exactly and the intervals are quantiles. No seed is consumed.")

    whole = features.build_design(
        cov, fit_months, features.clamp_bounds(cov, fit_months, features.WATER_TABLE), True
    )
    whole_fit = fitting.fit_lad(whole, features.log_target(monthly, fit_months))
    q10 = features.q10_from_slope(float(whole_fit.as_series()["soil_temp_c"]))
    print(f"\n  Fitted on all {len(fit_months)} months, Q10 = {q10:.2f}")
    print("  Deventer et al. (2019) measured 2.9 at this site, 95% interval 1.9 to 4.3")

    heading("WHAT EACH HOLDOUT WITHHOLDS")
    splits = holdout.build_splits(cov, fit_months)
    for name, test in splits:
        train = fit_months.difference(test)
        print(f"\n{name}: {len(test)} months held out, {len(train)} retained")
        print(f"  {', '.join(str(m) for m in test)}")
        print(holdout.holdout_covariate_contrast(cov, train, test, columns).to_string(index=False))

    heading("HOW FAR EACH HOLDOUT EXTRAPOLATES, AGAINST THE RECONSTRUCTION")
    print("Water table, the axis on which the reconstruction leaves the fitted range.")
    print(holdout.analogue_strength(cov, fit_months, built["reconstruction"], splits).to_string(index=False))

    records = []
    for name, test in splits:
        train = fit_months.difference(test)
        for include in (True, False):
            for weights in (None, inverse_variance.reindex(train).dropna()):
                records.append(
                    holdout.run_experiment(
                        name, cov, monthly, train, test, columns, include, weights, LEVEL
                    )
                )

    heading("RESULTS, UNWEIGHTED")
    view = [
        "experiment", "model", "n_train", "n_test", "q10",
        "medae_log", "mae_log", "mape_pct", "bias_log_obs_minus_pred",
        "coverage_empirical", "coverage_laplace",
        "holdout_nn_median", "holdout_nn_max", "holdout_beyond_train_p95",
    ]
    table = holdout.summarize(records)
    print(table[table.weighting == "unweighted"][view].round(3).to_string(index=False))

    heading("RESULTS, INVERSE-VARIANCE WEIGHTED")
    print(table[table.weighting == "inverse variance"][view].round(3).to_string(index=False))

    heading("TRAINING ERROR FOR CONTRAST")
    contrast = table[["experiment", "model", "weighting", "train_medae_log", "medae_log"]].copy()
    contrast["holdout_over_train"] = (contrast.medae_log / contrast.train_medae_log).round(2)
    print(contrast.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
