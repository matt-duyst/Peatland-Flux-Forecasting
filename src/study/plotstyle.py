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
from matplotlib.lines import Line2D
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
# whether a wind sector is retained or discarded and for whether the site was
# gathered into FLUXNET-CH4. They are the strongest separation in the set, 111.7
# apart under deuteranopia and 93.3 under protanopia.
#
#   FITTED  #009E73  the range across the eight fitted models, and on the
#                    seasonal split what the average year leaves
#   SITE    #F0E442  the site, and the tower on it
#
# `FITTED` is where this rule bends, and it has bent further than it was written
# to. It carries five meanings across six figures:
#
#   forecast error by horizon        the range across the eight fitted models
#   observed and predicted           the same range, month by month
#   measurements used across horizons  how often each measurement was chosen
#   seasonal cycle                   what the average year leaves
#   residual distribution check      the 115 months the model was fitted on
#   prediction error by year         the months of the panel's own year
#
# The first three are the original scoping and the reason for it: the study's
# halves ask different questions, the reconstruction figures being about support
# and the forecast figures about method, so neither set needs the other's
# encoding. A second blue was tried on the forecast figures and removed, because
# blue already means retained. The alternative on the seasonal split was a fifth
# hue for one row of three on a single figure.
#
# The last two were added later and are not covered by that reasoning. The
# residual check is close to it, since the 115 months are the fitted ones. The
# prediction error use is the loosest in the set: there green means the year a
# panel is about, against grey for every other year, which has nothing to do
# with fitting anything. It is recorded rather than repainted because neither
# late use collides. Both sit against grey alone, with no blue or orange on the
# panel, so the scoping still holds on the page even where the sentence naming
# it no longer describes what is drawn.
#
# The flux figure's use is the one the audit missed, and how it was missed is
# worth as much as the count. The sweep that produced this list grepped for
# `ps.FITTED` and filtered out lines containing `FITTED_FILL_ALPHA` to drop
# alpha constants, which is exactly how that figure writes its fill:
#
#     facecolor=ps.FITTED, alpha=ps.FITTED_FILL_ALPHA,
#
# So the one use with no recorded justification was invisible to the audit that
# existed to find unrecorded uses, and an audit written the same way would miss
# it again. Grep for the name and read every hit.
#
# Its justification, recorded now: grey is already doing three jobs on that
# panel, the uncertainty band on the measurement, the seasonal average's line,
# and the span marking where forecasts exist. A fourth grey for the model range
# would be indistinguishable from the first, which is the band it has to be read
# against.
#
# What this does not license is reaching for green as a general accent. Six
# figures is where it stops.
#
# `SITE` marks the flux tower in the site panel and the same site among the
# network in the panel beside it. A reader meeting a star in both panels assumes
# it means the same thing, and it does. It carries a dark casing in both, because
# it measures 0.161 in luminance from the pale state fill and 0.207 from the
# brightest ground near the tower, and a white casing would vanish on the first.
#
# Anything else carrying a hue is cartography rather than encoding, is local to
# the panel it appears on, and is not a general-purpose accent. The mapped
# wetland boundary is the only such case: heavy white over a dark casing, which
# separates from its thin white neighbors by weight rather than by hue.
#
# **None of these is available for reuse on a new figure without first checking
# what it already means.** That check has failed twice: sky blue was introduced
# for the fitted range beside a blue that meant retained, and the support orange
# was borrowed for the wetland boundary beside an orange that meant discarded.
# Both were caught after the figure was built rather than before.
INSIDE = "#0072B2"
OUTSIDE = "#D55E00"

#: How much of a measurement the date alone predicts, beside how often the models
#: used it. Achromatic because it is a property of the measurement rather than a
#: result, and lighter than `FITTED` so it reads as the quieter of the two. Chosen
#: by measurement: 16.7 from the green under the worst simulated deficiency and
#: 0.140 in relative luminance, against 11.7 and 0.076 for the mid gray, which is
#: too close to it, and 17.5 from the gridlines so a bar cannot merge with one.
DATE_SHARE = "#A9A9A9"

