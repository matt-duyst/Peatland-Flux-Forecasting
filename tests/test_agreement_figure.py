"""Predicted against measured: what the marks are, and what may not be inferred."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures
from study import plotstyle as ps

METHODS = ("ordinary least squares", "ridge", "random forest", "gradient boosting")


def synthetic(months: int = 48, seed: int = 0) -> dict[str, pd.DataFrame]:
    """Scored forecasts shaped like the real ones: two fitted families and the
    benchmarks, every method scoring every month at every horizon."""
    rng = np.random.default_rng(seed)
    targets = pd.period_range("2015-01", periods=months, freq="M")
    actual = pd.Series(40 + 25 * np.sin(2 * np.pi * targets.month / 12)
                       + rng.normal(0, 6, months), index=targets)
    frames = {}
    for family in ("autoregressive", "exogenous", "benchmarks"):
        methods = METHODS if family != "benchmarks" else ("climatology", "naive")
        rows = []
        for horizon in (1, 3):
            for method in methods:
                for target in targets:
                    rows.append({"origin": target - horizon, "target": target,
                                 "horizon": horizon, "method": method,
                                 "actual": float(actual[target]),
                                 "forecast": float(actual[target]) + rng.normal(0, 5),
                                 "error": 0.0, "mase_scale": 1.0})
        frames[family] = pd.DataFrame(rows)
    return frames


def panels() -> dict[str, pd.DataFrame]:
    return {key: figures.agreement_panel(synthetic(seed=index))
            for index, (key, _, _) in enumerate(figures.GAS_PANEL)}


def gas_panels(fig):
    """The two square panels, which the key's own axes sits below."""
    return fig.axes[:len(figures.GAS_PANEL)]


# --- what the panel is built from ---------------------------------------------


def test_the_range_spans_every_fitted_method_and_names_none():
    """The study's result is that they do not separate, and a panel that let a
    reader pick one out would invite the ranking it denies."""
    panel = figures.agreement_panel(synthetic())
    assert (panel["lowest"] <= panel["middle"]).all()
    assert (panel["middle"] <= panel["highest"]).all()
    assert set(panel.columns) == {"measured", "lowest", "highest", "middle", "seasonal"}


def test_only_the_months_every_method_scored_are_drawn():
    """Scoring each method on whatever months it reached would advantage the one
    asked the easiest question."""
    frames = synthetic()
    frames["exogenous"] = frames["exogenous"][
        frames["exogenous"]["target"] > pd.Period("2015-06", freq="M")]
    panel = figures.agreement_panel(frames)
    assert panel.index.min() == pd.Period("2015-07", freq="M")


def test_one_horizon_is_drawn_and_it_is_the_nearest():
    """The horizon most favorable to the fitted methods, so falling short of the
    seasonal average there says more than doing so a year out."""
    assert figures.AGREEMENT_HORIZON == 1
    panel = figures.agreement_panel(synthetic())
    assert len(panel) == 48


def test_the_four_numbers_are_properties_of_the_whole_cloud():
    panel = figures.agreement_panel(synthetic())
    assert panel.attrs["mean_miss"] > 0
    assert panel.attrs["root_mean_square"] >= panel.attrs["mean_miss"]
    assert 0.0 <= panel.attrs["brackets"] <= 1.0
    assert 0.0 <= panel.attrs["same_way"] <= 1.0
    assert "coefficient of determination" not in panel.attrs


def test_the_seasonal_average_is_the_only_benchmark_kept():
    """It is the one that beats the fitted methods; the other three are on the
    forecast comparison."""
    panel = figures.agreement_panel(synthetic())
    assert panel["seasonal"].notna().all()


# --- what is drawn ------------------------------------------------------------


def test_each_panel_is_square_and_its_axes_run_together():
    """On a one-to-one plot the diagonal has to sit at 45 degrees, or distance
    from it cannot be read."""
    fig = figures.predicted_against_measured(panels())
    width_px, height_px = ps.SIZES["square pair"]
    for ax in gas_panels(fig):
        box = ax.get_position()
        assert box.width * width_px == pytest.approx(box.height * height_px, rel=0.01)
        assert ax.get_xlim() == pytest.approx(ax.get_ylim())
    ps.plt.close(fig)


def test_the_gases_never_share_a_scale():
    """Different units, and one of them crosses zero."""
    fig = figures.predicted_against_measured(panels())
    left, right = gas_panels(fig)
    assert left.get_xlim() != right.get_xlim()
    ps.plt.close(fig)


def test_the_diagonal_is_named_rather_than_called_a_target():
    """The seasonal average does not sit on it either, so nothing here is being
    held to it."""
    said = figures.AGREEMENT_TEXT.subtitle
    assert "where a prediction equals the measurement" in said
    assert "nothing here is required to reach it" in said
    for word in ("perfect", "target", "ideal"):
        assert word not in said.lower()


