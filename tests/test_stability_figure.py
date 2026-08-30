"""Coefficient stability: the two spans it must carry, and the fair comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures
from study import plotstyle as ps

TREATMENTS = ("weighted", "unweighted")


def synthetic(drift: float = 0.5, control_drift: float = 0.1) -> pd.DataFrame:
    """A table shaped like the real one: one coefficient climbs, one barely does."""
    shares = [0, 10, 20, 30, 40]
    rows = []
    for treatment in TREATMENTS:
        for step, share in enumerate(shares):
            climb = 1 + drift * step / (len(shares) - 1)
            held = 1 + control_drift * step / (len(shares) - 1)
            rows.append({
                "treatment": treatment,
                "dropped_wettest_pct": share,
                "n_months": 115 - 11 * step,
                "wte_min": 413.13,
                "wte_max": 413.46 - 0.03 * step,
                "wte_range": 0.33 - 0.03 * step,
                "water_table_coef": 2.7 * climb,
                "water_table_lo": 2.1 * climb,
                "water_table_hi": 4.4 * climb,
                "water_table_includes_zero": False,
                "soil_temp_coef": 0.088 * held,
                "soil_temp_lo": 0.071 * held,
                "soil_temp_hi": 0.099 * held,
                "q10": 2.4 * held,
                "q10_lo": 2.0 * held,
                "q10_hi": 2.7 * held,
                "n_bootstrap_ok": 500,
            })
    return pd.DataFrame(rows)


def paths(**kwargs) -> dict[str, pd.DataFrame]:
    return figures.stability_paths(synthetic(**kwargs))


def drawn(fig, term: int) -> dict[str, np.ndarray]:
    """The y values each treatment's path was drawn at, on one panel.

    Read off the error bar containers rather than off `ax.lines`: the label sits
    on the container and its first artist is the path itself.
    """
    return {container.get_label(): container[0].get_ydata()
            for container in fig.axes[term].containers}


def strip_of(fig):
    """The band under the panels, found by the one distance it carries."""
    for ax in fig.axes:
        if any(figures.TESTED_LABEL in text.get_text() for text in ax.texts):
            return ax
    raise AssertionError("the band of distances is missing")


def counts_axis_of(fig):
    """The axis above the panels, which is a child of the first rather than a peer."""
    for child in fig.axes[0].child_axes:
        if child.get_xlabel() == figures.COUNT_AXIS:
            return child
    raise AssertionError("the months axis is missing")


# --- the two spans the figure exists to put side by side ----------------------


def test_the_edge_of_the_evidence_is_ruled_on_both_panels():
    """Bartley et al. (2019) shade where a model is asked to extrapolate. A block
    at panel height across two thirds of the canvas outweighed everything
    measured, so the region is a rule at its edge and an arrow along its length."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    for index in (0, 1):
        ruled = [line for line in fig.axes[index].lines
                 if len(line.get_xdata()) == 2 and np.allclose(line.get_xdata(), 0.0)]
        assert ruled, "the edge of the fitted range is missing from a panel"
        assert not fig.axes[index].patches, "the region has been filled again"
    ps.plt.close(fig)


def test_the_arrow_says_how_far_beyond_the_evidence_the_reconstruction_reaches():
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    said = " ".join(note.get_text() for note in fig.axes[0].texts)
    assert "0.29 m beyond" in said and "2.4 times the 0.12 m" in said
    assert any(note.arrow_patch is not None for note in fig.axes[0].texts)
    ps.plt.close(fig)


def test_nothing_is_drawn_inside_the_region_that_was_never_measured():
    """A line carried into the shaded region would assert what the figure denies."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    named = {label for _, label, _ in figures.TREATMENTS}
    for index in (0, 1):
        for line in fig.axes[index].lines:
            if line.get_label() not in named:
                continue                       # the reference line is apparatus
            assert np.asarray(line.get_xdata(), dtype=float).max() <= 1e-9
        for collection in fig.axes[index].collections:      # the intervals
            for segment in collection.get_segments():
                assert np.asarray(segment)[:, 0].max() <= 1e-9
    ps.plt.close(fig)


def test_the_tested_span_is_drawn_against_the_required_one_in_the_same_units():
    """The qualification is a ratio of two lengths, so it is drawn as two lengths."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    assert any(figures.TESTED_LABEL in text.get_text() and "0.05" in text.get_text()
               for text in strip_of(fig).texts)
    assert any("0.29 m beyond" in note.get_text() for note in fig.axes[0].texts)
    ps.plt.close(fig)


