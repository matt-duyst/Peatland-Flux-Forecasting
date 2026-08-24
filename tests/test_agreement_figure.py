"""Prediction error by year: what each panel holds, which way the subtraction
runs, and what may not be inferred."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_hex

from study import figures
from study import plotstyle as ps

METHODS = ("ordinary least squares", "ridge", "random forest", "gradient boosting")


def synthetic(months: int = 48, seed: int = 0) -> dict[str, pd.DataFrame]:
    """Scored forecasts shaped like the real ones: two fitted families and the
    benchmarks, every method scoring every month at every horizon."""
    rng = np.random.default_rng(seed)
    targets = pd.period_range("2015-01", periods=months, freq="M")
    actual = pd.Series(40 + 25 * np.sin(2 * np.pi * targets.month / 12)
                       + rng.normal(0, 6, months), index=targets)
    frames = {}
    for family in ("autoregressive", "exogenous", "benchmarks"):
        methods = METHODS if family != "benchmarks" else ("climatology", "naive")
        rows = []
        for horizon in (1, 3):
            for method in methods:
                for target in targets:
                    rows.append({"origin": target - horizon, "target": target,
                                 "horizon": horizon, "method": method,
                                 "actual": float(actual[target]),
                                 "forecast": float(actual[target]) + rng.normal(0, 5),
                                 "error": 0.0, "mase_scale": 1.0})
        frames[family] = pd.DataFrame(rows)
    return frames


def panels() -> dict[str, pd.DataFrame]:
    return {key: figures.agreement_panel(synthetic(seed=index))
            for index, (key, _, _) in enumerate(figures.GAS_PANEL)}


def drawn_years(frame) -> list[int]:
    """The years that earn a column: those with enough scored months. A year
    below the threshold keeps its months in the grey behind every panel."""
    counts = frame.index.year.value_counts()
    return sorted(int(year) for year, n in counts.items()
                  if n >= figures.YEAR_MIN_MONTHS)


def year_panels(fig):
    """Every year panel, in the order they were added. The key has an axes of its
    own and stands among them rather than after them, since it is placed inside
    the row it borrows its empty columns from."""
    return [ax for ax in fig.axes if ax.get_legend() is None]


# --- what the panel is built from ---------------------------------------------


def test_the_range_spans_every_fitted_method_and_names_none():
    """The study's result is that they do not separate, and a panel that let a
    reader pick one out would invite the ranking it denies."""
    panel = figures.agreement_panel(synthetic())
    assert (panel["lowest"] <= panel["middle"]).all()
    assert (panel["middle"] <= panel["highest"]).all()
    assert set(panel.columns) == {"measured", "lowest", "highest", "middle", "seasonal"}


def test_the_range_spans_all_eight_predictions_and_not_four_averages():
    """The two families run the same four method names. Pivoting on the name
    alone averages each method's two predictions and leaves a range over four
    numbers where the figure says eight, which understated the bar by a median
    factor of 1.57 on methane and halved the bracketing share."""
    frames = synthetic()
    panel = figures.agreement_panel(frames)

    # Every month really does carry eight predictions to span.
    fitted = pd.concat([frames[family] for family in ("autoregressive", "exogenous")])
    fitted = fitted[fitted["horizon"] == figures.AGREEMENT_HORIZON]
    assert set(fitted.groupby("target").size()) == {8}
    assert fitted["method"].nunique() == 4          # the same four names, twice

    # The drawn range reaches the extremes of all eight, not of four averages.
    reach = fitted.groupby("target")["forecast"].agg(["min", "max"])
    assert panel["lowest"].to_numpy() == pytest.approx(reach["min"].to_numpy())
    assert panel["highest"].to_numpy() == pytest.approx(reach["max"].to_numpy())


def test_only_the_months_every_method_scored_are_drawn():
    """Scoring each method on whatever months it reached would advantage the one
    asked the easiest question."""
    frames = synthetic()
    frames["exogenous"] = frames["exogenous"][
        frames["exogenous"]["target"] > pd.Period("2015-06", freq="M")]
    panel = figures.agreement_panel(frames)
    assert panel.index.min() == pd.Period("2015-07", freq="M")


def test_one_horizon_is_drawn_and_it_is_the_nearest():
    """The horizon most favorable to the fitted methods, so falling short of the
    seasonal average there says more than doing so a year out."""
    assert figures.AGREEMENT_HORIZON == 1
    panel = figures.agreement_panel(synthetic())
    assert len(panel) == 48


def test_every_number_is_a_property_of_the_whole_cloud():
    panel = figures.agreement_panel(synthetic())
    assert panel.attrs["mean_miss"] > 0
    assert panel.attrs["root_mean_square"] >= panel.attrs["mean_miss"]
    assert 0.0 <= panel.attrs["brackets"] <= 1.0
    assert 0.0 <= panel.attrs["same_way"] <= 1.0
    assert "coefficient of determination" not in panel.attrs


def test_the_panel_carries_both_ways_the_errors_could_be_arranged():
    """The residual panel asks two questions of the same cloud and they have
    different answers, so both have to be measured rather than one standing in
    for the other: whether the errors tilt, and whether they widen."""
    panel = figures.agreement_panel(synthetic())
    assert "tilt" in panel.attrs and "tilt_p_value" in panel.attrs
    assert panel.attrs["miss_smallest_third"] > 0
    assert panel.attrs["miss_largest_third"] > 0
    assert len(panel.attrs["relative_miss"]) == 3


def test_each_year_is_scored_against_months_of_its_own_size():
    """A raw yearly miss cannot separate a year that was predicted badly from one
    that simply held large months, because the miss grows with the size of the
    month. Dividing by what months of that size are missed by across the record
    does, and that ratio is the figure's central claim."""
    panel = figures.agreement_panel(synthetic())
    ratios = panel.attrs["year_ratio"]
    assert set(ratios) == set(panel.index.year.unique())
    assert all(value > 0 for value in ratios.values())


