"""Coefficient stability under a narrowing covariate range."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import stability


def frames(n: int = 40, water_effect: float = 2.0):
    """A synthetic record whose flux depends on soil temperature and water table."""
    months = pd.period_range("2010-01", periods=n, freq="M")
    rng = np.random.default_rng(0)
    soil_c = np.tile(np.linspace(0.0, 18.0, 12), n // 12 + 1)[:n]
    water = np.linspace(412.5, 413.5, n)
    covariates = pd.DataFrame(
        {"soil_temp_f": soil_c * 9 / 5 + 32, "wte_m": water}, index=months
    )
    log_flux = 2.0 + np.log(2.0) * soil_c / 10.0 + water_effect * (water - 413.0)
    monthly = pd.DataFrame({"fch4_mean": np.exp(log_flux)}, index=months)
    return covariates, monthly


def test_drier_subset_removes_the_wettest_months():
    covariates, _ = frames(20)
    kept = stability.drier_subset(covariates, covariates.index, 0.25)
    assert len(kept) == 15
    assert covariates.loc[kept, "wte_m"].max() < covariates["wte_m"].max()


def test_drier_subset_keeps_everything_at_zero():
    covariates, _ = frames(20)
    kept = stability.drier_subset(covariates, covariates.index, 0.0)
    assert len(kept) == 20


def test_drier_subset_rejects_an_impossible_share():
    covariates, _ = frames(10)
    with pytest.raises(ValueError, match="at least zero and below one"):
        stability.drier_subset(covariates, covariates.index, 1.0)


def test_a_genuinely_constant_coefficient_is_recovered_at_every_step():
    """Flux built with a fixed water table effect must show that effect throughout."""
    covariates, monthly = frames(48, water_effect=2.0)
    path = stability.coefficient_path(
        covariates, monthly, covariates.index, drop_shares=(0.0, 0.2, 0.4), n_bootstrap=40
    )
    assert np.allclose(path["water_table_coef"], 2.0, atol=1e-6)
    assert stability.verdict(path)["stable"] is True


def test_verdict_rejects_a_monotone_drift():
    """A coefficient climbing as the range narrows must not pass as stable."""
    path = pd.DataFrame(
        {
            "dropped_wettest_pct": [0, 10, 20, 30, 40],
            "water_table_coef": [2.5, 2.7, 2.9, 3.3, 4.1],
            "water_table_lo": [2.0] * 5,
            "water_table_hi": [5.0] * 5,
            "water_table_includes_zero": [False] * 5,
        }
    )
    result = stability.verdict(path)
    assert result["stable"] is False
    assert result["trend_with_share_removed"] == pytest.approx(1.0)
    assert any("trends monotonically" in f for f in result["failures"])
    assert "no linear continuation" in result["bracket_meaning"]


def test_verdict_rejects_an_interval_spanning_zero():
    path = pd.DataFrame(
        {
            "dropped_wettest_pct": [0, 10],
            "water_table_coef": [1.8, 1.9],
            "water_table_lo": [-0.1, -0.2],
            "water_table_hi": [3.0, 3.2],
            "water_table_includes_zero": [True, True],
        }
    )
    result = stability.verdict(path)
    assert result["stable"] is False
    assert any("spans zero" in f for f in result["failures"])


def test_verdict_rejects_a_sign_change():
    path = pd.DataFrame(
        {
            "dropped_wettest_pct": [0, 10, 20],
            "water_table_coef": [2.0, 0.5, -1.0],
            "water_table_lo": [1.0, -1.0, -3.0],
            "water_table_hi": [3.0, 2.0, 1.0],
            "water_table_includes_zero": [False, True, True],
        }
    )
    result = stability.verdict(path)
    assert result["stable"] is False
    assert any("sign changes" in f for f in result["failures"])
