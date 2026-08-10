"""The methods being compared, and the families they are kept in.

The families are separated because they answer different questions. The
autoregressive family uses only the flux's own past and the calendar, so every
predictor is known at the origin and a twelve-month horizon is genuine. The
exogenous family adds lagged covariates, which is honest but reaches only as far
as the shortest lag allows, and pooling the two would compare a model that can
see the weather against one that cannot.
"""

from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge

SEED = 20110801

#: Statistical methods, in the sense the 2018 comparisons use the word.
STATISTICAL = {
    "ordinary least squares": lambda: LinearRegression(),
    "ridge": lambda: Ridge(alpha=1.0),
}

#: Machine learning methods. Both are regularized by construction, which is what
#: Li et al. rely on when lagged predictors make the design collinear.
MACHINE_LEARNING = {
    "random forest": lambda: RandomForestRegressor(
        n_estimators=300, min_samples_leaf=2, random_state=SEED, n_jobs=1
    ),
    "gradient boosting": lambda: HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
        l2_regularization=1.0, early_stopping=True, validation_fraction=0.2,
        random_state=SEED
    ),
}

MODELS = {**STATISTICAL, **MACHINE_LEARNING}

#: Which family each method belongs to, for reporting.
FAMILY = {name: ("statistical" if name in STATISTICAL else "machine learning")
          for name in MODELS}
