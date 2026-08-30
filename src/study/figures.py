"""One function per figure, each taking prepared data and returning a figure.

Nothing here reads a file or computes a study result. Each function receives the
frames the study modules already produce and is responsible only for drawing, so
a figure can be built in a test from a few synthetic rows.

Shared drawing decisions live in `plotstyle`; the words each figure carries live
beside it here, as a `FigureText`, and reach the README through the same object.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap, to_rgba
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerBase, HandlerPatch
from matplotlib.patches import FancyArrow
from matplotlib.patches import Patch
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator, NullFormatter, ScalarFormatter
from matplotlib.transforms import blended_transform_factory

from forecast import evaluation, experiment, features, screening
from study import plotstyle as ps
from study import windows

#: Re-exported so a figure and the tables it sits beside cannot disagree about
#: which months the study fitted on. Defined in `study.windows`, which is what
#: every script builds its windows from.
WATER_TABLE_ARTIFACTS = windows.WATER_TABLE_ARTIFACTS

WATER_TABLE_TEXT = ps.FigureText(
    title="Monthly water table elevation at Marcell Bog Lake Peatland (1990 to 2019)",
    subtitle=(
        "Water table is one of the two measurements the reconstruction reads, and "
        "methane rises as it rises. The model only ever saw it across a 0.33 m band, "
        "because the flux record opens in 2009 after a decade of decline. Projecting "
        "back to 1990 asks for 0.29 m above that band, an excursion nearly as wide as "
        "the range the model was fitted on."
    ),
    description=(
        "Each point is one month's mean, and the shaded band marks the 115 months "
        "the fit used. The dashed lines are the highest and lowest water table those "
        "months reached. Everything beyond them is a value the model was never "
        "shown: 107 months above, in runs of up to 44 consecutive months from 1995 "
        "to 1998, and six below by no more than 0.06 m. The series stops in 2019 "
        "because precipitation, which the model also needs, ends there."
    ),
)


def water_table_support(
    water_table: pd.Series,
    fit_months: pd.PeriodIndex,
    reconstruction_months: pd.PeriodIndex,
    artifacts: tuple[pd.Period, ...] = WATER_TABLE_ARTIFACTS,
) -> Figure:
    """Monthly water table against the range and period the model was fitted on.

    Carries the support finding whole: which months lie beyond the fitted range,
    that they arrive in consecutive runs rather than singly, and that the fitted
    period opens after the decline separating it from the reconstruction.

    Months named as artifacts set no bound and are not drawn, which narrows the
    fitted range to what the record covers and makes the test stricter. The
    series is drawn on a complete monthly grid so absent months break the line
    rather than being bridged by it.
    """
    fig, ax = ps.canvas(WATER_TABLE_TEXT, size="wide")

    removed = pd.PeriodIndex(artifacts, freq="M")
    grid = pd.period_range(reconstruction_months.min(), fit_months.max(), freq="M")
    series = water_table.reindex(grid).copy()
    series[series.index.isin(removed)] = np.nan
    values = series.to_numpy(dtype=float)
    times = grid.to_timestamp()

    usable = fit_months.difference(removed)
    fitted = water_table.loc[water_table.index.isin(usable)].dropna()
    low, high = float(fitted.min()), float(fitted.max())

    span = float(np.nanmax(values) - np.nanmin(values))

    ax.set_ylim(np.nanmin(values) - 0.19 * span, np.nanmax(values) + 0.15 * span)

    fit_start = fit_months.min().to_timestamp()
    ps.fit_window_band(ax, fit_start, fit_months.max().to_timestamp())
    ps.fitted_range(ax, low, high)
    ps.label_period(ax, times[0], fit_start, "Reconstruction window (model predicts here)")
    ps.label_period(ax, fit_start, times[-1], "Fit window (model fitted here)")

    ax.plot(times, values, color=ps.MUTED, linewidth=0.7, alpha=0.45, zorder=1)

    reconstruction = grid.isin(reconstruction_months)
    above = reconstruction & (values > high)
    below = reconstruction & (values < low)
    outside = above | below
    seen = ~outside & ~np.isnan(values)
    ps.support_scatter(ax, times[seen], values[seen], inside=True)
    ps.support_scatter(ax, times[outside], values[outside], inside=False)

    ax.set_xlabel(ps.axis_label("Year"))
    ax.set_ylabel(ps.axis_label("Water table elevation", "meters above sea level"))
    ps.five_year_ticks(ax, grid.min().year, grid.max().year)
    ps.mirror_ticks(ax)

    handles = [
        Line2D([], [], color=ps.INSIDE, marker=ps.INSIDE_MARKER, linestyle="none",
               markersize=4.4, label="Within the fitted range"),
        Line2D([], [], color=ps.OUTSIDE, marker=ps.OUTSIDE_MARKER, linestyle="none",
               markersize=5.0,
               # A legend says what a mark means. How many carry it is a finding,
               # and the description states both counts.
               label="Outside the fitted range"),
        Line2D([], [], color=ps.BOUNDARY, linewidth=1.3, linestyle=(0, (7, 4)),
               label=f"Fitted range, {low:.2f} to {high:.2f} m"),
    ]
    # The legend sits between the panel's corner and the lower range line, and
    # at 80.5 px tall it left 9.0 px to the border and 4.3 px to the line. The
    # two clearances trade against each other, since insetting it further from
    # the corner pushes it into the line, so the box is reduced instead and the
    # inset set to split what that frees: 11.3 px and 11.1 px.
    ps.legend(ax, handles=handles, labels=[h.get_label() for h in handles],
              loc="lower left", ncols=1, fontsize=8.0, borderpad=0.30,
              labelspacing=0.22, handlelength=1.5, handletextpad=0.46,
              borderaxespad=0.68)

    ps.balance_drawing_block(fig, ax)
    return fig


#: The three lines are three assumptions about one term, not three models, so
#: they are named on the panel by what each assumes rather than by the internal
#: variant names.
#: The one word each entry shares with the subtitle is set bold, so a reader
#: carrying "flat, linear, absent" down from there finds it in the key.
WATER_TABLE_ASSUMPTIONS = {
    "clamped": r"Water table held $\bf{flat}$ beyond the fitted range",
    "unclamped": r"Water table continued $\bf{linearly}$",
    "reduced": r"Water table term $\bf{absent}$ altogether",
}

#: The two years a measurement of this peatland exists for, and the only years
#: in twenty where this reconstruction could ever be tested against one.
MEASURED_YEARS = (1991, 1992)

#: The reconstruction runs to 2009-03. A three-month year cannot be plotted
#: beside twelve-month years, so the panel stops at 2008.
LAST_PLOTTED_YEAR = 2008

RECONSTRUCTION_TEXT = ps.FigureText(
    title="Reconstructed methane emission at Marcell Bog Lake Peatland (1990 to 2008)",
    subtitle=(
        "Environmental records at this site reach back to 1990 while the flux record "
        "begins in 2009, so relationships fitted on the measured years can be "
        "projected into the earlier ones. Beyond the range the fit covered, the water "
        "table term has to be assumed rather than estimated, and the three "
        "assumptions drawn here give annual totals from 8 to 30 grams of carbon per "
        "square meter."
    ),
    description=(
        "Each marker is one year's emission in grams of carbon per square meter, from "
        "relationships fitted on the measured years (2009 to 2019). Beyond the fitted "
        "range the three take different views: the water table response either stops "
        "rising (flat), continues at the rate the fit found (linear), or is dropped "
        "altogether (absent). They agree closely where the water table stays inside "
        "that range, and fan apart where it does not. Almost none of this can be "
        "checked, because methane measurement stopped in 1992 and did not resume "
        "until 2009, leaving seventeen of these nineteen years with nothing to "
        "compare against. The exceptions are 1991 and 1992, measured by Shurpali and "
        "colleagues, whose published totals have not been obtained."
    ),
    emphasize=("flat", "linear", "absent"),
)


def reconstruction_series(annual: pd.DataFrame) -> Figure:
    """Annual reconstruction, its support, and the assumption it rests on.

    The three assumptions are drawn as three named lines rather than as a band.
    A band would say the answer lies somewhere inside it, which is the reading
    this study exists to refuse: the spread is what the choice of assumption
    buys, not a probability.
    """
    from matplotlib.ticker import FixedLocator, FormatStrFormatter, MultipleLocator

    frame = annual[annual["year"] <= LAST_PLOTTED_YEAR].copy()
    years = frame["year"].to_numpy()

    fig, rect = ps.canvas_area(RECONSTRUCTION_TEXT, size="standard")
    left, bottom, width, height = rect
    gap = 0.055 * height
    strip_h = 0.17 * height
    main_h = height - strip_h - gap
    ax = fig.add_axes((left, bottom + strip_h + gap, width, main_h))
    strip = fig.add_axes((left, bottom, width, strip_h), sharex=ax)

    for variant, label in WATER_TABLE_ASSUMPTIONS.items():
        ps.variant_line(ax, years, frame[variant].to_numpy(), variant, label=label)

    inside = frame["support"].to_numpy() == "inside"
    ps.support_scatter(ax, years[inside], frame["clamped"].to_numpy()[inside],
                       inside=True, label=r"Year $\bf{inside}$ the fitted range",
                       markersize=6.5)
    ps.support_scatter(ax, years[~inside], frame["clamped"].to_numpy()[~inside],
                       inside=False, label=r"Year $\bf{outside}$ the fitted range",
                       markersize=7.0)

    check = frame[frame["year"].isin(MEASURED_YEARS)]
    # Drawn large enough to encircle its point, but entered in the legend at the
    # size of the other two markers: a 13 pt sample crowds the column.
    ax.plot(check["year"], check["clamped"], linestyle="none", marker="o",
            markersize=13, markerfacecolor="none", markeredgecolor=ps.INK,
            markeredgewidth=1.2, zorder=3)
    measured_key = Line2D([], [], linestyle="none", marker="o", markersize=6.8,
                          markerfacecolor="none", markeredgecolor=ps.INK,
                          markeredgewidth=1.2,
                          label="Year with a published measurement to check against")

    # The circled years are two of these four, so one set of labels serves both.
    for _, row in frame[frame["support"] == "inside"].iterrows():
        ax.annotate(f"{int(row['year'])}", xy=(row["year"], row["clamped"]),
                    xytext=(0, 9), textcoords="offset points", ha="center",
                    va="bottom", fontsize=7.8, fontweight="bold", color=ps.INSIDE,
                    zorder=6, path_effects=[ps._outline()])

    ax.set_ylabel(ps.axis_label("Annual emission", "g C m$^{-2}$ yr$^{-1}$"))
    ax.set_ylim(0, frame[list(WATER_TABLE_ASSUMPTIONS)].to_numpy().max() * 1.18)
    # Every year is labeled, on the minor ticks. At 87 px a year against a
    # 50 px label there is room for all nineteen, and a reader should not have
    # to count along from a five-year mark to find one. The majors stay at five
    # years because the grid follows them: nineteen rules would be a lattice
    # over three lines and two marker colors, where five are an anchor.
    ticks = [y for y in range(int(years.min()), int(years.max()) + 1, 5)]
    if years.max() not in ticks:
        ticks.append(int(years.max()))
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    ax.xaxis.set_minor_formatter(FormatStrFormatter("%d"))
    ax.tick_params(axis="x", which="both", labelbottom=False)
    ps.mirror_ticks(ax)
    # Two columns, one group each: the lines are assumptions about the model and
    # the markers are properties of a year, which are different kinds of thing.
    collected = dict(zip(*reversed(ax.get_legend_handles_labels())))
    blank = Line2D([], [], linestyle="none", marker="none")
    entries = [(blank, r"$\bf{Assumption\ beyond\ the\ fitted\ range}$")]
    entries += [(collected[label], label) for label in WATER_TABLE_ASSUMPTIONS.values()]
    entries += [(blank, r"$\bf{Property\ of\ the\ year}$")]
    entries += [(collected[label], label) for label in
                (r"Year $\bf{inside}$ the fitted range",
                 r"Year $\bf{outside}$ the fitted range")]
    entries += [(measured_key, measured_key.get_label())]
    # The strip's marks are keyed in the strip, not here. Folding them in put an
    # entry for hatched bars on a panel carrying none, so a reader looking for
    # them would not find them.
    ps.legend(ax, handles=[h for h, _ in entries], labels=[label for _, label in entries],
              loc="lower left", fontsize=8.2, borderpad=0.5, labelspacing=0.3,
              handlelength=1.9, handletextpad=0.5, ncols=2, columnspacing=1.6,
              bbox_to_anchor=(0.015, 0.02))

    share = frame["pct_months_outside"].to_numpy()
    strip.bar(years[~inside], share[~inside], width=0.7, color=ps.OUTSIDE,
              edgecolor="white", linewidth=0.4, hatch=ps.OUTSIDE_HATCH)
    # A year wholly inside has a bar of zero height, which is a measured zero and
    # not a missing one. Flat rather than round, so it reads as a bar of no height
    # rather than as a point from another series, and blue because these are the
    # same four years the panel above marks blue. Orange would say outside the
    # range, which is the opposite of what the mark means.
    strip.plot(years[inside], np.zeros(inside.sum()), linestyle="none", marker="_",
               markersize=5.2, markeredgewidth=1.8, color=ps.INSIDE,
               clip_on=False, zorder=4)

    # The strip's own key, at the size the panel's key uses. Set as one row of
    # two with the heading as a legend title, which is the only arrangement that
    # clears the bars: the strip is an eighth of the block, and three stacked
    # rows run to 63% of its height and cover the 2007 bar whichever way the
    # heading is set. Laid across, the same entries take 43% and clear it by 19
    # points. The title device is the site figure's, so this is the set's other
    # heading rather than a new one.
    #
    # It names the marks rather than where they sit. Naming the location was
    # right when these entries lived in the panel's key and pointed downward;
    # from inside the strip it says only what a reader can already see. "What
    # each bar shows" would not do, because one of the two is a flat tick for a
    # year with no months outside, which is a bar of no height and does not read
    # as one. This wording covers both and is the set's for exactly that: it
    # heads the keys on the prediction error and residual figures, which group
    # unlike marks the same way.
    strip_key = [
        Patch(facecolor=ps.OUTSIDE, edgecolor="white", hatch=ps.OUTSIDE_HATCH,
              label="Months outside"),
        Line2D([], [], linestyle="none", marker="_", markersize=5.2,
               markeredgewidth=1.8, color=ps.INSIDE, label="No months outside"),
    ]
    # Upper right, where the last years' bars are short. That is a property of
    # the data rather than of the layout, so a test holds the clearance.
    strip_legend = ps.legend(
        strip, handles=strip_key, labels=[h.get_label() for h in strip_key],
        loc="upper right", ncols=2, fontsize=8.2, borderpad=0.4,
        labelspacing=0.28, handlelength=1.5, handletextpad=0.5, columnspacing=1.4,
        framealpha=1.0, title=r"$\bf{What\ each\ mark\ shows}$",
        bbox_to_anchor=(0.995, 0.97))
    # Bold through the same mathtext the panel's headings use, so the two are
    # one device set two ways rather than two that happen to look alike.
    strip_legend.get_title().set_fontsize(8.2)
    strip.set_ylim(0, 108)
    strip.set_yticks([0, 50, 100])
    # The strip is an eighth of the block's height and its label is set along
    # it, so at the set's label size the words run 217 px against a 128 px
    # frame and reach into the panel above. Reduced until they clear it.
    strip.set_ylabel(ps.axis_label("Months outside", "%"), fontsize=8.4)
    strip.set_xlabel(ps.axis_label("Year"))
    strip.set_xlim(years.min() - 0.8, years.max() + 0.8)
    strip.xaxis.set_minor_locator(MultipleLocator(1))
    ps.mirror_ticks(strip)
    # The year labels ride the minor ticks, so they are set to the size the
    # majors carry rather than the smaller default matplotlib gives minors.
    strip.tick_params(axis="x", which="minor", labelbottom=True,
                      labelsize=ps.TICK_SIZE)

    ps.balance_drawing_block(fig, ax, strip)
    # Ruled after the balance, never before. The rules are figure artists at fixed
    # figure coordinates and the balance moves the axes their legend rides on, so
    # ruling first leaves the line where the heading used to be. It struck through
    # both headings here for as long as this figure has been balanced.
    ps.underline_legend_headings(fig, ax)
    ps.underline_legend_title(fig, strip_legend)

    return fig


# --------------------------------------------------------------------------
# The forecast comparison
# --------------------------------------------------------------------------

#: Benchmarks drawn, in the order they are read. Achromatic and separated by line
#: style, as every non-hue category in this figure set is. Weight follows how much
#: each one carries: climatology is the result, so it is heaviest.
BENCHMARK_STYLE = {
    "climatology": {"color": "#1A1A1A", "linestyle": "-", "linewidth": 2.4},
    # Longer dashes and a little more weight, because this line crosses the green
    # fill and at #767676 it holds only 2.33:1 against it, under the 3:1 a
    # graphical object needs. It already draws above the fill, so order was not
    # the problem; the fill's alpha stays at the measured 0.45, which is what
    # keeps the subject 0.143 darker than the apparatus behind it. Ink is the
    # only lever left, and a dotted line at 1.4 on 2.2 lays down very little.
    "seasonal naive": {"color": "#767676", "linestyle": (0, (5.0, 2.6)), "linewidth": 2.2},
}

#: Benchmarks the panel table carries. Drawing is a separate question: the table
#: keeps every benchmark the study scored, so the subtitle can quote one the
#: panel does not draw and a test can check that it quotes it correctly.
#: Every benchmark the study scores reaches the panel's table, so the table can
#: answer why two of them are drawn and two are not. `BENCHMARK_STYLE` is the
#: drawn subset. Carrying three of the four was the older arrangement: `naive`
#: reached the table and nothing drew it, and `seasonal naive with drift` never
#: reached it at all, so neither the drawing nor the table was the complete set.
PANEL_BENCHMARKS = ("climatology", "seasonal naive", "naive",
                    "seasonal naive with drift")

#: Carrying last month's value forward is scored and reported but not drawn. It
#: is not a contender, and at twelve months it coincides with the seasonal
#: benchmark by construction. The subtitle states what it establishes.
PERSISTENCE_LAST_HORIZON = 6

#: Named by what they do. "Seasonal naive" and "climatology" tell a reader
#: nothing on first meeting; the subtitle and the notes carry the technical terms.
BENCHMARK_LABEL = {
    "climatology": "The average of that month in previous years",
    "seasonal naive": "The same month last year",
}

GAS_PANEL = (
    ("methane", "Methane", "nmol m$^{-2}$ s$^{-1}$"),
    ("carbon_dioxide", "Carbon dioxide", "$\\mu$mol m$^{-2}$ s$^{-1}$"),
)


def forecast_panel(
    frames: dict[str, pd.DataFrame], horizons: Sequence[int]
) -> pd.DataFrame:
    """Mean absolute error per method and horizon, on the months all of them scored.

    One row per horizon, carrying each benchmark, the range across every fitted
    model in both families, and the margin a method would need to be
    distinguishable from climatology. The margin is measured against the best
    fitted method at that horizon, because the claim the figure makes is that
    nothing fitted beats climatology, and the best method is what would have to.
    """
    keys = evaluation.shared_targets(list(frames.values()))
    rows = []
    for horizon in horizons:
        errors: dict[str, pd.Series] = {}
        for family, frame in frames.items():
            block = evaluation.restrict(frame, keys)
            block = block[block["horizon"] == horizon]
            for method, group in block.groupby("method"):
                errors[f"{family}/{method}"] = group.set_index("target")["error"]
        mae = {name: float(series.abs().mean()) for name, series in errors.items()}
        fitted = {k: v for k, v in mae.items() if not k.startswith("benchmarks/")}
        best = min(fitted, key=fitted.get)
        row = {
            "horizon": horizon,
            "fitted_low": min(fitted.values()),
            "fitted_high": max(fitted.values()),
            "n": len(errors["benchmarks/climatology"].dropna()),
            "effective_n": evaluation.diebold_mariano(
                errors[best], errors["benchmarks/climatology"], horizon)["effective_n"],
            "margin": evaluation.significance_margin(
                errors[best], errors["benchmarks/climatology"], horizon),
        }
        for method in PANEL_BENCHMARKS:
            row[method] = mae[f"benchmarks/{method}"]
        rows.append(row)
    return pd.DataFrame(rows)


FORECAST_TEXT = ps.FigureText(
    title=(
        "Monthly methane and carbon dioxide forecast error at Marcell Bog Lake "
        "Peatland"
    ),
    subtitle=(
        "Four fitted methods (ordinary least squares, ridge regression, random "
        "forest and gradient boosting), each run with and without lagged "
        "environmental covariates, are compared against four simple benchmarks: "
        "the average of that month in previous years, the same month last year, "
        "last month carried forward, and the same month last year adjusted for "
        "trend. The first two are drawn here. Each method is evaluated over 2013 "
        "to 2020 for carbon dioxide and 2014 to 2020 for methane, at forecast "
        "horizons of one to twelve months, meaning how far ahead the prediction "
        "is made. The pale band marks how far from the first of those "
        "a method would have to fall, in either direction, before the difference "
        "could be told apart from noise."
    ),
    description=(
        "Each panel is one gas, in mean absolute error. The green region covers "
        "all eight fitted models. It sits mostly above the seasonal average, "
        "and where it reaches beneath, at one month on both gases and at six "
        "months on methane, the difference stays inside the band; where its upper "
        "edge rises above the band, some fitted models are measurably worse than "
        "the average. The band is wide where the closest fitted model disagrees "
        "with the average erratically from month to month, not where the average "
        "is least certain. Methane is in nanomoles and carbon dioxide in "
        "micromoles, so the panels do not compare by eye."
    ),
)


def _draw_forecast_panel(ax, panel: pd.DataFrame, unit: str, labeled: bool = True) -> None:
    """One gas: the two benchmarks worth comparing, the fitted range, and the band.

    Carrying last month's value forward is not drawn. It loses at every horizon
    past one month and nobody would use it, and holding its 41.4 on the same axis
    as a seasonal average of 6.9 compresses the comparison the figure exists to
    show into the bottom of the panel. What it establishes, that recent
    information decays with horizon while a seasonal average does not, is a
    sentence, and the subtitle carries it.

    The vertical scale is linear and spans what the drawn series occupy. A
    logarithmic scale was tried while persistence was still drawn and made the
    carbon dioxide panel unreadable: a real 15% margin over the seasonal
    benchmark looks like nothing on an axis running to 1.0.

    The horizontal scale is categorical. At their true numeric positions the step
    from six months to twelve is twice the step from three to six, which stretches
    the curves for a reason that has nothing to do with the forecasts.
    """
    positions = np.arange(len(panel), dtype=float)
    climatology = panel["climatology"].to_numpy()
    margin = panel["margin"].to_numpy()

    lowest = float(min(panel["fitted_low"].min(), (climatology - margin).min(),
                       panel["seasonal naive"].min()))
    highest = float(max(panel["fitted_high"].max(), (climatology + margin).max(),
                        panel["seasonal naive"].max()))
    span = highest - lowest
    # A little room below, and enough above for the legend to sit over the left
    # of the panel without covering anything.
    ax.set_ylim(lowest - 0.05 * span, highest + 0.18 * span)
    ax.set_xlim(-0.35, len(panel) - 0.65)

    ax.fill_between(positions, climatology - margin, climatology + margin,
                    facecolor=ps.NOT_DISTINGUISHABLE, edgecolor="none", zorder=1)
    ax.fill_between(positions, panel["fitted_low"], panel["fitted_high"],
                    facecolor=ps.FITTED, alpha=ps.FITTED_FILL_ALPHA,
                    edgecolor="none", zorder=2)
    for edge in ("fitted_low", "fitted_high"):
        ax.plot(positions, panel[edge], color=ps.FITTED, linewidth=0.9, zorder=3)

    for method, style in BENCHMARK_STYLE.items():
        ax.plot(positions, panel[method].to_numpy(), zorder=4, **style)

    ax.set_xticks(positions)
    ax.set_xticklabels([str(h) for h in panel["horizon"]])
    if labeled:
        ax.set_xlabel(ps.axis_label("Forecast horizon", "months"))
    # Two lines: stacked panels are shorter than a single-line label is long, and
    # the two labels would otherwise run into each other down the left margin.
    ax.set_ylabel(f"Mean absolute error\n({unit})")
    ps.mirror_ticks(ax)


def forecast_error_by_horizon(panels: dict[str, pd.DataFrame]) -> Figure:
    """The forecast result: the seasonal average against everything fitted to beat it.

    Two panels rather than one axis, in each gas's own units, because the scaled
    error that would put them on a common axis is not comparable between them.
    Removing the measure removes the temptation.

    The fitted models appear as a range rather than as eight labeled curves.
    Four of the sixteen method comparisons reach nominal significance and none
    survives correction for multiple testing, so drawing an order would assert a
    ranking the evidence does not support.
    """
    fig, (left, bottom, width, height) = ps.canvas_area(FORECAST_TEXT, size="stacked", extra_left_px=34)
    gap = 0.055
    panel_height = (height - gap) / 2
    axes = []
    for index, (key, gas, unit) in enumerate(GAS_PANEL):
        # Top panel first, so the panels read down the page in the order lettered.
        row = bottom + (1 - index) * (panel_height + gap)
        ax = fig.add_axes((left, row, width, panel_height))
        _draw_forecast_panel(ax, panels[key], unit, labeled=index == len(GAS_PANEL) - 1)
        ps.panel_name(ax, gas)
        _forecast_legend(ax)
        axes.append(ax)

    # No note on the panel. The description says the same thing in nearly the
    # same words, and an arrow can only point at one horizon of a finding that
    # holds at three, so a reader met it twice above the axis and once below.
    for ax in axes:
        _raise_top_until_furniture_clears(ax)
    # Balance before ruling the headings. The rules are figure artists at fixed
    # figure coordinates, so anything that moves an axes afterwards slides its
    # legend out from under them.
    ps.balance_drawing_block(fig, *axes)
    for ax in axes:
        ps.underline_legend_headings(fig, ax)
    return fig


#: Pixels of clear space between the legend and the nearest series beneath it.
#: In pixels rather than as a share of the data range, which would grow with the
#: range it is used to enlarge. Carbon dioxide's benchmark line runs high in its
#: panel, so this is what separates the two; matching methane's much larger gap
#: exactly would compress the carbon dioxide comparison into half its panel.
LEGEND_CLEARANCE_PX = 60


def _highest_between(x, y, low: float, high: float) -> float:
    """Highest a piecewise-linear series reaches over an x span, edges included.

    Exact rather than sampled. Between two vertices the series is a straight
    line, so its maximum over an interval is attained either at a vertex inside
    the interval or at one of the two edges, and reading those is enough.

    Reading only the vertices is what this replaces, and it is wrong in a way
    that hides itself. On the forecast figure the methane envelope climbs from
    9.37 at one horizon to 15.06 at the next, so a key whose edge falls between
    them sees 9.37 and is placed where the series will be. That it currently
    clears on this data is luck, not layout.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = ~(np.isnan(x) | np.isnan(y))
    x, y = x[keep], y[keep]
    if x.size == 0:
        return -np.inf
    order = np.argsort(x)
    x, y = x[order], y[order]
    reach = list(y[(x >= low) & (x <= high)])
    for edge in (low, high):
        if x[0] <= edge <= x[-1]:
            reach.append(float(np.interp(edge, x, y)))
    return max(reach) if reach else -np.inf


