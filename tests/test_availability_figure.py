"""Availability: four kinds of month, two blocks, and the alignments they carry."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures
from study import plotstyle as ps


def synthetic() -> dict[str, pd.Series]:
    """Two series with different spans, one of them holed and one set aside."""
    long = pd.period_range("1990-01", "2019-12", freq="M")
    short = pd.period_range("2009-04", "2021-12", freq="M")
    holed = pd.Series(1.0, index=short)
    holed.loc[pd.Period("2013-05", freq="M")] = np.nan
    holed.loc[pd.period_range("2014-01", "2014-03", freq="M")] = np.nan
    return {"Air temperature": pd.Series(1.0, index=long),
            "Methane": holed,
            "Water table": pd.Series(1.0, index=pd.period_range("1990-01", "2021-01", freq="M"))}


ASIDE = {"Water table": (
    (pd.PeriodIndex(["2019-06", "2019-09"], freq="M"), "instrument error"),
    (pd.period_range("2020-01", "2021-01", freq="M"), "gauge change"),
)}

DREW_ON = [
    {"name": "Months with both flux and drivers (used to fit the model)",
     "first": pd.Period("2009-04", freq="M"), "last": pd.Period("2019-12", freq="M"),
     "months": 115, "lead": None, "support": True},
    {"name": "Months with drivers but no flux (estimated by the model)",
     "first": pd.Period("1990-01", freq="M"), "last": pd.Period("2009-03", freq="M"),
     "months": 230, "lead": None},
]
SCORED = [
    {"name": "Methane forecasts", "first": pd.Period("2014-06", freq="M"),
     "last": pd.Period("2020-12", freq="M"), "months": 71,
     "lead": (pd.Period("2009-04", freq="M"), pd.Period("2014-06", freq="M"))},
]
GROUPS = ((figures.BLOCK_HEADINGS[1], DREW_ON), (figures.BLOCK_HEADINGS[2], SCORED))
WINDOWS = DREW_ON + SCORED


def rows():
    return figures.availability_rows(synthetic(), ASIDE)


def figure():
    return figures.covariate_availability(rows(), GROUPS)


# --- four kinds of month ------------------------------------------------------


def test_rows_are_ordered_by_where_each_record_ends():
    """The ordering is the argument: the right edges step inward and the last step
    is where the fitting window stops."""
    ends = [row["present"].max() for row in rows()]
    assert ends == sorted(ends, reverse=True)


def test_a_gap_inside_a_run_is_told_apart_from_years_the_series_never_covered():
    """Both are months with no value, and only one of them is a gap."""
    built = {row["name"]: row for row in rows()}
    methane = built["Methane"]
    assert methane["present"].min() == pd.Period("2009-04", freq="M")
    assert list(methane["gaps"]) == list(pd.PeriodIndex(
        ["2013-05", "2014-01", "2014-02", "2014-03"], freq="M"))
    assert built["Air temperature"]["gaps"].empty


def test_a_month_set_aside_is_neither_missing_nor_counted_as_a_gap():
    """It was measured; a decision took it out, and the figure says which."""
    built = {row["name"]: row for row in rows()}
    water = built["Water table"]
    assert water["gaps"].empty
    reasons = [reason for _, reason in water["aside"]]
    assert reasons == ["instrument error", "gauge change"]
    assert water["months"] == 373                      # measured, before any decision


def test_the_count_is_what_was_measured_rather_than_what_survived():
    built = {row["name"]: row for row in rows()}
    assert built["Methane"]["months"] == len(built["Methane"]["present"])


# --- what is drawn ------------------------------------------------------------


def test_every_run_is_a_bar_and_every_hole_is_a_hole():
    """A gap drawn as a colored cell would make absence a category of its own."""
    fig = figure()
    ax = fig.axes[0]
    bars = [p for p in ax.patches if p.get_facecolor()[:3] != (1.0, 1.0, 1.0)]
    # Air temperature, water table and three methane runs, plus four windows.
    assert len(bars) == 5 + len(WINDOWS)
    ps.plt.close(fig)


def test_one_tick_marks_each_break_rather_than_each_missing_month():
    """Three months adjacent are one break in the record. Three ticks side by side
    were an indistinct smear, and the count of months is not the figure's business."""
    fig = figure()
    ticks = [line for line in fig.axes[0].lines
             if len(line.get_xdata()) == 2 and line.get_xdata()[0] == line.get_xdata()[1] > 1900
             and tuple(line.get_ydata()) != (0.0, 1.0)]
    assert len(ticks) == 2                              # one month, then three
    assert ticks[0].get_linewidth() > 1.2               # heavy enough to see
    ps.plt.close(fig)


