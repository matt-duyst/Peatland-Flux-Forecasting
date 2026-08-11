"""Daily aggregation under a minimum-coverage rule, and monthly aggregation from it.

Deventer et al. (2019) extrapolate half-hourly fluxes to a daily value only for
days holding at least eight valid observations, and test thresholds from eight
to sixteen. Observation counts and dispersion are retained at both the daily and
the monthly level.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import site


def _analyzer_fractions(values: pd.DataFrame, key) -> pd.DataFrame:
    """Share of each group's half-hours contributed by each analyzer.

    The two systems interleave at half-hourly scale and differ measurably in
    scale and offset, so a single day can draw on both. These fractions travel
    with the aggregates to make that visible downstream.
    """
    counts = values.groupby([key, "analyzer"]).size().unstack(fill_value=0)
    fractions = counts.div(counts.sum(axis=1), axis=0)
    fractions.columns = [f"frac_{site.analyzer_slug(c)}" for c in fractions.columns]
    for column in site.FRACTION_COLUMNS:
        if column not in fractions.columns:
            fractions[column] = 0.0
    fractions["n_analyzers"] = (counts > 0).sum(axis=1).astype("int64")
    fractions["is_mixed"] = fractions["n_analyzers"] > 1
    return fractions[[*site.FRACTION_COLUMNS, "n_analyzers", "is_mixed"]].fillna(0.0)


def daily_stats(merged: pd.DataFrame, min_halfhours: int = site.MIN_HALFHOURS_PER_DAY) -> pd.DataFrame:
    """Daily mean, count, dispersion and analyzer mix for days meeting the coverage rule."""
    values = merged.dropna(subset=["fch4"]).copy()
    values["date"] = values["timestamp_start"].dt.normalize()
    grouped = values.groupby("date")["fch4"]

    out = pd.DataFrame(
        {
            "fch4_mean": grouped.mean(),
            "fch4_n": grouped.size().astype("int64"),
            "fch4_sd": grouped.std(ddof=1),
        }
    )
    out["fch4_se"] = out["fch4_sd"] / np.sqrt(out["fch4_n"])
    out = out.join(_analyzer_fractions(values, "date"))
    out.index.name = "date"
    return out[out["fch4_n"] >= min_halfhours].reset_index()


def daily_to_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Monthly mean of daily means, with day counts, dispersion and analyzer mix.

    Analyzer fractions are weighted by each day's half-hour count, so they
    describe the month's underlying observations rather than its days.
    """
    frame = daily.copy()
    frame["month"] = frame["date"].dt.to_period("M")
    grouped = frame.groupby("month")

    out = pd.DataFrame(
        {
            "fch4_mean": grouped["fch4_mean"].mean(),
            "fch4_days": grouped.size().astype("int64"),
            "fch4_sd_across_days": grouped["fch4_mean"].std(ddof=1),
            "fch4_halfhours": grouped["fch4_n"].sum().astype("int64"),
            "n_mixed_days": grouped["is_mixed"].sum().astype("int64"),
        }
    )
    out["fch4_se_across_days"] = out["fch4_sd_across_days"] / np.sqrt(out["fch4_days"])

    for column in site.FRACTION_COLUMNS:
        weighted = frame[column] * frame["fch4_n"]
        out[column] = weighted.groupby(frame["month"]).sum() / out["fch4_halfhours"]

    out["n_analyzers"] = (out[list(site.FRACTION_COLUMNS)] > 0).sum(axis=1).astype("int64")
    out.index.name = "month"
    return out.reset_index()


def daily_stats_column(
    frame: pd.DataFrame,
    column: str,
    timestamp: str = "timestamp_start",
    min_halfhours: int = site.MIN_HALFHOURS_PER_DAY,
) -> pd.DataFrame:
    """Daily mean, count and dispersion for one flux column, under the same rule.

    The coverage rule is the one Deventer et al. (2019) apply and is taken from
    the same constant, so it cannot drift between gases. Carbon dioxide arrives
    as a single column with no replicates, so nothing here tracks analyzers; a
    test checks this reproduces `daily_stats` exactly on the methane column.
    """
    values = frame.dropna(subset=[column]).copy()
    values["date"] = values[timestamp].dt.normalize()
    grouped = values.groupby("date")[column]

    out = pd.DataFrame(
        {
            f"{column}_mean": grouped.mean(),
            f"{column}_n": grouped.size().astype("int64"),
            f"{column}_sd": grouped.std(ddof=1),
        }
    )
    out[f"{column}_se"] = out[f"{column}_sd"] / np.sqrt(out[f"{column}_n"])
    out.index.name = "date"
    return out[out[f"{column}_n"] >= min_halfhours].reset_index()


def daily_to_monthly_column(daily: pd.DataFrame, column: str) -> pd.DataFrame:
    """Monthly mean of daily means for one flux column, with counts and dispersion.

    Dispersion is across days rather than across half-hours, matching the
    methane series, so the standard error on a monthly mean means the same thing
    for both gases.
    """
    frame = daily.copy()
    frame["month"] = frame["date"].dt.to_period("M")
    grouped = frame.groupby("month")

    out = pd.DataFrame(
        {
            f"{column}_mean": grouped[f"{column}_mean"].mean(),
            f"{column}_days": grouped.size().astype("int64"),
            f"{column}_sd_across_days": grouped[f"{column}_mean"].std(ddof=1),
            f"{column}_halfhours": grouped[f"{column}_n"].sum().astype("int64"),
        }
    )
    out[f"{column}_se_across_days"] = (
        out[f"{column}_sd_across_days"] / np.sqrt(out[f"{column}_days"])
    )
    out.index.name = "month"
    return out.reset_index()


