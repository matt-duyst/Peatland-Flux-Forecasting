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


def annual_frame():
    """Six reconstruction years, two inside support and one partial."""
    years = [1990, 1991, 1992, 2007, 2008, 2009]
    return pd.DataFrame({
        "year": years,
        "n_months": [12, 12, 12, 12, 12, 3],
        "support": ["outside", "inside", "inside", "outside", "outside", "outside"],
        "pct_months_outside": [67.0, 0.0, 0.0, 33.0, 25.0, 33.0],
        "clamped": [17.4, 11.9, 11.2, 7.9, 8.2, 0.8],
        "unclamped": [20.3, 11.9, 11.2, 10.1, 9.3, 1.1],
        "reduced": [10.9, 11.3, 10.6, 7.8, 8.1, 0.8],
    })


def test_a_partial_year_is_not_plotted_beside_full_ones():
    """2009 holds three months; drawn as a year it would read as a collapse."""
    fig = figures.reconstruction_series(annual_frame())
    drawn = fig.axes[0].lines[0].get_xdata()
    assert max(drawn) == figures.LAST_PLOTTED_YEAR
    assert 2009 not in list(drawn)
    ps.plt.close(fig)


def test_the_spread_is_drawn_as_lines_and_never_as_a_band():
    """A band would say the answer lies inside it, which is the reading refused."""
    fig = figures.reconstruction_series(annual_frame())
    ax = fig.axes[0]
    filled = [c for c in ax.collections if type(c).__name__ in
              ("PolyCollection", "FillBetweenPolyCollection")]
    assert not filled, "the sensitivity spread must not be rendered as a filled region"
    assert not ax.patches
    assert len([l for l in ax.lines if l.get_marker() in ("None", "")]) == 3
    ps.plt.close(fig)


def test_the_three_lines_are_achromatic_and_separately_styled():
    fig = figures.reconstruction_series(annual_frame())
    lines = [l for l in fig.axes[0].lines if l.get_marker() in ("None", "")]
    from matplotlib.colors import to_hex
    for line in lines:
        r, g, b = (int(to_hex(line.get_color())[i:i + 2], 16) for i in (1, 3, 5))
        assert r == g == b, f"{to_hex(line.get_color())} is not achromatic"
    # A custom dash tuple reports as "--", so the styles are compared by the
    # dash pattern actually drawn rather than by the style name.
    patterns = {str(getattr(l, "_unscaled_dash_pattern", l.get_linestyle())) for l in lines}
    assert len(patterns) == 3
    ps.plt.close(fig)


def test_the_panel_names_assumptions_rather_than_internal_variants():
    fig = figures.reconstruction_series(annual_frame())
    import re

    raw = " ".join(t.get_text() for t in fig.axes[0].get_legend().get_texts())
    # Terms shared with the subtitle are set bold, so the markup is stripped
    # before comparing against the words a reader actually sees.
    labels = re.sub(r"\$\\bf\{(.*?)\}\$", r"\1", raw)
    for internal in ("clamped", "unclamped", "reduced"):
        assert internal not in labels.lower()
    assert "held flat" in labels and "continued linearly" in labels
    ps.plt.close(fig)


def test_support_is_shown_by_degree_as_well_as_by_verdict():
    """A year 25% outside must not read like one 100% outside."""
    fig = figures.reconstruction_series(annual_frame())
    heights = sorted(round(p.get_height(), 1) for p in fig.axes[1].patches)
    assert 25.0 in heights and 67.0 in heights
    ps.plt.close(fig)


def test_a_year_with_no_months_outside_is_marked_flat_and_in_blue():
    """A measured zero is not a missing bar, and its ink must not contradict itself.

    Flat rather than round, so it reads as a bar of no height rather than as a
    point from another series. Blue rather than orange, because orange means
    outside the fitted range across this set and the mark means none outside;
    these are the same years the panel above marks blue.
    """
    from matplotlib.colors import to_rgba

    fig = figures.reconstruction_series(annual_frame())
    strip = fig.axes[1]
    flat = [line for line in strip.lines if line.get_marker() == "_"]
    assert flat, "the inside years are not marked at all"
    assert len(flat[0].get_xdata()) == 2
    assert to_rgba(flat[0].get_color()) == to_rgba(ps.INSIDE)
    assert to_rgba(flat[0].get_color()) != to_rgba(ps.OUTSIDE)
    assert all(y == 0 for y in flat[0].get_ydata())
    ps.plt.close(fig)


def test_the_strip_names_both_of_its_marks():
    """The hatching and the flat mark are otherwise unexplained."""
    fig = figures.reconstruction_series(annual_frame())
    labels = [t.get_text() for t in fig.axes[1].get_legend().get_texts()]
    assert any("Share of the year outside" in label for label in labels)
    assert any("No months outside" in label for label in labels)
    ps.plt.close(fig)


def test_the_strip_legend_fits_inside_the_frame_without_covering_a_bar():
    """The strip is secondary and must not gain height to carry its own key."""
    fig = figures.reconstruction_series(annual_frame())
    fig.canvas.draw()
    strip = fig.axes[1]
    frame = strip.get_window_extent()
    legend = strip.get_legend().get_window_extent()
    assert legend.y1 <= frame.y1 and legend.y0 >= frame.y0, "the legend leaves the frame"
    box = legend.transformed(strip.transData.inverted())
    under = [bar.get_height() for bar in strip.patches
             if box.x0 <= bar.get_x() + bar.get_width() / 2 <= box.x1]
    assert box.y0 > max(under, default=0.0), "the legend covers a bar"
    ps.plt.close(fig)