def _raise_top_until_furniture_clears(ax, rounds: int = 8) -> None:
    """Grow the axis upward until the legend clears the series beneath it.

    The legend is anchored in axes fractions, so raising the top moves the data
    away from it. With the panel note gone there is one requirement left: a fixed
    pixel gap between the legend and the highest series running under it.
    """
    for _ in range(rounds):
        ax.figure.canvas.draw()
        low, high = ax.get_ylim()
        frame = ax.get_window_extent()
        needed = high - low

        legend = ax.get_legend().get_window_extent()
        box = legend.transformed(ax.transData.inverted())
        highest = max(
            (_highest_between(line.get_xdata(), line.get_ydata(), box.x0, box.x1)
             for line in ax.lines),
            default=-np.inf,
        )
        share = (legend.y0 - frame.y0 - LEGEND_CLEARANCE_PX) / frame.height
        if highest > -np.inf and share > 0:
            needed = max(needed, (highest - low) / share)

        if needed <= (high - low) * 1.001:
            return
        ax.set_ylim(low, low + needed)


def _forecast_legend(ax) -> None:
    """One legend per panel, carrying both distinctions, so each panel reads alone.

    Two columns, one group each, filled down the column so a heading sits above
    its own entries. Centered horizontally rather than pushed against the left
    edge, so it occupies the empty band above the curves instead of crowding the
    part of the panel where the comparison is closest.
    """
    blank = Line2D([], [], linestyle="none", marker="none")
    entries = [(blank, r"$\bf{Benchmark\ methods}$")]
    entries += [(Line2D([], [], **style), BENCHMARK_LABEL[method])
                for method, style in BENCHMARK_STYLE.items()]
    entries += [
        (blank, r"$\bf{Shaded\ regions}$"),
        (Patch(facecolor=ps.FITTED, alpha=ps.FITTED_FILL_ALPHA, edgecolor=ps.FITTED,
               linewidth=0.9), "Highest and lowest of the eight fitted models"),
        (Patch(facecolor=ps.NOT_DISTINGUISHABLE, edgecolor="none"),
         "Margin needed to differ from the average"),
    ]
    # Right edge on the last horizon rather than on the frame. The axis carries
    # a third of a category of margin past the final position so the twelve-month
    # markers are not drawn on the spine, and anchoring to the frame left that
    # margin as white space between the key and the panel edge. Both panels give
    # the same figure: the horizontal axis is categorical and both run the same
    # four horizons, so every series on both ends at the same position.
    low, high = ax.get_xlim()
    right = (max(ax.get_xticks()) - low) / (high - low)
    ps.legend(ax, handles=[h for h, _ in entries], labels=[label for _, label in entries],
              loc="upper right", bbox_to_anchor=(right, 0.985), ncol=2, borderpad=0.7,
              labelspacing=0.34, columnspacing=2.0, handlelength=2.2,
              handletextpad=0.8, fontsize=ps.LEGEND_SIZE - 1.0, framealpha=1.0,
              borderaxespad=0.0)


# --------------------------------------------------------------------------
# Observed against predicted
# --------------------------------------------------------------------------

#: Where each gas's observed monthly series lives, and the column holding the
#: standard error of each month's mean.
GAS_OBSERVED = {
    "methane": ("monthly_fch4_from_daily.csv", "fch4_mean", "fch4_se_across_days"),
    "carbon_dioxide": ("monthly_fco2_diurnally_balanced.csv", "fco2_mean",
                       "fco2_se_across_cells"),
}

#: The horizon this figure draws. One month is the horizon most favorable to the
#: fitted models, so showing that they do not follow the observations even there
#: is a stronger claim than showing it a year out.
FLUX_HORIZON = 1

#: The observed band spans this many standard errors either side of the mean.
OBSERVED_BAND_SIGMAS = 2

#: Clearance under the legend on this figure. Smaller than on the forecast
#: comparison because a series fills the panel here rather than running along the
#: bottom of it, so every pixel of clearance costs empty axis above the data.
FLUX_LEGEND_CLEARANCE_PX = 22


def flux_panel(
    observed: pd.DataFrame, frames: dict[str, pd.DataFrame], horizon: int = FLUX_HORIZON
) -> pd.DataFrame:
    """The observed series over the whole record, with predictions where they exist.

    Indexed by month over every observed month, so the figure can show how much of
    the record was never forecast. Prediction columns are absent outside the
    evaluated window rather than filled, which is what leaves the gap visible.
    """
    keys = evaluation.shared_targets(list(frames.values()))
    predictions: dict[str, pd.Series] = {}
    for family, frame in frames.items():
        block = evaluation.restrict(frame, keys)
        block = block[block["horizon"] == horizon]
        for method, group in block.groupby("method"):
            predictions[f"{family}/{method}"] = group.set_index("target")["forecast"]
    wide = pd.DataFrame(predictions)
    fitted = [name for name in wide.columns if not name.startswith("benchmarks/")]

    panel = observed.copy()
    panel["climatology"] = wide["benchmarks/climatology"]
    panel["fitted_low"] = wide[fitted].min(axis=1)
    panel["fitted_high"] = wide[fitted].max(axis=1)
    return panel


FLUX_TEXT = ps.FigureText(
    title=("Observed and predicted monthly flux at Marcell Bog Lake Peatland "
           "(2009 to 2024)"),
    subtitle=(
        "Each panel is one gas, with the measured monthly flux in black and a "
        "shaded band showing how precisely that month's average is known. "
        "Against it are two forecasts, each made using only what was known a "
        "month earlier: the seasonal average as a dashed line, and a green band "
        "spanning the highest and lowest of eight fitted models. The shaded "
        "years are where forecasts exist, since a seasonal average needs each "
        "calendar month observed several times before it can be made at all."
    ),
    description=(
        "The forecasts follow the seasonal cycle closely, rising and falling in "
        "step with the measurements. What they miss is how large each season "
        "will be: in 12 of the 57 evaluated methane months the measured flux "
        "fell below every fitted model, and in 9 of those below the seasonal "
        "average too. 2021, the weakest summer in the record, lies outside the "
        "years forecasts were made for. On carbon dioxide the eight models "
        "disagree by less than the uncertainty in the measurement, which is why "
        "the green band sits inside the black one. Methane is in nanomoles and "
        "carbon dioxide in micromoles, so the two panels cannot be compared by "
        "eye."
    ),
)


def _draw_flux_panel(ax, panel: pd.DataFrame, unit: str, labeled: bool) -> None:
    """One gas: the measured series over the record, and predictions where they exist.

    The evaluated months are shaded rather than clipped to, so a reader sees how
    much of the record was never forecast: 32% of the methane months carry a
    prediction and 44% of the carbon dioxide months.
    """
    times = panel.index.to_timestamp()
    observed = panel["observed"].to_numpy(dtype=float)
    spread = OBSERVED_BAND_SIGMAS * panel["se"].to_numpy(dtype=float)

    evaluated = panel.index[panel["climatology"].notna()]
    ps.fit_window_band(ax, evaluated.min().to_timestamp(),
                       (evaluated.max() + 1).to_timestamp())

    ax.fill_between(times, observed - spread, observed + spread, facecolor=ps.INK,
                    alpha=ps.OBSERVED_BAND_ALPHA, edgecolor="none", zorder=2)
    ax.fill_between(times, panel["fitted_low"], panel["fitted_high"],
                    facecolor=ps.FITTED, alpha=ps.FITTED_FILL_ALPHA,
                    edgecolor="none", zorder=3)
    ax.plot(times, panel["climatology"], color="#767676", linestyle=(0, (7, 2, 2, 2)),
            linewidth=1.6, zorder=4)
    ax.plot(times, observed, color=ps.INK, linewidth=1.5, zorder=5)

    if float(np.nanmin(observed)) < 0 < float(np.nanmax(observed)):
        ax.axhline(0.0, color=ps.BOUNDARY, linewidth=0.9, linestyle=(0, (3, 3)), zorder=1)

    low = float(np.nanmin([np.nanmin(observed - spread), panel["fitted_low"].min()]))
    high = float(np.nanmax([np.nanmax(observed + spread), panel["fitted_high"].max()]))
    margin = 0.04 * (high - low)
    ax.set_ylim(low - margin, high + margin)

    if labeled:
        ax.set_xlabel(ps.axis_label("Year"))
    ax.set_ylabel(f"Monthly flux\n({unit})")
    ps.mirror_ticks(ax)


def _flux_legend(ax, panel: pd.DataFrame) -> str:
    """Two columns, measured on the left and predicted on the right.

    Both panels put it on the right so a reader's eye does not relocate between
    them. Methane's peaks are all in the first half of its record, and carbon
    dioxide's right-hand months need a little more headroom than its left-hand
    ones, which the fitting loop supplies.
    """
    side = "upper right"
    blank = Line2D([], [], linestyle="none", marker="none")
    entries = [
        (blank, r"$\bf{Measured}$"),
        (Line2D([], [], color=ps.INK, linewidth=1.5), "Monthly mean flux"),
        (Patch(facecolor=ps.INK, alpha=ps.OBSERVED_BAND_ALPHA, edgecolor="none"),
         "Two standard errors on that mean"),
        (blank, r"$\bf{Predicted\ a\ month\ ahead}$"),
        (Line2D([], [], color="#767676", linestyle=(0, (7, 2, 2, 2)), linewidth=1.6),
         "The average of that month in previous years"),
        (Patch(facecolor=ps.FITTED, alpha=ps.FITTED_FILL_ALPHA, edgecolor=ps.FITTED,
               linewidth=0.9), "Highest and lowest of the eight fitted models"),
    ]
    anchor = (0.985, 0.975)
    ps.legend(ax, handles=[h for h, _ in entries], labels=[label for _, label in entries],
              loc=side, bbox_to_anchor=anchor, ncol=2, borderpad=0.6,
              labelspacing=0.3, columnspacing=1.8, handlelength=2.0,
              handletextpad=0.8, fontsize=ps.LEGEND_SIZE - 1.6, framealpha=1.0)
    return side


