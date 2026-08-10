"""Score the four benchmarks on both gases, before any model is fitted.

A method that cannot beat these has shown nothing. The point of running them
first is that the answer may be the study's finding: if month-of-year
climatology wins, the series is predictable from its seasonal mean and little
else, which is a result about the peatland rather than a baseline.

Carbon dioxide is read from the diurnally balanced series. The unbalanced one
carries a seasonal artifact worth 62% of its seasonal amplitude, which would
make a seasonal benchmark measure the tower's duty cycle.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from forecast import benchmarks, evaluation  # noqa: E402
from ingest import paths  # noqa: E402

SERIES = {
    "methane": ("monthly_fch4_from_daily.csv", "fch4_mean", "nmol m-2 s-1"),
    "carbon dioxide": ("monthly_fco2_diurnally_balanced.csv", "fco2_mean", "umol m-2 s-1"),
}


def heading(text: str) -> None:
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def load(name: str) -> pd.Series:
    filename, column, _ = SERIES[name]
    frame = pd.read_csv(paths.processed_dir() / filename)
    frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
    series = frame.set_index("month")[column]
    return series.reindex(pd.period_range(series.index.min(), series.index.max(), freq="M"))


def main() -> None:
    pd.set_option("display.width", 220)
    for name in SERIES:
        series = load(name)
        units = SERIES[name][2]
        heading(f"{name.upper()}  ({units})")
        print(f"  {series.notna().sum()} observed months of {len(series)}, "
              f"{series.index.min()} to {series.index.max()}")

        frame = evaluation.rolling_forecasts(series, benchmarks.BENCHMARKS)
        summary = evaluation.origin_summary(frame)
        print("  " + ", ".join(f"{k}: {v}" for k, v in summary.items()))
        print(f"  forecasts overlap heavily: {summary['scored forecasts']} scored forecasts rest on "
              f"{summary['distinct target months']} distinct months, so the effective sample is far "
              f"smaller than the count")

        table = evaluation.score(frame)
        for horizon in evaluation.HORIZONS:
            block = table[table["horizon"] == horizon].set_index("method")
            block = block.reindex(list(benchmarks.BENCHMARKS))
            print(f"\n  horizon {horizon} month{'s' if horizon > 1 else ''}"
                  f"   (n = {int(block['n'].iloc[0])} per method)")
            view = block[["MASE", "MASE_median", "MASE_q25", "MASE_q75",
                          "MAE", "RMSE", "share_beating_snaive"]].round(3)
            view.columns = ["MASE", "median", "q25", "q75", "MAE", "RMSE", "share<1"]
            print(view.to_string())

        best = table.loc[table.groupby("horizon")["MASE"].idxmin()]
        heading(f"{name.upper()}: WHICH BENCHMARK WINS AT EACH HORIZON")
        print(best[["horizon", "method", "MASE", "MAE", "RMSE"]].round(3).to_string(index=False))

        clim = table[table["method"] == "climatology"].set_index("horizon")["MASE"]
        snaive = table[table["method"] == "seasonal naive"].set_index("horizon")["MASE"]
        print("\n  climatology against seasonal naive, by horizon:")
        for h in evaluation.HORIZONS:
            gap = 100 * (snaive[h] - clim[h]) / snaive[h]
            verdict = "climatology better" if gap > 0 else "seasonal naive better"
            print(f"    h={h:2d}   climatology {clim[h]:.3f}   seasonal naive {snaive[h]:.3f}   "
                  f"{verdict} by {abs(gap):.1f}%")


if __name__ == "__main__":
    main()
