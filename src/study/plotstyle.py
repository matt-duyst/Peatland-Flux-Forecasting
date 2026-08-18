"""Shared drawing decisions for the figure set: sizing, ink, and repeated elements.

Every figure is a raster image displayed in a README and read at full size, so
each carries its own title, finding and description inside the canvas and stands
alone when separated from surrounding text. The text is held here with the
figure rather than written twice, and `readme_block` emits the same words for the
README so the two cannot drift.

Hue carries exactly one distinction across the whole set: whether a month falls
inside the range the model was fitted on. Everything else separates by line
style, marker shape, hatching or lightness, so no figure depends on hue being
seen. Model variants are deliberately achromatic for that reason.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from ingest import paths

# --------------------------------------------------------------------------
# Ink
# --------------------------------------------------------------------------

# --- What each hue means, and why none of them is free ------------------------
#
# Three hues carry meaning across the figure set, and each carries exactly one.
#
#   INSIDE  #0072B2  inside, or retained
#   OUTSIDE #D55E00  outside, or discarded
#
# These two are the support encoding. They appear on the reconstruction figures
# for whether a month lies inside the fitted range, and on the site map for
# whether a wind sector is retained or discarded and for whether the site is in
# the FLUXNET-CH4 network. They are the strongest separation in the set, 111.7
# apart under deuteranopia and 93.3 under protanopia.
#
#   FITTED  #009E73  the range across the eight fitted models
#
# Scoped to the two forecast figures only. It exists because the study's halves
# ask different questions: the reconstruction figures are about support and the
# forecast figures are about method, so neither set needs the other's encoding.
# A second blue was tried here and removed, because blue already means retained.
#
# Anything else carrying a hue is cartography rather than encoding, is local to
# the panel it appears on, and is not a general-purpose accent. The mapped
# wetland boundary on the site map is the only such case.
#
# **None of these is available for reuse on a new figure without first checking
# what it already means.** That check has failed twice: sky blue was introduced
# for the fitted range beside a blue that meant retained, and the support orange
# was borrowed for the wetland boundary beside an orange that meant discarded.
# Both were caught after the figure was built rather than before.
INSIDE = "#0072B2"
OUTSIDE = "#D55E00"

#: The fitted models in the two forecast figures, per the convention above.
#: Okabe-Ito bluish green, chosen by measurement: it clears `INSIDE` by 20.9 and
#: `OUTSIDE` by 35.9 under the worst simulated deficiency. Reddish purple was measured and rejected at **0.9 against
#: `OUTSIDE` under tritanopia**: the band edges and the legend patch are drawn in
#: the pure hue, so a reader would meet the same color carrying two meanings.
FITTED = "#009E73"
#: Alpha for the fitted fill. Heavier than the sky blue it replaces, because a
#: pale green sits close to the apparatus grays: at this weight the fill clears
#: every gray on the panel by 12.1 and by 0.197 in relative luminance, where sky
#: blue cleared the grid by 0.014 and was all but invisible in grayscale.
FITTED_FILL_ALPHA = 0.55

#: The uncertainty in an observed monthly mean, drawn as a band in the line's own
#: ink rather than as error bars, following Deventer et al. (2019) figure 10.
#: Light enough that the series reads through it on carbon dioxide, where the band
#: is wide: it separates from the fitted fill by 0.215 in relative luminance and
#: 12.7 under the worst simulated deficiency, and where the two overlap the result
#: is distinct from each of them.
OBSERVED_BAND_ALPHA = 0.16

#: The region within which a method is not distinguishable from the benchmark.
#: Apparatus rather than a category, so it is achromatic and lighter than the
#: envelope it must not be confused with.
NOT_DISTINGUISHABLE = "#EAEAEA"

#: Model variants, achromatic so that hue stays reserved for support status.
#: Each also takes a line style, so lightness alone never has to carry them.
#: Weight follows how far each assumption can be defended, not how large an
#: answer it gives. Continuing the water table term beyond its fitted range is
#: the assumption the stability test rejects, so it is drawn lightest; left
#: heavier it dominates the panel by amplitude alone.
VARIANT = {
    "clamped": {"color": "#1A1A1A", "linestyle": "-", "linewidth": 2.4},
    # Dash-dot rather than dashed: the apparatus tone is also a mid gray and is
    # also drawn dashed, and two dashed grays on one panel would be a standing
    # hazard rather than one this figure happens to avoid.
    "unclamped": {"color": "#767676", "linestyle": (0, (7, 2, 2, 2)), "linewidth": 1.1},
    "reduced": {"color": "#A9A9A9", "linestyle": (0, (1.4, 2.2)), "linewidth": 1.7},
}

#: Range boundaries and other apparatus. Neutral so it reads as annotation rather
#: than as a category, and measured clear of both support hues under every
#: simulated deficiency.
BOUNDARY = "#4D4D4D"

INK = "#1A1A1A"
MUTED = "#595959"
GRID = "#D9D9D9"
#: The fit window is an annotation on one continuous series, not a separate
#: chart region, so the fill is faint and its edge is only just visible.
FIT_BAND = "#F2F2F2"
FIT_BAND_EDGE = "#D8D8D8"

#: Non-hue channels paired with support status, chosen per mark type. A line has
#: no fill pattern and a band has no marker, so the redundant channel differs.
INSIDE_MARKER = "o"
OUTSIDE_MARKER = "^"
INSIDE_HATCH = ""
OUTSIDE_HATCH = "///"

#: Sequential quantities use cividis: perceptually uniform, monotonic in
#: lightness so it survives grayscale, and bundled with matplotlib.
SEQUENTIAL = "cividis"

# --------------------------------------------------------------------------
# Sizing
# --------------------------------------------------------------------------

#: Pixel dimensions are what a README displays; dots per inch only converts
#: between those pixels and the inch-and-point units matplotlib draws in. This
#: value is chosen so nominal point sizes below land at comfortable on-screen
#: sizes rather than needing fractional values.
DPI = 150

#: Named canvas sizes in pixels. A GitHub README renders its content column at
#: roughly 900 px, so 1800 px wide is drawn at about twice display size and stays
#: sharp on high-density screens and when opened on its own.
SIZES = {
    "wide": (1800, 900),
    "standard": (1800, 1200),
    "compact": (1200, 1200),
    "tall": (1800, 1400),
    #: Two panels stacked. Side by side, a panel is too narrow to hold a legend
    #: that names its methods by what they do rather than by their jargon, and the
    #: legend ends up over the data. Full width leaves room beside the curves.
    "stacked": (1800, 1500),
}

#: Fixed pixel allocations, so a figure's proportions do not depend on how much
#: text it happens to carry.
TITLE_BLOCK_PX = 96
DESCRIPTION_BLOCK_PX = 156
#: Room below the drawing area for tick labels and the axis label, so the
#: description block never collides with the axis it sits under.
XAXIS_BLOCK_PX = 74
MARGIN_PX = {"left": 108, "right": 40, "top": 26, "bottom": 22}

TITLE_SIZE = 15
#: Set to the description size. The subtitle carries the finding and is read
#: first, but it is near-black against the description's muted gray, and that
#: difference carries the hierarchy without a difference in size as well.
SUBTITLE_SIZE = 9.5
DESCRIPTION_SIZE = 9.5
LABEL_SIZE = 9.5
TICK_SIZE = 9.5
LEGEND_SIZE = 9.5
#: In-plot annotations sit below the region labels and the subtitle in the
#: hierarchy, so they are smaller and italic rather than competing with them.
ANNOTATION_SIZE = 8.5

#: Descriptions carry one idea per sentence, which takes more sentences than it
#: takes words. The fixed block height is the real bound on length; this only
#: catches a description that has become a paragraph of run-ons.
MAX_SENTENCES = 12

#: Mean glyph advance of DejaVu Sans as a fraction of point size, used to turn an
#: available width into a character count for wrapping.
_CHAR_WIDTH = 0.545


def apply_style() -> None:
    """Set the drawing defaults every figure in the set inherits."""
    plt.rcParams.update(
        {
            "figure.dpi": DPI,
            "savefig.dpi": DPI,
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "text.color": INK,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "axes.labelsize": LABEL_SIZE,
            "axes.labelweight": "bold",
            "axes.titlesize": TITLE_SIZE,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "xtick.color": INK,
            "ytick.color": INK,
            "xtick.labelsize": TICK_SIZE,
            "ytick.labelsize": TICK_SIZE,
            "xtick.top": True,
            "ytick.right": True,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.fontsize": LEGEND_SIZE,
            "legend.frameon": True,
            "legend.framealpha": 0.92,
            "legend.edgecolor": GRID,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FigureText:
    """The words a figure carries, held once and used for both canvas and README.

    The title states what is plotted, the subtitle states the finding rather than
    restating the title, and the description explains in two to four sentences
    what the viewer is looking at and what it shows.
    """

    title: str
    subtitle: str
    description: str
    #: Phrases set bold in the subtitle and description, so a term introduced
    #: above can be found again below. Matched on whole words only.
    emphasize: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        sentences = [s for s in self.description.replace("\n", " ").split(". ") if s.strip()]
        if not 2 <= len(sentences) <= MAX_SENTENCES:
            raise ValueError(
                f"description for {self.title!r} has {len(sentences)} sentences; "
                f"the standard is two to {MAX_SENTENCES}"
            )


class DescriptionOverflow(ValueError):
    """Raised when a description cannot fit its fixed allocation.

    The allocation is fixed so figures keep the same proportions whatever they
    say. Text that exceeds it would otherwise be clipped silently, so it fails
    here instead and the description is shortened.
    """


def _wrap_width(width_px: int) -> int:
    """Characters per line, tied to the drawable width of the canvas."""
    drawable_px = width_px - MARGIN_PX["left"] - MARGIN_PX["right"]
    drawable_points = drawable_px / DPI * 72.0
    return max(20, int(drawable_points / (_CHAR_WIDTH * DESCRIPTION_SIZE)))


def emphasize(text: str, terms: tuple[str, ...]) -> str:
    """Set the given phrases bold, matching whole words only.

    Applied to a description after wrapping, so the markup cannot affect where
    lines break. Bold is slightly wider than regular, which `wrap_description`
    allows for by shortening the line when any term is to be emphasized. Whole
    words only, so emphasizing "flat" cannot reach inside "flatten".
    """
    import re

    for term in terms:
        bold = r"$\bf{" + term.replace(" ", r"\ ") + "}$"
        text = re.sub(rf"\b{re.escape(term)}\b", bold.replace("\\", "\\\\"), text)
    return text


def wrap_subtitle(text: str, width_px: int) -> str:
    """Wrap a subtitle to the canvas width.

    A subtitle is usually one line, and the block that holds it is sized from
    what it wraps to rather than fixed, so a figure whose subtitle carries the
    definitions a reader needs is given the room instead of being compressed
    into it. Every other block stays fixed, so proportions still do not depend
    on how much text a figure happens to carry below the subtitle.
    """
    drawable_points = (width_px - MARGIN_PX["left"] - MARGIN_PX["right"]) / DPI * 72.0
    width = max(20, int(drawable_points / (_CHAR_WIDTH * SUBTITLE_SIZE)))
    return textwrap.fill(" ".join(text.split()), width=width)


def wrap_description(text: str, width_px: int, terms: tuple[str, ...] = ()) -> str:
    """Wrap a description to the canvas width, refusing text that will not fit."""
    width = _wrap_width(width_px) - (2 if terms else 0)
    wrapped = textwrap.fill(" ".join(text.split()), width=width)
    lines = wrapped.count("\n") + 1
    line_px = DESCRIPTION_SIZE * 1.45 / 72.0 * DPI
    if lines * line_px > DESCRIPTION_BLOCK_PX:
        allowed = int(DESCRIPTION_BLOCK_PX / line_px)
        raise DescriptionOverflow(
            f"description wraps to {lines} lines at this width; the fixed "
            f"allocation holds {allowed}. Shorten it rather than enlarging the block."
        )
    return emphasize(wrapped, terms)


def canvas_area(text: FigureText, size: str = "wide",
                extra_left_px: int = 0) -> tuple[Figure, tuple[float, float, float, float]]:
    """A figure carrying its text blocks, and the rectangle left for drawing.

    Callers that need one axes use `canvas`; callers laying out several panels
    take the rectangle and subdivide it, so every figure in the set keeps the
    same blocks in the same places whatever it draws inside them.
    """
    apply_style()
    width_px, height_px = SIZES[size]
    fig = plt.figure(figsize=(width_px / DPI, height_px / DPI), dpi=DPI)

    body = wrap_description(text.description, width_px, text.emphasize)
    heading = wrap_subtitle(text.subtitle, width_px)

    subtitle_line_px = SUBTITLE_SIZE * 1.5 / 72.0 * DPI
    title_block_px = max(
        TITLE_BLOCK_PX,
        TITLE_SIZE * 1.9 / 72.0 * DPI + (heading.count("\n") + 1) * subtitle_line_px + 18,
    )

    # Wider tick labels need a wider margin, or a two-line axis name runs off the
    # canvas. Measured rather than guessed: the carbon dioxide panel's label
    # reached 7.6 px past the left edge before this was added.
    left = (MARGIN_PX["left"] + extra_left_px) / width_px
    right = 1 - MARGIN_PX["right"] / width_px
    axes_top = 1 - (MARGIN_PX["top"] + title_block_px) / height_px
    axes_bottom = (
        MARGIN_PX["bottom"] + DESCRIPTION_BLOCK_PX + XAXIS_BLOCK_PX
    ) / height_px

    middle = (left + right) / 2
    fig.text(middle, 1 - MARGIN_PX["top"] / height_px, text.title,
             ha="center", va="top", fontsize=TITLE_SIZE, fontweight="bold", color=INK)
    fig.text(middle, 1 - (MARGIN_PX["top"] + TITLE_SIZE * 1.9 / 72 * DPI) / height_px,
             emphasize(heading, text.emphasize), ha="center", va="top",
             fontsize=SUBTITLE_SIZE, color=INK, linespacing=1.5)
    fig.text(left, (MARGIN_PX["bottom"] + DESCRIPTION_BLOCK_PX) / height_px,
             body, ha="left", va="top", fontsize=DESCRIPTION_SIZE, color=MUTED,
             linespacing=1.45)
    return fig, (left, axes_bottom, right - left, axes_top - axes_bottom)


def canvas(text: FigureText, size: str = "wide") -> tuple[Figure, plt.Axes]:
    """A figure with its text blocks and a single drawing area."""
    fig, rect = canvas_area(text, size)
    return fig, fig.add_axes(rect)


# --------------------------------------------------------------------------
# Repeated elements
# --------------------------------------------------------------------------


def fit_window_band(ax: plt.Axes, start, end, label: str | None = None) -> None:
    """Shade the months the model was fitted on. The reconstruction stays unshaded.

    The fill is faint because the series running through it is continuous: the
    band says which months the fit used, not that the chart changes. Its own
    edge marks where the window opens, so nothing further is drawn there.
    """
    ax.axvspan(start, end, facecolor=FIT_BAND, edgecolor=FIT_BAND_EDGE,
               linewidth=0.9, zorder=0, label=label)


def fitted_range(ax: plt.Axes, low: float, high: float) -> None:
    """Draw the bounds of a covariate's fitted range as apparatus.

    The bounds are drawn dashed and in the neutral apparatus tone rather than a
    support hue, because they are reference lines by which points are classified
    and not a category of their own. Which side of them a point falls on is
    carried by the point.
    """
    for bound in (low, high):
        ax.axhline(bound, color=BOUNDARY, linewidth=1.3, linestyle=(0, (7, 4)), zorder=2)


def axis_label(name: str, unit: str | None = None) -> str:
    """One axis label, name and unit together.

    Labels are set bold and small by `apply_style`, which keeps the hierarchy
    against the description block below without letting the label dominate.
    """
    return name if unit is None else f"{name} ({unit})"


def mirror_ticks(ax: plt.Axes) -> None:
    """Ticks on all four sides, labeled only on the left and bottom.

    A boxed plot reads as complete with ticks all round, and values on the right
    become readable without tracking across the full width.
    """
    for which in ("major", "minor"):
        ax.tick_params(which=which, top=True, right=True,
                       labeltop=False, labelright=False)


def five_year_ticks(ax: plt.Axes, first_year: int, last_year: int) -> None:
    """Major ticks every five years from a round start, with the endpoint named.

    The automatic choice starts wherever the data happens to and steps by
    whatever interval fits, which reads as arbitrary on a record whose start and
    end both carry meaning.
    """
    import datetime as _dt

    from matplotlib.dates import DateFormatter, YearLocator, date2num
    from matplotlib.ticker import FixedLocator

    years = list(range(first_year, last_year + 1, 5))
    if last_year not in years:
        years.append(last_year)
    ax.xaxis.set_major_locator(FixedLocator([date2num(_dt.date(y, 1, 1)) for y in years]))
    ax.xaxis.set_major_formatter(DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(YearLocator(1))


def even_year_ticks(ax: plt.Axes, first_year: int, last_year: int) -> None:
    """Major ticks evenly spaced from the first year to the last, annual minors.

    `five_year_ticks` appends the endpoint when it does not fall on a multiple of
    five, which leaves a short final gap against long ones elsewhere. Here the
    step is chosen so the last label lands on the end of the axis and every gap
    is the same.
    """
    import datetime as _dt

    from matplotlib.dates import DateFormatter, YearLocator, date2num
    from matplotlib.ticker import FixedLocator

    span = last_year - first_year
    step = next((s for s in (5, 4, 3, 2, 1) if span % s == 0), 1)
    years = list(range(first_year, last_year + 1, step))
    ax.xaxis.set_major_locator(FixedLocator([date2num(_dt.date(y, 1, 1)) for y in years]))
    ax.xaxis.set_major_formatter(DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(YearLocator(1))


def label_period(ax: plt.Axes, start, end, text: str, y: float = 0.965) -> None:
    """Name a span of the axis in place, centered over it.

    Set bold, so the two region names read as structure rather than as one more
    annotation competing with the data.
    """
    middle = start + (end - start) / 2
    ax.annotate(text, xy=(middle, y), xycoords=("data", "axes fraction"),
                ha="center", va="top", fontsize=LEGEND_SIZE,
                fontweight="bold", color=BOUNDARY)


def support_scatter(ax: plt.Axes, x, y, inside: bool, label: str | None = None, **kwargs):
    """Points marked by support status, in both hue and marker shape."""
    style = dict(
        color=INSIDE if inside else OUTSIDE,
        marker=INSIDE_MARKER if inside else OUTSIDE_MARKER,
        linestyle="none",
        markersize=4.4 if inside else 5.0,
        markeredgecolor="white",
        markeredgewidth=0.4,
        zorder=4,
    )
    style.update(kwargs)
    return ax.plot(x, y, label=label, **style)


def support_key(inside_label: str, outside_label: str) -> list[Patch]:
    """Legend handles for support status, carrying hue and hatching together."""
    return [
        Patch(facecolor=INSIDE, edgecolor=INK, hatch=INSIDE_HATCH, label=inside_label),
        Patch(facecolor=OUTSIDE, edgecolor=INK, hatch=OUTSIDE_HATCH, label=outside_label),
    ]


def variant_line(ax: plt.Axes, x, y, variant: str, label: str | None = None, **kwargs):
    """One model variant, separated by line style rather than by hue."""
    style = dict(VARIANT[variant])
    style.update(kwargs)
    return ax.plot(x, y, label=label, zorder=3, **style)


def legend(ax: plt.Axes, handles=None, labels=None, loc: str = "upper left", **kwargs):
    """Legend placed inside the axes, off the data.

    A legend is the default wherever more than one series or category appears.
    Where a single element can be labeled in place without ambiguity, direct
    labeling is preferred and no legend is drawn.
    """
    options = dict(loc=loc, borderpad=0.6, labelspacing=0.5, handlelength=2.4)
    options.update(kwargs)
    if handles is None:
        return ax.legend(**options)
    return ax.legend(handles=handles, labels=labels, **options)


def annotate(ax: plt.Axes, text: str, xy, xytext, **kwargs):
    """In-place label, used where it replaces a legend entry."""
    options = dict(fontsize=ANNOTATION_SIZE, style="italic", color=INK,
                   ha="left", va="center",
                   arrowprops=dict(arrowstyle="->", color=MUTED, linewidth=0.9,
                                   shrinkA=2, shrinkB=4))
    options.update(kwargs)
    return ax.annotate(text, xy=xy, xytext=xytext, **options)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def scale_bar(ax: plt.Axes, length_m: float, divisions: int = 4,
              corner: tuple[float, float] = (0.05, 0.10)) -> None:
    """A divided bar of known ground length, on a panel drawn in meters.

    Divisions let a reader measure a fraction of the bar rather than only its
    whole, and the backing keeps it legible over dark imagery. It replaces a
    stated scale, which is wrong as soon as the figure is resized.
    """
    from matplotlib.patches import FancyBboxPatch, Rectangle

    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    w, h = x1 - x0, y1 - y0
    x, y = x0 + corner[0] * w, y0 + corner[1] * h
    bar_h = 0.011 * h
    step = length_m / divisions

    ax.add_patch(FancyBboxPatch(
        (x - 0.035 * w, y - 0.028 * h), length_m + 0.07 * w, 0.085 * h,
        boxstyle="round,pad=0.002", facecolor="white", alpha=0.78,
        edgecolor="none", zorder=6, transform=ax.transData))
    for i in range(divisions):
        ax.add_patch(Rectangle((x + i * step, y), step, bar_h,
                               facecolor=INK if i % 2 == 0 else "white",
                               edgecolor=INK, linewidth=0.7, zorder=7))
    for value in (0, length_m):
        ax.annotate(f"{value:g}" if value else "0",
                    xy=(x + value, y + bar_h * 1.5), ha="center", va="bottom",
                    fontsize=7.4, color=INK, zorder=8)
    ax.annotate("m", xy=(x + length_m + 0.012 * w, y + bar_h * 0.4), ha="left",
                va="center", fontsize=7.4, color=INK, zorder=8)


def north_arrow(ax: plt.Axes, at: tuple[float, float] = (0.94, 0.13),
                size: float = 0.075) -> None:
    """A north arrow, for a panel that carries nothing else to orient by.

    Only warranted where orientation is otherwise unstated. A panel with a
    coastline, a state outline or a compass already says which way is up.
    """
    x, y = at
    ax.annotate("", xy=(x, y + size), xytext=(x, y - size * 0.35),
                xycoords="axes fraction", textcoords="axes fraction", zorder=8,
                arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=1.5,
                                mutation_scale=15,
                                path_effects=[_outline()]))
    ax.annotate("N", xy=(x, y + size * 1.12), xycoords="axes fraction",
                ha="center", va="bottom", fontsize=ANNOTATION_SIZE,
                fontweight="bold", color=INK, zorder=8,
                path_effects=[_outline()])


def _outline():
    """A thin light halo, so small text stays legible over imagery."""
    from matplotlib import patheffects
    return patheffects.withStroke(linewidth=2.4, foreground="white")


def credit(ax: plt.Axes, text: str, xy: tuple[float, float] = (0.5, 0.012),
           va: str = "bottom", ha: str = "center") -> None:
    """In-panel attribution for imagery or a published layer.

    Anything drawn from someone else's data says so inside the panel, because a
    figure separated from its caption still has to carry its sources.
    """
    ax.annotate(text, xy=xy, xycoords="axes fraction", ha=ha, va=va,
                fontsize=7.6, color=INK, zorder=7, path_effects=[_outline()])


def panel_letter(ax: plt.Axes, letter: str, label: str | None = None,
                 size: float = LEGEND_SIZE) -> None:
    """Mark a panel so the description can refer to it without naming positions.

    A label placed here rather than on the axis keeps a long axis name from
    reaching into the title block, and names the panel where a reader looks
    first. Where the label is the main distinction between panels rather than a
    cross-reference, it is set larger than a legend entry. It takes the corner the
    legend does not, so the two never contend for the same one.
    """
    text = f"({letter})" if label is None else f"({letter})  {label}"
    ax.annotate(text, xy=(0.014, 0.986), xycoords="axes fraction",
                ha="left", va="top", fontsize=size, fontweight="bold",
                color=INK, zorder=8, path_effects=[_outline()])


def panel_name(ax: plt.Axes, name: str, y: float = 0.952, align: str = "left") -> None:
    """Name a panel in a bordered box, which carries the emphasis size otherwise would.

    Used where the panels differ in what they show rather than in which step of an
    argument they carry, so the name is the label and no letter is needed. Seated
    below the top of the axes rather than against it: the padded box is drawn
    outside the text extent, so an anchor that measures as inside can still cross
    the spine.
    """
    x = 0.016 if align == "left" else 0.984
    ax.annotate(name, xy=(x, y), xycoords="axes fraction", ha=align, va="top",
                fontsize=LEGEND_SIZE + 1.6, fontweight="bold", color=INK, zorder=9,
                bbox=dict(boxstyle="round,pad=0.42", facecolor="white",
                          edgecolor=BOUNDARY, linewidth=0.9))


def figures_dir() -> Path:
    """Directory the figure set is written to, tracked so the README resolves."""
    return paths.repo_root() / "figures"


def save(fig: Figure, stem: str) -> Path:
    """Write one figure as a portable network graphic and return its path."""
    directory = figures_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{stem}.png"
    fig.savefig(target, dpi=DPI, facecolor="white")
    plt.close(fig)
    return target


def readme_block(text: FigureText, stem: str) -> str:
    """The same words as markdown, so the README and the canvas cannot diverge."""
    body = " ".join(text.description.split())
    return (
        f"### {text.title}\n\n"
        f"![{text.title}](figures/{stem}.png)\n\n"
        f"**{text.subtitle}**\n\n"
        f"{body}\n"
    )
