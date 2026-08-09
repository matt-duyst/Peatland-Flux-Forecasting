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

#: Months whose water table is not credible as a measurement. Both sit about
#: 0.8 m below their neighbors and recover within one month, and both are the
#: lowest value on record for their calendar month by a wide margin. They set no
#: bound and are not drawn; `notes/study.md` carries the evidence.
WATER_TABLE_ARTIFACTS = (pd.Period("2019-06", freq="M"), pd.Period("2019-09", freq="M"))

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
WATER_TABLE_ASSUMPTIONS = {
    "clamped": "Water table held flat beyond the fitted range",
    "unclamped": "Water table continued linearly",
    "reduced": "Water table term absent altogether",
}

#: The reconstruction runs to 2009-03. A three-month year cannot be plotted
#: beside twelve-month years, so the panel stops at 2008.
LAST_PLOTTED_YEAR = 2008

RECONSTRUCTION_TEXT = ps.FigureText(
    title="Reconstructed methane emission at Marcell Bog Lake Peatland, 1990 to 2008",
    subtitle=(
        "Where the water table runs beyond its fitted range, the answer depends on an "
        "assumption the record cannot test"
    ),
    description=(
        "Each marker is one year's emission in grams of carbon per square meter, "
        "fitted on 2009 to 2019. The three lines are not a likely range: each "
        "assumes something different about the water table beyond its fitted range, "
        "and where they diverge the assumption sets the answer. The strip gives the "
        "share of each year's months outside that range, which separates marginal "
        "years from unsupported ones. Shurpali et al. (1993) and Shurpali and Verma "
        "(1998) measured 1991 and 1992, the only independent check; this predicts "
        "9.29 and 8.49 for May to October, and their values have not been obtained. "
        "The model should read low by about 14%, stated not applied: correcting "
        "would extrapolate the correction. 2009 is omitted with three months; 1995 "
        "keeps eleven."
    ),
    emphasize=(),
)


def reconstruction_series(annual: pd.DataFrame) -> Figure:
    """Annual reconstruction, its support, and the assumption it rests on.

    The three assumptions are drawn as three named lines rather than as a band.
    A band would say the answer lies somewhere inside it, which is the reading
    this study exists to refuse: the spread is what the choice of assumption
    buys, not a probability.
    """
    from matplotlib.ticker import MultipleLocator

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
                       inside=True, label="Year inside the fitted range",
                       markersize=6.5)
    ps.support_scatter(ax, years[~inside], frame["clamped"].to_numpy()[~inside],
                       inside=False, label="Year outside it", markersize=7.0)

    ax.set_ylabel(ps.axis_label("Annual emission", "g C m$^{-2}$ yr$^{-1}$"))
    ax.set_ylim(0, frame[list(WATER_TABLE_ASSUMPTIONS)].to_numpy().max() * 1.18)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    ax.tick_params(labelbottom=False)
    ps.mirror_ticks(ax)
    ps.legend(ax, loc="upper left", fontsize=8.4, borderpad=0.45, labelspacing=0.34,
              handlelength=2.6, ncols=2, columnspacing=1.6)

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

    check = frame[frame["year"].isin((1991, 1992))]
    ps.annotate(
        ax,
        "1991 and 1992 carry the only\nindependent check, still pending",
        xy=(1992, float(check["clamped"].max())),
        xytext=(1993.4, float(check["clamped"].max()) * 0.66),
        ha="left", va="center",
    )
    return fig