def test_the_seasonal_average_is_the_only_benchmark_kept():
    """It is the one that beats the fitted methods; the other three are on the
    forecast comparison."""
    panel = figures.agreement_panel(synthetic())
    assert panel["seasonal"].notna().all()



# --- what is drawn ------------------------------------------------------------


def test_the_error_is_the_measurement_minus_the_prediction():
    """The convention the axis name and the subtitle both state. Drawn the other
    way round every reading of the panel inverts, so it is checked against the
    panel it is drawn from rather than trusted to the labels."""
    built = figures.agreement_panel(synthetic())
    errors = figures.agreement_errors(built)

    def same(drawn: str, taken_from: str) -> None:
        assert errors[drawn].to_numpy() == pytest.approx(
            (built["measured"] - built[taken_from]).to_numpy())

    same("middle", "middle")
    same("seasonal", "seasonal")
    # The bar's ends swap: the highest prediction is the lowest error.
    same("lowest", "highest")
    same("highest", "lowest")
    assert (errors["lowest"] <= errors["highest"]).all()


def test_a_month_predicted_too_low_is_drawn_above_the_zero_line():
    """Which side of zero a point falls on is the whole reading of the panel."""
    built = figures.agreement_panel(synthetic())
    errors = figures.agreement_errors(built)
    under = built["middle"] < built["measured"]
    assert (errors["middle"][under] > 0).all()
    assert (errors["middle"][~under] <= 0).all()


def test_there_is_one_panel_per_evaluated_year_per_gas():
    """A panel per year is the whole device: six years told apart by hue would
    overlap into one cloud, which is what the pooled builds showed."""
    built = panels()
    fig = figures.prediction_error_by_year(built)
    expected = sum(len(drawn_years(frame)) for frame in built.values())
    assert len(year_panels(fig)) == expected
    ps.plt.close(fig)


