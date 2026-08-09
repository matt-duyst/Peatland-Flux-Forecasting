"""Daily and monthly aggregation: coverage rule, dispersion, analyzer fractions."""

from __future__ import annotations

import math

import pandas as pd
import pytest
from conftest import merged_day, merged_frame

from ingest import daily, site


def test_analyzer_fractions_sum_to_one_on_every_row():
    frame = merged_day([1, 2, 3, 4], ["site_aggregated", "site_aggregated", "TGA-100A", "LI-7700"], "2015-06-01")
    frame["date"] = frame["timestamp_start"].dt.normalize()
    fractions = daily._analyzer_fractions(frame, "date")

    assert fractions[list(site.FRACTION_COLUMNS)].sum(axis=1).eq(1.0).all()
    assert fractions.loc[pd.Timestamp("2015-06-01"), "frac_site_aggregated"] == 0.5
    assert fractions.loc[pd.Timestamp("2015-06-01"), "frac_tga100a"] == 0.25
    assert fractions.loc[pd.Timestamp("2015-06-01"), "frac_li7700"] == 0.25


def test_absent_analyzer_yields_a_zero_column_not_a_missing_one():
    """The fallback path: a frame holding one analyzer still emits all three columns."""
    frame = merged_day([1, 2], ["site_aggregated"] * 2, "2015-06-01")
    frame["date"] = frame["timestamp_start"].dt.normalize()
    fractions = daily._analyzer_fractions(frame, "date")

    assert list(site.FRACTION_COLUMNS) == [c for c in fractions.columns if c.startswith("frac_")]
    assert fractions["frac_tga100a"].eq(0.0).all()
    assert fractions["frac_li7700"].eq(0.0).all()
    assert fractions["frac_site_aggregated"].eq(1.0).all()


def test_unknown_analyzer_label_raises_rather_than_vanishing():
    """A fraction set summing below one would look valid, so this must fail loudly."""
    frame = merged_day([1, 2], ["site_aggregated", "NEW-SENSOR"], "2015-06-01")
    frame["date"] = frame["timestamp_start"].dt.normalize()

    with pytest.raises(ValueError, match="unknown analyzer label"):
        daily._analyzer_fractions(frame, "date")


def test_mixed_day_is_flagged_and_counted():
    frame = merged_day([1, 2], ["TGA-100A", "LI-7700"], "2015-06-01")
    frame["date"] = frame["timestamp_start"].dt.normalize()
    fractions = daily._analyzer_fractions(frame, "date")

    assert fractions.loc[pd.Timestamp("2015-06-01"), "n_analyzers"] == 2
    assert bool(fractions.loc[pd.Timestamp("2015-06-01"), "is_mixed"])


def test_daily_threshold_keeps_eight_and_drops_seven():
    """The coverage rule admits a day at exactly eight valid half-hours."""
    seven = merged_day(list(range(7)), ["site_aggregated"] * 7, "2015-06-01")
    eight = merged_day(list(range(8)), ["site_aggregated"] * 8, "2015-06-02")

    assert daily.daily_stats(seven, min_halfhours=8).empty
    assert len(daily.daily_stats(eight, min_halfhours=8)) == 1


def test_daily_statistics_match_hand_computation(site_only_day):
    """Values 2..16 step 2: mean 9, variance 24, standard error sqrt(3)."""
    result = daily.daily_stats(site_only_day, min_halfhours=8)
    row = result.iloc[0]

    assert row["fch4_n"] == 8
    assert row["fch4_mean"] == pytest.approx(9.0)
    assert row["fch4_sd"] == pytest.approx(math.sqrt(24.0))
    assert row["fch4_se"] == pytest.approx(math.sqrt(3.0))


def test_single_observation_day_has_undefined_dispersion():
    frame = merged_day([42.0], ["site_aggregated"], "2015-06-01")
    result = daily.daily_stats(frame, min_halfhours=1)

    assert result.loc[0, "fch4_n"] == 1
    assert result.loc[0, "fch4_mean"] == 42.0
    assert pd.isna(result.loc[0, "fch4_sd"])
    assert pd.isna(result.loc[0, "fch4_se"])


def test_month_built_from_one_day_has_undefined_across_day_dispersion():
    frame = merged_day([2, 4, 6, 8, 10, 12, 14, 16], ["site_aggregated"] * 8, "2015-06-01")
    monthly = daily.daily_to_monthly(daily.daily_stats(frame, min_halfhours=8))

    assert monthly.loc[0, "fch4_days"] == 1
    assert monthly.loc[0, "fch4_mean"] == pytest.approx(9.0)
    assert pd.isna(monthly.loc[0, "fch4_sd_across_days"])
    assert pd.isna(monthly.loc[0, "fch4_se_across_days"])


def test_monthly_fractions_weight_days_by_observation_count():
    """Day one is eight site-aggregated values; day two is four TGA and four LI."""
    day_one = merged_day([10] * 8, ["site_aggregated"] * 8, "2015-06-01")
    day_two = merged_day([20] * 8, ["TGA-100A"] * 4 + ["LI-7700"] * 4, "2015-06-02")
    frame = pd.concat([day_one, day_two], ignore_index=True)

    monthly = daily.daily_to_monthly(daily.daily_stats(frame, min_halfhours=8))
    row = monthly.iloc[0]

    assert row["fch4_days"] == 2
    assert row["fch4_halfhours"] == 16
    assert row["fch4_mean"] == pytest.approx(15.0)
    assert row["frac_site_aggregated"] == pytest.approx(0.5)
    assert row["frac_tga100a"] == pytest.approx(0.25)
    assert row["frac_li7700"] == pytest.approx(0.25)
    assert row["n_mixed_days"] == 1
    assert sum(row[c] for c in site.FRACTION_COLUMNS) == pytest.approx(1.0)


def test_monthly_fractions_sum_to_one_across_several_months():
    frames = [
        merged_day([1] * 8, ["site_aggregated"] * 8, "2015-06-01"),
        merged_day([2] * 8, ["TGA-100A"] * 8, "2015-07-01"),
        merged_day([3] * 8, ["LI-7700"] * 4 + ["site_aggregated"] * 4, "2015-08-01"),
    ]
    monthly = daily.daily_to_monthly(
        daily.daily_stats(pd.concat(frames, ignore_index=True), min_halfhours=8)
    )

    totals = monthly[list(site.FRACTION_COLUMNS)].sum(axis=1)
    assert len(monthly) == 3
    assert totals.eq(1.0).all()


def test_daily_means_ignore_null_flux_slots():
    frame = merged_frame(
        [4.0, None, 8.0, None, 12.0, None, 4.0, 8.0, 12.0, None],
        ["site_aggregated"] * 10,
        start="2015-06-01 00:00",
    )
    result = daily.daily_stats(frame, min_halfhours=6)

    assert result.loc[0, "fch4_n"] == 6
    assert result.loc[0, "fch4_mean"] == pytest.approx(8.0)