#: Every bar on the availability figure that is not the fitted range. Neutral, so
#: the only colored marks on that panel are the two that carry meaning: orange for
#: months a decision discarded, blue for the range the model was fitted on. It
#: clears the orange by **54.5 under the worst simulated deficiency and 0.147 in
#: relative luminance**, which matters because the discard outlines are drawn on
#: top of these bars. Reddish purple was measured and set aside for that reason:
#: Okabe-Ito's #CC79A7 sits **0.9 from the orange under tritanopia**, and a darker
#: plum that cleared it added a fifth hue to the set for rows that are context.
MEASURED = "#4D4D4D"

#: The average year on the seasonal split, light enough to read as a line rather
#: than as a weight beside the two below it. Achromatic no longer: that row now
#: takes `INSIDE`, which is the study's own benchmark, so this constant is kept
#: only for the width of the line it is drawn at.
SEASONAL_SHAPE_WIDTH = 1.1

#: The site and its tower, on the site map only. Okabe-Ito yellow, measured
#: against the imagery it sits on: 41.3 from the light peat beside the tower and
#: 101.5 from the dark forest, under the worst simulated deficiency.
SITE = "#F0E442"

#: The fitted models in the two forecast figures, and what the average year leaves
#: on the seasonal split, per the two scopes named in the convention above.
#: Okabe-Ito bluish green, chosen by measurement: it clears `INSIDE` by 20.9 and
#: `OUTSIDE` by 35.9 under the worst simulated deficiency. Reddish purple was measured and rejected at **0.9 against
#: `OUTSIDE` under tritanopia**: the band edges and the legend patch are drawn in
#: the pure hue, so a reader would meet the same color carrying two meanings.
FITTED = "#009E73"
#: Alpha for the fill under what the average year leaves, on the seasonal split.
#: Heavier than a line so the row carries weight, light enough that the zero rule
#: and the gridlines read through it.
LEFTOVER_FILL_ALPHA = 0.5

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
    #: Three rows of two panels, with a label band over each row. The stacked
    #: height was set for two rows and leaves these at about half the canvas.
    #: Wider than the rest of the set: three rows of two time series, each needing
    #: a name in the gutter and a unit on its axis, do not fit the standard width.
    "triple": (2300, 1900),
    #: Two square panels side by side. A one-to-one plot has to be square, so the
    #: height is set by what the width leaves rather than chosen: any more and the
    #: canvas carries empty ground under the panels.
    "square pair": (1800, 1300),
    #: Two panels stacked. Side by side, a panel is too narrow to hold a legend
    #: that names its methods by what they do rather than by their jargon, and the
    #: legend ends up over the data. Full width leaves room beside the curves.
    "stacked": (1800, 1500),
    #: One row of small multiples per gas, one column per evaluated year. Wider
    #: than the standard so eight columns each keep about 244 px, which is what a
    #: panel needs before its points start to merge. The height is set so those
    #: panels come out a little taller than they are wide rather than half as
    #: tall: these are residual panels and vertical position is what is read off
    #: them, so height is the dimension that cannot be given away. It came down
    #: 120 px when the key moved into the gap the methane row leaves at its left,
    #: which freed the band that had held the key under both rows.
    "year grid": (2300, 1185),
    #: Two rows of two square panels, each holding one comparison of the same
    #: residuals against one distribution. Square because the reference is a line
    #: of equality, which has to sit at 45 degrees or distance from it cannot be
    #: read. The width sets the panel side, and the height is then whatever makes
    #: them square at that side rather than a number chosen first: set shorter,
    #: the panels shrink and leave empty margins either side of the pair. Two rows
    #: of square panels under a text stack of about 750 px is a taller canvas than
    #: it is wide, which is why this is the one portrait size in the set.
    "quad": (1560, 2065),
}

#: How a count is written in a text block. Large or precise counts are numerals,
#: small counts of things a reader can see on the panel are spelled: "115
#: months" and "12 of the 57" against "two hollow marks" and "six below". The
#: line is not arbitrary. A numeral is read as a measurement and a word as a
#: quantity, so a figure that says "seventeen of these nineteen years" beside
#: another saying "12 of the 57 evaluated months" has written one measurement
#: two ways. Where a sentence carries several counts they take one form, since
#: mixing them inside one clause reads worse than either choice does alone.
#:
#: Years, percentages and measured values are always numerals and are not
#: counts, so they do not enter into this.

