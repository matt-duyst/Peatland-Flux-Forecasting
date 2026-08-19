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

WINDOWS = [
    {"name": "Reconstruction", "first": pd.Period("1990-01", freq="M"),
     "last": pd.Period("2009-03", freq="M"), "months": 230, "lead": None},
    {"name": "Fitting window", "first": pd.Period("2009-04", freq="M"),
     "last": pd.Period("2019-12", freq="M"), "months": 115, "lead": None},
    {"name": "Forecast comparison", "first": pd.Period("2014-06", freq="M"),
     "last": pd.Period("2020-12", freq="M"), "months": 71,
     "lead": (pd.Period("2009-04", freq="M"), pd.Period("2014-06", freq="M"))},
]


def rows():
    return figures.availability_rows(synthetic(), ASIDE)


def figure(guides=()):
    return figures.covariate_availability(rows(), WINDOWS, guides)


# --- four kinds of month ------------------------------------------------------


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


def test_each_hole_carries_a_tick_because_one_month_is_four_pixels_wide():
    fig = figure()
    ticks = [line for line in fig.axes[0].lines
             if len(line.get_xdata()) == 2 and line.get_xdata()[0] == line.get_xdata()[1]]
    assert len(ticks) == 4                              # one per missing month
    ps.plt.close(fig)


def test_what_was_set_aside_is_drawn_hollow_rather_than_absent():
    fig = figure()
    hollow = [p for p in fig.axes[0].patches if p.get_facecolor()[:3] == (1.0, 1.0, 1.0)]
    assert len(hollow) == 3                             # two single months, one run
    ps.plt.close(fig)


def test_the_reason_a_month_was_set_aside_is_written_beside_it():
    """The key never has to encode a reason, which is what keeps it to three marks."""
    fig = figure()
    said = [note.get_text() for note in fig.axes[0].texts]
    assert "instrument error" in said and "gauge change" in said
    ps.plt.close(fig)


def test_the_key_carries_three_marks_and_no_reasons():
    fig = figure()
    labels = [text.get_text() for text in fig.axes[0].get_legend().get_texts()]
    assert labels == [figures.PRESENT_LABEL, figures.MISSING_LABEL, figures.ASIDE_LABEL]
    ps.plt.close(fig)


# --- the two blocks -----------------------------------------------------------


def test_the_windows_are_their_own_rows_rather_than_shading_over_the_series():
    """Shaded across the panel they would read as a property of the data."""
    fig = figure()
    ax = fig.axes[0]
    names = [label.get_text() for label in ax.get_yticklabels()]
    assert names[-len(WINDOWS):] == [row["name"] for row in WINDOWS]
    # Every mark is one row tall: nothing spans the panel the way a band would.
    assert {round(p.get_height(), 6) for p in ax.patches} == {figures.BAR_HEIGHT}
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


def test_guides_are_drawn_only_where_the_caller_asks_for_them():
    """They are for alignments that carry a claim, not for every boundary."""
    plain = figure()
    guided = figure((pd.Period("2009-04", freq="M"), pd.Period("2020-01", freq="M")))
    def verticals(fig):
        """Full-height rules, which are in year coordinates and axes fractions."""
        return sum(1 for line in fig.axes[0].lines
                   if len(line.get_xdata()) == 2
                   and line.get_xdata()[0] == line.get_xdata()[1] > 1900
                   and tuple(line.get_ydata()) == (0.0, 1.0))
    assert verticals(guided) - verticals(plain) == 2
    ps.plt.close(plain)
    ps.plt.close(guided)


# --- what the words carry -----------------------------------------------------


def test_the_description_says_what_the_window_cost_and_not_only_its_cause():
    said = figures.AVAILABILITY_TEXT.description
    assert "discards 25 months of methane" in said
    assert "48 months of flux" in said and "62 calendar months" in said


def test_the_description_names_the_benchmark_tail_without_drawing_it():
    """A fourth mark for a clause is not worth it."""
    assert "benchmarks alone reach" in figures.AVAILABILITY_TEXT.description


def test_the_subtitle_says_the_windows_were_chosen():
    said = figures.AVAILABILITY_TEXT.subtitle
    assert "chosen from what was available" in said
    assert "rather than being facts about the site" in said


def test_the_figure_asks_no_reader_to_know_the_method():
    text = figures.AVAILABILITY_TEXT
    said = " ".join([text.title, text.subtitle, text.description,
                     *figures.BLOCK_HEADINGS, figures.PRESENT_LABEL,
                     figures.MISSING_LABEL, figures.ASIDE_LABEL]).lower()
    for jargon in ("covariate", "exogenous", "holdout", "horizon", "gap-filling",
                   "boruta", "fold", "datum"):
        assert jargon not in said


def test_the_title_names_the_site():
    assert "Marcell Bog Lake Peatland" in figures.AVAILABILITY_TEXT.title