def test_what_was_set_aside_is_drawn_hollow_and_edged_in_the_discard_hue():
    """Discarded is what that hue means everywhere else in the set, and this is the
    one place on the panel where something was discarded rather than absent."""
    from matplotlib.colors import to_rgb

    fig = figure()
    hollow = [p for p in fig.axes[0].patches if p.get_facecolor()[:3] == (1.0, 1.0, 1.0)]
    assert len(hollow) == 3                             # two single months, one run
    assert all(p.get_edgecolor()[:3] == to_rgb(ps.OUTSIDE) for p in hollow)
    ps.plt.close(fig)


def test_the_measured_hue_clears_the_outline_drawn_on_top_of_it():
    """Okabe-Ito reddish purple measures 0.9 from the discard orange under
    tritanopia, and the set-aside outlines sit on these bars."""
    source = (ps.paths.repo_root() / "scripts/verify_palette.py").read_text()
    helpers: dict = {}
    exec(source.split("def report")[0], helpers)
    worst = min(helpers["dE"](helpers["sim"](helpers["hex2rgb"](ps.MEASURED), kind),
                              helpers["sim"](helpers["hex2rgb"](ps.OUTSIDE), kind))
                for kind in ("deuteranopia", "protanopia", "tritanopia"))
    assert worst > 20.0


def test_the_fitting_window_carries_the_hue_that_means_inside_the_fitted_range():
    """It is that range, in time. The reconstruction beside it stays neutral: its
    months are half inside and half outside, and one hue would assert otherwise."""
    from matplotlib.colors import to_rgb

    fig = figure()
    filled = [p.get_facecolor()[:3] for p in fig.axes[0].patches
              if p.get_facecolor()[:3] != (1.0, 1.0, 1.0)]
    assert filled.count(to_rgb(ps.INSIDE)) == 1
    assert to_rgb(ps.OUTSIDE) not in filled
    assert to_rgb(ps.MEASURED) in filled
    ps.plt.close(fig)


def test_the_reason_a_month_was_set_aside_is_written_beside_it():
    """The key never has to encode a reason, which is what keeps it to three marks."""
    fig = figure()
    said = [note.get_text() for note in fig.axes[0].texts]
    assert "instrument error" in said and "gauge change" in said
    # Each reason is tied to its own mark rather than crossing the bar to reach it.
    leaders = [note.get_text() for note in fig.axes[0].texts
               if getattr(note, "arrow_patch", None) is not None]
    assert {"instrument error", "gauge change"} <= set(leaders)
    ps.plt.close(fig)


def test_the_key_covers_every_mark_on_the_panel_and_carries_no_reasons():
    """Both blocks are keyed from one place: the lower block holds two fills and
    one of them is a hue that means something across the whole set."""
    fig = figure()
    labels = [text.get_text() for text in fig.axes[0].get_legend().get_texts()]
    # One group to a row, each headed at its left. Matplotlib fills columns top
    # to bottom, so the order is interleaved and the shorter group is padded.
    assert labels == [figures.RECORD_HEADING, figures.DECIDED_HEADING,
                      figures.PRESENT_LABEL, figures.ASIDE_LABEL,
                      figures.MISSING_LABEL, figures.FITTED_RANGE_LABEL,
                      "", figures.TRAINING_LABEL]
    ps.plt.close(fig)


