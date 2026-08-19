"""Observed against predicted: the panel data, the two fills, and the furniture.

The synthetic frames are built here so the suite stays offline. The few checks
that depend on real geometry, or on a number the figure states, read the
committed series, as the site-map and forecast figures already do.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures
from study import plotstyle as ps

HORIZONS = (1, 3, 6, 12)


def observed(n: int = 60, start: str = "2012-01") -> pd.DataFrame:
    months = pd.period_range(start, periods=n, freq="M")
    rng = np.random.default_rng(0)
    season = 20 + 15 * np.sin(2 * np.pi * months.month / 12)
    return pd.DataFrame({"observed": season + rng.normal(0, 2, n),
                         "se": rng.uniform(0.5, 2.0, n)}, index=months)


def forecast_frames(target_months: pd.PeriodIndex) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(1)
    families = {"benchmarks": ("climatology", "seasonal naive"),
                "autoregressive": ("ridge", "random forest"),
                "exogenous": ("ridge", "random forest")}
    rows = []
    for family, methods in families.items():
        for method in methods:
            for horizon in HORIZONS:
                for month in target_months:
                    rows.append({"family": family, "method": method, "horizon": horizon,
                                 "origin": month - horizon, "target": month,
                                 "forecast": 20 + rng.normal(0, 3),
                                 "error": rng.normal(0, 3), "actual": 20.0,
                                 "mase_scale": 1.0})
    frame = pd.DataFrame(rows)
    return {f: frame[frame["family"] == f].drop(columns="family").copy() for f in families}


def panel() -> pd.DataFrame:
    obs = observed()
    return figures.flux_panel(obs, forecast_frames(obs.index[24:48]))


def real_panels() -> dict[str, pd.DataFrame]:
    from ingest import paths

    out = {}
    for gas, (filename, column, error) in figures.GAS_OBSERVED.items():
        frame = pd.read_csv(paths.processed_dir() / filename)
        frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
        obs = frame.set_index("month")[[column, error]].rename(
            columns={column: "observed", error: "se"})
        built = {}
        for family in ("benchmarks", "autoregressive", "exogenous"):
            forecasts = pd.read_csv(paths.processed_dir() / f"forecasts_{gas}_{family}.csv")
            forecasts["target"] = pd.PeriodIndex(forecasts["target"], freq="M")
            built[family] = forecasts
        out[gas] = figures.flux_panel(obs, built)
    return out


# --- the panel data ---------------------------------------------------------


def test_the_whole_observed_record_is_kept_not_only_the_evaluated_months():
    """The gap is the point: it shows how much was never forecast."""
    table = panel()
    assert len(table) == 60
    assert table["climatology"].isna().sum() > 0


def test_predictions_appear_only_where_they_were_made():
    table = panel()
    predicted = table.index[table["climatology"].notna()]
    assert predicted.min() >= table.index[24]
    assert predicted.max() <= table.index[47]


def test_the_fitted_range_brackets_every_fitted_model_and_excludes_the_benchmarks():
    table = panel().dropna(subset=["fitted_low"])
    assert len(table) > 0
    assert (table["fitted_low"] <= table["fitted_high"]).all()
    # A benchmark inside the range would mean the range was built from the wrong set.
    assert not table["climatology"].between(table["fitted_low"], table["fitted_high"]).all()


def test_the_evaluated_share_of_each_record_is_what_the_figure_says():
    """The panel note claims 40% of methane months and 44% of carbon dioxide."""
    shares = {gas: table["climatology"].notna().mean() for gas, table in real_panels().items()}
    assert shares["methane"] == pytest.approx(0.40, abs=0.01)
    assert shares["carbon_dioxide"] == pytest.approx(0.44, abs=0.01)


def test_the_count_of_months_below_every_prediction_is_what_the_description_says():
    """Twelve of fifty-seven, stated on the figure, checked against the series."""
    table = real_panels()["methane"].dropna(subset=["climatology"])
    assert len(table) == 57
    below_fitted = int((table["observed"] < table["fitted_low"]).sum())
    below_all = int((table["observed"]
                     < np.minimum(table["fitted_low"], table["climatology"])).sum())
    # The two counts differ, and an earlier draft stated the first against the
    # second: twelve months fall below every fitted model, nine below all nine.
    assert (below_fitted, below_all) == (12, 9)
    said = figures.FLUX_TEXT.description
    assert "12 of the 57" in said and "every fitted model" in said
    assert "nine of those" in said


def test_2021_lies_outside_the_evaluated_window_on_methane():
    """The weakest summer in the record was never forecast, and the figure says so."""
    table = real_panels()["methane"]
    evaluated = table.index[table["climatology"].notna()]
    assert not any(month.year == 2021 for month in evaluated)
    assert any(month.year == 2021 for month in table.index)
    assert "2021" in figures.FLUX_TEXT.description


def test_the_models_disagree_less_than_the_observation_is_known_on_carbon_dioxide():
    """The second panel's reason for existing, checked rather than asserted."""
    ratios = {}
    for gas, table in real_panels().items():
        scored = table.dropna(subset=["climatology"])
        spread = (scored["fitted_high"] - scored["fitted_low"]).mean()
        known = (2 * figures.OBSERVED_BAND_SIGMAS * scored["se"]).mean() / 2
        ratios[gas] = spread / known
    assert ratios["carbon_dioxide"] < 0.5
    assert ratios["methane"] > 3.0


# --- what the panel draws ---------------------------------------------------


def test_both_panels_share_one_time_axis():
    """A year must sit at the same place in each, or the eye misreads the timing."""
    fig = figures.observed_and_predicted(real_panels())
    assert fig.axes[0].get_xlim() == fig.axes[1].get_xlim()
    ps.plt.close(fig)


