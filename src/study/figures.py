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
from matplotlib.patches import Patch
from matplotlib.patches import Rectangle
from matplotlib.ticker import NullFormatter, ScalarFormatter
from matplotlib.transforms import blended_transform_factory

from forecast import evaluation, experiment, features, screening
from study import plotstyle as ps
from study import windows

#: Re-exported so a figure and the tables it sits beside cannot disagree about
#: which months the study fitted on. Defined in `study.windows`, which is what
#: every script builds its windows from.
WATER_TABLE_ARTIFACTS = windows.WATER_TABLE_ARTIFACTS

WATER_TABLE_TEXT = ps.FigureText(
    title="Monthly water table elevation at Marcell Bog Lake Peatland, Minnesota (1990 to 2019)",
    subtitle=(
        "The water table runs 0.29 m past the fitted maximum, against a fitted range "
        "only 0.33 m wide"
    ),
    description=(
        "Reconstruction means estimating methane emissions for years before "
        "measurements began in 2009, from relationships fitted on 2009 to 2019. "
        "Each point is one month's mean. The shaded band marks the 115 months the "
        "fit used. The water table fell through the 2000s, so the fit window opens "
        "after the wetter state has gone, sampling only the drier conditions. The "
        "dashed lines mark the highest and lowest water table they reached. Points "
        "beyond them lie outside anything the model has seen: 107 above in runs "
        "lasting years, six below by under 0.06 m. Those lines sit 0.33 m apart, "
        "and the reconstruction runs 0.29 m above the upper one: the excursion is "
        "nearly as wide as the whole fitted span. It stops at 2019 because "
        "precipitation, a covariate it needs, ends there."
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
               label=(f"Outside the fitted range "
                      f"({int(above.sum())} months above, {int(below.sum())} below)")),
        Line2D([], [], color=ps.BOUNDARY, linewidth=1.3, linestyle=(0, (7, 4)),
               label=f"Fitted range, {low:.2f} to {high:.2f} m"),
    ]
    ps.legend(ax, handles=handles, labels=[h.get_label() for h in handles],
              loc="lower left", ncols=1, fontsize=8.6, borderpad=0.42,
              labelspacing=0.32, handlelength=1.9, handletextpad=0.6)

    if above.any():
        peak = int(np.nanargmax(np.where(above, values, np.nan)))
        run = _run_length(above, peak)
        ps.annotate(
            ax,
            f"Peak of {run} consecutive months\nabove the fitted maximum",
            xy=(times[peak], values[peak]),
            xytext=(times[peak] - pd.Timedelta(days=260), values[peak]),
            ha="right", va="center",
        )
    return fig


