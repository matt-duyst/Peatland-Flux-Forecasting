"""The forecast comparison: its panel data, its encodings, and its clearances.

The panel data is built from small synthetic frames so the suite stays offline.
The palette check is arithmetic on the constants and reads nothing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from matplotlib.lines import Line2D

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
        "benchmarks": ("climatology", "seasonal naive", "naive",
                       "seasonal naive with drift"),
        "autoregressive": ("ridge", "random forest"),
        "exogenous": ("ridge", "random forest"),
    }
    for family, methods in families.items():
        for method in methods:
            scale = {"climatology": 1.0, "seasonal naive": 1.4, "naive": 1.2,
                     "seasonal naive with drift": 1.45}.get(method, 1.1)
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
    for column in ("climatology", "seasonal naive", "naive",
                   "seasonal naive with drift", "fitted_low",
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
    fig = figures.forecast_error_by_horizon(tables)
    for ax in fig.axes:
        assert len([line for line in ax.lines if line.get_linestyle() != "None"]) == 4
    ps.plt.close(fig)


def test_both_scales_are_linear():
    """A logarithmic scale made the carbon dioxide comparison unreadable."""
    fig = figures.forecast_error_by_horizon({k: panel() for k, _, _ in figures.GAS_PANEL})
    for ax in fig.axes:
        assert ax.get_yscale() == "linear"
    ps.plt.close(fig)


def test_each_panel_spans_what_its_series_occupy():
    """The axis is set from the data, not padded out to a shared round number."""
    tables = {k: panel() for k, _, _ in figures.GAS_PANEL}
    fig = figures.forecast_error_by_horizon(tables)
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
    fig = figures.forecast_error_by_horizon(tables)
    assert fig.axes[0].get_ylim() != fig.axes[1].get_ylim()
    ps.plt.close(fig)


def test_no_legend_covers_any_series():
    """Measured against the drawn data, not judged by eye, which missed it twice."""
    fig = figures.forecast_error_by_horizon({k: panel() for k, _, _ in figures.GAS_PANEL})
    fig.canvas.draw()
    for ax in fig.axes:
        box = ax.get_legend().get_window_extent().transformed(ax.transData.inverted())
        for line in ax.lines:
            x = np.asarray(line.get_xdata(), dtype=float)
            y = np.asarray(line.get_ydata(), dtype=float)
            inside = (x >= box.x0) & (x <= box.x1) & (y >= box.y0) & (y <= box.y1)
            assert not inside.any(), f"the legend covers {line.get_color()}"
    ps.plt.close(fig)


def test_the_legend_is_two_columns_with_a_heading_over_each_group():
    fig = figures.forecast_error_by_horizon({k: panel() for k, _, _ in figures.GAS_PANEL})
    for ax in fig.axes:
        legend = ax.get_legend()
        assert legend._ncols == 2
        headings = [t.get_text() for t in legend.get_texts() if t.get_text().startswith("$")]
        assert len(headings) == 2
    # Mathtext cannot underline, so a rule is drawn under each heading instead.
    assert len([a for a in fig.artists if isinstance(a, Line2D)]) == 2 * len(fig.axes)
    ps.plt.close(fig)


def test_every_panel_carries_the_whole_key():
    """Split across panels, each would have been half a key."""
    fig = figures.forecast_error_by_horizon({k: panel() for k, _, _ in figures.GAS_PANEL})
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
    fig = figures.forecast_error_by_horizon({k: panel() for k, _, _ in figures.GAS_PANEL})
    for ax in fig.axes:
        ticks = ax.get_xticks()
        assert list(np.diff(ticks)) == [1.0] * (len(ticks) - 1)
        assert [t.get_text() for t in ax.get_xticklabels()] == ["1", "3", "6", "12"]
    ps.plt.close(fig)


def test_nothing_drawn_over_a_panel_covers_a_series():
    """Legend, panel name and annotation all measured against the drawn data.

    Fixing only the legend once moved a collision onto the annotation rather than
    removing it, so every piece of furniture is checked, not just the one that
    failed last.
    """
    tables = {key: real_panel(key) for key, _, _ in figures.GAS_PANEL}
    fig = figures.forecast_error_by_horizon(tables)
    fig.canvas.draw()
    for ax in fig.axes:
        furniture = [("legend", ax.get_legend())]
        furniture += [(text.get_text()[:18], text) for text in ax.texts]
        for name, artist in furniture:
            box = artist.get_window_extent().transformed(ax.transData.inverted())
            for line in ax.lines:
                x = np.asarray(line.get_xdata(), dtype=float)
                y = np.asarray(line.get_ydata(), dtype=float)
                covered = ((x >= box.x0) & (x <= box.x1)
                           & (y >= box.y0) & (y <= box.y1))
                assert not covered.any(), f"{name} covers a series"
    ps.plt.close(fig)


def test_the_furniture_does_not_overlap_itself():
    fig = figures.forecast_error_by_horizon({k: real_panel(k) for k, _, _ in figures.GAS_PANEL})
    fig.canvas.draw()
    for ax in fig.axes:
        boxes = [ax.get_legend().get_window_extent()]
        boxes += [text.get_window_extent() for text in ax.texts]
        for i, first in enumerate(boxes):
            for second in boxes[i + 1:]:
                apart = (first.x1 <= second.x0 or second.x1 <= first.x0
                         or first.y1 <= second.y0 or second.y1 <= first.y0)
                assert apart, "two pieces of furniture overlap"
    ps.plt.close(fig)


def test_the_panel_name_is_larger_than_a_legend_entry():
    """It is the primary distinction between the panels."""
    fig = figures.forecast_error_by_horizon({k: panel() for k, _, _ in figures.GAS_PANEL})
    for ax in fig.axes:
        name = next(a for a in ax.texts if "Methane" in a.get_text()
                    or "Carbon dioxide" in a.get_text())
        assert name.get_fontsize() > ps.LEGEND_SIZE
    ps.plt.close(fig)


def test_the_figure_does_not_describe_a_series_it_does_not_draw():
    """Persistence is scored and recorded in the notes, not narrated on the panel."""
    words = figures.FORECAST_TEXT.description + figures.FORECAST_TEXT.subtitle
    assert "carrying last month" not in words.lower()
    assert "41.4" not in words


def test_the_units_caveat_names_the_units():
    """An abstract "different units" leaves a reader to work out which."""
    said = figures.FORECAST_TEXT.description
    assert "nanomole" in said and "micromole" in said


def test_no_panel_repeats_what_the_description_says():
    """The note that used to sit in each corner said what the description says
    in nearly the same words, and pointed at one horizon of a finding holding at
    three, so a reader met it twice above the axis and once below."""
    tables = {key: real_panel(key) for key, _, _ in figures.GAS_PANEL}
    fig = figures.forecast_error_by_horizon(tables)
    for ax in fig.axes:
        drawn = " ".join(a.get_text() for a in ax.texts)
        assert "above the band" not in drawn, drawn
    assert "above the band" in figures.FORECAST_TEXT.description
    ps.plt.close(fig)


def test_a_series_peaking_between_plotted_points_is_not_missed():
    """The clearance test reads the series exactly, not at its vertices.

    Between two plotted horizons the series is a straight line, so its highest
    point over an interval is at a vertex inside it or at one of the edges.
    Reading only the vertices misses a climb that starts inside the key's span
    and finishes outside it, which is exactly the shape of methane's envelope
    between six and twelve months: 9.37 rising to 15.06.
    """
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.array([9.98, 11.13, 9.37, 15.06])
    vertices_only = float(y[(x >= 0.4) & (x <= 2.9)].max())
    assert vertices_only == 11.13
    assert figures._highest_between(x, y, 0.4, 2.9) > 14.0
    # and it agrees with the naive reading wherever the edges land on vertices
    assert figures._highest_between(x, y, 0.0, 3.0) == 15.06


def test_the_clearance_test_survives_gaps_and_an_empty_span():
    x = np.array([0.0, 1.0, np.nan, 3.0])
    y = np.array([1.0, 5.0, np.nan, 2.0])
    assert figures._highest_between(x, y, 0.0, 1.0) == 5.0
    assert figures._highest_between(np.array([]), np.array([]), 0.0, 1.0) == -np.inf
    # a span entirely off the left of the series reaches nothing
    assert figures._highest_between(x, y, -5.0, -4.0) == -np.inf


def test_the_legend_keeps_its_clearance_on_both_panels():
    tables = {key: real_panel(key) for key, _, _ in figures.GAS_PANEL}
    fig = figures.forecast_error_by_horizon(tables)
    fig.canvas.draw()
    for ax in fig.axes:
        legend = ax.get_legend().get_window_extent()
        box = legend.transformed(ax.transData.inverted())
        highest = -np.inf
        for line in ax.lines:
            x = np.asarray(line.get_xdata(), dtype=float)
            y = np.asarray(line.get_ydata(), dtype=float)
            under = (x >= box.x0) & (x <= box.x1)
            if under.any():
                highest = max(highest, float(y[under].max()))
        gap = legend.y0 - ax.transData.transform((0, highest))[1]
        assert gap >= figures.LEGEND_CLEARANCE_PX - 1
    ps.plt.close(fig)


# --- the palette ------------------------------------------------------------


def _lab(hex_color: str) -> np.ndarray:
    rgb = np.array([int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    matrix = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722],
                       [0.0193, 0.1192, 0.9505]])
    xyz = (matrix @ lin) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def _simulate(hex_color: str, kind: str) -> str:
    rgb = np.array([int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)])
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


# --- what is drawn against what the rows say --------------------------------
#
# The gap this closes: a check that reads the artifact confirms what was drawn,
# and a check on the numbers confirms the arithmetic, but if they never run in
# one process the first faithfully confirms whatever the second regressed to.
# Everything below recomputes from the scored rows with its own arithmetic and
# then reads the geometry off the artists the production path drew.


def _raw(gas: str) -> dict:
    from ingest import paths

    built = {}
    for family in ("benchmarks", "autoregressive", "exogenous"):
        frame = pd.read_csv(paths.processed_dir() / f"forecasts_{gas}_{family}.csv")
        frame["target"] = pd.PeriodIndex(frame["target"], freq="M")
        built[family] = frame
    return built


def _shared(frames: dict) -> set:
    """Horizon and target pairs every method scored, computed here."""
    sets = []
    for frame in frames.values():
        usable = frame.dropna(subset=["actual", "forecast", "mase_scale"])
        methods = usable["method"].nunique()
        counts = usable.groupby(["horizon", "target"])["method"].nunique()
        sets.append({pair for pair, n in counts.items() if n == methods})
    return set.intersection(*sets)


def _errors(frames: dict, keys: set, horizon: int) -> dict:
    """One error series per family and method. Keyed on both, never on method
    alone: the two families run the same four method names, so pivoting on the
    name averages each method's two predictions and halves the envelope."""
    out = {}
    for family, frame in frames.items():
        pairs = list(zip(frame["horizon"], frame["target"]))
        block = frame[[p in keys for p in pairs]]
        block = block[block["horizon"] == horizon]
        for method, group in block.groupby("method"):
            out[f"{family}/{method}"] = group.set_index("target")["error"]
    return out


