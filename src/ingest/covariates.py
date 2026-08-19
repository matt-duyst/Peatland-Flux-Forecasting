"""Monthly covariate series reconstructed from the repository's own CSV files.

Each loader returns a frame indexed by month. Series are derived from the
primary files held in the repository rather than from any pre-joined
intermediate.
"""

from __future__ import annotations

import pandas as pd

from . import paths

ENCODING = "utf-8-sig"

#: Known values for each series, used to verify the reconstructions.
SPOT_CHECKS = {
    "soil_temp_f": {"2009-04": 33.3362, "2009-05": 45.9725, "2009-07": 54.9024},
    "precip_in": {"1990-01": 0.125},
    "fco2": {"2009-01": -0.070729},
    "atm_temp_f": {"1990-01": 18.275},
    "wte_m": {"1990-01": 413.56},
}


def _to_month(series: pd.Series) -> pd.PeriodIndex:
    return pd.PeriodIndex(pd.to_datetime(series), freq="M")


def load_soil_temperature() -> pd.DataFrame:
    """Monthly mean soil temperature at 10 cm depth, in Fahrenheit.

    The source file's own monthly column holds no values, so monthly means are
    computed from the individual depth10cm readings in Celsius and converted.
    """
    raw = pd.read_csv(paths.soil_temperature_csv(), encoding=ENCODING)
    readings = raw[["depth10cm", "Month/Year"]].dropna()
    month = pd.PeriodIndex(
        pd.to_datetime(readings["Month/Year"], format="%m/%Y"), freq="M"
    )
    grouped = readings.groupby(month)["depth10cm"]
    out = pd.DataFrame(
        {
            "soil_temp_f": grouped.mean() * 9 / 5 + 32,
            "soil_temp_n": grouped.size().astype("int64"),
        }
    )
    out.index.name = "month"
    return out.sort_index()


def load_precipitation() -> pd.DataFrame:
    """Monthly cumulative precipitation mean (south/north gauge average)."""
    raw = pd.read_csv(paths.precipitation_csv(), encoding=ENCODING)
    raw = raw.dropna(subset=["Date-Month", "Cumulative Precipitation Mean"])
    out = pd.DataFrame(
        {"precip_in": raw["Cumulative Precipitation Mean"].to_numpy()},
        index=_to_month(raw["Date-Month"]),
    )
    out.index.name = "month"
    return out.sort_index()


def load_fco2() -> pd.DataFrame:
    """Monthly mean carbon dioxide flux.

    The source file stacks three independently dated blocks side by side, so the
    flux column is paired with its own date column rather than the leading one.
    """
    raw = pd.read_csv(paths.combined_variables_csv(), encoding=ENCODING)
    block = raw[["FCO2 Date-Month", "FC02_Avg"]].dropna()
    out = pd.DataFrame(
        {"fco2": block["FC02_Avg"].to_numpy()},
        index=_to_month(block["FCO2 Date-Month"]),
    )
    out.index.name = "month"
    return out.sort_index()


def load_atm_temperature() -> pd.DataFrame:
    """Monthly mean air temperature in Fahrenheit."""
    raw = pd.read_csv(paths.air_temperature_csv(), encoding=ENCODING)
    raw = raw.dropna(subset=["Date", "Cumulative Temperature Mean (F)"])
    out = pd.DataFrame(
        {"atm_temp_f": raw["Cumulative Temperature Mean (F)"].to_numpy()},
        index=_to_month(raw["Date"]),
    )
    out.index.name = "month"
    return out.sort_index()


def load_water_table() -> pd.DataFrame:
    """Monthly mean water table elevation in meters.

    Four water table files exist. This is the unscaled monthly series covering
    the full period; one other is a byte-identical duplicate of it, one is a
    rescaling to the unit interval, and the fourth is annual.
    """
    raw = pd.read_csv(paths.water_table_csv(), encoding=ENCODING)
    raw = raw.dropna(subset=["Date", "Mean(WTE)"])
    out = pd.DataFrame(
        {"wte_m": raw["Mean(WTE)"].to_numpy()}, index=_to_month(raw["Date"])
    )
    out.index.name = "month"
    return out.sort_index()


#: The water table series steps −2.25 m between 2019-12 and 2020-01 and never
#: returns: every month from 1990 to 2019-12 sits between 413.07 and 413.75, and
#: every month afterwards between 411.08 and 411.22, with no intervening values
#: and a series as smooth on each side as the other. That is a change of datum or
#: of gauge, not a drawdown, and reading across it turns an instrument change into
#: two meters of hydrology.
WATER_TABLE_DATUM_BREAK = pd.Period("2020-01", freq="M")


def before_datum_break(frame: pd.DataFrame, column: str = "wte_m") -> pd.DataFrame:
    """The same frame with the water table masked from the datum break onward.

    Masked rather than dropped, so the other covariates in those months are
    unaffected and the caller's index does not change under its feet. The
    reconstruction half never meets these months, since no month after the break
    carries a complete covariate set; the forecasting half runs to 2021 and does.
    """
    out = frame.copy()
    if column in out.columns:
        out.loc[out.index >= WATER_TABLE_DATUM_BREAK, column] = float("nan")
    return out


def load_all() -> pd.DataFrame:
    """Join every covariate on the month index."""
    parts = [
        load_soil_temperature(),
        load_atm_temperature(),
        load_precipitation(),
        load_fco2(),
        load_water_table(),
    ]
    return pd.concat(parts, axis=1).sort_index()


def verify_spot_checks(covariates: pd.DataFrame, tolerance: float = 1e-3) -> pd.DataFrame:
    """Compare each reconstructed series against its known values."""
    records = []
    for column, checks in SPOT_CHECKS.items():
        for month, expected in checks.items():
            period = pd.Period(month, freq="M")
            actual = (
                covariates.at[period, column]
                if period in covariates.index and column in covariates.columns
                else float("nan")
            )
            records.append(
                {
                    "column": column,
                    "month": month,
                    "expected": expected,
                    "actual": actual,
                    "abs_diff": abs(actual - expected),
                    "match": bool(abs(actual - expected) < tolerance),
                }
            )
    return pd.DataFrame.from_records(records)


def _compact_runs(months: pd.PeriodIndex) -> str:
    """Render a month index as contiguous runs, such as 2011-02, 2021-07..2021-12."""
    if len(months) == 0:
        return ""
    ordinals = months.astype("int64")
    breaks = [0, *(i for i in range(1, len(months)) if ordinals[i] != ordinals[i - 1] + 1)]
    runs = []
    for start, end in zip(breaks, [*breaks[1:], len(months)]):
        first, last = months[start], months[end - 1]
        runs.append(str(first) if first == last else f"{first}..{last}")
    return ", ".join(runs)


def coverage(covariates: pd.DataFrame, grid: pd.PeriodIndex) -> pd.DataFrame:
    """Per-covariate coverage against the target monthly grid.

    Gaps are reported as contiguous runs, since a first-to-last span would hide
    isolated interior holes.
    """
    records = []
    for column in covariates.columns:
        if column.endswith("_n"):
            continue
        series = covariates[column].dropna()
        missing = grid.difference(series.index)
        records.append(
            {
                "covariate": column,
                "first": series.index.min(),
                "last": series.index.max(),
                "n_months_total": len(series),
                "n_months_on_grid": len(series.index.intersection(grid)),
                "n_missing_from_grid": len(missing),
                "missing_months": _compact_runs(missing),
            }
        )
    return pd.DataFrame.from_records(records)
