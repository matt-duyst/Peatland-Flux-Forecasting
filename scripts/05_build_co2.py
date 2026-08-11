"""Build the monthly carbon dioxide series from the AmeriFlux BASE product.

Carbon dioxide is brought to the standard methane already meets: daily means
only from days holding at least eight valid half-hours, monthly means of those
daily means, and observation counts and dispersion retained at both levels.

The source is FC in the 2025 BASE product rather than the 2022 workbook export,
because that export carries only the three methane columns. The two products
were shown to hold identical methane values over every shared half-hour, so
taking one gas from each is not a change of source in any material sense.
`notes/base_v55.md` records the comparison.

Writes: data/processed/{daily_fc,monthly_fco2_from_daily}.{csv,parquet}
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from ingest import covariates, daily, paths, site  # noqa: E402
from validation import base_v55  # noqa: E402

COLUMN = "FC"
UNITS = "umol m-2 s-1"


def heading(text: str) -> None:
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def main() -> None:
    pd.set_option("display.width", 200)
    product = base_v55.load_base()
    frame = product[[COLUMN]].reset_index()

    heading("SOURCE")
    valid = int(frame[COLUMN].notna().sum())
    print(f"  {base_v55.PRODUCT_CITATION}")
    print(f"  half-hours {len(frame):,}, valid {valid:,} ({100 * valid / len(frame):.1f}%)")
    print(f"  {frame['timestamp_start'].min()} to {frame['timestamp_start'].max()}, units {UNITS}")

    heading(f"DAILY, at least {site.MIN_HALFHOURS_PER_DAY} valid half-hours")
    day = daily.daily_stats_column(frame, COLUMN)
    print(f"  days retained {len(day):,} of {frame['timestamp_start'].dt.normalize().nunique():,}")
    print(f"  mean {day[f'{COLUMN}_mean'].mean():.4f}, "
          f"range {day[f'{COLUMN}_mean'].min():.3f} to {day[f'{COLUMN}_mean'].max():.3f}")

    monthly = daily.daily_to_monthly_column(day, COLUMN)
    monthly = monthly.rename(columns={
        f"{COLUMN}_mean": "fco2_mean", f"{COLUMN}_days": "fco2_days",
        f"{COLUMN}_sd_across_days": "fco2_sd_across_days",
        f"{COLUMN}_halfhours": "fco2_halfhours",
        f"{COLUMN}_se_across_days": "fco2_se_across_days"})

    heading("MONTHLY")
    print(f"  months {len(monthly)}, {monthly['month'].min()} to {monthly['month'].max()}")
    span = pd.period_range(monthly["month"].min(), monthly["month"].max(), freq="M")
    absent = span.difference(pd.PeriodIndex(monthly["month"]))
    print(f"  span {len(span)} months, absent {len(absent)}: {[str(a) for a in absent]}")
    print(f"  days per month: median {monthly['fco2_days'].median():.0f}, "
          f"min {monthly['fco2_days'].min()}, max {monthly['fco2_days'].max()}")
    print(f"  months resting on fewer than 10 days: {int((monthly['fco2_days'] < 10).sum())}")
    print(f"  mean {monthly['fco2_mean'].mean():.4f}, "
          f"range {monthly['fco2_mean'].min():.3f} to {monthly['fco2_mean'].max():.3f}")
    print(f"  crosses zero: {bool((monthly['fco2_mean'] < 0).any() and (monthly['fco2_mean'] > 0).any())}, "
          f"months at or above zero {int((monthly['fco2_mean'] >= 0).sum())}")

    heading("AGAINST THE SINGLE-COLUMN SERIES THE STUDY HAS USED")
    legacy = covariates.load_all()["fco2"].dropna()
    built = monthly.set_index(pd.PeriodIndex(monthly["month"], freq="M"))["fco2_mean"]
    shared = built.index.intersection(legacy.index)
    print(f"  legacy months {len(legacy)} ({legacy.index.min()} to {legacy.index.max()}), "
          f"built {len(built)}, shared {len(shared)}")
    print(f"  only in legacy: {len(legacy.index.difference(built.index))}, "
          f"only in built: {len(built.index.difference(legacy.index))}")
    a, b = legacy[shared], built[shared]
    diff = b - a
    print(f"  correlation {np.corrcoef(a, b)[0, 1]:+.4f}")
    print(f"  difference built minus legacy: mean {diff.mean():+.4f}, median {diff.median():+.4f}, "
          f"sd {diff.std():.4f}")
    print(f"  identical to 3 decimals: {int((diff.abs() < 5e-4).sum())} of {len(shared)}")
    print(f"  largest disagreements:")
    print(pd.DataFrame({"legacy": a, "built": b, "difference": diff}).reindex(
        diff.abs().nlargest(6).index).round(3).to_string())

    heading("THE DIURNAL PROBLEM, WHICH METHANE DOES NOT HAVE")
    # The contrast between the two gases was recorded in notes/ingestion.md before
    # any script produced it. Both columns are read from the same product and
    # before any merge or quality control, so the two gases are compared on the
    # same footing; the merged methane series gives 0.97% and 37.4% instead,
    # which is the pair quoted for the aggregation decision.
    print("  Raw product columns, before merge or quality control:")
    for label, column in (("methane", "FCH4"), ("carbon dioxide", COLUMN)):
        shares = daily.diurnal_vs_seasonal(product[[column]].reset_index(), column)
        print(f"    {label:15s} half-hour-of-day {100 * shares['diurnal_eta_squared']:5.2f}% "
              f"of variance, month-of-year {100 * shares['seasonal_eta_squared']:5.2f}%, "
              f"n = {shares['n']:,}")
    print(f"  daylight share of retained carbon dioxide observations: "
          f"{100 * daily.daylight_share(frame, COLUMN):.1f}%, against 50% if even")

    balanced = daily.monthly_diurnally_balanced(frame, COLUMN)
    bal = balanced.set_index(pd.PeriodIndex(balanced["month"], freq="M"))[f"{COLUMN}_mean"]
    rule = monthly.set_index(pd.PeriodIndex(monthly["month"], freq="M"))["fco2_mean"]
    shared_b = rule.index.intersection(bal.index)
    bias = rule[shared_b] - bal[shared_b]
    print(f"  daily-rule mean minus diurnally balanced mean: mean {bias.mean():+.4f}, "
          f"max |difference| {bias.abs().max():.3f}")
    by_moy = bias.groupby(bias.index.month).mean()
    seasonal = rule[shared_b].groupby(rule[shared_b].index.month).mean()
    print(f"  the bias is seasonal: {by_moy.min():+.3f} in month {int(by_moy.idxmin())}, "
          f"{by_moy.max():+.3f} in month {int(by_moy.idxmax())}")
    print(f"  its seasonal swing is {by_moy.max() - by_moy.min():.3f} against a series seasonal "
          f"amplitude of {seasonal.max() - seasonal.min():.3f}, "
          f"or {100 * (by_moy.max() - by_moy.min()) / (seasonal.max() - seasonal.min()):.0f}%")
    balanced = balanced.rename(columns={
        f"{COLUMN}_mean": "fco2_mean", f"{COLUMN}_cells": "fco2_cells",
        f"{COLUMN}_sd_across_cells": "fco2_sd_across_cells",
        f"{COLUMN}_halfhours": "fco2_halfhours",
        f"{COLUMN}_se_across_cells": "fco2_se_across_cells"})

    directory = paths.processed_dir()
    directory.mkdir(parents=True, exist_ok=True)
    for name, table in (("daily_fc", day), ("monthly_fco2_from_daily", monthly),
                        ("monthly_fco2_diurnally_balanced", balanced)):
        out = table.copy()
        if "month" in out:
            out["month"] = out["month"].astype(str)
        out.to_csv(directory / f"{name}.csv", index=False)
        out.to_parquet(directory / f"{name}.parquet", index=False)
    print(f"\nwrote three tables to {directory.relative_to(paths.repo_root())}")


if __name__ == "__main__":
    main()