def _run_length(flags: np.ndarray, index: int) -> int:
    """Length of the unbroken stretch of True values containing one position."""
    start = index
    while start > 0 and flags[start - 1]:
        start -= 1
    end = index
    while end + 1 < len(flags) and flags[end + 1]:
        end += 1
    return end - start + 1

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
        "The water table coefficient drifts as its range narrows: flat, linear, or "
        "absent (the three give 10 to 30 g C per square meter)"
    ),
    description=(
        "Each marker is one year's emission in grams of carbon per square meter, "
        "from relationships fitted on the measured years (2009 to 2019). Where the "
        "water table stays inside the range those years covered, the three "
        "assumptions agree closely; where it moves beyond, they fan apart, and the "
        "strip below shows how much of each year fell outside. Very little of this "
        "can be verified, because measurement stopped in 1992 and did not resume "
        "until 2007, leaving eighteen of these twenty years with nothing to compare "
        "against. The exceptions are 1991 and 1992, measured by Shurpali and "
        "colleagues, for which this reconstruction predicts 9.29 and 8.49 grams of "
        "carbon from May to October; their published totals have not been obtained."
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
    from matplotlib.ticker import FixedLocator, MultipleLocator

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
    ticks = [y for y in range(int(years.min()), int(years.max()) + 1, 5)]
    if years.max() not in ticks:
        ticks.append(int(years.max()))
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    ax.tick_params(labelbottom=False)
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

    # The strip carries two marks a reader cannot otherwise name: the hatching,
    # and a flat mark that means a measured zero rather than a missing year.
    strip_key = [
        Patch(facecolor=ps.OUTSIDE, edgecolor="white", hatch=ps.OUTSIDE_HATCH,
              label="Share of the year outside"),
        Line2D([], [], linestyle="none", marker="_", markersize=5.2,
               markeredgewidth=1.8, color=ps.INSIDE,
               label="No months outside"),
    ]
    # Inside the frame, in the block the last six years leave clear. The strip is
    # a secondary element and should not gain height to carry its own key, so the
    # key is made small enough to fit what the bars already leave.
    ps.legend(strip, handles=strip_key, labels=[h.get_label() for h in strip_key],
              loc="upper right", ncols=1, fontsize=6.4, borderpad=0.3,
              labelspacing=0.2, handlelength=1.3, handletextpad=0.4,
              framealpha=1.0, bbox_to_anchor=(0.995, 0.97))
    strip.set_ylim(0, 108)
    strip.set_yticks([0, 50, 100])
    strip.set_ylabel(ps.axis_label("Months outside", "%"))
    strip.set_xlabel(ps.axis_label("Year"))
    strip.set_xlim(years.min() - 0.8, years.max() + 0.8)
    strip.xaxis.set_minor_locator(MultipleLocator(1))
    ps.mirror_ticks(strip)

    _underline_legend_headings(fig, ax)

    return fig


# --------------------------------------------------------------------------
# The forecast comparison
# --------------------------------------------------------------------------

#: Benchmarks drawn, in the order they are read. Achromatic and separated by line
#: style, as every non-hue category in this figure set is. Weight follows how much
#: each one carries: climatology is the result, so it is heaviest.
BENCHMARK_STYLE = {
    "climatology": {"color": "#1A1A1A", "linestyle": "-", "linewidth": 2.4},
    "seasonal naive": {"color": "#767676", "linestyle": (0, (1.4, 2.2)), "linewidth": 1.9},
}

#: Benchmarks the panel table carries. Drawing is a separate question: the table
#: keeps every benchmark the study scored, so the subtitle can quote one the
#: panel does not draw and a test can check that it quotes it correctly.
PANEL_BENCHMARKS = ("climatology", "seasonal naive", "naive")

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
        "environmental covariates, are compared against four simple benchmarks. "
        "Each is evaluated at forecast horizons of one to twelve months, meaning "
        "how far ahead the prediction is made. The most accurate at every horizon "
        "on both gases is the simplest: predicting each month as the average of "
        "that month in previous years. The pale band marks how far below that "
        "average a method would have to fall before the difference could be told "
        "apart from noise."
    ),
    description=(
        "Methane is measured in nanomoles and carbon dioxide in micromoles, so "
        "the two panels cannot be compared by eye. The green region spans all "
        "eight fitted models. Its lower edge dips below the seasonal average at "
        "one month on both gases, and at six months on methane, though never by "
        "more than the band. Its upper edge rises above the band at three, six "
        "and twelve months: some fitted models are distinguishably worse than "
        "the average. The band is wide where the closest fitted model disagrees "
        "with the average erratically from month to month, not where the average "
        "is least certain."
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

    # The result in the other direction, on both panels because it holds on both.
    # Anchored at twelve months, where the envelope's upper edge is highest, and
    # set into the corner beyond the legend's right edge. Wrapped narrow so it
    # fits the strip the legend leaves rather than reaching back across it.
    for ax, (key, _, _) in zip(axes, GAS_PANEL):
        table = panels[key]
        last = len(table) - 1
        ps.annotate(
            ax,
            "above the band,\nsome fitted models are\ndistinguishably worse",
            xy=(float(last), float(table["fitted_high"].iloc[last])),
            xytext=(0.988, 0.97), textcoords="axes fraction", ha="right", va="top",
        )

    # Both pieces of furniture are in place, so the axis can be grown to fit them.
    for ax in axes:
        _raise_top_until_furniture_clears(ax)
        _underline_legend_headings(fig, ax)
    return fig


#: Where the annotation's target sits in the panel, as a share of its height.
#: The note is anchored near the top, so holding its target here leaves a leader
#: long enough for the arrowhead to read. Set rather than measured: an
#: Annotation's window extent covers its arrow as well as its text, so sizing the
#: arrow from that extent is circular and does not converge.
ANNOTATION_TARGET_SHARE = 0.72

#: Pixels of clear space between the legend and the nearest series beneath it.
#: In pixels rather than as a share of the data range, which would grow with the
#: range it is used to enlarge. Carbon dioxide's benchmark line runs high in its
#: panel, so this is what separates the two; matching methane's much larger gap
#: exactly would compress the carbon dioxide comparison into half its panel.
LEGEND_CLEARANCE_PX = 60


def _raise_top_until_furniture_clears(ax, rounds: int = 8) -> None:
    """Grow the axis upward until the legend clears the series and the leader shows.

    The legend and the note are both anchored in axes fractions, so raising the
    top moves the data away from them. Two requirements: the legend keeps a fixed
    pixel gap above the highest series beneath it, and the note's target sits at a
    fixed share of the panel height, which is what gives the arrow its length.
    """
    for _ in range(rounds):
        ax.figure.canvas.draw()
        low, high = ax.get_ylim()
        frame = ax.get_window_extent()
        needed = high - low

        legend = ax.get_legend().get_window_extent()
        box = legend.transformed(ax.transData.inverted())
        highest = -np.inf
        for line in ax.lines:
            x = np.asarray(line.get_xdata(), dtype=float)
            y = np.asarray(line.get_ydata(), dtype=float)
            under = (x >= box.x0) & (x <= box.x1)
            if under.any():
                highest = max(highest, float(y[under].max()))
        share = (legend.y0 - frame.y0 - LEGEND_CLEARANCE_PX) / frame.height
        if highest > -np.inf and share > 0:
            needed = max(needed, (highest - low) / share)

        for note in ax.texts:
            if "above the band" in note.get_text():
                needed = max(needed, (note.xy[1] - low) / ANNOTATION_TARGET_SHARE)

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
    ps.legend(ax, handles=[h for h, _ in entries], labels=[label for _, label in entries],
              loc="upper center", bbox_to_anchor=(0.46, 0.90), ncol=2, borderpad=0.7,
              labelspacing=0.34, columnspacing=2.0, handlelength=2.2,
              handletextpad=0.8, fontsize=ps.LEGEND_SIZE - 1.0, framealpha=1.0)


def _underline_legend_headings(fig, ax) -> None:
    """Rule each legend heading, which mathtext cannot do itself.

    Drawn on the figure rather than the axes so it does not appear in `ax.lines`,
    where the checks that keep the legend off the data would then see it.
    """
    fig.canvas.draw()
    legend = ax.get_legend()
    for text in legend.get_texts():
        if not text.get_text().startswith("$"):
            continue
        box = text.get_window_extent().transformed(fig.transFigure.inverted())
        y = box.y0 - 0.10 * (box.y1 - box.y0)
        fig.add_artist(Line2D([box.x0, box.x1], [y, y], transform=fig.transFigure,
                              color=ps.INK, linewidth=0.9,
                              zorder=legend.get_zorder() + 1))


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
    title="Observed and predicted monthly flux at Marcell Bog Lake Peatland",
    subtitle=(
        "Each month's flux is measured as an average of the half-hourly readings "
        "taken that month, drawn here in black with a shaded band showing the "
        "uncertainty in that average, drawn as two standard errors. Two "
        "predictions are drawn against it, both made a "
        "month in advance: the seasonal average, which uses the mean of that month "
        "across previous years, and a green band spanning the highest and lowest of "
        "eight fitted models. Neither is available for most of the record, since "
        "the models need several years of history before they can forecast at all. "
        "The shaded years mark where predictions exist."
    ),
    description=(
        "The predictions follow the seasonal cycle, rising and falling in step "
        "with the measurements. On methane their largest misses are usually "
        "over-predictions. In 12 of the 57 evaluated methane months the flux came "
        "in below every fitted model, and in nine of those below the seasonal "
        "average too. 2015 is the clearest example: the seasonal average "
        "predicted 94 nanomoles for July and the tower measured 40. What the "
        "models miss is not when the season happens but how large it will be in a "
        "weak year. 2021, the weakest summer, lies outside the evaluated window "
        "and was never forecast. On carbon dioxide the eight models disagree by "
        "less than half the uncertainty in the measurement, which is why the green "
        "band sits inside the black one."
    ),
)


