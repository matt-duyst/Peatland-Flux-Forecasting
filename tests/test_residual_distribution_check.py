"""Whether the model's error follows the shape its estimator assumes.

The band is the part that has to be right. A band drawn point by point at the
level wanted for the whole figure is escaped by most samples that follow the
distribution exactly, so these check the global construction rather than trusting
it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures, residuals
from study import plotstyle as ps


def errors(n: int = 60, seed: int = 0, family: str = "laplace") -> pd.Series:
    rng = np.random.default_rng(seed)
    draw = rng.laplace if family == "laplace" else rng.normal
    return pd.Series(draw(0.0, 0.2, n))


def four_panels(n: int = 60) -> dict[tuple[str, str], pd.DataFrame]:
    level = residuals.local_level(n)
    return {(treatment, family): residuals.quantile_comparison(
                errors(n, seed=index, family="laplace"), family, level=level)
            for index, treatment in enumerate(("weighted", "unweighted"))
            for family in residuals.FAMILIES}


# --- the band -----------------------------------------------------------------


def test_a_pointwise_band_would_be_escaped_by_most_correct_samples():
    """The reason the band is not drawn point by point. At 115 months, bounds
    each holding 95% of their own order statistic are escaped somewhere by more
    than half of the samples that follow the distribution exactly."""
    from scipy import stats

    n = 115
    k = np.arange(1, n + 1)
    naive = 1.0 - residuals._all_inside(
        stats.beta.ppf(0.025, k, n - k + 1), stats.beta.ppf(0.975, k, n - k + 1), n)
    assert naive > 0.5


def test_the_band_holds_every_point_at_the_level_asked_for():
    """Equal local levels: each point is tested at whatever level makes the
    chance of any point escaping the level wanted for the figure."""
    from scipy import stats

    for n in (20, 60):
        level = residuals.local_level(n, overall=0.05)
        k = np.arange(1, n + 1)
        achieved = 1.0 - residuals._all_inside(
            stats.beta.ppf(level / 2, k, n - k + 1),
            stats.beta.ppf(1 - level / 2, k, n - k + 1), n)
        assert achieved == pytest.approx(0.05, abs=2e-4)
        assert level < 0.05          # every point is held tighter than the whole


def test_the_band_is_computed_rather_than_simulated():
    """The study has one stochastic step and it is a seeded bootstrap elsewhere.
    Repeating the solve has to give the same number to the last digit."""
    assert residuals.local_level(30) == residuals.local_level(30)


def test_the_exact_band_agrees_with_counting_how_often_a_sample_escapes():
    """The recursion is checked against the thing it computes."""
    from scipy import stats

    n, level = 25, 0.01
    k = np.arange(1, n + 1)
    low = stats.beta.ppf(level / 2, k, n - k + 1)
    high = stats.beta.ppf(1 - level / 2, k, n - k + 1)
    exact = residuals._all_inside(low, high, n)
    draws = np.sort(np.random.default_rng(20110801).random((30000, n)), axis=1)
    simulated = (~((draws < low) | (draws > high)).any(axis=1)).mean()
    assert exact == pytest.approx(simulated, abs=0.01)


def test_every_point_of_a_well_behaved_sample_stays_inside():
    frame = residuals.quantile_comparison(errors(80, seed=3), "Laplace")
    assert (frame["observed"] >= frame["lowest"]).all()
    assert (frame["observed"] <= frame["highest"]).all()


# --- the comparison -----------------------------------------------------------


def test_the_gap_is_positive_when_laplace_is_the_better_shape():
    """Signed the same way the ingestion layer signs its analyzer comparison, so
    the two can be read side by side."""
    heavy = residuals.distribution_comparison(errors(400, seed=1, family="laplace"))
    light = residuals.distribution_comparison(errors(400, seed=1, family="normal"))
    assert heavy["delta_aic"] > 0
    assert light["delta_aic"] < 0


def test_each_shape_is_fitted_to_the_errors_by_maximum_likelihood():
    """Which is why the reference is the line of equality and not a fitted one:
    the shape is already centered and scaled on these errors."""
    values = errors(200, seed=2)
    frame = residuals.quantile_comparison(values, "Laplace")
    assert frame["expected"].median() == pytest.approx(values.median(), abs=0.02)
    assert len(frame) == len(values)
    assert (frame["observed"].to_numpy() == np.sort(values.to_numpy())).all()


# --- what is drawn ------------------------------------------------------------


def test_there_are_four_panels_naming_both_distribution_and_weighting():
    """A panel lifted out of the figure still says what it is."""
    fig = figures.residual_distribution_check(four_panels())
    drawn = [ax for ax in fig.axes if ax.get_legend() is None]
    assert len(drawn) == 4
    named = {note.get_text() for ax in drawn for note in ax.texts}
    assert named == {name for _, name in figures.DISTRIBUTION_PANELS}
    ps.plt.close(fig)


def test_each_panel_is_square_and_carries_the_line_of_equality():
    """Distance from that line is the reading, so it has to sit at 45 degrees."""
    fig = figures.residual_distribution_check(four_panels())
    width_px, height_px = ps.SIZES["quad"]
    for ax in [ax for ax in fig.axes if ax.get_legend() is None]:
        box = ax.get_position()
        assert box.width * width_px == pytest.approx(box.height * height_px, rel=0.01)
        assert ax.get_xlim() == pytest.approx(ax.get_ylim())
    ps.plt.close(fig)


def test_both_axes_of_every_panel_say_the_scale():
    """The log scale is the thing a reader most needs stated: these are errors in
    log flux, so 0.3 is a third rather than a third of a nanomole."""
    fig = figures.residual_distribution_check(four_panels())
    for ax in [ax for ax in fig.axes if ax.get_legend() is None]:
        assert figures.DISTRIBUTION_UNIT in ax.get_xlabel()
        assert figures.DISTRIBUTION_UNIT in ax.get_ylabel()
        assert figures.DISTRIBUTION_EXPECTED in ax.get_xlabel()
        assert figures.DISTRIBUTION_OBSERVED in ax.get_ylabel()
    ps.plt.close(fig)


def test_the_key_names_the_points_the_line_and_the_band():
    fig = figures.residual_distribution_check(four_panels())
    keys = [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    assert len(keys) == 1
    labels = [text.get_text() for text in keys[0].get_texts()]
    for entry in figures.DISTRIBUTION_KEYS:
        assert entry in labels
    assert sum(label.startswith("$") for label in labels) == 1
    ps.plt.close(fig)


def test_the_panels_carry_no_numbers():
    """At four panels the description carries them."""
    fig = figures.residual_distribution_check(four_panels())
    named = {name for _, name in figures.DISTRIBUTION_PANELS}
    for ax in [ax for ax in fig.axes if ax.get_legend() is None]:
        assert not [note for note in ax.texts
                    if note.get_text().strip() and note.get_text() not in named]
    ps.plt.close(fig)


# --- what the words carry -----------------------------------------------------


def test_the_title_names_this_a_diagnostic():
    """It checks an assumption and reports a null. Earlier titles ("Model error
    against the shapes it might follow", "Whether the model's errors follow the
    distribution its estimator assumes") implied a finding it does not carry."""
    title = figures.DISTRIBUTION_TEXT.title
    assert title.startswith("Diagnostic check on the model's errors")
    assert "Marcell Bog Lake Peatland" in title
    assert title.endswith("(2009 to 2019)")


def test_nothing_the_figure_says_calls_a_distribution_a_shape():
    """"Shape" was doing the work of a word that already exists, and a reader
    could not tell whether it meant a curve, a pattern or a distribution."""
    text = figures.DISTRIBUTION_TEXT
    said = " ".join([text.title, text.subtitle, text.description,
                     *figures.DISTRIBUTION_KEYS,
                     figures.DISTRIBUTION_EXPECTED,
                     figures.DISTRIBUTION_OBSERVED]).lower()
    assert "shape" not in said


def test_the_axes_take_the_names_a_quantile_plot_carries():
    """Short, because the subtitle now says what they are in full."""
    assert figures.DISTRIBUTION_EXPECTED == "Theoretical quantiles"
    assert figures.DISTRIBUTION_OBSERVED == "Sample quantiles"


def test_the_key_names_the_line_without_explaining_it():
    """The subtitle defines the 1:1 line, so a trailing clause here repeats it."""
    assert figures.DISTRIBUTION_KEYS[1] == "The 1:1 line"
    assert figures.DISTRIBUTION_KEYS[2].startswith("95% band")


def test_the_subtitle_says_what_kind_of_plot_this_is_before_anything_else():
    """A reader who has not met one has no way to work out what pairing sorted
    errors with predicted values is for."""
    said = figures.DISTRIBUTION_TEXT.subtitle
    assert said.startswith("This is a quantile-quantile plot, which compares the "
                           "errors the model made against the errors a named "
                           "distribution predicts.")
    assert "sorted smallest to largest" in said
    assert "log scale, so 0.3 means the prediction was out by about a third" in said
    assert "Points falling on the 1:1 line are errors matching the distribution" in said


def test_the_subtitle_explains_what_weighting_means():
    """It was a parenthesis that named the fit rather than saying what it does."""
    said = figures.DISTRIBUTION_TEXT.subtitle
    assert ("weighted fit counts a month resting on many measurements more "
            "heavily than one resting on few") in said
    assert "runs both weighted and unweighted throughout" in said


def test_the_subtitle_says_the_band_is_global_and_what_escaping_it_means():
    said = figures.DISTRIBUTION_TEXT.subtitle
    assert "covers all 115 points at once" in said
    assert "holds 95 percent of the time when the distribution is correct" in said
    assert "a single point outside it is enough" in said


def test_the_description_carries_no_number_a_reader_cannot_check():
    """The counts, the gap and the factor are precise and none of them can be
    read off a panel, so they are in the notes."""
    said = figures.DISTRIBUTION_TEXT.description
    for moved in ("554", "96", "0.31", "11 months", "61", "AIC", "factor of"):
        assert moved not in said


def test_the_description_says_why_the_estimator_was_chosen_before_testing_it():
    """A null result on an assumption means nothing to a reader who does not know
    the assumption was load-bearing."""
    said = figures.DISTRIBUTION_TEXT.description
    assert said.startswith("Fitting by least absolute deviations is optimal when "
                           "errors follow a Laplace distribution, which is why "
                           "this study chose it.")
    assert "equally consistent with Laplace and with Gaussian" in said
    assert "not supported by the model's own residuals" in said


def test_the_description_names_the_conflation():
    """The published result is about two instruments compared against each other;
    the assumption is about a fitted model's error."""
    said = figures.DISTRIBUTION_TEXT.description
    assert "comparing two instruments against each other" in said
    assert "a different quantity" in said


def test_the_description_bounds_the_null_result():
    """Without this a reader is left working out what a failed assumption breaks.
    The estimator stays robust and the intervals never used the distribution."""
    said = figures.DISTRIBUTION_TEXT.description
    assert "remains robust either way" in said
    assert "intervals are empirical rather than distributional" in said
    assert "nothing downstream changes" in said


def test_no_term_a_reader_outside_the_study_would_have_to_decode():
    """Study vocabulary, not standard statistics: this figure is a quantile plot
    and is allowed to say so."""
    text = figures.DISTRIBUTION_TEXT
    said = " ".join([text.title, text.subtitle, text.description]).lower()
    for term in ("boruta", "fold", "survival", "screening", "covariate",
                 "heteroscedastic", "kurtosis", "leptokurtic", "order statistic",
                 "maximum likelihood"):
        assert term not in said
