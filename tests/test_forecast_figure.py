"""The forecast comparison: its panel data, its encodings, and its clearances.

The panel data is built from small synthetic frames so the suite stays offline.
The palette check is arithmetic on the constants and reads nothing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecast import evaluation
from study import figures
from study import plotstyle as ps

HORIZONS = (1, 3, 6, 12)
PERSISTENCE_LAST = 6


def frames(seed: int = 0) -> dict[str, pd.DataFrame]:
    """One synthetic scored-forecast frame per family, shaped like the real ones."""
    rng = np.random.default_rng(seed)
    months = pd.period_range("2015-01", periods=60, freq="M")
    rows = []
    families = {
        "benchmarks": ("climatology", "seasonal naive", "naive"),
        "autoregressive": ("ridge", "random forest"),
        "exogenous": ("ridge", "random forest"),
    }
    for family, methods in families.items():
        for method in methods:
            scale = {"climatology": 1.0, "seasonal naive": 1.4, "naive": 1.2}.get(method, 1.1)
            for horizon in HORIZONS:
                grow = horizon if method == "naive" else 1.0
                for month in months[:40]:
                    rows.append({
                        "family": family, "method": method, "horizon": horizon,
                        "origin": month, "target": month + horizon,
                        "error": rng.normal(0, scale * grow),
                        "mase_scale": 1.0, "actual": 1.0, "forecast": 1.0,
                    })
    frame = pd.DataFrame(rows)
    return {f: frame[frame["family"] == f].drop(columns="family").copy()
            for f in families}


def panel() -> pd.DataFrame:
    return figures.forecast_panel(frames(), HORIZONS)


def real_panel(gas: str) -> pd.DataFrame:
    """The committed forecasts for one gas, for the few checks that need them."""
    from ingest import paths

    built = {}
    for family in ("benchmarks", "autoregressive", "exogenous"):
        frame = pd.read_csv(paths.processed_dir() / f"forecasts_{gas}_{family}.csv")
        frame["target"] = pd.PeriodIndex(frame["target"], freq="M")
        built[family] = frame
    return figures.forecast_panel(built, HORIZONS)


# --- the panel data ---------------------------------------------------------


def test_one_row_per_horizon_with_the_benchmarks_and_the_fitted_range():
    table = panel()
    assert list(table["horizon"]) == list(HORIZONS)
    for column in ("climatology", "seasonal naive", "naive", "fitted_low",
                   "fitted_high", "margin", "effective_n"):
        assert column in table


def test_the_fitted_range_brackets_every_fitted_method():
    table = panel()
    assert (table["fitted_low"] <= table["fitted_high"]).all()


def test_the_margin_is_the_difference_that_would_have_been_significant():
    """The band is an inverted test, so a difference at its edge sits at p = 0.05."""
    index = pd.period_range("2015-01", periods=80, freq="M")
    rng = np.random.default_rng(1)
    left = pd.Series(np.abs(rng.normal(size=80)), index=index)
    right = pd.Series(np.abs(rng.normal(size=80)), index=index)
    for horizon in (1, 6):
        margin = evaluation.significance_margin(left, right, horizon)
        difference = (left.abs() - right.abs()).to_numpy()
        at_margin = pd.Series(
            np.abs(right.to_numpy()) + (difference - difference.mean() + margin), index=index)
        assert evaluation.diebold_mariano(at_margin, right, horizon)["p"] == pytest.approx(0.05, abs=1e-3)


def test_the_band_widens_when_the_effective_sample_shrinks():
    """Overlap costs precision, and the band has to show it."""
    index = pd.period_range("2015-01", periods=90, freq="M")
    rng = np.random.default_rng(2)
    independent = pd.Series(np.abs(rng.normal(size=90)), index=index)
    smooth = pd.Series(
        np.abs(np.convolve(rng.normal(size=110), np.ones(12) / 12, "valid")[:90]), index=index)
    zero = pd.Series(np.zeros(90), index=index)
    wide = evaluation.significance_margin(smooth, zero, 12)
    narrow = evaluation.significance_margin(independent, zero, 1)
    assert (wide / smooth.mean()) > (narrow / independent.mean())


# --- what the panel draws ---------------------------------------------------


def test_persistence_is_scored_but_not_drawn():
    """It is not a contender, and holding its value compresses the comparison."""
    tables = {k: panel() for k, _, _ in figures.GAS_PANEL}
    assert "naive" in tables["methane"], "it is still scored"
    assert "naive" not in figures.BENCHMARK_STYLE, "and no longer drawn"
    fig = figures.forecast_comparison(tables)
    for ax in fig.axes:
        assert len([line for line in ax.lines if line.get_linestyle() != "None"]) == 4
    ps.plt.close(fig)


def test_both_scales_are_linear():
    """A logarithmic scale made the carbon dioxide comparison unreadable."""
    fig = figures.forecast_comparison({k: panel() for k, _, _ in figures.GAS_PANEL})
    for ax in fig.axes:
        assert ax.get_yscale() == "linear"
    ps.plt.close(fig)


def test_each_panel_spans_what_its_series_occupy():
    """The axis is set from the data, not padded out to a shared round number."""
    tables = {k: panel() for k, _, _ in figures.GAS_PANEL}
    fig = figures.forecast_comparison(tables)
    for ax, key in zip(fig.axes, [k for k, _, _ in figures.GAS_PANEL]):
        table = tables[key]
        low, high = ax.get_ylim()
        drawn_low = min(table["fitted_low"].min(),
                        (table["climatology"] - table["margin"]).min())
        assert low < drawn_low, "the lowest mark must be inside the axis"
        assert low > drawn_low - (high - low), "and not floated far above the floor"
    ps.plt.close(fig)


def test_the_two_panels_do_not_share_a_scale():
    """The gases are in different units and must not invite comparison by height."""
    tables = {k: panel() for k, _, _ in figures.GAS_PANEL}
    tables["carbon_dioxide"] = tables["carbon_dioxide"] * 0.01
    tables["carbon_dioxide"]["horizon"] = list(HORIZONS)
    fig = figures.forecast_comparison(tables)
    assert fig.axes[0].get_ylim() != fig.axes[1].get_ylim()
    ps.plt.close(fig)


def test_no_legend_covers_any_series():
    """Measured against the drawn data, not judged by eye, which missed it twice."""
    fig = figures.forecast_comparison({k: panel() for k, _, _ in figures.GAS_PANEL})
    fig.canvas.draw()
    for ax in fig.axes:
        box = ax.get_legend().get_window_extent().transformed(ax.transData.inverted())
        for line in ax.lines:
            x = np.asarray(line.get_xdata(), dtype=float)
            y = np.asarray(line.get_ydata(), dtype=float)
            inside = (x >= box.x0) & (x <= box.x1) & (y >= box.y0) & (y <= box.y1)
            assert not inside.any(), f"the legend covers {line.get_color()}"
    ps.plt.close(fig)


def test_every_panel_carries_the_whole_key():
    """Split across panels, each would have been half a key."""
    fig = figures.forecast_comparison({k: panel() for k, _, _ in figures.GAS_PANEL})
    for ax in fig.axes:
        legend = ax.get_legend()
        assert legend is not None
        labels = [text.get_text() for text in legend.get_texts()]
        assert any("Benchmark" in label for label in labels)
        assert any("Shaded" in label for label in labels)
        for method in figures.BENCHMARK_STYLE:
            assert figures.BENCHMARK_LABEL[method] in labels
    ps.plt.close(fig)


def test_the_benchmarks_are_named_by_what_they_do():
    """A reader meeting "persistence" or "seasonal naive" learns nothing."""
    for label in figures.BENCHMARK_LABEL.values():
        assert "naive" not in label.lower()
        assert "persistence" not in label.lower()
        assert "climatology" not in label.lower()


def test_the_horizons_are_evenly_spaced_and_no_tick_is_invented():
    """At true positions the step from six to twelve is twice the step before it."""
    fig = figures.forecast_comparison({k: panel() for k, _, _ in figures.GAS_PANEL})
    for ax in fig.axes:
        ticks = ax.get_xticks()
        assert list(np.diff(ticks)) == [1.0] * (len(ticks) - 1)
        assert [t.get_text() for t in ax.get_xticklabels()] == ["1", "3", "6", "12"]
    ps.plt.close(fig)


def test_the_annotation_reaches_its_target_without_crossing_a_series():
    """An earlier anchor at six months put the arrow through the seasonal line.

    Read from the scored forecasts, because whether an arrow clears a curve is a
    property of the real geometry and a synthetic frame would not test it.
    """
    tables = {key: real_panel(key) for key, _, _ in figures.GAS_PANEL}
    fig = figures.forecast_comparison(tables)
    for ax, key in zip(fig.axes, [k for k, _, _ in figures.GAS_PANEL]):
        note = next(a for a in ax.texts if "above the band" in a.get_text())
        (x0, y0), (x1, y1) = note.get_position(), note.xy
        xs = np.linspace(x0, x1, 80)
        ys = np.interp(xs, [x0, x1], [y0, y1])
        low, high = ax.get_ylim()
        positions = np.arange(len(tables[key]), dtype=float)
        for name in ("climatology", "seasonal naive", "fitted_low"):
            series = np.interp(xs, positions, tables[key][name].to_numpy())
            assert np.all(np.abs(series - ys) > 0.004 * (high - low)), name
    ps.plt.close(fig)


def test_the_panel_name_is_larger_than_a_legend_entry():
    """It is the primary distinction between the panels."""
    fig = figures.forecast_comparison({k: panel() for k, _, _ in figures.GAS_PANEL})
    for ax in fig.axes:
        name = next(a for a in ax.texts if "Methane" in a.get_text()
                    or "Carbon dioxide" in a.get_text())
        assert name.get_fontsize() > ps.LEGEND_SIZE
    ps.plt.close(fig)


def test_the_subtitle_quotes_the_persistence_values_the_data_holds():
    """The subtitle states what the panel no longer draws, so it has to be checked.

    This is the one test here that reads the scored forecasts rather than a
    synthetic frame, because that is the thing being checked.
    """
    table = real_panel("methane")
    said = figures.FORECAST_TEXT.subtitle
    at_one = table.loc[table["horizon"] == 1, "naive"].iloc[0]
    at_six = table.loc[table["horizon"] == PERSISTENCE_LAST, "naive"].iloc[0]
    assert f"{at_one:.1f}" in said, f"subtitle should quote {at_one:.1f}"
    assert f"{at_six:.1f}" in said, f"subtitle should quote {at_six:.1f}"


# --- the palette ------------------------------------------------------------


def _lab(hex_colour: str) -> np.ndarray:
    rgb = np.array([int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    matrix = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722],
                       [0.0193, 0.1192, 0.9505]])
    xyz = (matrix @ lin) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def _simulate(hex_colour: str, kind: str) -> str:
    rgb = np.array([int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    lms = np.array([[17.8824, 43.5161, 4.11935], [3.45565, 27.1554, 3.86714],
                    [0.0299566, 0.184309, 1.46709]])
    sim = {"deuteranopia": np.array([[1, 0, 0], [0.494207, 0, 1.24827], [0, 0, 1]]),
           "protanopia": np.array([[0, 2.02344, -2.52581], [0, 1, 0], [0, 0, 1]]),
           "tritanopia": np.array([[1, 0, 0], [0, 1, 0], [-0.395913, 0.801109, 0]])}[kind]
    out = np.linalg.inv(lms) @ (sim @ (lms @ lin))
    out = np.clip(out, 0, 1)
    srgb = np.where(out <= 0.0031308, out * 12.92, 1.055 * out ** (1 / 2.4) - 0.055)
    return "#" + "".join(f"{int(round(v * 255)):02X}" for v in np.clip(srgb, 0, 1))


#: Two colors become distinguishable at about this CIE 1976 difference.
NOTICEABLE = 2.3


@pytest.mark.parametrize("other", [ps.INSIDE, ps.OUTSIDE, ps.BOUNDARY,
                                   "#1A1A1A", "#767676", "#A9A9A9"])
def test_the_fitted_hue_is_clear_of_every_other_ink_under_deficiency(other):
    """Reddish purple failed this at 0.9 against OUTSIDE under tritanopia."""
    for kind in ("deuteranopia", "protanopia", "tritanopia"):
        difference = np.linalg.norm(
            _lab(_simulate(ps.FITTED, kind)) - _lab(_simulate(other, kind)))
        assert difference > 4 * NOTICEABLE, f"{ps.FITTED} against {other} under {kind}"


def test_the_two_filled_regions_separate_in_grayscale_as_well_as_in_hue():
    """A reader without color must still tell the envelope from the band."""
    blended = np.array([int(ps.FITTED[i:i + 2], 16) / 255 for i in (1, 3, 5)]) * ps.FITTED_FILL_ALPHA \
        + np.ones(3) * (1 - ps.FITTED_FILL_ALPHA)
    band = np.array([int(ps.NOT_DISTINGUISHABLE[i:i + 2], 16) / 255 for i in (1, 3, 5)])

    def luminance(rgb):
        lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
        return float(np.dot(lin, [0.2126, 0.7152, 0.0722]))

    assert abs(luminance(blended) - luminance(band)) > 0.10
    assert luminance(blended) < luminance(band), "the subject must be darker than the apparatus"