#: The least air `balance_drawing_block` will leave between the drawing block and
#: the text above and below it. Reached only where the block does not fit, which
#: is where growing cannot help and something has to give.
MIN_BLOCK_GAP_PX = 18.0

#: Fixed pixel allocation, so a figure's proportions do not depend on how much
#: text it happens to carry. There was a `TITLE_BLOCK_PX = 96` floor beside this
#: one, under the title and subtitle. It never bound: the block those two need is
#: their own measured height, which runs 137 to 226 px across the set, so the
#: floor was below every figure that ever tested it. It arrived with the original
#: scaffolding and was never revisited, and it is gone rather than retuned.
DESCRIPTION_BLOCK_PX = 156
#: Room below the drawing area for tick labels and the axis label, so the
#: description block never collides with the axis it sits under.
XAXIS_BLOCK_PX = 74
#: Top and bottom are equal because they are the two the eye compares: the
#: title's first line against the canvas top, and the description's last against
#: the canvas bottom. They were 26 and 22, and the four pixels between them were
#: never the reason the figures looked unevenly bounded. That was the block
#: below being fixed at five lines while every description in the set uses three
#: or four, so the unused rows fell out as white space at the canvas edge. The
#: description is now set from the bottom of its block rather than the top,
#: which puts the slack between the axis label and the text, where it reads as
#: air inside the figure rather than a broken margin.
MARGIN_PX = {"left": 108, "right": 40, "top": 26, "bottom": 26}

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

#: Air between the title and the subtitle, and between the subtitle and the
#: drawing area, for figures that ask for the text blocks to be measured rather
#: than allotted. The allotment reserves a share of the title's own height, so
#: the gap a reader sees below a title doubles when the title wraps to two lines;
#: measuring keeps it the same whatever the title does.
TEXT_GAP_PX = 26

#: Descriptions carry one idea per sentence, which takes more sentences than it
#: takes words. The fixed block height is the real bound on length; this only
#: catches a description that has become a paragraph of run-ons.
MAX_SENTENCES = 12

#: Mean glyph advance of DejaVu Sans as a fraction of point size, used to turn an
#: available width into a character count. Titles and subtitles still wrap this
#: way; descriptions no longer do. Measured over the set's own description text
#: the true mean is 0.5055, so this is 7.8% too wide and every line it sets falls
#: short of the measure. It is not a bad estimate that can be corrected, though.
#: A character count has to cover the widest line rather than the mean, and the
#: widest line in the set runs 11.2% above the corpus mean, so no single value is
#: both tight and safe: at the true mean seven of eleven descriptions overflowed,
#: and the sequence is not even monotone, since 0.515 overflows more figures than
#: 0.520 does. 0.545 is near the tightest value that never overflows, and the 3
#: to 9% of width it leaves is the price of counting characters at all. That is
#: why descriptions are measured instead. Titles and subtitles keep the estimate
#: because changing how they wrap changes the height of the block above every
#: panel, which is a separate decision from how the block below them is set.
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


_MEASURING: Figure | None = None


def _measurer() -> tuple[Figure, object]:
    """A scratch canvas kept for measuring text, built once and reused.

    Every measurement needs a renderer, and making one per string is what made
    measuring look expensive enough to estimate around in the first place.
    """
    global _MEASURING
    if _MEASURING is None:
        _MEASURING = plt.figure(figsize=(1, 1), dpi=DPI)
        _MEASURING.canvas.draw()
    return _MEASURING, _MEASURING.canvas.get_renderer()


def text_width_px(text: str, size: float) -> float:
    """Rendered width of a string at the set's font, in pixels."""
    if not text:
        return 0.0
    fig, renderer = _measurer()
    drawn = fig.text(0, 0, text, fontsize=size)
    width = drawn.get_window_extent(renderer=renderer).width
    drawn.remove()
    return width


