"""Reconstruction variants, support classification and annual assembly."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import reconstruct


def frames(n: int = 36):
    """Synthetic record: flux rises with soil temperature and water table."""
    months = pd.period_range("2010-01", periods=n, freq="M")
    soil_c = np.tile(np.linspace(0.0, 18.0, 12), n // 12 + 1)[:n]
    water = np.linspace(412.6, 413.4, n)
    covariates = pd.DataFrame(
        {
            "soil_temp_f": soil_c * 9 / 5 + 32,
            "atm_temp_f": soil_c * 9 / 5 + 30,
            "precip_in": np.full(n, 0.2),
            "wte_m": water,
        },
        index=months,
    )
    log_flux = 2.0 + np.log(2.0) * soil_c / 10.0 + 1.5 * (water - 413.0)
    monthly = pd.DataFrame({"fch4_mean": np.exp(log_flux)}, index=months)
    return covariates, monthly


COLUMNS = ("soil_temp_f", "atm_temp_f", "precip_in", "wte_m")


def test_unknown_variant_is_rejected():
    covariates, monthly = frames()
    with pytest.raises(ValueError, match="unknown variant"):
        reconstruct.fit_variant(covariates, monthly, covariates.index, "sideways")


def test_reduced_variant_drops_the_water_table_column():
    covariates, monthly = frames()
    fit, _ = reconstruct.fit_variant(covariates, monthly, covariates.index, "reduced")
    assert "water_table_clamped" not in fit.columns
    full, _ = reconstruct.fit_variant(covariates, monthly, covariates.index, "clamped")
    assert "water_table_clamped" in full.columns


def test_clamped_and_unclamped_agree_inside_the_fitted_range():
    """Beyond the range they must part; inside it they are the same model."""
    covariates, monthly = frames()
    fit_months = covariates.index[:24]
    inside = covariates.index[:24]
    fit, bounds = reconstruct.fit_variant(covariates, monthly, fit_months, "clamped")

    clamped = reconstruct.predict_variant(fit, covariates, inside, "clamped", bounds)
    unclamped = reconstruct.predict_variant(fit, covariates, inside, "unclamped", bounds)
    assert np.allclose(clamped, unclamped)


def test_unclamped_departs_from_clamped_beyond_the_range():
    covariates, monthly = frames()
    fit_months = covariates.index[:24]
    beyond = covariates.index[24:]
    fit, bounds = reconstruct.fit_variant(covariates, monthly, fit_months, "clamped")

    clamped = reconstruct.predict_variant(fit, covariates, beyond, "clamped", bounds)
    unclamped = reconstruct.predict_variant(fit, covariates, beyond, "unclamped", bounds)
    assert (unclamped > clamped).all()


def test_support_marks_years_outside_the_fitted_range():
    covariates, monthly = frames(36)
    fit_months = covariates.index[:24]
    target = covariates.index[24:]
    table = reconstruct.year_support(covariates, fit_months, target, COLUMNS)

    assert set(table["support"]) <= {"inside", "outside"}
    assert table["n_months_outside_range"].sum() > 0
    assert "wte_m" in " ".join(table["covariates_outside"])


def test_support_marks_a_contained_period_inside():
    covariates, _ = frames(36)
    fit_months = covariates.index
    target = covariates.index[:12]
    table = reconstruct.year_support(covariates, fit_months, target, COLUMNS)
    assert (table["support"] == "inside").all()
    assert table["n_months_outside_range"].sum() == 0


def test_monthly_reconstruction_carries_all_variants_and_an_interval():
    covariates, monthly = frames(36)
    fit_months = covariates.index[:24]
    target = covariates.index[24:]
    frame = reconstruct.monthly_reconstruction(covariates, monthly, fit_months, target)

    assert set(reconstruct.VARIANTS) <= set(frame.columns)
    assert (frame["lower"] <= frame["clamped"]).all()
    assert (frame["upper"] >= frame["clamped"]).all()
    assert (frame[list(reconstruct.VARIANTS)] > 0).all().all()


def test_annual_assembly_reports_span_and_bias_direction():
    covariates, monthly = frames(36)
    fit_months = covariates.index[:24]
    target = covariates.index[24:]
    frame = reconstruct.monthly_reconstruction(covariates, monthly, fit_months, target)
    support_table = reconstruct.year_support(covariates, fit_months, target, COLUMNS)
    annual = reconstruct.annual_reconstruction(frame, support_table, expected_bias_log=0.148)

    row = annual.iloc[0]
    assert row["sensitivity_low"] <= row["clamped"] <= row["sensitivity_high"]
    assert row["bias_expectation"] == "model predicts low"
    # A positive expected bias means an upward correction, were one applied.
    assert row["if_corrected"] > row["clamped"]


def test_zero_expected_bias_leaves_the_estimate_unchanged():
    covariates, monthly = frames(36)
    fit_months = covariates.index[:24]
    target = covariates.index[24:]
    frame = reconstruct.monthly_reconstruction(covariates, monthly, fit_months, target)
    support_table = reconstruct.year_support(covariates, fit_months, target, COLUMNS)
    annual = reconstruct.annual_reconstruction(frame, support_table, expected_bias_log=0.0)
    assert annual.iloc[0]["if_corrected"] == pytest.approx(annual.iloc[0]["clamped"], abs=0.01)
