"""Coverage of the merged series against the calendar, by month and analyser.

Deventer et al. (2019) note that open-path systems lose data during freezing or
rainy periods and that snow cover at this site lasts roughly 120 days. Where
coverage is seasonally uneven, the pooled observed mean is a biased estimate of
the annual mean and any budget scaled from it inherits that bias.
"""

from __future__ import annotations

import calendar

import pandas as pd

from . import site

HALFHOURS_PER_DAY = 48


def _possible_halfhours(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1] * HALFHOURS_PER_DAY


def possible_by_year_month(merged: pd.DataFrame) -> pd.DataFrame:
    """Slots the calendar allows, per year-month, over the record's span."""
    stamps = merged["timestamp_start"]
    index = pd.period_range(stamps.min(), stamps.max(), freq="M")
    return pd.DataFrame(
        {
            "year": index.year,
            "month_of_year": index.month,
            "possible": [_possible_halfhours(p.year, p.month) for p in index],
        },
        index=index,
    ).rename_axis("month")


def coverage_by_month_of_year(merged: pd.DataFrame) -> pd.DataFrame:
    """Valid fraction per calendar month pooled across years, split by analyser."""
    observed = merged.dropna(subset=["fch4"]).copy()
    observed["month_of_year"] = observed["timestamp_start"].dt.month

    possible = possible_by_year_month(merged).groupby("month_of_year")["possible"].sum()
    counts = observed.groupby(["month_of_year", "analyzer"]).size().unstack(fill_value=0)
    counts.columns = [site.analyzer_slug(c) for c in counts.columns]
    counts = counts.reindex(columns=list(site.SLUGS), fill_value=0)

    out = counts.reindex(range(1, 13), fill_value=0)
    out["observed"] = out[list(site.SLUGS)].sum(axis=1)
    out["possible"] = possible.reindex(out.index)
    for column in [*site.SLUGS, "observed"]:
        out[f"frac_{column}"] = out[column] / out["possible"]
    out.index.name = "month_of_year"
    return out.reset_index()


def coverage_by_year_and_month(merged: pd.DataFrame) -> pd.DataFrame:
    """Valid fraction per calendar month within each year, split by analyser."""
    observed = merged.dropna(subset=["fch4"]).copy()
    observed["year"] = observed["timestamp_start"].dt.year
    observed["month_of_year"] = observed["timestamp_start"].dt.month

    counts = (
        observed.groupby(["year", "month_of_year", "analyzer"])
        .size()
        .unstack(fill_value=0)
    )
    counts.columns = [site.analyzer_slug(c) for c in counts.columns]
    counts = counts.reindex(columns=list(site.SLUGS), fill_value=0)

    possible = possible_by_year_month(merged).set_index(["year", "month_of_year"])["possible"]
    out = counts.join(possible, how="right").fillna(0)
    out[list(site.SLUGS)] = out[list(site.SLUGS)].astype(int)
    out["observed"] = out[list(site.SLUGS)].sum(axis=1)
    out["frac_observed"] = out["observed"] / out["possible"]
    return out.reset_index()


def coverage_matrix(merged: pd.DataFrame) -> pd.DataFrame:
    """Year by month-of-year grid of observed fraction, for inspecting seasonality."""
    per = coverage_by_year_and_month(merged)
    return per.pivot(index="year", columns="month_of_year", values="frac_observed")


def seasonal_bias_summary(merged: pd.DataFrame, winter=(11, 12, 1, 2, 3), summer=(6, 7, 8)) -> dict[str, float]:
    """Contrast cold-season and growing-season coverage and their mean fluxes."""
    pooled = coverage_by_month_of_year(merged).set_index("month_of_year")
    observed = merged.dropna(subset=["fch4"]).copy()
    observed["month_of_year"] = observed["timestamp_start"].dt.month
    means = observed.groupby("month_of_year")["fch4"].mean()

    winter_cov = pooled.loc[list(winter), "observed"].sum() / pooled.loc[list(winter), "possible"].sum()
    summer_cov = pooled.loc[list(summer), "observed"].sum() / pooled.loc[list(summer), "possible"].sum()
    return {
        "winter_coverage": float(winter_cov),
        "summer_coverage": float(summer_cov),
        "summer_minus_winter": float(summer_cov - winter_cov),
        "coverage_ratio": float(summer_cov / winter_cov),
        "winter_mean_flux": float(means.loc[list(winter)].mean()),
        "summer_mean_flux": float(means.loc[list(summer)].mean()),
    }
