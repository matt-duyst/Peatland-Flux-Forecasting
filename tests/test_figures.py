"""The water table figure, drawn from synthetic months rather than the dataset."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures, plotstyle as ps


def frames():
    """Twelve reconstruction months, six of them wet, then six fitted months."""
    months = pd.period_range("2000-01", periods=18, freq="M")
    values = np.concatenate([
        np.full(6, 413.0),      # reconstruction, inside
        np.full(6, 413.9),      # reconstruction, above anything fitted
        np.linspace(413.0, 413.4, 6),  # the fit window
    ])
    series = pd.Series(values, index=months, name="wte_m")
    return series, months[12:], months[:12]


def test_each_legend_entry_does_one_job():
    """A legend says what a mark means, and the range entry says where it sits.

    How many months fall outside is a finding rather than a key, and the
    description carries both counts. The elevations stay, because they are what
    the dashed lines mark and a reader cannot read them off the axis.
    """
    series, fit, reconstruction = frames()
    fig = figures.water_table_support(series, fit, reconstruction, artifacts=())
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert "Outside the fitted range" in labels, labels
    assert not any(char.isdigit() for label in labels
                   for char in label if "Fitted range," not in label), labels
    assert any(label.startswith("Fitted range, ") and " to " in label
               for label in labels), labels
    ps.plt.close(fig)


def test_months_beyond_the_fitted_range_are_marked_apart():
    series, fit, reconstruction = frames()
    fig = figures.water_table_support(series, fit, reconstruction, artifacts=())
    marks = {(line.get_color(), line.get_marker())
             for line in fig.axes[0].lines
             if line.get_linestyle() == "None" and len(line.get_xdata())}
    assert len(marks) == 2, f"inside and outside are two separate marks: {marks}"
    ps.plt.close(fig)


def test_an_artifact_month_sets_no_bound_and_is_not_drawn():
    """Excluding a spurious low month narrows the range and tightens the test."""
    series, fit, reconstruction = frames()
    spurious = fit[0]
    series = series.copy()
    series.loc[spurious] = 400.0

    with_it = figures.water_table_support(series, fit, reconstruction, artifacts=())
    without = figures.water_table_support(series, fit, reconstruction, artifacts=(spurious,))
    def lower_bound(fig):
        # The range bounds are the horizontal two-point lines; the window
        # boundary is vertical and must not be mistaken for one.
        flat = [l.get_ydata() for l in fig.axes[0].lines
                if len(l.get_ydata()) == 2 and l.get_ydata()[0] == l.get_ydata()[1]]
        return min(y[0] for y in flat)

    lower_with, lower_without = lower_bound(with_it), lower_bound(without)
    assert lower_with == 400.0 and lower_without > 400.0

    drawn = max(without.axes[0].lines, key=lambda l: len(l.get_ydata())).get_ydata()
    assert np.isnan(drawn).sum() == 1
    ps.plt.close(with_it); ps.plt.close(without)


def test_a_gap_breaks_the_line_rather_than_being_bridged():
    series, fit, reconstruction = frames()
    series = series.drop(series.index[3])
    fig = figures.water_table_support(series, fit, reconstruction)
    # The bound rules are drawn first; the series is the line spanning every month.
    series_line = max(fig.axes[0].lines, key=lambda l: len(l.get_ydata()))
    assert np.isnan(series_line.get_ydata()).sum() == 1
    ps.plt.close(fig)


def test_axes_are_labelled_with_units():
    series, fit, reconstruction = frames()
    fig = figures.water_table_support(series, fit, reconstruction)
    assert "meters" in fig.axes[0].get_ylabel()
    assert fig.axes[0].get_xlabel()
    ps.plt.close(fig)


def test_the_figure_carries_its_own_words():
    assert figures.WATER_TABLE_TEXT.title
    assert figures.WATER_TABLE_TEXT.subtitle != figures.WATER_TABLE_TEXT.title
    body = ps.readme_block(figures.WATER_TABLE_TEXT, "water_table_support")
    assert "Each point" in body


def test_the_panel_defines_reconstruction_for_a_reader_arriving_cold():
    """The definition moved out of the description and onto the panel.

    The description used to open by saying what reconstruction means. It now
    opens on the marks, and the term is defined where it is drawn: the two
    period labels say which window the model was fitted on and which it
    predicts into, which is the whole of the definition a reader needs here.
    """
    series, fit, reconstruction = frames()
    fig = figures.water_table_support(series, fit, reconstruction)
    drawn = " ".join(t.get_text() for t in fig.axes[0].texts)
    assert "model predicts here" in drawn, drawn
    assert "model fitted here" in drawn, drawn
    ps.plt.close(fig)


def annual_frame():
    """The reconstruction's nineteen years plus the partial twentieth.

    Shaped like the real table rather than shortened to the few rows most of
    these checks need. A five-year version compresses the x axis enough that the
    strip's key spans half the panel instead of an eighth, which is a different
    layout from the one being checked.
    """
    years = list(range(1990, 2010))
    outside = [67.0, 0.0, 0.0, 7.0, 74.0, 100.0, 100.0, 100.0, 82.0, 74.0,
               100.0, 74.0, 100.0, 7.0, 0.0, 25.0, 0.0, 33.0, 25.0, 33.0]
    clamped = [17.4, 11.9, 11.2, 15.0, 17.6, 16.2, 17.3, 17.4, 17.9, 18.0,
               16.8, 18.0, 17.6, 13.8, 11.4, 16.8, 13.1, 7.9, 8.2, 0.8]
    return pd.DataFrame({
        "year": years,
        "n_months": [12] * 19 + [3],
        "support": ["inside" if y in (1991, 1992, 2004, 2006) else "outside"
                    for y in years],
        "pct_months_outside": outside,
        "clamped": clamped,
        "unclamped": [v + 2.9 if o > 50 else v for v, o in zip(clamped, outside)],
        "reduced": [10.9 if o > 50 else v - 0.6 for v, o in zip(clamped, outside)],
    })


def test_a_partial_year_is_not_plotted_beside_full_ones():
    """2009 holds three months; drawn as a year it would read as a collapse."""
    fig = figures.reconstruction_series(annual_frame())
    drawn = fig.axes[0].lines[0].get_xdata()
    assert max(drawn) == figures.LAST_PLOTTED_YEAR
    assert 2009 not in list(drawn)
    ps.plt.close(fig)


def test_the_spread_is_drawn_as_lines_and_never_as_a_band():
    """A band would say the answer lies inside it, which is the reading refused."""
    fig = figures.reconstruction_series(annual_frame())
    ax = fig.axes[0]
    filled = [c for c in ax.collections if type(c).__name__ in
              ("PolyCollection", "FillBetweenPolyCollection")]
    assert not filled, "the sensitivity spread must not be rendered as a filled region"
    assert not ax.patches
    assert len([l for l in ax.lines if l.get_marker() in ("None", "")]) == 3
    ps.plt.close(fig)


def test_the_three_lines_are_achromatic_and_separately_styled():
    fig = figures.reconstruction_series(annual_frame())
    lines = [l for l in fig.axes[0].lines if l.get_marker() in ("None", "")]
    from matplotlib.colors import to_hex
    for line in lines:
        r, g, b = (int(to_hex(line.get_color())[i:i + 2], 16) for i in (1, 3, 5))
        assert r == g == b, f"{to_hex(line.get_color())} is not achromatic"
    # A custom dash tuple reports as "--", so the styles are compared by the
    # dash pattern actually drawn rather than by the style name.
    patterns = {str(getattr(l, "_unscaled_dash_pattern", l.get_linestyle())) for l in lines}
    assert len(patterns) == 3
    ps.plt.close(fig)


def test_the_panel_names_assumptions_rather_than_internal_variants():
    fig = figures.reconstruction_series(annual_frame())
    import re

    raw = " ".join(t.get_text() for t in fig.axes[0].get_legend().get_texts())
    # Terms shared with the subtitle are set bold, so the markup is stripped
    # before comparing against the words a reader actually sees.
    labels = re.sub(r"\$\\bf\{(.*?)\}\$", r"\1", raw)
    for internal in ("clamped", "unclamped", "reduced"):
        assert internal not in labels.lower()
    assert "held flat" in labels and "continued linearly" in labels
    ps.plt.close(fig)


def test_support_is_shown_by_degree_as_well_as_by_verdict():
    """A year 25% outside must not read like one 100% outside."""
    fig = figures.reconstruction_series(annual_frame())
    heights = sorted(round(p.get_height(), 1) for p in fig.axes[1].patches)
    assert 25.0 in heights and 67.0 in heights
    ps.plt.close(fig)


def test_a_year_with_no_months_outside_is_marked_flat_and_in_blue():
    """A measured zero is not a missing bar, and its ink must not contradict itself.

    Flat rather than round, so it reads as a bar of no height rather than as a
    point from another series. Blue rather than orange, because orange means
    outside the fitted range across this set and the mark means none outside;
    these are the same years the panel above marks blue.
    """
    from matplotlib.colors import to_rgba

    fig = figures.reconstruction_series(annual_frame())
    strip = fig.axes[1]
    flat = [line for line in strip.lines if line.get_marker() == "_"]
    assert flat, "the inside years are not marked at all"
    inside = (annual_frame()["support"] == "inside").sum()
    assert len(flat[0].get_xdata()) == inside
    assert to_rgba(flat[0].get_color()) == to_rgba(ps.INSIDE)
    assert to_rgba(flat[0].get_color()) != to_rgba(ps.OUTSIDE)
    assert all(y == 0 for y in flat[0].get_ydata())
    ps.plt.close(fig)


def test_the_strip_names_both_of_its_marks_in_its_own_key():
    """The hatching and the flat mark appear only in the strip, so they are
    keyed there. Folded into the panel above they would put an entry for hatched
    bars on a panel carrying none."""
    fig = figures.reconstruction_series(annual_frame())
    labels = [t.get_text() for t in fig.axes[1].get_legend().get_texts()]
    assert "Months outside" in labels, labels
    assert "No months outside" in labels, labels
    panel = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert "Months outside" not in panel, panel
    ps.plt.close(fig)


def test_the_strip_bar_is_named_what_the_strip_axis_names():
    """One quantity, one name. The key said share of the year and the axis said
    months outside, which are the same thing counted the same way."""
    fig = figures.reconstruction_series(annual_frame())
    labels = [t.get_text() for t in fig.axes[1].get_legend().get_texts()]
    assert "Months outside" in fig.axes[1].get_ylabel()
    assert "Months outside" in labels
    ps.plt.close(fig)


def test_both_keys_head_their_groups_at_one_size_and_weight():
    """Two placements of one device, not two devices.

    The panel heads its groups with blank-handle rows and the strip heads its
    one with a legend title, because three stacked rows cover the 2007 bar
    however the heading is set. They differ in where the text sits, so they must
    not differ in anything else.
    """
    fig = figures.reconstruction_series(annual_frame())
    headings = [text for text in fig.axes[0].get_legend().get_texts()
                if text.get_text().startswith("$")]
    assert len(headings) == 2, "the panel names both of its groups"
    title = fig.axes[1].get_legend().get_title()
    assert title.get_text(), "the strip names its group"
    everything = headings + [title]
    sizes = {round(t.get_fontsize(), 3) for t in everything}
    assert len(sizes) == 1, f"headings set at different sizes: {sizes}"
    assert all(t.get_text().startswith(r"$\bf{") for t in everything), \
        "all three are bold through the same mathtext"
    ps.plt.close(fig)


def test_every_group_heading_is_ruled():
    """The rule is what makes a heading read as one, so all three carry it."""
    from matplotlib.lines import Line2D as _Line2D

    fig = figures.reconstruction_series(annual_frame())
    rules = [a for a in fig.artists
             if isinstance(a, _Line2D) and a.get_transform() is fig.transFigure]
    assert len(rules) == 3, f"two panel headings and one strip heading: {len(rules)}"
    ps.plt.close(fig)


def test_the_strip_legend_fits_inside_the_frame_without_covering_a_bar():
    """The strip is secondary and must not gain height to carry its own key.

    The key clears the tallest bar beneath it by 18.6 points on the real data,
    but that is a property of the last years being short rather than of the
    layout, so nothing would fail if a future change put a tall bar under it.
    This is what fails.
    """
    fig = figures.reconstruction_series(annual_frame())
    fig.canvas.draw()
    strip = fig.axes[1]
    frame = strip.get_window_extent()
    legend = strip.get_legend().get_window_extent()
    assert legend.y1 <= frame.y1 and legend.y0 >= frame.y0, "the legend leaves the frame"
    box = legend.transformed(strip.transData.inverted())
    under = [bar.get_height() for bar in strip.patches
             if box.x0 <= bar.get_x() + bar.get_width() / 2 <= box.x1]
    assert box.y0 > max(under, default=0.0), "the legend covers a bar"
    ps.plt.close(fig)


def test_a_year_wholly_inside_is_drawn_as_a_zero_and_not_omitted():
    """A measured zero is not a missing year, so the strip marks it."""
    fig = figures.reconstruction_series(annual_frame())
    strip = fig.axes[1]
    flat = [line for line in strip.lines if line.get_marker() == "_"]
    assert flat, "no zero marks drawn"
    assert (flat[0].get_ydata() == 0).all()
    ps.plt.close(fig)


# ---------------------------------------------------------------------------
# Drawn geometry against a fresh recomputation, for the figures whose drawn
# values are an estimator's output rather than a redrawing of an input.
#
# The gap: a check that reads the artifact confirms what was drawn, a check on
# the numbers confirms the arithmetic, and while the two never run in one
# process the first faithfully confirms whatever the second regressed to. Each
# test below builds the figure through the production path and compares geometry
# read off the artists against values recomputed here.
# ---------------------------------------------------------------------------


def _forecast_rows(gas: str) -> dict:
    from ingest import paths

    built = {}
    for family in ("benchmarks", "autoregressive", "exogenous"):
        frame = pd.read_csv(paths.processed_dir() / f"forecasts_{gas}_{family}.csv")
        frame["target"] = pd.PeriodIndex(frame["target"], freq="M")
        built[family] = frame
    return built


def _shared_pairs(frames: dict) -> set:
    sets = []
    for frame in frames.values():
        usable = frame.dropna(subset=["actual", "forecast", "mase_scale"])
        methods = usable["method"].nunique()
        counts = usable.groupby(["horizon", "target"])["method"].nunique()
        sets.append({pair for pair, n in counts.items() if n == methods})
    return set.intersection(*sets)


@pytest.mark.parametrize("gas", ["methane", "carbon_dioxide"])
def test_year_panels_draw_the_recomputed_errors(gas):
    """Every point is a month's measurement against the middle of eight
    predictions, recomputed here from the scored rows.

    The pivot is on family and method. Keying on the method name alone averages
    each method's two families, which is the bug that once halved this figure's
    bar, so the count of columns is asserted rather than assumed.
    """
    frames = _forecast_rows(gas)
    pairs = {p for p in _shared_pairs(frames) if p[0] == figures.AGREEMENT_HORIZON}

    def only(frame):
        both = list(zip(frame["horizon"], frame["target"]))
        return frame[[p in pairs for p in both]].copy()

    fitted = pd.concat([only(frames[family]).assign(family=family)
                        for family in ("autoregressive", "exogenous")])
    spread = fitted.pivot_table(index="target", columns=["family", "method"],
                                values="forecast")
    assert spread.shape[1] == 8, "eight fitted predictions per month"
    measured = fitted.groupby("target")["actual"].first()
    want = pd.DataFrame({"measured": measured,
                         "middle": measured - spread.median(axis=1)})

    panels = {k: figures.agreement_panel(_forecast_rows(k))
              for k in ("methane", "carbon_dioxide")}
    fig = figures.prediction_error_by_year(panels)
    fig.canvas.draw()

    row = ["methane", "carbon_dioxide"].index(gas)
    drawn = {}
    for ax in fig.axes:
        for line in ax.lines:
            if line.get_marker() != "o" or not len(line.get_xdata()):
                continue
            key = line.get_markerfacecolor()
            drawn.setdefault(key, set()).update(
                zip(np.round(line.get_xdata(), 10), np.round(line.get_ydata(), 10)))
    every = set()
    for points in drawn.values():
        every |= points
    # A year with too few months is dropped from the background as well as the
    # foreground, so the span the title gives is the span of what is drawn.
    counts = want.index.year.value_counts()
    keep = want.index.year.isin(counts[counts >= figures.YEAR_MIN_MONTHS].index)
    want = want[keep]
    expected = set(zip(np.round(want["measured"], 10), np.round(want["middle"], 10)))
    # The gas rows share a figure, so the drawn set is the union of both.
    assert expected <= every, "a recomputed month is missing from the panels"
    assert len(expected) > 40, "the check would pass vacuously on an empty set"
    ps.plt.close(fig)


def test_the_reconstruction_lines_draw_the_recomputed_totals():
    """The three assumption lines are the three variants' annual totals."""
    from ingest import covariates
    from study import (bias, reconstruct, targets, weights as weighting, windows)

    cov = covariates.load_all()
    from ingest import paths
    monthly = pd.read_csv(paths.processed_dir() / "monthly_fch4_from_daily.csv")
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    monthly = monthly.set_index("month")
    built = windows.build_windows(cov, monthly.index)
    inverse = weighting.inverse_variance_weights(monthly).reindex(built["fit"]).dropna()
    monthly_recon = reconstruct.monthly_reconstruction(
        cov, monthly, built["fit"], built["reconstruction"], inverse)
    annual = reconstruct.annual_reconstruction(
        monthly_recon,
        reconstruct.year_support(cov, built["fit"], built["reconstruction"],
                                 windows.RECONSTRUCTION_COVARIATES),
        bias.wet_end_bias(cov, monthly, built["fit"], inverse))
    for variant in reconstruct.VARIANTS:
        totals = targets.monthly_flux_to_annual(monthly_recon[variant])["g_C_m2"]
        annual[variant] = annual["year"].map(totals)

    fig = figures.reconstruction_series(annual)
    fig.canvas.draw()
    kept = annual[annual["year"] <= figures.LAST_PLOTTED_YEAR]
    lines = [line for line in fig.axes[0].lines if line.get_marker() in ("None", "")]
    assert len(lines) == 3
    drawn = sorted((np.asarray(line.get_ydata(), dtype=float) for line in lines),
                   key=lambda a: a.mean())
    want = sorted((kept[v].to_numpy(dtype=float) for v in reconstruct.VARIANTS),
                  key=lambda a: a.mean())
    for got, expect in zip(drawn, want):
        assert np.allclose(got, expect, rtol=0, atol=1e-9)
    ps.plt.close(fig)