def _wrap_measured(body: str, limit_px: float, size: float) -> list[str]:
    """Greedy wrap on rendered width rather than on a character count."""
    lines: list[str] = []
    current = ""
    for word in body.split():
        trial = f"{current} {word}".strip()
        if current and text_width_px(trial, size) > limit_px:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _balance_measured(body: str, limit_px: float, size: float) -> list[str]:
    """Wrap to the narrowest measure that still uses the same number of lines.

    The measured analogue of `_balance`, and it is here for the same reason.
    Filling to the edge leaves whatever the last line happens to inherit, which
    on this set was a description ending in a four-character line under four
    full ones. Holding the line count and pulling the measure in spreads the
    words evenly instead, and because the count is held no block changes height
    and nothing below the description moves.
    """
    lines = len(_wrap_measured(body, limit_px, size))
    if lines <= 1:
        return [body]
    low, high = 1.0, limit_px
    while high - low > 0.5:
        middle = (low + high) / 2
        if len(_wrap_measured(body, middle, size)) <= lines:
            high = middle
        else:
            low = middle
    return _wrap_measured(body, high, size)


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


def wrap_title(text: str, width_px: int) -> str:
    """Wrap a title to the canvas width.

    Titles are one line in this set and the block is sized for one, but a title
    naming both the site and what is being varied can outrun the canvas. It wraps
    rather than being cut or shrunk: the size carries the hierarchy, and a title
    that runs off the edge is the one failure a reader cannot work around.
    """
    drawable_points = (width_px - MARGIN_PX["left"] - MARGIN_PX["right"]) / DPI * 72.0
    width = max(20, int(drawable_points / (_CHAR_WIDTH * 1.09 * TITLE_SIZE)))
    return textwrap.fill(" ".join(text.split()), width=width)


def _balance(text: str, width: int) -> str:
    """Wrap to the narrowest width that still uses the same number of lines.

    A centred block is not justified, it is balanced. Setting flush edges on a
    centred display line is the wrong instrument twice over: the last line of a
    justified block is never stretched, so a two-line subtitle would end up with
    one flush line above one ragged one, and stretching word spaces to reach a
    fixed measure is what body text in a column needs, not a heading. What a
    ragged centred block actually wants is lines of similar length, so the shape
    reads as deliberate rather than as the accident of where the wrap fell.

    Binary search finds the narrowest measure that does not spill into another
    line. Because the line count is held, no block changes height and nothing
    below the subtitle moves.
    """
    body = " ".join(text.split())
    lines = textwrap.fill(body, width=width).count("\n") + 1
    if lines == 1:
        return body
    low, high = 1, width
    while low < high:
        middle = (low + high) // 2
        if textwrap.fill(body, width=middle).count("\n") + 1 <= lines:
            high = middle
        else:
            low = middle + 1
    return textwrap.fill(body, width=low)


def wrap_subtitle(text: str, width_px: int) -> str:
    """Wrap a subtitle to the canvas width, balanced across its lines.

    A subtitle is usually one line, and the block that holds it is sized from
    what it wraps to rather than fixed, so a figure whose subtitle carries the
    definitions a reader needs is given the room instead of being compressed
    into it. Every other block stays fixed, so proportions still do not depend
    on how much text a figure happens to carry below the subtitle.

    Where it does run to more than one line, the lines are balanced rather than
    filled. See `_balance` for why a centred block is balanced and not
    justified.
    """
    drawable_points = (width_px - MARGIN_PX["left"] - MARGIN_PX["right"]) / DPI * 72.0
    width = max(20, int(drawable_points / (_CHAR_WIDTH * SUBTITLE_SIZE)))
    return _balance(text, width)


