"""Three examinations of the model comparison, run from the saved forecasts.

Nothing here refits a model. `scripts/forecast_models.py` writes one frame per
gas and family to the processed directory, and these read them back, so the
examinations are cheap to repeat and cannot drift from the scores they explain.

One: what the per-fold screening kept, and whether the covariates that survived
carry anything the seasonal terms do not already hold.

Two: where the one methane case that beats climatology gets its advantage.

Three: the significance tests, corrected for the serial correlation the earlier
sign tests ignored.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from scipy import stats

from forecast import evaluation, experiment, features, models, preprocessing  # noqa: E402
from forecast_models import COVARIATES, load, load_covariates  # noqa: E402
from ingest import paths  # noqa: E402

GASES = {"methane": "methane", "carbon dioxide": "carbon_dioxide"}
FAMILIES = ("benchmarks", "autoregressive", "exogenous")

#: The year the methane advantage turns out to live in, examined separately.
ANOMALOUS_YEAR = 2015


def heading(text: str) -> None:
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def read(stem: str, family: str) -> pd.DataFrame:
    frame = pd.read_csv(paths.processed_dir() / f"forecasts_{stem}_{family}.csv")
    frame["target"] = pd.PeriodIndex(frame["target"], freq="M")
    return frame


def shared(stem: str) -> tuple[dict[str, pd.DataFrame], set]:
    frames = {family: read(stem, family) for family in FAMILIES}
    keys = evaluation.shared_targets(list(frames.values()))
    return {k: evaluation.restrict(v, keys) for k, v in frames.items()}, keys


def errors_at(frames: dict[str, pd.DataFrame], horizon: int) -> pd.DataFrame:
    """Signed error by target month, one column per family and method."""
    parts = []
    for family, frame in frames.items():
        block = frame[frame["horizon"] == horizon]
        wide = block.pivot_table(index="target", columns="method", values="error")
        wide.columns = [f"{family[:4]}/{c}" for c in wide.columns]
        parts.append(wide)
    return pd.concat(parts, axis=1)


# --- one: what the screening kept -------------------------------------------


def survival_table(stem: str, family: str) -> pd.DataFrame:
    frame = read(stem, family)
    frequency = experiment.predictor_frequency(frame)
    table = frequency.pivot_table(index="predictor", columns="horizon", values="share").fillna(0)
    return table.reindex(table.mean(axis=1).sort_values(ascending=False).index)


def seasonal_redundancy(gas: str, names: list[str]) -> pd.DataFrame:
    """How much of each covariate lag the calendar already explains.

    A phase-shifted annual cycle is a linear combination of the same sine and
    cosine, so a lag does not protect a seasonal driver from being restated by
    the seasonal terms. The partial correlation is what is left: the correlation
    between the covariate's non-seasonal part and the flux's non-seasonal part.
    """
    series = load(gas)
    covariates = load_covariates(series.index)
    terms = features.seasonal_terms(series.index)
    residual_flux = preprocessing.SeasonalAdjustment().fit(series).transform(series)
    records = []
    for name in names:
        column, lag = name.rsplit("_lag", 1)
        joined = pd.concat(
            [covariates[column].shift(int(lag)).rename("x"), terms,
             residual_flux.rename("y")], axis=1
        ).dropna()
        design = np.column_stack(
            [np.ones(len(joined)), joined[list(features.SEASONAL_TERMS)].to_numpy()]
        )
        coefficients, *_ = np.linalg.lstsq(design, joined["x"].to_numpy(), rcond=None)
        residual_x = joined["x"].to_numpy() - design @ coefficients
        explained = 1 - residual_x.var() / joined["x"].to_numpy().var()
        correlation, p = stats.pearsonr(residual_x, joined["y"].to_numpy())
        records.append(
            {"predictor": name, "n": len(joined),
             "explained by the calendar": round(float(explained), 3),
             "partial r with the flux": round(float(correlation), 3),
             "p": round(float(p), 4)}
        )
    return pd.DataFrame.from_records(records)


def survivors_worth_testing(stem: str, threshold: float = 0.25) -> list[str]:
    """Covariate lags that survived screening in at least `threshold` of folds."""
    table = survival_table(stem, "exogenous")
    covariate = [name for name in table.index if name.rsplit("_lag", 1)[0] in COVARIATES]
    return [name for name in covariate if table.loc[name].max() >= threshold]


def examination_one() -> None:
    heading("ONE: what the per-fold screening kept")
    for gas, stem in GASES.items():
        for family in ("autoregressive", "exogenous"):
            print(f"\n  {gas} / {family}: share of folds each predictor survived")
            print(survival_table(stem, family).round(2).to_string())
    heading("ONE: are the surviving covariates the season restated?")
    tested: list[str] = []
    print("  Explained-by-the-calendar is the R-squared of the covariate lag on the three")
    print("  seasonal terms. Partial r is what the covariate's non-seasonal part shares")
    print("  with the flux's non-seasonal part.")
    for gas, stem in GASES.items():
        names = survivors_worth_testing(stem)
        if not names:
            print(f"\n  {gas}: no covariate survived in a quarter of folds or more")
            continue
        print(f"\n  {gas}")
        print(seasonal_redundancy(gas, names).to_string(index=False))
        tested.extend(names)
    print(f"\n  {len(tested)} covariate lags tested, so the Bonferroni threshold is "
          f"p = {0.05 / len(tested):.4f}.")


# --- two: where the methane advantage lives ---------------------------------


def examination_two() -> None:
    heading(f"TWO: methane at one month, where ridge's advantage comes from")
    frames, _ = shared("methane")
    err = errors_at(frames, 1)
    ridge, climatology = err["auto/ridge"], err["benc/climatology"]
    saved = climatology.abs() - ridge.abs()

    print("\n  absolute error ridge saves against climatology, by year")
    yearly = saved.groupby(saved.index.year).agg(["size", "sum", "mean"]).round(2)
    yearly.columns = ["months", "nmol saved", "per month"]
    series = load("methane")
    summer = series[series.index.month.isin([6, 7, 8, 9])]
    amplitude = summer.groupby(summer.index.year).mean()
    yearly["summer as a share of normal"] = (amplitude / amplitude.mean()).round(2)
    print(yearly.to_string())

    print(f"\n  ridge against climatology, with and without {ANOMALOUS_YEAR}")
    for label, mask in (
        ("all months", pd.Series(True, index=err.index)),
        (f"excluding {ANOMALOUS_YEAR}", err.index.year != ANOMALOUS_YEAR),
        (f"{ANOMALOUS_YEAR} only", err.index.year == ANOMALOUS_YEAR),
    ):
        block = err[mask]
        result = evaluation.diebold_mariano(block["auto/ridge"], block["benc/climatology"], 1)
        gap = block["benc/climatology"].abs().sum() - block["auto/ridge"].abs().sum()
        print(f"    {label:18s} n = {result['n']:3d}   ridge saves {gap:+7.1f} nmol   "
              f"DM t = {result['statistic']:+.2f}   p = {result['p']:.3f}")

    print(f"\n  what every method saved against climatology in {ANOMALOUS_YEAR} alone (nmol)")
    block = err[err.index.year == ANOMALOUS_YEAR]
    reference = block["benc/climatology"].abs().sum()
    scores = {c: reference - block[c].abs().sum() for c in err.columns if c != "benc/climatology"}
    for name, value in sorted(scores.items(), key=lambda kv: -kv[1]):
        print(f"    {name:34s} {value:+7.1f}")

    print("\n  what ridge weights, fitted at one origin inside the anomaly")
    origin = pd.Period(f"{ANOMALOUS_YEAR}-07", freq="M")
    design, target, _, _ = experiment.fold_matrices(series, origin, 1, None)
    columns = list(features.SEASONAL_TERMS) + [c for c in design.columns
                                               if c.startswith("flux_lag")]
    fitted = models.MODELS["ridge"]().fit(design[columns].to_numpy(), target.to_numpy())
    print(f"    origin {origin}, on the deseasonalized series")
    for name, coefficient in zip(columns, fitted.coef_):
        print(f"      {name:16s} {coefficient:+.3f}")


# --- three: significance, with the overlap accounted for --------------------


def examination_three() -> None:
    heading("THREE: significance with serial correlation accounted for")
    print("  Effective n is the number of forecasts divided by the variance inflation of")
    print("  the loss differential. Above n means the differential alternates rather than")
    print("  persists, which is information rather than an error.")
    for gas, stem in GASES.items():
        frames, _ = shared(stem)
        records = []
        for horizon in evaluation.HORIZONS:
            err = errors_at(frames, horizon)
            climatology = err["benc/climatology"]
            candidates = [c for c in err.columns if not c.startswith("benc")]
            best = err[candidates].abs().mean().idxmin()
            result = evaluation.diebold_mariano(err[best], climatology, horizon)
            wins = int((climatology.abs() > err[best].abs()).sum())
            records.append(
                {"horizon": horizon, "best method": best, "n": result["n"],
                 "effective n": round(result["effective_n"], 1),
                 "DM t": round(result["statistic"], 2), "DM p": round(result["p"], 3),
                 "sign-test p": round(stats.binomtest(wins, len(err), 0.5).pvalue, 3)}
            )
        print(f"\n  {gas}: the best method against climatology")
        print(pd.DataFrame(records).to_string(index=False))

    heading("THREE: machine learning against statistical, the original question")
    print("  Sixteen comparisons, so the Bonferroni threshold is p = 0.0031.")
    for gas, stem in GASES.items():
        frames, _ = shared(stem)
        records = []
        for family in ("autoregressive", "exogenous"):
            for horizon in evaluation.HORIZONS:
                block = frames[family]
                err = block[block["horizon"] == horizon].pivot_table(
                    index="target", columns="method", values="error")
                statistical = err[[c for c in err if models.FAMILY[c] == "statistical"]]
                learning = err[[c for c in err if models.FAMILY[c] == "machine learning"]]
                result = evaluation.diebold_mariano(
                    learning.abs().mean(axis=1), statistical.abs().mean(axis=1), horizon)
                records.append(
                    {"family": family, "horizon": horizon, "n": result["n"],
                     "effective n": round(result["effective_n"], 1),
                     "mean ML - statistical": round(result["mean_difference"], 3),
                     "DM t": round(result["statistic"], 2), "DM p": round(result["p"], 3)}
                )
        print(f"\n  {gas}")
        print(pd.DataFrame(records).to_string(index=False))


def main() -> None:
    pd.set_option("display.width", 220)
    examination_one()
    examination_two()
    examination_three()


if __name__ == "__main__":
    main()