def _raise_top_for_flux_legend(ax, panel: pd.DataFrame, rounds: int = 8) -> None:
    """Grow the axis until the legend clears everything drawn beneath it.

    The band tops are polygon fills rather than lines, so the series to clear are
    taken from the panel data rather than from the artists. Measured in pixels for
    the same reason as on the forecast figure: a clearance expressed as a share of
    the range grows with the range it is used to enlarge.
    """
    import matplotlib.dates as mdates

    positions = mdates.date2num(panel.index.to_timestamp())
    ceiling = np.fmax(
        (panel["observed"] + OBSERVED_BAND_SIGMAS * panel["se"]).to_numpy(dtype=float),
        panel["fitted_high"].to_numpy(dtype=float),
    )
    for _ in range(rounds):
        ax.figure.canvas.draw()
        low, high = ax.get_ylim()
        frame = ax.get_window_extent()
        legend = ax.get_legend().get_window_extent()
        box = legend.transformed(ax.transData.inverted())
        highest = _highest_between(positions, ceiling, box.x0, box.x1)
        if highest == -np.inf:
            return
        share = (legend.y0 - frame.y0 - FLUX_LEGEND_CLEARANCE_PX) / frame.height
        if share <= 0:
            return
        needed = (highest - low) / share
        if needed <= (high - low) * 1.001:
            return
        ax.set_ylim(low, low + needed)


def observed_and_predicted(panels: dict[str, pd.DataFrame]) -> Figure:
    """The measured flux over the record, against what every method predicted.

    A time series rather than a scatter against a one-to-one line. A scatter shows
    how far predictions miss by and destroys when they miss, and the finding is
    about which months: the low-amplitude summers, where the measurement falls
    below every prediction at once.
    """
    fig, (left, bottom, width, height) = ps.canvas_area(FLUX_TEXT, size="stacked",
                                                        extra_left_px=34)
    gap = 0.055
    panel_height = (height - gap) / 2
    axes = []
    for index, (key, gas, unit) in enumerate(GAS_PANEL):
        row = bottom + (1 - index) * (panel_height + gap)
        ax = fig.add_axes((left, row, width, panel_height))
        _draw_flux_panel(ax, panels[key], unit, labeled=index == len(GAS_PANEL) - 1)
        # One key for the pair, on the upper panel. The two are stacked on a
        # shared axis and neither carries a mark the other lacks, so a second
        # copy names nothing new and costs the lower panel 8% of its area. That
        # is the panel whose green band is thinnest: half its forecast months
        # sit inside the uncertainty band on the measurement.
        if index == 0:
            _flux_legend(ax, panels[key])
        ps.panel_name(ax, gas, align="left")
        axes.append(ax)

    # One time axis for both panels, so a year sits at the same place in each.
    # The methane record ends in 2021 and the gap at the right of its panel says
    # so, which is why the two windows of evaluated months differ in length.
    first = min(panel.index.min() for panel in panels.values()).to_timestamp()
    last = (max(panel.index.max() for panel in panels.values()) + 1).to_timestamp()
    for ax, (key, _, _) in zip(axes, GAS_PANEL):
        ax.set_xlim(first, last)
        ps.even_year_ticks(ax, first.year, last.year, label_every_year=True)
        if ax.get_legend() is not None:
            _raise_top_for_flux_legend(ax, panels[key])
    ps.balance_drawing_block(fig, *axes)
    for ax in axes:
        if ax.get_legend() is not None:
            ps.underline_legend_headings(fig, ax)
    return fig


# --------------------------------------------------------------------------
# Screening survival
# --------------------------------------------------------------------------

#: Covariates offered to the screening, in the order the rows are read.
SCREENED_COVARIATES = (
    ("soil_temp_f", "Soil temperature"),
    ("atm_temp_f", "Air temperature"),
    ("precip_in", "Precipitation"),
    ("wte_m", "Water table"),
)

#: The flux's own past, split into the two lags that mean different things: the
#: most recent month, and the same month a year earlier. Collapsing them would
#: conflate two claims, and it is the annual lag that carries the result.
FLUX_ROWS = ("The flux a month before", "The flux a year before")

#: Cells above this are dark enough to need light text on them.
DARK_CELL = 0.55


def screening_panel(
    exogenous: pd.DataFrame,
    covariates: pd.DataFrame,
    index: pd.PeriodIndex,
    horizons: Sequence[int] = evaluation.HORIZONS,
) -> pd.DataFrame:
    """Share of folds each predictor survived, by horizon, with its calendar share.

    A covariate offered at several lags takes its best-surviving one, since the
    question is whether that driver survived at all rather than which lag of it
    did. A predictor that never survived is a measured zero, not a gap, so it is
    filled rather than left absent.

    The share of each covariate the calendar already explains is carried on the
    frame's `attrs`, because it belongs beside the row label rather than in a
    second encoded quantity on the same geometry.
    """
    frequency = experiment.predictor_frequency(exogenous).set_index(
        ["predictor", "horizon"])["share"]
    rows: dict[str, dict[int, float]] = {name: {} for name in FLUX_ROWS}
    rows |= {label: {} for _, label in SCREENED_COVARIATES}
    for horizon in horizons:
        annual = features.annual_lag(horizon)
        rows[FLUX_ROWS[1]][horizon] = float(frequency.get((f"flux_lag{annual}", horizon), 0.0))
        rows[FLUX_ROWS[0]][horizon] = (
            float(frequency.get(("flux_lag1", horizon), 0.0)) if horizon == 1 else np.nan
        )
        for column, label in SCREENED_COVARIATES:
            candidates = [float(frequency.get((f"{column}_lag{lag}", horizon), 0.0))
                          for lag in range(1, 2 * evaluation.PERIOD + 2)]
            rows[label][horizon] = max(candidates)
    panel = pd.DataFrame(rows).T[list(horizons)]
    panel.attrs["calendar"] = {
        label: screening.explained_by_calendar(covariates[column], index)
        for column, label in SCREENED_COVARIATES
    }
    return panel


MEASUREMENTS_TEXT = ps.FigureText(
    title=("Which measurements the models used at Marcell Bog Lake Peatland "
           "(by forecast horizon)"),
    subtitle=(
        # "Inputs" rather than "measurements": two of the six rows are the flux's
        # own past values, which the description says in the same breath are not
        # measurements taken at the site, so naming all six that way makes the two
        # blocks disagree on one figure.
        "Each model predicts a fixed distance ahead, from one month to twelve, "
        "and was rebuilt every month as the record grew. At every rebuild the "
        "model selected which of the six inputs listed at the left to include, "
        "and the green bars give the share of rebuilds in which each was "
        "selected. The grey bars answer a separate question that has nothing to "
        "do with the model: how much of each input's own variation can be "
        "predicted from the calendar date alone. Reading the two together shows "
        "whether the models reached for inputs carrying information the date "
        "does not already supply."
    ),
    description=(
        # "On methane" is doing real work. Ranking by mean share across horizons,
        # the water table is chosen least on methane at 10% but not on carbon
        # dioxide, where precipitation is lower at 14% against 16%. The claim
        # above it is likewise a methane finding that carbon dioxide follows only
        # at the top: the rank correlation between what the date explains and what
        # the models chose is +0.80 against +0.60, and the bottom two invert.
        "Read across a row and the two blocks answer different questions, one "
        "asking how often the models used that input and the other how much of "
        "it the date already explains. The models reached for what the date "
        "predicts and left alone what it does not, choosing temperature most and "
        "the water table least on methane. The two gases differ in kind rather "
        "than degree. Methane's models take soil and air temperature in almost "
        "every rebuild one month out, while carbon dioxide's take them almost "
        "never and lean instead on the flux's own value a year earlier. A struck "
        "cell is one where no number could be computed, either because the "
        "flux's own past values are not measurements taken at the site, or "
        "because last month's flux is unavailable three or more months ahead."
    ),
)

#: Headings over the two column groups, each centered on the columns it covers and
#: broken before the parenthetical so the pair reads in the same register.
#:
#: "Chosen" rather than "kept" or "retained", which are the more literal words for
#: what a selection step does. Kept implies a pool the reader has not been shown,
#: and naming that pool is the screening vocabulary coming back by another route;
#: chosen needs no antecedent. It also holds the subtitle and the heading to one
#: verb, so the panel and the sentence above it describe one act rather than two.
CHOSEN_HEADING = "Chosen by the models\n(% of rebuilds)"
DATE_HEADING = "Predictable from the date\n(% of variation)"

#: The same units again, under the ticks they belong to. The heading sits a full
#: figure height above the bottom row, so a reader at the tick marks would have to
#: travel back up to learn what the numbers are.
DATE_AXIS = "% of variation"
CHOSEN_AXIS = "% of rebuilds"

#: How far the strike in an empty cell reaches, on the panel's 0 to 124 scale.
#: It starts where a bar starts. An earlier version began 1.0 in, which at this
#: scale is 2 px: too little for a reader to register as "this is not measured
#: from the axis" and enough to invite them to look for meaning in the gap, where
#: there is none.
#:
#: Length is not what tells a strike from a bar and cannot be made to. At 8.0 it
#: renders 16.6 px against a 9% bar's 19.6, and this figure draws bars at 9% and
#: 10%, so the two end within 3 px. What separates them is thickness, 2.9 px
#: against a bar's 39.4, and the labelling rule: every bar carries its number,
#: including a "0" where the value is a measured zero, and no strike carries one.
#: A change to bar height or to that rule would remove the distinction without
#: touching this constant, which is why a test holds both.
STRIKE_WIDTH = 8.0


def usage_order(panels: dict[str, pd.DataFrame]) -> list[str]:
    """Predictors ordered by mean use across both gases and every horizon.

    One order for all ten panels, which is what makes small multiples readable:
    a row sits in the same place everywhere, so the eye compares along it.
    """
    combined = pd.concat(list(panels.values()), axis=1)
    return list(combined.mean(axis=1, skipna=True).sort_values(ascending=False).index)


