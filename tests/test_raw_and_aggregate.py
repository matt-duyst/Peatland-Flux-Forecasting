"""Sentinel replacement in the raw reader, and monthly aggregation arithmetic."""

from __future__ import annotations

import math

import pandas as pd
import pytest
from conftest import raw_frame

from ingest import aggregate, raw, site


def _fake_sheet() -> pd.DataFrame:
    """A raws-shaped sheet: BASE timestamps, sentinels, and one real value each."""
    return pd.DataFrame(
        {
            "TIMESTAMP_START": [201501010030, 201501010000, 201501010100],
            "FCH4": [-9999.0, 12.5, 20.0],
            "FCH4_1_1_1": [-9999.0, -9999.0, 7.0],
            "FCH4_1_1_2": [3.0, -9999.0, -9999.0],
        }
    )


def test_sentinel_becomes_null_and_real_values_survive(monkeypatch, tmp_path):
    monkeypatch.setattr(raw, "_read_sheet", _fake_sheet)
    monkeypatch.setattr(raw, "_cache_path", lambda: tmp_path / "cache.parquet")

    frame = raw.load_halfhourly(use_cache=False)

    assert frame["FCH4"].isna().sum() == 1
    assert frame["FCH4_1_1_1"].isna().sum() == 2
    assert frame["FCH4_1_1_2"].isna().sum() == 2
    assert set(frame["FCH4"].dropna()) == {12.5, 20.0}
    assert not (frame[list(site.ANALYZER_BY_COLUMN)] == raw.SENTINEL).any().any()


def test_timestamps_are_parsed_and_sorted(monkeypatch, tmp_path):
    monkeypatch.setattr(raw, "_read_sheet", _fake_sheet)
    monkeypatch.setattr(raw, "_cache_path", lambda: tmp_path / "cache.parquet")

    frame = raw.load_halfhourly(use_cache=False)

    assert frame["timestamp_start"].is_monotonic_increasing
    assert frame.loc[0, "timestamp_start"] == pd.Timestamp("2015-01-01 00:00")
    assert frame.loc[2, "timestamp_start"] == pd.Timestamp("2015-01-01 01:00")
    assert not frame["timestamp_start"].duplicated().any()


def test_missing_expected_column_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(raw, "_read_sheet", lambda: _fake_sheet().drop(columns=["FCH4_1_1_2"]))
    monkeypatch.setattr(raw, "_cache_path", lambda: tmp_path / "cache.parquet")

    with pytest.raises(ValueError, match="missing columns"):
        raw.load_halfhourly(use_cache=False)


def test_sentinel_report_counts_valid_and_missing():
    frame = raw_frame(FCH4=[1.0, None, 3.0], FCH4_1_1_1=[None, None, None])
    report = raw.sentinel_report(frame).set_index("column")

    assert report.loc["FCH4", "n_valid"] == 2
    assert report.loc["FCH4", "n_missing"] == 1
    assert report.loc["FCH4_1_1_1", "n_valid"] == 0
    assert report.loc["FCH4", "pct_missing"] == pytest.approx(33.33, abs=0.01)


def test_monthly_statistics_match_hand_computation():
    """Values 1..6 in one month: mean 3.5, variance 3.5, count 6."""
    frame = pd.DataFrame(
        {
            "timestamp_start": pd.date_range("2015-06-01", periods=6, freq="30min"),
            "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )
    result = aggregate.monthly_stats(frame, "value")
    row = result.iloc[0]

    assert row["value_n"] == 6
    assert row["value_mean"] == pytest.approx(3.5)
    assert row["value_sd"] == pytest.approx(math.sqrt(3.5))
    assert row["value_se"] == pytest.approx(math.sqrt(3.5 / 6))


def test_monthly_statistics_skip_null_values():
    frame = pd.DataFrame(
        {
            "timestamp_start": pd.date_range("2015-06-01", periods=4, freq="30min"),
            "value": [2.0, None, 4.0, None],
        }
    )
    result = aggregate.monthly_stats(frame, "value")

    assert result.iloc[0]["value_n"] == 2
    assert result.iloc[0]["value_mean"] == pytest.approx(3.0)


def test_single_observation_month_has_undefined_dispersion():
    frame = pd.DataFrame(
        {"timestamp_start": pd.to_datetime(["2015-06-01"]), "value": [5.0]}
    )
    result = aggregate.monthly_stats(frame, "value")

    assert result.iloc[0]["value_n"] == 1
    assert pd.isna(result.iloc[0]["value_sd"])
    assert pd.isna(result.iloc[0]["value_se"])


def test_month_grid_leaves_no_month_out():
    grid = aggregate.month_grid("2015-01", "2015-12")

    assert len(grid) == 12
    assert str(grid[0]) == "2015-01"
    assert str(grid[-1]) == "2015-12"


def test_analyzer_slug_rejects_unknown_labels():
    assert site.analyzer_slug("TGA-100A") == "tga100a"
    with pytest.raises(ValueError, match="unknown analyzer label"):
        site.analyzer_slug("NEW-SENSOR")
