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


def test_persistence_stops_before_it_would_coincide_with_seasonal_naive():
    """Drawn to twelve it would appear to recover, which is an artifact."""
    fig = figures.forecast_comparison({k: panel() for k, _, _ in figures.GAS_PANEL})
    ax = fig.axes[0]
    # Matplotlib normalizes a dash tuple, so the line is found by its ink instead.
    colour = figures.BENCHMARK_STYLE["naive"]["color"]
    drawn = [l for l in ax.lines if l.get_color() == colour]
    assert drawn, "persistence was not drawn"
    assert max(drawn[0].get_xdata()) == figures.PERSISTENCE_LAST_HORIZON
    others = [l for l in ax.lines
              if l.get_color() == figures.BENCHMARK_STYLE["climatology"]["color"]]
    assert max(others[0].get_xdata()) == 12, "the other benchmarks run the full range"
    ps.plt.close(fig)


def test_the_two_panels_do_not_share_a_scale():
    """The gases are in different units and must not invite comparison by height."""
    tables = {k: panel() for k, _, _ in figures.GAS_PANEL}
    tables["carbon_dioxide"] = tables["carbon_dioxide"] * 0.01
    tables["carbon_dioxide"]["horizon"] = list(HORIZONS)
    fig = figures.forecast_comparison(tables)
    assert fig.axes[0].get_ylim() != fig.axes[1].get_ylim()
    ps.plt.close(fig)


def test_neither_legend_covers_any_series():
    fig = figures.forecast_comparison({k: panel() for k, _, _ in figures.GAS_PANEL})
    fig.canvas.draw()
    for ax in fig.axes:
        legend = ax.get_legend()
        assert legend is not None
        box = legend.get_window_extent().transformed(ax.transData.inverted())
        lowest = min(line.get_ydata().min() for line in ax.lines if len(line.get_ydata()))
        assert box.y1 < lowest, "the legend reaches into the drawn series"
    ps.plt.close(fig)


def test_both_legends_are_drawn_one_for_methods_and_one_for_regions():
    fig = figures.forecast_comparison({k: panel() for k, _, _ in figures.GAS_PANEL})
    titles = [ax.get_legend().get_title().get_text() for ax in fig.axes]
    assert set(titles) == {"Methods", "Regions"}
    ps.plt.close(fig)


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