def test_a_year_too_thin_to_show_anything_loses_its_column_not_its_months():
    """2020 holds one scored month on each gas, because the drivers the fitted
    methods need stop at the end of 2019. A column carrying a single point shows
    nothing about the year and costs its width in every row. It is dropped from
    the background as well, so the span the title gives is the span of what is
    drawn."""
    built = panels()
    thin = max(frame.index.year.max() for frame in built.values())
    for key, frame in built.items():
        one = frame.index[frame.index.year == thin][:1]
        built[key] = frame[(frame.index.year != thin) | frame.index.isin(one)]
        assert (built[key].index.year == thin).sum() == 1

    fig = figures.prediction_error_by_year(built)
    axes = year_panels(fig)
    assert str(thin) not in {ax.get_title() for ax in axes}
    assert len(axes) == sum(len(drawn_years(frame)) for frame in built.values())

    # Its month is gone from the background too, so nothing drawn falls outside
    # the years the columns name.
    first = axes[0]
    behind = next(line for line in first.lines if line.get_marker() == "o"
                  and round(line.get_markersize(), 1) == figures.YEAR_CONTEXT_SIZE)
    front = next(line for line in first.lines if line.get_marker() == "o"
                 and round(line.get_markersize(), 1) == figures.YEAR_FOREGROUND_SIZE)
    key = figures.GAS_PANEL[0][0]
    drawn = len(behind.get_xdata()) + len(front.get_xdata())
    assert drawn == len(built[key]) - 1
    assert drawn == sum(n for year, n in built[key].index.year.value_counts().items()
                        if year != thin)
    ps.plt.close(fig)


def test_a_year_with_no_forecasts_gets_nothing_drawn_in_its_column():
    """A panel with axes and grey context but no year in it reads as a year that
    was forecast and missed everywhere. A note standing where the other columns
    carry year labels reads as a third kind of mark. Nothing is drawn, and that
    methane starts late is a fact about the record, so it is in the description."""
    built = panels()
    key = figures.GAS_PANEL[0][0]
    built[key] = built[key][built[key].index.year > built[key].index.year.min()]
    fig = figures.prediction_error_by_year(built)
    expected = sum(len(drawn_years(frame)) for frame in built.values())
    assert len(year_panels(fig)) == expected
    said = " ".join(note.get_text() for note in fig.texts).lower()
    assert "no forecasts" not in said
    ps.plt.close(fig)


def test_every_panel_in_both_rows_carries_its_year():
    """The rows do line up by year. Unlabeled, a reader has no way of knowing
    that and will assume they do not, which is what a row of unlabeled panels
    under a labeled one invites."""
    built = panels()
    fig = figures.prediction_error_by_year(built)
    axes = year_panels(fig)
    start = 0
    for key, _, _ in figures.GAS_PANEL:
        years = drawn_years(built[key])
        titles = [ax.get_title() for ax in axes[start:start + len(years)]]
        assert titles == [str(year) for year in years]
        start += len(years)

    # And the columns really do align: a year drawn in both rows is at one x.
    placed = {}
    fig.canvas.draw()
    start = 0
    for key, _, _ in figures.GAS_PANEL:
        years = drawn_years(built[key])
        for offset, year in enumerate(years):
            box = axes[start + offset].get_window_extent()
            placed.setdefault(year, set()).add(round(box.x0, 1))
        start += len(years)
    assert all(len(edges) == 1 for edges in placed.values())
    ps.plt.close(fig)


def test_each_row_is_named_by_its_gas_in_the_framed_treatment():
    """The treatment the gas labels take across this set. Plain rotated text in
    the gutter did not match it and did not read as a row heading."""
    fig = figures.prediction_error_by_year(panels())
    named = {gas for _, gas, _ in figures.GAS_PANEL}
    framed = [note for note in fig.texts
              if note.get_text() in named and note.get_bbox_patch() is not None]
    assert len(framed) == len(figures.GAS_PANEL)
    ps.plt.close(fig)


def test_every_panel_in_a_row_shares_its_axes():
    """Shared axes are the point of small multiples: a year that sits low has to
    be low against the other panels rather than against its own."""
    built = panels()
    fig = figures.prediction_error_by_year(built)
    axes = year_panels(fig)
    start = 0
    for key, _, _ in figures.GAS_PANEL:
        count = len(drawn_years(built[key]))
        row = axes[start:start + count]
        assert len({tuple(np.round(ax.get_xlim(), 9)) for ax in row}) == 1
        assert len({tuple(np.round(ax.get_ylim(), 9)) for ax in row}) == 1
        low, high = row[0].get_ylim()
        assert low == pytest.approx(-high)
        start += count
    # The two gases are in different units and cannot share one scale.
    assert axes[0].get_ylim() != axes[-1].get_ylim()
    ps.plt.close(fig)


