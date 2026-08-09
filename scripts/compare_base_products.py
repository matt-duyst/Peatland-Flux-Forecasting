"""Compare the 2022 export the pipeline reads against the 2025 BASE product.

Reports the BADM metadata, the delivered variable inventory, agreement between
the two products value by value, the paired-analyzer statistics recomputed on
each, and what the excluded wind sector removes. Reads both products and writes
nothing. The ingestion path is untouched by this script.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from ingest import analyzers, raw, site
from validation import base_v55

METHANE = ("FCH4", "FCH4_1_1_1", "FCH4_1_1_2")
PRECEDENCE = (site.BASE_COLUMN, site.TGA_COLUMN, site.LI7700_COLUMN)


def banner(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def main() -> None:
    export = raw.load_halfhourly().set_index("timestamp_start").sort_index()
    product = base_v55.load_base()
    badm = base_v55.load_badm()

    banner("Provenance")
    print(f"BASE version {base_v55.BASE_VERSION}, BADM {base_v55.BADM_VERSION}")
    print(f"DOI {base_v55.PRODUCT_DOI}, license {base_v55.PRODUCT_LICENCE}")
    print(base_v55.PRODUCT_CITATION)

    banner("BADM metadata")
    groups = badm["VARIABLE_GROUP"].unique()
    for group in ("GRP_INST", "GRP_INSTPAIR"):
        print(f"{group}: {'present' if group in groups else 'ABSENT'}")
    for variable in ("IGBP", "LOCATION_ELEV", "SITE_SNOW_COVER_DAYS",
                     "SURFACE_HOMOGENEITY", "WIND_DIRECTION", "UTC_OFFSET"):
        print(f"  {variable:22s} {base_v55.badm_value(badm, variable)}")
    print("\nSITE_DESC:")
    print(f"  {base_v55.badm_value(badm, 'SITE_DESC')}")

    banner("Variable inventory as delivered")
    print(f"{product.shape[1]} variables, {len(product)} half-hours, "
          f"{product.index.min()} to {product.index.max()}")
    print("columns:", ", ".join(product.columns))

    banner("Agreement between the two products")
    print(base_v55.compare_columns(export, product, METHANE).to_string(index=False))
    for column in METHANE:
        print(f"\nBy year, {column}:")
        print(base_v55.difference_by_year(export, product, column).to_string())

    banner("Paired-analyzer statistics on each product")
    for tag, frame in (("2022 export", export), ("2025 product", product)):
        pairs = analyzers.paired(frame.reset_index())
        stats = analyzers.difference_statistics(pairs["difference"])
        print(f"\n{tag}: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
        print(analyzers.fit_laplace_vs_gaussian(pairs["difference"]).to_string(index=False))

    banner("The excluded wind sector")
    print(base_v55.sector_cost(product, METHANE + ("FC",)).to_string(index=False))
    methane = base_v55.merged_methane(product, PRECEDENCE)
    print()
    print(base_v55.coverage_against_sector(product, methane).to_string(index=False))


if __name__ == "__main__":
    main()
