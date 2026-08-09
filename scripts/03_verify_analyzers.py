"""Identify the two methane analysers and compare the pair against published values.

Reports deployment evidence for the TGA-100A and LI-7700, the distribution of
their paired differences, competing Laplace and Gaussian fits to those
differences, and regressions of one analyser on the other across a range of
outlier screens.

Run: .venv/bin/python scripts/03_verify_analyzers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import analyzers, raw, site  # noqa: E402


def main() -> None:
    pd.set_option("display.width", 220)
    frame = raw.load_halfhourly()

    print("=" * 78)
    print(f"SITE {site.SITE_ID} — {site.SITE_NAME}")
    print("=" * 78)
    print(f"  {site.LATITUDE} N, {site.LONGITUDE} W — {site.LOCATION}")
    print(f"  data product DOI {site.DATA_PRODUCT_DOI} — {site.DATA_CITATION}")
    print(f"  reference        {site.REFERENCE_DOI} — {site.REFERENCE_CITATION}")
    print(f"  FCH4 units       {site.FCH4_UNITS}")

    print("\n" + "=" * 78)
    print("ANALYSER IDENTIFICATION")
    print("=" * 78)
    print(analyzers.identification_evidence(frame).to_string(index=False))
    print(
        f"\n  Deventer et al. (2019): LI-7700 not operated before"
        f" {site.PUBLISHED_LI7700_START}; {site.PUBLISHED_TGA_RETAINED:,}"
        f" retained TGA-100A fluxes"
    )

    pairs = analyzers.paired(frame)

    print("\n" + "=" * 78)
    print("PAIRED DIFFERENCES (TGA-100A minus LI-7700)")
    print("=" * 78)
    for key, value in analyzers.difference_statistics(pairs["difference"]).items():
        print(f"  {key:28s} {value:12.3f}")
    print(
        "\n  Deventer et al. (2019): "
        + ", ".join(f"{k} {v}" for k, v in site.PUBLISHED_PAIRED_STATS.items())
    )

    print("\n" + "=" * 78)
    print("DISTRIBUTIONAL FIT OF THE PAIRED DIFFERENCES")
    print("=" * 78)
    print(analyzers.fit_laplace_vs_gaussian(pairs["difference"]).to_string(index=False))

    print("\n" + "=" * 78)
    print("REGRESSION OF LI-7700 ON TGA-100A, BY OUTLIER SCREEN")
    print("=" * 78)
    sweep = analyzers.regression_sweep(pairs)
    print(sweep.round(3).to_string(index=False))
    print(
        f"\n  Deventer et al. (2019) reduced major axis:"
        f" slope {site.PUBLISHED_RMA['slope']} +/- {site.PUBLISHED_RMA['slope_se']},"
        f" intercept {site.PUBLISHED_RMA['intercept']} +/- {site.PUBLISHED_RMA['intercept_se']}"
    )
    print("  Ordinary least squares slope and intercept reported as not")
    print("  significantly different from 1 and 0\n")
    print(analyzers.published_agreement(sweep).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