def wrap_description(text: str, width_px: int, terms: tuple[str, ...] = (),
                     extra_left_px: int = 0) -> str:
    """Wrap a description to its measured width, refusing text that will not fit.

    `extra_left_px` is the same shift the drawing area takes, and the description
    starts at it too. Wrapping ignored it while the width was estimated, which
    was safe only because the estimate ran short by more than the shift: the flux
    figure was set as though it had 1652 px when it had 1618, and came out at
    96.9% of an edge it was never measured against. Measuring makes that the
    first thing to overflow, so the shift is taken off the measure here.
    """
    limit = width_px - MARGIN_PX["left"] - extra_left_px - MARGIN_PX["right"]
    if terms:
        # Emphasis is applied after wrapping and bold is wider than regular, so
        # the measure gives back about what two characters would take.
        limit -= text_width_px("nn", DESCRIPTION_SIZE)
    body = " ".join(text.split())
    lines = _balance_measured(body, limit, DESCRIPTION_SIZE)
    line_px = DESCRIPTION_SIZE * 1.45 / 72.0 * DPI
    if len(lines) * line_px > DESCRIPTION_BLOCK_PX:
        allowed = int(DESCRIPTION_BLOCK_PX / line_px)
        raise DescriptionOverflow(
            f"description wraps to {len(lines)} lines at this width; the fixed "
            f"allocation holds {allowed}. Shorten it rather than enlarging the block."
        )
    return emphasize("\n".join(lines), terms)


def _below(fig: Figure, drawn, height_px: int) -> float:
    """Where the next block starts, one gap under what this one occupies."""
    fig.canvas.draw()
    box = drawn.get_window_extent().transformed(fig.transFigure.inverted())
    return box.y0 - TEXT_GAP_PX / height_px


def canvas_area(text: FigureText, size: str = "wide", extra_left_px: int = 0,
                ) -> tuple[Figure, tuple[float, float, float, float]]:
    """A figure carrying its text blocks, and the rectangle left for drawing.

    Callers that need one axes use `canvas`; callers laying out several panels
    take the rectangle and subdivide it, so every figure in the set keeps the
    same blocks in the same places whatever it draws inside them.

    The subtitle and the drawing area are placed against what the blocks above
    them actually occupy. This was `measured_text`, opt-in, so that no figure
    moved without asking, and two figures asked. The allotment it replaces gave
    a title 1.9 times its own point size, 59.4 px for 29 px of ink, so what a
    reader saw below a one-line title was the leftover rather than a chosen
    distance, and it doubled when a title wrapped. Measured, the gap is
    TEXT_GAP_PX whatever the title does, and the drawing area gains the 10 to 20
    px the allotment was holding. Now that every figure takes it there is no
    second behaviour to select, and the flag is gone with the allotment.
    """
    apply_style()
    width_px, height_px = SIZES[size]
    fig = plt.figure(figsize=(width_px / DPI, height_px / DPI), dpi=DPI)

    body = wrap_description(text.description, width_px, text.emphasize,
                            extra_left_px)
    heading = wrap_subtitle(text.subtitle, width_px)
    title = wrap_title(text.title, width_px)

    # Wider tick labels need a wider margin, or a two-line axis name runs off the
    # canvas. Measured rather than guessed: the carbon dioxide panel's label
    # reached 7.6 px past the left edge before this was added.
    left = (MARGIN_PX["left"] + extra_left_px) / width_px
    right = 1 - MARGIN_PX["right"] / width_px
    # `axes_top` is set from the drawn subtitle below. The allotment that used to
    # compute it here, a title-height share plus a subtitle-line count plus 18,
    # went dead the moment every figure measured instead, and it is not kept as a
    # fallback: two ways of placing one edge is how the two drift apart.
    axes_bottom = (
        MARGIN_PX["bottom"] + DESCRIPTION_BLOCK_PX + XAXIS_BLOCK_PX
    ) / height_px

    middle = (left + right) / 2
    drawn_title = fig.text(middle, 1 - MARGIN_PX["top"] / height_px, title,
                           ha="center", va="top", fontsize=TITLE_SIZE,
                           fontweight="bold", color=INK, linespacing=1.35)
    subtitle_at = _below(fig, drawn_title, height_px)
    drawn_subtitle = fig.text(middle, subtitle_at,
                              emphasize(heading, text.emphasize), ha="center",
                              va="top", fontsize=SUBTITLE_SIZE, color=INK,
                              linespacing=1.5)
    axes_top = _below(fig, drawn_subtitle, height_px)
    # Anchored to the floor of its block, not the ceiling. The block stays the
    # same fixed height either way, so `axes_bottom` above is untouched and no
    # panel moves; only where the slack sits changes.
    fig.text(left, MARGIN_PX["bottom"] / height_px,
             body, ha="left", va="bottom", fontsize=DESCRIPTION_SIZE, color=MUTED,
             linespacing=1.45)
    return fig, (left, axes_bottom, right - left, axes_top - axes_bottom)


