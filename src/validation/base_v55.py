"""The 2025 AmeriFlux BASE product, read alongside the 2022 export for comparison.

The pipeline in `src.ingest` reads a 2022 workbook export carrying a timestamp
and three methane columns. This module reads the full BASE Version 5-5 product
for the same site, which carries 32 variables over a longer record, and compares
the two where they overlap. Nothing here is wired into the pipeline: the
ingestion path does not import this module, and no study result depends on it.

Both products use the AmeriFlux missing-value sentinel of -9999 and the
TIMESTAMP_START format YYYYMMDDHHMM, so the only structural difference is the
column set and the file format. Provenance, license and the comparison result
are recorded in `notes/base_v55.md`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ingest import paths, raw

#: Directory the downloaded archive was extracted to, beside the archive itself.
PRODUCT_DIRECTORY = "AMF_US-MBP_BASE-BADM_5-5"
BASE_FILENAME = "AMF_US-MBP_BASE_HH_5-5.csv"
BADM_FILENAME = "AMF_US-MBP_BIF_20260527.xlsx"

#: The product carries two comment lines above its header row.
HEADER_ROW = 2

BASE_VERSION = "5-5"
BADM_VERSION = "20260527"
PRODUCT_DOI = "10.17190/AMF/1767835"
PRODUCT_LICENCE = "CC-BY-4.0"
PRODUCT_CITATION = (
    "Tyler Roman, Andrew C. Hill, Randy Kolka, Timothy Griffis, Julian Deventer "
    "(2025), AmeriFlux BASE US-MBP Marcell Bog Lake Peatland, Ver. 5-5, "
    "AmeriFlux AMP, (Dataset). https://doi.org/10.17190/AMF/1767835"
)

#: Wind sectors discarded by Deventer et al. (2019) for tower flow distortion and
#: upland forest in the flux footprint. Degrees clockwise from north.
EXCLUDED_SECTOR = (30.0, 200.0)


def product_dir() -> Path:
    """Directory holding the extracted product."""
    return paths.csv_dir() / PRODUCT_DIRECTORY


def load_base(path: Path | None = None) -> pd.DataFrame:
    """Half-hourly product indexed by timestamp, with sentinels replaced by NaN."""
    source = path or (product_dir() / BASE_FILENAME)
    frame = pd.read_csv(source, skiprows=HEADER_ROW, na_values=[raw.SENTINEL])
    stamps = pd.to_datetime(
        frame["TIMESTAMP_START"].astype("int64").astype(str), format="%Y%m%d%H%M"
    )
    frame = frame.drop(columns=["TIMESTAMP_START", "TIMESTAMP_END"], errors="ignore")
    frame.index = pd.DatetimeIndex(stamps, name="timestamp_start")
    return frame.sort_index()


def load_badm(path: Path | None = None) -> pd.DataFrame:
    """Site metadata records, one row per variable within a group."""
    return pd.read_excel(path or (product_dir() / BADM_FILENAME))


def badm_value(badm: pd.DataFrame, variable: str) -> str | None:
    """First value recorded for a metadata variable, or None where it is absent."""
    matches = badm.loc[badm["VARIABLE"] == variable, "DATAVALUE"]
    return None if matches.empty else str(matches.iloc[0])


def compare_columns(
    export: pd.DataFrame, product: pd.DataFrame, columns: tuple[str, ...]
) -> pd.DataFrame:
    """Agreement between the two products over the timestamps they share.

    The export is indexed by timestamp rather than carrying it as a column, so
    callers pass it already indexed. A column present in one product and absent
    from the other is reported rather than raising, since the products carry
    different variable sets by design.
    """
    shared = export.index.intersection(product.index)
    records = []
    for column in columns:
        if column not in export or column not in product:
            records.append({"column": column, "in_both_products": False})
            continue
        left, right = export.loc[shared, column], product.loc[shared, column]
        overlap = left.notna() & right.notna()
        difference = (right - left)[overlap]
        records.append(
            {
                "column": column,
                "in_both_products": True,
                "shared_timestamps": len(shared),
                "valid_export": int(left.notna().sum()),
                "valid_product": int(right.notna().sum()),
                "valid_both": int(overlap.sum()),
                "identical": int((difference == 0).sum()),
                "differing": int((difference != 0).sum()),
                "only_export": int((left.notna() & right.isna()).sum()),
                "only_product": int((left.isna() & right.notna()).sum()),
                "max_abs_difference": float(difference.abs().max()) if overlap.any() else np.nan,
            }
        )
    return pd.DataFrame.from_records(records)


def difference_by_year(
    export: pd.DataFrame, product: pd.DataFrame, column: str
) -> pd.DataFrame:
    """Per-year agreement for one column, which localises any reprocessing."""
    shared = export.index.intersection(product.index)
    left, right = export.loc[shared, column], product.loc[shared, column]
    frame = pd.DataFrame({"left": left, "right": right})
    frame = frame[frame["left"].notna() & frame["right"].notna()]
    grouped = frame.groupby(frame.index.year)
    out = pd.DataFrame(
        {
            "n": grouped.size(),
            "identical": grouped.apply(
                lambda g: int((g["right"] == g["left"]).sum()), include_groups=False
            ),
        }
    )
    out["differing"] = out["n"] - out["identical"]
    out.index.name = "year"
    return out


def sector_membership(product: pd.DataFrame, sector: tuple[float, float] = EXCLUDED_SECTOR) -> pd.Series:
    """Whether each half-hour's wind direction falls in the excluded sector."""
    low, high = sector
    return product["WD"].between(low, high, inclusive="left")