def test_the_spans_come_from_the_caller_rather_than_from_the_module():
    """Both are properties of the windows in use and would go stale if pinned."""
    fig = figures.coefficient_stability(paths(), required=0.4, tested=0.1)
    said = " ".join(text.get_text() for text in strip_of(fig).texts)
    said += " ".join(note.get_text() for note in fig.axes[0].texts)
    assert "0.40" in said and "0.10" in said
    ps.plt.close(fig)


# --- the comparison the control panel rests on --------------------------------


def test_a_percent_of_change_covers_the_same_distance_on_both_panels():
    """Each axis is in its own unit, so the comparison rests on the geometry: the
    panels are as tall as the proportional range each has to cover, and a control
    scaled to its own data would draw a 10% climb exactly like a 50% one."""
    fig = figures.coefficient_stability(paths(drift=0.5, control_drift=0.1),
                                        required=0.29, tested=0.05)
    pixels = []
    for index in (0, 1):
        ax = fig.axes[index]
        low, high = ax.get_ylim()
        reference = drawn(fig, index)["with weighting"][0]
        height = ax.get_position().height
        pixels.append(height / ((high - low) / reference))   # per unit of proportion
    assert pixels[0] == pytest.approx(pixels[1], rel=0.02)
    ps.plt.close(fig)


def test_each_path_is_drawn_in_the_units_of_the_coefficient_itself():
    """A reader should not have to translate an index back into a coefficient."""
    split = paths(drift=0.5, control_drift=0.1)
    fig = figures.coefficient_stability(split, required=0.29, tested=0.05)
    for index, column in ((0, "water_table_coef"), (1, "soil_temp_coef")):
        for treatment, label, _ in figures.TREATMENTS:
            expected = split[treatment][column].to_numpy()
            assert drawn(fig, index)[label] == pytest.approx(expected)
    ps.plt.close(fig)


def test_the_total_change_is_labeled_at_the_end_of_each_path():
    """It is the number the panels are compared on, so it is on the panels."""
    fig = figures.coefficient_stability(paths(drift=0.5, control_drift=0.1),
                                        required=0.29, tested=0.05)
    for index, expected in ((0, "+50%"), (1, "+10%")):
        printed = [note.get_text() for note in fig.axes[index].texts]
        assert printed.count(expected) == len(figures.TREATMENTS)
    ps.plt.close(fig)


def test_the_control_panel_carries_its_name_and_nothing_else():
    """It used to carry a note as well: "The control: the same experiment, on a
    coefficient that barely moves". That restated the description's last sentence,
    took a colon into a caption, and labeled a panel already named in a bordered
    box above it. The description says what the panel is for; the panel says what
    it is."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    said = " ".join(note.get_text() for note in fig.axes[1].texts)
    assert "Soil temperature" in said
    assert "control" not in said and "barely moves" not in said
    assert figures.STABILITY_TERMS[1][5] is None
    ps.plt.close(fig)


def test_the_key_sits_over_the_annotation_rather_than_under_the_panel_name():
    """Nothing in this set puts a legend under the panels, and this one stands in
    the ground the fill used to cover.

    Not in the upper right, where it started. Bordering it showed what being
    frameless had hidden: 13.9 px under the bordered panel name and 3.3 px off the
    panel's own edge, crowding two things at once. It is now centred on the orange
    annotation, which is the only other object in that half of the panel.
    """
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    ax = fig.axes[0]
    key = ax.get_legend()
    assert key is not None
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    box = key.get_window_extent(renderer)
    note = next(text for text in ax.texts if "reconstruction" in text.get_text())
    name = next(text for text in ax.texts if text.get_text() == "Water table")

    # Above the annotation and centred on it.
    assert box.y0 > note.get_window_extent(renderer).y1
    assert ((box.x0 + box.x1) / 2 == pytest.approx(
        sum(note.get_window_extent(renderer).intervalx) / 2, abs=1.0))
    # Clear of the panel name it used to crowd, and of the panel's own edges.
    assert name.get_window_extent(renderer).y0 - box.y1 > 100
    frame = ax.get_window_extent(renderer)
    assert min(box.x0 - frame.x0, frame.x1 - box.x1) > ps.MIN_BLOCK_GAP_PX
    # Still off the data, which is what put it in this half of the panel at all.
    assert box.x0 > max(line.get_window_extent().x1 for line in ax.lines
                        if len(line.get_xdata()) and max(line.get_xdata()) < 0.001)
    ps.plt.close(fig)


def test_the_month_counts_sit_with_the_fits_they_describe():
    """They were at the foot of the figure, away from the points they belong to."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    assert [text.get_text() for text in counts_axis_of(fig).get_xticklabels()] == \
        [f"{n:.0f}" for n in paths()["weighted"]["n_months"]]
    ps.plt.close(fig)


