"""Covariate coverage and the fit and reconstruction windows drawn from it."""

from __future__ import annotations

import pandas as pd

from study import windows


def covariates(n: int = 24, start: str = "2009-01") -> pd.DataFrame:
    months = pd.period_range(start, periods=n, freq="M")
    return pd.DataFrame(
        {
            "soil_temp_f": range(n),
            "atm_temp_f": range(n),
            "precip_in": [0.2] * n,
            "wte_m": [413.0] * n,
            "fco2": [-1.0] * n,
        },
        index=months,
        dtype=float,
    )


def test_coverage_reports_span_and_interior_gaps():
    cov = covariates(6)
    cov.loc[pd.Period("2009-03", freq="M"), "wte_m"] = None
    table = windows.covariate_coverage(cov).set_index("covariate")

    assert table.loc["wte_m", "n_months"] == 5
    assert table.loc["wte_m", "span_months"] == 6
    assert table.loc["wte_m", "n_interior_gaps"] == 1
    assert table.loc["wte_m", "interior_gaps"] == "2009-03"
    assert table.loc["soil_temp_f", "n_interior_gaps"] == 0


def test_coverage_marks_which_covariates_can_reconstruct():
    table = windows.covariate_coverage(covariates()).set_index("covariate")
    assert table.loc["soil_temp_f", "reconstruction_capable"]
    assert not table.loc["fco2", "reconstruction_capable"]
    assert "fco2" in windows.CONTEMPORANEOUS_ONLY


def test_complete_months_require_every_named_covariate():
    cov = covariates(4)
    cov.loc[pd.Period("2009-02", freq="M"), "precip_in"] = None
    complete = windows.complete_covariate_months(cov)
    assert len(complete) == 3
    assert pd.Period("2009-02", freq="M") not in complete


def test_windows_split_on_the_first_methane_month():
    """Complete months before the record begins are reconstruction, not gaps."""
    cov = covariates(12)
    methane = pd.period_range("2009-07", periods=6, freq="M")
    built = windows.build_windows(cov, methane)

    assert len(built["fit"]) == 6
    assert len(built["reconstruction"]) == 6
    assert built["reconstruction"].max() < methane.min()
    assert len(built["interior_gaps"]) == 0


def test_months_without_methane_after_the_record_starts_are_interior_gaps():
    cov = covariates(5)
    methane = pd.PeriodIndex(["2009-01", "2009-02", "2009-05"], freq="M")
    built = windows.build_windows(cov, methane)

    assert set(map(str, built["interior_gaps"])) == {"2009-03", "2009-04"}
    assert len(built["reconstruction"]) == 0


def test_methane_months_lacking_a_covariate_are_excluded():
    cov = covariates(6)
    cov.loc[pd.Period("2009-04", freq="M"), "soil_temp_f"] = None
    methane = pd.period_range("2009-01", periods=6, freq="M")
    built = windows.build_windows(cov, methane)

    assert pd.Period("2009-04", freq="M") in built["methane_excluded"]
    assert pd.Period("2009-04", freq="M") not in built["fit"]


def test_accounting_reports_absent_months_only_for_contiguous_windows():
    cov = covariates(5)
    methane = pd.PeriodIndex(["2009-01", "2009-02", "2009-05"], freq="M")
    built = windows.build_windows(cov, methane)
    table = windows.window_accounting(built).set_index("window")

    assert table.loc["fit", "span_months"] == 5
    assert table.loc["fit", "n_absent"] == 2
    assert table.loc["interior_gaps", "span_months"] == ""


def test_absent_months_lists_the_holes_in_a_span():
    cov = covariates(5)
    methane = pd.PeriodIndex(["2009-01", "2009-02", "2009-05"], freq="M")
    built = windows.build_windows(cov, methane)
    assert windows.absent_months(built, "fit") == ["2009-03", "2009-04"]


def test_binding_constraint_names_the_limiting_covariate():
    cov = covariates(12)
    cov.loc[cov.index[-3:], "atm_temp_f"] = None   # ends earliest
    cov.loc[cov.index[:2], "precip_in"] = None     # starts latest
    table = windows.binding_constraint(windows.covariate_coverage(cov)).set_index("bound")

    assert table.loc["fit window ends at", "covariate"] == "atm_temp_f"
    assert table.loc["reconstruction window starts at", "covariate"] == "precip_in"