def monthly_diurnally_balanced(
    frame: pd.DataFrame, column: str, timestamp: str = "timestamp_start"
) -> pd.DataFrame:
    """Monthly mean with every half-hour of the day weighted equally.

    A mean over retained half-hours inherits whatever diurnal skew the retained
    sample carries. That is immaterial for methane at this site, whose diurnal
    cycle explains under 2% of half-hourly variance, and material for carbon
    dioxide, whose cycle explains 29% while daylight supplies 62% of retained
    observations. Averaging within half-hour of day first, then across those
    cells, removes the skew at the cost of discarding the uneven weighting.
    """
    values = frame.dropna(subset=[column]).copy()
    stamps = values[timestamp]
    values["month"] = pd.PeriodIndex(stamps, freq="M")
    values["halfhour"] = stamps.dt.hour * 2 + stamps.dt.minute // 30

    cell = values.groupby(["month", "halfhour"])[column].mean()
    grouped = cell.groupby(level="month")
    out = pd.DataFrame(
        {
            f"{column}_mean": grouped.mean(),
            f"{column}_cells": grouped.size().astype("int64"),
            f"{column}_sd_across_cells": grouped.std(ddof=1),
        }
    )
    out[f"{column}_halfhours"] = values.groupby("month").size().astype("int64")
    out[f"{column}_se_across_cells"] = (
        out[f"{column}_sd_across_cells"] / np.sqrt(out[f"{column}_cells"])
    )
    out.index.name = "month"
    return out.reset_index()


def threshold_comparison(
    merged: pd.DataFrame, thresholds: tuple[int, ...] = site.DAILY_THRESHOLDS
) -> pd.DataFrame:
    """Monthly series under each daily coverage threshold, joined for comparison."""
    parts = []
    for threshold in thresholds:
        monthly = daily_to_monthly(daily_stats(merged, threshold)).set_index("month")
        monthly = monthly[["fch4_mean", "fch4_days"]].add_suffix(f"_t{threshold}")
        parts.append(monthly)
    return pd.concat(parts, axis=1).sort_index().reset_index()


def threshold_summary(comparison: pd.DataFrame, thresholds: tuple[int, ...]) -> pd.DataFrame:
    """Movement in the monthly series as the coverage threshold tightens."""
    base = thresholds[0]
    records = []
    for threshold in thresholds:
        mean_column = f"fch4_mean_t{threshold}"
        day_column = f"fch4_days_t{threshold}"
        difference = comparison[mean_column] - comparison[f"fch4_mean_t{base}"]
        records.append(
            {
                "threshold": threshold,
                "n_months": int(comparison[mean_column].notna().sum()),
                "total_days": int(comparison[day_column].sum()),
                "mean_flux": comparison[mean_column].mean(),
                f"max_abs_shift_vs_t{base}": float(difference.abs().max()),
                f"median_abs_shift_vs_t{base}": float(difference.abs().median()),
                f"months_lost_vs_t{base}": int(
                    comparison[f"fch4_mean_t{base}"].notna().sum()
                    - comparison[mean_column].notna().sum()
                ),
            }
        )
    return pd.DataFrame.from_records(records)


def diurnal_vs_seasonal(merged: pd.DataFrame, column: str = "fch4") -> dict[str, object]:
    """Compare the strength of the diurnal cycle against the seasonal cycle.

    Reports amplitude and explained variance for the half-hour-of-day grouping
    against the month-of-year grouping. A weak diurnal signal relative to the
    seasonal one is what makes aggregation to monthly defensible, which is true
    of methane here and emphatically not of carbon dioxide, so the column is a
    parameter and both gases are reported.
    """
    values = merged.dropna(subset=[column]).copy()
    values["halfhour"] = (
        values["timestamp_start"].dt.hour * 2 + values["timestamp_start"].dt.minute // 30
    )
    values["month_of_year"] = values["timestamp_start"].dt.month

    total_variance = values[column].var(ddof=0)
    result: dict[str, object] = {"n": len(values), "total_variance": float(total_variance)}

    for label, key in (("diurnal", "halfhour"), ("seasonal", "month_of_year")):
        group_means = values.groupby(key)[column].mean()
        group_sizes = values.groupby(key)[column].size()
        between = float(
            np.average((group_means - values[column].mean()) ** 2, weights=group_sizes)
        )
        result[f"{label}_amplitude"] = float(group_means.max() - group_means.min())
        result[f"{label}_eta_squared"] = between / float(total_variance)

    result["seasonal_to_diurnal_amplitude_ratio"] = (
        result["seasonal_amplitude"] / result["diurnal_amplitude"]
    )
    return result


def diurnal_cycle_by_season(merged: pd.DataFrame) -> pd.DataFrame:
    """Hourly means within the growing season and outside it."""
    values = merged.dropna(subset=["fch4"]).copy()
    values["hour"] = values["timestamp_start"].dt.hour
    values["season"] = np.where(
        values["timestamp_start"].dt.month.isin([6, 7, 8]), "JJA", "other"
    )
    table = values.pivot_table(index="hour", columns="season", values="fch4", aggfunc="mean")
    return table.reset_index()


def daylight_share(merged: pd.DataFrame, column: str, low: int = 6, high: int = 18) -> float:
    """Share of retained observations falling in daylight hours.

    Even sampling would give a half. Carbon dioxide is taken up in daylight, so
    over-representation here is what turns a day-weighted monthly mean into a
    seasonal artifact rather than a constant offset.
    """
    values = merged.dropna(subset=[column])
    hour = values["timestamp_start"].dt.hour
    return float(((hour >= low) & (hour < high)).mean())
