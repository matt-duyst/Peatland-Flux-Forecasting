"""Fit both model families against the benchmarks, on both gases.

Two families are run and never pooled. The autoregressive family sees the flux's
own past and the calendar, so a twelve-month forecast is a genuine twelve-month
forecast. The exogenous family adds lagged soil and air temperature, precipitation
and water table depth, which is more information, so it is reported beside the
autoregressive family rather than against it.

Nothing is scored on data its model could have seen. The month-of-year means, the
screening and the fit all happen inside the fold, on months up to the origin.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from forecast import benchmarks, evaluation, experiment, models  # noqa: E402
from ingest import covariates, paths  # noqa: E402

SERIES = {
    "methane": ("monthly_fch4_from_daily.csv", "fch4_mean", "nmol m-2 s-1"),
    "carbon dioxide": ("monthly_fco2_diurnally_balanced.csv", "fco2_mean", "umol m-2 s-1"),
}

#: Environmental drivers, from the legacy monthly file. Soil and air temperature
#: are in Fahrenheit and precipitation in inches, as recorded; a monotone unit
#: change cannot alter a tree and only rescales a linear coefficient, so they are
#: left as they are rather than silently converted.
COVARIATES = ("soil_temp_f", "atm_temp_f", "precip_in", "wte_m")


def heading(text: str) -> None:
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def load(name: str) -> pd.Series:
    filename, column, _ = SERIES[name]
    frame = pd.read_csv(paths.processed_dir() / filename)
    frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
    series = frame.set_index("month")[column]
    return series.reindex(pd.period_range(series.index.min(), series.index.max(), freq="M"))


def load_covariates(index: pd.PeriodIndex) -> pd.DataFrame:
    """The environmental drivers, with the water table cut at its datum break.

    This half of the study runs to 2021 and so meets the step described in
    `ingest.covariates.before_datum_break`. Read across it, the last twelve months
    of water table are two meters below everything before them, which is a gauge
    change wearing the clothes of a drought.
    """
    frame = pd.read_csv(paths.processed_dir() / "monthly_bog_lake_fen.csv")
    frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
    frame = covariates.before_datum_break(frame.set_index("month"))
    return frame[list(COVARIATES)].reindex(index)


def report(title: str, frame: pd.DataFrame, order: list[str]) -> pd.DataFrame:
    table = evaluation.score(frame)
    heading(title)
    summary = evaluation.origin_summary(frame)
    print("  " + ", ".join(f"{k}: {v}" for k, v in summary.items()))
    for horizon in evaluation.HORIZONS:
        block = table[table["horizon"] == horizon].set_index("method").reindex(order).dropna(how="all")
        if block.empty:
            continue
        print(f"\n  horizon {horizon} month{'s' if horizon > 1 else ''}")
        view = block[["n", "MASE", "MASE_median", "MAE", "RMSE", "share_beating_snaive"]].round(3)
        view.columns = ["n", "MASE", "median", "MAE", "RMSE", "share<1"]
        print(view.to_string())
    return table


def main() -> None:
    pd.set_option("display.width", 220)
    for name in SERIES:
        series = load(name)
        stem = name.replace(" ", "_")
        heading(f"{name.upper()}  ({SERIES[name][2]})")
        print(f"  {series.notna().sum()} observed months of {len(series)}, "
              f"{series.index.min()} to {series.index.max()}, "
              f"minimum training window {evaluation.MIN_TRAIN} months")

        bench = evaluation.rolling_forecasts(series, benchmarks.BENCHMARKS)
        autoregressive = experiment.run(series)
        exogenous = experiment.run(series, exogenous=load_covariates(series.index))

        report(f"{name}: benchmarks, on every month each could score", bench,
               list(benchmarks.BENCHMARKS))
        report(f"{name}: autoregressive family, on every month each could score",
               autoregressive, list(models.MODELS))
        report(f"{name}: exogenous family, on every month each could score",
               exogenous, list(models.MODELS))

        keys = evaluation.shared_targets([bench, autoregressive, exogenous])
        heading(f"{name}: every method on the months all of them could score")
        print(f"  {len(keys)} horizon-and-target pairs are scored by every method in all three\n"
              f"  families. The tables above rest on different month sets, because the\n"
              f"  families reach different distances into the record, so only this table\n"
              f"  compares methods rather than comparing records.")
        combined = pd.concat(
            [
                evaluation.score(evaluation.restrict(bench, keys)).assign(family="benchmark"),
                evaluation.score(evaluation.restrict(autoregressive, keys)).assign(family="autoregressive"),
                evaluation.score(evaluation.restrict(exogenous, keys)).assign(family="exogenous"),
            ]
        )
        for horizon in evaluation.HORIZONS:
            block = combined[combined["horizon"] == horizon].sort_values("MASE")
            if block.empty:
                continue
            best_benchmark = block[block["family"] == "benchmark"]["MASE"].min()
            block = block.assign(vs_best_benchmark=(block["MASE"] / best_benchmark).round(3))
            print(f"\n  horizon {horizon}   (n = {int(block['n'].iloc[0])} per method)")
            print(block[["family", "method", "MASE", "MAE", "RMSE", "share_beating_snaive",
                         "vs_best_benchmark"]].round(3).to_string(index=False))

        for label, frame in (("benchmarks", bench), ("autoregressive", autoregressive),
                             ("exogenous", exogenous)):
            frame.to_csv(paths.processed_dir() / f"forecasts_{stem}_{label}.csv", index=False)

        heading(f"{name}: which predictors survived screening, exogenous family")
        frequency = experiment.predictor_frequency(exogenous)
        for horizon in evaluation.HORIZONS:
            block = frequency[frequency["horizon"] == horizon]
            if block.empty:
                continue
            print(f"\n  horizon {horizon}")
            print(block[["predictor", "folds", "share"]].to_string(index=False))


if __name__ == "__main__":
    main()
