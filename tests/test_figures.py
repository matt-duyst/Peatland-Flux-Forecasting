"""The water table figure, drawn from synthetic months rather than the dataset."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures, plotstyle as ps


def frames():
    """Twelve reconstruction months, six of them wet, then six fitted months."""
    months = pd.period_range("2000-01", periods=18, freq="M")
    values = np.concatenate([
        np.full(6, 413.0),      # reconstruction, inside
        np.full(6, 413.9),      # reconstruction, above anything fitted
        np.linspace(413.0, 413.4, 6),  # the fit window
    ])
    series = pd.Series(values, index=months, name="wte_m")
    return series, months[12:], months[:12]


def test_months_beyond_the_fitted_range_are_marked_and_counted():
    series, fit, reconstruction = frames()
    fig = figures.water_table_support(series, fit, reconstruction, artifacts=())
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert any("6 months above" in l for l in labels), labels
    ps.plt.close(fig)


def test_an_artifact_month_sets_no_bound_and_is_not_drawn():
    """Excluding a spurious low month narrows the range and tightens the test."""
    series, fit, reconstruction = frames()
    spurious = fit[0]
    series = series.copy()
    series.loc[spurious] = 400.0

    with_it = figures.water_table_support(series, fit, reconstruction, artifacts=())
    without = figures.water_table_support(series, fit, reconstruction, artifacts=(spurious,))
    def lower_bound(fig):
        # The range bounds are the horizontal two-point lines; the window
        # boundary is vertical and must not be mistaken for one.
        flat = [l.get_ydata() for l in fig.axes[0].lines
                if len(l.get_ydata()) == 2 and l.get_ydata()[0] == l.get_ydata()[1]]
        return min(y[0] for y in flat)

    lower_with, lower_without = lower_bound(with_it), lower_bound(without)
    assert lower_with == 400.0 and lower_without > 400.0

    drawn = max(without.axes[0].lines, key=lambda l: len(l.get_ydata())).get_ydata()
    assert np.isnan(drawn).sum() == 1
    ps.plt.close(with_it); ps.plt.close(without)


def test_a_gap_breaks_the_line_rather_than_being_bridged():
    series, fit, reconstruction = frames()
    series = series.drop(series.index[3])
    fig = figures.water_table_support(series, fit, reconstruction)
    # The bound rules are drawn first; the series is the line spanning every month.
    series_line = max(fig.axes[0].lines, key=lambda l: len(l.get_ydata()))
    assert np.isnan(series_line.get_ydata()).sum() == 1
    ps.plt.close(fig)


def test_axes_are_labelled_with_units():
    series, fit, reconstruction = frames()
    fig = figures.water_table_support(series, fit, reconstruction)
    assert "meters" in fig.axes[0].get_ylabel()
    assert fig.axes[0].get_xlabel()
    ps.plt.close(fig)


def test_the_figure_carries_its_own_words():
    assert figures.WATER_TABLE_TEXT.title
    assert figures.WATER_TABLE_TEXT.subtitle != figures.WATER_TABLE_TEXT.title
    body = ps.readme_block(figures.WATER_TABLE_TEXT, "water_table_support")
    # The central term is defined for a reader arriving cold.
    assert body.index("Reconstruction means") < body.index("Each point")