def _draw_flux_panel(ax, panel: pd.DataFrame, unit: str, labeled: bool) -> None:
    """One gas: the measured series over the record, and predictions where they exist.

    The evaluated months are shaded rather than clipped to, so a reader sees how
    much of the record was never forecast: 40% of the methane months carry a
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
        under = (positions >= box.x0) & (positions <= box.x1)
        if not under.any():
            return
        highest = float(np.nanmax(ceiling[under]))
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
        ps.even_year_ticks(ax, first.year, last.year)
        _raise_top_for_flux_legend(ax, panels[key])
        _underline_legend_headings(fig, ax)
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
        "Each model predicts a fixed distance ahead, from one month to twelve, "
        "and was rebuilt every month as the record grew. Each time it chose which "
        "of the measurements to use, and the green bars show how often each was "
        "chosen, from never to every rebuild. The grey bars show something "
        "different: how much of that measurement can be predicted from the date "
        "alone, which is high for temperature and near zero for the water table. "
        "Reading the two together, what the models chose most often are the "
        "measurements the date already predicts, and the one thing the date "
        "cannot predict is the one they chose least."
    ),
    description=(
        "Two marks stand where a number would mean nothing. The date question does "
        "not apply to the flux's own past values, which are not measurements taken "
        "at the site. Last month's flux is unavailable to a model forecasting three "
        "or more months ahead. Where a grey bar does stand, it is what three "
        "seasonal terms account for: 95% of soil and air temperature, and about 5% of "
        "the water table. The sharpest case is carbon dioxide three months ahead, "
        "where the models chose none of the four measurements in any rebuild and "
        "kept only the flux's own value from a year earlier."
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

#: The two reasons a cell is empty, which are not the same reason and so are not
#: drawn the same way. Neither is missing data.
NOT_ASKED = "does not apply"
NOT_AVAILABLE = "not available"


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
    blank: str,
) -> None:
    """One column of bars: a share from nothing to everything, per measurement.

    `blank` is what an empty cell means on this column, written into the cell.
    A blank on the date column is a question that does not apply; a blank on a
    horizon column is a value a model at that horizon cannot have. Left unmarked
    they would look alike, and both would look like missing data.
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
    for position in positions[~drawn]:
        ax.text(3.0, position, blank, va="center", ha="left", style="italic",
                fontsize=ps.TICK_SIZE - 2.0, color=ps.MUTED, zorder=3)

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
                          ps.DATE_SHARE, bottom_row, rule_after, NOT_ASKED)
        date.set_yticklabels(order, fontsize=ps.TICK_SIZE, color=ps.INK)
        # Named in the same bordered box as the other figures, seated above the
        # panel rather than in its corner: the corner holds the first row, which
        # here is a marked cell rather than the empty space the box needs.
        ps.panel_name(date, gas, x=-LABEL_PX / (column * width_px),
                      y=1 + 30 / (row_height * height_px))

        for index, horizon in enumerate(horizons):
            ax = fig.add_axes((first + index * (column + gap), base, column, row_height))
            _draw_usage_panel(ax, panel[horizon], order, ps.FITTED, bottom_row,
                              rule_after, NOT_AVAILABLE)
            if row == 0:
                fig.text(first + index * (column + gap) + column / 2,
                         base + row_height + 8 / height_px,
                         f"{horizon} month" + ("s" if horizon > 1 else ""),
                         ha="center", va="bottom", fontsize=ps.LABEL_SIZE, color=ps.INK)

    # Two headings rather than a legend: they name the two quantities the two
    # colors stand for, so a key repeating them would say nothing the columns do
    # not already say in the place a reader is looking.
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
        fig.text(middle, bottom - 34 / height_px, axis, ha="center", va="top",
                 fontsize=ps.LABEL_SIZE, color=ps.MUTED)
    return fig


