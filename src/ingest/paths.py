"""Lazy resolution of input and output paths, relative to the repository root.

Importing this module performs no filesystem work. Each path is resolved at the
moment it is requested, so the package imports cleanly from any working
directory and in checkouts where the data directories are absent.
"""

from __future__ import annotations

from pathlib import Path

#: A directory is the repository root when it contains every entry of any one
#: marker set. The version-control directory identifies a clone; the content
#: markers identify a source tree exported without it.
_MARKER_SETS: tuple[tuple[str, ...], ...] = ((".git",), ("src", "requirements.txt"))


def repo_root(start: Path | None = None) -> Path:
    """Nearest ancestor directory holding a complete marker set."""
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        for markers in _MARKER_SETS:
            if all((candidate / marker).exists() for marker in markers):
                return candidate
    expected = " or ".join(", ".join(markers) for markers in _MARKER_SETS)
    raise FileNotFoundError(
        f"repository root not found. Expected a directory containing {expected}. "
        f"Searched {here} and every parent directory up to {here.anchor}."
    )


def csv_dir() -> Path:
    """Directory holding the tabular sources carried by the repository."""
    return repo_root() / "CSVs"


def data_dir() -> Path:
    """Directory holding generated data."""
    return repo_root() / "data"


def interim_dir() -> Path:
    """Cached intermediates, regenerable and not tracked."""
    return data_dir() / "interim"


def processed_dir() -> Path:
    """Published outputs of the ingestion pipeline."""
    return data_dir() / "processed"


def workbook() -> Path:
    """Excel workbook carrying the raw half-hourly AmeriFlux BASE sheet."""
    return csv_dir() / "FCH4 PivotTable 2009_2021 and Raw Ameriflux Data.xlsx"


def derived_fch4_csv() -> Path:
    """Sub-daily methane subset derived from the workbook outside this pipeline."""
    return csv_dir() / "FCH4 Data.csv"


def soil_temperature_csv() -> Path:
    """Individual soil temperature readings at 10 cm depth."""
    return csv_dir() / "MEF_soil_temp_weekly.csv"


def precipitation_csv() -> Path:
    """Monthly precipitation means."""
    return csv_dir() / "Monthly Precipitation Average .csv"


def air_temperature_csv() -> Path:
    """Monthly air temperature means."""
    return csv_dir() / "Monthly Temperature Average.csv"


def combined_variables_csv() -> Path:
    """Side-by-side monthly blocks, the source of the carbon dioxide flux series."""
    return csv_dir() / "All Combined Variables Monthly.csv"


def water_table_csv() -> Path:
    """Unscaled monthly water table elevation over the full period."""
    return csv_dir() / "Water Table Elevation (1990 - 2021).csv"


def ensure_dirs() -> None:
    """Create the generated-data directories if they are absent."""
    interim_dir().mkdir(parents=True, exist_ok=True)
    processed_dir().mkdir(parents=True, exist_ok=True)
