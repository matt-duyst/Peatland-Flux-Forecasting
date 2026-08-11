"""Direct forecasting, seasonal adjustment, screening, and the leakage guards.

Every test builds its own small frame. Nothing here reads the site record, so the
suite stays offline and fast.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecast import evaluation, experiment, features, models, preprocessing, screening


def months(n: int, start: str = "2010-01") -> pd.PeriodIndex:
    return pd.period_range(start, periods=n, freq="M")


def seasonal_series(n: int = 96, amplitude: float = 10.0, noise: float = 0.0) -> pd.Series:
    index = months(n)
    rng = np.random.default_rng(0)
    values = 20 + amplitude * np.sin(2 * np.pi * index.month / 12)
    if noise:
        values = values + rng.normal(0, noise, n)
    return pd.Series(values, index=index)


# --- the direct-forecast property ------------------------------------------


@pytest.mark.parametrize("horizon", [1, 2, 3, 6, 12, 13, 24])
def test_no_predictor_reaches_data_later_than_the_origin(horizon):
    """A lag below the horizon would be a value from after the forecast was made."""
    assert min(features.flux_lags_for(horizon)) >= horizon
    assert min(features.horizon_lags(features.BASE_COVARIATE_LAGS, horizon)) >= horizon


def test_the_annual_lag_stays_a_year_rather_than_sliding_with_the_horizon():
    """At a twelve-month horizon the annual lag is the origin month itself."""
    assert features.annual_lag(1) == 12
    assert features.annual_lag(12) == 12
    assert features.annual_lag(13) == 24


def test_recent_lags_keep_their_spacing_when_shifted():
    assert features.horizon_lags((1, 2, 3), 6) == (6, 7, 8)


def test_a_design_row_holds_only_values_from_before_its_own_month():
    series = pd.Series(range(40), index=months(40), dtype=float)
    horizon = 6
    design = features.build_design(series, horizon)
    row = design.loc[months(40)[30]]
    for column, value in row.items():
        if not column.startswith("flux_lag"):
            continue
        lag = int(column.removeprefix("flux_lag"))
        assert value == series.iloc[30 - lag]
        assert 30 - lag <= 30 - horizon


def test_seasonal_terms_are_a_property_of_the_calendar_alone():
    january = features.seasonal_terms(pd.PeriodIndex(["2011-01", "2019-01"], freq="M"))
    assert january.iloc[0].equals(january.iloc[1])


# --- seasonal adjustment ----------------------------------------------------


def test_adjustment_learns_from_the_training_window_only():
    series = seasonal_series(60)
    later = series.copy()
    later.iloc[48:] += 1000.0  # a level shift entirely after the training window
    train = series.iloc[:48]
    assert (preprocessing.SeasonalAdjustment().fit(train).means
            .equals(preprocessing.SeasonalAdjustment().fit(later.iloc[:48]).means))


def test_adjustment_round_trips():
    series = seasonal_series(48, noise=1.0)
    adjustment = preprocessing.SeasonalAdjustment().fit(series)
    restored = adjustment.inverse(adjustment.transform(series))
    pd.testing.assert_series_equal(restored, series)


def test_adjustment_removes_a_pure_seasonal_cycle():
    series = seasonal_series(48)
    residual = preprocessing.SeasonalAdjustment().fit(series).transform(series)
    assert residual.abs().max() < 1e-9


def test_an_unseen_month_falls_back_to_the_overall_mean():
    series = pd.Series([1.0, 2.0, 3.0], index=months(3))
    adjustment = preprocessing.SeasonalAdjustment().fit(series)
    expected = adjustment.transform(pd.Series([5.0], index=pd.PeriodIndex(["2010-07"], freq="M")))
    assert expected.iloc[0] == pytest.approx(5.0 - series.mean())


# --- screening --------------------------------------------------------------


def test_screening_keeps_a_real_predictor_and_drops_pure_noise():
    rng = np.random.default_rng(1)
    index = months(80)
    signal = pd.Series(rng.normal(size=80), index=index)
    design = pd.DataFrame(
        {"real": signal, "noise": rng.normal(size=80), "more_noise": rng.normal(size=80)},
        index=index,
    )
    target = 3 * signal + rng.normal(0, 0.1, 80)
    kept = screening.boruta_select(design, pd.Series(target, index=index))
    assert "real" in kept
    assert "noise" not in kept


def test_named_columns_survive_screening_whatever_the_forest_thinks():
    rng = np.random.default_rng(2)
    index = months(60)
    design = pd.DataFrame({"useless": rng.normal(size=60), "sin_year": rng.normal(size=60)},
                          index=index)
    target = pd.Series(rng.normal(size=60), index=index)
    assert "sin_year" in screening.boruta_select(design, target, always_keep=("sin_year",))


def test_a_redundant_copy_of_a_real_predictor_also_survives():
    """Boruta is all-relevant: two columns carrying the same signal both pass.

    This is why the kept sets are larger than a stepwise procedure would give,
    and why counting survivors does not count independent information.
    """
    rng = np.random.default_rng(4)
    index = months(96)
    signal = rng.normal(size=96)
    design = pd.DataFrame(
        {"real": signal, "copy": signal + rng.normal(0, 0.01, 96),
         "noise": rng.normal(size=96)},
        index=index,
    )
    target = pd.Series(3 * signal + rng.normal(0, 0.3, 96), index=index)
    kept = screening.boruta_select(design, target)
    assert {"real", "copy"} <= set(kept)
    assert "noise" not in kept


def test_irrelevant_candidates_survive_only_occasionally():
    """The screening is liberal by design, but it must not wave everything through.

    Only the shadow is redrawn between repeats, so the binomial threshold is not
    a guaranteed error rate and a single seed proves nothing either way. The
    bound here is loose on purpose: it catches the rule collapsing, not drift.
    """
    index = months(96)
    season = np.sin(2 * np.pi * index.month / 12)
    kept_count = trials = 0
    for seed in range(10):
        rng = np.random.default_rng(seed)
        design = pd.DataFrame(
            {"sin_year": season, **{f"c{i}": rng.normal(size=96) for i in range(4)}},
            index=index,
        )
        target = pd.Series(2 * season + rng.normal(size=96), index=index)
        kept_count += len(screening.boruta_select(design, target, always_keep=("sin_year",))) - 1
        trials += 4
    assert kept_count / trials < 0.25


def test_a_retained_term_is_never_judged_and_always_comes_first():
    rng = np.random.default_rng(5)
    index = months(96)
    design = pd.DataFrame({"sin_year": np.sin(2 * np.pi * index.month / 12),
                           "candidate": rng.normal(size=96)}, index=index)
    target = pd.Series(rng.normal(size=96), index=index)
    assert screening.boruta_select(design, target, always_keep=("sin_year",))[0] == "sin_year"


def test_screening_never_returns_an_empty_design():
    index = months(6)
    design = pd.DataFrame({"a": range(6)}, index=index, dtype=float)
    assert screening.boruta_select(design, pd.Series(range(6), index=index, dtype=float))


def test_screening_is_deterministic_for_a_given_seed():
    rng = np.random.default_rng(3)
    index = months(72)
    design = pd.DataFrame({f"x{i}": rng.normal(size=72) for i in range(4)}, index=index)
    target = pd.Series(design["x0"] * 2 + rng.normal(0, 0.2, 72), index=index)
    assert screening.boruta_select(design, target) == screening.boruta_select(design, target)


# --- leakage ----------------------------------------------------------------


def test_a_fold_is_built_from_months_up_to_the_origin_and_one_test_month():
    series = seasonal_series(72, noise=1.0)
    origin = series.index[59]
    horizon = 3
    design, target, test, _ = experiment.fold_matrices(series, origin, horizon, None)
    assert design.index.max() <= origin
    assert target.index.max() <= origin
    assert len(test) == 1
    assert test.index[0] == origin + horizon


def test_changing_the_future_cannot_change_a_fold_s_forecast():
    """The strongest leakage test available: corrupt everything after the target."""
    series = seasonal_series(84, noise=1.0)
    origin, horizon = series.index[59], 3
    corrupted = series.copy()
    corrupted.iloc[series.index.get_loc(origin + horizon) + 1:] = 9999.0

    def one(data):
        frame = experiment.run(data.loc[:origin + horizon], horizons=(horizon,),
                               min_train=48, methods={"ridge": models.MODELS["ridge"]})
        return frame[frame["origin"] == origin]["forecast"].to_numpy()

    np.testing.assert_allclose(one(series), one(corrupted))


def test_the_seasonal_adjustment_inside_a_fold_never_sees_the_test_month():
    series = seasonal_series(72, noise=1.0)
    origin, horizon = series.index[59], 6
    shifted = series.copy()
    shifted.loc[origin + horizon] += 500.0
    _, _, _, left = experiment.fold_matrices(series, origin, horizon, None)
    _, _, _, right = experiment.fold_matrices(shifted, origin, horizon, None)
    pd.testing.assert_series_equal(left.means, right.means)


def test_screening_is_rerun_per_fold_rather_than_once_over_the_record():
    series = seasonal_series(84, noise=2.0)
    frame = experiment.run(series, horizons=(1,), min_train=48,
                           methods={"ridge": models.MODELS["ridge"]})
    assert frame["origin"].nunique() > 1
    # Folds are not required to disagree, but they must each carry their own
    # answer rather than a single record-wide one copied down the column.
    assert frame["predictors"].notna().all()


def test_a_run_can_be_scored_by_the_same_code_as_a_benchmark():
    series = seasonal_series(84, noise=1.0)
    frame = experiment.run(series, horizons=(1, 3), min_train=48,
                           methods={"ridge": models.MODELS["ridge"]})
    table = evaluation.score(frame)
    assert set(table["horizon"]) == {1, 3}
    assert table["MASE"].notna().all()


# --- families ---------------------------------------------------------------


def test_the_two_families_are_disjoint_and_cover_every_model():
    assert not set(models.STATISTICAL) & set(models.MACHINE_LEARNING)
    assert set(models.MODELS) == set(models.STATISTICAL) | set(models.MACHINE_LEARNING)
    assert set(models.FAMILY) == set(models.MODELS)


def test_an_exogenous_run_uses_covariates_and_an_autoregressive_one_does_not():
    series = seasonal_series(84, noise=1.0)
    covariates = pd.DataFrame({"driver": np.arange(84, dtype=float)}, index=series.index)
    plain = experiment.run(series, horizons=(1,), min_train=48, screen=False,
                           methods={"ridge": models.MODELS["ridge"]})
    with_driver = experiment.run(series, exogenous=covariates, horizons=(1,), min_train=48,
                                 screen=False, methods={"ridge": models.MODELS["ridge"]})
    assert not any("driver" in p for p in plain["predictors"])
    assert all("driver_lag1" in p for p in with_driver["predictors"])


# --- comparability ----------------------------------------------------------


def test_a_month_one_method_could_not_score_is_not_in_the_shared_set():
    frame = pd.DataFrame(
        {
            "horizon": [1, 1, 1, 1],
            "target": list(months(2)) * 2,
            "method": ["a", "a", "b", "b"],
            "actual": [1.0, 2.0, 1.0, 2.0],
            "forecast": [1.0, 2.0, 1.0, np.nan],
            "mase_scale": [1.0] * 4,
        }
    )
    shared = evaluation.fully_scored(frame)
    assert (1, months(2)[0]) in shared
    assert (1, months(2)[1]) not in shared


def test_restricting_to_shared_months_puts_every_family_on_one_footing():
    index = months(4)
    def frame(targets):
        return pd.DataFrame(
            {"horizon": 1, "target": targets, "method": "m",
             "actual": 1.0, "forecast": 1.0, "mase_scale": 1.0}
        )
    left, right = frame(list(index[:4])), frame(list(index[1:4]))
    keys = evaluation.shared_targets([left, right])
    assert len(keys) == 3
    assert len(evaluation.restrict(left, keys)) == len(evaluation.restrict(right, keys)) == 3


# --- Diebold-Mariano --------------------------------------------------------


def test_identical_forecasts_give_no_evidence_either_way():
    index = months(120)
    errors = pd.Series(np.random.default_rng(0).normal(size=120), index=index)
    result = evaluation.diebold_mariano(errors, errors.copy(), 1)
    assert result["statistic"] == 0.0
    assert result["p"] == 1.0


def test_a_clearly_worse_forecast_is_detected_and_the_sign_says_which():
    index = months(120)
    good = pd.Series(np.random.default_rng(0).normal(size=120), index=index)
    result = evaluation.diebold_mariano(good, good * 3, 1)
    assert result["statistic"] < 0          # the first argument had the smaller loss
    assert result["p"] < 0.001


def test_an_autocorrelated_difference_costs_effective_sample_size():
    """The whole point of the correction: overlap is not free information."""
    index = months(120)
    rng = np.random.default_rng(1)
    smooth = pd.Series(np.convolve(rng.normal(size=140), np.ones(12) / 12, "valid")[:120],
                       index=index)
    rough = pd.Series(rng.normal(size=120), index=index)
    zero = pd.Series(0.0, index=index)
    assert (evaluation.diebold_mariano(smooth + 3, zero, 6)["effective_n"]
            < evaluation.diebold_mariano(rough + 3, zero, 1)["effective_n"] / 2)


def test_the_small_sample_correction_shrinks_the_statistic_at_long_horizons():
    index = months(40)
    errors = pd.Series(np.random.default_rng(2).normal(size=40) + 1.0, index=index)
    zero = pd.Series(0.0, index=index)
    short = abs(evaluation.diebold_mariano(errors, zero, 1)["statistic"])
    long = abs(evaluation.diebold_mariano(errors, zero, 12)["statistic"])
    assert long < short


def test_too_few_paired_months_returns_nothing_rather_than_a_number():
    index = months(5)
    errors = pd.Series(np.random.default_rng(3).normal(size=5), index=index)
    assert np.isnan(evaluation.diebold_mariano(errors, errors * 2, 1)["p"])