STABILITY_TEXT = ps.FigureText(
    title=("The water table coefficient refitted on drier months at "
           "Marcell Bog Lake Peatland"),
    subtitle=(
        "The model was fitted five times, each on a smaller set of months: first "
        "all 115, then the same months with the wettest tenth removed, and on to "
        "the wettest two fifths. The water table coefficient is how much predicted "
        "emission changes per meter of water table, and each point is what that "
        "coefficient came out as, placed at the wettest month still in the fit. It "
        "climbs at every step, while the soil temperature coefficient beside it "
        "moves a third as far. A coefficient that changes when its range of water "
        "table shrinks is describing the months it was fitted on rather than the "
        "peatland, so it cannot be carried out along the arrow, where the "
        "reconstruction needs it."
    ),
    description=(
        "The same analysis is drawn twice, once weighting each month by how well it "
        "was measured and once not. Both fail and neither is the better treatment: "
        "weighted, the coefficient rises 51%, from 2.704 to 4.077; unweighted, 38%, "
        "from 2.385 to 3.299. Every step's range overlaps the first, so no single "
        "step is decisive, and the evidence is that it climbs at all four and never "
        "once falls. The soil temperature coefficient moves 16% along the same "
        "path, and only without weighting is it flat."
    ),
)

#: The two treatments, achromatic and separated by line style. Hue would make them
#: read as two methods being compared, and they are one analysis run twice: the
#: finding is that neither survives, not that one of them does.
TREATMENTS = (
    ("weighted", "with weighting", {"color": ps.INK, "linestyle": "-", "linewidth": 1.8,
                                    "marker": "o", "markersize": 6.0}),
    ("unweighted", "without weighting", {"color": "#767676", "linestyle": (0, (7, 2, 2, 2)),
                                         "linewidth": 1.5, "marker": "^", "markersize": 6.2}),
)

