"""Shared figure infrastructure: canvas geometry, text fitting, and the ink rules."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from study import plotstyle as ps

TEXT = ps.FigureText(
    title="A title",
    subtitle="A finding, not a restatement",
    description="First sentence of the description. Second sentence of the description.",
)


def test_a_description_must_be_more_than_one_sentence_and_not_unbounded():
    with pytest.raises(ValueError, match="two to"):
        ps.FigureText(title="t", subtitle="s", description="Only one sentence here.")
    too_many = ". ".join(f"S{i}" for i in range(ps.MAX_SENTENCES + 3)) + "."
    with pytest.raises(ValueError, match="two to"):
        ps.FigureText(title="t", subtitle="s", description=too_many)


def test_wrap_width_is_tied_to_canvas_width():
    narrow = ps._wrap_width(ps.SIZES["compact"][0])
    wide = ps._wrap_width(ps.SIZES["wide"][0])
    assert wide > narrow


def test_a_description_that_will_not_fit_raises_rather_than_being_clipped():
    """The block height is fixed, so overflow has to fail loudly."""
    long_text = "A sentence that keeps going and going. " * 20
    with pytest.raises(ps.DescriptionOverflow, match="Shorten it"):
        ps.wrap_description(long_text, ps.SIZES["wide"][0])


def test_canvas_reserves_fixed_blocks_so_proportions_do_not_move():
    short = ps.FigureText("t", "s", "One sentence. Two sentences.")
    longer = ps.FigureText("t", "s", "One sentence. Two sentences. Three of them now. And four.")
    boxes = []
    for text in (short, longer):
        fig, ax = ps.canvas(text, size="wide")
        boxes.append(ax.get_position().bounds)
        ps.plt.close(fig)
    assert boxes[0] == pytest.approx(boxes[1])


def test_canvas_pixel_size_matches_the_named_size(tmp_path):
    fig, _ = ps.canvas(TEXT, size="wide")
    target = tmp_path / "out.png"
    fig.savefig(target, dpi=ps.DPI)
    ps.plt.close(fig)
    assert Image.open(target).size == ps.SIZES["wide"]


def test_hue_is_reserved_for_support_status():
    """No model variant may reuse a support hue, in any channel."""
    variant_colors = {v["color"].upper() for v in ps.VARIANT.values()}
    assert ps.INSIDE.upper() not in variant_colors
    assert ps.OUTSIDE.upper() not in variant_colors


def test_variants_are_achromatic_and_separated_by_line_style():
    for style in ps.VARIANT.values():
        r, g, b = (int(style["color"][i:i + 2], 16) for i in (1, 3, 5))
        assert r == g == b, f"{style['color']} is not achromatic"
    assert len({v["linestyle"] for v in ps.VARIANT.values()}) == len(ps.VARIANT)


def test_support_status_carries_a_second_channel_beyond_hue():
    assert ps.INSIDE_MARKER != ps.OUTSIDE_MARKER
    assert ps.INSIDE_HATCH != ps.OUTSIDE_HATCH


def test_readme_block_repeats_the_canvas_words_exactly():
    block = ps.readme_block(TEXT, "some_stem")
    assert TEXT.title in block
    assert TEXT.subtitle in block
    assert " ".join(TEXT.description.split()) in block
    assert "figures/some_stem.png" in block


def test_save_writes_a_png_and_returns_its_path(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "figures_dir", lambda: tmp_path / "figures")
    fig, ax = ps.canvas(TEXT, size="compact")
    ax.plot([0, 1], [0, 1])
    path = ps.save(fig, "example")
    assert path.exists() and path.suffix == ".png"
    assert Image.open(path).size == ps.SIZES["compact"]


def test_range_bounds_are_apparatus_rather_than_a_category():
    """The bounds classify points, so they must not wear a support hue."""
    fig, ax = ps.canvas(TEXT, size="wide")
    ax.set_ylim(0, 10)
    before = len(ax.lines)
    ps.fitted_range(ax, 2.0, 8.0)
    drawn = ax.lines[before:]
    assert len(drawn) == 2
    assert {line.get_color() for line in drawn} == {ps.BOUNDARY}
    assert ps.BOUNDARY not in (ps.INSIDE, ps.OUTSIDE)
    ps.plt.close(fig)


def test_support_scatter_separates_the_two_states():
    fig, ax = ps.canvas(TEXT, size="wide")
    inside, = ps.support_scatter(ax, [0, 1], [1, 2], inside=True)
    outside, = ps.support_scatter(ax, [0, 1], [3, 4], inside=False)
    assert inside.get_marker() != outside.get_marker()
    assert inside.get_color() != outside.get_color()
    ps.plt.close(fig)


def test_region_labels_are_bold_so_they_read_as_structure():
    """Regression guard: the weight has been lost to silent edits before."""
    fig, ax = ps.canvas(TEXT, size="wide")
    ax.set_xlim(0, 10)
    ps.label_period(ax, 0, 5, "Some window (something here)")
    label = ax.texts[-1]
    assert label.get_fontweight() == "bold"
    ps.plt.close(fig)


def test_annotations_sit_below_region_labels_in_the_hierarchy():
    fig, ax = ps.canvas(TEXT, size="wide")
    ps.annotate(ax, "a note", xy=(0, 0), xytext=(1, 1))
    note = ax.texts[-1]
    assert note.get_style() == "italic"
    assert note.get_fontsize() < ps.LEGEND_SIZE
    ps.plt.close(fig)