def test_the_lead_on_a_forecast_row_is_keyed():
    """A thin rule marks the months a model had to accumulate before it could
    forecast. It was drawn and never keyed, and TRAINING_LABEL was written for it
    and never wired to anything, so the label sat with no caller."""
    fig = figure()
    labels = [text.get_text() for text in fig.axes[0].get_legend().get_texts()]
    assert figures.TRAINING_LABEL in labels
    leads = [line for line in fig.axes[0].lines
             if line.get_color() == ps.MUTED and len(line.get_xdata()) == 2]
    assert leads, "the mark the entry keys is drawn"
    ps.plt.close(fig)


def test_the_blue_convention_is_stated_somewhere_on_the_figure():
    """A reader meeting this figure first has to be told what blue means.

    The description carried a sentence saying so until the key gained a fourth
    entry naming the fitted range. Two statements of one convention is one more
    than the figure needs, and the key is where a reader looks for it, so the
    sentence went and this now checks the key rather than the words.
    """
    fig = figure()
    key = next(ax.get_legend() for ax in fig.axes if ax.get_legend())
    labels = [text.get_text() for text in key.get_texts()]
    assert figures.FITTED_RANGE_LABEL in labels
    assert "Blue marks the range the model was fitted on" not in \
        figures.AVAILABILITY_TEXT.description
    ps.plt.close(fig)


def test_one_neutral_serves_every_bar_that_is_not_the_fitted_range():
    """Two grays would draw a distinction the blocks already carry by position."""
    from matplotlib.colors import to_rgb

    fig = figure()
    fills = {p.get_facecolor()[:3] for p in fig.axes[0].patches}
    assert fills == {to_rgb(ps.MEASURED), to_rgb(ps.INSIDE), (1.0, 1.0, 1.0)}
    ps.plt.close(fig)


# --- the two blocks -----------------------------------------------------------


def test_the_windows_are_their_own_rows_rather_than_shading_over_the_series():
    """Shaded across the panel they would read as a property of the data."""
    fig = figure()
    ax = fig.axes[0]
    names = [label.get_text() for label in ax.get_yticklabels()]
    assert names[-len(WINDOWS):] == [row["name"] for row in WINDOWS]
    assert not any("\n" in name for name in names)      # every row on one line
    # Every mark is one row tall: nothing spans the panel the way a band would.
    assert {round(p.get_height(), 6) for p in ax.patches} == {figures.BAR_HEIGHT}
    ps.plt.close(fig)


def test_the_two_kinds_of_window_are_grouped_and_headed_separately():
    """Spans the study drew on and spans it scored over are not the same thing, and
    four identical bars said they were."""
    fig = figure()
    said = " ".join(note.get_text() for note in fig.axes[0].texts)
    assert figures.BLOCK_HEADINGS[1] in said and figures.BLOCK_HEADINGS[2] in said
    ps.plt.close(fig)


def test_each_block_name_is_framed_and_clears_the_plot():
    """Framed as the panel names are elsewhere in the set, and seated in a gutter
    wide enough that no frame reaches the bars."""
    fig = figure()
    ax = fig.axes[0]
    fig.canvas.draw()
    framed = [note for note in ax.texts if note.get_bbox_patch() is not None]
    assert sorted(note.get_text() for note in framed) == sorted(figures.BLOCK_HEADINGS)
    edge = ax.get_window_extent().x0
    for note in framed:
        assert note.get_bbox_patch().get_window_extent().x1 < edge
    ps.plt.close(fig)