def test_the_stability_paths_draw_the_recomputed_coefficients():
    """Each point is one refit's coefficient, at the wettest month it kept."""
    from ingest import paths

    frame = pd.read_csv(paths.processed_dir() / "coefficient_stability.csv")
    fig = figures.coefficient_stability(figures.stability_paths(frame), 0.29, 0.05)
    fig.canvas.draw()
    drawn = set()
    for ax in fig.axes:
        for line in ax.lines:
            if line.get_marker() in ("None", ""):
                continue
            drawn |= set(np.round(np.asarray(line.get_ydata(), dtype=float), 10))
    missing = [(column, value)
               for column in ("water_table_coef", "soil_temp_coef")
               for value in frame[column].dropna()
               if round(float(value), 10) not in drawn]
    assert not missing, f"refits not drawn: {missing}"
    # and nothing is drawn that no refit produced
    # The bars carry the bootstrap interval, so its ends are drawn too.
    every = {round(float(v), 10)
             for column in ("water_table_coef", "water_table_lo", "water_table_hi",
                            "soil_temp_coef", "soil_temp_lo", "soil_temp_hi")
             for v in frame[column].dropna()}
    assert drawn <= every, f"drawn values with no refit behind them: {drawn - every}"
    ps.plt.close(fig)


def test_the_distribution_panels_draw_the_recomputed_quantiles():
    """Each point is one residual against the quantile its rank expects.

    The residuals are refitted here rather than read from anything cached, so a
    change in the fit that the figure quietly inherited would show up as points
    off the recomputed positions.
    """
    from ingest import covariates, paths
    from study import (reconstruct, residuals, weights as weighting, windows)

    cov = covariates.load_all()
    monthly = pd.read_csv(paths.processed_dir() / "monthly_fch4_from_daily.csv")
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    monthly = monthly.set_index("month")
    built = windows.build_windows(cov, monthly.index)
    inverse = weighting.inverse_variance_weights(monthly).reindex(built["fit"]).dropna()
    level = residuals.local_level(len(built["fit"]))
    panels = {}
    for treatment, weights in (("weighted", inverse), ("unweighted", None)):
        fit, _ = reconstruct.fit_variant(cov, monthly, built["fit"], "clamped", weights)
        error = fit.residuals
        if weights is not None:
            error = error * weights.reindex(error.index)
        for family in residuals.FAMILIES:
            panels[(treatment, family)] = residuals.quantile_comparison(
                error, family, level=level)
    fig = figures.residual_distribution_check(panels)
    fig.canvas.draw()
    for ax, (key, frame) in zip(fig.axes, panels.items()):
        points = [line for line in ax.lines
                  if line.get_marker() == "o" and len(line.get_xdata())]
        assert points, f"no points drawn for {key}"
        got_x = np.sort(np.asarray(points[0].get_xdata(), dtype=float))
        got_y = np.sort(np.asarray(points[0].get_ydata(), dtype=float))
        assert np.allclose(got_x, np.sort(frame["expected"].to_numpy()),
                           rtol=0, atol=1e-9)
        assert np.allclose(got_y, np.sort(frame["observed"].to_numpy()),
                           rtol=0, atol=1e-9)
    ps.plt.close(fig)
