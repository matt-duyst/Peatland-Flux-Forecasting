"""Characterize the three raw methane columns and the derived FCH4 Data.csv subset.

Reports sentinel removal counts, the temporal coverage and overlap of the three
columns, the source column behind each value in the derived file, and tests of
whether any threshold or dispersion rule reproduces that file's row selection.

Run: .venv/bin/python scripts/01_investigate_raw.py
Writes: data/interim/derived_labelled.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import clean, paths, raw  # noqa: E402


def main() -> None:
    pd.set_option("display.width", 200)
    halfhourly = raw.load_halfhourly()

    print("=" * 78)
    print("SENTINEL REMOVAL")
    print("=" * 78)
    print(raw.sentinel_report(halfhourly).to_string(index=False))

    print("\n" + "=" * 78)
    print("COLUMN COVERAGE")
    print("=" * 78)
    print(clean.column_coverage(halfhourly).to_string(index=False))

    print("\nValid observations per year:")
    print(clean.yearly_valid_counts(halfhourly).to_string())

    print("\n" + "=" * 78)
    print("COLUMN OVERLAP")
    print("=" * 78)
    print(clean.column_overlap(halfhourly).to_string(index=False))

    long = clean.to_long(halfhourly)
    labeled = clean.label_derived_subset(long)
    paths.ensure_dirs()
    labeled.to_parquet(paths.interim_dir() / "derived_labelled.parquet", index=False)

    print("\n" + "=" * 78)
    print("DERIVED FCH4 Data.csv — SOURCE COLUMN BY YEAR")
    print("=" * 78)
    print(clean.derived_provenance(labeled).to_string())

    print("\n" + "=" * 78)
    print("DERIVED FCH4 Data.csv — TESTS OF CANDIDATE SELECTION RULES")
    print("=" * 78)
    for key, value in clean.derived_rule_tests(labeled).items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
