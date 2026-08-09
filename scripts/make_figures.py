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
from study import (figures, plotstyle, reconstruct, sitemap, targets,
                   weights as weighting, windows)

MONTHLY = "data/processed/monthly_fch4_from_daily.csv"

#: Wet-end directional expectation from src/study/bias.py, carried as a stated
#: direction rather than applied as a correction.
WET_END_BIAS_LOG = 0.148


def load() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.PeriodIndex]]:
    """Covariates, the monthly series, and the windows they imply.

    The fit window excludes the two months of 2019 recorded as instrument
    artifacts, so every figure describes the window the study adopted.
    """
    root = Path(__file__).resolve().parents[1]
    cov = covariates.load_all()
    monthly = pd.read_csv(root / MONTHLY)
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    monthly = monthly.set_index("month")
    built = windows.build_windows(cov, monthly.index)
    built["fit"] = built["fit"].difference(
        pd.PeriodIndex(figures.WATER_TABLE_ARTIFACTS, freq="M")
    )
    return cov, monthly, built


def main() -> None:
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
        WET_END_BIAS_LOG,
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

    target = plotstyle.figures_dir() / "README_fragments.md"
    target.write_text("\n".join(fragments))
    print(f"wrote {target.relative_to(plotstyle.figures_dir().parent)}")


if __name__ == "__main__":
    main()
