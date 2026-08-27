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
    # 2024, not 2021: methane is read from the 2025 BASE product, which carries
    # three years the 2022 workbook export stopped short of.
    assert panel.index.max().year == 2024
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


def test_nothing_is_drawn_at_the_right_of_a_panel():
    """The scale bars took three rounds to label and never read: the label had to
    be rotated, and the ratio they existed to show is one sentence of the
    description, stated exactly rather than left to be measured off a rectangle."""
    fig = figures.seasonal_cycle(panels())
    for ax in fig.axes:
        # The series and the zero rule are all that is left; a bar was the only
        # two-point mark ever drawn in axes fractions past the right spine.
        assert not [line for line in ax.lines
                    if len(line.get_xdata()) == 2
                    and line.get_transform() is ps.blended(ax)]
        assert not [note for note in ax.texts if "bar" in note.get_text()]
    assert not [text for text in fig.texts if "bar" in text.get_text()]
    ps.plt.close(fig)


def test_no_year_is_singled_out_on_any_panel():
    """The marks named an amplitude and pointed at a departure, were wrong twice,
    and the range they illustrated is in the description."""
    fig = figures.seasonal_cycle(panels())
    assert not [note for ax in fig.axes for note in ax.texts
                if "season" in note.get_text()]
    ps.plt.close(fig)


def test_every_panel_names_its_unit_on_its_own_axis():
    """A reader on a middle-row panel had nothing on the axis saying what the
    numbers were. Set above the panel instead, the unit read as belonging to the
    row beneath it; rotated at the left is where a reader looks for it, and the
    one place rotation is expected."""
    fig = figures.seasonal_cycle(panels())
    rows = len(figures.SEASONAL_ROWS)
    for column, (_, _, unit) in enumerate(figures.GAS_PANEL):
        for index in range(rows):
            assert fig.axes[column * rows + index].get_ylabel() == unit
    ps.plt.close(fig)


def test_each_row_name_is_written_in_its_own_row_s_ink():
    """It ties the label to the line without six legend boxes repeating six
    labels; the line beneath stays muted so the hierarchy inside the frame holds."""
    from matplotlib.colors import to_rgb

    fig = figures.seasonal_cycle(panels())
    named = {label.partition(" (")[0]: ink for label, _, ink, _ in figures.SEASONAL_ROWS}
    asides = 0
    for text in fig.texts:
        if text.get_text() in named:
            assert to_rgb(text.get_color()) == to_rgb(named[text.get_text()])
        elif text.get_text().startswith("("):
            assert to_rgb(text.get_color()) == to_rgb(ps.MUTED)
            asides += 1
    assert asides == len(figures.SEASONAL_ROWS)
    ps.plt.close(fig)


def test_no_panel_carries_a_legend():
    """One line to a panel, and the row label to its left already names it."""
    fig = figures.seasonal_cycle(panels())
    assert not [ax for ax in fig.axes if ax.get_legend()]
    ps.plt.close(fig)


def test_one_scale_runs_through_a_column_and_height_is_flux():
    """Rows scaled to their own data made three bars of three different heights,
    which is the opposite of what a reader takes from them. Height is now the flux
    a row covers, and the bars come out identical rather than being made to."""
    fig = figures.seasonal_cycle(panels())
    rows = len(figures.SEASONAL_ROWS)
    for column in range(len(figures.GAS_PANEL)):
        scales = []
        for index in range(rows):
            ax = fig.axes[column * rows + index]
            low, high = ax.get_ylim()
            scales.append((high - low) / ax.get_position().height)
        assert scales[0] == pytest.approx(scales[1], rel=1e-6) == pytest.approx(scales[2], rel=1e-6)
    ps.plt.close(fig)


def test_the_middle_row_is_the_shortest_because_it_covers_the_least_flux():
    fig = figures.seasonal_cycle(panels())
    heights = [ax.get_position().height for ax in fig.axes[:len(figures.SEASONAL_ROWS)]]
    assert heights[1] == min(heights)
    ps.plt.close(fig)


def test_only_the_leftover_row_carries_a_zero_line():
    fig = figures.seasonal_cycle(panels())
    zeroed = [index for index, ax in enumerate(fig.axes)
              if any(np.allclose(line.get_ydata(), 0.0) for line in ax.lines)]
    assert len(zeroed) == len(figures.GAS_PANEL)
    ps.plt.close(fig)


def test_each_row_is_named_once_rather_than_once_per_column():
    fig = figures.seasonal_cycle(panels())
    said = " ".join(text.get_text() for text in fig.texts)
    for label, _, _, _ in figures.SEASONAL_ROWS:
        name, _, aside = label.partition(" (")
        assert said.count(name) == 1
        assert said.count(f"({aside}") == 1
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


