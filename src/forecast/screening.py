"""Feature screening by shadow comparison, following Li et al. (2026).

Pearson and Spearman correlations cannot see a nonlinear relationship, and
Deventer et al. (2019) established that the water table response at this site is
neither linear nor log-linear. The original 2022 work selected predictors from a
Pearson ranking computed over the whole record, which was both the wrong measure
and a use of data the models were later scored on.

Boruta compares each predictor against a shadow of itself: the same column with
its rows permuted, which keeps the marginal distribution and destroys the
relationship. Each repeat is one trial, and a predictor that carries nothing
should beat the best shadow about as often as not. A predictor is kept when it
beats the shadows more often than a fair coin plausibly would, at the five
percent level. Seasonal terms are retained regardless, as in Li et al., because
the question is what remains after the season rather than whether a season exists.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from scipy import stats

ITERATIONS = 20
ALPHA = 0.05


def hit_threshold(iterations: int = ITERATIONS, alpha: float = ALPHA) -> int:
    """Hits a predictor needs before its record stops looking like a coin.

    Under the null a predictor beats the best shadow with probability one half,
    so the count of hits is binomial. This returns the smallest count whose upper
    tail is no larger than `alpha`, which is twenty for twenty repeats at five
    percent when nothing else is said.
    """
    for count in range(iterations + 1):
        if stats.binom.sf(count - 1, iterations, 0.5) <= alpha:
            return count
    return iterations + 1


def boruta_select(
    design: pd.DataFrame,
    target: pd.Series,
    always_keep: Sequence[str] = (),
    iterations: int = ITERATIONS,
    alpha: float = ALPHA,
    seed: int = 20110801,
) -> list[str]:
    """Predictors worth keeping, plus any named as always kept.

    Returns the always-kept columns alone if nothing else survives, so a caller
    is never handed an empty design.
    """
    usable = design.dropna()
    aligned = target.reindex(usable.index).dropna()
    usable = usable.loc[aligned.index]
    candidates = [c for c in usable.columns if c not in always_keep]
    if len(aligned) < 12 or not candidates:
        return list(always_keep) + candidates

    rng = np.random.default_rng(seed)
    wins = dict.fromkeys(candidates, 0)
    values = usable[candidates].to_numpy()

    for iteration in range(iterations):
        shadow = np.column_stack([rng.permutation(values[:, j]) for j in range(values.shape[1])])
        combined = np.hstack([values, shadow])
        forest = RandomForestRegressor(
            n_estimators=100, random_state=seed + iteration, n_jobs=1
        ).fit(combined, aligned.to_numpy())
        importance = forest.feature_importances_
        threshold = importance[len(candidates):].max()
        for position, name in enumerate(candidates):
            if importance[position] > threshold:
                wins[name] += 1

    needed = hit_threshold(iterations, alpha)
    kept = [name for name in candidates if wins[name] >= needed]
    return list(always_keep) + kept