def sector_cost(
    product: pd.DataFrame,
    flux_columns: tuple[str, ...],
    sector: tuple[float, float] = EXCLUDED_SECTOR,
) -> pd.DataFrame:
    """Share of each flux column, and of all half-hours, inside the excluded sector.

    A share of zero for every flux column against a substantial share of all
    half-hours means the exclusion was applied before publication, so the sector
    is a property of the delivered record rather than a filter available here.
    """
    inside = sector_membership(product, sector)
    recorded = product["WD"].notna()
    records = [
        {
            "series": "all half-hours",
            "n_with_wind_direction": int(recorded.sum()),
            "pct_inside_sector": round(100 * float(inside[recorded].mean()), 2),
        }
    ]
    for column in flux_columns:
        usable = product[column].notna() & recorded
        records.append(
            {
                "series": column,
                "n_with_wind_direction": int(usable.sum()),
                "pct_inside_sector": round(100 * float(inside[usable].mean()), 2)
                if usable.any()
                else np.nan,
            }
        )
    return pd.DataFrame.from_records(records)


def coverage_against_sector(product: pd.DataFrame, methane: pd.Series) -> pd.DataFrame:
    """Record length at each stage, from all half-hours to retained methane.

    Coverage quoted against the whole record understates retention, because the
    footprint rule removes a large share before any instrument or quality
    consideration applies.
    """
    inside = sector_membership(product)
    recorded = product["WD"].notna()
    total = len(product)
    available = int((recorded & ~inside).sum())
    retained = int(methane.notna().sum())
    stages = [
        ("all half-hours", total),
        ("wind direction recorded", int(recorded.sum())),
        ("removed by the excluded sector", int(inside.sum())),
        ("outside sector, wind direction recorded", available),
        ("methane retained", retained),
    ]
    frame = pd.DataFrame(stages, columns=["stage", "n_half_hours"])
    frame["pct_of_record"] = (100 * frame["n_half_hours"] / total).round(1)
    frame["pct_of_what_sector_leaves"] = np.where(
        frame["stage"] == "methane retained", round(100 * retained / available, 1), np.nan
    )
    return frame


def load_methane(path: Path | None = None) -> pd.DataFrame:
    """The three methane columns in the shape `ingest.raw.load_halfhourly` returns.

    The ingestion layer reads methane from here rather than from the 2022
    workbook export, because this product carries the same values and three more
    years of them. Every one of the 66,946 half-hours the two share is identical
    and neither holds a value the other lacks, so the change is additive rather
    than a reprocessing; `compare_columns` is what establishes that and
    `notes/base_v55.md` records it.

    The Excel path in `ingest.raw` is not dead. `scripts/01_investigate_raw.py`
    characterises the derived `CSVs/FCH4 Data.csv` subset against the workbook it
    was cut from, which is a question about that file rather than about the
    flux, and this product cannot answer it.
    """
    product = load_base(path)
    missing = [column for column in raw.FCH4_COLUMNS if column not in product.columns]
    if missing:
        raise ValueError(f"BASE product {BASE_FILENAME!r} is missing columns: {missing}")
    return product[list(raw.FCH4_COLUMNS)].reset_index()


def merged_methane(product: pd.DataFrame, precedence: tuple[str, ...]) -> pd.Series:
    """One methane series under the precedence the ingestion layer applies."""
    series = product[precedence[0]]
    for column in precedence[1:]:
        series = series.combine_first(product[column])
    return series
