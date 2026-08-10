"""Rolling-origin evaluation of the forecasting methods themselves.

The output frame has the same columns as `evaluation.rolling_forecasts`, so the
benchmarks and the models are scored by exactly the same code. Everything that
could leak is done inside the fold: the month-of-year means are learned from the
training window, the screening is rerun on the training rows, and the model sees
the test row only to predict it.

Two families are run and reported separately. The autoregressive family uses the
flux's own past and the calendar. The exogenous family adds lagged covariates.
Pooling them would put a model that can see the weather against one that cannot,
which is a comparison of information rather than of method.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from forecast import evaluation, features, models, preprocessing, screening

#: Rows a fold needs after lagging before it is worth fitting anything to.
MIN_DESIGN_ROWS = 24


def fold_matrices(
    series: pd.Series,
    origin: pd.Period,
    horizon: int,
    exogenous: pd.DataFrame | None,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, preprocessing.SeasonalAdjustment] | None:
    """Training design, training target and the single test row for one fold.

    The seasonal adjustment is fitted on the training window alone and returned
    so the caller can put the season back on the prediction.
    """
    target_month = origin + horizon
    if target_month > series.index[-1]:
        return None

    adjustment = preprocessing.SeasonalAdjustment().fit(series.loc[:origin])
    adjusted = adjustment.transform(series)

    design = features.build_design(adjusted, horizon, exogenous)
    train = design.loc[:origin].join(adjusted.rename("y")).dropna()
    if len(train) < MIN_DESIGN_ROWS:
        return None
    if target_month not in design.index:
        return None
    test = design.loc[[target_month]]
    if test.isna().to_numpy().any():
        return None
    return train.drop(columns="y"), train["y"], test, adjustment


def run(
    series: pd.Series,
    exogenous: pd.DataFrame | None = None,
    methods: dict | None = None,
    min_train: int = evaluation.MIN_TRAIN,
    horizons: Sequence[int] = evaluation.HORIZONS,
    period: int = evaluation.PERIOD,
    screen: bool = True,
) -> pd.DataFrame:
    """One row per origin, method and horizon, scored like any other method."""
    methods = methods or models.MODELS
    rows = []
    for origin in evaluation.origins(series, min_train, horizons):
        train_window = series.loc[:origin]
        scale = evaluation.mase_scale(train_window, period)
        for horizon in horizons:
            prepared = fold_matrices(series, origin, horizon, exogenous)
            if prepared is None:
                continue
            design, adjusted_target, test, adjustment = prepared
            # Screening happens once per fold and horizon, and every method in
            # the fold sees the same predictors. Running it per method would
            # confound the choice of predictors with the choice of method.
            kept = (
                screening.boruta_select(design, adjusted_target,
                                        always_keep=features.SEASONAL_TERMS)
                if screen else list(design.columns)
            )
            target_month = origin + horizon
            for name, build in methods.items():
                fitted = build().fit(design[kept].to_numpy(), adjusted_target.to_numpy())
                adjusted_prediction = float(fitted.predict(test[kept].to_numpy())[0])
                forecast = adjustment.inverse(
                    pd.Series([adjusted_prediction], index=pd.PeriodIndex([target_month],
                                                                          freq=series.index.freq))
                ).iloc[0]
                rows.append(
                    {
                        "origin": origin, "method": name, "horizon": horizon,
                        "target": target_month, "forecast": float(forecast),
                        "actual": series.get(target_month, np.nan),
                        "train_n": int(train_window.notna().sum()),
                        "mase_scale": scale,
                        "n_predictors": len(kept),
                        "predictors": ", ".join(kept),
                    }
                )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["error"] = frame["actual"] - frame["forecast"]
    frame["scaled"] = frame["error"].abs() / frame["mase_scale"]
    return frame


def predictor_frequency(frame: pd.DataFrame) -> pd.DataFrame:
    """How often each predictor survived screening, by horizon.

    A predictor kept in almost every fold is a stable finding. One kept in a
    third of them is the screening reacting to the training window, which is
    worth seeing rather than hiding behind a single whole-record ranking.
    """
    counts = []
    for horizon, block in frame.groupby("horizon"):
        folds = block.drop_duplicates(subset=["origin"])
        total = len(folds)
        tally: dict[str, int] = {}
        for names in folds["predictors"]:
            for name in names.split(", "):
                tally[name] = tally.get(name, 0) + 1
        for name, count in tally.items():
            counts.append({"horizon": horizon, "predictor": name,
                           "folds": count, "share": round(count / total, 3)})
    return pd.DataFrame(counts).sort_values(["horizon", "share"], ascending=[True, False])