def balance_drawing_block(fig: Figure, *axes: plt.Axes, rounds: int = 6,
                          extra=(), reflow=None, grow: bool = True) -> None:
    """Give the drawing block the same air above it as below it.

    The gap above is what the title and subtitle blocks leave; the gap below is
    what the description block leaves once its text is set from the floor. The
    two rarely match, and they miss in both directions: a three-line
    description leaves 70 px of its block unused and the panel floats high, a
    five-line one leaves 12 px and the panel sits low against its own axis
    label.

    The block expands into whichever gap is larger until the two agree, so the
    panel only ever grows. That is the point: the fixed description block exists
    so text cannot steal drawing space, and the worst case it protects against,
    a description filling all five lines, is left exactly as it was. Rows the
    text does not use are not a reservation to defend, and the panel claims
    them.

    Pass every panel in the block. A figure whose panels are stacked grows as a
    unit and keeps the proportions between them, so a strip stays the fraction
    of the block it was given rather than absorbing the whole gain.

    Call after everything else is drawn on the axes, since the lower gap is
    measured to the tick labels and axis title rather than the frame.

    `extra` names artists that are part of the block but are not axes and do not
    move with one: figure-level text standing above or below the panels. They are
    measured as ink like any other furniture. Without them the block balances to
    the panels alone and drives whatever sits outside them into a text block,
    which is what a boxed gas label above a row does.

    `grow` may be turned off where the block's size is not the caller's to give
    away. The residual check draws four panels that are square **in pixels**,
    because the reference they carry is a line of equality and a panel that is not
    square puts it at some other angle; growing them vertically to fill a gap
    would break the one thing those panels have to be. With `grow=False` the block
    is translated rather than scaled, both gaps meeting in the middle instead of
    the smaller one being filled, and the caller keeps responsibility for the block
    fitting at all.

    `reflow` is called after every resize. Anything in `extra` has to be put back
    against the panels it belongs to, since moving an axes does not move a figure
    text placed relative to it, and the next round measures against where it now
    is. A caller passing `extra` and no `reflow` gets a stale measurement.

    """
    height_px = fig.get_size_inches()[1] * fig.dpi
    subtitle, description = fig.texts[1], fig.texts[2]

    def ink(renderer):
        boxes = [ax.get_tightbbox(renderer) for ax in axes]
        boxes += [artist.get_window_extent(renderer) for artist in extra]
        return boxes

    def bounds(renderer):
        boxes = ink(renderer)
        return max(b.y1 for b in boxes), min(b.y0 for b in boxes)

    # Iterated, because growing the block moves what it was measured against:
    # taller panels put their tick labels somewhere new, so one pass overshoots
    # wherever the block scales rather than simply shifts.
    for _ in range(rounds):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        # Both gaps are measured to ink rather than to the frame. The lower one
        # always was, because tick labels and an axis title hang below the frame.
        # The upper one was measured to the frame, which is right only where
        # nothing sits above it: the seasonal figure puts a boxed gas label
        # there, and balancing to the frame would push it into the subtitle.
        ceiling, floor = bounds(renderer)
        above = subtitle.get_window_extent(renderer).y0 - ceiling
        below = floor - description.get_window_extent(renderer).y1
        if abs(above - below) < 0.05:
            break
        room = abs(above - below) / height_px

        boxes = [ax.get_position() for ax in axes]
        floor = min(b.y0 for b in boxes)
        ceiling = max(b.y1 for b in boxes)
        span = ceiling - floor
        if not grow:
            # Slid, not stretched. Half the difference moves from one gap to the
            # other and the block keeps its size.
            base, scale = floor - (below - above) / (2 * height_px), 1.0
        elif below > above:
            # The block drops its floor and stretches down into the gap.
            base, scale = floor - room, (span + room) / span
        else:
            # The block keeps its floor and stretches up.
            base, scale = floor, (span + room) / span
        _resize(axes, boxes, floor, base, scale)
        if reflow is not None:
            reflow()

    # Equal is not the whole job. A block can be taller than the space between
    # the two text blocks, and then equalising only shares the overlap out: the
    # availability figure's key gained two headed groups, 58 px of height its
    # layout did not have, and both gaps came to −35 px. Growing is the normal
    # case and is preferred, since rows the description does not use are not a
    # reservation to defend; shrinking happens only when the block does not fit.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    furniture = ink(renderer)
    gap = min(subtitle.get_window_extent(renderer).y0 - max(f.y1 for f in furniture),
              min(f.y0 for f in furniture) - description.get_window_extent(renderer).y1)
    if gap >= MIN_BLOCK_GAP_PX or not grow:
        # Nothing to shrink where the caller has fixed the block's size: the only
        # instrument left would be the one `grow=False` exists to withhold.
        return
    boxes = [ax.get_position() for ax in axes]
    floor = min(b.y0 for b in boxes)
    span = max(b.y1 for b in boxes) - floor
    shrink = 2 * (MIN_BLOCK_GAP_PX - gap) / height_px
    _resize(axes, boxes, floor, floor + shrink / 2, (span - shrink) / span)
    if reflow is not None:
        reflow()