def test_each_panel_draws_its_own_year_over_every_other_year():
    """The background-context device: each panel shows one year against the whole
    record, so a reader sees where a year sits without a callout naming it."""
    from matplotlib.colors import to_rgb

    built = panels()
    fig = figures.prediction_error_by_year(built)
    axes = year_panels(fig)
    start = 0
    for key, _, _ in figures.GAS_PANEL:
        frame = built[key]
        years = sorted(frame.index.year.unique())
        for offset, year in enumerate(years):
            ax = axes[start + offset]
            drawn = {round(line.get_markersize(), 2): line
                     for line in ax.lines if line.get_marker() == "o"}
            assert len(drawn) == 2
            front = drawn[figures.YEAR_FOREGROUND_SIZE]
            behind = drawn[figures.YEAR_CONTEXT_SIZE]
            chosen = int((frame.index.year == year).sum())
            assert len(front.get_xdata()) == chosen
            assert len(behind.get_xdata()) == len(frame) - chosen
            assert to_rgb(front.get_markerfacecolor()) == to_rgb(ps.FITTED)
            assert to_rgb(behind.get_markerfacecolor()) == to_rgb(figures.YEAR_CONTEXT)
            assert front.get_zorder() > behind.get_zorder()
        start += len(years)
    ps.plt.close(fig)


def test_a_month_is_one_point_rather_than_a_segment():
    """At this panel size the background is a hundred and forty months in every
    panel, and drawn as segments it fills the panel and buries the year in it.
    What the segments carried is a pooled statement about method agreement, which
    the description makes in numbers."""
    fig = figures.prediction_error_by_year(panels())
    for ax in year_panels(fig):
        assert not ax.collections            # no vlines
    ps.plt.close(fig)


def test_the_seasonal_average_is_not_drawn_on_the_panels():
    """A third mark type at this size doubles the foreground ink where the year
    signal has to be legible, and the comparison it carries is pooled rather than
    year-level, so it is a number in the description instead."""
    fig = figures.prediction_error_by_year(panels())
    for ax in year_panels(fig):
        assert not [line for line in ax.lines if line.get_marker() == "_"]
    ps.plt.close(fig)


def test_every_panel_carries_a_zero_line():
    """It is the reference every panel is read against."""
    fig = figures.prediction_error_by_year(panels())
    for ax in year_panels(fig):
        flat = [line for line in ax.lines
                if len(line.get_ydata()) == 2 and not any(line.get_ydata())]
        assert len(flat) == 1
        assert flat[0].get_linestyle() != "-"
    ps.plt.close(fig)


def test_the_panels_carry_no_numbers_at_all():
    """At this size a number in a panel competes with the points. The description
    carries them."""
    fig = figures.prediction_error_by_year(panels())
    for ax in year_panels(fig):
        assert not [note for note in ax.texts if note.get_text().strip()]
    ps.plt.close(fig)


def test_no_method_is_identifiable_anywhere():
    fig = figures.prediction_error_by_year(panels())
    drawn = " ".join(note.get_text() for note in fig.texts).lower()
    drawn += " ".join(note.get_text() for ax in fig.axes for note in ax.texts).lower()
    key = " ".join(figures.AGREEMENT_KEYS).lower()
    for method in METHODS + ("ridge", "forest", "boosting"):
        assert method not in drawn and method not in key
    ps.plt.close(fig)


# --- the key ------------------------------------------------------------------


