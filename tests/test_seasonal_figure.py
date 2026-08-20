"""The seasonal split: what the shape is, what it leaves, and over which months."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures
from study import plotstyle as ps


def synthetic(years: int = 12, seed: int = 0) -> pd.Series:
    """A repeating shape whose size varies from year to year without direction."""
    rng = np.random.default_rng(seed)
    months = pd.period_range("2009-01", periods=12 * years, freq="M")
    shape = 40 + 30 * np.sin(2 * np.pi * (months.month - 4) / 12)
    size = np.repeat(rng.uniform(0.4, 1.6, years), 12)
    return pd.Series(20 + shape * size + rng.normal(0, 2.0, len(months)), index=months)


def panels() -> dict[str, pd.DataFrame]:
    return {key: figures.seasonal_parts(synthetic(seed=index))
            for index, (key, _, _) in enumerate(figures.GAS_PANEL)}


# --- what the split is --------------------------------------------------------


def test_the_three_parts_add_back_to_the_measurements():
    """A split that does not reconstitute is not a split."""
    panel = figures.seasonal_parts(synthetic())
    rebuilt = panel["repeating"] + panel["leftover"]
    assert rebuilt.to_numpy() == pytest.approx(panel["observed"].to_numpy())


def test_the_repeating_part_holds_one_shape_for_the_whole_record():
    """The study's benchmark is a fixed month-of-year average, so a shape that
    evolved across the record would answer a question the benchmark does not ask."""
    panel = figures.seasonal_parts(synthetic())
    by_month = panel.groupby(panel.index.month)["repeating"]
    assert (by_month.std().fillna(0) < 1e-9).all()
    assert panel["repeating"].nunique() == 12


def test_the_leftover_is_measured_against_the_shape_rather_than_smoothed():
    """It is what the shape does not account for, month by month."""
    panel = figures.seasonal_parts(synthetic())
    assert abs(panel["leftover"].mean()) < 1e-9
    assert panel["leftover"].std() > 0


def test_the_split_carries_the_amplitude_result_it_exists_to_show():
    panel = figures.seasonal_parts(synthetic())
    swing = panel.attrs["swing"]
    assert len(swing) >= 10
    assert 0.0 < panel.attrs["trend_p"] <= 1.0
    assert 0.0 < panel.attrs["left_share"] < 1.0
    assert 0.0 < panel.attrs["explained"] < 1.0


def test_a_year_missing_its_summer_is_left_out_of_the_amplitude():
    """It would report a swing it never had."""
    series = synthetic()
    clipped = series.drop(series.index[series.index.year == 2012][:6])
    assert 2012 not in figures.seasonal_parts(clipped).attrs["swing"].index
    assert 2012 in figures.seasonal_parts(series).attrs["swing"].index


def test_the_split_runs_over_every_observed_month_of_the_committed_record():
    """The fitting window ends before methane's weakest season, which is half of
    what the amplitude range says."""
    from ingest import paths

    filename, column, _ = figures.GAS_OBSERVED["methane"]
    series = pd.read_csv(paths.processed_dir() / filename)
    series["month"] = pd.PeriodIndex(series["month"], freq="M")
    panel = figures.seasonal_parts(series.set_index("month")[column])
    assert panel.index.max().year == 2021
    assert panel.attrs["swing"].idxmin() == 2021
    assert panel.attrs["swing"].max() / panel.attrs["swing"].min() > 4.4


# --- what is drawn ------------------------------------------------------------


def test_the_gases_are_columns_and_never_share_a_scale():
    """Different units, and one of them crosses zero where the other does not."""
    fig = figures.seasonal_cycle(panels())
    rows = len(figures.SEASONAL_ROWS)
    assert len(fig.axes) == 2 * rows
    for index in range(rows):
        left, right = fig.axes[index], fig.axes[rows + index]
        assert left.get_position().x0 < right.get_position().x0
        assert left.get_position().y0 == pytest.approx(right.get_position().y0)
    ps.plt.close(fig)


def test_every_panel_shares_one_time_axis():
    """A month has to sit in the same place in all six, or the rows cannot be read
    against each other."""
    fig = figures.seasonal_cycle(panels())
    spans = {ax.get_xlim() for ax in fig.axes}
    assert len(spans) == 1
    ps.plt.close(fig)


def test_the_leftover_row_is_the_tallest():
    """It is where the finding is; the row above it is twelve numbers repeated."""
    fig = figures.seasonal_cycle(panels())
    heights = [ax.get_position().height for ax in fig.axes[:len(figures.SEASONAL_ROWS)]]
    assert heights[-1] == max(heights)
    assert heights[-1] > 1.5 * heights[1]
    ps.plt.close(fig)


def test_only_the_leftover_row_carries_a_zero_line():
    fig = figures.seasonal_cycle(panels())
    zeroed = [index for index, ax in enumerate(fig.axes)
              if any(np.allclose(line.get_ydata(), 0.0) for line in ax.lines)]
    assert len(zeroed) == len(figures.GAS_PANEL)
    ps.plt.close(fig)


def test_each_row_is_named_once_rather_than_once_per_column():
    fig = figures.seasonal_cycle(panels())
    said = [text.get_text() for text in fig.texts]
    for name, _ in figures.SEASONAL_ROWS:
        assert said.count(name) == 1
    ps.plt.close(fig)


def test_the_gases_are_named_in_the_bordered_box_with_their_units():
    fig = figures.seasonal_cycle(panels())
    boxed = [note.get_text() for ax in fig.axes for note in ax.texts
             if note.get_bbox_patch() is not None]
    assert len(boxed) == len(figures.GAS_PANEL)
    for gas in boxed:
        assert "m$^{-2}$" in gas
    ps.plt.close(fig)


def test_the_two_marked_years_are_set_lightly():
    """The finding is that the size varies without direction, so these are two
    labeled points in a scattered field, not two events on a quiet background."""
    fig = figures.seasonal_cycle(panels())
    marks = [note for ax in fig.axes for note in ax.texts if "season" in note.get_text()]
    assert len(marks) == 2 * len(figures.GAS_PANEL)
    for mark in marks:
        assert mark.get_fontsize() < ps.ANNOTATION_SIZE
        assert mark.get_style() == "italic"
    ps.plt.close(fig)


# --- what the words carry -----------------------------------------------------


def test_the_description_leads_with_the_share_of_the_spread():
    """Variance share and standard deviation share pull opposite ways, and a
    reader takes whichever arrives first."""
    said = figures.SEASONAL_TEXT.description
    assert said.index("0.54") < said.index("71%")


def test_the_description_says_the_shape_is_not_the_benchmark_s():
    """One is fitted on every observed month; the other is rebuilt inside a fold."""
    said = figures.SEASONAL_TEXT.description
    assert "fitted on every observed month" in said
    assert "rebuilt inside each fold" in said


def test_the_description_reports_both_amplitudes_with_their_trend_tests():
    said = figures.SEASONAL_TEXT.description
    for number in ("33.7", "150.6", "4.5", "0.8", "2.4", "3.0", "0.119", "0.505"):
        assert number in said


def test_the_subtitle_carries_the_finding_the_title_leaves_out():
    """The title names the middle row, which orients; the finding is the bottom."""
    text = figures.SEASONAL_TEXT
    assert "seasonal cycle" in text.title
    assert "nothing in this study predicts" in text.subtitle
    assert text.emphasize == ("nothing in this study predicts",)


def test_the_figure_names_no_method():
    text = figures.SEASONAL_TEXT
    said = " ".join([text.title, text.subtitle, text.description,
                     *[name for name, _ in figures.SEASONAL_ROWS]]).lower()
    for jargon in ("decompos", "stl", "residual", "loess", "detrend", "component"):
        assert jargon not in said
