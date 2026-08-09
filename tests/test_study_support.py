"""Whether a target period lies inside the range a fit period covers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import support

COLUMNS = ("a", "b")


def frame(a: list, b: list) -> pd.DataFrame:
    months = pd.period_range("2009-01", periods=len(a), freq="M")
    return pd.DataFrame({"a": a, "b": b}, index=months, dtype=float)


def test_distribution_comparison_counts_values_outside_the_fit_range():
    cov = frame([1, 2, 3, 0, 5], [1, 1, 1, 1, 1])
    fit, target = cov.index[:3], cov.index[3:]
    table = support.distribution_comparison(cov, fit, target, COLUMNS).set_index("covariate")

    assert table.loc["a", "fit_min"] == 1.0 and table.loc["a", "fit_max"] == 3.0
    assert table.loc["a", "n_below_fit_min"] == 1
    assert table.loc["a", "n_above_fit_max"] == 1
    assert table.loc["a", "pct_outside"] == 100.0
    assert table.loc["b", "n_outside"] == 0


def test_out_of_range_months_records_direction_and_excess():
    cov = frame([1, 2, 3, 0, 5], [1, 1, 1, 1, 1])
    table = support.out_of_range_months(cov, cov.index[:3], cov.index[3:], COLUMNS).set_index("month")

    assert table.loc["2009-04", "direction"] == "below"
    assert table.loc["2009-04", "excess"] == 1.0
    assert table.loc["2009-05", "direction"] == "above"
    assert table.loc["2009-05", "excess"] == 2.0


def test_a_fully_contained_target_yields_no_rows():
    cov = frame([1, 2, 3, 2, 2], [1, 1, 1, 1, 1])
    table = support.out_of_range_months(cov, cov.index[:3], cov.index[3:], COLUMNS)
    assert table.empty
    assert list(table.columns)[:3] == ["month", "covariate", "value"]


def test_any_covariate_outside_counts_months_not_covariate_months():
    """One month failing on two covariates is one month, not two."""
    cov = frame([1, 2, 9], [1, 2, 9])
    table = support.out_of_range_months(cov, cov.index[:2], cov.index[2:], COLUMNS)
    summary = support.months_with_any_covariate_outside(table, n_reconstruction=1)

    assert len(table) == 2
    assert summary["n_months_any_outside"] == 1
    assert summary["pct_of_reconstruction"] == 100.0


def test_runs_collapse_consecutive_months():
    months = pd.period_range("2009-01", periods=6, freq="M")
    cov = pd.DataFrame({"a": [1, 1, 9, 9, 1, 9], "b": [1] * 6}, index=months, dtype=float)
    table = support.out_of_range_months(cov, months[[0, 1]], months[2:], COLUMNS)
    runs = support.out_of_range_runs(table)

    spans = {(r["from"], r["to"], r["n_months"]) for _, r in runs.iterrows()}
    assert ("2009-03", "2009-04", 2) in spans
    assert ("2009-06", "2009-06", 1) in spans


def test_joint_support_places_a_distant_month_beyond_the_fit_spread():
    months = pd.period_range("2009-01", periods=6, freq="M")
    cov = pd.DataFrame(
        {"a": [1.0, 1.1, 0.9, 1.05, 0.95, 20.0], "b": [1.0, 1.2, 0.8, 1.1, 0.9, 1.0]},
        index=months,
    )
    table = support.joint_support(cov, months[:5], months[5:], COLUMNS).set_index("group")
    held = table.loc["reconstruction months to nearest fit month"]

    assert held["n_beyond_fit_p95"] == 1
    assert held["median"] > table.loc["fit months to nearest other fit month", "median"]


def test_joint_support_ignores_a_covariate_that_never_varies():
    """A constant covariate must not make every distance undefined."""
    months = pd.period_range("2009-01", periods=6, freq="M")
    cov = pd.DataFrame(
        {"a": [1.0, 1.1, 0.9, 1.05, 0.95, 20.0], "b": [1.0] * 6}, index=months
    )
    table = support.joint_support(cov, months[:5], months[5:], COLUMNS).set_index("group")
    held = table.loc["reconstruction months to nearest fit month"]

    assert np.isfinite(held["median"])
    assert held["n_beyond_fit_p95"] == 1


def test_joint_support_raises_when_nothing_varies():
    months = pd.period_range("2009-01", periods=4, freq="M")
    cov = pd.DataFrame({"a": [1.0] * 4, "b": [2.0] * 4}, index=months)
    with pytest.raises(ValueError, match="no covariate varies"):
        support.joint_support(cov, months[:3], months[3:], COLUMNS)
