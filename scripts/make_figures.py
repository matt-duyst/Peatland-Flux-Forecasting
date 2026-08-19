"""Build the figure set and the README fragments that accompany it.

Reads the processed monthly dataset and the covariates the ingestion layer
produced, rebuilds the study windows, and writes one portable network graphic per
figure into `figures/`. The markdown for each figure is written alongside from
the same text the canvas carries, so the two cannot drift.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from ingest import covariates
from forecast import evaluation
from study import (bias, features, figures, holdout, plotstyle, reconstruct, sitemap,
                   targets, weights as weighting, windows)

MONTHLY = "data/processed/monthly_fch4_from_daily.csv"

# The wet-end directional expectation is computed from the fit window in use,
# not pinned. It was a literal here and in scripts/reconstruct.py, both carrying
# the nominal window's 0.148 after the study had adopted the 115-month window.


def load() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.PeriodIndex]]:
    """Covariates, the monthly series, and the windows they imply.

    `windows.build_windows` excludes the two months of 2019 recorded as
    instrument artifacts, so every figure describes the window the study adopted
    and describes the same one the tables do.
    """
    root = Path(__file__).resolve().parents[1]
    cov = covariates.load_all()
    monthly = pd.read_csv(root / MONTHLY)
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    monthly = monthly.set_index("month")
    built = windows.build_windows(cov, monthly.index)
    return cov, monthly, built


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cov, monthly, built = load()
    fragments = []

    fig = figures.water_table_support(cov["wte_m"], built["fit"], built["reconstruction"])
    path = plotstyle.save(fig, "water_table_support")
    fragments.append(plotstyle.readme_block(figures.WATER_TABLE_TEXT, "water_table_support"))
    print(f"wrote {path.relative_to(plotstyle.figures_dir().parent)}")

    from PIL import Image
    image = Image.open(sitemap.geodata_dir() / "naip_us_mbp_2021.jpg")
    fig = sitemap.site_overview(
        image,
        sitemap.load_geojson("nwi_wetlands.geojson"),
        sitemap.load_geojson("us_states.geojson"),
        sitemap.load_network_sites(),
        sitemap.wind_shares(),
    )
    path = plotstyle.save(fig, "site_overview")
    fragments.append(plotstyle.readme_block(sitemap.SITEMAP_TEXT, "site_overview"))
    print(f"wrote {path.relative_to(plotstyle.figures_dir().parent)}")

    inverse_variance = weighting.inverse_variance_weights(monthly).reindex(
        built["fit"]).dropna()
    monthly_recon = reconstruct.monthly_reconstruction(
        cov, monthly, built["fit"], built["reconstruction"], inverse_variance)
    annual = reconstruct.annual_reconstruction(
        monthly_recon,
        reconstruct.year_support(cov, built["fit"], built["reconstruction"],
                                 windows.RECONSTRUCTION_COVARIATES),
        bias.wet_end_bias(cov, monthly, built["fit"], inverse_variance),
    )
    # The annual table keeps the primary series and the envelope; the figure
    # draws the three assumptions themselves, so each is totaled here.
    for variant in reconstruct.VARIANTS:
        totals = targets.monthly_flux_to_annual(monthly_recon[variant])["g_C_m2"]
        annual[variant] = annual["year"].map(totals)

    fig = figures.reconstruction_series(annual)
    path = plotstyle.save(fig, "reconstruction_series")
    fragments.append(plotstyle.readme_block(figures.RECONSTRUCTION_TEXT,
                                            "reconstruction_series"))
    print(f"wrote {path.relative_to(plotstyle.figures_dir().parent)}")

    # The forecast comparison reads the scored forecasts rather than refitting.
    # scripts/forecast_models.py writes them; nothing here can drift from them.
    panels = {}
    for key, _, _ in figures.GAS_PANEL:
        frames = {}
        for family in ("benchmarks", "autoregressive", "exogenous"):
            frame = pd.read_csv(root / f"data/processed/forecasts_{key}_{family}.csv")
            frame["target"] = pd.PeriodIndex(frame["target"], freq="M")
            frames[family] = frame
        panels[key] = figures.forecast_panel(frames, evaluation.HORIZONS)

    fig = figures.forecast_error_by_horizon(panels)
    path = plotstyle.save(fig, "forecast_error_by_horizon")
    fragments.append(plotstyle.readme_block(figures.FORECAST_TEXT, "forecast_error_by_horizon"))
    print(f"wrote {path.relative_to(plotstyle.figures_dir().parent)}")

    # Observed against predicted reads the same scored forecasts, plus the
    # observed series over the whole record so the unforecast years stay visible.
    flux = {}
    for key, _, _ in figures.GAS_PANEL:
        filename, column, error = figures.GAS_OBSERVED[key]
        series = pd.read_csv(root / "data/processed" / filename)
        series["month"] = pd.PeriodIndex(series["month"], freq="M")
        observed_series = series.set_index("month")[[column, error]].rename(
            columns={column: "observed", error: "se"})
        frames = {}
        for family in ("benchmarks", "autoregressive", "exogenous"):
            frame = pd.read_csv(root / f"data/processed/forecasts_{key}_{family}.csv")
            frame["target"] = pd.PeriodIndex(frame["target"], freq="M")
            frames[family] = frame
        flux[key] = figures.flux_panel(observed_series, frames)

    fig = figures.observed_and_predicted(flux)
    path = plotstyle.save(fig, "observed_and_predicted")
    fragments.append(plotstyle.readme_block(figures.FLUX_TEXT, "observed_and_predicted"))
    print(f"wrote {path.relative_to(plotstyle.figures_dir().parent)}")

    # Which measurements were used reads the same scored forecasts, plus the
    # covariates it needs to say how much of each the date already accounts for.
    screening_panels = {}
    for key, _, _ in figures.GAS_PANEL:
        frame = pd.read_csv(root / f"data/processed/forecasts_{key}_exogenous.csv")
        frame["target"] = pd.PeriodIndex(frame["target"], freq="M")
        filename, column, _ = figures.GAS_OBSERVED[key]
        series = pd.read_csv(root / "data/processed" / filename)
        series["month"] = pd.PeriodIndex(series["month"], freq="M")
        months = pd.PeriodIndex(series["month"], freq="M")
        # Cut at the datum break, as the forecasting half itself is: the share of
        # each covariate the date accounts for is measured on the same months the
        # models saw, and two metres of gauge change would swamp the water table.
        screening_panels[key] = figures.screening_panel(
            frame, covariates.before_datum_break(cov).reindex(months), months)

    fig = figures.measurements_used(screening_panels)
    path = plotstyle.save(fig, "measurements_used_across_forecast_horizons")
    fragments.append(plotstyle.readme_block(figures.MEASUREMENTS_TEXT,
                                           "measurements_used_across_forecast_horizons"))
    print(f"wrote {path.relative_to(plotstyle.figures_dir().parent)}")

    # Coefficient stability reads the table `scripts/reconstruct.py` writes, and
    # takes the two spans in metres from the same windows every other figure uses:
    # what the reconstruction has to reach, and how far the holdout actually did.
    stability = pd.read_csv(root / "data/processed/coefficient_stability.csv")
    fitted, projected = built["fit"], built["reconstruction"]
    wettest_fitted = float(cov.loc[fitted, features.WATER_TABLE].max())
    required = float(cov.loc[projected, features.WATER_TABLE].max()) - wettest_fitted
    withheld = fitted.difference(holdout.wettest_decile(cov, fitted))
    tested = wettest_fitted - float(cov.loc[withheld, features.WATER_TABLE].max())

    fig = figures.coefficient_stability(
        figures.stability_paths(stability), required, tested)
    path = plotstyle.save(fig, "coefficient_stability")
    fragments.append(plotstyle.readme_block(figures.STABILITY_TEXT, "coefficient_stability"))
    print(f"wrote {path.relative_to(plotstyle.figures_dir().parent)}")

    target = plotstyle.figures_dir() / "README_fragments.md"
    target.write_text("\n".join(fragments))
    print(f"wrote {target.relative_to(plotstyle.figures_dir().parent)}")


if __name__ == "__main__":
    main()