def test_each_block_name_sits_over_the_names_it_heads():
    """Left-aligned at the margin they floated, since the widest block set the
    gutter and the other two headings ended up far from their own rows."""
    fig = figure()
    ax = fig.axes[0]
    fig.canvas.draw()
    labels = ax.get_yticklabels()
    framed = {note.get_text(): note for note in ax.texts
              if note.get_bbox_patch() is not None}
    edge = ax.get_window_extent().x0
    start = 0
    for heading, size in zip(figures.BLOCK_HEADINGS,
                             [len(rows())] + [len(group) for _, group in GROUPS]):
        extents = [label.get_window_extent() for label in labels[start:start + size]]
        middle = (min(box.x0 for box in extents) + max(box.x1 for box in extents)) / 2
        box = framed[heading].get_bbox_patch().get_window_extent()
        centered = abs((box.x0 + box.x1) / 2 - middle) < 3
        clamped = abs(box.x1 - (edge - figures.HEADING_CLEAR_PX)) < 3
        assert centered or clamped, heading
        start += size
    ps.plt.close(fig)


def test_the_first_heading_claims_nothing_about_where_things_were_measured():
    """Only the two fluxes come from the tower: soil temperature is the forest's
    weekly record and precipitation the average of a north and a south gauge."""
    assert "at the site" not in figures.BLOCK_HEADINGS[0]
    assert "measured" in figures.BLOCK_HEADINGS[0]


def test_the_description_uses_the_panel_s_own_word_for_the_measurements():
    said = figures.AVAILABILITY_TEXT.description
    assert "Forecasts inherit the same limit" in said
    assert "environmental measurements" not in said


def test_no_block_name_carries_a_comma():
    for heading in figures.BLOCK_HEADINGS:
        assert "," not in heading


def test_the_key_is_framed_and_centered_on_the_canvas():
    """Centred on the canvas, not on the panel.

    The row labels take a wide left gutter, so the panel occupies only the right
    two thirds. A key wider than the panel and centred on it hangs off the canvas
    edge, which is what the five-entry key did before its anchor was blended: x
    from the figure, y from the axes so it still rides the panel when the block
    is rebalanced.
    """
    fig = figure()
    ax = fig.axes[0]
    fig.canvas.draw()
    key = ax.get_legend()
    assert key.get_frame_on()
    box = key.get_window_extent()
    width = fig.get_size_inches()[0] * fig.dpi
    assert abs((box.x0 + box.x1) / 2 - width / 2) < 12
    assert box.x0 >= ps.MARGIN_PX["left"] - 12, "the key stays inside the margins"
    assert box.x1 <= width - ps.MARGIN_PX["right"] + 12
    ps.plt.close(fig)


def test_both_blocks_are_named_on_the_panel():
    fig = figure()
    said = " ".join(note.get_text() for note in fig.axes[0].texts)
    for heading in figures.BLOCK_HEADINGS:
        assert heading in said
    ps.plt.close(fig)


def test_the_training_lead_is_a_lighter_weight_of_the_same_mark():
    """A fourth symbol for it would have cost a fourth entry in the key."""
    fig = figure()
    leads = [line for line in fig.axes[0].lines
             if len(line.get_xdata()) == 2 and line.get_xdata()[0] > 1900
             and line.get_xdata()[0] != line.get_xdata()[1]]
    assert len(leads) == 1
    assert leads[0].get_linewidth() < 2.0
    ps.plt.close(fig)


# --- what the words carry -----------------------------------------------------


def test_the_description_says_what_the_window_cost_and_not_only_its_cause():
    """Phrased as what the window leaves unusable rather than as a discard. The
    count grew from 24 to 60 when methane was read from the 2025 product, and
    "discards 60" would read as a larger loss when nothing was lost that was not
    already lost: the number grew because the record did."""
    said = figures.AVAILABILITY_TEXT.description
    assert "leaves 60 months of methane the tower recorded but the model cannot use" in said
    assert "discards" not in said
    assert "48 months have accumulated" in said and "62 calendar months" in said


def test_the_description_names_the_benchmark_tail_without_drawing_it():
    """A fourth mark for a clause is not worth it."""
    assert "seasonal benchmarks, which need no drivers, reach 2024" in \
        figures.AVAILABILITY_TEXT.description


def test_the_subtitle_gives_the_mechanism_rather_than_asserting_the_choice():
    """It said the spans were chosen from what was available rather than being
    facts about the site, which is the conclusion. It now says what produces
    them, which a reader can check against the bars: an analysis needing several
    records at once can only run where all of them overlap."""
    said = figures.AVAILABILITY_TEXT.subtitle
    assert "can only run where all of them overlap" in said
    assert "follows directly from the block above" in said
    assert "rather than being facts about the site" not in said


