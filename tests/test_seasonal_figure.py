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
    for name, _, _, _ in figures.SEASONAL_ROWS:
        assert said.count(name) == 1
    ps.plt.close(fig)


def test_the_gases_are_named_with_their_units_centered_over_the_column():
    """The row names span both columns and cannot carry two units, so the column
    header is where the unit belongs."""
    fig = figures.seasonal_cycle(panels())
    boxed = [note for ax in fig.axes for note in ax.texts
             if note.get_bbox_patch() is not None]
    assert [note.get_text() for note in boxed] == \
        [f"{gas} ({unit})" for _, gas, unit in figures.GAS_PANEL]
    for note in boxed:
        assert note.get_ha() == "center"
        assert note.get_position()[0] == pytest.approx(0.5)
    ps.plt.close(fig)


def test_each_row_is_named_over_itself_in_the_frame_the_gases_use():
    """Held in a left gutter the names needed 517 px for the widest line alone,
    which took a quarter of the canvas from the panels."""
    fig = figures.seasonal_cycle(panels())
    framed = {text.get_text(): text for text in fig.texts
              if text.get_bbox_patch() is not None}
    assert set(framed) == {name for name, _, _, _ in figures.SEASONAL_ROWS}
    for text in framed.values():
        assert text.get_ha() == "left"
    ps.plt.close(fig)


def test_each_row_name_says_how_its_row_was_built():
    """The parentheticals carry what the names cannot: how a monthly value is
    made, that the middle row is one fixed set of twelve, and what the
    subtraction is."""
    names = [name for name, _, _, _ in figures.SEASONAL_ROWS]
    assert "half-hourly readings" in names[0]
    assert "twelve values, repeated every year" in names[1]
    assert "minus that month's average" in names[2]
    for name in names:
        assert "shape" not in name


def test_every_panel_carries_its_own_labeled_time_axis():
    """A row whose ticks are bare asks a reader to carry them down from another."""
    fig = figures.seasonal_cycle(panels())
    for ax in fig.axes:
        assert [label.get_text() for label in ax.get_xticklabels() if label.get_text()]
    said = [text.get_text() for text in fig.texts]
    assert said.count(figures.SEASONAL_TIME_AXIS) == len(figures.GAS_PANEL)
    ps.plt.close(fig)


def test_the_scale_bar_says_what_it_is_beside_the_middle_row():
    """It is the same length in all three rows, and a label at the top read as
    belonging to the top row alone."""
    fig = figures.seasonal_cycle(panels())
    rows = len(figures.SEASONAL_ROWS)
    for column in range(len(figures.GAS_PANEL)):
        labeled = [index for index in range(rows)
                   if any("in every row" in note.get_text()
                          for note in fig.axes[column * rows + index].texts)]
        assert labeled == [1]
    ps.plt.close(fig)


def test_the_scale_bars_hang_from_one_height_in_every_row():
    """Centred, they had to be compared by their middles; hung, by their ends."""
    fig = figures.seasonal_cycle(panels())
    rows = len(figures.SEASONAL_ROWS)
    for column in range(len(figures.GAS_PANEL)):
        tops = []
        for index in range(rows):
            ax = fig.axes[column * rows + index]
            bar = next(line for line in ax.lines
                       if len(line.get_xdata()) == 2
                       and line.get_xdata()[0] == line.get_xdata()[1] > 1.0)
            low, high = ax.get_ylim()
            tops.append((max(bar.get_ydata()) - low) / (high - low))
        assert tops[0] == pytest.approx(tops[1]) == pytest.approx(tops[2])
    ps.plt.close(fig)


def test_each_row_is_drawn_in_its_own_ink_at_its_own_weight():
    """Three kinds of thing: the record, the benchmark fitted from it, and what
    that benchmark leaves. The measurements stay neutral and heaviest."""
    from matplotlib.colors import to_rgb

    fig = figures.seasonal_cycle(panels())
    weights = []
    for index, (_, _, ink, weight) in enumerate(figures.SEASONAL_ROWS):
        series = next(line for line in fig.axes[index].lines
                      if len(line.get_xdata()) > 2)
        assert to_rgb(series.get_color()) == to_rgb(ink)
        weights.append(series.get_linewidth())
    assert weights[0] == max(weights)
    red, green, blue = to_rgb(figures.SEASONAL_ROWS[0][2])
    assert red == pytest.approx(green) == pytest.approx(blue)
    ps.plt.close(fig)


