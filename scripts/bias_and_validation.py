"""Bias direction over the reconstruction period, and the out-of-sample Olson comparison.

States the sign convention, reports each holdout's bias as a multiplicative
error, estimates the net direction expected over a period that is both earlier
and wetter than the fit window, and compares the withheld 2009-2011 predictions
against Olson et al. (2013). Reconstructs nothing.

Run: .venv/bin/python scripts/bias_and_validation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import covariates  # noqa: E402
from study import bias, features, fitting, holdout, targets, weights as weighting, windows  # noqa: E402

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
    state_window(built)
    fit_months, reconstruction = built["fit"], built["reconstruction"]
    inverse_variance = weighting.inverse_variance_weights(monthly).reindex(fit_months).dropna()

    heading("SIGN CONVENTION")
    print(f"  Bias is {bias.CONVENTION}, on the logarithmic scale the model fits.")
    print("    positive  observation exceeded prediction, so the model predicted LOW")
    print("    negative  prediction exceeded observation, so the model predicted HIGH")
    print("  On a logarithmic scale a bias is multiplicative: a bias of b means the")
    print("  prediction sat at exp(-b) times the observation.")

    splits = holdout.build_splits(cov, fit_months)
    records = []
    for name, test in splits:
        train = fit_months.difference(test)
        for include in (True, False):
            for w in (None, inverse_variance.reindex(train).dropna()):
                records.append(
                    holdout.run_experiment(name, cov, monthly, train, test, columns, include, w, LEVEL)
                )

    heading("BIAS BY EXPERIMENT")
    table = bias.bias_table(records)
    full = table[table.model == "with water table"]
    print(full.round(4).to_string(index=False))

    heading("ARE THE TWO AXES SEPARABLE INSIDE THE FIT WINDOW?")
    independence = bias.axis_independence(cov, fit_months, features.WATER_TABLE)
    print(f"  correlation between calendar time and water table over the {independence['n']} fit "
          f"months: r = {independence['correlation_with_time']:+.3f}, p = {independence['p_value']:.3f}")
    wet = holdout.wettest_decile(cov, fit_months)
    early = holdout.earliest_years(fit_months, 3)
    print(f"  wettest decile and earliest three years share {len(wet.intersection(early))} months")
    print(f"  water table over the earliest three years: {cov.loc[early, features.WATER_TABLE].mean():.3f}")
    print(f"  water table over the rest of the fit window: "
          f"{cov.loc[fit_months.difference(early), features.WATER_TABLE].mean():.3f}")
    print("\n  The reconstruction period is both earlier and wetter. No block of the fit")
    print("  window is both, so the joint effect cannot be measured, only assumed.")

    heading("NET DIRECTION EXPECTED OVER THE RECONSTRUCTION")
    for weighting_name in ("unweighted", "inverse variance"):
        chosen = {
            r["experiment"]: float(r["bias_log_obs_minus_pred"])
            for r in records
            if r["model"] == "with water table" and r["weighting"] == weighting_name
        }
        combined = bias.combine_additively(
            {"backward transfer": chosen["earliest three years"], "wetter conditions": chosen["wettest decile"]}
        )
        print(f"\n  {weighting_name}")
        print(f"    backward transfer  {combined['component_backward transfer']:+.4f}")
        print(f"    wetter conditions  {combined['component_wetter conditions']:+.4f}")
        print(f"    net                {combined['bias_log_obs_minus_pred']:+.4f}  "
              f"-> prediction sits at {combined['predicted_over_observed']:.3f} of the observation "
              f"({combined['prediction_error_pct']:+.1f}%)")
        print(f"    direction          {combined['direction']}")
        print(f"    cancellation       {100 * combined['cancellation_share']:.0f}% of the summed magnitude")

    heading("IS THE BACKWARD-TRANSFER BIAS UNIFORM ACROSS WATER TABLE?")
    print("If it is, treating the two effects as separable is more defensible.")
    for weighting_name in ("unweighted", "inverse variance"):
        record = next(
            r for r in records
            if r["experiment"] == "earliest three years"
            and r["model"] == "with water table"
            and r["weighting"] == weighting_name
        )
        train = fit_months.difference(early)
        design = features.build_design(cov, early, record["fit"].water_table_bounds, True)
        predicted = record["fit"].predict(design)
        observed = features.log_target(monthly, early)
        print(f"\n  {weighting_name}")
        print(bias.bias_by_covariate_band(observed, predicted, cov[features.WATER_TABLE]).to_string())

    heading("OLSON COMPARISON, OUT OF SAMPLE")
    print("The earliest three years are withheld, so 2009-2011 is predicted by a model")
    print("fitted only on 2012-2019. Every month of those years is integrated, including")
    print("the three before the flux record begins, which the model never saw either.")
    train = fit_months.difference(early)
    years = pd.period_range("2009-01", "2011-12", freq="M")
    available = pd.PeriodIndex(cov.loc[years, list(columns)].dropna().index, freq="M")
    for weighting_name, w in (("unweighted", None), ("inverse variance", inverse_variance.reindex(train).dropna())):
        bounds = features.clamp_bounds(cov, train, features.WATER_TABLE)
        fit = fitting.fit_lad(
            features.build_design(cov, train, bounds, True), features.log_target(monthly, train), w
        )
        predicted_flux = np.exp(fit.predict(features.build_design(cov, available, bounds, True)))
        annual = targets.monthly_flux_to_annual(predicted_flux)
        print(f"\n  {weighting_name}, model fitted on {len(train)} months of 2012-2019")
        print(targets.holdout_against_published(annual).to_string(index=False))

    heading("IN-SAMPLE AGREEMENT, REPORTED AS FIT QUALITY NOT VALIDATION")
    bounds = features.clamp_bounds(cov, fit_months, features.WATER_TABLE)
    fit = fitting.fit_lad(
        features.build_design(cov, fit_months, bounds, True),
        features.log_target(monthly, fit_months),
        inverse_variance,
    )
    predicted_flux = np.exp(fit.predict(features.build_design(cov, available, bounds, True)))
    annual = targets.monthly_flux_to_annual(predicted_flux)
    print("Fitted on all 117 months, which include 2009-2011. Agreement here measures")
    print("how well the model describes data it was shown, not reconstruction skill.")
    print(targets.holdout_against_published(annual).to_string(index=False))

    heading("STATUS OF EACH COMPARISON")
    print("  Shurpali et al. (1993), Shurpali and Verma (1998), 1991-1992")
    print("    independent validation: measured before this record began, never seen")
    print("  Olson et al. (2013) annual budgets 2009-2011, earliest-years holdout")
    print("    out-of-sample comparison against an independent flux analysis")
    print("  Olson et al. (2013) annual budgets 2009-2011, full fit")
    print("    fit quality only, since those months are in the training set")
    print("  Olson et al. (2013) retrospective range 1991-2011")
    print("    method agreement: produced by fitting a short flux record and")
    print("    projecting backward, which is the approach used here")


if __name__ == "__main__":
    main()