def test_the_key_names_every_point_and_the_line_they_are_read_against():
    """A reader meeting green and grey points with nothing to read them by has to
    go to the subtitle, and a figure that must be read before it can be looked at
    has failed. The zero line is named too: it is the reference the whole figure
    is read against."""
    fig = figures.prediction_error_by_year(panels())
    keys = [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    assert len(keys) == 1
    labels = [text.get_text() for text in keys[0].get_texts()]
    for entry in figures.AGREEMENT_KEYS:
        assert entry in labels
    assert len(figures.AGREEMENT_KEYS) == 3
    assert "Zero error" in figures.AGREEMENT_KEYS[2]
    assert keys[0].axes not in year_panels(fig)          # clear of the data
    ps.plt.close(fig)


def test_the_key_heading_reads_as_a_label_and_is_centered_over_its_column():
    """One heading over all three entries. It was split across two columns for a
    build, which put the zero line on its own away from the two kinds of point:
    a division a reader cannot see on the panel and does not need."""
    fig = figures.prediction_error_by_year(panels())
    fig.canvas.draw()
    legend = next(ax.get_legend() for ax in fig.axes if ax.get_legend())
    texts = legend.get_texts()
    assert [text.get_text() for text in texts] == [
        r"$\bf{What\ each\ mark\ shows}$", *figures.AGREEMENT_KEYS]

    heading, entries = texts[0], texts[1:]
    boxes = [text.get_window_extent() for text in entries]
    middle = (min(box.x0 for box in boxes) + max(box.x1 for box in boxes)) / 2
    box = heading.get_window_extent()
    centered = abs((box.x0 + box.x1) / 2 - middle)
    # Nearer the middle of its column than the left edge it started from.
    assert centered < abs(box.x0 - min(b.x0 for b in boxes))
    ps.plt.close(fig)


def test_the_zero_line_entry_parenthesizes_its_gloss():
    """A comma made the entry read as two things named rather than one thing and
    what it means."""
    entry = figures.AGREEMENT_KEYS[2]
    assert entry == "Zero error (where a prediction matched the measurement)"


# --- what the words carry -----------------------------------------------------


def test_each_subtitle_sentence_does_one_job():
    """It carried five things in three sentences. One sentence each now, and
    methane's start date is not something a reader needs before looking at a
    panel, so it moved to the description."""
    said = figures.AGREEMENT_TEXT.subtitle
    sentences = [s.strip() for s in said.split(". ") if s.strip()]
    assert max(len(s) for s in sentences) < 160
    assert sentences[0] == "Each panel is one evaluated year"
    assert "sixty months" not in said


def test_the_subtitle_defines_prediction_error_rather_than_assuming_it():
    """The title names it and nothing said what it was. A reader meeting an axis
    called Error has to be told what it is the error of."""
    said = figures.AGREEMENT_TEXT.subtitle
    assert "Prediction error is how far a prediction fell from what was measured" in said
    assert "measurement minus the prediction" in said
    assert "above the zero line was predicted too low" in said


def test_the_subtitle_says_why_the_two_gases_run_opposite_ways():
    """Nothing in this figure set said why one axis sits below zero and the other
    above. A reader without it has no way to know that is the ecosystem doing two
    different things rather than a convention of the plot."""
    said = figures.AGREEMENT_TEXT.subtitle
    assert "Carbon dioxide runs negative" in said
    assert "takes up more carbon than it releases" in said
    assert "methane runs positive because peatlands emit it" in said


def test_the_description_is_short_enough_to_leave_the_panels_room():
    """Six lines of text under twelve small panels put the words over more of the
    canvas than the data. Everything precise that a reader cannot check against a
    panel went to the notes."""
    said = figures.AGREEMENT_TEXT.description
    sentences = [s.strip() for s in said.split(". ") if s.strip()]
    assert len(sentences) <= 3
    assert len(said) < 400


def test_the_description_keeps_only_what_can_be_read_off_the_panels():
    """What is left is what a reader needs while looking: that the panels are
    alike, and that methane's 2015 differs in which months it holds."""
    said = figures.AGREEMENT_TEXT.description
    # What the alikeness means, rather than only that the panels look alike.
    assert said.startswith("Across every evaluated year the methods fail in much "
                           "the same way")
    assert "regardless of which year they are predicting" in said
    assert "The one exception is methane in 2015" in said
    assert "which months it contains rather than how they were predicted" in said
    assert "lower half of the axis" in said
    # Every precise figure moved out: none of them is checkable against a panel.
    for moved in ("16.5", "9.8", "1.7 times", "8.3", "13.3", "0.21", "0.28",
                  "56%", "16%", "81%", "87%", "January 2020", "sixty months",
                  "2020"):
        assert moved not in said


def test_no_coefficient_of_determination_appears():
    """It inflates on a strongly seasonal series: predicting the seasonal mean
    alone would score well while adding nothing."""
    text = figures.AGREEMENT_TEXT
    said = " ".join([text.title, text.subtitle, text.description]).lower()
    for term in ("r2", "r²", "coefficient of determination", "variance explained"):
        assert term not in said


def test_no_under_specification_is_claimed_anywhere_in_the_words():
    """Spread growing with magnitude and a patterned mean are different
    diagnostics. An under-specified model shows as a slope or a curve in the
    residuals, and the tilt is flat on both gases."""
    text = figures.AGREEMENT_TEXT
    said = " ".join([text.title, text.subtitle, text.description]).lower()
    for term in ("under-specified", "underspecified", "missing variable",
                 "missing whatever"):
        assert term not in said


def test_averaging_the_families_would_shrink_the_bar_and_the_bracketing_share():
    """What the pivot bug did, held as a test so the shares quoted in the
    description cannot drift back."""
    frames = synthetic()
    panel = figures.agreement_panel(frames)

    fitted = pd.concat([frames[family] for family in ("autoregressive", "exogenous")])
    fitted = fitted[fitted["horizon"] == figures.AGREEMENT_HORIZON]
    collapsed = fitted.pivot_table(index="target", columns="method", values="forecast")
    assert collapsed.shape[1] == 4                  # what the mistake leaves

    drawn = (panel["highest"] - panel["lowest"]).median()
    averaged = (collapsed.max(axis=1) - collapsed.min(axis=1)).median()
    assert drawn > averaged

    measured = panel["measured"]
    shrunk = ((measured >= collapsed.min(axis=1))
              & (measured <= collapsed.max(axis=1))).mean()
    assert panel.attrs["brackets"] > shrunk


def test_the_key_falls_back_to_a_band_when_no_row_leaves_it_columns():
    """Methane happens to start two years after carbon dioxide, which is what
    leaves the gap the key stands in. A figure whose key existed only because of
    that would lose it the moment the record changed."""
    built = panels()
    years = {key: drawn_years(frame) for key, frame in built.items()}
    assert len({tuple(v) for v in years.values()}) == 1      # no gap in either row
    fig = figures.prediction_error_by_year(built)
    keys = [ax for ax in fig.axes if ax.get_legend()]
    assert len(keys) == 1
    # Below every panel rather than beside one.
    fig.canvas.draw()
    lowest = min(ax.get_window_extent().y0 for ax in year_panels(fig))
    assert keys[0].get_window_extent().y0 < lowest
    ps.plt.close(fig)


def test_the_key_takes_the_empty_columns_when_a_row_leaves_them():
    """Real data does leave them, and a key standing in blank columns costs no
    height where a band under the rows cost 96 px of it."""
    built = panels()
    key = figures.GAS_PANEL[0][0]
    keep = drawn_years(built[key])[figures.YEAR_KEY_COLUMNS:]
    built[key] = built[key][built[key].index.year.isin(keep)]
    fig = figures.prediction_error_by_year(built)
    fig.canvas.draw()
    box = next(ax for ax in fig.axes if ax.get_legend()).get_window_extent()
    top_row = max(ax.get_window_extent().y1 for ax in year_panels(fig))
    # Beside the top row, not under everything.
    assert box.y1 <= top_row + 1
    assert box.x0 < min(ax.get_window_extent().x0 for ax in year_panels(fig))
    ps.plt.close(fig)


def test_the_title_names_the_span_the_columns_actually_cover():
    """It read (2013 to 2020) while the 2020 column was drawn. With that column
    cut the panels end at 2019, and a title naming 2020 would describe something
    not on the canvas."""
    assert figures.AGREEMENT_TEXT.title.endswith("(2013 to 2019)")