def _draw_usage_panel(
    ax,
    values,
    order,
    color: str,
    ticked: bool,
    rule_after: int | None,
) -> None:
    """One column of bars: a share from nothing to everything, per measurement.

    An empty cell carries a strike rather than a number. The two reasons differ,
    a question that does not apply on the date column and a value a model at that
    horizon cannot have, but the mark is one: unmarked they would look like
    missing data, and separately worded they cost ten annotations on a panel that
    already meets a reader with text in eight places.
    """
    positions = np.arange(len(order))
    heights = np.array([values.get(name, np.nan) for name in order], dtype=float)
    drawn = ~np.isnan(heights)
    ax.barh(positions[drawn], 100 * heights[drawn], height=0.6, color=color,
            edgecolor="none", zorder=2)
    for position, height in zip(positions[drawn], heights[drawn]):
        share = 100 * height
        ax.text(share + 4.0, position, f"{share:.0f}", va="center", ha="left",
                fontsize=ps.TICK_SIZE - 1.5, color=ps.MUTED, zorder=3)
    # A strike where the bar would start, not a phrase. The two reasons a cell is
    # empty were written into it, "does not apply" on the date column and "not
    # available" on a horizon column, which is ten italic annotations and 1,070 px
    # of text for cells that are simply empty. Nothing in this literature
    # annotates inapplicable cells, so there is no convention being departed from,
    # and the description carries both reasons in one sentence.
    for position in positions[~drawn]:
        ax.plot([0.0, STRIKE_WIDTH], [position, position], color=ps.MUTED,
                linewidth=1.4, solid_capstyle="butt", zorder=3)

    if rule_after is not None:
        ax.axhline(rule_after + 0.5, color=ps.GRID, linewidth=1.0, zorder=1)
    ax.set_xlim(0, 124)
    ax.set_ylim(len(order) - 0.5, -0.5)
    ax.set_yticks(positions)
    ax.set_yticklabels([])
    ax.set_xticks([0, 50, 100])
    ax.set_xticklabels(["0", "50", "100"] if ticked else [])
    ax.tick_params(length=0, labelsize=ps.TICK_SIZE - 1.5, colors=ps.MUTED)
    ax.grid(axis="x", color=ps.GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(ps.BOUNDARY)


#: Pixel allocations inside the drawing rectangle. Row names are set once at the
#: left of both gases rather than repeated on ten panels, and the width here is
#: what the longest of them needs; the rest divides evenly between the five
#: columns, with the date column set apart because it answers a different question.
LABEL_PX = 258
LEAD_PX = 44
COLUMN_GAP_PX = 20
HEADING_PX = 64
COLUMN_TITLE_PX = 30
GAS_LABEL_PX = 40


def measurements_used(panels: dict[str, pd.DataFrame]) -> Figure:
    """What the models chose, beside how much of each choice is simply the date.

    Ranked bars in small multiples rather than a grid of shaded cells: with fifty
    numbers a reader has to decode a shading scale to find the pattern, where
    sorted bars put it in the length of the marks and in the order of the rows.
    The leading column answers a different question from the four beside it, so
    it is set apart by a gap and drawn achromatic.
    """
    fig, (left, bottom, width, height) = ps.canvas_area(MEASUREMENTS_TEXT, size="tall")
    width_px, height_px = ps.SIZES["tall"]
    order = usage_order(panels)
    # The flux's own past is not a measurement from the site, so it is ruled off
    # from the four that are. Drawn only where those rows fall together, which is
    # what the ordering gives whenever the flux is used more than the site data.
    flux_at = sorted(order.index(name) for name in FLUX_ROWS if name in order)
    rule_after = max(flux_at) if flux_at == list(range(len(flux_at))) else None

    horizons = list(panels[GAS_PANEL[0][0]].columns)
    label = LABEL_PX / width_px
    lead = LEAD_PX / width_px
    gap = COLUMN_GAP_PX / width_px
    column = (width - label - lead - gap * (len(horizons) - 1)) / (1 + len(horizons))
    date_left = left + label
    first = date_left + column + lead

    row_height = (height - (HEADING_PX + COLUMN_TITLE_PX + GAS_LABEL_PX) / height_px) / 2
    top = bottom + height

    for row, (key, gas, _) in enumerate(GAS_PANEL):
        panel = panels[key]
        bottom_row = row == len(GAS_PANEL) - 1
        base = bottom + (1 - row) * (row_height + GAS_LABEL_PX / height_px)
        date = fig.add_axes((date_left, base, column, row_height))
        _draw_usage_panel(date, panel.attrs.get("calendar", {}), order,
                          ps.DATE_SHARE, bottom_row, rule_after)
        date.set_yticklabels(order, fontsize=ps.TICK_SIZE, color=ps.INK)
        # Named in the same bordered box as the other figures, seated above the
        # panel rather than in its corner: the corner holds the first row, which
        # here is a marked cell rather than the empty space the box needs.
        ps.panel_name(date, gas, x=-LABEL_PX / (column * width_px),
                      y=1 + 30 / (row_height * height_px))

        for index, horizon in enumerate(horizons):
            ax = fig.add_axes((first + index * (column + gap), base, column, row_height))
            _draw_usage_panel(ax, panel[horizon], order, ps.FITTED, bottom_row,
                              rule_after)
            if row == 0:
                fig.text(first + index * (column + gap) + column / 2,
                         base + row_height + 8 / height_px,
                         f"{horizon} month" + ("s" if horizon > 1 else ""),
                         # Bold, like every other panel identifier in the set:
                         # the boxed gas labels, the residual check's four titles,
                         # the year grid's years. These name the four columns and
                         # were the only ones set normal.
                         ha="center", va="bottom", fontsize=ps.LABEL_SIZE,
                         fontweight="bold", color=ps.INK)

    # Two headings rather than a legend, and this figure should not gain one.
    # Position is the encoding here, not color: the grey bars occupy one column
    # and the green four, and neither appears in the other's, so a reader could
    # lose the hue entirely and still read the panel. A key would say "grey means
    # predictable from the date", which is the heading verbatim an inch above it.
    # That is unlike the figures where a key earns its space, the forecast
    # envelope, the water table months, the year panels, where two colors share
    # one axis and position tells a reader nothing. It would also make nine the
    # number of places this figure meets a reader with text before the caption.
    date_middle = date_left + column / 2
    chosen_middle = first + (left + width - first) / 2
    heading_base = top - (HEADING_PX - 8) / height_px
    # Named per group rather than per column: the unit is a property of the two
    # questions, and five copies of it would be five repetitions of two facts.
    for middle, heading, axis in ((date_middle, DATE_HEADING, DATE_AXIS),
                                  (chosen_middle, CHOSEN_HEADING, CHOSEN_AXIS)):
        fig.text(middle, heading_base, heading, ha="center", va="bottom",
                 fontsize=ps.LABEL_SIZE, fontweight="bold", color=ps.INK,
                 linespacing=1.4)
        # Bold, because these are axis titles. Drawn as figure text rather than
        # through set_xlabel, they bypass the style's axes.labelweight and were
        # the only unbold axis titles in the set.
        fig.text(middle, bottom - 34 / height_px, axis, ha="center", va="top",
                 fontsize=ps.LABEL_SIZE, fontweight="bold", color=ps.MUTED)
    return fig


STABILITY_TEXT = ps.FigureText(
    title=("The water table coefficient refitted on drier months at "
           "Marcell Bog Lake Peatland"),
    #: Three things left this block. The tenths and fifths named the old x-axis,
    #: which counted the share of months dropped; the axis now counts the months
    #: left in the fit, so the subtitle was describing a quantity the figure had
    #: stopped drawing. "It climbs at every step" and the soil temperature
    #: comparison are the description's to make. And the closing clause about
    #: carrying the coefficient along the arrow is said where the arrow is, by the
    #: annotation that also carries the distances.
    #:
    #: "All 115" stays where "ending with 69" went: the top axis draws both
    #: numbers, but only the first of them needs saying, because a bare 115 on an
    #: axis does not say it is the whole fit window.
    subtitle=(
        "The model was fitted five times, each on fewer months than the last, "
        "starting with all 115. The water table coefficient is how much predicted "
        "emission changes per meter of water table, and each point is what that "
        "coefficient came out as, placed at the wettest month still in the fit. A "
        "coefficient that changes when its range of water table shrinks is "
        "describing the months it was fitted on rather than the peatland."
    ),
    #: The four percentages are labeled on the panel at the end of each path, so
    #: quoting them here read them back rather than adding to them. What is left
    #: is the shape of the result, which no single label carries: that both
    #: treatments climb, that they climb at every step, and that no one step
    #: proves it.
    description=(
        "Weighting each month by how well it was measured changes the numbers but "
        "not the outcome. The coefficient climbs at all four steps under both "
        "treatments and never once falls. Every step's range overlaps the first, "
        "so no single step is decisive and the pattern is the evidence. Soil "
        "temperature, run through the same experiment, moves far less. The "
        "percentage at the dry end of each line is its total change across all "
        "five fits."
    ),
)

#: The two treatments, achromatic and separated by line style. Hue would make them
#: read as two methods being compared, and they are one analysis run twice: the
#: finding is that neither survives, not that one of them does.
#: The markers are drawn open, and the two settings that make them open live here
#: rather than at the `errorbar` call. They were added at the call, which the key
#: does not go through: the panel drew hollow rings and the key drew solid marks
#: for the same two paths, for as long as this figure has had a key. Keeping every
#: property in the dict both readers share removes the way that happened rather
#: than the instance of it.
TREATMENTS = (
    ("weighted", "with weighting", {"color": ps.INK, "linestyle": "-", "linewidth": 1.8,
                                    "marker": "o", "markersize": 6.0,
                                    "markerfacecolor": "white", "markeredgewidth": 1.4}),
    ("unweighted", "without weighting", {"color": "#767676", "linestyle": (0, (7, 2, 2, 2)),
                                         "linewidth": 1.5, "marker": "^", "markersize": 6.2,
                                         "markerfacecolor": "white", "markeredgewidth": 1.4}),
)

#: The two terms, the columns each is carried in, and the unit its axis is in.
#: Soil temperature is drawn as the fitted slope rather than as its Q10, which is
#: an exponential of the same number: on the Q10 scale the same experiment reports
#: a different drift, and the two panels would no longer be comparable.
STABILITY_TERMS = (
    ("Water table", "water_table_coef", "water_table_lo", "water_table_hi",
     "Per meter of water table", None),
    # No note on the control panel. "The control: the same experiment, on a
    # coefficient that barely moves" carried a colon, restated the description's
    # last sentence, and labeled a panel already carrying a bordered
    # "Soil temperature" name three centimetres above it.
    ("Soil temperature", "soil_temp_coef", "soil_temp_lo", "soil_temp_hi",
     "Per °C of soil temperature", None),
)

STABILITY_X_AXIS = "Water table, in meters from the wettest month the model was fitted on"
COUNT_AXIS = "Months in the fit"
TESTED_LABEL = "held out and tested"
BEYOND_LABEL = (
    "The reconstruction needs this coefficient to hold {required:.2f} m beyond the\n"
    "wettest month ever fitted ({ratio:.1f} times the {span:.2f} m this experiment covers)"
)
EDGE_LABEL = "The wettest month the model was fitted on"
#: The arrow's own entry. It was the one mark on the panel carrying no key, while
#: the dashed rule beside it in the same orange carried one, so a reader met two
#: orange marks handled two different ways. Worded to name the mark rather than to
#: repeat the annotation standing on it, which carries the two distances.
BEYOND_KEY = "How far the reconstruction reaches past the fit"
#: What the strip's mark is, rather than what it measures. It read "A distance in
#: meters of water table", and a distance does not describe a bracket: the mark is
#: a span with a tick at each end, and the ticks are where a reader takes the
#: reading from.
BRACKET_KEY = "A bracketed span, in meters of water table"


def stability_paths(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The coefficient table split by treatment, each ordered driest last."""
    return {
        treatment: part.sort_values("dropped_wettest_pct").reset_index(drop=True)
        for treatment, part in frame.groupby("treatment")
    }


def _stability_window(paths: dict[str, pd.DataFrame], term, margin: float = 0.05):
    """Axis limits for one term, as a multiple of its value on the whole range.

    Returned as a multiple rather than as values because the two panels are then
    given heights in the same proportion, which is what makes their slopes
    comparable: a sixteen percent climb and a fifty-one percent climb cover
    different distances on the page only if the pixels per percent are equal.
    """
    _, value, low, high, _, _ = term
    reference = float(paths[TREATMENTS[0][0]][value].iloc[0])
    lowest = min(float(paths[name][low].min()) for name, _, _ in TREATMENTS)
    highest = max(float(paths[name][high].max()) for name, _, _ in TREATMENTS)
    room = margin * (highest - lowest)
    return reference, ((lowest - room) / reference, (highest + room) / reference)


def _draw_stability_panel(ax, paths, reference, window, term) -> None:
    """One term's coefficient against the wet edge of the range it was fitted on."""
    name, value, low, high, unit, caption = term
    # The edge of the evidence, ruled rather than filled. A shaded block reaching
    # across two thirds of the canvas gave a region marker more weight than
    # anything measured, and the space it took is where the key now sits.
    ax.axvline(0.0, color=ps.OUTSIDE, linewidth=1.1, linestyle=(0, (5, 3)), zorder=1)

    for treatment, label, style in TREATMENTS:
        frame = paths[treatment]
        anchor = float(frame["wte_max"].iloc[0])
        x = frame["wte_max"].to_numpy() - anchor
        y = frame[value].to_numpy()
        ax.errorbar(x, y, yerr=np.vstack([y - frame[low].to_numpy(),
                                          frame[high].to_numpy() - y]),
                    elinewidth=1.0, capsize=3.5, ecolor=style["color"], zorder=3,
                    label=label, **style)
        # Where it started, carried across, so the climb is read against a line
        # rather than against the axis.
        ax.plot([x.min(), 0.0], [y[0], y[0]], color=style["color"], linewidth=0.9,
                linestyle=(0, (1, 2.4)), zorder=2)
        change = 100 * (y[-1] / y[0] - 1)
        ax.annotate(f"{change:+.0f}%", xy=(x[-1], y[-1]), xytext=(-8, 0),
                    textcoords="offset points", ha="right", va="center",
                    fontsize=ps.ANNOTATION_SIZE, fontweight="bold",
                    color=style["color"], zorder=4)

    ax.set_ylim(reference * window[0], reference * window[1])
    ax.set_ylabel(unit, fontsize=ps.LABEL_SIZE, color=ps.INK)
    ax.tick_params(top=False, right=False)
    ax.grid(axis="y", color=ps.GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(ps.BOUNDARY)
    # Centred over the panel, which is where the other two multi-panel figures in
    # the set put a panel name. In the upper right it sat 722.7 px off centre and
    # read as a note in the corner rather than as the name of the row; there is
    # nothing in the upper middle of either panel to displace, since the fits
    # occupy the leftmost third and everything else is furniture below them.
    ps.panel_name(ax, name, align="center")
    if caption:
        ax.text(0.985, 0.46, caption, transform=ax.transAxes, ha="right", va="center",
                fontsize=ps.ANNOTATION_SIZE, style="italic", color=ps.MUTED, zorder=5)


def _draw_beyond_arrow(ax, required: float, span: float) -> None:
    """What the reconstruction asks for, as an arrow rather than as a region."""
    ax.annotate("", xy=(required, 0.20), xytext=(0.004, 0.20),
                xycoords=("data", "axes fraction"), textcoords=("data", "axes fraction"),
                arrowprops=dict(arrowstyle="-|>", color=ps.OUTSIDE, linewidth=1.2,
                                shrinkA=0, shrinkB=0), zorder=4)
    return ax.text(required / 2, 0.245,
                   BEYOND_LABEL.format(required=required, ratio=required / span,
                                       span=span),
                   transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                   fontsize=ps.ANNOTATION_SIZE, color=ps.OUTSIDE, linespacing=1.5,
                   zorder=4)


def _draw_stability_strip(ax, span, tested: float) -> None:
    """The one distance the panels cannot show: how far the holdout actually got."""
    ax.set_ylim(0, 1)
    ax.plot([-tested, 0.0], [0.5, 0.5], color=ps.BOUNDARY, linewidth=1.2, zorder=3)
    for edge in (-tested, 0.0):
        ax.plot([edge, edge], [0.28, 0.72], color=ps.BOUNDARY, linewidth=1.2, zorder=3)
    ax.text(-tested - 0.008, 0.5, f"{TESTED_LABEL}: {tested:.2f} m", ha="right",
            va="center", fontsize=ps.ANNOTATION_SIZE, color=ps.MUTED)
    ax.set_xlim(*span)
    ax.set_yticks([])
    ax.tick_params(top=False, right=False, left=False)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(ps.BOUNDARY)


class _MarkKey(Patch):
    """A stand-in whose only job is to be recognised by a handler below.

    Three marks on this figure cannot be keyed by a `Line2D`, because a legend
    lays every handle on three sample points and draws the marker at each of them.
    A marker-only entry therefore renders as **three** ticks where the panel draws
    one interval, and the bracket renders with a third tick in its middle where
    the strip has two at its ends. Neither was noticed: at this size three ticks
    in a row read as one thick mark.
    """


class _ArrowKey(_MarkKey):
    """The reach the reconstruction needs, drawn as an arrow."""


class _IntervalKey(_MarkKey):
    """Where the coefficient landed in the resamples: a capped interval."""


class _BracketKey(_MarkKey):
    """A span in meters, bracketed at both ends."""


class _IntervalHandler(HandlerBase):
    """A vertical interval with a cap at each end, as `errorbar` draws it."""

    def create_artists(self, legend, orig_handle, xdescent, ydescent,
                       width, height, fontsize, trans):
        middle, cap = width / 2.0, 3.5
        parts = [Line2D([middle, middle], [height * 0.02, height * 0.98])]
        parts += [Line2D([middle - cap, middle + cap], [y, y])
                  for y in (height * 0.02, height * 0.98)]
        for part in parts:
            part.set(color=ps.BOUNDARY, linewidth=1.0)
            part.set_transform(trans)
        return parts


class _BracketHandler(HandlerBase):
    """A horizontal span with a tick at each end, as the strip draws it.

    Two ticks, not three. The end ticks are what make it a bracket rather than a
    rule, and a third in the middle marks a place the strip does not.
    """

    def create_artists(self, legend, orig_handle, xdescent, ydescent,
                       width, height, fontsize, trans):
        parts = [Line2D([0.0, width], [height / 2.0, height / 2.0])]
        parts += [Line2D([x, x], [height * 0.18, height * 0.82])
                  for x in (0.0, width)]
        for part in parts:
            part.set(color=ps.BOUNDARY, linewidth=1.2)
            part.set_transform(trans)
        return parts


class _ArrowHandler(HandlerPatch):
    """Draw the arrow entry as an arrow.

    Every other handle in this key is a line and needs no handler. An arrow drawn
    as a plain line loses the head, which is the whole of what distinguishes it
    from the dashed rule two rows above it in the same hue.
    """

    def create_artists(self, legend, orig_handle, xdescent, ydescent,
                       width, height, fontsize, trans):
        arrow = FancyArrow(0.0, height / 2.0, width, 0.0,
                           length_includes_head=True, head_width=height * 0.75,
                           head_length=width * 0.30, width=0.9,
                           color=ps.OUTSIDE, linewidth=0.0)
        arrow.set_transform(trans)
        return [arrow]


def _stability_legend(fig, ax) -> None:
    """One key for both panels, in the ground the shaded region used to cover.

    Two columns with ruled headings, as elsewhere in the set. Panel b carries the
    same marks and no key of its own, so a second one would repeat itself.
    """
    blank = Line2D([], [], linestyle="none", marker="none")
    entries = [(blank, r"$\bf{The\ two\ treatments}$")]
    entries += [(Line2D([], [], **style), label) for _, label, style in TREATMENTS]
    # Three spacers, not two. The columns fill top to bottom, so the first has to
    # be padded to the length of the second or the second heading falls to the
    # foot of the first column instead of standing over the marks it names. The
    # arrow entry made the second column five long and this three.
    entries += [(blank, ""), (blank, ""), (blank, "")]
    entries += [
        (blank, r"$\bf{What\ the\ marks\ show}$"),
        (_IntervalKey(), "Where the coefficient landed in 500 resamples"),
        (Line2D([], [], color=ps.INK, linestyle=(0, (1, 2.4)), linewidth=0.9),
         "Its value on the whole range, carried across"),
        (Line2D([], [], color=ps.OUTSIDE, linestyle=(0, (5, 3)), linewidth=1.1),
         EDGE_LABEL),
        (_BracketKey(), BRACKET_KEY),
        (_ArrowKey(), BEYOND_KEY),
    ]
    ps.legend(ax, handles=[h for h, _ in entries],
              labels=[label for _, label in entries],
              handler_map={_ArrowKey: _ArrowHandler(),
                           _IntervalKey: _IntervalHandler(),
                           _BracketKey: _BracketHandler()},
              # Seated over the orange annotation rather than in the upper right.
              # There it sat 13.9 px under the bordered panel name and 3.3 px off
              # the panel's own edge, crowding two things at once; the border made
              # both visible. The anchor is set again after the balance, from the
              # annotation's drawn position, since that is the object it is seated
              # against and the balance moves the panel under both of them.
              loc="lower center", bbox_to_anchor=(0.5, 0.42), ncol=2,
              # Bordered. Five marks in two columns standing loose on the panel
              # read as annotation scattered in empty ground; a frame says they
              # are one object and that the ground around them is not part of it.
              frameon=True, edgecolor=ps.BOUNDARY, facecolor="white",
              labelspacing=0.42, columnspacing=2.2, handlelength=2.4,
              handletextpad=0.9, fontsize=ps.LEGEND_SIZE - 1.0, borderpad=0.55,
              # The inner padding was already taken to zero here, so the outer
              # inset was the only thing left between the anchor and the corner
              # it names. It was the default half a font size, 8.85 px, which
              # put the key 12.2 px inside the axes where 3.3 px was chosen.
              borderaxespad=0.0)


#: Pixel allocations for the stability figure. The strip is thin because it now
#: carries one bracket: the counts moved onto the top axis, where the fits they
#: describe are, and the region the reconstruction needs is an arrow on the panel.
STABILITY_STRIP_PX = 46
STABILITY_XLABEL_PX = 76
STABILITY_COUNT_PX = 52
STABILITY_GAP_PX = 26


def _seat_axis_names(fig, axes, pad_px: float = 17.0) -> None:
    """Set both axis names just clear of the widest tick label on either panel.

    Measured rather than guessed, and measured across both panels rather than
    each on its own: one panel's ticks read 7 and the other's 0.12, so a fixed
    inset either collides with the second or strands the first far to the left.
    The pad clears the tick labels and half the rotated name, which is anchored
    at its center.
    """
    fig.canvas.draw()
    widest = max(label.get_window_extent().width
                 for ax in axes for label in ax.get_yticklabels() if label.get_text())
    for ax in axes:
        width_px = ax.get_window_extent().width
        ax.yaxis.set_label_coords(-(widest + pad_px) / width_px, 0.5)


#: How far the key stands above the annotation it is seated over. Wider than the
#: 18 px the set uses between a block and a text block, because these two are not
#: a block and its margin: they are two objects in one field of empty ground, and
#: at 18 px they read as one stack rather than as a key above a note.
STABILITY_KEY_GAP_PX = 40.0

#: How far the months axis name stands above its own numbers. The numbers are set
#: outside the axes, so this cannot be expressed as an axes fraction and is
#: measured off them.
COUNT_AXIS_PAD_PX = 14.0


def _seat_count_axis_name(fig, counts) -> None:
    """Centre the months axis name on the numbers it names.

    It was centred on the axes, which is 1652 px wide, while the five fits it
    counts occupy the leftmost 466 of them. That put the name 528 px to the right
    of anything it labeled, over the empty ground the arrow crosses.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [label.get_window_extent(renderer) for label in counts.get_xticklabels()
             if label.get_text()]
    middle = (min(box.x0 for box in boxes) + max(box.x1 for box in boxes)) / 2.0
    # Above the numbers, not level with them. `set_label_coords` reads its pair in
    # axes fractions, and 1.0 is the top of the axes rather than the top of the
    # tick labels, which stand outside it: seating the name there dropped it into
    # the row of numbers it names.
    over = max(box.y1 for box in boxes) + COUNT_AXIS_PAD_PX
    counts.xaxis.set_label_coords(
        *counts.transAxes.inverted().transform((middle, over)),
        transform=counts.transAxes)


def _seat_stability_key(fig, ax, beyond) -> None:
    """Centre the key over the annotation, once the panel has stopped moving.

    Measured against the annotation rather than set at a fraction, because the
    annotation's own height is fixed in points while the panel's is not: the
    balance rescales the panel and a fraction chosen before it drifts.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    note = beyond.get_window_extent(renderer)
    panel = ax.get_window_extent(renderer)
    # Centred in the ground above the annotation rather than set at a fixed gap
    # over it. At 40 px it was nearer the annotation than anything else on the
    # panel was to anything, which made the two read as one stack; the column
    # above it is empty as far as the panel's own top, because the fits end well
    # to the left, so there is nothing to spend it on but this.
    seat = ax.transAxes.inverted().transform(
        ((note.x0 + note.x1) / 2, (note.y1 + panel.y1) / 2))
    ax.get_legend().set_bbox_to_anchor(tuple(seat))
    ax.get_legend().set_loc("center")


def coefficient_stability(paths: dict[str, pd.DataFrame], required: float,
                          tested: float) -> Figure:
    """The water table coefficient as the wet end of its evidence is taken away.

    Drawn against the water table itself rather than against the share of months
    removed, so what the reconstruction asks for can be measured on the same axis.
    Every refit occupies the narrow band on the left; the arrow is what the
    reconstruction needs the coefficient to hold across, and nothing is drawn
    along it because nothing was measured there.

    Each panel carries its own coefficient in its own unit. The comparison is kept
    by giving the panels heights in proportion to the range each has to cover, so
    a percent of change is the same number of pixels on both and the control panel
    cannot flatter itself with a tighter axis.
    """
    fig, (left, bottom, width, height) = ps.canvas_area(STABILITY_TEXT, size="stacked")
    width_px, height_px = ps.SIZES["stacked"]
    strip = STABILITY_STRIP_PX / height_px
    label_band = STABILITY_XLABEL_PX / height_px
    counts_band = STABILITY_COUNT_PX / height_px
    gap = STABILITY_GAP_PX / height_px

    reference = paths[TREATMENTS[0][0]]
    anchor = float(reference["wte_max"].iloc[0])
    x = reference["wte_max"].to_numpy() - anchor
    pad = 0.05 * (required - x.min())
    span = (x.min() - pad, required + pad)

    windows = [_stability_window(paths, term) for term in STABILITY_TERMS]
    spans = [high - low for _, (low, high) in windows]
    room = height - strip - label_band - counts_band - 2 * gap
    heights = [room * one / sum(spans) for one in spans]

    top = bottom + height - counts_band
    axes = []
    for index, (term, (anchor_value, window)) in enumerate(zip(STABILITY_TERMS, windows)):
        base = top - sum(heights[: index + 1]) - index * gap
        ax = fig.add_axes((left, base, width, heights[index]))
        _draw_stability_panel(ax, paths, anchor_value, window, term)
        ax.set_xlim(*span)
        ax.set_xticklabels([])
        axes.append(ax)

    # How many months each fit had, on the axis above the fits themselves. The
    # share dropped said the same thing counting down while the axis counted up.
    counts = axes[0].secondary_xaxis("top")
    counts.set_xticks(list(x))
    # Bold, like the percentages at the other end of each path. They are the
    # sample size every point rests on, which is a reading a reader takes rather
    # than apparatus they read past. Not boxed: this set borders panel names and
    # nothing else, so a second kind of box on one panel would cost the border
    # the one meaning it has.
    counts.set_xticklabels([f"{n:.0f}" for n in reference["n_months"]],
                           fontsize=ps.TICK_SIZE - 1.5, color=ps.MUTED,
                           fontweight="bold")
    counts.set_xlabel(COUNT_AXIS, fontsize=ps.LABEL_SIZE, color=ps.INK, labelpad=6)
    counts.tick_params(length=3.2, width=0.9, colors=ps.MUTED)
    counts.spines["top"].set_visible(False)

    _seat_axis_names(fig, axes)
    beyond = _draw_beyond_arrow(axes[0], required, abs(x.min()))
    _stability_legend(fig, axes[0])
    # Ruled after the balance below, for the reason recorded on the reconstruction
    # figure: the rules do not move with the legend.


    strip_base = bottom + label_band
    strip_ax = fig.add_axes((left, strip_base, width, strip))
    _draw_stability_strip(strip_ax, span, tested)
    name = fig.text(left + width / 2, strip_base - 44 / height_px, STABILITY_X_AXIS,
                    ha="center", va="top", fontsize=ps.LABEL_SIZE,
                    fontweight="bold", color=ps.INK)
    # The block sat 34 px under the subtitle and 147 px over the description, the
    # widest split left in the set. The axis name below the strip is figure text
    # and the panel names and key are axes text, so neither reaches the balancer
    # through `get_tightbbox`; both are passed as ink. Nothing reflows, because
    # every one of them is placed against the strip or the panel it belongs to
    # and moves with it, except this name, which is put back afterwards.
    def replace() -> None:
        floor = min(ax.get_position().y0 for ax in (*axes, strip_ax))
        name.set_position((left + width / 2, floor - 44 / height_px))
        # The months axis name is seated in pixels off its own numbers, so it has
        # to be seated again whenever the panel is rescaled. Seated only after the
        # balance it becomes the block's top ink at a height the balance never
        # measured, and the two gaps stop agreeing.
        _seat_count_axis_name(fig, counts)

    ps.balance_drawing_block(fig, *axes, strip_ax, extra=[name], reflow=replace)
    _seat_stability_key(fig, axes[0], beyond)
    ps.underline_legend_headings(fig, axes[0])
    return fig


# --------------------------------------------------------------------------
# Covariate availability
# --------------------------------------------------------------------------

AVAILABILITY_TEXT = ps.FigureText(
    title=("Which months each measurement and each analysis cover at "
           "Marcell Bog Lake Peatland"),
    subtitle=(
        "Each row in the upper block is one measurement and the bar covers the "
        "months it exists, ordered by where each record ends so the shortest sit "
        "at the bottom. The environmental records begin 19 years before either "
        "flux does, and that gap is the span the reconstruction covers. The rows "
        "below show what each analysis could use, which follows directly from "
        "the block above, since an analysis needing several records at once can "
        "only run where all of them overlap."
    ),
    description=(
        # The framing sentence that used to open this is gone: the subtitle
        # carries the mechanism, and stating it again as a claim repeats it.
        # That frees the line the hollow marks need. They earn it, because the
        # orange labels say why those months were set aside and not that the
        # months exist, and on a coverage figure a hollow mark reads as missing
        # data unless a reader is told otherwise.
        "Air temperature and precipitation stop at the end of 2019, which ends "
        "the months the model could learn from and leaves 60 months of methane "
        "the tower recorded but the model cannot use. Forecasts inherit the same "
        "limit, stopping in 2020 and running four years short of the flux. They "
        "cannot begin until 48 months have accumulated, which for methane "
        "took 62 calendar months because of the gaps in 2013 and 2014. Only the "
        "seasonal benchmarks, which need no drivers, reach 2024 on both gases."
    ),
)

#: One register across the three, each naming what the rows below it are, with
#: parentheses rather than commas. Measured at 9.5 pt bold: 422, 338 and 507 px,
#: each inside a frame that clears the plot within the 580 px gutter.
#:
#: Not "measured at the site": only the two fluxes come from the tower. Soil
#: temperature is the experimental forest's weekly record, and precipitation is
#: the average of a north and a south gauge, as `covariates.load_precipitation`
#: says. Where each series is measured is a question for the notes, not a claim to
#: slip into a heading.
BLOCK_HEADINGS = ("What was measured (monthly means)", "Which months the model used",
                  "Which months the forecasts were checked on")

#: The two groups the key splits into, which are the two the figure is built on.
#: An unheaded row of four flattens the distinction: the first two say what the
#: record holds and the second two say what the study decided about it, and that
#: is the same division as the upper block against the lower.
#: Bold and a colon, not bold and a rule, because these sit at the left of their
#: rows. That is one of the set's two forms and the rule for choosing between
#: them is in `plotstyle`, under "Naming a group inside a key"; this is the only
#: key in the set the colon applies to.
RECORD_HEADING = r"$\bf{What\ the\ record\ holds:}$"
DECIDED_HEADING = r"$\bf{What\ the\ study\ decided:}$"
TIME_AXIS = "Year"
PRESENT_LABEL = "months covered"
MISSING_LABEL = "a month missing"
ASIDE_LABEL = "set aside by the study"
FITTED_RANGE_LABEL = "the range the model was fitted on"
TRAINING_LABEL = "48 months of training first"

#: The key's own geometry, tightened from the defaults so it spends less of the
#: room between the subtitle and the panel. See the note in study.md for what
#: each lever bought and where it stopped.
LEGEND_HANDLE = 1.8
LEGEND_TEXT_PAD = 0.5
LEGEND_ROW_GAP = 0.22
LEGEND_BORDER_PAD = 0.35

#: The key's clearance above the panel is not a constant. It is set after the
#: block settles, from `MIN_BLOCK_GAP_PX` and the panel's final height, so the
#: gap under the key matches the gap over it and the four elements step down
#: evenly. `borderaxespad` goes to zero so the anchor is the whole of it: at the
#: default half font unit the anchor controlled only part of the distance, which
#: is how a matplotlib default nobody chose came to set this spacing.

#: Bar geometry in row units. The bars are the figure, so they are heavy; the notch
#: has to read as a break in one rather than as a mark on top of one, which is why
#: it is a hole in the bar with a tick under it rather than a symbol over it. One
#: tick per stretch of missing months, not per month: five months adjacent are one
#: break in the record, and five ticks side by side were an indistinct smear.
BAR_HEIGHT = 0.46
NOTCH_TICK = 0.42


def _runs(index: pd.PeriodIndex) -> list[tuple[pd.Period, pd.Period]]:
    """Contiguous stretches of months, so a gap is a hole rather than a color."""
    months = pd.PeriodIndex(sorted(index), freq="M")
    runs, start, previous = [], None, None
    for month in months:
        if start is None:
            start = previous = month
        elif month == previous + 1:
            previous = month
        else:
            runs.append((start, previous))
            start = previous = month
    if start is not None:
        runs.append((start, previous))
    return runs


def _position(period: pd.Period) -> float:
    """A month as a decimal year, so the axis is time rather than an index."""
    return period.year + (period.month - 1) / 12.0


def availability_rows(
    series: dict[str, pd.Series],
    set_aside: dict[str, tuple[tuple[pd.PeriodIndex, str], ...]] | None = None,
) -> list[dict]:
    """Each series as its span, its interior gaps, and what was set aside in it.

    A month is one of four things and the difference matters: measured, missing
    from an otherwise unbroken run, present but set aside by a decision, or
    outside the years the series covers at all. Only the first three are drawn.
    """
    set_aside = set_aside or {}
    rows = []
    for name, values in series.items():
        present = pd.PeriodIndex(values.dropna().index, freq="M").sort_values()
        covered = pd.period_range(present.min(), present.max(), freq="M")
        rows.append({
            "name": name,
            "present": present,
            "gaps": covered.difference(present),
            "aside": tuple(set_aside.get(name, ())),
            "months": len(present),
        })
    # Latest-ending record first, earliest-starting to break a tie. Ordered this
    # way the right edges step inward and stop exactly where the fitting window
    # does, which turns the study's central constraint into a shape.
    return sorted(rows, key=lambda row: (-row["present"].max().ordinal,
                                         row["present"].min().ordinal))


def _draw_bar(ax, y: float, first: pd.Period, last: pd.Period, **kwargs) -> None:
    """One stretch of months as a bar, from the first to the end of the last."""
    start = _position(first)
    ax.add_patch(Rectangle((start, y - BAR_HEIGHT / 2),
                           _position(last) + 1 / 12.0 - start, BAR_HEIGHT, **kwargs))


def _draw_availability_row(ax, y: float, row: dict) -> None:
    """A series: what exists, where it breaks, and what was set aside in it."""
    for first, last in _runs(row["present"]):
        _draw_bar(ax, y, first, last, facecolor=ps.MEASURED, edgecolor="none", zorder=3)
    # One tick per break, because a single missing month is four pixels wide across
    # thirty-five years and reads as nothing at all on its own.
    for first, last in _runs(row["gaps"]):
        middle = (_position(first) + _position(last) + 1 / 12.0) / 2
        ax.plot([middle] * 2,
                [y - BAR_HEIGHT / 2 - NOTCH_TICK, y - BAR_HEIGHT / 2 - 0.02],
                color=ps.MEASURED, linewidth=1.4, zorder=4)
    # Discarded, which is what the support hue means everywhere else in the set.
    for months, _ in row["aside"]:
        for first, last in _runs(months):
            _draw_bar(ax, y, first, last, facecolor="white", edgecolor=ps.OUTSIDE,
                      linewidth=1.2, zorder=5)


#: The span that defines what "inside the fitted range" means everywhere else in
#: the study, drawn in the hue that carries it. The span beside it stays neutral:
#: 117 of its 230 months lie outside that range and 113 inside, so one hue across
#: the whole bar would assert a verdict the study measured as mixed. Every other
#: bar on the panel takes the same neutral, since a second gray would draw a
#: distinction the blocks already carry by position.


def _draw_window_row(ax, y: float, row: dict) -> None:
    """A window: the months it covers, and any lead spent on training first."""
    if row.get("lead"):
        first, last = row["lead"]
        ax.plot([_position(first), _position(last)], [y, y], color=ps.MUTED,
                linewidth=1.1, zorder=3)
    _draw_bar(ax, y, row["first"], row["last"],
              facecolor=ps.INSIDE if row.get("support") else ps.MEASURED,
              edgecolor="none", zorder=3)


#: How far a block heading's frame stays clear of the plot, in pixels.
HEADING_CLEAR_PX = 8


def _seat_headings(fig, ax, headings, sizes) -> None:
    """Center each block heading over the row names it heads.

    Measured rather than placed: the names are right-aligned against the plot and
    the blocks are different widths, so where the middle of a block's names falls
    is a fact about the longest name in it.
    """
    fig.canvas.draw()
    labels = ax.get_yticklabels()
    to_axes = ax.transAxes.inverted()
    edge = ax.get_window_extent().x0
    start = 0
    for (y, name), size in zip(headings, sizes):
        extents = [label.get_window_extent() for label in labels[start:start + size]]
        middle = (min(box.x0 for box in extents) + max(box.x1 for box in extents)) / 2
        seated = ax.text(to_axes.transform((middle, 0))[0], y, name,
                         transform=blended_transform_factory(ax.transAxes, ax.transData),
                         ha="center", va="center", fontsize=ps.LABEL_SIZE,
                         fontweight="bold", color=ps.INK,
                         bbox=dict(boxstyle="round,pad=0.42", facecolor="white",
                                   edgecolor=ps.BOUNDARY, linewidth=0.9))
        # A heading wider than the names it heads would reach into the plot if it
        # were truly centered on them. Where that happens it is pushed left until
        # its frame clears: off center by a little beats a frame over the bars.
        fig.canvas.draw()
        over = seated.get_bbox_patch().get_window_extent().x1 - (edge - HEADING_CLEAR_PX)
        if over > 0:
            seated.set_x(to_axes.transform((middle - over, 0))[0])
        start += size


#: Row spacing. The wide gap holds the two reasons a month was set aside, which
#: are labeled where they happened rather than encoded in the key; the narrow one
#: separates the two things the lower block holds, which are not the same thing.
BLOCK_GAP = 2.2
GROUP_GAP = 1.5
HEADING_OFFSET = 1.15

#: Room at the left for the row names and at the top for the key, in pixels. Taken
#: out of the drawing rectangle rather than out of the canvas, so the title and the
#: description stay centered on the page rather than on the bars.
#:
#: Wide, because the two rows in the middle block say what their span is rather
#: than naming it — 565 px at 9.5 pt — and a name a reader has to already know is
#: worse than a narrower timeline. The cost is 2.4 px per month instead of 2.9,
#: which the notch ticks were already there to survive.
NAME_GUTTER_PX = 580
KEY_BAND_PX = 40


def covariate_availability(rows: list[dict],
                           groups: Sequence[tuple[str, list[dict]]]) -> Figure:
    """Every series against every window the study drew, on one timeline.

    Two blocks rather than one: the windows are choices made from what was
    available, and shading them across the series would draw them as a property of
    the data. Drawn as their own rows with their own names, they read as what they
    are, and the alignments carry the argument — the fitting window ends where the
    shortest measurement does, and the projection covers the years the flux does
    not reach.

    Rows are ordered by where each record ends, latest first, so the right edges
    step inward and the last step is the month the fitting window stops at. Three
    full-height guides were drawn at those boundaries before the ordering did the
    work, and went with it.
    """
    # Measured rather than allotted. The allotment gives the title a share of its
    # own height, 59.4 px for 29 px of ink, so the subtitle sat 30.4 px under a
    # title while the key beneath it had 11.7. Measuring seats the subtitle one
    # gap under what the title actually occupies and hands the difference to the
    # block, where the key needs it.
    fig, (left, bottom, width, height) = ps.canvas_area(
        AVAILABILITY_TEXT, size="standard")
    width_px, height_px = ps.SIZES["standard"]
    gutter = NAME_GUTTER_PX / width_px
    key_band = KEY_BAND_PX / height_px
    ax = fig.add_axes((left + gutter, bottom, width - gutter, height - key_band))

    series_y = list(range(len(rows)))
    for y, row in zip(series_y, rows):
        _draw_availability_row(ax, y, row)

    # The lower block holds two different things: spans of months the study drew
    # on, and spans it scored predictions over. Grouped and headed separately
    # rather than distinguished by a mark, which would have cost a fourth key.
    headings = [(series_y[0] - HEADING_OFFSET, BLOCK_HEADINGS[0])]
    window_y, window_rows = [], []
    cursor = len(rows) + BLOCK_GAP
    for index, (heading, group) in enumerate(groups):
        headings.append((cursor - HEADING_OFFSET, heading))
        for row in group:
            _draw_window_row(ax, cursor, row)
            window_y.append(cursor)
            window_rows.append(row)
            cursor += 1
        cursor += GROUP_GAP if index < len(groups) - 1 else 0

    first_year = min(_position(row["present"].min()) for row in rows)
    ax.set_xlim(first_year - 0.5, 2026.4)
    ax.set_ylim(window_y[-1] + 1.0, -HEADING_OFFSET - 0.9)
    ax.set_yticks(series_y + window_y)
    ax.set_yticklabels([row["name"] for row in rows + window_rows],
                       fontsize=ps.TICK_SIZE)
    ax.set_xticks(list(range(1990, 2026, 5)))
    ax.set_xticklabels([str(year) for year in range(1990, 2026, 5)])
    # Named, though the direction is plain from the labels. No name on the other
    # axis: every row carries its own, and a title over them would repeat six.
    ax.set_xlabel(TIME_AXIS, fontsize=ps.LABEL_SIZE, color=ps.INK, labelpad=8)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=ps.GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(ps.BOUNDARY)

    ax.axhline(len(rows) + BLOCK_GAP - 1.9, color=ps.BOUNDARY, linewidth=0.8,
               alpha=0.45, zorder=1)
    heading_at = blended_transform_factory(ax.transAxes, ax.transData)
    outside = -gutter / (width - gutter)
    # Framed as the panel names are elsewhere in the set, and each seated over the
    # names it heads rather than at the margin, where the widest block's labels had
    # left the other two headings floating far from their own rows.
    _seat_headings(fig, ax, headings, [len(rows)] + [len(group) for _, group in groups])

    # Both reasons stacked in the clear ground to the right of the row they belong
    # to, half a row above and below it, so each leader is short and neither
    # crosses a bar. The key says the marks are months set aside; these say why.
    for y, row in zip(series_y, rows):
        for index, (months, reason) in enumerate(row["aside"]):
            ps.annotate(ax, reason,
                        xy=(_position(months.max()) + 1 / 12.0, y),
                        xytext=(_position(row["present"].max()) + 0.8,
                                y - 0.55 + 1.1 * index),
                        ha="left", va="center", color=ps.OUTSIDE,
                        arrowprops=dict(arrowstyle="-", color=ps.OUTSIDE, linewidth=0.9,
                                        shrinkA=3, shrinkB=3))

    # Two headed groups filled down their columns, not one row of four. The four
    # entries divide exactly as the panel does: two say what the record holds and
    # two say what the study decided about it, which is the upper block against
    # the lower. Unheaded they read as one list of marks and the division the
    # figure exists to draw is not in its key. It is also narrower this way, 670
    # px against 1095, at the cost of 58 px of height the balance absorbs.
    # One group to a row, each headed at its left, so the boundary between the two
    # is a line break rather than a reader noticing which item has no marker.
    # Five entries cannot go in one row: they measure 1897 px against 1652 of
    # drawable width, and nothing short of 7.5 pt closes that, which is below the
    # set's floor. Matplotlib fills columns top to bottom, so the order is
    # interleaved and the shorter group is padded with an empty cell.
    blank = Line2D([], [], linestyle="none", marker="none")
    covered = Patch(facecolor=ps.MEASURED, edgecolor="none")
    missing = Line2D([], [], color=ps.MEASURED, linestyle="none", marker="|",
                     markersize=10, markeredgewidth=1.4)
    aside = Patch(facecolor="white", edgecolor=ps.OUTSIDE, linewidth=1.2)
    fitted = Patch(facecolor=ps.INSIDE, edgecolor="none")
    # The lead on a forecast row, which had a label written for it and never
    # wired to anything: TRAINING_LABEL sat with no caller.
    training = Line2D([], [], color=ps.MUTED, linewidth=1.1)
    entries = [
        (blank, RECORD_HEADING), (blank, DECIDED_HEADING),
        (covered, PRESENT_LABEL), (aside, ASIDE_LABEL),
        (missing, MISSING_LABEL), (fitted, FITTED_RANGE_LABEL),
        (blank, ""), (training, TRAINING_LABEL),
    ]
    ps.legend(ax, handles=[h for h, _ in entries], labels=[label for _, label in entries],
              loc="lower center",
              # Centred on the canvas, not on the axes. The row labels take a
              # wide left gutter, so the axes occupies only the right two thirds
              # and a key centred in axes fractions hangs off the canvas edge.
              # Blended: x from the figure, y from the axes, so the key still
              # rides the panel when the block is rebalanced.
              bbox_to_anchor=(0.5, 1.0),
              bbox_transform=blended_transform_factory(fig.transFigure, ax.transAxes),
              ncol=4,
              framealpha=1.0, handlelength=LEGEND_HANDLE, handletextpad=LEGEND_TEXT_PAD,
              columnspacing=1.6, labelspacing=LEGEND_ROW_GAP,
              borderpad=LEGEND_BORDER_PAD, borderaxespad=0.0,
              fontsize=ps.LEGEND_SIZE - 1.0)
    # No rules here: these headings sit at the left of their rows, which is the
    # colon's case under the set-wide rule in `plotstyle`. Nothing has to be
    # drawn after the block settles, which is the incidental benefit rather than
    # the reason.
    ps.balance_drawing_block(fig, ax)
    # The key rides the panel at the same clearance the block keeps from the text
    # above and below it, so the four elements step down evenly. Set from the
    # panel's final height, which is only known once the block has settled.
    ax.get_legend().set_bbox_to_anchor(
        (0.5, 1.0 + ps.MIN_BLOCK_GAP_PX / ax.get_window_extent().height),
        transform=blended_transform_factory(fig.transFigure, ax.transAxes))
    ps.balance_drawing_block(fig, ax)
    return fig


# --------------------------------------------------------------------------
# The seasonal cycle and what it leaves
# --------------------------------------------------------------------------

SEASONAL_TEXT = ps.FigureText(
    title="The seasonal cycle in monthly flux at Marcell Bog Lake Peatland",
    subtitle=(
        # It ended "It is where the size of each season lives. Nothing tested here
        # predicted it", where the second "it" could be read as the row or as the
        # size of the season, and the finding depended on which. The finding is in
        # the description now and the subtitle stops at describing the rows.
        "Each column is one gas and each row is one part of its record. The "
        "middle row is one average shape for the whole record, the same twelve "
        "values repeated every year, and the bottom row is what the measurements "
        "leave once that shape is taken out. What remains there is the size of "
        "each season."
    ),
    description=(
        # The precise figures are in the notes: the spread ratios, the two swings,
        # both trend p values, the level trend and the fold caveat. What a reader
        # needs while looking is the share, the fold change and the fact that
        # nothing reached it.
        #
        # "Neither showing a trend" rather than "neither of them trending": at
        # p = 0.215 and 0.505 no trend was detected, which is not the same as
        # none being there.
        "The repeating shape accounts for 74% of the variation on methane and "
        "71% on carbon dioxide, leaving roughly a quarter of each record "
        "unexplained by it. That quarter is where the size of each season sits, "
        "and it varies more than fourfold on methane between its weakest year "
        "and its strongest, threefold on carbon dioxide, with neither showing a "
        "trend. Structure left in a bottom row usually means the shape taken out "
        "was the wrong one. Here it is the result. This year-to-year variation "
        "is what nothing tested here "
        "predicted, across eight fitted models, four benchmarks and four "
        "measured drivers."
    ),
)

#: The three parts, top to bottom, and the column each is held in.
#: Each row named for what it is and how it was built, with the ink and the weight
#: it is drawn at. The measurements are neutral and heaviest, since they are the
#: record. The average year takes `INSIDE`, which means retained across the set and
#: is what this row is: the benchmark that beat every fitted model. What that
#: leaves is filled rather than drawn, in `FITTED`, so the row carries the mass its
#: finding deserves. Each parenthetical says something the name cannot: how a
#: monthly value is built, that the middle row is one fixed set of twelve rather
#: than something recomputed, and what the subtraction actually is.
#: Padding around each row's data before the common scale is set, so a line does
#: not run along its own frame.
SEASONAL_MARGIN = 0.13

#: Years with fewer months than this are dropped from the amplitude, since a year
#: missing its summer would report a swing it never had.
AMPLITUDE_MIN_MONTHS = 10

SEASONAL_ROWS = (
    ("Monthly flux measured at the tower "
     "(each month averaged from its half-hourly readings)", "observed", ps.INK, 1.7),
    ("The average flux for each calendar month "
     "(twelve values, repeated every year)", "repeating", ps.INSIDE,
     ps.SEASONAL_SHAPE_WIDTH),
    ("Each month compared to a typical year "
     "(the measurement minus that month's average)", "leftover", ps.FITTED, 1.0),
)

def seasonal_parts(series: pd.Series) -> pd.DataFrame:
    """A flux record split into the shape that repeats and what it leaves.

    One shape for the whole record, the twelve month-of-year averages, applied to
    every year alike. That is the study's own benchmark, so the split answers the
    question the benchmark asks. It is fitted on every observed month here, which
    the benchmark does not do: inside a fold it sees only months up to the origin.
    Nothing is predicted on this figure, so there is nothing to leak into.
    """
    from forecast import preprocessing
    from scipy import stats

    observed = series.dropna()
    leftover = preprocessing.SeasonalAdjustment().fit(observed).transform(observed)
    panel = pd.DataFrame({"observed": observed, "repeating": observed - leftover,
                          "leftover": leftover})

    counted = observed.groupby(observed.index.year).size()
    swing = observed.groupby(observed.index.year).agg(lambda year: year.max() - year.min())
    swing = swing[counted >= AMPLITUDE_MIN_MONTHS]
    trend = stats.linregress(np.asarray(swing.index, dtype=float), swing.to_numpy())
    panel.attrs["swing"] = swing
    panel.attrs["trend_p"] = float(trend.pvalue)
    panel.attrs["explained"] = float(1 - leftover.var() / observed.var())
    panel.attrs["left_share"] = float(leftover.std() / observed.std())
    return panel


#: Room at the left for the row names, at the top for the gas labels, and between
#: the rows for each panel's own tick labels.
#:
#: Nothing is reserved at the right any more. A strip stood there for the scale
#: bars, which took three rounds to label and never read: the label had to be
#: rotated, and every degree of rotation slows reading. What they were for is one
#: sentence of the description, stated exactly rather than left to be measured.
SEASONAL_GUTTER_PX = 624
SEASONAL_HEAD_PX = 46
SEASONAL_ROW_GAP_PX = 64
SEASONAL_COLUMN_GAP_PX = 108

SEASONAL_TIME_AXIS = "Year"

#: Points between the bottom row's tick labels and its axis name. The name used
#: to be figure text placed 38 px below the row, which is 18.2 pt at this DPI.
SEASONAL_TIME_AXIS_PAD_PT = 12.0

#: Space between an axis name and the nearest of its tick labels. Left to
#: matplotlib the name sits off the widest label on the axis, whichever one that
#: is, which left gaps running from −4 to 8 px across the six panels.
SEASONAL_NAME_GAP_PX = 5


def _draw_seasonal_row(ax, values: pd.Series, ink: str, weight: float,
                       filled: bool) -> None:
    """One part of one gas, against the time axis every panel shares."""
    when = values.index.to_timestamp()
    if filled:
        # A departure from zero, so the distance from zero is what is drawn. It
        # also gives the row the weight the finding in it deserves.
        ax.axhline(0.0, color=ps.BOUNDARY, linewidth=0.9, zorder=1)
        ax.fill_between(when, 0.0, values.to_numpy(), color=ink,
                        alpha=ps.LEFTOVER_FILL_ALPHA, linewidth=0, zorder=2)
    ax.plot(when, values.to_numpy(), color=ink, linewidth=weight, zorder=3)
    # Both, or the annual minor ticks keep the style's default and print
    # themselves through the tick labels of the row above.
    ax.tick_params(which="both", top=False, right=False)
    ax.grid(axis="x", color=ps.GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(ps.BOUNDARY)


def _row_spans(panels: dict[str, pd.DataFrame]) -> list[float]:
    """How much flux each row covers, as a share of the measurements' own span.

    Taken across both gases so the rows line up, and used as the row heights. With
    one scale through a column, height and flux are the same thing: a row covering
    half the flux is half the height, and the scale bars come out identical without
    being made to.
    """
    shares = []
    for _, part, _, _ in SEASONAL_ROWS:
        shares.append(max(
            float(panel[part].max() - panel[part].min())
            / float(panel["observed"].max() - panel["observed"].min())
            for panel in panels.values()))
    return shares


def _framed_rows(fig, x: float, middles: list[float]) -> None:
    """Each row named in the gutter: what it is, and beneath it how it was built.

    Two lines rather than one, because one line long enough to hold both took a
    quarter of the canvas from the panels. The frame is the one the gas labels
    take, drawn behind both lines once their extents are known.
    """
    from matplotlib.patches import FancyBboxPatch

    for (label, _, ink, _), middle in zip(SEASONAL_ROWS, middles):
        name, _, aside = label.partition(" (")
        # The name in its own row's ink, which ties label to line without six
        # legend boxes repeating six labels. The line beneath stays muted, so the
        # hierarchy inside the frame holds.
        head = fig.text(x, middle, name, ha="right", va="bottom",
                        fontsize=ps.TICK_SIZE, fontweight="bold", color=ink)
        foot = fig.text(x, middle, f"({aside}", ha="right", va="top",
                        fontsize=ps.ANNOTATION_SIZE - 0.5, color=ps.MUTED)
        # Centered on each other rather than hung from one edge. The bold line is
        # the wider on every row, and a second line sharing its right edge read as
        # indented under it.
        fig.canvas.draw()
        widest = max(text.get_window_extent().width for text in (head, foot))
        for text in (head, foot):
            text.set_ha("center")
            text.set_x(x - (widest / 2) / ps.SIZES["triple"][0])
        fig.canvas.draw()
        boxes = [text.get_window_extent().transformed(fig.transFigure.inverted())
                 for text in (head, foot)]
        pad = 7 / ps.SIZES["triple"][0]
        fig.add_artist(FancyBboxPatch(
            (min(box.x0 for box in boxes) - pad, min(box.y0 for box in boxes) - pad),
            max(box.x1 for box in boxes) - min(box.x0 for box in boxes) + 2 * pad,
            max(box.y1 for box in boxes) - min(box.y0 for box in boxes) + 2 * pad,
            boxstyle="round,pad=0.004", facecolor="white", edgecolor=ps.BOUNDARY,
            linewidth=0.9, transform=fig.transFigure, zorder=1))
        for text in (head, foot):
            text.set_zorder(2)


def seasonal_cycle(panels: dict[str, pd.DataFrame]) -> Figure:
    """Each gas split into the shape that repeats and what that shape leaves.

    Three rows against one time axis, so a month sits in the same place in every
    panel and the bottom row can be read as what the two above it do not account
    for. The gases are columns with their own scales: they are in different units,
    and carbon dioxide crosses zero where methane does not.

    Inside a column the three rows share one scale, and their heights are the flux
    each covers. That is what makes the scale bars mean anything: equal height is
    equal flux, and the bars come out identical rather than being made to.
    """
    fig, (left, bottom, width, height) = ps.canvas_area(SEASONAL_TEXT, size="triple")
    width_px, height_px = ps.SIZES["triple"]
    gutter = SEASONAL_GUTTER_PX / width_px
    head = SEASONAL_HEAD_PX / height_px
    row_gap = SEASONAL_ROW_GAP_PX / height_px
    column_gap = SEASONAL_COLUMN_GAP_PX / width_px
    column_width = (width - gutter - column_gap) / 2
    room = height - head - row_gap * (len(SEASONAL_ROWS) - 1)
    spans = _row_spans(panels)
    heights = [room * span / sum(spans) for span in spans]

    first = min(panel.index.min() for panel in panels.values()).to_timestamp()
    last = (max(panel.index.max() for panel in panels.values()) + 1).to_timestamp()
    top = bottom + height - head

    def row_base(index: int) -> float:
        return top - sum(heights[: index + 1]) - index * row_gap

    for column, (key, gas, unit) in enumerate(GAS_PANEL):
        panel = panels[key]
        base_x = left + gutter + column * (column_width + column_gap)
        # One scale for the column: the tightest that fits every row in the height
        # that row was given.
        scale = max(
            (1 + 2 * SEASONAL_MARGIN) * float(panel[part].max() - panel[part].min())
            / (heights[index] * height_px)
            for index, (_, part, _, _) in enumerate(SEASONAL_ROWS))
        axes = []
        for index, (_, part, ink, weight) in enumerate(SEASONAL_ROWS):
            values = panel[part]
            ax = fig.add_axes((base_x, row_base(index), column_width, heights[index]))
            _draw_seasonal_row(ax, values, ink, weight, filled=part == "leftover")
            middle = float(values.max() + values.min()) / 2
            reach = scale * heights[index] * height_px / 2
            ax.set_ylim(middle - reach, middle + reach)
            ax.set_xlim(first, last)
            ps.even_year_ticks(ax, first.year, last.year)
            # Rotated at the left of its own axis, which is where a reader looks
            # for it and the one place rotation is expected. Above the panel it
            # sat under the row before and read as that row's own.
            ax.set_ylabel(unit, fontsize=ps.LABEL_SIZE - 0.5, color=ps.INK)
            if part == "observed":
                ps.panel_name(ax, f"{gas} ({unit})", x=0.5, align="center",
                              y=1.0 + 52 / (heights[index] * height_px))
            axes.append(ax)

        # An axis label rather than figure text. As figure text it sat at a fixed
        # fraction, so a block that moved underneath it left the name inside the
        # panel, and placing it afterwards put it on the description instead,
        # because a figure artist is not in the axes extent the block is balanced
        # against. As a label it is measured with everything else.
        axes[-1].set_xlabel(SEASONAL_TIME_AXIS, fontsize=ps.LABEL_SIZE,
                            fontweight="bold", color=ps.INK,
                            labelpad=SEASONAL_TIME_AXIS_PAD_PT)

    # Each axis name seated a fixed distance from its own widest tick label.
    # Left to matplotlib it sits off the widest label of the axis whatever the
    # leftmost one is, which left gaps of −4 to 8 px across the six panels.
    fig.canvas.draw()
    # Pinned, then corrected against what it measures at: a rotated label's extent
    # is not settled until it has been drawn where it will sit, and `set_position`
    # does not hold on an axis label, which recomputes its own place on every draw.
    for ax in fig.axes:
        panel = ax.get_window_extent()
        nearest = min(label.get_window_extent().x0
                      for label in ax.get_yticklabels() if label.get_text())
        ax.yaxis.set_label_coords((nearest - 30 - panel.x0) / panel.width, 0.5)
    fig.canvas.draw()
    for ax in fig.axes:
        panel = ax.get_window_extent()
        nearest = min(label.get_window_extent().x0
                      for label in ax.get_yticklabels() if label.get_text())
        name = ax.yaxis.get_label()
        drift = nearest - SEASONAL_NAME_GAP_PX - name.get_window_extent().x1
        ax.yaxis.set_label_coords(name.get_position()[0] + drift / panel.width, 0.5)

    # Balanced before the two sets of figure text are placed, not after. Both are
    # at fixed fractions, so a block that moves underneath them leaves the row
    # labels naming the wrong rows and the axis name inside the bottom panel.
    ps.balance_drawing_block(fig, *fig.axes)


    # Seated clear of the widest tick label and the axis name beside it, and
    # centred on where each row actually sits rather than on where it was
    # allocated.
    fig.canvas.draw()
    clear = max(label.get_window_extent().width for label in fig.axes[0].get_yticklabels()
                if label.get_text())
    rows = [fig.axes[index].get_position() for index in range(len(SEASONAL_ROWS))]
    _framed_rows(fig, left + gutter - (clear + 96) / width_px,
                 [box.y0 + box.height / 2 for box in rows])
    return fig


# --------------------------------------------------------------------------
# Prediction error by year
# --------------------------------------------------------------------------

AGREEMENT_TEXT = ps.FigureText(
    title=("Prediction error by year at Marcell Bog Lake Peatland "
           "(2013 to 2019)"),
    #: The grey points had a sentence here naming them. It restated the key's
    #: second entry word for word, and the key is the place a reader looks for
    #: what a mark means.
    subtitle=(
        "Each panel is one evaluated year, and each point is one month placed at "
        "the middle of what the eight fitted methods predicted for it. Prediction "
        "error is how far a prediction fell from what was measured, taken here as "
        "the measurement minus the prediction, so a point above the zero line was "
        "predicted too low. Carbon dioxide runs negative because the peatland "
        "takes up more carbon than it releases, while methane runs positive "
        "because peatlands emit it. Every panel in a row shares its axes."
    ),
    #: Two claims this block used to make were wrong and are gone. It said the
    #: methods missed *in similar directions*, which nothing computed supports:
    #: the share of positive errors runs 25% in 2016 to 67% in 2018, and
    #: `same_way` measures the fitted and seasonal methods agreeing with each
    #: other, not years agreeing with each other. And it said 2015's months were
    #: *all small ones*, which these notes had already recorded as false one
    #: commit before the sentence was written: they sit in the middle third of
    #: the size distribution, and the true statement is the range, 17 to 52.
    description=(
        "Across every evaluated year the methods miss by similar amounts, running "
        "4.1 to 8.3 on methane once 2015 is set aside, though the direction of the "
        "miss varies from year to year. Methane in 2015 is the one exception and "
        "it differs twice over. Its months run 17 to 52 where the evaluated record "
        "runs 10 to 104, so a season with no large months puts its points entirely "
        "in the lower half of the axis, and those months are also missed about 1.7 "
        "times as badly as months of the same size across the record."
    ),
)

#: The one horizon drawn. It is the one most favorable to the fitted methods, so
#: falling short of the seasonal average there says more than doing so a year out,
#: and the forecast comparison already carries the horizon story.
AGREEMENT_HORIZON = 1

AGREEMENT_MEASURED = "Measured"
#: The vertical axis of every panel. Which side of zero a point falls on is the
#: whole reading, and at this panel size the name has to be short enough to sit
#: beside a 260 px panel, so it carries the quantity and the subtitle carries the
#: direction of the subtraction.
AGREEMENT_ERROR = "Error"

#: The key's three entries. Everything drawn is named: a reader meeting green and
#: grey points with nothing to read them by has to go to the subtitle, and a
#: figure that must be read before it can be looked at has failed. The zero line
#: is named too. It is not a mark, but every panel is read against it, and the
#: reference a figure is read against is the last thing that should go
#: unexplained.
AGREEMENT_KEYS = (
    "The months of this panel's year",
    "The months of every other year",
    "Zero error (where a prediction matched the measurement)",
)


def agreement_panel(frames: dict[str, pd.DataFrame],
                    horizon: int = AGREEMENT_HORIZON) -> pd.DataFrame:
    """Each month's measurement, the range the fitted methods gave it, and the
    seasonal average, on the months every method scored.

    The eight fitted methods are collapsed to a range rather than drawn apart: no
    method is identifiable on the panel, because the study's result is that they
    do not separate and a figure naming them would invite the ranking it denies.
    """
    from scipy import stats

    keys = {key for key in evaluation.shared_targets(list(frames.values()))
            if key[0] == horizon}
    fitted = pd.concat([evaluation.restrict(frames[family], keys).assign(family=family)
                        for family in ("autoregressive", "exogenous")])
    benchmarks = evaluation.restrict(frames["benchmarks"], keys)

    # Spread across family *and* method, not method alone. The two families run
    # the same four method names, so pivoting on the name silently averaged each
    # method's two predictions and left a range over four numbers where the
    # figure said eight. It understated the bar by a median factor of 1.57 on
    # methane and 1.22 on carbon dioxide, and halved the bracketing share.
    spread = fitted.pivot_table(index="target", columns=["family", "method"],
                                values="forecast")
    panel = pd.DataFrame({
        "measured": fitted.groupby("target")["actual"].first(),
        "lowest": spread.min(axis=1),
        "highest": spread.max(axis=1),
        "middle": spread.median(axis=1),
        "seasonal": benchmarks[benchmarks["method"] == "climatology"]
        .set_index("target")["forecast"],
    })

    missed = fitted["forecast"] - fitted["actual"]
    fitted_error = panel["middle"] - panel["measured"]
    seasonal_error = panel["seasonal"] - panel["measured"]
    panel.attrs["months"] = len(panel)
    panel.attrs["mean_miss"] = float(missed.abs().mean())
    panel.attrs["root_mean_square"] = float(np.sqrt((missed ** 2).mean()))
    panel.attrs["brackets"] = float(((panel["measured"] >= panel["lowest"])
                                     & (panel["measured"] <= panel["highest"])).mean())
    panel.attrs["same_way"] = float(
        (np.sign(fitted_error) == np.sign(seasonal_error)).mean())

    # How the errors are arranged against the measurement, which is what the
    # residual panel is for. Two things are asked of them and they answer
    # differently: whether they tilt, and whether they widen.
    tilt = stats.linregress(panel["measured"].to_numpy(),
                            -fitted_error.to_numpy())
    panel.attrs["tilt"] = float(tilt.slope)
    panel.attrs["tilt_p_value"] = float(tilt.pvalue)

    # Thirds of the months by how large the month is, so carbon dioxide's uptake
    # sorts by size rather than by sign. Every method's miss is counted, not the
    # middle one's, so these are on the same footing as `mean_miss` above.
    size = panel["measured"].abs()
    edges = np.quantile(size, [0.0, 1 / 3, 2 / 3, 1.0])
    thirds = pd.cut(fitted["actual"].abs(), edges, labels=False, include_lowest=True)
    by_size = missed.abs().groupby(thirds).mean()
    panel.attrs["miss_smallest_third"] = float(by_size.iloc[0])
    panel.attrs["miss_largest_third"] = float(by_size.iloc[-1])
    panel.attrs["relative_miss"] = [
        float(v) for v in (missed.abs() / fitted["actual"].abs()).groupby(thirds).mean()]

    # Each year's miss against what months of its size are missed by across the
    # record. The raw yearly miss cannot separate a year that was predicted badly
    # from one that simply held large months, because the miss grows with the
    # size of the month; dividing by the size-matched expectation does.
    by_size = missed.abs().groupby(thirds).mean()
    expected = thirds.map(by_size).groupby(fitted["target"].dt.year).mean()
    actual = missed.abs().groupby(fitted["target"].dt.year).mean()
    panel.attrs["year_ratio"] = {int(year): float(value)
                                 for year, value in (actual / expected).items()}
    return panel




def agreement_errors(panel: pd.DataFrame) -> pd.DataFrame:
    """The panel as errors: measurement minus prediction, so a positive error
    means the prediction was too low.

    Subtracting this way round rather than the other is the convention the axis
    name and the subtitle both state. It is chosen so that the vertical axis runs
    the same way as the flux does: a point high on the panel is a month the
    methods left short.
    """
    measured = panel["measured"]
    return pd.DataFrame({
        "measured": measured,
        # The bar's ends swap: the highest prediction is the lowest error.
        "lowest": measured - panel["highest"],
        "highest": measured - panel["lowest"],
        "middle": measured - panel["middle"],
        "seasonal": measured - panel["seasonal"],
    }, index=panel.index)


#: Room at the left for the gas name and the axis name beside it, above the top
#: row for the year labels, under each row for its own tick labels and axis name,
#: between the rows, and under both for the key. Each row carries its own
#: horizontal axis because the two gases are in different units and cannot share
#: one; within a row every panel does share it, which is what makes the columns
#: comparable.
YEAR_AXIS_PX = 112
#: The band over each row holding its framed gas name, and the band under that
#: holding one year label per panel. Both rows carry both: a row of panels whose
#: columns are unlabeled cannot be checked against the row above it, and a reader
#: who cannot check will assume the columns do not line up.
YEAR_GAS_PX = 46
YEAR_HEAD_PX = 30
#: Tick labels and the row's axis name under them, with the name set close enough
#: to the labels to read as belonging to them.
YEAR_XAXIS_PX = 74
YEAR_ROW_GAP_PX = 26
YEAR_COLUMN_GAP_PX = 13

#: The key sits in the columns the methane row leaves empty, at the top left,
#: rather than in a band of its own under both rows. Those columns are already
#: blank and a key standing in them costs nothing, where a band under the rows
#: cost 96 px of height that the panels now have instead. How many leading empty
#: columns a row needs before the key will fit in them.
#: How far the boxed gas label stands above its row's panels. It was 56, which
#: the year labels cleared but only just: the frame's lower edge sat on top of
#: them and the two read as one stack rather than as a name over a row of years.
YEAR_GAS_LABEL_PX = 64

YEAR_KEY_COLUMNS = 2

#: The band under both rows the key falls back to when no row leaves that many
#: columns empty. Nothing in the data guarantees one does: methane happens to
#: start two years after carbon dioxide, and a figure whose key exists only
#: because of that would lose it the moment the record changed.
YEAR_KEY_PX = 96

#: Scored months a year needs before it earns a column of its own. 2020 has one
#: on each gas, because the drivers the fitted methods need stop at the end of
#: 2019 and the last month they can reach is January 2020. A column carrying a
#: single point shows nothing about the year and costs its width in every row.
#: A year below this is left out of the figure entirely, background included, so
#: that the span in the title is the span of everything drawn.
YEAR_MIN_MONTHS = 3

#: Reclaimed from the horizontal-axis block `canvas_area` reserves under the
#: drawing area. Each row carries its own axis name inside its own band, so that
#: reserve is unused here, and leaving it there put half again as much space
#: between the last row and the description as sits between the subtitle and the
#: first row. Taking this much levels the two.
YEAR_FOOT_PX = 45

#: The months of every year but the panel's own, repeated behind each panel.
#: Light enough that the panel's own year is what the eye lands on: at a hundred
#: and forty background points against eight to twelve in front, anything heavier
#: competes with the year it exists to give context for.
#: Labeled ticks across a panel. Two of them, which is what a three-bin locator
#: left on both rows, gives a reader nothing to place a point against but the
#: panel edges. The steps keep the values round: left to itself the locator
#: offered carbon dioxide -2.4, -1.6 and -0.8.
YEAR_X_TICKS = 7
YEAR_X_STEPS = (1, 2, 5, 10)

YEAR_CONTEXT = "#DEDEDE"
YEAR_CONTEXT_SIZE = 2.6
YEAR_FOREGROUND_SIZE = 5.0


def _draw_year_panel(ax, errors: pd.DataFrame, year: int,
                     limits: tuple[tuple[float, float], tuple[float, float]]) -> None:
    """One year of one gas, against every other year of it.

    The panel's own year is drawn last and largest. Everything else is drawn
    first in grey, at every panel, so the comparison a reader needs is inside the
    panel they are looking at rather than spread across the row.
    """
    (low, high), reach = limits
    chosen = errors.index.year == year

    ax.axhline(0.0, color=ps.BOUNDARY, linewidth=0.9, linestyle=(0, (5, 3)),
               zorder=2)
    ax.plot(errors.loc[~chosen, "measured"], errors.loc[~chosen, "middle"],
            linestyle="none", marker="o", markersize=YEAR_CONTEXT_SIZE,
            markerfacecolor=YEAR_CONTEXT, markeredgecolor="none", zorder=1)
    ax.plot(errors.loc[chosen, "measured"], errors.loc[chosen, "middle"],
            linestyle="none", marker="o", markersize=YEAR_FOREGROUND_SIZE,
            markerfacecolor=ps.FITTED, markeredgecolor="none", zorder=3)

    ax.set_xlim(low, high)
    ax.set_ylim(-reach, reach)
    ax.xaxis.set_major_locator(MaxNLocator(YEAR_X_TICKS, steps=list(YEAR_X_STEPS)))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.tick_params(which="both", top=False, right=False, labelsize=ps.TICK_SIZE - 2.0,
                   length=3, pad=2)
    ax.grid(color=ps.GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(ps.BOUNDARY)


#: The key's own size, set here rather than taken off `LEGEND_SIZE` because this
#: key is the one in the set that stands inside the drawing block rather than
#: beside it. It was two points under the set size, which is smaller than
#: anything else a reader has to read on the canvas, and the columns it stands in
#: are empty: there was nothing the extra height could collide with.
YEAR_KEY_SIZE = 8.2

#: The two axis names on each row. They were 9.0, the same as the bold year label
#: over every panel, and two bold labels at one size in one figure compete: a
#: reader has nothing but position to tell a panel's name from the row's quantity.
#: 10.5 puts a step between them without reaching the boxed gas names at 11.1,
#: which stay the largest thing in the block because they name the row. The
#: ladder is 7.5 ticks, 9.0 year labels, 10.5 axis names, 11.1 gas names.
YEAR_AXIS_TITLE_SIZE = 10.5


def _year_key(fig, rect: tuple[float, float, float, float],
              left_x: float | None = None):
    """One key for every panel, standing in the columns the methane row leaves
    empty at its left.

    Those columns are blank because methane has no forecasts before 2015, so a
    key in them costs nothing, where the band it used to occupy under both rows
    cost height the panels now have. It also puts the key where a reader meets it
    first, above the panels rather than past them.

    One column under one centered ruled heading. It was split across two columns
    for a build, between what is drawn from the data and what it is drawn
    against, which put the zero line on its own away from the two kinds of point.
    That division is one a reader cannot see on the panel and does not need: all
    three are simply what is drawn, and one list of three is shorter to read than
    two lists with a rule to work out between them.
    """
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    dot = dict(linestyle="none", marker="o", markeredgecolor="none")
    entries = [
        (Line2D([], [], linestyle="none", marker="none"),
         r"$\bf{What\ each\ mark\ shows}$"),
        (Line2D([], [], markerfacecolor=ps.FITTED, markersize=7, **dot),
         AGREEMENT_KEYS[0]),
        (Line2D([], [], markerfacecolor=YEAR_CONTEXT, markersize=6, **dot),
         AGREEMENT_KEYS[1]),
        (Line2D([], [], color=ps.BOUNDARY, linewidth=1.0, linestyle=(0, (5, 3))),
         AGREEMENT_KEYS[2]),
    ]
    # Held below the middle of its region. The row's rotated axis name is
    # centered on the row, so a key centered there too sits at the same height
    # and the two read as one band however far apart they are; dropping the key
    # below that line is what separates them.
    #
    # Horizontally its left edge is set on the left edge of the carbon dioxide
    # row's axis name, passed in as `left_x`. Those two are the only things
    # standing in this gutter and a reader reads down it, so one shared left
    # margin is what makes them a column rather than two loose objects. Centering
    # them on each other instead is not available: the key is 577 px wide against
    # a 25 px axis name, and a shared center line would carry its left edge off
    # the canvas. The edge is measured off the drawn name rather than written
    # down as an offset, so it survives a change to the grid or to the key's own
    # width, both of which have moved during this figure's life.
    anchor = (0.54, "center") if left_x is None else (
        (left_x - rect[0]) / rect[2], "center left")
    ps.legend(ax, handles=[handle for handle, _ in entries],
              labels=[label for _, label in entries], loc=anchor[1],
              bbox_to_anchor=(anchor[0], 0.34), ncol=1, framealpha=1.0,
              borderpad=1.0, labelspacing=1.0, handlelength=1.9,
              handletextpad=0.7, fontsize=YEAR_KEY_SIZE,
              # Otherwise matplotlib insets the box from the anchor by half a
              # font size, which is 8.6 px here and is exactly the kind of
              # almost-aligned that reads as a mistake rather than a margin.
              borderaxespad=0.0)
    ps.underline_legend_headings(fig, ax, center=True)
    return ax


def prediction_error_by_year(panels: dict[str, pd.DataFrame]) -> Figure:
    """One small panel per evaluated year, each year against the whole record.

    Faceted rather than colored. Six years told apart by hue would overlap into
    one cloud, which is what the pooled builds of this figure showed: the first
    marked a single year and could not say the rest of it was scattered
    elsewhere, and the second showed spread without direction. A panel per year
    separates them, and drawing every other year behind each one in grey means a
    reader sees where a year sits without a callout naming it.

    A point per month rather than a segment per month. At this panel size the
    background context is a hundred and forty months in every panel, and drawn
    as segments it fills the panel and buries the year in it. What the segments
    carried is a pooled statement about method agreement, which the description
    now makes in numbers.
    """
    fig, (left, bottom, width, height) = ps.canvas_area(AGREEMENT_TEXT,
                                                        size="year grid")
    width_px, height_px = ps.SIZES["year grid"]
    # The reserve under the drawing area is not used here, so the rows take it.
    bottom -= YEAR_FOOT_PX / height_px
    height += YEAR_FOOT_PX / height_px

    errors = {key: agreement_errors(panels[key]) for key, _, _ in GAS_PANEL}
    # Only years with enough months to say anything are drawn at all. A year
    # below the threshold is dropped from the background as well as from the
    # foreground, so the span the title gives is the span of what is drawn.
    months = {key: frame.index.year.value_counts() for key, frame in errors.items()}
    years = sorted({int(year) for frame in errors.values()
                    for year in frame.index.year
                    if max(count.get(year, 0) for count in months.values())
                    >= YEAR_MIN_MONTHS})
    errors = {key: frame[frame.index.year.isin(years)]
              for key, frame in errors.items()}
    months = {key: frame.index.year.value_counts() for key, frame in errors.items()}

    axis_room = YEAR_AXIS_PX / width_px
    gap = YEAR_COLUMN_GAP_PX / width_px
    across = (width - axis_room - (len(years) - 1) * gap) / len(years)
    gas_band = YEAR_GAS_PX / height_px
    head = YEAR_HEAD_PX / height_px
    x_room = YEAR_XAXIS_PX / height_px
    row_gap = YEAR_ROW_GAP_PX / height_px
    # Each row is a framed gas name, a band of year labels, the panels, and the
    # row's own horizontal axis. The key takes what is left at the foot, so the
    # last row's axis name can never reach it.
    # The columns each gas occupies, worked out before the layout because where
    # the key goes decides how much height the rows have. Methane starts at 2015,
    # so its names hang off its own first panel rather than off the grid's left
    # edge, which is two empty columns away from anything it names.
    occupied = {}
    for key, _, _ in GAS_PANEL:
        occupied[key] = [column for column, year in enumerate(years)
                         if months[key].get(year, 0) >= YEAR_MIN_MONTHS]
    in_gap = next((key for key, filled in occupied.items()
                   if filled[0] >= YEAR_KEY_COLUMNS), None)

    banding = len(GAS_PANEL) * (gas_band + head + x_room)
    foot = 0.0 if in_gap else YEAR_KEY_PX / height_px
    down = (height - foot - banding
            - (len(GAS_PANEL) - 1) * row_gap) / len(GAS_PANEL)

    rows = []
    for row, (key, gas, unit) in enumerate(GAS_PANEL):
        frame = errors[key]
        # One scale for the row, so a year that sits low is low against every
        # other year rather than against its own panel.
        span = frame["measured"].max() - frame["measured"].min()
        low = frame["measured"].min() - 0.08 * span
        high = frame["measured"].max() + 0.08 * span
        # Carried to zero when the flux does not cross it, which methane's never
        # does. It gives the row an anchor a reader can count from, and it is
        # what puts a labeled tick at 0 rather than at whatever the locator
        # picked inside the data.
        limits = ((min(low, 0.0), max(high, 0.0)),
                  1.08 * frame["middle"].abs().max())
        row_top = bottom + height - row * (gas_band + head + down + x_room + row_gap)
        top = row_top - gas_band - head
        # Nothing at all is drawn in the columns this gas does not occupy: a panel
        # with axes and grey context but no year in it reads as a year that was
        # forecast and missed everywhere, and a note standing where the other
        # columns carry year labels reads as a third kind of mark. That methane
        # starts late is a fact about the record and it is in the description.
        filled = occupied[key]

        drawn = []
        for column in filled:
            at = left + axis_room + column * (across + gap)
            ax = fig.add_axes((at, top - down, across, down))
            _draw_year_panel(ax, frame, years[column], limits)
            if column != filled[0]:
                ax.set_yticklabels([])
            # Every panel in both rows, so the columns can be checked against
            # each other. They do line up by year; unlabeled, a reader has no way
            # of knowing that and will assume they do not.
            ax.set_title(str(years[column]), fontsize=ps.LABEL_SIZE - 0.5,
                         fontweight="bold", color=ps.INK, pad=5)
            drawn.append(ax)
        rows.append((key, gas, unit, drawn))

    # Everything but the panels is placed against them rather than against the
    # grid, and placed again whenever they move. `balance_drawing_block` resizes
    # axes and nothing else, so a figure-level text put at a computed height
    # stays where it was while the panel it names slides out from under it. That
    # is the fault the seasonal figure hit; here there are six such texts and a
    # key, so they are built by one function the balancer can call.
    furniture: list = []
    # What the balancer measures as the block's edges besides the panels. The gas
    # labels stand above the top row, and where the key falls back to a band it
    # stands below the bottom one; either would be walked into a text block by a
    # balance that measured the panels alone.
    measured: list = []
    #: The row axis names, which are the lowest ink on the canvas and are what
    #: the description is set against. They are figure text, so they were outside
    #: the balance entirely: it equalised to the carbon dioxide tick labels and
    #: left the axis name hanging 34 px below them, 1.5 px clear of the
    #: description. The gap it reported as 35.6 px was 1.5 px of real air.
    bottoms: list = []

    def place() -> None:
        while furniture:
            furniture.pop().remove()
        measured.clear()
        bottoms.clear()
        names: dict[str, object] = {}
        boxes = {key: [ax.get_position() for ax in drawn]
                 for key, _, _, drawn in rows}
        edges = {key: (min(b.x0 for b in box), max(b.x1 for b in box),
                       max(b.y1 for b in box), min(b.y0 for b in box))
                 for key, box in boxes.items()}
        for key, gas, unit, _ in rows:
            first, last, ceiling, floor = edges[key]
            # Framed and centered over the row, the treatment the gas labels take
            # across this set. Held clear above the year labels standing under it.
            label = fig.text((first + last) / 2,
                             ceiling + YEAR_GAS_LABEL_PX / height_px, gas,
                             ha="center", va="center",
                             fontsize=ps.LEGEND_SIZE + 1.6, fontweight="bold",
                             color=ps.INK, zorder=9,
                             bbox=dict(boxstyle="round,pad=0.42",
                                       facecolor="white", edgecolor=ps.BOUNDARY,
                                       linewidth=0.9))
            furniture.append(label)
            measured.append(label)
            # One axis name for the row, centered under the panels it belongs to,
            # since every panel in the row shares the scale and one copy per panel
            # would say so eight times. Close under the tick labels, so it reads
            # as belonging to them rather than floating between the rows.
            across_name = fig.text(
                (first + last) / 2, floor - 34 / height_px,
                f"{AGREEMENT_MEASURED} ({unit})", ha="center", va="top",
                fontsize=YEAR_AXIS_TITLE_SIZE, fontweight="bold", color=ps.INK)
            furniture.append(across_name)
            bottoms.append(across_name)
            measured.append(across_name)
            # Clear of the tick labels beside it: one rotated line is about 30 px
            # wide and a signed two-decimal tick label about 34 px, so anything
            # closer than this puts the minus sign under the axis name.
            names[key] = fig.text(
                first - 68 / width_px, (ceiling + floor) / 2,
                f"{AGREEMENT_ERROR} ({unit})", ha="center", va="center",
                rotation=90, fontsize=YEAR_AXIS_TITLE_SIZE, fontweight="bold",
                color=ps.INK)
            furniture.append(names[key])

        # The key stands in the columns one row leaves empty at its left, and
        # takes its left margin from the description, which begins at the canvas
        # margin below it. It was set on the carbon dioxide axis name instead,
        # 31.2 px further right: that lined it up with the nearest thing rather
        # than with the page, and it spent the difference on clearance to the
        # methane row's own axis name, which was the tightest gap on the figure.
        # The description's edge is the one a reader already reads down.
        if in_gap:
            first, _, ceiling, floor = edges[in_gap]
            fig.canvas.draw()
            target = (fig.texts[2].get_window_extent(fig.canvas.get_renderer()).x0
                      / width_px)
            standing = list(fig.artists)
            axis = _year_key(fig, (left, floor, first - 84 / width_px - left,
                                   ceiling - floor), left_x=target)
            furniture.append(axis)
            # The heading rule is added to the figure rather than to the key's
            # own axes, so removing the axes alone would leave it behind and the
            # next call would draw a second one under it.
            furniture.extend(a for a in fig.artists if a not in standing)
        else:
            # Hung off the lowest row rather than set at the foot of the canvas.
            # At the foot it does not move when the block grows, and the block
            # grows downward by however much slack the description leaves, so the
            # panels walk straight through it. Anchored here it descends with
            # them, and it is measured as the block's floor so the gap below is
            # the gap under the key rather than under the last row.
            base = min(floor for _, _, _, floor in edges.values())
            axis = _year_key(fig, (left,
                                   base - (YEAR_XAXIS_PX + YEAR_KEY_PX) / height_px,
                                   width, YEAR_KEY_PX / height_px))
            furniture.append(axis)
            measured.append(axis)

    place()
    # Ink to ink at both ends, which is the balancer's default and is what the
    # two gaps have to be to look even. Both ends of this block are furniture
    # rather than panel: a boxed gas name stands above the top row and the row's
    # axis name hangs below the bottom one, each in the margin at its own end.
    # Balancing to the panel border instead was tried and measures symmetric
    # while reading bottom-heavy, because the top gap then carries the gas label
    # inside it, 75.5 px of 111.1, and the bottom gap carries nothing. Treating
    # the two objects alike is what makes the white space alike.
    ps.balance_drawing_block(fig, *[ax for _, _, _, drawn in rows for ax in drawn],
                             extra=measured, reflow=place)
    return fig


# --------------------------------------------------------------------------
# Whether the model's errors follow the distribution the estimator assumes
# --------------------------------------------------------------------------

DISTRIBUTION_TEXT = ps.FigureText(
    #: One line at this canvas width. "the model's errors" wrapped it, leaving
    #: "2019)" alone on a second line, which is the fault this figure spent a
    #: pass fixing elsewhere. The year range keeps the set's "2009 to 2019" form
    #: rather than taking a dash, since every other title in the set reads that
    #: way and the two words saved by dropping the possessive were enough.
    title=("Diagnostic check on model errors at Marcell Bog Lake Peatland "
           "(2009 to 2019)"),
    #: "On a log scale" is gone: all four axes are linear and what is logged is
    #: the quantity, which the axis names already carry as "(log flux)". And a
    #: point on the line is one order statistic sitting where the fitted
    #: distribution puts it, not "an error matching the distribution" — a
    #: distribution is matched by the whole sample, not by a point.
    #: Four sentences, not three: the band sentence carried three ideas at once and
    #: "covers all 115 at once" was the heaviest with the least explanation, since
    #: a reader does not know what the alternative would be. Split, "together" does
    #: that work and the consequence follows the mechanism instead of sitting
    #: beside it.
    subtitle=(
        "This is a quantile-quantile plot, which compares the errors the model "
        "made against the errors a named distribution predicts. Points sitting on "
        "the 1:1 line are quantiles the distribution places exactly right. The "
        "band is drawn so that all 115 points should fall inside it together, "
        "which means a single point outside is enough to say the distribution "
        "does not hold. The weighted fit counts a month resting on many "
        "measurements more heavily than one resting on few, and the study runs "
        "both throughout."
    ),
    #: The block said the errors were *equally consistent with Laplace and with
    #: Gaussian*, which the figure contradicts by the criterion the subtitle sets:
    #: of the four panels exactly one has every point inside its band, and it is
    #: Laplace unweighted. It also left both weighted panels uncaptioned, so half
    #: the figure showed decisive rejection with no account of it anywhere.
    #:
    #: The weighted row is an artifact, but not for the reason a first draft gave.
    #: A 554-fold weight span does not imply unequal spread: if the weights were
    #: right, scale proportional to 1/w, multiplying by w would make the scaled
    #: residuals homoscedastic, which is what inverse-variance weighting is for.
    #: The spread is unequal because the weights are *wrong*, which is a finding of
    #: the simulation in these notes and not something the span implies.
    description=(
        "Of the four panels, only Laplace on the unweighted residuals has every "
        "point inside its band. The two weighted panels fail for a reason of their "
        "own, since the weights do not track how the errors actually vary, so that "
        "row tests the weighting rather than the distribution. Nothing here changes "
        "what the study concludes: its intervals are built from the residuals "
        "themselves and assume no distribution at all."
    ),
)

#: What the four panels hold. Each names its distribution and its weighting, so
#: a panel lifted out of the figure still says what it is.
DISTRIBUTION_PANELS = (
    ("weighted", "Laplace (weighted)"),
    ("weighted", "Gaussian (weighted)"),
    ("unweighted", "Laplace (unweighted)"),
    ("unweighted", "Gaussian (unweighted)"),
)

#: The names a quantile plot's axes carry by convention. The subtitle says what
#: they are in full, so the axes themselves stay short enough to sit beside a
#: panel without crowding it.
DISTRIBUTION_EXPECTED = "Theoretical quantiles"
DISTRIBUTION_OBSERVED = "Sample quantiles"
DISTRIBUTION_UNIT = "log flux"

#: The band is the region every point has to stay inside, so it is drawn as
#: ground rather than as a pair of lines: two edges read as two series.
DISTRIBUTION_BAND_FILL = "#ECECEC"
DISTRIBUTION_BAND_EDGE = "#A6A6A6"

#: Parentheses rather than a colon on the third, and the coverage clause dropped
#: because the subtitle carries it. What the parenthetical keeps is the property
#: that separates a simultaneous band from a pointwise one, which is what this
#: method's own literature stresses: the band holds for all 115 at once, not for
#: each point on its own. Plain language on the canvas; "simultaneous testing
#: band" is the term, and it is in the notes rather than here.
DISTRIBUTION_KEYS = (
    "One month's error",
    "The 1:1 line",
    "95% band (covering all 115 points at once)",
)

DISTRIBUTION_AXIS_PX = 118
DISTRIBUTION_HEAD_PX = 46
DISTRIBUTION_XAXIS_PX = 76
DISTRIBUTION_COLUMN_GAP_PX = 76
DISTRIBUTION_ROW_GAP_PX = 34
DISTRIBUTION_KEY_PX = 92


def _draw_distribution_panel(ax, frame: pd.DataFrame, unit: str) -> None:
    """One comparison: the model's sorted errors against one distribution's."""
    # Set by the points and the line they are read against, not by the band. The
    # band's outermost step runs to the value a level of 0.002 puts on the first
    # of 115 ranks, which is far outside anything observed and would squash the
    # cloud into the middle of the panel. It is clipped instead.
    low = min(frame["expected"].min(), frame["observed"].min())
    high = max(frame["expected"].max(), frame["observed"].max())
    room = 0.08 * (high - low)
    limits = (low - room, high + room)

    ax.fill_between(frame["expected"], frame["lowest"], frame["highest"],
                    facecolor=DISTRIBUTION_BAND_FILL, linewidth=0.0, zorder=1)
    for edge in ("lowest", "highest"):
        ax.plot(frame["expected"], frame[edge], color=DISTRIBUTION_BAND_EDGE,
                linewidth=1.0, zorder=1)
    # Equality, not a fitted line: both distributions are fitted to these errors
    # by maximum likelihood, so agreement is the line rather than a slope.
    ax.plot(limits, limits, color=ps.BOUNDARY, linewidth=1.0,
            linestyle=(0, (5, 3)), zorder=2)
    ax.plot(frame["expected"], frame["observed"], linestyle="none", marker="o",
            markersize=4.2, markerfacecolor=ps.FITTED, markeredgecolor="none",
            zorder=3)

    ax.set_xlim(*limits)
    ax.set_ylim(*limits)
    ax.set_xlabel(f"{DISTRIBUTION_EXPECTED} ({unit})",
                  fontsize=ps.LABEL_SIZE - 1.0, color=ps.INK)
    ax.set_ylabel(f"{DISTRIBUTION_OBSERVED} ({unit})",
                  fontsize=ps.LABEL_SIZE - 1.0, color=ps.INK)
    ax.xaxis.set_major_locator(MaxNLocator(5, steps=[1, 2, 5, 10]))
    ax.yaxis.set_major_locator(MaxNLocator(5, steps=[1, 2, 5, 10]))
    ax.tick_params(which="both", top=False, right=False,
                   labelsize=ps.TICK_SIZE - 1.5)
    ax.grid(color=ps.GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(ps.BOUNDARY)


def _distribution_key(fig, left: float, bottom: float, width: float) -> None:
    """One key for all four panels, under them and clear of every mark."""
    ax = fig.add_axes((left, bottom, width,
                       DISTRIBUTION_KEY_PX / ps.SIZES["quad"][1]))
    ax.set_axis_off()
    entries = [
        (Line2D([], [], linestyle="none", marker="none"),
         r"$\bf{What\ each\ mark\ shows}$"),
        (Line2D([], [], linestyle="none", marker="o", markersize=6,
                markerfacecolor=ps.FITTED, markeredgecolor="none"),
         DISTRIBUTION_KEYS[0]),
        (Line2D([], [], color=ps.BOUNDARY, linewidth=1.0, linestyle=(0, (5, 3))),
         DISTRIBUTION_KEYS[1]),
        (Patch(facecolor=DISTRIBUTION_BAND_FILL, edgecolor=DISTRIBUTION_BAND_EDGE,
               linewidth=1.0), DISTRIBUTION_KEYS[2]),
    ]
    # Held below the middle of its band. The key is taller than the band it sits
    # in, so centering it puts its top edge against the axis names of the row
    # above; the room it needs is all below, where the description is not for
    # another sixty pixels.
    ps.legend(ax, handles=[handle for handle, _ in entries],
              labels=[label for _, label in entries], loc="center",
              bbox_to_anchor=(0.5, 0.30), ncol=1, framealpha=1.0, borderpad=0.7,
              labelspacing=0.5, handlelength=2.0, handletextpad=0.8,
              fontsize=ps.LEGEND_SIZE - 1.5)
    # Ruled by the caller, after the balance. The rule is a figure artist at fixed
    # coordinates and the balance moves the axes this legend rides on; ruling here
    # would leave the line where the heading used to be. This figure escaped that
    # only because it did not balance.
    return ax


def residual_distribution_check(
        panels: dict[tuple[str, str], pd.DataFrame]) -> Figure:
    """The reconstruction model's errors against the two distributions in play.

    Methane only, and the reconstruction fit only. That fit minimizes absolute
    deviations, which is maximum likelihood under Laplace error, so it is the one
    the assumption belongs to. The forecast methods minimize squared error or
    have no likelihood at all, and carbon dioxide has no fit of this kind: it
    crosses zero, so the log target the model needs does not exist for it.
    """
    # Measured text blocks: the title wraps to two lines here, and the allotted
    # spacing gives a two-line title twice the air a one-line title gets.
    fig, (left, bottom, width, height) = ps.canvas_area(
        DISTRIBUTION_TEXT, size="quad")
    width_px, height_px = ps.SIZES["quad"]

    axis_room = DISTRIBUTION_AXIS_PX / width_px
    gap = DISTRIBUTION_COLUMN_GAP_PX / width_px
    head = DISTRIBUTION_HEAD_PX / height_px
    x_room = DISTRIBUTION_XAXIS_PX / height_px
    row_gap = DISTRIBUTION_ROW_GAP_PX / height_px

    # Square in pixels rather than in figure fractions, and set by whichever of
    # the two directions runs out first. The reference is a line of equality, so
    # a panel that is not square puts it at some other angle and distance from it
    # stops being readable.
    side_px = min(((width - axis_room - gap) / 2) * width_px,
                  (height * height_px - DISTRIBUTION_KEY_PX
                   - 2 * (DISTRIBUTION_HEAD_PX + DISTRIBUTION_XAXIS_PX)
                   - DISTRIBUTION_ROW_GAP_PX) / 2)
    across, down = side_px / width_px, side_px / height_px
    drawn = []
    for index, (weighting, name) in enumerate(DISTRIBUTION_PANELS):
        row, column = divmod(index, 2)
        family = name.split(" ")[0]
        at = left + axis_room + column * (across + gap)
        top = bottom + height - row * (head + down + x_room + row_gap) - head
        ax = fig.add_axes((at, top - down, across, down))
        _draw_distribution_panel(ax, panels[(weighting, family)],
                                 DISTRIBUTION_UNIT)
        # Clear of the panel top by more than the frame's own line weight: the
        # label is drawn from its top edge, so a smaller offset leaves the box
        # sitting on the frame it names.
        ps.panel_name(ax, name, x=0.5, align="center",
                      y=1.0 + 44 / (down * height_px))
        drawn.append(ax)

    # Slid so the whole block sits centered, the block being the panels together
    # with the axis names and tick labels standing left of them. The canvas keeps
    # a wider margin at the left than at the right, which this figure does not
    # need: its own gutter already holds what that margin is there for.
    shift = _centering_shift(fig, drawn, width_px)
    for ax in drawn:
        box = ax.get_position()
        ax.set_position((box.x0 + shift, box.y0, box.width, box.height))
    # Centered on the canvas, as the block above it now is.
    key = _distribution_key(fig, 0.5 - width / 2, bottom, width)

    def seat_key() -> None:
        """Centre the key in the band between the panels and the description.

        Measured from the key's *drawn* extent, not from the axes it sits in: the
        legend is 120 px tall in a 92 px band and deliberately overflows downward,
        so the axes rect is 32.6 px short of where the ink actually ends.
        """
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        floor = min(ax.get_tightbbox(renderer).y0 for ax in drawn)
        described = fig.texts[2].get_window_extent(renderer).y1
        box = key.get_legend().get_window_extent(renderer)
        shift = ((floor + described) / 2.0 - (box.y0 + box.y1) / 2.0) / height_px
        seat = key.get_position()
        key.set_position((seat.x0, seat.y0 + shift, seat.width, seat.height))

    # Translated, not stretched. The panels are square in pixels because the
    # reference they carry is a line of equality, so the block may move into the
    # gap below it but may not grow into it.
    #
    # The key is measured as the block's floor but moved by `seat_key` rather than
    # by the balancer, and the two settle together: centring the key makes the gap
    # above it equal the gap below it, and the balance makes both equal the gap
    # under the subtitle. Three gaps, one number. The legend itself goes in
    # `extra`, not its axes, for the same reason `seat_key` measures it.
    ps.balance_drawing_block(fig, *drawn, extra=[key.get_legend()],
                             reflow=seat_key, grow=False)
    # Ruled last, after the final seating. The rule is a figure artist at fixed
    # coordinates: anything that moves the key after this leaves the line behind.
    ps.underline_legend_headings(fig, key, center=True)
    return fig


def _centering_shift(fig, drawn: list, width_px: int) -> float:
    """How far to slide the panels so the whole block sits centered.

    Measured after drawing rather than taken from the room set aside: what a
    y-axis name and its tick labels occupy is not what was allotted to them.
    """
    fig.canvas.draw()
    left_edge = min(ax.yaxis.get_label().get_window_extent().x0 for ax in drawn)
    right_edge = max(ax.get_window_extent().x1 for ax in drawn)
    return ((width_px - (right_edge - left_edge)) / 2 - left_edge) / width_px
