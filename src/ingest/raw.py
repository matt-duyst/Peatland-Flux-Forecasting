"""Reader for the raw half-hourly methane sheet in the AmeriFlux workbook.

Scope is limited to timestamp parsing and replacement of the -9999 missing
sentinel with NaN. Filtering, column merging and aggregation happen elsewhere.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

from . import paths

SHEET = "raws"
SENTINEL = -9999.0
FCH4_COLUMNS = ("FCH4", "FCH4_1_1_1", "FCH4_1_1_2")

#: The workbook stores TIMESTAMP_START in AmeriFlux BASE form: YYYYMMDDHHMM.
_TIMESTAMP_FORMAT = "%Y%m%d%H%M"


def _cache_path() -> Path:
    """Location of the parquet cache holding the parsed half-hourly frame."""
    return paths.interim_dir() / "raw_halfhourly.parquet"


def _read_sheet() -> pd.DataFrame:
    """Stream the raws worksheet into a frame using openpyxl read-only mode."""
    workbook = load_workbook(paths.workbook(), read_only=True, data_only=True)
    try:
        rows = workbook[SHEET].values
        header = [str(c) for c in next(rows)]
        frame = pd.DataFrame(rows, columns=header)
    finally:
        workbook.close()
    return frame


def load_halfhourly(use_cache: bool = True) -> pd.DataFrame:
    """Return the half-hourly record with sentinels replaced by NaN.

    Columns: timestamp_start (datetime64), FCH4, FCH4_1_1_1, FCH4_1_1_2 (float).
    """
    cache = _cache_path()
    if use_cache and cache.exists():
        return pd.read_parquet(cache)

    frame = _read_sheet()
    missing = [c for c in ("TIMESTAMP_START", *FCH4_COLUMNS) if c not in frame.columns]
    if missing:
        raise ValueError(f"workbook sheet {SHEET!r} is missing columns: {missing}")

    out = pd.DataFrame(
        {
            "timestamp_start": pd.to_datetime(
                frame["TIMESTAMP_START"].astype("int64").astype(str),
                format=_TIMESTAMP_FORMAT,
            )
        }
    )
    for column in FCH4_COLUMNS:
        values = pd.to_numeric(frame[column], errors="coerce").astype("float64")
        out[column] = values.mask(np.isclose(values, SENTINEL), np.nan)

    out = out.sort_values("timestamp_start").reset_index(drop=True)

    cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache, index=False)
    return out


def sentinel_report(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-column valid/missing counts and value range after sentinel removal."""
    records = []
    for column in FCH4_COLUMNS:
        series = frame[column]
        records.append(
            {
                "column": column,
                "n_slots": len(series),
                "n_valid": int(series.notna().sum()),
                "n_missing": int(series.isna().sum()),
                "pct_missing": round(100 * series.isna().mean(), 2),
                "min": series.min(),
                "max": series.max(),
                "mean": series.mean(),
            }
        )
    return pd.DataFrame.from_records(records)
