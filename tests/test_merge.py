"""Precedence merge: selection, provenance counts, validation and run structure."""

from __future__ import annotations

import pandas as pd
import pytest
from conftest import raw_frame

from ingest import merge, site

BASE, TGA, LI = site.BASE_COLUMN, site.TGA_COLUMN, site.LI7700_COLUMN


def test_precedence_selects_higher_column_and_never_averages():
    """Where two analysers report, the merged value equals one of them exactly."""
    frame = raw_frame(**{TGA: [10.0, None], LI: [20.0, 20.0]})
    merged = merge.merge_halfhourly(frame, precedence=(TGA, LI))

    assert merged.loc[0, "fch4"] == 10.0
    assert merged.loc[0, "fch4"] != 15.0
    assert merged.loc[0, "source_column"] == TGA
    assert merged.loc[1, "fch4"] == 20.0
    assert merged.loc[1, "source_column"] == LI


def test_every_merged_value_comes_from_some_input_column():
    """No merged value is a blend: each appears in one of the source columns."""
    frame = raw_frame(**{TGA: [10.0, None, 3.5], LI: [20.0, 7.25, None]})
    merged = merge.merge_halfhourly(frame, precedence=(TGA, LI))

    for row in merged.dropna(subset=["fch4"]).itertuples():
        candidates = {frame.loc[row.Index, TGA], frame.loc[row.Index, LI]}
        assert row.fch4 in candidates


def test_slots_without_any_report_are_null_and_labelled_none():
    frame = raw_frame(**{TGA: [1.0, None], LI: [None, None]})
    merged = merge.merge_halfhourly(frame, precedence=(TGA, LI))

    assert pd.isna(merged.loc[1, "fch4"])
    assert merged.loc[1, "source_column"] == "none"
    assert merged.loc[1, "analyzer"] == "none"


def test_output_preserves_every_timestamp_exactly_once():
    frame = raw_frame(**{TGA: [1.0, 2.0, None, 4.0]})
    merged = merge.merge_halfhourly(frame, precedence=(TGA,))

    assert len(merged) == len(frame)
    assert not merged["timestamp_start"].duplicated().any()
    assert merged["timestamp_start"].equals(frame["timestamp_start"])


def test_single_column_precedence_reports_no_contention():
    """Provenance counts follow the precedence argument, not the module constant."""
    frame = raw_frame(**{TGA: [1.0, 2.0], LI: [9.0, 9.0]})
    merged = merge.merge_halfhourly(frame, precedence=(TGA,))

    assert merged["n_analyzers_reporting"].max() == 1
    summary = merge.contention_summary(merged)
    assert summary["contested_slots"] == 0
    assert summary["discarded_alternates"] == 0
    assert summary["slots_with_any_value"] == 2


def test_two_column_precedence_counts_contention():
    frame = raw_frame(**{TGA: [1.0, 2.0], LI: [9.0, None]})
    merged = merge.merge_halfhourly(frame, precedence=(TGA, LI))

    summary = merge.contention_summary(merged)
    assert summary["contested_slots"] == 1
    assert summary["discarded_alternates"] == 1
    assert summary[f"resolved_to_{TGA}"] == 1


def test_pairwise_overlap_is_indexable_when_precedence_has_one_column():
    frame = raw_frame(**{TGA: [1.0, 2.0]})
    overlap = merge.pairwise_overlap(frame, precedence=(TGA,))

    assert list(overlap.columns) == ["left", "right", "n_overlap"]
    assert overlap.empty


def test_missing_column_raises():
    frame = raw_frame(**{TGA: [1.0]}).drop(columns=[LI])
    with pytest.raises(KeyError, match="missing required columns"):
        merge.merge_halfhourly(frame, precedence=(TGA, LI))


def test_empty_precedence_raises():
    with pytest.raises(ValueError, match="at least one column"):
        merge.merge_halfhourly(raw_frame(**{TGA: [1.0]}), precedence=())


def test_assert_disjoint_raises_on_overlapping_columns():
    """Callers assert independence for the columns they believe never coincide."""
    frame = raw_frame(**{TGA: [1.0], LI: [2.0]})
    with pytest.raises(ValueError, match="expected to be disjoint overlap"):
        merge.assert_disjoint(frame, (TGA, LI))


def test_assert_disjoint_passes_when_columns_never_coincide():
    frame = raw_frame(**{BASE: [None, 5.0], TGA: [1.0, None]})
    merge.assert_disjoint(frame, (BASE, TGA))


def test_overlap_is_resolved_by_precedence_not_rejected():
    """Overlap is what precedence exists to arbitrate, so the merge accepts it."""
    frame = raw_frame(**{BASE: [None, 5.0], TGA: [1.0, None], LI: [2.0, None]})
    merged = merge.merge_halfhourly(frame)

    assert merged.loc[0, "fch4"] == 1.0
    assert merged.loc[1, "fch4"] == 5.0


def test_switch_spanning_a_year_boundary_is_counted():
    """A transition on New Year belongs to the year the new run begins."""
    frame = pd.DataFrame(
        {
            "timestamp_start": pd.to_datetime(
                ["2015-12-31 23:00", "2015-12-31 23:30", "2016-01-01 00:00", "2016-01-01 00:30"]
            ),
            BASE: [1.0, 2.0, None, None],
            TGA: [None, None, 3.0, 4.0],
            LI: [None] * 4,
        }
    )
    merged = merge.merge_halfhourly(frame)
    summary = merge.switch_summary(merged)

    assert merge.total_switches(merged) == 1
    assert summary["n_switches"].sum() == 1
    assert summary.set_index("year").loc[2016, "n_switches"] == 1
    assert summary.set_index("year").loc[2015, "n_switches"] == 0


def test_switch_counts_sum_to_series_total():
    frame = raw_frame(**{TGA: [1.0, None, 3.0, None], LI: [None, 2.0, None, 4.0]})
    merged = merge.merge_halfhourly(frame, precedence=(TGA, LI))
    summary = merge.switch_summary(merged)

    assert merge.total_switches(merged) == 3
    assert summary["n_switches"].sum() == merge.total_switches(merged)


def test_analyzer_runs_group_consecutive_observations():
    frame = raw_frame(**{TGA: [1.0, 2.0, None], LI: [None, None, 3.0]})
    runs = merge.analyzer_runs(merge.merge_halfhourly(frame, precedence=(TGA, LI)))

    assert len(runs) == 2
    assert runs.loc[0, "analyzer"] == "TGA-100A"
    assert runs.loc[0, "n"] == 2
    assert runs.loc[1, "analyzer"] == "LI-7700"
    assert runs.loc[1, "n"] == 1