def test_the_benchmark_row_takes_the_hue_that_means_retained():
    """It is the month-of-year average that beat every fitted model, which is what
    blue marks across this set."""
    assert figures.SEASONAL_ROWS[1][2] == ps.INSIDE


def test_no_row_is_drawn_in_the_hue_that_means_discarded():
    """The average year is neither outside anything nor discarded."""
    assert ps.OUTSIDE not in [ink for _, _, ink, _ in figures.SEASONAL_ROWS]


def test_what_the_shape_leaves_is_filled_to_zero_rather_than_drawn_as_a_line():
    """It is a departure from zero, so the distance from zero is what is drawn,
    and the fill gives the row the weight its finding deserves."""
    fig = figures.seasonal_cycle(panels())
    rows = len(figures.SEASONAL_ROWS)
    for column in range(len(figures.GAS_PANEL)):
        for index in range(rows):
            ax = fig.axes[column * rows + index]
            assert bool(ax.collections) == (index == rows - 1)
    ps.plt.close(fig)


def test_every_panel_carries_a_scale_bar_of_one_length_per_column():
    """Each row is scaled to its own data, so without a bar in its own units a
    reader cannot tell that what the average year leaves is as wide as the average
    year itself. Cleveland et al. (1990) put one in every panel for that reason."""
    fig = figures.seasonal_cycle(panels())
    rows = len(figures.SEASONAL_ROWS)
    for column in range(len(figures.GAS_PANEL)):
        lengths = []
        for index in range(rows):
            ax = fig.axes[column * rows + index]
            bars = [line for line in ax.lines
                    if len(line.get_xdata()) == 2
                    and line.get_xdata()[0] == line.get_xdata()[1] > 1.0]
            assert len(bars) == 1, "a panel is missing its scale bar"
            low, high = bars[0].get_ydata()
            lengths.append(high - low)
        assert lengths[0] == pytest.approx(lengths[1]) == pytest.approx(lengths[2])
    ps.plt.close(fig)


def test_the_scale_bar_sits_outside_the_panel_rather_than_over_the_data():
    """Carbon dioxide runs to the right edge of its axis, so a bar inside would
    cross the record's last months."""
    fig = figures.seasonal_cycle(panels())
    for ax in fig.axes:
        bars = [line for line in ax.lines
                if len(line.get_xdata()) == 2
                and line.get_xdata()[0] == line.get_xdata()[1] > 1.0]
        assert bars[0].get_xdata()[0] > 1.0
    ps.plt.close(fig)


def test_the_two_marked_years_are_led_to_their_points_by_arrows():
    """Both labels sat on the line before; they are now in cleared strips, and a
    plain stub did not clearly reach its target."""
    fig = figures.seasonal_cycle(panels())
    marks = [note for ax in fig.axes for note in ax.texts if "season" in note.get_text()]
    for mark in marks:
        assert getattr(mark, "arrow_patch", None) is not None
        assert "->" in str(mark.arrowprops.get("arrowstyle"))
    ps.plt.close(fig)


def test_the_marked_month_is_the_year_s_largest_departure_either_way():
    """Taking the maximum for the strong year and the minimum for the weak one
    assumed a positive flux. Carbon dioxide is an uptake, so both of its marks
    landed on months near zero that meant nothing."""
    panel = figures.seasonal_parts(-synthetic())           # an uptake, sign flipped
    swing = panel.attrs["swing"]
    strongest = panel["leftover"][panel.index.year == swing.idxmax()]
    assert abs(strongest.min()) > abs(strongest.max())      # its extreme is negative
    fig = figures.seasonal_cycle({key: panel for key, _, _ in figures.GAS_PANEL})
    marks = [note for note in fig.axes[2].texts if "strongest" in note.get_text()]
    assert marks and marks[0].xy[1] == pytest.approx(strongest.min())
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


def test_the_subtitle_claims_only_what_was_tested():
    """"Nothing in this study predicts it" overstates. What is true is narrower,
    and it is not the only bolded clause in any subtitle in the set."""
    text = figures.SEASONAL_TEXT
    assert "seasonal cycle" in text.title
    assert "Nothing tested here predicted it" in text.subtitle
    assert "eight fitted models, four benchmarks and four measured drivers" in text.subtitle
    assert text.emphasize == ()


def test_the_figure_names_no_method():
    text = figures.SEASONAL_TEXT
    said = " ".join([text.title, text.subtitle, text.description,
                     *[name for name, _, _, _ in figures.SEASONAL_ROWS]]).lower()
    for jargon in ("decompos", "stl", "residual", "loess", "detrend", "component"):
        assert jargon not in said