def test_every_month_of_the_marked_year_is_set_apart_by_shape_and_weight():
    """A single callout cannot say that the rest of the year is scattered
    elsewhere on the panel, and a recolored year would make hue mean the mark and
    the year at once."""
    from matplotlib.colors import to_rgb

    built = panels()
    fig = figures.predicted_against_measured(built)
    for ax, key in zip(gas_panels(fig), [key for key, _, _ in figures.GAS_PANEL]):
        weights = {round(collection.get_linewidth()[0], 2)
                   for collection in ax.collections}
        assert len(weights) == 2
        rings = [line for line in ax.lines if line.get_marker() == "o"]
        assert len(rings) == 1
        marked = built[key].index.year == figures.MARKED_YEAR
        assert len(rings[0].get_xdata()) == int(marked.sum())
        assert rings[0].get_markerfacecolor() == "none"
        assert to_rgb(rings[0].get_markeredgecolor()) == to_rgb(ps.FITTED)
    ps.plt.close(fig)


def test_the_key_names_every_mark_on_the_panel():
    """A reader meeting green bars and black dashes with nothing to read them by
    has to go to the subtitle, and a figure that must be read before it can be
    looked at has failed."""
    fig = figures.predicted_against_measured(panels())
    keys = [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    assert len(keys) == 1
    labels = [text.get_text() for text in keys[0].get_texts()]
    for entry in figures.AGREEMENT_KEYS:
        assert entry in labels
    assert sum(label.startswith("$") for label in labels) == 2      # two headings
    assert keys[0].axes not in gas_panels(fig)                      # clear of data
    ps.plt.close(fig)


def test_no_method_is_identifiable_on_the_panel():
    fig = figures.predicted_against_measured(panels())
    drawn = " ".join(note.get_text() for ax in fig.axes for note in ax.texts).lower()
    key = " ".join(figures.AGREEMENT_KEYS).lower()
    for method in METHODS + ("ridge", "forest", "boosting"):
        assert method not in drawn and method not in key
    ps.plt.close(fig)


def test_both_axes_of_both_panels_are_named_with_their_units():
    fig = figures.predicted_against_measured(panels())
    for ax, (_, _, unit) in zip(gas_panels(fig), figures.GAS_PANEL):
        assert unit in ax.get_xlabel() and figures.AGREEMENT_MEASURED in ax.get_xlabel()
        assert unit in ax.get_ylabel() and figures.AGREEMENT_PREDICTED in ax.get_ylabel()
    ps.plt.close(fig)


def test_the_panel_keeps_the_two_error_numbers_and_not_the_two_shares():
    """A magnitude is worth having while looking at a point. The shares are
    statements about the whole cloud and read as well in the description, where
    they are not competing with the marks."""
    fig = figures.predicted_against_measured(panels())
    for ax in gas_panels(fig):
        block = next(note.get_text() for note in ax.texts
                     if "average miss" in note.get_text())
        assert "All eight fitted methods together" in block
        assert "root mean square" in block
        assert "%" not in block
        assert len(block.splitlines()) == 2
    ps.plt.close(fig)


# --- what the words carry -----------------------------------------------------


def test_the_description_says_what_the_gap_between_the_two_errors_means():
    said = figures.AGREEMENT_TEXT.description
    assert "weights large misses more heavily" in said
    assert "a few big errors carry the total" in said


def test_the_description_states_the_two_shares_and_what_they_mean():
    said = figures.AGREEMENT_TEXT.description
    assert "30%" in said and "11%" in said
    assert "75%" in said and "87%" in said
    assert "agree with each other and" in said


def test_the_slope_is_a_clause_rather_than_a_number_on_the_panel():
    """It is a diagnostic of shape, not a performance measure: at 1.07 and 0.94 it
    rules out compression toward the middle, which no error metric states."""
    assert "not compressed toward the middle" in figures.AGREEMENT_TEXT.description
    fig = figures.predicted_against_measured(panels())
    drawn = " ".join(note.get_text() for ax in gas_panels(fig) for note in ax.texts)
    assert "slope" not in drawn.lower()
    ps.plt.close(fig)


def test_no_coefficient_of_determination_appears():
    """It inflates on a strongly seasonal series: predicting the seasonal mean
    alone would score well while adding nothing."""
    text = figures.AGREEMENT_TEXT
    said = " ".join([text.title, text.subtitle, text.description]).lower()
    for term in ("r2", "r²", "coefficient of determination", "variance explained"):
        assert term not in said


def test_the_description_states_the_over_and_under_pattern_the_panel_shows():
    """It is the clearest statement of the finding available and it was buried
    behind the 2015 sentence."""
    said = figures.AGREEMENT_TEXT.description
    assert "above the line at low measured values and below it at high ones" in said
    assert "too much predicted in the weak months and too little in the strong" in said


def test_the_marked_year_claim_is_year_level_and_methane_only():
    """Pooled, over-prediction is a coin flip at 31 of 57 methane months and 41 of
    85 carbon dioxide. The structure is real but it is a property of one year on
    one gas."""
    said = figures.AGREEMENT_TEXT.description
    assert "Methane's 2015" in said
    assert "carbon dioxide's is not" in said
    for phrase in ("always", "almost always", "systematically"):
        assert phrase not in said.lower()
