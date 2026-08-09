"""Test configuration and synthetic frame builders.

Every fixture here is constructed in memory. No test reads the AmeriFlux
workbook, any file under data/, or anything else on disk, so the suite runs
offline and its expected values are derivable by hand rather than copied from a
previous run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import site  # noqa: E402

HALFHOUR = pd.Timedelta(minutes=30)


def timestamps(start: str, n: int) -> pd.DatetimeIndex:
    """``n`` consecutive half-hourly timestamps beginning at ``start``."""
    return pd.date_range(start=start, periods=n, freq="30min")


def raw_frame(**columns: list) -> pd.DataFrame:
    """Build a raw-shaped frame from equal-length column lists.

    Keys are the three methane column names; values may contain None for slots
    where that column did not report.
    """
    lengths = {len(v) for v in columns.values()}
    if len(lengths) != 1:
        raise ValueError("all columns must be the same length")
    n = lengths.pop()
    frame = pd.DataFrame({"timestamp_start": timestamps("2015-01-01 00:00", n)})
    for name in site.ANALYZER_BY_COLUMN:
        frame[name] = pd.Series(columns.get(name, [None] * n), dtype="float64")
    return frame


def merged_frame(values: list, analyzers: list, start: str = "2015-06-01 00:00") -> pd.DataFrame:
    """Build a merged-shaped frame directly, bypassing the precedence merge.

    Used where the aggregation or quality-control behavior is under test rather
    than the merge itself.
    """
    if len(values) != len(analyzers):
        raise ValueError("values and analyzers must be the same length")
    frame = pd.DataFrame(
        {
            "timestamp_start": timestamps(start, len(values)),
            "fch4": pd.Series(values, dtype="float64"),
            "analyzer": analyzers,
        }
    )
    inverse = {v: k for k, v in site.ANALYZER_BY_COLUMN.items()}
    frame["source_column"] = [inverse.get(a, "none") for a in analyzers]
    frame["n_analyzers_reporting"] = frame["fch4"].notna().astype(int)
    return frame


def merged_day(values: list, analyzers: list, day: str) -> pd.DataFrame:
    """A single day's worth of half-hourly observations."""
    return merged_frame(values, analyzers, start=f"{day} 00:00")


@pytest.fixture
def site_only_day() -> pd.DataFrame:
    """Eight site-aggregated values on one day, mean 9, sd sqrt(24), se sqrt(3)."""
    return merged_day([2, 4, 6, 8, 10, 12, 14, 16], ["site_aggregated"] * 8, "2015-06-01")
