"""Measurements used: the panel data, the two results it must carry, the bars."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import figures
from study import plotstyle as ps

HORIZONS = (1, 3, 6, 12)


def synthetic() -> tuple[pd.DataFrame, pd.DataFrame, pd.PeriodIndex]:
    months = pd.period_range("2012-01", periods=72, freq="M")
    rng = np.random.default_rng(0)
    season = np.sin(2 * np.pi * months.month / 12)
    covariates = pd.DataFrame(
        {"soil_temp_f": 40 + 20 * season + rng.normal(0, 0.6, 72),
         "atm_temp_f": 38 + 22 * season + rng.normal(0, 0.6, 72),
         "precip_in": 0.2 + 0.1 * season + rng.normal(0, 0.08, 72),
         "wte_m": 413 + rng.normal(0, 0.1, 72)},
        index=months,
    )
    rows = []
    for horizon in HORIZONS:
        for predictor, share in (("flux_lag1", 1.0), ("flux_lag12", 0.5),
                                 ("soil_temp_f_lag1", 0.9), ("wte_m_lag1", 0.1)):
            for origin in months[:20]:
                rows.append({"origin": origin, "target": origin + horizon,
                             "horizon": horizon, "method": "ridge",
                             "predictors": ", ".join(
                                 ["sin_year"] + ([predictor] if rng.random() < share else [])),
                             "forecast": 1.0, "error": 0.0, "actual": 1.0,
                             "mase_scale": 1.0})
    return pd.DataFrame(rows), covariates, months


def real_panels() -> dict[str, pd.DataFrame]:
    from ingest import paths

    out = {}
    for key, _, _ in figures.GAS_PANEL:
        frame = pd.read_csv(paths.processed_dir() / f"forecasts_{key}_exogenous.csv")
        frame["target"] = pd.PeriodIndex(frame["target"], freq="M")
        filename, _, _ = figures.GAS_OBSERVED[key]
        series = pd.read_csv(paths.processed_dir() / filename)
        months = pd.PeriodIndex(series["month"], freq="M")
        covariates = pd.read_csv(paths.processed_dir() / "monthly_bog_lake_fen.csv")
        covariates["month"] = pd.PeriodIndex(covariates["month"], freq="M")
        out[key] = figures.screening_panel(
            frame, covariates.set_index("month").reindex(months), months)
    return out


# --- the panel data ---------------------------------------------------------


def test_a_predictor_that_never_survived_is_a_zero_not_a_gap():
    frame, covariates, months = synthetic()
    panel = figures.screening_panel(frame, covariates, months)
    assert panel.loc["Air temperature"].tolist() == [0.0, 0.0, 0.0, 0.0]


def test_the_one_month_lag_is_struck_where_it_does_not_exist():
    """It is not a predictor that failed; at longer horizons it is not offered."""
    frame, covariates, months = synthetic()
    panel = figures.screening_panel(frame, covariates, months)
    row = panel.loc["The flux a month before"]
    assert not np.isnan(row[1])
    assert all(np.isnan(row[h]) for h in (3, 6, 12))


def test_the_two_flux_lags_are_separate_rows():
    """Collapsing them would conflate last month with the same month last year."""
    frame, covariates, months = synthetic()
    panel = figures.screening_panel(frame, covariates, months)
    assert set(figures.FLUX_ROWS) <= set(panel.index)
    assert panel.loc[figures.FLUX_ROWS[0], 1] != panel.loc[figures.FLUX_ROWS[1], 1]


def test_the_calendar_share_rides_on_the_frame_not_on_a_second_scale():
    frame, covariates, months = synthetic()
    panel = figures.screening_panel(frame, covariates, months)
    calendar = panel.attrs["calendar"]
    # The contrast is what matters here. Fitting four terms to 72 months of noise
    # explains about 6% by chance, so the loose bound is the honest one on
    # synthetic data; the real series is asserted below at under one percent.
    assert calendar["Soil temperature"] > 0.9
    assert calendar["Water table"] < 0.15


# --- the two results it must carry ------------------------------------------


def test_no_covariate_survives_on_carbon_dioxide_at_three_months():
    panel = real_panels()["carbon_dioxide"]
    covariates = [label for _, label in figures.SCREENED_COVARIATES]
    assert panel.loc[covariates, 3].max() == 0.0
    assert panel.loc["The flux a year before", 3] == 1.0


def test_every_surviving_temperature_is_almost_all_calendar():
    for panel in real_panels().values():
        for name in ("Soil temperature", "Air temperature"):
            assert panel.attrs["calendar"][name] > 0.94


def test_the_water_table_is_the_mirror_image():
    """It carries independent information and barely survives, which is the point."""
    panels = real_panels()
    for panel in panels.values():
        assert panel.attrs["calendar"]["Water table"] < 0.01
    methane = panels["methane"]
    assert methane.loc["Water table"].max() < methane.loc["Soil temperature"].max()


def test_the_figure_names_the_water_table_rather_than_leaving_it_to_be_noticed():
    """Absence reads as unremarkable, so the sharpest result is said in words."""
    said = figures.MEASUREMENTS_TEXT.subtitle
    assert "water table" in said and "the date cannot predict" in said


# --- what it draws ----------------------------------------------------------


def test_one_row_order_holds_across_every_panel():
    """Small multiples only work if a row sits in the same place everywhere."""
    panels = real_panels()
    order = figures.usage_order(panels)
    fig = figures.measurements_used(panels)
    named = [ax for ax in fig.axes if any(t.get_text() for t in ax.get_yticklabels())]
    assert len(named) == len(figures.GAS_PANEL)      # named once per gas, not per panel
    for ax in named:
        assert [t.get_text() for t in ax.get_yticklabels()] == order
    for ax in fig.axes:
        assert len(ax.get_yticks()) == len(order)
    ps.plt.close(fig)


def test_the_rows_are_ordered_by_use_with_the_flux_at_the_top():
    panels = real_panels()
    order = figures.usage_order(panels)
    assert order[:len(figures.FLUX_ROWS)] == list(figures.FLUX_ROWS)
    assert order[-1] == "Water table"


def test_the_two_quantities_are_named_in_headings_rather_than_in_a_key():
    """A legend would repeat what the column heading already says where it is read."""
    fig = figures.measurements_used(real_panels())
    assert not any(ax.get_legend() for ax in fig.axes)
    said = [t.get_text() for t in fig.texts]
    assert figures.CHOSEN_HEADING in said and figures.DATE_HEADING in said
    ps.plt.close(fig)


def test_every_bar_prints_its_share_so_length_is_not_the_only_reading():
    panels = real_panels()
    fig = figures.measurements_used(panels)
    drawn = sum(int(np.isfinite(v)) for panel in panels.values()
                for v in panel.to_numpy(dtype=float).ravel())
    drawn += len(figures.SCREENED_COVARIATES) * len(panels)      # the date column
    printed = sum(1 for ax in fig.axes for text in ax.texts
                  if text.get_text().replace(".", "").isdigit())
    assert printed == drawn
    ps.plt.close(fig)


def test_a_share_below_one_percent_is_not_printed_as_a_zero():
    """Rounding would show what the date barely predicts as what it cannot."""
    fig = figures.measurements_used(real_panels())
    date_column = fig.axes[0]
    assert "0.5" in [text.get_text() for text in date_column.texts]
    ps.plt.close(fig)


def test_the_date_column_is_achromatic_and_the_usage_columns_are_not():
    """The two answer different questions, and only one of them is a result."""
    from matplotlib.colors import to_rgb

    fig = figures.measurements_used(real_panels())
    grey = to_rgb(ps.DATE_SHARE)
    assert grey[0] == pytest.approx(grey[1]) == pytest.approx(grey[2])
    used = {bar.get_facecolor()[:3] for ax in fig.axes for bar in ax.patches}
    assert to_rgb(ps.FITTED) in used and grey in used
    ps.plt.close(fig)


def test_the_figure_asks_no_reader_to_know_the_method():
    """Plain terms or nothing: none of the working vocabulary reaches the page."""
    text = figures.MEASUREMENTS_TEXT
    said = " ".join([text.title, text.subtitle, text.description, figures.DATE_HEADING,
                     figures.CHOSEN_HEADING, figures.NOT_ASKED,
                     figures.NOT_AVAILABLE]).lower()
    for jargon in ("boruta", "fold", "shadow", "survival", "survived", "lag",
                   "exogenous", "ridge", "screening", "covariate", "predictor"):
        assert jargon not in said


def test_the_description_states_what_the_order_is_built_from():
    """A sorted figure that does not say what it sorted on invites the wrong reading."""
    assert "ordered by how often the models chose" in figures.MEASUREMENTS_TEXT.description


def test_the_seasonal_terms_are_not_a_row():
    """Kept in every fit by construction, so a row of ones would say nothing."""
    panel = real_panels()["methane"]
    assert not any("sin" in name or "seasonal term" in name.lower() for name in panel.index)


def test_the_two_kinds_of_empty_cell_are_told_apart():
    """One is a question that does not apply; the other is a value a model cannot
    have. Drawn alike they would both read as data that went missing."""
    fig = figures.measurements_used(real_panels())
    marks = [text.get_text() for ax in fig.axes for text in ax.texts]
    assert marks.count(figures.NOT_ASKED) == 2 * len(figures.FLUX_ROWS)
    assert marks.count(figures.NOT_AVAILABLE) == 2 * 3      # one-month lag, three horizons
    assert figures.NOT_ASKED != figures.NOT_AVAILABLE
    ps.plt.close(fig)


def test_the_description_says_what_each_empty_cell_means():
    said = figures.MEASUREMENTS_TEXT.description
    assert "does not apply to the flux's own past values" in said
    assert "unavailable to a" in said and "three months or more ahead" in said


def test_both_column_groups_carry_the_axis_they_are_read_against():
    fig = figures.measurements_used(real_panels())
    assert [t.get_text() for t in fig.texts].count(figures.AXIS_LABEL) == 2
    ps.plt.close(fig)


def test_the_gases_are_named_in_the_bordered_box_the_other_figures_use():
    fig = figures.measurements_used(real_panels())
    boxed = [note for ax in fig.axes for note in ax.texts if note.get_bbox_patch()]
    assert sorted(note.get_text() for note in boxed) == \
        sorted(gas for _, gas, _ in figures.GAS_PANEL)
    ps.plt.close(fig)
