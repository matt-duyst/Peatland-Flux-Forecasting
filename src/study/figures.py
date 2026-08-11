"""One function per figure, each taking prepared data and returning a figure.

Nothing here reads a file or computes a study result. Each function receives the
frames the study modules already produce and is responsible only for drawing, so
a figure can be built in a test from a few synthetic rows.

Shared drawing decisions live in `plotstyle`; the words each figure carries live
beside it here, as a `FigureText`, and reach the README through the same object.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

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
    ax.set_xlim(times[0], times[-1])
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
        "from relationships fitted on 2009 to 2019. The three lines each assume "
        "something different about the water table beyond the range it was fitted "
        "on, and they agree only where it stays inside that range. The strip below "
        "gives the share of each year's months that fall outside it. Measurement at "
        "this peatland stopped in 1992 and did not resume until 2007, so eighteen "
        "of these twenty years can never be checked against one. Only 1991 and 1992 "
        "were measured, by Shurpali et al. (1993) and Shurpali and Verma (1998). "
        "Their published totals have not been obtained; this reconstruction "
        "predicts 9.29 and 8.49 g C for May to October."
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
                       inside=False, label=r"Year $\bf{outside}$ it", markersize=7.0)

    check = frame[frame["year"].isin(MEASURED_YEARS)]
    ax.plot(check["year"], check["clamped"], linestyle="none", marker="o",
            markersize=13, markerfacecolor="none", markeredgecolor=ps.INK,
            markeredgewidth=1.2, zorder=3, label="The only measured years")

    # The circled years are two of these four, so one set of labels serves both.
    for _, row in frame[frame["support"] == "inside"].iterrows():
        ax.annotate(f"{int(row['year'])}", xy=(row["year"], row["clamped"]),
                    xytext=(0, 17), textcoords="offset points", ha="center",
                    va="bottom", fontsize=7.8, color=ps.INSIDE, zorder=6,
                    path_effects=[ps._outline()])

    ax.set_ylabel(ps.axis_label("Annual emission", "g C m$^{-2}$ yr$^{-1}$"))
    ax.set_ylim(0, frame[list(WATER_TABLE_ASSUMPTIONS)].to_numpy().max() * 1.18)
    ticks = [y for y in range(int(years.min()), int(years.max()) + 1, 5)]
    if years.max() not in ticks:
        ticks.append(int(years.max()))
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    ax.tick_params(labelbottom=False)
    ps.mirror_ticks(ax)
    ps.legend(ax, loc="lower left", fontsize=8.2, borderpad=0.36, labelspacing=0.3,
              handlelength=1.9, handletextpad=0.5, ncols=2, columnspacing=0.9,
              bbox_to_anchor=(0.015, 0.02))

    share = frame["pct_months_outside"].to_numpy()
    # A year wholly inside has a bar of zero height. Marking those years on the
    # baseline distinguishes a measured zero from a year with nothing plotted.
    strip.bar(years[inside], share[inside], width=0.7, color=ps.INSIDE,
              edgecolor="white", linewidth=0.4)
    strip.plot(years[inside], np.zeros(inside.sum()), linestyle="none",
               marker=ps.INSIDE_MARKER, markersize=4.6, color=ps.INSIDE,
               markeredgecolor="white", markeredgewidth=0.5, clip_on=False, zorder=4)
    strip.bar(years[~inside], share[~inside], width=0.7, color=ps.OUTSIDE,
              edgecolor="white", linewidth=0.4, hatch=ps.OUTSIDE_HATCH)
    strip.set_ylim(0, 108)
    strip.set_yticks([0, 50, 100])
    strip.set_ylabel(ps.axis_label("Months outside", "%"))
    strip.set_xlabel(ps.axis_label("Year"))
    strip.set_xlim(years.min() - 0.8, years.max() + 0.8)
    strip.xaxis.set_minor_locator(MultipleLocator(1))
    ps.mirror_ticks(strip)

    # Set under the fan rather than led to it: a leader from clear space to the
    # middle of the spread would cross every line it is describing.
    fan = frame.loc[(frame["unclamped"] - frame["reduced"]).idxmax(), "year"]
    ax.annotate(
        "The three assumptions agree inside the fitted range and fan apart outside it",
        xy=(float(fan) + 1.0, 13.8), ha="center", va="center",
        fontsize=ps.ANNOTATION_SIZE, style="italic", color=ps.INK, zorder=5,
        path_effects=[ps._outline()],
    )
    return fig
