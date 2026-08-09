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
from study import figures, plotstyle, sitemap, windows

MONTHLY = "data/processed/monthly_fch4_from_daily.csv"


def load() -> tuple[pd.DataFrame, dict[str, pd.PeriodIndex]]:
    """Covariates and the fit and reconstruction windows they imply."""
    root = Path(__file__).resolve().parents[1]
    cov = covariates.load_all()
    monthly = pd.read_csv(root / MONTHLY)
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    return cov, windows.build_windows(cov, monthly.set_index("month").index)


def main() -> None:
    cov, built = load()
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

    target = plotstyle.figures_dir() / "README_fragments.md"
    target.write_text("\n".join(fragments))
    print(f"wrote {target.relative_to(plotstyle.figures_dir().parent)}")


if __name__ == "__main__":
    main()