def _resize(axes, boxes, floor: float, base: float, scale: float) -> None:
    """Move and scale a block about its floor, keeping the gaps inside it."""
    for ax, box in zip(axes, boxes):
        ax.set_position((box.x0, base + (box.y0 - floor) * scale,
                         box.width, box.height * scale))



# --------------------------------------------------------------------------
# Naming a group inside a key
# --------------------------------------------------------------------------
#
# The set names a group of legend entries two ways, and which one applies is set
# by where the heading sits rather than by the figure.
#
# **A heading on top of a stacked column is ruled.** The rule is what makes the
# heading govern the entries beneath it: without it a bold row at the head of a
# column is just another entry that happens to be bold, and nothing says how far
# down its authority reaches. Seven headings in the set are of this kind, on the
# reconstruction, forecast, flux, stability, year-grid and residual-check
# figures, and `underline_legend_headings` draws them.
#
# **A heading at the left of a row carries a colon and no rule.** There it
# governs what is beside it rather than what is under it, the extent is given by
# the row itself, and a rule marks nothing the boldness has not already marked.
# A colon is the ordinary separator between a label and what it introduces. One
# key in the set is of this kind, the availability figure's, and it sets its
# headings as `$\bf{...:}$` with no call to the ruler.
#
# The rule lived as a comment on the availability figure's heading constants,
# where it read as a decision about that figure. It is a decision about the set,
# and either form is correct where its own geometry holds.
#
# Both forms have to be drawn after the block is balanced. The rules are figure
# artists at fixed positions, so a panel that moves afterwards leaves them where
# the headings used to be, which struck through two headings for as long as the
# reconstruction figure had been balanced. Where a caller reflows during
# balancing it must also remove the rules it drew, since the ruler adds an
# artist rather than replacing one.

def underline_legend_title(fig, legend) -> None:
    """Rule a legend title, so it reads as the heading rows elsewhere do.

    A title and a blank-handle row are the set's two ways of naming a group. They
    differ in where the text sits, not in what it is, so the rule that marks one
    marks the other and the two read as the same device.
    """
    fig.canvas.draw()
    text = legend.get_title()
    box = text.get_window_extent().transformed(fig.transFigure.inverted())
    y = box.y0 - 0.10 * (box.y1 - box.y0)
    fig.add_artist(Line2D([box.x0, box.x1], [y, y], transform=fig.transFigure,
                          color=INK, linewidth=0.9,
                          zorder=legend.get_zorder() + 1))


