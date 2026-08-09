"""Diagnostics on the three raw methane columns and on the derived Excel subset.

All functions here describe the series; none alters it. Combining the three
columns into a single target is the responsibility of merge.py.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd

from . import paths
from .raw import FCH4_COLUMNS


def column_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """First/last valid timestamp and valid count for each methane column."""
    records = []
    for column in FCH4_COLUMNS:
        stamps = frame.loc[frame[column].notna(), "timestamp_start"]
        records.append(
            {
                "column": column,
                "n_valid": len(stamps),
                "first_valid": stamps.min(),
                "last_valid": stamps.max(),
            }
        )
    return pd.DataFrame.from_records(records)


def column_overlap(frame: pd.DataFrame) -> pd.DataFrame:
    """Timestamp-level co-occurrence and agreement for each column pair."""
    records = []
    for i, left in enumerate(FCH4_COLUMNS):
        for right in FCH4_COLUMNS[i + 1 :]:
            both = frame[left].notna() & frame[right].notna()
            n_both = int(both.sum())
            record = {"left": left, "right": right, "n_both_present": n_both}
            if n_both:
                pair = frame.loc[both]
                record["correlation"] = pair[left].corr(pair[right])
                record["n_identical"] = int((pair[left] == pair[right]).sum())
                record["mean_difference"] = (pair[left] - pair[right]).mean()
            records.append(record)
    return pd.DataFrame.from_records(records)


def yearly_valid_counts(frame: pd.DataFrame) -> pd.DataFrame:
    """Valid observations per calendar year per column — shows the handover."""
    by_year = frame.assign(year=frame["timestamp_start"].dt.year).groupby("year")
    return by_year[list(FCH4_COLUMNS)].apply(lambda g: g.notna().sum())


def to_long(frame: pd.DataFrame) -> pd.DataFrame:
    """Melt the three methane columns to one row per (timestamp, column, value)."""
    long = frame.melt(
        id_vars="timestamp_start",
        value_vars=list(FCH4_COLUMNS),
        var_name="column",
        value_name="value",
    ).dropna(subset=["value"])
    long["date"] = long["timestamp_start"].dt.normalize()
    return long.sort_values(["timestamp_start", "column"]).reset_index(drop=True)


def label_derived_subset(long: pd.DataFrame, decimals: int = 3) -> pd.DataFrame:
    """Mark which raw half-hourly rows appear in the derived ``FCH4 Data.csv``.

    That file carries a date but no time, so rows are matched as a per-day
    value multiset. Values are near-unique at three decimal places, which makes
    the greedy assignment effectively exact.
    """
    derived = pd.read_csv(paths.derived_fch4_csv())
    derived["date"] = pd.to_datetime(derived["Date"])
    derived["rounded"] = derived["FCH4 Value"].round(decimals)

    long = long.copy()
    long["rounded"] = long["value"].round(decimals)
    long["in_derived"] = False

    wanted = {date: Counter(g["rounded"]) for date, g in derived.groupby("date")}
    keep_index = []
    for date, group in long.groupby("date"):
        pool = wanted.get(date)
        if not pool:
            continue
        pool = Counter(pool)
        for index, value in zip(group.index, group["rounded"]):
            if pool[value] > 0:
                pool[value] -= 1
                keep_index.append(index)
    long.loc[keep_index, "in_derived"] = True

    matched, expected = len(keep_index), len(derived)
    if matched != expected:
        raise ValueError(f"matched {matched} rows, expected {expected}")
    return long


def derived_provenance(labelled: pd.DataFrame) -> pd.DataFrame:
    """Source column of each retained value in the derived file, by year."""
    kept = labelled[labelled["in_derived"]]
    counts = (
        kept.assign(year=kept["timestamp_start"].dt.year)
        .groupby(["year", "column"])
        .size()
        .rename("n")
        .reset_index()
    )
    return counts.pivot(index="year", columns="column", values="n").fillna(0).astype(int)


def derived_rule_tests(labelled: pd.DataFrame) -> dict[str, object]:
    """Test whether a threshold or dispersion screen explains the derived subset.

    Reports the share of discarded values falling inside the retained range,
    which no threshold rule can produce, together with the accuracy of
    per-month k-sigma screens against the observed retain and discard labels.
    """
    kept = labelled[labelled["in_derived"]]
    dropped = labelled[~labelled["in_derived"]]
    low, high = kept["value"].min(), kept["value"].max()
    inside = dropped["value"].between(low, high)

    sigma_accuracy = {}
    by_month = labelled.groupby(labelled["timestamp_start"].dt.to_period("M"))
    for k in (1.0, 1.5, 2.0, 2.5, 3.0):
        correct = 0
        for _, group in by_month:
            mean, sd = group["value"].mean(), group["value"].std()
            predicted = group["value"].between(mean - k * sd, mean + k * sd)
            correct += int((predicted == group["in_derived"]).sum())
        sigma_accuracy[k] = round(100 * correct / len(labelled), 1)

    return {
        "kept_range": (low, high),
        "n_kept": len(kept),
        "n_dropped": len(dropped),
        "n_dropped_inside_kept_range": int(inside.sum()),
        "pct_dropped_inside_kept_range": round(100 * inside.mean(), 1),
        "sigma_screen_accuracy_pct": sigma_accuracy,
        "base_rate_pct": round(100 * labelled["in_derived"].mean(), 1),
    }
