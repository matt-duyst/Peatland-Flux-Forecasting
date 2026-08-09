"""Where a model's error sits, and whether it concentrates or spreads.

A shortfall in an annual total can arise two ways. It can be spread across the
year, which points to a mis-specified seasonal response, or it can sit in one or
two months, which points to episodes the covariates do not describe. Irvin et
al. (2021) note that episodic fluxes, ebullition among them, are often missed by
gap-filling models and replaced with averages for comparable conditions. The two
have different implications, so they are worth separating.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import targets


def monthly_comparison(observed_flux: pd.Series, predicted_flux: pd.Series) -> pd.DataFrame:
    """Observed against predicted flux per month, with each month's mass contribution.

    Contributions are in grams of carbon per square meter, so a month's share of
    an annual shortfall can be read directly.
    """
    months = observed_flux.index.intersection(predicted_flux.index)
    frame = pd.DataFrame(
        {"observed": observed_flux.reindex(months), "predicted": predicted_flux.reindex(months)}
    )
    seconds = np.array([p.days_in_month * 86400 for p in frame.index], dtype=float)
    factor = seconds * 1e-9 * targets.MOLAR_MASS_CH4 * targets.C_PER_CH4
    frame["observed_g_C"] = frame["observed"] * factor
    frame["predicted_g_C"] = frame["predicted"] * factor
    frame["shortfall_g_C"] = frame["observed_g_C"] - frame["predicted_g_C"]
    frame["ratio"] = frame["predicted"] / frame["observed"]
    return frame


def concentration(comparison: pd.DataFrame, column: str = "shortfall_g_C") -> dict[str, object]:
    """How much of the total shortfall the largest few months carry.

    A shortfall concentrated in one or two months is an episode problem. One
    spread evenly is a seasonal-response problem.
    """
    values = comparison[column]
    total = float(values.sum())
    ranked = values.sort_values(ascending=False)
    positive = ranked[ranked > 0]
    out: dict[str, object] = {
        "total_shortfall_g_C": total,
        "n_months": int(len(values)),
        "n_months_under_predicted": int((values > 0).sum()),
    }
    for k in (1, 2, 3):
        if len(ranked) >= k:
            out[f"top_{k}_share_of_total_pct"] = round(100 * float(ranked.iloc[:k].sum()) / total, 1) if total else float("nan")
    out["largest_month"] = str(ranked.index[0])
    out["largest_month_g_C"] = round(float(ranked.iloc[0]), 3)
    out["sum_of_positive_shortfalls_g_C"] = round(float(positive.sum()), 3)
    return out


def covariate_anomaly(
    covariates: pd.DataFrame,
    target_months: pd.PeriodIndex,
    reference_months: pd.PeriodIndex,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    """How a period's covariates differ from a reference period, in native and standard units."""
    records = []
    for column in columns:
        target = covariates.loc[target_months, column].dropna()
        reference = covariates.loc[reference_months, column].dropna()
        spread = reference.std(ddof=1)
        records.append(
            {
                "covariate": column,
                "period_mean": round(float(target.mean()), 3),
                "reference_mean": round(float(reference.mean()), 3),
                "difference": round(float(target.mean() - reference.mean()), 3),
                "standardized": round(float((target.mean() - reference.mean()) / spread), 2) if spread else np.nan,
                "period_max": round(float(target.max()), 3),
                "reference_max": round(float(reference.max()), 3),
            }
        )
    return pd.DataFrame.from_records(records)


def extreme_months(
    observed_flux: pd.Series, reference: pd.Series, n: int = 5
) -> pd.DataFrame:
    """Months whose flux stands furthest above the same calendar month elsewhere."""
    frame = pd.DataFrame({"flux": observed_flux})
    frame["month_of_year"] = [p.month for p in frame.index]
    climatology = reference.groupby([p.month for p in reference.index])
    frame["reference_mean"] = frame["month_of_year"].map(climatology.mean())
    frame["reference_sd"] = frame["month_of_year"].map(climatology.std(ddof=1))
    # A calendar month with one reference observation, or several identical ones,
    # has no spread to standardize by; leave those undefined rather than infinite.
    spread = frame["reference_sd"].where(frame["reference_sd"] > 0)
    frame["standardized"] = (frame["flux"] - frame["reference_mean"]) / spread
    out = frame.nlargest(n, "standardized")[["flux", "reference_mean", "reference_sd", "standardized"]]
    out.index = out.index.astype(str)
    return out.round(3)