def test_one_key_serves_both_panels_and_names_every_mark():
    """Panel b carries the same marks and had no key of its own."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    keys = [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    assert len(keys) == 1
    labels = [text.get_text() for text in keys[0].get_texts()]
    for mark in ("resamples", "carried across", "wettest month the model",
                 "bracketed span", "reaches past the fit"):
        assert any(mark in label for label in labels)
    assert sum(label.startswith("$") for label in labels) == 2      # two headings
    # The arrow was the one mark on the panel with no entry, while the dashed
    # rule beside it in the same orange had one. Two orange marks, handled two
    # ways, is what a reader had to work out unaided.
    assert figures.BEYOND_KEY in labels
    ps.plt.close(fig)


def test_the_two_treatments_carry_no_hue_between_them():
    """They are one analysis run twice, not two methods being compared."""
    for _, _, style in figures.TREATMENTS:
        red, green, blue = ps.plt.matplotlib.colors.to_rgb(style["color"])
        assert red == pytest.approx(green) == pytest.approx(blue)
    styles = {style["linestyle"] for _, _, style in figures.TREATMENTS}
    assert len(styles) == len(figures.TREATMENTS)      # separated without hue


def test_neither_treatment_is_named_as_the_better_one():
    """Said now by the outcome rather than by a verdict on the two: weighting
    changes the numbers and not the result, and the climb holds under both."""
    said = figures.STABILITY_TEXT.description
    assert "changes the numbers but not the outcome" in said
    assert "under both treatments" in said
    for better in ("Both fail", "the better treatment", "neither survives"):
        assert better not in said


# --- what the words have to carry ---------------------------------------------


def test_the_subtitle_says_what_the_coefficient_is_before_the_panel_is_read():
    said = figures.STABILITY_TEXT.subtitle
    assert "per meter of water table" in said
    assert "fitted five times" in said


def test_the_subtitle_says_why_a_moving_coefficient_matters():
    """Drift on its own is not the finding; what it implies about the fit is."""
    said = figures.STABILITY_TEXT.subtitle
    assert "describing the months it was fitted on rather than the peatland" in said


def test_the_description_does_not_let_one_step_stand_for_the_result():
    said = figures.STABILITY_TEXT.description
    assert "no single step is decisive" in said
    assert "climbs at all four steps under both treatments and never once falls" in said
    assert "the pattern is the evidence" in said


def test_the_control_is_not_reported_as_flat_where_it_is_not():
    """Under weighting it moves 16%, which is a third of the water table's 51%
    rather than nothing at all. The block says *moves far less*, not *is flat*,
    and the two numbers it used to quote are labeled on the panel at the end of
    each path, where a reader can check them against the lines they belong to."""
    said = figures.STABILITY_TEXT.description
    assert "moves far less" in said
    for flat in ("is flat", "does not move", "barely moves", "stays put"):
        assert flat not in said
    # Quoted on the panel instead, at the dry end of every path.
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    labeled = " ".join(note.get_text() for ax in fig.axes for note in ax.texts)
    assert labeled.count("%") == 4
    ps.plt.close(fig)


def test_the_verdict_criterion_is_not_put_on_the_panel():
    """It took four clauses to state and would imply the answer was obvious."""
    text = figures.STABILITY_TEXT
    said = " ".join([text.title, text.subtitle, text.description]).lower()
    for term in ("criterion", "verdict", "monotone", "spearman", "bootstrap",
                 "significant", "p =", "stable"):
        assert term not in said


def test_the_figure_spells_it_the_american_way():
    text = figures.STABILITY_TEXT
    said = " ".join([text.title, text.subtitle, text.description,
                     figures.STABILITY_X_AXIS]).lower()
    assert "metre" not in said and "meter" in said


# --- the table it reads -------------------------------------------------------


def test_the_paths_are_split_by_treatment_and_ordered_driest_last():
    split = paths()
    assert set(split) == set(TREATMENTS)
    for frame in split.values():
        assert frame["dropped_wettest_pct"].is_monotonic_increasing
        assert frame["wte_max"].is_monotonic_decreasing


def test_the_committed_table_carries_both_treatments_and_every_step():
    """The figure reads what the pipeline wrote, as the rest of the set does."""
    from ingest import paths as repo

    frame = pd.read_csv(repo.processed_dir() / "coefficient_stability.csv")
    assert set(frame["treatment"]) == set(TREATMENTS)
    for _, part in frame.groupby("treatment"):
        assert sorted(part["dropped_wettest_pct"]) == [0, 10, 20, 30, 40]
        assert (part["n_bootstrap_ok"] == 500).all()

def test_every_ruled_legend_heading_is_ruled_under_its_own_text():
    """The rules are figure artists at fixed figure coordinates and the balance
    moves the axes the legend rides on, so ruling before balancing leaves the line
    where the heading used to be and draws it through the letters.

    Found by measuring, not by looking: at this size the strike sits in the lower
    third of a bold capital and reads as a heavy baseline. It had been doing that
    on the reconstruction figure for as long as that figure had been balanced, and
    the flux figure ruled twice, leaving a stale artist under every correct one.
    """
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    headings = [text for ax in fig.axes if ax.get_legend()
                for text in ax.get_legend().get_texts()
                if text.get_text().startswith("$")]
    rules = [artist for artist in fig.artists if hasattr(artist, "get_data")]
    assert headings, "the key has no ruled headings"
    assert len(rules) == len(headings), "a heading is ruled twice or not at all"

    for text in headings:
        box = text.get_window_extent(renderer)
        middle = (box.x0 + box.x1) / 2
        near = []
        for artist in rules:
            ends = artist.get_transform().transform(list(zip(*artist.get_data())))
            if abs(ends[:, 0].mean() - middle) < 6:
                near.append(ends[0, 1])
        assert len(near) == 1, f"{text.get_text()} has {len(near)} rules under it"
        assert near[0] < box.y0, (
            f"{text.get_text()} is struck through: rule at {near[0]:.1f}, "
            f"text starts at {box.y0:.1f}")
    ps.plt.close(fig)

def test_the_key_draws_the_marks_the_panel_draws():
    """A key showing a mark the figure does not contain is wrong in the way a
    wrong number is wrong.

    Two faults, both structural. The open markers were made open at the
    `errorbar` call, which the key does not go through, so the panel drew hollow
    rings and the key drew solid ones. And a legend lays every handle on three
    sample points and draws the marker at each, so a marker-only entry rendered
    as three ticks where the panel draws one capped interval, and the bracket
    rendered with a third tick in its middle where the strip has two at its ends.
    Neither reads as an error at this size, which is why both survived.
    """
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    ax, key = fig.axes[0], fig.axes[0].get_legend()
    fig.canvas.draw()

    # Every marker property the panel sets, the key shows.
    panel = {bar.get_label(): bar[0] for bar in ax.containers}
    shown = {line.get_marker(): line for line in key.get_lines()
             if line.get_marker() in ("o", "^")}
    assert len(shown) == len(panel)
    for drawn in panel.values():
        keyed = shown[drawn.get_marker()]
        for read in ("get_markerfacecolor", "get_markeredgecolor",
                     "get_markeredgewidth", "get_markersize"):
            assert getattr(keyed, read)() == getattr(drawn, read)(), read

    # The interval and the bracket are drawn by handlers, not by a marker laid on
    # however many sample points the legend happens to use.
    for stand_in, handler, pieces in (
            (figures._IntervalKey, figures._IntervalHandler(), 3),
            (figures._BracketKey, figures._BracketHandler(), 3)):
        parts = handler.create_artists(key, stand_in(), 0, 0, 24.0, 12.0, 8.5,
                                       ax.transData)
        assert len(parts) == pieces
        # The bracket's ticks are at its ends, which is what makes it a bracket.
        if stand_in is figures._BracketKey:
            ends = sorted(part.get_xdata()[0] for part in parts[1:])
            assert ends == [0.0, 24.0]
    ps.plt.close(fig)


def test_the_percentages_on_the_panel_are_said_to_be_totals():
    """Four numbers stood beside the line ends with nothing saying what they
    measured. They are each coefficient's change from the 115-month fit to the
    69-month one, which is not something the panel can show."""
    said = figures.STABILITY_TEXT.description
    assert "total change across all five fits" in said
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    labeled = " ".join(note.get_text() for ax in fig.axes for note in ax.texts)
    assert labeled.count("%") == 4
    ps.plt.close(fig)
