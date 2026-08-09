"""Holdout selection, the training-only clamp, and the extrapolation diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import holdout


def frames(n: int = 24):
    """A synthetic record whose flux follows an exact Q10 of 2 in soil temperature."""
    months = pd.period_range("2010-01", periods=n, freq="M")
    soil_c = np.linspace(0.0, 20.0, n)
    covariates = pd.DataFrame(
        {
            "soil_temp_f": soil_c * 9 / 5 + 32,
            "atm_temp_f": soil_c * 9 / 5 + 30,
            "precip_in": np.linspace(0.1, 0.4, n),
            "wte_m": np.linspace(412.5, 413.5, n),
        },
        index=months,
    )
    flux = 10.0 * 2.0 ** (soil_c / 10.0)
    monthly = pd.DataFrame(
        {
            "fch4_mean": flux,
            "fch4_se_across_days": flux * 0.05,
            "fch4_days": np.full(n, 20),
        },
        index=months,
    )
    return covariates, monthly


def test_wettest_decile_selects_the_highest_water_table_months():
    covariates, _ = frames(20)
    held = holdout.wettest_decile(covariates, covariates.index, share=0.10)
    assert len(held) == 2
    assert set(held) == set(covariates.index[-2:])


def test_coldest_decile_selects_the_lowest_soil_temperature_months():
    covariates, _ = frames(20)
    held = holdout.coldest_decile(covariates, covariates.index, share=0.10)
    assert set(held) == set(covariates.index[:2])


def test_earliest_and_latest_years_split_on_whole_years():
    months = pd.period_range("2010-01", periods=48, freq="M")
    assert {m.year for m in holdout.earliest_years(months, 2)} == {2010, 2011}
    assert {m.year for m in holdout.latest_years(months, 2)} == {2012, 2013}
    assert len(holdout.earliest_years(months, 2)) == 24


def test_splits_never_overlap_their_training_set():
    covariates, _ = frames(30)
    for _, held in holdout.build_splits(covariates, covariates.index):
        train = covariates.index.difference(held)
        assert len(train.intersection(held)) == 0
        assert len(train) + len(held) == len(covariates.index)


def test_experiment_recovers_a_known_q10():
    """Flux built with a Q10 of exactly 2 must be recovered as 2."""
    covariates, monthly = frames(24)
    held = holdout.latest_years(covariates.index, 1)
    train = covariates.index.difference(held)
    record = holdout.run_experiment(
        "synthetic", covariates, monthly, train, held,
        ("soil_temp_f", "wte_m"), include_water_table=False,
    )
    assert record["q10"] == pytest.approx(2.0, abs=1e-6)
    assert record["mae_log"] == pytest.approx(0.0, abs=1e-6)


def test_clamp_is_set_from_training_months_only():
    """A holdout wetter than the training set must not extend the clamp."""
    covariates, monthly = frames(24)
    held = holdout.wettest_decile(covariates, covariates.index, share=0.10)
    train = covariates.index.difference(held)
    record = holdout.run_experiment(
        "synthetic", covariates, monthly, train, held,
        ("soil_temp_f", "wte_m"), include_water_table=True,
    )
    train_max = covariates.loc[train, "wte_m"].max()
    assert record["fit"].water_table_bounds[1] == pytest.approx(train_max)
    assert covariates.loc[held, "wte_m"].max() > train_max


def test_covariate_contrast_counts_months_outside_the_training_range():
    covariates, _ = frames(20)
    held = holdout.wettest_decile(covariates, covariates.index, share=0.10)
    train = covariates.index.difference(held)
    contrast = holdout.holdout_covariate_contrast(
        covariates, train, held, ("soil_temp_f", "wte_m")
    ).set_index("covariate")

    assert contrast.loc["wte_m", "n_holdout_outside"] == 2
    assert contrast.loc["wte_m", "pct_holdout_outside"] == 100.0


def test_analogue_strength_compares_holdout_reach_with_reconstruction_reach():
    covariates, _ = frames(24)
    fit_months = covariates.index[:20]
    reconstruction = covariates.index[20:]
    splits = [("wettest", holdout.wettest_decile(covariates, fit_months, 0.10))]
    table = holdout.analogue_strength(covariates, fit_months, reconstruction, splits)

    row = table.iloc[0]
    assert row["max_excess"] > 0
    assert row["reconstruction_max_excess"] > row["max_excess"]
    assert row["share_of_reconstruction_excess"] < 1.0
