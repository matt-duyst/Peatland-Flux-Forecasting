"""Merge the methane columns, report quality diagnostics, and aggregate to monthly.

Produces the merged half-hourly series with per-value provenance, negative-flux
and coverage diagnostics, daily and monthly aggregates under the minimum-coverage
rule, and annual budgets integrated from observed half-hours.

Run: .venv/bin/python scripts/04_merge_qc_aggregate.py
Writes: data/processed/{halfhourly_merged,daily_fch4,monthly_fch4_from_daily}.*
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import budgets, coverage, daily, merge, paths, qc, raw, site  # noqa: E402


def main() -> None:
    pd.set_option("display.width", 220)
    frame = raw.load_halfhourly()
    # The site-aggregated series is treated as independent of both replicates,
    # so precedence should never have to arbitrate against it.
    merge.assert_disjoint(frame, (site.BASE_COLUMN, site.TGA_COLUMN))
    merge.assert_disjoint(frame, (site.BASE_COLUMN, site.LI7700_COLUMN))
    merged = merge.merge_halfhourly(frame)

    print("=" * 78)
    print("MERGED SERIES WITH PROVENANCE")
    print("=" * 78)
    print(f"  precedence: {' > '.join(merge.PRECEDENCE)}\n")
    print(merge.provenance_summary(merged).to_string(index=False))
    print("\nBy year:")
    print(merge.provenance_by_year(merged).to_string())
    print("\nPrecedence contention:")
    for key, value in merge.contention_summary(merged).items():
        print(f"  {key:28s} {value:,}")
    print("\nAnalyser switching, each switch carrying the inter-analyzer scale offset:")
    print(merge.switch_summary(merged).to_string(index=False))
    print(f"  total switches across the series: {merge.total_switches(merged):,}")
    print("\nDeployment boundaries, runs of at least 200 half-hours:")
    print(merge.structural_boundaries(merged).to_string(index=False))

    print("\n" + "=" * 78)
    print("NEGATIVE FLUXES")
    print("=" * 78)
    for key, value in qc.negative_summary(merged).items():
        print(f"  {key:38s} {value}")
    print(
        f"\nSensitivity across a detection limit of {site.DETECTION_LIMIT:g}"
        f" +/- {site.DETECTION_LIMIT_UNCERTAINTY:g} nmol m-2 s-1:"
    )
    print(qc.detection_limit_sensitivity(merged)[
        ["detection_limit", "n_negative", "n_negative_within_detection_limit",
         "n_negative_exceeding_detection_limit", "pct_of_negatives_exceeding_limit"]
    ].to_string(index=False))
    print("\nConcurrence between analyzers:")
    for key, value in qc.concurrent_negatives(frame).items():
        print(f"  {key:42s} {value}")
    print("\nNegative share by year:")
    print(qc.negative_share_by_year(merged).to_string(index=False))

    print("\n" + "=" * 78)
    print("DAILY AGGREGATION BY MINIMUM-COVERAGE THRESHOLD")
    print("=" * 78)
    comparison = daily.threshold_comparison(merged)
    print(daily.threshold_summary(comparison, site.DAILY_THRESHOLDS).round(3).to_string(index=False))

    print("\nDiurnal against seasonal structure:")
    for key, value in daily.diurnal_vs_seasonal(merged).items():
        print(f"  {key:38s} {value:,.4f}" if isinstance(value, float) else f"  {key:38s} {value:,}")
    print("\nHourly means, growing season against the rest of the year:")
    print(daily.diurnal_cycle_by_season(merged).round(2).to_string(index=False))

    print("\n" + "=" * 78)
    print("COVERAGE BY MONTH OF YEAR, ALL YEARS POOLED")
    print("=" * 78)
    pooled = coverage.coverage_by_month_of_year(merged)
    display = ["month_of_year", "observed", "possible", "frac_observed"] + [
        c for c in pooled.columns if c.startswith("frac_") and c != "frac_observed"
    ]
    print(pooled[display].round(4).to_string(index=False))
    print("\nSeasonal contrast:")
    for key, value in coverage.seasonal_bias_summary(merged).items():
        print(f"  {key:26s} {value:.4f}")

    print("\nCoverage by year and month of year:")
    print(coverage.coverage_matrix(merged).round(3).to_string())

    print("\n" + "=" * 78)
    print("ANNUAL BUDGETS FROM OBSERVED HALF-HOURS (g-CH4 m-2 yr-1)")
    print("=" * 78)
    annual = budgets.annual_budget(merged)
    print(budgets.budget_gap(annual).round(2).to_string(index=False))
    print(f"\n  published uncertainty: {site.PUBLISHED_BUDGET_UNCERTAINTY_PCT[0]}-"
          f"{site.PUBLISHED_BUDGET_UNCERTAINTY_PCT[1]}%")

    print("\nPooled-mean scaling against calendar-weighted monthly means:")
    print(budgets.budget_method_comparison(merged).round(2).to_string(index=False))

    print("\nAll years, observed-only integration:")
    print(annual[["year", "n_halfhours", "coverage_pct", "mean_flux", "observed_only"]]
          .round(2).to_string(index=False))

    paths.ensure_dirs()
    daily_frame = daily.daily_stats(merged)
    monthly_frame = daily.daily_to_monthly(daily_frame)
    written = {
        "halfhourly_merged": merged.assign(
            timestamp_start=merged["timestamp_start"].astype(str)
        ),
        "daily_fch4": daily_frame.assign(date=daily_frame["date"].astype(str)),
        "monthly_fch4_from_daily": monthly_frame.assign(
            month=monthly_frame["month"].astype(str)
        ),
    }
    print("\n" + "=" * 78)
    print("OUTPUT")
    print("=" * 78)
    for name, table in written.items():
        table.to_csv(paths.processed_dir() / f"{name}.csv", index=False)
        table.to_parquet(paths.processed_dir() / f"{name}.parquet", index=False)
        print(f"  {name}: {len(table):,} rows x {len(table.columns)} cols")


if __name__ == "__main__":
    main()