def underline_legend_headings(fig, ax, center: bool = False) -> None:
    """Rule each legend heading, which mathtext cannot do itself.

    Drawn on the figure rather than the axes so it does not appear in `ax.lines`,
    where the checks that keep the legend off the data would then see it.

    With `center`, each heading is first moved to the middle of the column it
    heads. A legend column runs from the left edge of its handles to the right
    edge of its longest label, and a heading left-aligned with the labels sits
    off to one side of that, reading as another entry rather than as the name of
    the group. The rule is drawn after the move so it follows the text.
    """
    fig.canvas.draw()
    legend = ax.get_legend()
    headings = [text for text in legend.get_texts()
                if text.get_text().startswith("$")]
    if center:
        _center_legend_headings(fig, legend, headings)
        fig.canvas.draw()
    for text in headings:
        box = text.get_window_extent().transformed(fig.transFigure.inverted())
        y = box.y0 - 0.10 * (box.y1 - box.y0)
        fig.add_artist(Line2D([box.x0, box.x1], [y, y], transform=fig.transFigure,
                              color=INK, linewidth=0.9,
                              zorder=legend.get_zorder() + 1))


def _center_legend_headings(fig, legend, headings) -> None:
    """Move each heading to the middle of its own column.

    Columns are recovered from the drawn artists rather than from the layout
    arguments: matplotlib does not expose which entry went into which column,
    but every entry in one column shares a label left edge, so grouping on that
    edge recovers the columns whatever `ncol` was.
    """
    renderer = fig.canvas.get_renderer()
    columns: dict[int, list] = {}
    for handle, text in zip(legend.legend_handles, legend.get_texts()):
        label = text.get_window_extent()
        try:
            mark = handle.get_window_extent(renderer)
            left = min(mark.x0, label.x0)
        except (AttributeError, TypeError, RuntimeError):
            left = label.x0
        columns.setdefault(round(label.x0), []).append((text, left, label.x1))

    for heading in headings:
        column = next(rows for rows in columns.values()
                      if any(text is heading for text, _, _ in rows))
        spans = [(left, right) for text, left, right in column
                 if text is not heading]
        if not spans:
            continue
        middle = (min(left for left, _ in spans) + max(right for _, right in spans)) / 2
        box = heading.get_window_extent()
        _, y = heading.get_position()
        moved = heading.get_transform().inverted().transform(
            (box.x0 + middle - (box.x0 + box.x1) / 2, box.y0))
        heading.set_position((moved[0], y))

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
    # Minor ticks are what a reader counts along to find an unlabeled year, so
    # they are given enough weight to be countable rather than left hairline.
    ax.tick_params(which="minor", width=0.9, length=3.2)
    ax.tick_params(which="major", width=1.0, length=5.0)


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


def even_year_ticks(ax: plt.Axes, first_year: int, last_year: int,
                    label_every_year: bool = False) -> None:
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
    if label_every_year:
        # The minors were always drawn here and never named, so a reader counted
        # along from a major to find a year. Naming them is what the
        # reconstruction figure does: the grid stays on the majors, and every
        # year carries its label. It also removes the reason the step lands
        # where it does, which on a sixteen-year span is four rather than five.
        ax.xaxis.set_minor_formatter(DateFormatter("%Y"))
        ax.tick_params(axis="x", which="minor", labelbottom=True,
                       labelsize=TICK_SIZE)


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


def blended(ax: plt.Axes):
    """x in axes fractions, y in data units, for marks seated against an edge."""
    from matplotlib.transforms import blended_transform_factory

    return blended_transform_factory(ax.transAxes, ax.transData)


def panel_name(ax: plt.Axes, name: str, y: float = 0.952, align: str = "left",
               x: float | None = None) -> None:
    """Name a panel in a bordered box, which carries the emphasis size otherwise would.

    Used where the panels differ in what they show rather than in which step of an
    argument they carry, so the name is the label and no letter is needed. Seated
    below the top of the axes rather than against it: the padded box is drawn
    outside the text extent, so an anchor that measures as inside can still cross
    the spine. `x` overrides the inset for a panel whose corner is not free, so a
    name can sit outside the axes without a second way of drawing the same box.
    """
    if x is None:
        # Axes fractions are fractions of the drawn panel, not of the room it sits
        # in: the rotated axis name and the tick labels stand outside the axes, so
        # 0.5 is the middle of the frame a reader sees rather than the middle of
        # the frame plus its left gutter. Centring on the tight bounding box
        # instead would pull the name left by half the gutter.
        x = {"left": 0.016, "center": 0.5}.get(align, 0.984)
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
