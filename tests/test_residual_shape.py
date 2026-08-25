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


def test_there_are_four_panels_naming_both_shape_and_weighting():
    """A panel lifted out of the figure still says what it is."""
    fig = figures.residual_shape(four_panels())
    drawn = [ax for ax in fig.axes if ax.get_legend() is None]
    assert len(drawn) == 4
    named = {note.get_text() for ax in drawn for note in ax.texts}
    assert named == {name for _, name in figures.SHAPE_PANELS}
    ps.plt.close(fig)


def test_each_panel_is_square_and_carries_the_line_of_equality():
    """Distance from that line is the reading, so it has to sit at 45 degrees."""
    fig = figures.residual_shape(four_panels())
    width_px, height_px = ps.SIZES["quad"]
    for ax in [ax for ax in fig.axes if ax.get_legend() is None]:
        box = ax.get_position()
        assert box.width * width_px == pytest.approx(box.height * height_px, rel=0.01)
        assert ax.get_xlim() == pytest.approx(ax.get_ylim())
    ps.plt.close(fig)


def test_both_axes_of_every_panel_say_the_scale():
    """The log scale is the thing a reader most needs stated: these are errors in
    log flux, so 0.3 is a third rather than a third of a nanomole."""
    fig = figures.residual_shape(four_panels())
    for ax in [ax for ax in fig.axes if ax.get_legend() is None]:
        assert figures.SHAPE_UNIT in ax.get_xlabel()
        assert figures.SHAPE_UNIT in ax.get_ylabel()
        assert figures.SHAPE_EXPECTED in ax.get_xlabel()
        assert figures.SHAPE_OBSERVED in ax.get_ylabel()
    ps.plt.close(fig)


def test_the_key_names_the_points_the_line_and_the_band():
    fig = figures.residual_shape(four_panels())
    keys = [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    assert len(keys) == 1
    labels = [text.get_text() for text in keys[0].get_texts()]
    for entry in figures.SHAPE_KEYS:
        assert entry in labels
    assert sum(label.startswith("$") for label in labels) == 1
    ps.plt.close(fig)


def test_the_panels_carry_no_numbers():
    """At four panels the description carries them."""
    fig = figures.residual_shape(four_panels())
    named = {name for _, name in figures.SHAPE_PANELS}
    for ax in [ax for ax in fig.axes if ax.get_legend() is None]:
        assert not [note for note in ax.texts
                    if note.get_text().strip() and note.get_text() not in named]
    ps.plt.close(fig)


# --- what the words carry -----------------------------------------------------


def test_the_title_names_what_is_plotted_the_site_and_the_span():
    title = figures.SHAPE_TEXT.title
    assert title.startswith("Model error against the shapes it might follow")
    assert "Marcell Bog Lake Peatland" in title
    assert title.endswith("(2009 to 2019)")


def test_the_subtitle_states_the_log_scale_and_what_the_band_covers():
    said = figures.SHAPE_TEXT.subtitle
    assert "log scale" in said
    assert "covers every point at once" in said
    assert "one point outside it is enough" in said


def test_the_description_reports_the_negative_result_rather_than_the_assumption():
    """The estimator assumes Laplace. The model's own error does not carry it,
    and the figure was built to be able to say so."""
    said = figures.SHAPE_TEXT.description
    assert "does not carry the shape the estimator assumes" in said
    assert "difference between two instruments" in said
    assert "a different quantity" in said


def test_the_weighted_row_is_not_read_as_confirming_the_assumption():
    """It looks strongly Laplace and that is an artifact of the weights, which
    span a factor of 554 and turn errors of one size into a heavy-tailed
    mixture. Left unsaid, the row would be read as the opposite of the finding."""
    said = figures.SHAPE_TEXT.description
    assert "554" in said
    assert "errors of one constant size" in said
    assert "11 months escape the Laplace band and 61 the Gaussian" in said


def test_no_term_a_reader_outside_the_study_would_have_to_decode():
    text = figures.SHAPE_TEXT
    said = " ".join([text.title, text.subtitle, text.description]).lower()
    for term in ("quantile", "residual", "heteroscedastic", "kurtosis", "aic",
                 "maximum likelihood", "q-q", "estimator assumption",
                 "leptokurtic", "order statistic"):
        assert term not in said
