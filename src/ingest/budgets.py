"""Annual methane budgets integrated from observed half-hours, against published values.

Estimates here use only half-hours that were actually measured. Because roughly
two thirds of each year is missing, they fall well short of the gap-filled
annual emissions published by Deventer et al. (2019); the difference measures
how much of an annual budget rests on inference rather than observation.
"""

from __future__ import annotations

import pandas as pd

from . import coverage, site

HALFHOURS_PER_YEAR = 17520


def annual_budget(merged: pd.DataFrame) -> pd.DataFrame:
    """Integrate observed half-hours per year and compare with published budgets.

    ``observed_only`` sums the measured half-hours alone. ``coverage_scaled``
    applies the same mean across a full year, which assumes gaps resemble
    observations and so serves to size the shortfall rather than to fill it.
    """
    values = merged.dropna(subset=["fch4"]).copy()
    values["year"] = values["timestamp_start"].dt.year
    grouped = values.groupby("year")["fch4"]

    out = pd.DataFrame({"n_halfhours": grouped.size().astype("int64"), "mean_flux": grouped.mean()})
    slots = (
        merged.assign(year=merged["timestamp_start"].dt.year)
        .groupby("year")
        .size()
        .rename("slots_in_year")
    )
    out = out.join(slots)
    out["coverage_pct"] = (100 * out["n_halfhours"] / out["slots_in_year"]).round(1)
    out["observed_only"] = out["n_halfhours"] * out["mean_flux"] * site.NMOL_S_TO_G_PER_HALFHOUR
    out["coverage_scaled"] = (
        out["mean_flux"] * HALFHOURS_PER_YEAR * site.NMOL_S_TO_G_PER_HALFHOUR
    )
    out["published"] = out.index.map(site.PUBLISHED_ANNUAL_BUDGET)
    out["observed_pct_of_published"] = (100 * out["observed_only"] / out["published"]).round(1)
    out["shortfall_g"] = out["published"] - out["observed_only"]
    out.index.name = "year"
    return out.reset_index()


def annual_budget_month_weighted(merged: pd.DataFrame) -> pd.DataFrame:
    """Annual mean as a calendar-weighted average of monthly means.

    Each month contributes in proportion to its share of the year rather than
    to how many observations it happened to yield, so uneven coverage across
    months cannot tilt the annual mean. Weights are renormalised over months
    that have data; months with none are counted and reported, not imputed.
    """
    values = merged.dropna(subset=["fch4"]).copy()
    values["year"] = values["timestamp_start"].dt.year
    values["month_of_year"] = values["timestamp_start"].dt.month
    monthly_mean = values.groupby(["year", "month_of_year"])["fch4"].mean().rename("mean")

    possible = coverage.possible_by_year_month(merged).set_index(
        ["year", "month_of_year"]
    )["possible"]
    joined = pd.concat([monthly_mean, possible], axis=1).dropna(subset=["mean"])

    records = []
    for year, group in joined.groupby(level="year"):
        weights = group["possible"]
        weighted_mean = float((group["mean"] * weights).sum() / weights.sum())
        records.append(
            {
                "year": int(year),
                "months_with_data": int(len(group)),
                "weighted_mean_flux": weighted_mean,
                "month_weighted": weighted_mean
                * HALFHOURS_PER_YEAR
                * site.NMOL_S_TO_G_PER_HALFHOUR,
            }
        )
    return pd.DataFrame.from_records(records)


def budget_method_comparison(merged: pd.DataFrame) -> pd.DataFrame:
    """Compare pooled-mean scaling with calendar-weighted monthly means.

    Divergence between the two estimates is the coverage bias carried by the
    pooled mean, which uneven monthly sampling would otherwise hide.
    """
    pooled = annual_budget(merged)[
        ["year", "coverage_pct", "mean_flux", "observed_only", "coverage_scaled", "published"]
    ]
    weighted = annual_budget_month_weighted(merged)
    out = pooled.merge(weighted, on="year", how="left")
    out["divergence_g"] = out["coverage_scaled"] - out["month_weighted"]
    out["divergence_pct"] = 100 * out["divergence_g"] / out["month_weighted"]
    out["weighted_pct_of_published"] = 100 * out["month_weighted"] / out["published"]
    return out


def budget_gap(annual: pd.DataFrame) -> pd.DataFrame:
    """Restrict to the years covered by Deventer et al. (2019)."""
    published_years = sorted(site.PUBLISHED_ANNUAL_BUDGET)
    columns = [
        "year",
        "n_halfhours",
        "coverage_pct",
        "mean_flux",
        "observed_only",
        "coverage_scaled",
        "published",
        "observed_pct_of_published",
        "shortfall_g",
    ]
    return annual[annual["year"].isin(published_years)][columns].reset_index(drop=True)
