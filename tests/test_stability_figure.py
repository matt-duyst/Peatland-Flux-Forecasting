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
    """The band of distances under the panels, found by what it carries."""
    for ax in fig.axes:
        if any(figures.REQUIRED_LABEL in text.get_text() for text in ax.texts):
            return ax
    raise AssertionError("the strip of distances is missing")


# --- the two spans the figure exists to put side by side ----------------------


def test_the_region_the_reconstruction_needs_is_shaded_on_both_panels():
    """Bartley et al. (2019) shade where a model is asked to extrapolate; here it
    is shaded to show that no refit reaches it."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    for index in (0, 1):
        spans = [p for p in fig.axes[index].patches if p.get_width() == pytest.approx(0.29)]
        assert spans, "the required region is missing from a panel"
        assert spans[0].get_x() == pytest.approx(0.0)
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
    labels = [t.get_text() for t in strip_of(fig).texts]
    assert any(figures.TESTED_LABEL in text and "0.05" in text for text in labels)
    assert any(figures.REQUIRED_LABEL in text and "0.29" in text for text in labels)
    ps.plt.close(fig)


def test_the_spans_come_from_the_caller_rather_than_from_the_module():
    """Both are properties of the windows in use and would go stale if pinned."""
    fig = figures.coefficient_stability(paths(), required=0.4, tested=0.1)
    labels = " ".join(t.get_text() for t in strip_of(fig).texts)
    assert "0.40" in labels and "0.10" in labels
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


def test_the_control_panel_says_on_the_panel_what_it_is_for():
    """A nearly flat line with no caption is the hardest mark on the figure."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    said = " ".join(note.get_text() for note in fig.axes[1].texts)
    assert "same five fits" in said
    ps.plt.close(fig)


def test_one_key_serves_both_panels_and_names_every_mark():
    """Panel b carries the same marks and had no key of its own."""
    fig = figures.coefficient_stability(paths(), required=0.29, tested=0.05)
    keys = [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    assert len(keys) == 1
    labels = [text.get_text() for text in keys[0].get_texts()]
    for mark in ("resamples", "carried across", "reconstruction needs", "distance in meters"):
        assert any(mark in label for label in labels)
    assert sum(label.startswith("$") for label in labels) == 2      # two headings
    ps.plt.close(fig)


def test_the_two_treatments_carry_no_hue_between_them():
    """They are one analysis run twice, not two methods being compared."""
    for _, _, style in figures.TREATMENTS:
        red, green, blue = ps.plt.matplotlib.colors.to_rgb(style["color"])
        assert red == pytest.approx(green) == pytest.approx(blue)
    styles = {style["linestyle"] for _, _, style in figures.TREATMENTS}
    assert len(styles) == len(figures.TREATMENTS)      # separated without hue


def test_neither_treatment_is_named_as_the_better_one():
    said = figures.STABILITY_TEXT.description
    assert "Both fail" in said and "neither is the better treatment" in said


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
    assert "climbs at all four and never once falls" in said


def test_the_control_is_not_reported_as_flat_where_it_is_not():
    """Under weighting it moves 16%, which is a third of the water table's 51%
    rather than nothing at all."""
    said = figures.STABILITY_TEXT.description
    assert "16%" in said and "51%" in said
    assert "only without weighting is it flat" in said


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
