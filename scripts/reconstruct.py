"""Project the fitted model back to 1990, and show what each year rests on.

The projection is the vehicle for a demonstration, not an estimate to be
defended. Reports the reconstruction alongside the coefficient instability, the
support verdict for every year, the sensitivity range across water table
variants, and the directional bias each year is expected to carry.

Run: .venv/bin/python scripts/reconstruct.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import covariates  # noqa: E402
from study import (  # noqa: E402
    features, fitting, reconstruct, stability, targets, weights as weighting, windows,
)

RULE = "=" * 78
LEVEL = 0.90
WET_END_BIAS_LOG = 0.148  # wettest band of the backward-transfer holdout, weighted


def heading(text: str) -> None:
    print(f"\n{RULE}\n{text}\n{RULE}")


def main() -> None:
    pd.set_option("display.width", 260)
    cov = covariates.load_all()
    monthly = pd.read_csv(
        Path(__file__).resolve().parents[1] / "data/processed/monthly_fch4_from_daily.csv"
    )
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    monthly = monthly.set_index("month")

    columns = windows.RECONSTRUCTION_COVARIATES
    built = windows.build_windows(cov, monthly.index, columns)
    fit_months, recon_months = built["fit"], built["reconstruction"]
    iv = weighting.inverse_variance_weights(monthly).reindex(fit_months).dropna()

    heading("WHY THE WATER TABLE TERM CANNOT BE PROJECTED")
    path = stability.coefficient_path(cov, monthly, fit_months, weights=iv)
    print(path[["dropped_wettest_pct", "n_months", "wte_max", "water_table_coef",
                "water_table_lo", "water_table_hi"]].round(3).to_string(index=False))
    result = stability.verdict(path)
    print(f"\n  seed {stability.SEED}, 500 bootstrap resamples per step")
    print(f"  stable: {result['stable']}")
    for failure in result["failures"]:
        print(f"    fails because {failure}")
    print(f"  therefore {result['bracket_meaning']}")
    print("\n  The spread across variants below is a SENSITIVITY RANGE. It is not a")
    print("  confidence interval and does not bound the answer.")

    heading("RECONSTRUCTION, WEIGHTED FULL MODEL PRIMARY (g C m-2 yr-1)")
    reconstruction = reconstruct.monthly_reconstruction(cov, monthly, fit_months, recon_months, iv, LEVEL)
    support_table = reconstruct.year_support(cov, fit_months, recon_months, columns)
    annual = reconstruct.annual_reconstruction(reconstruction, support_table, WET_END_BIAS_LOG)
    print(annual.to_string(index=False))
    inside = (annual["support"] == "inside").sum()
    print(f"\n  {inside} of {len(annual)} years lie inside the fitted support.")
    print(f"  {len(annual) - inside} require the model to extrapolate on at least one covariate.")

    heading("EMPIRICAL COVERAGE AGAINST NOMINAL")
    primary, bounds = reconstruct.fit_variant(cov, monthly, fit_months, "clamped", iv)
    in_sample = fitting.empirical_interval(
        primary, primary.predict(features.build_design(cov, fit_months, bounds, True)), LEVEL
    )
    observed = features.log_target(monthly, fit_months)
    print(f"  nominal level                          {LEVEL:.0%}")
    print(f"  in sample, over the {len(fit_months)} fit months      "
          f"{fitting.coverage(in_sample, observed):.1%}")
    print("  backward transfer, weighted, held out  84.4%  (from scripts/holdout_experiments.py)")
    print("  backward transfer, unweighted          62.5%  (from scripts/holdout_experiments.py)")
    print("\n  No empirical coverage can be computed over the reconstruction period,")
    print("  because nothing was observed there. The held-out figures are the only")
    print("  evidence about how these intervals behave away from the fit window.")

    heading("INDEPENDENT VALIDATION: THE 1991 AND 1992 GROWING SEASONS")
    for year in targets.SHURPALI_SEASONS:
        season = pd.period_range(f"{year}-05", f"{year}-10", freq="M")
        available = season.intersection(reconstruction.index)
        total = targets.monthly_flux_to_annual(reconstruction.loc[available, "clamped"])
        low = targets.monthly_flux_to_annual(reconstruction.loc[available, "lower"])
        high = targets.monthly_flux_to_annual(reconstruction.loc[available, "upper"])
        row = support_table.set_index("year").loc[year]
        print(f"  {year} growing season, May to October, {len(available)} months")
        print(f"    reconstructed {float(total['g_C_m2'].iloc[0]):.2f} g C m-2 "
              f"({float(low['g_C_m2'].iloc[0]):.2f} to {float(high['g_C_m2'].iloc[0]):.2f})")
        print(f"    support: {row['support']}, {int(row['n_months_outside_range'])} months outside range")
    print(f"\n  Measured by {' and '.join(targets.SHURPALI_CITATIONS)}. Their published")
    print("  values were not supplied to this analysis, so the comparison is set up")
    print("  but not completed. These are the two best-supported years in the")
    print("  reconstruction, which is what makes the check worth doing.")

    heading("METHOD AGREEMENT: OLSON'S RETROSPECTIVE RANGE")
    published = targets.published_reconstruction_range()
    complete = annual[annual["n_months"] == 12]
    print(f"  Olson et al. (2013), 1991 to 2011: {published['low_g_C']} to {published['high_g_C']} "
          f"+/- {published['uncertainty_g_C']} g C m-2 yr-1")
    print(f"  This reconstruction, {len(complete)} complete years 1990 to 2008: "
          f"{complete['clamped'].min():.2f} to {complete['clamped'].max():.2f}, "
          f"mean {complete['clamped'].mean():.2f}")
    print("\n  Both were produced by fitting a short flux record and projecting backward.")
    print("  Agreement between them is method agreement, not independent confirmation.")

    heading("WHAT THIS DEMONSTRATES")
    print("  1  The water table coefficient is a property of the sample, not the system:")
    print("     it drifts 59% as its supporting range narrows, monotonically.")
    print(f"  2  {len(annual) - inside} of {len(annual)} reconstructed years need extrapolation on at least")
    print("     one covariate, mostly water table.")
    print("  3  The episodic component that dominates 2011 is invisible to the")
    print("     covariates, so its frequency before 2009 is unconstrained.")
    print("\n  Each year's sensitivity span shows how much of its estimate rests on the")
    print("  first of these. Spans reach a full multiple of the estimate itself.")


if __name__ == "__main__":
    main()
