"""What the benchmark scores rest on, and what the series look like before fitting.

Three things a model comparison would otherwise inherit unexamined: whether the
scaled error is comparable between the two gases, where the winning benchmark
fails, and whether the seasonal signal it extracts is stable enough for a single
climatology to be the right benchmark at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from scipy import stats

from forecast import benchmarks, evaluation  # noqa: E402
from ingest import paths  # noqa: E402

SERIES = {
    "methane": ("monthly_fch4_from_daily.csv", "fch4_mean"),
    "carbon dioxide": ("monthly_fco2_diurnally_balanced.csv", "fco2_mean"),
}


def heading(text: str) -> None:
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def load(name: str) -> pd.Series:
    filename, column = SERIES[name]
    frame = pd.read_csv(paths.processed_dir() / filename)
    frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
    series = frame.set_index("month")[column]
    return series.reindex(pd.period_range(series.index.min(), series.index.max(), freq="M"))


def autocorrelation(x: np.ndarray, nlags: int) -> np.ndarray:
    x = np.asarray(x, float) - np.mean(x)
    denominator = np.dot(x, x)
    return np.array([1.0] + [np.dot(x[k:], x[:-k]) / denominator for k in range(1, nlags + 1)])


def main() -> None:
    pd.set_option("display.width", 200)
    runs = {name: evaluation.rolling_forecasts(load(name), benchmarks.BENCHMARKS)
            for name in SERIES}

    heading("IS THE SCALED ERROR COMPARABLE BETWEEN THE TWO GASES?")
    for name, frame in runs.items():
        series = load(name)
        scale = frame.groupby("origin")["mase_scale"].first().dropna()
        scored = frame[frame["method"] == "seasonal naive"].dropna(subset=["actual", "forecast"])
        out_of_sample = scored["error"].abs().mean()
        print(f"\n  {name}")
        print(f"    denominator, seasonal naive error on the training window: "
              f"mean {scale.mean():.3f}, first origin {scale.iloc[0]:.3f}, "
              f"last {scale.iloc[-1]:.3f}")
        print(f"    the same benchmark measured on the months actually scored: {out_of_sample:.3f}")
        print(f"    ratio, scored to training: {out_of_sample / scale.mean():.3f}")
    print("\n  A ratio near one means the training window is as hard as the test window and the")
    print("  scaled error means what it appears to. Below one means the denominator is inflated")
    print("  and every scaled error for that gas is depressed by the same factor.")

    heading("THE SAME COMPARISON IN UNITS THAT DO TRAVEL BETWEEN GASES")
    for name, frame in runs.items():
        print(f"\n  {name}: error as a ratio to seasonal naive on the same months")
        print(evaluation.relative_to(frame).round(3).to_string(index=False))

    heading("WHERE THE WINNING BENCHMARK FAILS")
    for name, frame in runs.items():
        clim = frame[frame["method"] == "climatology"].dropna(subset=["scaled"])
        years = clim.assign(year=clim["target"].map(lambda p: p.year))
        grouped = years.groupby("year")["scaled"]
        table = pd.DataFrame({"n": grouped.size(), "mean": grouped.mean(),
                              "median": grouped.median(), "max": grouped.max(),
                              "share_above_1": grouped.apply(lambda v: (v > 1).mean())})
        table["share_of_total_error"] = 100 * grouped.sum() / clim["scaled"].sum()
        print(f"\n  {name}, climatology by target year")
        print(table.round(3).to_string())
        top = table.nlargest(2, "share_of_total_error")
        print(f"    the worst two years carry {top['share_of_total_error'].sum():.0f}% of the "
              f"total scaled error on {100 * top['n'].sum() / table['n'].sum():.0f}% of the forecasts")

    heading("WHAT THE EVALUATION WINDOW CAN AND CANNOT SEE")
    for name in SERIES:
        series = load(name)
        first = evaluation.origins(series)[0]
        print(f"  {name}: first origin {first}, so the earliest month scored is {first + 1}; "
              f"everything before is training for every origin")

    heading("PREPROCESSING DIAGNOSTICS")
    for name in SERIES:
        series = load(name).dropna()
        values = series.to_numpy()
        a = autocorrelation(values, 13)
        bartlett = np.sqrt((1 + 2 * np.sum(a[1:12] ** 2)) / len(values))
        t = np.arange(len(values), dtype=float)
        raw = stats.linregress(t, values)
        month_means = series.groupby(series.index.month).transform("mean")
        deseasonalized = stats.linregress(t, (series - month_means).to_numpy())
        counts = series.groupby(series.index.year).size()
        amplitude = series.groupby(series.index.year).agg(lambda g: g.max() - g.min())[counts >= 10]
        trend = stats.linregress(np.array(amplitude.index, float), amplitude.to_numpy())

        print(f"\n  {name} (n = {len(values)})")
        print(f"    lag-12 autocorrelation {a[12]:+.3f}, Bartlett standard error {bartlett:.3f}, "
              f"z = {a[12] / bartlett:.2f} -> "
              f"{'significant' if abs(a[12] / bartlett) > 1.96 else 'not significant'}")
        print(f"    trend, raw series: {raw.slope * 12:+.3f} per year, p = {raw.pvalue:.3f}")
        print(f"    trend, month-of-year means removed: {deseasonalized.slope * 12:+.3f} per year, "
              f"p = {deseasonalized.pvalue:.3f}")
        print(f"    within-year amplitude: mean {amplitude.mean():.2f}, "
              f"range {amplitude.min():.2f} to {amplitude.max():.2f}, "
              f"coefficient of variation {100 * amplitude.std() / amplitude.mean():.0f}%")
        print(f"    amplitude trend: {trend.slope:+.3f} per year, p = {trend.pvalue:.3f} -> "
              f"{'changing' if trend.pvalue < 0.05 else 'varying without direction'}")


if __name__ == "__main__":
    main()
