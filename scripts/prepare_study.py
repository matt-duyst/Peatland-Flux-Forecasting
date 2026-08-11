"""Establish whether the pre-2009 period can be reconstructed from the observed record.

Reports the fit and reconstruction windows and the covariate coverage that bounds
them, how far the reconstruction period falls outside the range the fit period
covers, whether covariate distributions differ between the two, what
inverse-variance weighting will do to the fit window, and the published budgets
the result will be checked against. Fits nothing.

Run: .venv/bin/python scripts/prepare_study.py
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import budgets, covariates, merge, raw  # noqa: E402
from study import stationarity, support, targets, weights, windows  # noqa: E402

RULE = "=" * 78


def heading(text: str) -> None:
    print(f"\n{RULE}\n{text}\n{RULE}")


def state_window(built) -> None:
    """Say which fit window the numbers below rest on, every time."""
    excluded = ", ".join(str(m) for m in built["excluded"]) or "none"
    print(f"  Fit window: {len(built['fit'])} months "
          f"(nominal {len(built['fit_nominal'])}, excluded as instrument artifacts: {excluded})")


def main() -> None:
    pd.set_option("display.width", 220)
    cov = covariates.load_all()
    monthly = pd.read_csv(
        Path(__file__).resolve().parents[1] / "data/processed/monthly_fch4_from_daily.csv"
    )
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    monthly = monthly.set_index("month")
    columns = windows.RECONSTRUCTION_COVARIATES

    heading("COVARIATE COVERAGE")
    coverage = windows.covariate_coverage(cov)
    print(coverage.to_string(index=False))
    print("\nWhat bounds each window:")
    print(windows.binding_constraint(coverage).to_string(index=False))
    print(f"\nExcluded from the reconstruction covariates: {', '.join(windows.CONTEMPORANEOUS_ONLY)}")
    print("  Carbon dioxide flux begins with the methane record and has no earlier values.")

    heading("FIT AND RECONSTRUCTION WINDOWS")
    built = windows.build_windows(cov, monthly.index, columns)
    state_window(built)
    print(windows.window_accounting(built).to_string(index=False))
    for name in ("fit", "reconstruction"):
        absent = windows.absent_months(built, name)
        print(f"\nMonths absent from the {name} span ({len(absent)}):")
        print(textwrap.fill(", ".join(absent), width=76, initial_indent="  ", subsequent_indent="  "))
    print(f"\nMethane months lost to covariate limits ({len(built['methane_excluded'])}):")
    print(textwrap.fill(", ".join(str(m) for m in built["methane_excluded"]),
                        width=76, initial_indent="  ", subsequent_indent="  "))

    heading("RECONSTRUCTION PERIOD AGAINST FIT PERIOD")
    comparison = support.distribution_comparison(cov, built["fit"], built["reconstruction"], columns)
    print(comparison.round(3).to_string(index=False))

    outside = support.out_of_range_months(cov, built["fit"], built["reconstruction"], columns)
    summary = support.months_with_any_covariate_outside(outside, len(built["reconstruction"]))
    print(f"\nReconstruction months with at least one covariate outside the fit range: "
          f"{summary['n_months_any_outside']} of {len(built['reconstruction'])} "
          f"({summary['pct_of_reconstruction']}%)")
    if len(outside):
        print("\nOut-of-range stretches, by covariate:")
        print(support.out_of_range_runs(outside).to_string(index=False))
        print(f"\nAll {len(outside)} out-of-range covariate-months:")
        print(textwrap.fill(", ".join(f"{r.month}/{r.covariate}" for r in outside.itertuples()),
                            width=76, initial_indent="  ", subsequent_indent="  "))

    print("\nJoint support, standardized covariate space:")
    print(support.joint_support(cov, built["fit"], built["reconstruction"], columns).round(3).to_string(index=False))

    heading("STATIONARITY OF THE COVARIATES")
    print("Raw monthly values:")
    print(stationarity.compare_periods(cov, built["fit"], built["reconstruction"], columns).round(4).to_string(index=False))
    print("\nAnomalies from the month-of-year mean, removing the seasonal cycle:")
    print(stationarity.compare_periods(
        cov, built["fit"], built["reconstruction"], columns, deseasonalised=True
    ).round(4).to_string(index=False))
    print("\nThe contrast Olson et al. (2013) drew, 1991-1999 against 2007-2011:")
    print(stationarity.early_late_contrast(cov, columns, ("1991-01", "1999-12"), ("2007-01", "2011-12")).to_string(index=False))
    print("\nAnnual means over the reconstruction window:")
    print(stationarity.annual_means(cov, columns, built["reconstruction"]).to_string())

    heading("WEIGHTING OF THE FIT WINDOW")
    print(weights.weight_summary(monthly, built["fit"]).to_string())
    print("\nConcentration of weight:")
    print(weights.weight_concentration(monthly, built["fit"]).to_string(index=False))
    print("\nLeast influential months under inverse-variance weighting:")
    print(weights.least_influential(monthly, built["fit"]).to_string())
    print("\nMost influential, for contrast:")
    print(weights.most_influential(monthly, built["fit"]).to_string())
    print("\nWeight by month of year:")
    print(weights.seasonal_weight_balance(monthly, built["fit"]).to_string())

    heading("VALIDATION TARGETS")
    print(f"{targets.OLSON_CITATION}, doi {targets.OLSON_DOI}")
    print(f"Conversion: 1 g CH4 carries {targets.C_PER_CH4:.5f} g C; "
          f"1 g C as methane is {1 / targets.C_PER_CH4:.5f} g CH4.")
    print("\nPublished annual budgets, both mass conventions:")
    print(targets.published_annual_targets().to_string(index=False))
    reconstruction_range = targets.published_reconstruction_range()
    print(f"\nPublished 1991-2011 reconstruction: "
          f"{reconstruction_range['low_g_C']} to {reconstruction_range['high_g_C']} "
          f"+/- {reconstruction_range['uncertainty_g_C']} g C m-2 yr-1, "
          f"equivalently {reconstruction_range['low_g_CH4']} to {reconstruction_range['high_g_CH4']} "
          f"+/- {reconstruction_range['uncertainty_g_CH4']} g CH4 m-2 yr-1")

    annual = budgets.annual_budget(merge.merge_halfhourly(raw.load_halfhourly()))
    print("\nObserved record against the published budgets:")
    print(targets.observed_against_published(annual).to_string(index=False))

    print(f"\nIndependent check, {' and '.join(targets.SHURPALI_CITATIONS)}:")
    print(targets.independent_check_coverage(monthly.index).to_string(index=False))


if __name__ == "__main__":
    main()
