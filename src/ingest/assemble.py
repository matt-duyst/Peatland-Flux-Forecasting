"""Join of monthly methane aggregates and covariates onto a regular month grid.

Every month in the target span receives a row, including months holding no
methane data. Absence is carried as a null value rather than a missing row, so
the series is regularly spaced by construction.
"""

from __future__ import annotations

import pandas as pd

from . import aggregate, covariates, paths, raw

TARGET_START = "2009-04"
TARGET_END = "2021-12"


def build_monthly(
    halfhourly: pd.DataFrame,
    start: str = TARGET_START,
    end: str = TARGET_END,
) -> pd.DataFrame:
    """Assemble the monthly dataset over the target span.

    The three methane columns are aggregated independently and kept separate.
    """
    grid = aggregate.month_grid(start, end)
    methane = aggregate.monthly_stats_all_columns(halfhourly, raw.FCH4_COLUMNS)
    covs = covariates.load_all()

    out = pd.DataFrame(index=grid)
    out.index.name = "month"
    out = out.join(methane, how="left").join(covs, how="left")

    for column in out.columns:
        if column.endswith("_n"):
            out[column] = out[column].fillna(0).astype("int64")

    return out.reset_index()


def write_monthly(monthly: pd.DataFrame) -> dict[str, object]:
    """Write the tidy dataset to CSV and Parquet under data/processed."""
    paths.ensure_dirs()
    frame = monthly.copy()
    frame["month"] = frame["month"].astype(str)

    csv_path = paths.processed_dir() / "monthly_bog_lake_fen.csv"
    parquet_path = paths.processed_dir() / "monthly_bog_lake_fen.parquet"
    frame.to_csv(csv_path, index=False)
    frame.to_parquet(parquet_path, index=False)

    return {
        "csv": csv_path.relative_to(paths.repo_root()),
        "parquet": parquet_path.relative_to(paths.repo_root()),
        "rows": len(frame),
        "columns": len(frame.columns),
    }


def absent_months(monthly: pd.DataFrame, count_column: str = "fch4_n") -> list[str]:
    """Months on the grid holding no observations in the given count column."""
    absent = monthly.loc[monthly[count_column] == 0, "month"]
    return [str(m) for m in absent]


def absent_months_all_methane(monthly: pd.DataFrame) -> list[str]:
    """Months holding no observations in any of the three methane columns."""
    count_columns = [f"{c.lower()}_n" for c in raw.FCH4_COLUMNS]
    absent = monthly.loc[monthly[count_columns].sum(axis=1) == 0, "month"]
    return [str(m) for m in absent]
