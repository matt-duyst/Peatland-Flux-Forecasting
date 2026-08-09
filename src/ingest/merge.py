"""Merge of the three raw methane columns into one series with explicit provenance.

Deventer et al. (2019) permit combining observations from different measurement
systems provided the combined series is treated as carrying the flux uncertainty
of a single system. Values are selected by precedence and never averaged, so
every retained value traces to exactly one analyzer.
"""

from __future__ import annotations

import pandas as pd

from . import site

#: Highest precedence first. Selection rationale is recorded in notes/ingestion.md.
PRECEDENCE = (site.BASE_COLUMN, site.TGA_COLUMN, site.LI7700_COLUMN)


def pairwise_overlap(frame: pd.DataFrame, precedence: tuple[str, ...] = PRECEDENCE) -> pd.DataFrame:
    """Timestamps on which each pair of precedence columns both report."""
    records = []
    for i, left in enumerate(precedence):
        for right in precedence[i + 1 :]:
            both = frame[left].notna() & frame[right].notna()
            records.append({"left": left, "right": right, "n_overlap": int(both.sum())})
    # A single-column precedence yields no pairs; name the columns explicitly so
    # the empty frame is still indexable by callers.
    return pd.DataFrame.from_records(records, columns=["left", "right", "n_overlap"])


def assert_disjoint(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    """Raise unless the named columns never report on the same timestamp.

    Disjointness is a property of a particular dataset rather than a constraint
    on the merge, which exists precisely to arbitrate between columns that do
    overlap. Callers assert it for the columns they believe independent.
    """
    overlap = pairwise_overlap(frame, columns)
    conflicting = overlap[overlap["n_overlap"] > 0]
    if not conflicting.empty:
        pairs = ", ".join(
            f"{row.left}/{row.right} on {row.n_overlap} timestamps"
            for row in conflicting.itertuples()
        )
        raise ValueError(f"columns expected to be disjoint overlap: {pairs}")


def _validate(frame: pd.DataFrame, precedence: tuple[str, ...]) -> None:
    """Check that the merge has a usable precedence and the columns to apply it to."""
    if not precedence:
        raise ValueError("precedence must name at least one column")
    missing = [c for c in ("timestamp_start", *precedence) if c not in frame.columns]
    if missing:
        raise KeyError(f"frame is missing required columns: {missing}")


def merge_halfhourly(frame: pd.DataFrame, precedence: tuple[str, ...] = PRECEDENCE) -> pd.DataFrame:
    """Collapse the named columns to one value with a provenance label.

    Returns every half-hourly slot. Slots where no analyzer reported carry a
    null flux and a source of "none". Provenance counts describe only the
    columns named in ``precedence``.
    """
    _validate(frame, precedence)

    out = frame[["timestamp_start"]].copy()
    out["fch4"] = pd.NA
    out["source_column"] = "none"

    for column in precedence:
        fill = out["fch4"].isna() & frame[column].notna()
        out.loc[fill, "fch4"] = frame.loc[fill, column]
        out.loc[fill, "source_column"] = column

    out["fch4"] = pd.to_numeric(out["fch4"], errors="coerce")
    out["analyzer"] = out["source_column"].map(
        lambda c: site.ANALYZER_BY_COLUMN.get(c, "none")
    )
    out["n_analyzers_reporting"] = frame[list(precedence)].notna().sum(axis=1)
    return out


def provenance_summary(merged: pd.DataFrame) -> pd.DataFrame:
    """Retained value counts by source column and analyzer."""
    reported = merged[merged["fch4"].notna()]
    summary = (
        reported.groupby(["source_column", "analyzer"]).size().rename("n").reset_index()
    )
    summary["pct"] = (100 * summary["n"] / len(reported)).round(2)
    return summary.sort_values("n", ascending=False).reset_index(drop=True)


def provenance_by_year(merged: pd.DataFrame) -> pd.DataFrame:
    """Provenance breakdown by calendar year."""
    reported = merged[merged["fch4"].notna()].copy()
    reported["year"] = reported["timestamp_start"].dt.year
    table = (
        reported.groupby(["year", "analyzer"]).size().rename("n").reset_index()
        .pivot(index="year", columns="analyzer", values="n")
        .fillna(0)
        .astype(int)
    )
    table["total"] = table.sum(axis=1)
    return table


def contention_summary(merged: pd.DataFrame) -> dict[str, int]:
    """Count of slots where precedence had to choose between reporting columns.

    Resolution counts are keyed by whichever source columns actually appear, so
    the summary follows the precedence the merge was given.
    """
    contested = merged["n_analyzers_reporting"] > 1
    summary = {
        "slots_with_any_value": int(merged["fch4"].notna().sum()),
        "contested_slots": int(contested.sum()),
        "discarded_alternates": int(
            (merged.loc[contested, "n_analyzers_reporting"] - 1).sum()
        ),
    }
    for column in sorted(set(merged.loc[contested, "source_column"])):
        summary[f"resolved_to_{column}"] = int(
            (contested & (merged["source_column"] == column)).sum()
        )
    return summary


def analyzer_runs(merged: pd.DataFrame) -> pd.DataFrame:
    """Consecutive runs of a single analyzer within the merged series."""
    reported = merged[merged["fch4"].notna()].copy()
    changed = reported["analyzer"].ne(reported["analyzer"].shift())
    runs = reported.assign(run=changed.cumsum()).groupby("run")
    return pd.DataFrame(
        {
            "analyzer": runs["analyzer"].first(),
            "first": runs["timestamp_start"].min(),
            "last": runs["timestamp_start"].max(),
            "n": runs.size(),
        }
    ).reset_index(drop=True)


def switch_summary(merged: pd.DataFrame) -> pd.DataFrame:
    """Frequency and length of analyzer runs, by year.

    Between 2015 and 2018 the two systems interleave at half-hourly scale rather
    than occupying distinct periods, and each switch carries the scale offset
    between them, so the number of switches matters more than their locations.
    """
    runs = analyzer_runs(merged)
    runs["year"] = runs["first"].dt.year

    # Every run after the first is entered by a switch; attributing that switch
    # to the year the new run starts in makes the per-year counts sum to the
    # total for the series, including transitions across a year boundary.
    switches = runs.iloc[1:].groupby("year").size().rename("n_switches")

    grouped = runs.groupby("year")
    out = pd.DataFrame(
        {
            "n_runs": grouped.size(),
            "median_run_halfhours": grouped["n"].median(),
            "max_run_halfhours": grouped["n"].max(),
            "analyzers": grouped["analyzer"].agg(lambda s: "/".join(sorted(set(s)))),
        }
    )
    out.insert(1, "n_switches", switches.reindex(out.index, fill_value=0).astype("int64"))
    return out.reset_index()


def total_switches(merged: pd.DataFrame) -> int:
    """Number of analyzer transitions across the whole series."""
    return max(len(analyzer_runs(merged)) - 1, 0)


def structural_boundaries(merged: pd.DataFrame, min_run: int = 200) -> pd.DataFrame:
    """Long single-analyzer runs, which mark the boundaries between deployments."""
    runs = analyzer_runs(merged)
    return runs[runs["n"] >= min_run].reset_index(drop=True)