def test_the_subtitle_describes_the_order_the_rows_are_actually_in():
    """It said longest record at the top while they were sorted by end date, which
    put soil temperature, the longest at 383 months, third."""
    said = figures.AVAILABILITY_TEXT.subtitle
    assert "ordered by where each record ends" in said
    assert "longest record at the top" not in said


def test_neither_block_of_text_runs_more_than_two_clauses_to_a_sentence():
    """Four clauses across three facts is one sentence doing three jobs."""
    text = figures.AVAILABILITY_TEXT
    for block in (text.subtitle, text.description):
        for sentence in block.split(". "):
            assert sentence.count(",") <= 2, sentence


def test_the_figure_asks_no_reader_to_know_the_method():
    text = figures.AVAILABILITY_TEXT
    said = " ".join([text.title, text.subtitle, text.description,
                     *figures.BLOCK_HEADINGS, figures.PRESENT_LABEL,
                     figures.MISSING_LABEL, figures.ASIDE_LABEL]).lower()
    for jargon in ("covariate", "exogenous", "holdout", "horizon", "gap-filling",
                   "boruta", "fold", "datum"):
        assert jargon not in said


def test_no_counts_are_drawn_beside_the_bars():
    """A reader does not need them while looking at the panel, the bar lengths
    already carry relative magnitude, and the exact figures are in the notes."""
    fig = figure()
    assert not [note for note in fig.axes[0].texts
                if note.get_text().replace(".", "").isdigit()]
    ps.plt.close(fig)


def test_no_term_appears_as_a_row_name_without_being_explained():
    """Reconstruction, fitting window and scored over were all internal."""
    said = " ".join([row["name"] for row in WINDOWS] + list(figures.BLOCK_HEADINGS)).lower()
    for term in ("reconstruction", "fitting window", "scored", "projected"):
        assert term not in said


def test_the_model_rows_say_what_their_span_is_rather_than_naming_it():
    """A reader meeting this figure first does not know the study's structure, so
    a row cannot be called "learned from" and leave them to work out what from."""
    names = [row["name"] for row in DREW_ON]
    for name in names:
        assert "flux" in name and "drivers" in name
    # And having said it, nothing else on the panel needs to repeat it.
    fig = figure()
    assert not [note for note in fig.axes[0].texts if "check against" in note.get_text()]
    ps.plt.close(fig)


def test_the_time_axis_is_named_and_the_row_axis_is_not():
    """Every row carries its own name; a title over them would repeat six."""
    fig = figure()
    assert fig.axes[0].get_xlabel() == figures.TIME_AXIS
    assert not fig.axes[0].get_ylabel()
    ps.plt.close(fig)


def test_the_title_names_the_site():
    assert "Marcell Bog Lake Peatland" in figures.AVAILABILITY_TEXT.title


def test_the_subtitle_says_the_block_splits_at_both_ends():
    """The right edges say where the fit window had to stop. The left edges say
    why a reconstruction is possible at all, and nothing else on the figure
    states it.

    19 understates, deliberately and in two directions. Three of the four
    environmental records begin 1990-01 against carbon dioxide at 2009-01, which
    is 19 years exactly; against methane at 2009-04 it is 19 years and 3 months,
    and soil temperature begins six months earlier still. The reconstruction runs
    1990-01 to 2009-03, so the span it covers is the gap before methane rather
    than the 19 years before carbon dioxide, and it is the larger of the two.
    """
    said = figures.AVAILABILITY_TEXT.subtitle
    assert "begin 19 years before either flux does" in said
    assert "that gap is the span the reconstruction covers" in said
    # Placed with the other statement about the measurement block, and before the
    # sentence about the lower rows.
    assert said.index("at the bottom") < said.index("19 years")
    assert said.index("19 years") < said.index("The rows below")
