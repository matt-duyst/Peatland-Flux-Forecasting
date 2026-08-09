"""Build the monthly dataset of methane aggregates and covariates.

Verifies each reconstructed covariate against its known values, reports coverage
against the target monthly span, summarises observation counts per month, and
lists months holding no methane observations.

Run: .venv/bin/python scripts/02_build_monthly.py
Writes: data/processed/monthly_bog_lake_fen.{csv,parquet}
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import aggregate, assemble, covariates, raw  # noqa: E402


def main() -> None:
    pd.set_option("display.width", 200)
    halfhourly = raw.load_halfhourly()
    monthly = assemble.build_monthly(halfhourly)
    grid = aggregate.month_grid(assemble.TARGET_START, assemble.TARGET_END)

    print("=" * 78)
    print("COVARIATE VERIFICATION AGAINST KNOWN VALUES")
    print("=" * 78)
    checks = covariates.verify_spot_checks(covariates.load_all())
    print(checks.to_string(index=False))
    if not checks["match"].all():
        print("\n  mismatch present in the rows above")

    print("\n" + "=" * 78)
    print("COVARIATE COVERAGE AGAINST TARGET GRID "
          f"({assemble.TARGET_START}..{assemble.TARGET_END}, {len(grid)} months)")
    print("=" * 78)
    print(covariates.coverage(covariates.load_all(), grid).to_string(index=False))

    print("\n" + "=" * 78)
    print("OBSERVATION COUNT DISTRIBUTION PER MONTH")
    print("=" * 78)
    for column in raw.FCH4_COLUMNS:
        count_column = f"{column.lower()}_n"
        present = monthly.loc[monthly[count_column] > 0, count_column]
        if present.empty:
            print(f"\n{column}: no months with data")
            continue
        print(f"\n{column} — {len(present)} months with data")
        print(aggregate.observation_count_distribution(
            monthly.loc[monthly[count_column] > 0], count_column
        ).to_string())

    print("\n" + "=" * 78)
    print("ABSENT MONTHS")
    print("=" * 78)
    all_absent = assemble.absent_months_all_methane(monthly)
    print(f"months on grid with no methane in any column: {len(all_absent)}")
    print("  " + ", ".join(all_absent))
    base_absent = assemble.absent_months(monthly, "fch4_n")
    print(f"\nmonths with no data in the base FCH4 column: {len(base_absent)}")
    print("  " + ", ".join(base_absent))

    print("\n" + "=" * 78)
    print("OUTPUT")
    print("=" * 78)
    for key, value in assemble.write_monthly(monthly).items():
        print(f"  {key}: {value}")
    print()
    print(monthly.head(4).to_string(index=False))


if __name__ == "__main__":
    main()
