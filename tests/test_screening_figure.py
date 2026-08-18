"""Screening survival: the panel data, the two results it must carry, the ramp."""

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
    """Absence reads as unremarkable on a heatmap, so the sharpest result is said."""
    fig = figures.screening_survival(real_panels())
    notes = [t.get_text() for t in fig.axes[0].texts]
    assert any("calendar cannot explain" in text for text in notes)
    said = figures.SCREENING_TEXT.subtitle
    assert "water table" in said and "season under another name" in said
    ps.plt.close(fig)


# --- what it draws ----------------------------------------------------------


def test_the_ramp_is_monochrome_so_it_collides_with_no_encoded_hue():
    fig = figures.screening_survival(real_panels())
    image = fig.axes[0].images[0]
    for level in (0.0, 0.5, 1.0):
        red, green, blue, _ = image.cmap(level)
        assert red == pytest.approx(green, abs=0.02)
        assert green == pytest.approx(blue, abs=0.02)
    ps.plt.close(fig)


def test_every_cell_prints_its_value_so_the_ramp_is_redundant():
    panels = real_panels()
    fig = figures.screening_survival(panels)
    for ax, key in zip(fig.axes, [k for k, _, _ in figures.GAS_PANEL]):
        values = panels[key].to_numpy(dtype=float)
        printed = [t.get_text() for t in ax.texts]
        assert sum(not np.isnan(v) for v in values.ravel()) == \
            sum(1 for text in printed if text.replace(".", "").isdigit())
    ps.plt.close(fig)


def test_dark_cells_carry_light_text():
    panels = real_panels()
    fig = figures.screening_survival(panels)
    for text in fig.axes[0].texts:
        body = text.get_text()
        if body.replace(".", "").isdigit():
            light = text.get_color() in ("white", "#FFFFFF")
            assert light == (float(body) > figures.DARK_CELL)
    ps.plt.close(fig)


def test_the_seasonal_terms_are_not_a_row():
    """Kept in every fit by construction, so a row of ones would say nothing."""
    panel = real_panels()["methane"]
    assert not any("sin" in name or "seasonal term" in name.lower() for name in panel.index)
    assert "not shown" in figures.SCREENING_TEXT.description