def test_each_row_is_named_in_the_gutter_on_two_lines_inside_one_frame():
    """The name bold, how the row was built beneath it, and a frame round both.
    On one line they needed a quarter of the canvas; the parentheticals are free,
    since the bold line above them is the wider of the two on every row."""
    from matplotlib.patches import FancyBboxPatch

    fig = figures.seasonal_cycle(panels())
    fig.canvas.draw()
    frames = [art for art in fig.artists if isinstance(art, FancyBboxPatch)]
    assert len(frames) == len(figures.SEASONAL_ROWS)
    names = {label.partition(" (")[0] for label, _, _, _ in figures.SEASONAL_ROWS}
    heads = [text for text in fig.texts if text.get_text() in names]
    assert len(heads) == len(figures.SEASONAL_ROWS)
    # Both lines centered on each other rather than hung from one edge.
    for text in fig.texts:
        if text.get_text() in names or text.get_text().startswith("(each") \
                or text.get_text().startswith("(twelve") or text.get_text().startswith("(the"):
            assert text.get_ha() == "center"
    panel = fig.axes[0].get_window_extent()
    for frame in frames:
        assert frame.get_window_extent().x1 < panel.x0
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
    # An axis label on the bottom row of each column, not figure text. As figure
    # text it sat at a fixed fraction and the balanced block moved out from under
    # it; placed after the balance it landed on the description, because a figure
    # artist is not in the extent the block is balanced against.
    named = [ax for ax in fig.axes if ax.get_xlabel() == figures.SEASONAL_TIME_AXIS]
    assert len(named) == len(figures.GAS_PANEL)
    assert not [text for text in fig.texts
                if text.get_text() == figures.SEASONAL_TIME_AXIS]
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


def test_the_description_gives_one_share_and_not_two():
    """Variance share and standard deviation share pull opposite ways, and a
    reader takes whichever arrives first. The block used to carry both, 74% and
    0.51, which are the same fact on two scales. It now carries the variance
    share alone and states the remainder as a quarter; the spread ratios are in
    the notes."""
    said = figures.SEASONAL_TEXT.description
    assert "74%" in said and "71%" in said
    assert "0.51" not in said and "0.53" not in said


def test_the_fold_caveat_is_recorded_where_it_can_be_checked():
    """One shape is fitted on every observed month; the benchmark is rebuilt
    inside each fold. It is a real distinction and it is not what a reader needs
    while looking, so it moved to the notes with the other precise figures."""
    from pathlib import Path

    said = figures.SEASONAL_TEXT.description
    assert "fitted on every observed month" not in said
    # The notes are hard-wrapped, so a phrase can straddle a newline.
    notes = " ".join(
        (Path(__file__).resolve().parents[1] / "notes" / "study.md").read_text().split())
    assert "fitted on every observed month" in notes
    assert "rebuilt from the months up to the origin" in notes


def test_the_amplitudes_and_their_trend_tests_are_recorded():
    """The description gives the fold change in words and the notes give the
    numbers. Nothing that left the block is unrecorded, which is the failure this
    guards: two of these were stale in the notes and two were absent when the
    block was cut."""
    from pathlib import Path

    said = figures.SEASONAL_TEXT.description
    assert "fourfold" in said and "threefold" in said
    notes = " ".join(
        (Path(__file__).resolve().parents[1] / "notes" / "study.md").read_text().split())
    for number in ("33.7", "150.6", "0.215", "0.505", "74.2%", "71.5%"):
        assert number in notes, f"{number} left the figure and is not in the notes"


def test_no_trend_is_reported_as_undetected_rather_than_absent():
    """At p = 0.215 and 0.505 nothing was detected, which is not the same as
    nothing being there, and fourteen annual points have little power to find a
    small trend."""
    said = figures.SEASONAL_TEXT.description
    assert "neither showing a trend" in said
    assert "neither of them trending" not in said


def test_the_subtitle_claims_only_what_was_tested():
    """"Nothing in this study predicts it" overstates. What is true is narrower,
    and it is not the only bolded clause in any subtitle in the set."""
    text = figures.SEASONAL_TEXT
    assert "seasonal cycle" in text.title
    # The claim moved to the description, and with it the pronoun that made the
    # subtitle ambiguous: "It is where the size of each season lives. Nothing
    # tested here predicted it" left the second "it" readable as the row or as
    # the size of the season, and the finding depended on which.
    assert "Nothing tested here predicted it" not in text.subtitle
    assert "nothing tested here predicted" in text.description
    assert "eight fitted models, four benchmarks and four measured drivers" in text.description
    assert text.emphasize == ()


def test_the_figure_names_no_method():
    text = figures.SEASONAL_TEXT
    said = " ".join([text.title, text.subtitle, text.description,
                     *[name for name, _, _, _ in figures.SEASONAL_ROWS]]).lower()
    for jargon in ("decompos", "stl", "residual", "loess", "detrend", "component"):
        assert jargon not in said
