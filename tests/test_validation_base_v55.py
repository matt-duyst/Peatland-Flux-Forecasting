"""Reading the 2025 product and comparing it against the export, on synthetic frames."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from validation import base_v55


def stamps(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2015-01-01", periods=n, freq="30min", name="timestamp_start")


def frames(n: int = 8):
    """An export and a product agreeing everywhere they overlap."""
    index = stamps(n)
    values = np.arange(n, dtype=float)
    export = pd.DataFrame({"FCH4": values, "FCH4_1_1_1": values + 1}, index=index)
    product = export.copy()
    product["WD"] = np.linspace(0.0, 350.0, n)
    return export, product


def test_load_base_skips_the_comment_lines_and_replaces_sentinels(tmp_path):
    path = tmp_path / "base.csv"
    path.write_text(
        "# Site: US-MBP\n"
        "# Version: 5-5\n"
        "TIMESTAMP_START,TIMESTAMP_END,FCH4,WD\n"
        "201501010000,201501010030,12.5,45\n"
        "201501010030,201501010100,-9999,90\n"
    )
    frame = base_v55.load_base(path)

    assert list(frame.columns) == ["FCH4", "WD"]
    assert frame.index[0] == pd.Timestamp("2015-01-01 00:00")
    assert frame["FCH4"].iloc[0] == 12.5
    assert pd.isna(frame["FCH4"].iloc[1])


def test_identical_products_report_no_differences():
    export, product = frames()
    out = base_v55.compare_columns(export, product, ("FCH4",)).iloc[0]

    assert out["differing"] == 0
    assert out["identical"] == out["valid_both"] == 8
    assert out["only_export"] == 0 and out["only_product"] == 0
    assert out["max_abs_difference"] == 0.0


def test_a_changed_value_is_counted_and_measured():
    export, product = frames()
    product.loc[product.index[3], "FCH4"] += 0.25
    out = base_v55.compare_columns(export, product, ("FCH4",)).iloc[0]

    assert out["differing"] == 1
    assert out["identical"] == 7
    assert out["max_abs_difference"] == pytest.approx(0.25)


def test_a_column_absent_from_one_product_is_reported_not_raised():
    export, product = frames()
    out = base_v55.compare_columns(export, product, ("USTAR",)).iloc[0]

    assert not out["in_both_products"]


def test_differences_are_localised_to_the_year_they_occur_in():
    index = pd.DatetimeIndex(["2015-06-01", "2015-06-02", "2016-06-01"], name="timestamp_start")
    export = pd.DataFrame({"FCH4": [1.0, 2.0, 3.0]}, index=index)
    product = pd.DataFrame({"FCH4": [1.0, 2.0, 9.0]}, index=index)
    out = base_v55.difference_by_year(export, product, "FCH4")

    assert out.loc[2015, "differing"] == 0
    assert out.loc[2016, "differing"] == 1


def test_sector_membership_is_half_open_on_its_bounds():
    product = pd.DataFrame({"WD": [29.0, 30.0, 199.0, 200.0, np.nan]}, index=stamps(5))
    inside = base_v55.sector_membership(product)

    assert list(inside) == [False, True, True, False, False]


def test_a_flux_already_filtered_shows_a_zero_share_against_a_nonzero_baseline():
    """The published product carries no flux from the excluded sector."""
    index = stamps(4)
    product = pd.DataFrame(
        {"WD": [45.0, 100.0, 250.0, 300.0], "FCH4": [np.nan, np.nan, 5.0, 6.0]},
        index=index,
    )
    out = base_v55.sector_cost(product, ("FCH4",)).set_index("series")

    assert out.loc["all half-hours", "pct_inside_sector"] == 50.0
    assert out.loc["FCH4", "pct_inside_sector"] == 0.0


def test_coverage_is_reported_against_what_the_sector_leaves():
    index = stamps(4)
    product = pd.DataFrame({"WD": [45.0, 100.0, 250.0, 300.0]}, index=index)
    methane = pd.Series([np.nan, np.nan, 5.0, np.nan], index=index)
    out = base_v55.coverage_against_sector(product, methane).set_index("stage")

    assert out.loc["removed by the excluded sector", "n_half_hours"] == 2
    assert out.loc["outside sector, wind direction recorded", "n_half_hours"] == 2
    assert out.loc["methane retained", "pct_of_record"] == 25.0
    assert out.loc["methane retained", "pct_of_what_sector_leaves"] == 50.0


def test_merged_methane_follows_precedence_and_never_averages():
    index = stamps(3)
    product = pd.DataFrame(
        {"FCH4": [1.0, np.nan, np.nan], "FCH4_1_1_1": [7.0, 2.0, np.nan],
         "FCH4_1_1_2": [8.0, 9.0, 3.0]},
        index=index,
    )
    merged = base_v55.merged_methane(product, ("FCH4", "FCH4_1_1_1", "FCH4_1_1_2"))

    assert list(merged) == [1.0, 2.0, 3.0]


def test_badm_value_returns_none_for_an_absent_variable():
    badm = pd.DataFrame({"VARIABLE": ["IGBP"], "DATAVALUE": ["WET"]})

    assert base_v55.badm_value(badm, "IGBP") == "WET"
    assert base_v55.badm_value(badm, "GRP_INST") is None
