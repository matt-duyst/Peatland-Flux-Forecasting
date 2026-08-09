"""Negative-flux diagnostics against the detection limit."""

from __future__ import annotations

import math

from conftest import merged_frame, raw_frame

from ingest import qc, site

TGA, LI = site.TGA_COLUMN, site.LI7700_COLUMN


def test_series_without_negatives_reports_zero_and_no_spurious_percentages():
    frame = merged_frame([1.0, 2.0, 3.0, 4.0], ["site_aggregated"] * 4)
    summary = qc.negative_summary(frame)

    assert summary["n_negative"] == 0
    assert summary["pct_negative"] == 0.0
    assert summary["pct_of_negatives_within_limit"] == 0.0
    assert summary["pct_of_negatives_exceeding_limit"] == 0.0
    assert math.isnan(summary["most_negative"])


def test_negatives_split_at_the_detection_limit():
    """With a limit of 3, only -1 lies within it; -4 and -10 exceed it."""
    frame = merged_frame([-1.0, -4.0, -10.0, 5.0], ["site_aggregated"] * 4)
    summary = qc.negative_summary(frame, limit=3.0)

    assert summary["n_values"] == 4
    assert summary["n_negative"] == 3
    assert summary["n_negative_within_detection_limit"] == 1
    assert summary["n_negative_exceeding_detection_limit"] == 2
    assert summary["most_negative"] == -10.0


def test_value_exactly_at_the_limit_counts_as_exceeding():
    frame = merged_frame([-3.0], ["site_aggregated"])
    summary = qc.negative_summary(frame, limit=3.0)

    assert summary["n_negative_exceeding_detection_limit"] == 1
    assert summary["n_negative_within_detection_limit"] == 0


def test_detection_limit_sensitivity_spans_the_published_range():
    frame = merged_frame([-1.0, -4.0, -10.0], ["site_aggregated"] * 3)
    table = qc.detection_limit_sensitivity(frame)

    assert list(table["detection_limit"]) == [
        site.DETECTION_LIMIT - site.DETECTION_LIMIT_UNCERTAINTY,
        site.DETECTION_LIMIT,
        site.DETECTION_LIMIT + site.DETECTION_LIMIT_UNCERTAINTY,
    ]
    assert table["n_negative"].eq(3).all()
    # Limits 1, 3 and 5 against -1, -4 and -10: three, two, then one exceed.
    assert list(table["n_negative_exceeding_detection_limit"]) == [3, 2, 1]


def test_concurrent_negatives_counts_only_shared_timestamps():
    """One timestamp is negative in both analyzers; two are negative in one only."""
    frame = raw_frame(
        **{
            TGA: [-5.0, -5.0, 5.0, 5.0],
            LI: [-5.0, 5.0, -5.0, 5.0],
        }
    )
    summary = qc.concurrent_negatives(frame, limit=3.0)

    assert summary["n_paired_timestamps"] == 4
    assert summary["n_negative_tga"] == 2
    assert summary["n_negative_li7700"] == 2
    assert summary["n_negative_in_either"] == 3
    assert summary["n_negative_in_both"] == 1
    assert summary["pct_of_either_that_are_concurrent"] == 33.3


def test_concurrent_negatives_ignores_unpaired_timestamps():
    frame = raw_frame(**{TGA: [-5.0, -5.0], LI: [-5.0, None]})
    summary = qc.concurrent_negatives(frame, limit=3.0)

    assert summary["n_paired_timestamps"] == 1
    assert summary["n_negative_in_both"] == 1


def test_negative_share_by_year_reports_active_analyzers():
    frame = merged_frame([-1.0, 2.0, 3.0, 4.0], ["site_aggregated", "site_aggregated", "TGA-100A", "TGA-100A"])
    table = qc.negative_share_by_year(frame)

    assert len(table) == 1
    assert table.loc[0, "n"] == 4
    assert table.loc[0, "n_negative"] == 1
    assert table.loc[0, "pct_negative"] == 25.0
    assert table.loc[0, "analyzer"] == "TGA-100A/site_aggregated"
