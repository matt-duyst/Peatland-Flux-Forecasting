"""Published budgets, mass conversion and annual integration."""

from __future__ import annotations

import pandas as pd
import pytest

from study import targets


def test_carbon_and_methane_conversion_are_inverses():
    assert targets.methane_to_carbon(targets.carbon_to_methane(10.0)) == pytest.approx(10.0)


def test_one_gram_of_methane_carries_the_molar_mass_fraction_of_carbon():
    assert targets.C_PER_CH4 == pytest.approx(12.011 / 16.043)
    assert targets.methane_to_carbon(1.0) == pytest.approx(0.74868, abs=1e-5)
    assert targets.carbon_to_methane(1.0) == pytest.approx(1.33569, abs=1e-5)


def test_published_targets_carry_both_mass_conventions():
    table = targets.published_annual_targets().set_index("year")
    assert table.loc[2009, "olson_g_C_m2_yr"] == 11.8
    assert table.loc[2009, "olson_g_CH4_m2_yr"] == pytest.approx(15.76, abs=0.01)


def test_reconstruction_range_converts_both_ends():
    published = targets.published_reconstruction_range()
    assert published["low_g_C"] == 7.8
    assert published["low_g_CH4"] == pytest.approx(targets.carbon_to_methane(7.8), abs=0.01)
    assert published["high_g_CH4"] > published["low_g_CH4"]


def test_annual_integration_matches_a_hand_calculation():
    """Ten nmol per square meter per second held for a 365-day year."""
    flux = pd.Series([10.0] * 12, index=pd.period_range("2010-01", periods=12, freq="M"))
    table = targets.monthly_flux_to_annual(flux)
    expected = 10.0 * 365 * 86400 * 1e-9 * targets.MOLAR_MASS_CH4

    assert table.loc[2010, "n_months"] == 12
    assert table.loc[2010, "g_CH4_m2"] == pytest.approx(expected, abs=0.001)
    assert table.loc[2010, "g_C_m2"] == pytest.approx(expected * targets.C_PER_CH4, abs=0.001)


def test_integration_respects_unequal_month_lengths():
    """January and February at the same flux must not contribute equally."""
    flux = pd.Series([10.0, 10.0], index=pd.period_range("2010-01", periods=2, freq="M"))
    table = targets.monthly_flux_to_annual(flux)
    single = targets.monthly_flux_to_annual(flux.iloc[:1])
    # Totals are reported to three decimal places, so compare within that.
    assert table.loc[2010, "g_CH4_m2"] / single.loc[2010, "g_CH4_m2"] == pytest.approx(59 / 31, rel=0.01)


def test_partial_years_are_flagged_by_their_month_count():
    flux = pd.Series([10.0] * 5, index=pd.period_range("2010-08", periods=5, freq="M"))
    table = targets.monthly_flux_to_annual(flux)
    assert table.loc[2010, "n_months"] == 5
    assert table.loc[2011, "n_months"] == 0 if 2011 in table.index else True


def test_holdout_comparison_flags_whether_each_year_lands_inside():
    annual = pd.DataFrame(
        {"n_months": [12, 12, 12], "g_CH4_m2": [0.0] * 3, "g_C_m2": [11.0, 20.0, 24.0]},
        index=pd.Index([2009, 2010, 2011], name="year"),
    )
    table = targets.holdout_against_published(annual).set_index("year")

    assert bool(table.loc[2009, "within_olson_interval"]) is True     # |11.0-11.8| < 3.1
    assert bool(table.loc[2010, "within_olson_interval"]) is False    # |20.0-12.2| > 3.0
    assert table.loc[2011, "difference_g_C"] == pytest.approx(-0.9)


def test_independent_check_reports_no_observations_before_the_record():
    observed = pd.period_range("2009-04", periods=12, freq="M")
    table = targets.independent_check_coverage(observed).set_index("growing_season")
    assert table.loc["1991-05..1991-10", "months_observed_here"] == 0
    assert table.loc["1992-05..1992-10", "months_in_season"] == 6
