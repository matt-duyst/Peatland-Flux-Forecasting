"""Whether the water table coefficient survives narrowing the range it is fitted on.

Extrapolating a coefficient beyond the observed range assumes the coefficient is
a property of the system rather than of the sample. That assumption is testable
without leaving the record: refit on progressively drier subsets and watch the
coefficient as its supporting range shrinks. A coefficient that holds is a
candidate for extrapolation; one that drifts or changes sign is not.

Bootstrap resampling is the only stochastic step in the study. Its seed is fixed
here and reported with the results.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import features, fitting

SEED = 20110801
DROP_SHARES = (0.0, 0.10, 0.20, 0.30, 0.40)
WATER_TABLE = features.WATER_TABLE


def drier_subset(covariates: pd.DataFrame, months: pd.PeriodIndex, drop_share: float) -> pd.PeriodIndex:
    """Months remaining after removing the wettest share of them."""
    if not 0.0 <= drop_share < 1.0:
        raise ValueError("drop_share must be at least zero and below one")
    values = covariates.loc[months, WATER_TABLE].dropna().sort_values()
    keep = len(values) - int(round(drop_share * len(values)))
    return pd.PeriodIndex(values.index[:keep], freq="M").sort_values()


def _bootstrap_coefficients(
    design: pd.DataFrame,
    target: pd.Series,
    weights: pd.Series | None,
    n_bootstrap: int,
    seed: int,
) -> pd.DataFrame:
    """Refit on resampled months to get a distribution-free coefficient interval."""
    rng = np.random.default_rng(seed)
    index = np.arange(len(target))
    draws = []
    for _ in range(n_bootstrap):
        picked = rng.choice(index, size=len(index), replace=True)
        months = target.index[picked]
        try:
            resampled = fitting.fit_lad(
                design.iloc[picked].reset_index(drop=True),
                target.iloc[picked].reset_index(drop=True),
                None if weights is None else weights.reindex(months).reset_index(drop=True),
            )
        except (RuntimeError, ValueError):
            continue
        draws.append(resampled.as_series())
    return pd.DataFrame(draws)


def coefficient_path(
    covariates: pd.DataFrame,
    monthly: pd.DataFrame,
    months: pd.PeriodIndex,
    drop_shares: tuple[float, ...] = DROP_SHARES,
    weights: pd.Series | None = None,
    n_bootstrap: int = 500,
    seed: int = SEED,
) -> pd.DataFrame:
    """Track each coefficient as the wettest months are progressively removed.

    The water table term is left unclamped, since the question is what the fitted
    slope does, not how it is capped at prediction time.
    """
    records = []
    for share in drop_shares:
        subset = drier_subset(covariates, months, share)
        bounds = features.clamp_bounds(covariates, subset, WATER_TABLE)
        design = features.build_design(covariates, subset, bounds, include_water_table=True)
        target = features.log_target(monthly, subset)
        subset_weights = None if weights is None else weights.reindex(subset).dropna()

        fit = fitting.fit_lad(design, target, subset_weights)
        draws = _bootstrap_coefficients(design, target, subset_weights, n_bootstrap, seed)
        water = draws["water_table_clamped"]
        soil = draws["soil_temp_c"]

        records.append(
            {
                "dropped_wettest_pct": round(100 * share),
                "n_months": len(subset),
                "wte_min": round(float(covariates.loc[subset, WATER_TABLE].min()), 3),
                "wte_max": round(float(covariates.loc[subset, WATER_TABLE].max()), 3),
                "wte_range": round(float(covariates.loc[subset, WATER_TABLE].max() - covariates.loc[subset, WATER_TABLE].min()), 3),
                "water_table_coef": float(fit.as_series()["water_table_clamped"]),
                "water_table_lo": float(water.quantile(0.025)),
                "water_table_hi": float(water.quantile(0.975)),
                "water_table_includes_zero": bool(
                    water.quantile(0.025) <= 0.0 <= water.quantile(0.975)
                ),
                "q10": features.q10_from_slope(float(fit.as_series()["soil_temp_c"])),
                "q10_lo": features.q10_from_slope(float(soil.quantile(0.025))),
                "q10_hi": features.q10_from_slope(float(soil.quantile(0.975))),
                "n_bootstrap_ok": len(draws),
            }
        )
    return pd.DataFrame.from_records(records)


def verdict(path: pd.DataFrame, max_drift: float = 0.25, trend_alpha: float = 0.05) -> dict[str, object]:
    """Whether the coefficient held across the narrowing range, and what follows.

    Stability requires four things: the sign never changes, no step's interval
    spans zero, the coefficient moves by less than ``max_drift`` of its
    full-range value, and it shows no monotone trend against the share removed.
    The trend test matters most. A coefficient that climbs steadily as its
    supporting range narrows is a property of the sample rather than of the
    system, and containment inside a wide full-range interval does not redeem it.
    """
    from scipy import stats

    baseline = float(path["water_table_coef"].iloc[0])
    signs = np.sign(path["water_table_coef"])
    sign_changes = int((signs != signs.iloc[0]).sum())
    spans_zero = int(path["water_table_includes_zero"].sum())
    spread = float(path["water_table_coef"].max() - path["water_table_coef"].min())
    drift = spread / abs(baseline) if baseline else float("inf")
    trend, trend_p = stats.spearmanr(path["dropped_wettest_pct"], path["water_table_coef"])

    failures = []
    if sign_changes:
        failures.append("the sign changes")
    if spans_zero:
        failures.append(f"the interval spans zero at {spans_zero} of {len(path)} steps")
    if drift > max_drift:
        failures.append(f"the coefficient drifts by {100 * drift:.0f}% of its full-range value")
    if abs(trend) >= 0.9 and trend_p < trend_alpha:
        failures.append("the coefficient trends monotonically as the range narrows")

    stable = not failures
    return {
        "baseline_coefficient": baseline,
        "sign_changes": sign_changes,
        "steps_whose_interval_spans_zero": spans_zero,
        "coefficient_spread": spread,
        "relative_drift": drift,
        "trend_with_share_removed": float(trend),
        "trend_p_value": float(trend_p),
        "stable": stable,
        "failures": failures,
        "bracket_meaning": (
            "linear continuation is a defensible aggressive bound"
            if stable
            else "no linear continuation is trustworthy outside the fitted range"
        ),
    }