def test_the_axis_is_set_to_what_the_data_occupies():
    fig = figures.observed_and_predicted(real_panels())
    tables = real_panels()
    for ax, key in zip(fig.axes, [k for k, _, _ in figures.GAS_PANEL]):
        table = tables[key]
        low, high = ax.get_ylim()
        drawn = np.nanmax(np.fmax(
            (table["observed"] + figures.OBSERVED_BAND_SIGMAS * table["se"]).to_numpy(),
            table["fitted_high"].to_numpy()))
        assert (drawn - low) / (high - low) > 0.7, "too much empty axis above the data"
    ps.plt.close(fig)


def test_no_legend_or_panel_name_covers_the_series():
    import matplotlib.dates as mdates

    tables = real_panels()
    fig = figures.observed_and_predicted(tables)
    fig.canvas.draw()
    for ax, key in zip(fig.axes, [k for k, _, _ in figures.GAS_PANEL]):
        table = tables[key]
        positions = mdates.date2num(table.index.to_timestamp())
        ceiling = np.fmax(
            (table["observed"] + figures.OBSERVED_BAND_SIGMAS * table["se"]).to_numpy(),
            table["fitted_high"].to_numpy())
        for artist in [ax.get_legend(), *ax.texts]:
            box = artist.get_window_extent().transformed(ax.transData.inverted())
            under = (positions >= box.x0) & (positions <= box.x1)
            if not under.any():
                continue
            assert box.y0 > np.nanmax(ceiling[under]), "furniture over the series"
    ps.plt.close(fig)


def test_the_legend_and_the_panel_name_take_opposite_corners():
    fig = figures.observed_and_predicted(real_panels())
    fig.canvas.draw()
    for ax in fig.axes:
        legend = ax.get_legend().get_window_extent()
        name = next(a.get_window_extent() for a in ax.texts
                    if a.get_text() in ("Methane", "Carbon dioxide"))
        assert legend.x1 <= name.x0 or name.x1 <= legend.x0
    ps.plt.close(fig)


def test_the_figure_carries_no_score():
    """A number on the panel would read as a verdict the evidence does not support."""
    fig = figures.observed_and_predicted(real_panels())
    for ax in fig.axes:
        for text in ax.texts:
            assert not any(token in text.get_text().lower()
                           for token in ("mae", "rmse", "error =", "r2", "p ="))
    ps.plt.close(fig)


# --- the two fills ----------------------------------------------------------


def _luminance(rgb: np.ndarray) -> float:
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return float(np.dot(linear, [0.2126, 0.7152, 0.0722]))


def _hex_to_rgb(value: str) -> np.ndarray:
    return np.array([int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)])


def _over(color: str, alpha: float, base: np.ndarray | None = None) -> np.ndarray:
    ground = np.ones(3) if base is None else base
    return _hex_to_rgb(color) * alpha + ground * (1 - alpha)


def test_the_observed_band_and_the_fitted_band_separate_in_grayscale():
    """They overlap substantially on carbon dioxide, so hue alone will not do."""
    grey = _over(ps.INK, ps.OBSERVED_BAND_ALPHA)
    blue = _over(ps.FITTED, ps.FITTED_FILL_ALPHA)
    assert abs(_luminance(grey) - _luminance(blue)) > 0.10


def test_where_the_two_bands_overlap_the_result_is_distinct_from_each():
    grey = _over(ps.INK, ps.OBSERVED_BAND_ALPHA)
    blue = _over(ps.FITTED, ps.FITTED_FILL_ALPHA)
    both = _over(ps.FITTED, ps.FITTED_FILL_ALPHA, base=grey)
    for other in (grey, blue):
        assert np.linalg.norm(both - other) > 0.04


def test_both_legends_sit_on_the_same_side():
    """A legend that moves between panels makes the eye relocate."""
    fig = figures.observed_and_predicted(real_panels())
    fig.canvas.draw()
    corners = set()
    for ax in fig.axes:
        box = ax.get_legend().get_window_extent().transformed(ax.transAxes.inverted())
        corners.add(round((box.x0 + box.x1) / 2) )
    assert len(corners) == 1
    ps.plt.close(fig)


def test_the_year_ticks_are_evenly_spaced_and_reach_the_end_of_the_axis():
    import matplotlib.dates as mdates

    fig = figures.observed_and_predicted(real_panels())
    for ax in fig.axes:
        years = [mdates.num2date(t).year for t in ax.get_xticks()]
        gaps = {b - a for a, b in zip(years, years[1:])}
        assert len(gaps) == 1, f"uneven year gaps: {years}"
        assert years[-1] == mdates.num2date(ax.get_xlim()[1]).year
        assert len(ax.xaxis.get_minor_locator()() ) > len(years), "annual minors missing"
    ps.plt.close(fig)


def test_the_legend_names_what_the_band_is_not_what_it_is_for():
    fig = figures.observed_and_predicted(real_panels())
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert "Two standard errors on that mean" in labels
    assert "Highest and lowest of the eight fitted models" in labels
    assert not any("precisely" in label for label in labels)
    ps.plt.close(fig)


def test_the_eight_are_called_models_wherever_they_are_named():
    """Four methods, each run two ways, are eight models.

    "Four fitted methods" naming the four algorithms is the one correct use of the
    word and is left alone; what is forbidden is calling the eight fitted things
    methods.
    """
    for text in (figures.FLUX_TEXT, figures.FORECAST_TEXT):
        words = text.subtitle + text.description
        assert "eight fitted methods" not in words
        assert "fitted method disagrees" not in words
    fig = figures.observed_and_predicted(real_panels())
    for ax in fig.axes:
        for label in (t.get_text() for t in ax.get_legend().get_texts()):
            assert "fitted methods" not in label
    ps.plt.close(fig)