def _margin(best: pd.Series, base: pd.Series, horizon: int, alpha: float = 0.05) -> float:
    """Diebold-Mariano margin with the Harvey correction, written out here."""
    from scipy import stats as st

    pair = pd.concat([best.rename("a"), base.rename("b")], axis=1).dropna()
    n = len(pair)
    d = (pair["a"].abs() - pair["b"].abs()).to_numpy()
    lag = max(horizon - 1, int(np.floor(4 * (n / 100) ** (2 / 9))))
    centred = d - d.mean()
    variance = float(centred @ centred / n)
    for k in range(1, lag + 1):
        variance += 2 * (1 - k / (lag + 1)) * float(centred[k:] @ centred[:-k] / n)
    variance = max(variance, 1e-12)
    harvey = np.sqrt(max((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n, 1e-12))
    return float(st.t.isf(alpha / 2, n - 1) * np.sqrt(variance / n) / harvey)


def _expected(gas: str) -> pd.DataFrame:
    frames = _raw(gas)
    keys = _shared(frames)
    rows = []
    for horizon in HORIZONS:
        errors = _errors(frames, keys, horizon)
        mae = {k: float(v.abs().mean()) for k, v in errors.items()}
        fitted = {k: v for k, v in mae.items() if not k.startswith("benchmarks/")}
        best = min(fitted, key=fitted.get)
        rows.append({
            "climatology": mae["benchmarks/climatology"],
            "seasonal naive": mae["benchmarks/seasonal naive"],
            "low": min(fitted.values()),
            "high": max(fitted.values()),
            "n_fitted": len(fitted),
            "margin": _margin(errors[best], errors["benchmarks/climatology"], horizon),
        })
    return pd.DataFrame(rows)


def _drawn(ax) -> dict:
    """Geometry read off the artists rather than off the table behind them."""
    import matplotlib.colors as mc

    out = {"edges": []}
    for line in ax.lines:
        colour, width = line.get_color(), line.get_linewidth()
        y = np.asarray(line.get_ydata(), dtype=float)
        if colour == figures.BENCHMARK_STYLE["climatology"]["color"] and width > 2.0:
            out["climatology"] = y
        elif colour == figures.BENCHMARK_STYLE["seasonal naive"]["color"]:
            out["seasonal naive"] = y
        elif colour == ps.FITTED:
            out["edges"].append(y)
    for coll in ax.collections:
        paths = coll.get_paths()
        if not paths:
            continue
        vertices = paths[0].vertices
        low, high = [], []
        for position in range(len(HORIZONS)):
            ys = vertices[np.abs(vertices[:, 0] - position) < 1e-9][:, 1]
            low.append(float(ys.min()))
            high.append(float(ys.max()))
        name = "band" if np.allclose(coll.get_facecolor()[0][:3],
                                     mc.to_rgb(ps.NOT_DISTINGUISHABLE)) else "fill"
        out[name] = (np.array(low), np.array(high))
    out["edges"].sort(key=lambda a: a.mean())
    return out


@pytest.mark.parametrize("gas", [key for key, _, _ in figures.GAS_PANEL])
def test_every_drawn_value_matches_a_fresh_recomputation(gas):
    panels = {k: figures.forecast_panel(_raw(k), HORIZONS)
              for k, _, _ in figures.GAS_PANEL}
    fig = figures.forecast_error_by_horizon(panels)
    fig.canvas.draw()
    index = [k for k, _, _ in figures.GAS_PANEL].index(gas)
    got, want = _drawn(fig.axes[index]), _expected(gas)

    assert set(want["n_fitted"]) == {8}, "the envelope spans eight fitted models"
    for name in ("climatology", "seasonal naive"):
        assert np.allclose(got[name], want[name].to_numpy(), rtol=0, atol=1e-9), name
    assert np.allclose(got["edges"][0], want["low"].to_numpy(), rtol=0, atol=1e-9)
    assert np.allclose(got["edges"][1], want["high"].to_numpy(), rtol=0, atol=1e-9)
    assert np.allclose(got["fill"][0], want["low"].to_numpy(), rtol=0, atol=1e-9)
    assert np.allclose(got["fill"][1], want["high"].to_numpy(), rtol=0, atol=1e-9)
    assert np.allclose(got["band"][0], (want["climatology"] - want["margin"]).to_numpy(),
                       rtol=0, atol=1e-9)
    assert np.allclose(got["band"][1], (want["climatology"] + want["margin"]).to_numpy(),
                       rtol=0, atol=1e-9)
    ps.plt.close(fig)


@pytest.mark.parametrize("gas", [key for key, _, _ in figures.GAS_PANEL])
def test_every_method_is_scored_on_identical_months(gas):
    frames = _raw(gas)
    keys = _shared(frames)
    for frame in frames.values():
        pairs = list(zip(frame["horizon"], frame["target"]))
        block = frame[[p in keys for p in pairs]]
        counts = block.groupby(["method", "horizon"]).size().unstack()
        assert (counts.nunique(axis=0) == 1).all(), \
            "methods differ in how many months they were scored on"