#: The two terms, the columns each is carried in, and the unit its axis is in.
#: Soil temperature is drawn as the fitted slope rather than as its Q10, which is
#: an exponential of the same number: on the Q10 scale the same experiment reports
#: a different drift, and the two panels would no longer be comparable.
STABILITY_TERMS = (
    ("Water table", "water_table_coef", "water_table_lo", "water_table_hi",
     "Per meter of water table", None),
    ("Soil temperature", "soil_temp_coef", "soil_temp_lo", "soil_temp_hi",
     "Per °C of soil temperature",
     "The control: the same experiment, on a coefficient that barely moves"),
)

STABILITY_X_AXIS = "Water table, in meters from the wettest month the model was fitted on"
COUNT_AXIS = "Months in the fit"
TESTED_LABEL = "held out and tested"
BEYOND_LABEL = (
    "The reconstruction needs this coefficient to hold {required:.2f} m beyond the\n"
    "wettest month ever fitted ({ratio:.1f} times the {span:.2f} m this experiment covers)"
)
EDGE_LABEL = "The wettest month the model was fitted on"


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
                    label=label, **style, markerfacecolor="white",
                    markeredgewidth=1.4)
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
    # Off the data and into the ground the fill used to cover, on both panels.
    ps.panel_name(ax, name, align="right")
    if caption:
        ax.text(0.985, 0.46, caption, transform=ax.transAxes, ha="right", va="center",
                fontsize=ps.ANNOTATION_SIZE, style="italic", color=ps.MUTED, zorder=5)


def _draw_beyond_arrow(ax, required: float, span: float) -> None:
    """What the reconstruction asks for, as an arrow rather than as a region."""
    ax.annotate("", xy=(required, 0.20), xytext=(0.004, 0.20),
                xycoords=("data", "axes fraction"), textcoords=("data", "axes fraction"),
                arrowprops=dict(arrowstyle="-|>", color=ps.OUTSIDE, linewidth=1.2,
                                shrinkA=0, shrinkB=0), zorder=4)
    ax.text(required / 2, 0.245, BEYOND_LABEL.format(required=required,
                                                     ratio=required / span, span=span),
            transform=ax.get_xaxis_transform(), ha="center", va="bottom",
            fontsize=ps.ANNOTATION_SIZE, color=ps.OUTSIDE, linespacing=1.5, zorder=4)


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


def _stability_legend(fig, ax) -> None:
    """One key for both panels, in the ground the shaded region used to cover.

    Two columns with ruled headings, as elsewhere in the set. Panel b carries the
    same four marks and no key of its own, so a second one would repeat itself.
    """
    blank = Line2D([], [], linestyle="none", marker="none")
    entries = [(blank, r"$\bf{The\ two\ treatments}$")]
    entries += [(Line2D([], [], **style), label) for _, label, style in TREATMENTS]
    entries += [(blank, ""), (blank, "")]
    entries += [
        (blank, r"$\bf{What\ the\ marks\ show}$"),
        (Line2D([], [], color=ps.BOUNDARY, linestyle="none", marker="|", markersize=11,
                markeredgewidth=1.2),
         "Where the coefficient landed in 500 resamples"),
        (Line2D([], [], color=ps.INK, linestyle=(0, (1, 2.4)), linewidth=0.9),
         "Its value on the whole range, carried across"),
        (Line2D([], [], color=ps.OUTSIDE, linestyle=(0, (5, 3)), linewidth=1.1),
         EDGE_LABEL),
        (Line2D([], [], color=ps.BOUNDARY, linewidth=1.2, marker="|", markersize=8,
                markeredgewidth=1.2),
         "A distance in meters of water table"),
    ]
    ps.legend(ax, handles=[h for h, _ in entries],
              labels=[label for _, label in entries],
              loc="upper right", bbox_to_anchor=(0.998, 0.90), ncol=2, frameon=False,
              labelspacing=0.42, columnspacing=2.2, handlelength=2.4,
              handletextpad=0.9, fontsize=ps.LEGEND_SIZE - 1.0, borderpad=0.0)
    _underline_legend_headings(fig, ax)


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
    counts.set_xticklabels([f"{n:.0f}" for n in reference["n_months"]],
                           fontsize=ps.TICK_SIZE - 1.5, color=ps.MUTED)
    counts.set_xlabel(COUNT_AXIS, fontsize=ps.LABEL_SIZE, color=ps.INK, labelpad=6)
    counts.tick_params(length=3.2, width=0.9, colors=ps.MUTED)
    counts.spines["top"].set_visible(False)

    _seat_axis_names(fig, axes)
    _draw_beyond_arrow(axes[0], required, abs(x.min()))
    _stability_legend(fig, axes[0])

    strip_base = bottom + label_band
    strip_ax = fig.add_axes((left, strip_base, width, strip))
    _draw_stability_strip(strip_ax, span, tested)
    fig.text(left + width / 2, strip_base - 44 / height_px, STABILITY_X_AXIS,
             ha="center", va="top", fontsize=ps.LABEL_SIZE, fontweight="bold",
             color=ps.INK)
    return fig


# --------------------------------------------------------------------------
# Covariate availability
# --------------------------------------------------------------------------

AVAILABILITY_TEXT = ps.FigureText(
    title=("Which months each measurement and each analysis cover at "
           "Marcell Bog Lake Peatland"),
    subtitle=(
        "Each row in the upper block is one measurement, and the bar covers the "
        "months it exists. They are ordered by where each record ends, latest "
        "first. The rows below are what each analysis covers: the months the model "
        "used, and the months its forecasts were checked on. Those spans were "
        "chosen from what was available rather than being facts about the site. "
        "The study's boundaries fall where the shortest records end."
    ),
    description=(
        "Air temperature and precipitation stop at the end of 2019. That ends the "
        "months the model could learn from, and discards 25 months of methane the "
        "tower recorded. Forecasts cannot be checked until 48 months of flux have "
        "accumulated. For methane that took 62 calendar months, because of the "
        "gaps in 2013 and 2014. The check ends in 2020, which is as far as the "
        "models that use the drivers can run. The seasonal "
        "benchmarks alone reach 2021 and 2024. Blue marks the range the model was "
        "fitted on, as it does across this set. The two hollow marks are decisions "
        "rather than absences. The water table is set aside from January 2020 for "
        "a gauge change. Two months of 2019 are set aside for instrument error."
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
TIME_AXIS = "Year"
PRESENT_LABEL = "months covered"
MISSING_LABEL = "a month missing"
ASIDE_LABEL = "set aside by the study"
FITTED_RANGE_LABEL = "the range the model was fitted on"
TRAINING_LABEL = "48 months of training first"

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
    fig, (left, bottom, width, height) = ps.canvas_area(AVAILABILITY_TEXT, size="standard")
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

    entries = [
        (Patch(facecolor=ps.MEASURED, edgecolor="none"), PRESENT_LABEL),
        (Line2D([], [], color=ps.MEASURED, linestyle="none", marker="|", markersize=10,
                markeredgewidth=1.4), MISSING_LABEL),
        (Patch(facecolor="white", edgecolor=ps.OUTSIDE, linewidth=1.2), ASIDE_LABEL),
        (Patch(facecolor=ps.INSIDE, edgecolor="none"), FITTED_RANGE_LABEL),
    ]
    ps.legend(ax, handles=[h for h, _ in entries], labels=[label for _, label in entries],
              loc="lower center", bbox_to_anchor=(0.5, 1.012), ncol=len(entries),
              framealpha=1.0, handlelength=1.8, handletextpad=0.7, columnspacing=2.0,
              borderpad=0.55, fontsize=ps.LEGEND_SIZE - 1.0)
    return fig


# --------------------------------------------------------------------------
# The seasonal cycle and what it leaves
# --------------------------------------------------------------------------

SEASONAL_TEXT = ps.FigureText(
    title="The seasonal cycle in monthly flux at Marcell Bog Lake Peatland",
    subtitle=(
        "Each column is one gas and each row is one part of its record. The middle "
        "row is one average shape for the whole record (the same twelve values "
        "repeated every year). The bottom row is what the measurements leave once "
        "that shape is taken out. It is where the size of each season lives. "
        "Nothing tested here predicted it: eight fitted models, four benchmarks "
        "and four measured drivers."
    ),
    description=(
        "What the repeating shape leaves is half the variation in the record: 0.54 "
        "of the measurements' spread on methane and 0.53 on carbon dioxide. The "
        "shape accounts for the rest, 71% of the variance in both. The size of the "
        "season is what varies: methane's swing from lowest to highest month runs "
        "33.7 to 150.6 across the years, a factor of 4.5, and carbon dioxide's 0.8 "
        "to 2.4, a factor of 3.0, neither of them trending (p = 0.119 and 0.505). "
        "The level was tested for a trend as well, and neither gas has one, so "
        "nothing was removed for it. This shape is fitted on every observed month, "
        "which is not what the forecast benchmark does: that one is rebuilt inside "
        "each fold from the months up to it."
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
#: Height of each row against the others. The bottom row is where the finding is,
#: and the middle row is twelve numbers repeated, so it needs the least.
SEASONAL_WEIGHTS = (1.0, 0.8, 1.5)

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


#: Room at the left for the row names, and at the top for the gas labels.
SEASONAL_GUTTER_PX = 486
SEASONAL_HEAD_PX = 46
SEASONAL_ROW_GAP_PX = 26
SEASONAL_COLUMN_GAP_PX = 96


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
    ax.margins(y=0.08)
    ax.tick_params(top=False, right=False)
    ax.grid(axis="x", color=ps.GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(ps.BOUNDARY)


def _scale_step(span: float) -> float:
    """A round number about a third of the widest panel in this gas's units."""
    rough = span / 3.0
    power = 10.0 ** np.floor(np.log10(rough))
    return float(next(step * power for step in (1.0, 2.0, 5.0, 10.0)
                      if step * power >= rough * 0.7))


def _draw_scale_bar(ax, step: float, unit: str, labeled: bool) -> None:
    """The same length in data units on every row, following Cleveland et al.

    Each row is scaled to its own data, so without this a reader cannot tell that
    what the average year leaves is smaller than the average year's own swing
    rather than compressed into a shorter panel. Hung from the same height in each
    row so the three can be compared by their ends rather than by their middles.
    """
    low, high = ax.get_ylim()
    ceiling = low + 0.88 * (high - low)
    width_px = ax.get_window_extent().width
    at = 1.0 + 14 / width_px
    ax.plot([at] * 2, [ceiling - step, ceiling], transform=ps.blended(ax),
            color=ps.BOUNDARY, linewidth=3.0, solid_capstyle="butt", zorder=5,
            clip_on=False)
    if labeled:
        # Said once per column, beside the topmost bar, because a grey rectangle
        # with a number next to it is the one mark here nothing else accounts for.
        ax.text(at + 11 / width_px, ceiling - step / 2, f"{step:g} {unit} in every row",
                transform=ps.blended(ax), rotation=90, ha="left", va="center",
                fontsize=ps.ANNOTATION_SIZE - 1.0, color=ps.MUTED, zorder=5,
                clip_on=False)


def _mark_extreme_years(ax, panel: pd.DataFrame) -> None:
    """Name the strongest and weakest seasons, lightly and off the data.

    The finding is that the size of the season varies without direction, so these
    are two labeled points in a scattered field rather than two events against a
    quiet background. They are set at annotation weight for that reason, seated in
    a strip cleared above and below the data so neither sits on the line.
    """
    swing = panel.attrs["swing"]
    leftover = panel["leftover"]
    low, high = ax.get_ylim()
    room = 0.18 * (high - low)
    ax.set_ylim(low - room, high + room)
    floor, ceiling = ax.get_ylim()
    # The scale bar reads inside its own panel, series against bar, so padding a
    # row to make room for a label does not disturb the comparison between rows.
    span = ax.get_xlim()

    for year, name in ((swing.idxmax(), "strongest season"),
                       (swing.idxmin(), "weakest season")):
        # The year comes from the measured swing, which is what a season's size
        # means; the month marked is where that year departs furthest from the
        # average, in whichever direction. Picking the maximum for the strong year
        # and the minimum for the weak one assumed the flux was positive, and
        # carbon dioxide is an uptake: its strongest season is its deepest
        # negative and its weakest a high positive, so both marks landed on
        # months near zero that meant nothing.
        inside = leftover[leftover.index.year == year]
        month = inside.abs().idxmax()
        # Seated directly over or under its own point so the leader is vertical
        # and crosses nothing, and pulled inside the axis where a label at the
        # edge would otherwise run off it.
        high_side = float(inside[month]) > 0
        at = ax.convert_xunits(month.to_timestamp())
        room = 0.20 * (span[1] - span[0])
        ps.annotate(ax, f"{year}, {name}",
                    xy=(month.to_timestamp(), float(inside[month])),
                    xytext=(min(max(at, span[0] + room), span[1] - room),
                            ceiling - 0.08 * (ceiling - floor) if high_side
                            else floor + 0.08 * (ceiling - floor)),
                    ha="center", va="center", color=ps.MUTED,
                    fontsize=ps.ANNOTATION_SIZE - 1.0,
                    arrowprops=dict(arrowstyle="->", color=ps.MUTED, linewidth=0.9,
                                    shrinkA=7, shrinkB=5))


#: Room at the left for each column's tick labels, at the top for the gas labels,
#: above each row for its name, and under each panel for its own tick labels.
#:
#: The names sit over their rows rather than beside them. Held in a left gutter
#: they needed 517 px for the widest line alone, which took a quarter of the
#: canvas from the panels; over the row they run the full width and cost only the
#: band they stand in.
SEASONAL_GUTTER_PX = 104
SEASONAL_HEAD_PX = 48
SEASONAL_LABEL_PX = 38
SEASONAL_ROW_GAP_PX = 46
SEASONAL_COLUMN_GAP_PX = 96

#: Reserved to the right of each column for the scale bar and its label, so the
#: bar sits outside the panel rather than over the months at the end of a record.
SEASONAL_BAR_PX = 56

SEASONAL_TIME_AXIS = "Year"


def seasonal_cycle(panels: dict[str, pd.DataFrame]) -> Figure:
    """Each gas split into the shape that repeats and what that shape leaves.

    Three rows against one time axis, so a month sits in the same place in every
    panel and the bottom row can be read as what the two above it do not account
    for. The gases are columns with their own scales: they are in different units,
    and carbon dioxide crosses zero where methane does not. Each column carries a
    scale bar of one length in its own units, since three rows each scaled to their
    own data cannot otherwise be compared.
    """
    fig, (left, bottom, width, height) = ps.canvas_area(SEASONAL_TEXT, size="triple")
    width_px, height_px = ps.SIZES["triple"]
    gutter = SEASONAL_GUTTER_PX / width_px
    head = SEASONAL_HEAD_PX / height_px
    band = SEASONAL_LABEL_PX / height_px
    row_gap = SEASONAL_ROW_GAP_PX / height_px
    column_gap = SEASONAL_COLUMN_GAP_PX / width_px
    bar_room = SEASONAL_BAR_PX / width_px

    column_width = (width - gutter - column_gap - 2 * bar_room) / 2
    room = height - head - len(SEASONAL_ROWS) * band - row_gap * len(SEASONAL_ROWS)
    heights = [room * weight / sum(SEASONAL_WEIGHTS) for weight in SEASONAL_WEIGHTS]

    first = min(panel.index.min() for panel in panels.values()).to_timestamp()
    last = (max(panel.index.max() for panel in panels.values()) + 1).to_timestamp()
    top = bottom + height - head
    columns = []

    def row_base(index: int) -> float:
        """The foot of one row, below its own name band and its own tick labels."""
        return top - sum(heights[: index + 1]) - (index + 1) * band - index * row_gap

    for column, (key, gas, unit) in enumerate(GAS_PANEL):
        panel = panels[key]
        base_x = left + gutter + column * (column_width + column_gap + bar_room)
        step = _scale_step(float(panel["observed"].max() - panel["observed"].min()))
        axes = []
        for index, (_, part, ink, weight) in enumerate(SEASONAL_ROWS):
            ax = fig.add_axes((base_x, row_base(index), column_width, heights[index]))
            _draw_seasonal_row(ax, panel[part], ink, weight, filled=part == "leftover")
            ax.set_xlim(first, last)
            ps.even_year_ticks(ax, first.year, last.year)
            if part == "leftover":
                _mark_extreme_years(ax, panel)
            # Beside the middle bar rather than the top one: the bar is the same
            # length in all three rows, and a label at the top read as the top
            # row's own.
            _draw_scale_bar(ax, step, unit, labeled=index == 1)
            if index == 0:
                # Above the row's own name band, not into it: the band sits
                # directly on the panel and the two frames would otherwise stack.
                ps.panel_name(ax, f"{gas} ({unit})", x=0.5, align="center",
                              y=1.0 + (SEASONAL_LABEL_PX + 34)
                              / (heights[index] * height_px))
            axes.append(ax)
        columns.append((base_x, axes))

    # One time axis name under each column, since a reader reads a column downward
    # and meets its own axis at the foot of it. The ticks are labeled on every
    # panel: a row whose ticks are bare asks the reader to carry them down.
    for base_x, axes in columns:
        fig.text(base_x + column_width / 2, bottom - 34 / height_px,
                 SEASONAL_TIME_AXIS, ha="center", va="top", fontsize=ps.LABEL_SIZE,
                 fontweight="bold", color=ps.INK)

    # Each row named above itself, in the frame the gas labels use, spanning both
    # columns because the row means the same thing in each.
    for index, (name, _, _, _) in enumerate(SEASONAL_ROWS):
        fig.text(left, row_base(index) + heights[index] + band / 2, name, ha="left",
                 va="center", fontsize=ps.TICK_SIZE, color=ps.INK,
                 bbox=dict(boxstyle="round,pad=0.42", facecolor="white",
                           edgecolor=ps.BOUNDARY, linewidth=0.9))
    return fig
