"""Published budgets this reconstruction will be checked against, and unit conversion.

Olson et al. (2013) report annual budgets for this site as carbon mass, in grams
of carbon per square meter per year. The ingestion layer reports methane mass,
in grams of methane over the same area and period. The two differ by the ratio
of molar masses and are not comparable until converted.
"""

from __future__ import annotations

import pandas as pd

MOLAR_MASS_CH4 = 16.043
MOLAR_MASS_C = 12.011

#: One gram of methane carries this mass of carbon.
C_PER_CH4 = MOLAR_MASS_C / MOLAR_MASS_CH4

OLSON_DOI = "10.1002/jgrg.20031"
OLSON_CITATION = (
    "Olson et al. (2013), Journal of Geophysical Research: Biogeosciences 118, 226-238"
)

#: Annual budgets published by Olson et al. (2013), g C m-2 yr-1.
OLSON_ANNUAL_C = {2009: (11.8, 3.1), 2010: (12.2, 3.0), 2011: (24.9, 5.6)}

#: Range published for the 1991-2011 reconstruction, g C m-2 yr-1.
OLSON_RECONSTRUCTION_C = (7.8, 15.2, 2.7)

#: Growing seasons measured by Shurpali et al. (1993) and Shurpali and Verma
#: (1998), which precede the flux record and are the independent check.
SHURPALI_SEASONS = (1991, 1992)
SHURPALI_CITATIONS = (
    "Shurpali et al. (1993)",
    "Shurpali and Verma (1998)",
)


def carbon_to_methane(grams_carbon: float) -> float:
    """Convert a carbon mass to the methane mass carrying it."""
    return grams_carbon / C_PER_CH4


def methane_to_carbon(grams_methane: float) -> float:
    """Convert a methane mass to the carbon mass it carries."""
    return grams_methane * C_PER_CH4


def published_annual_targets() -> pd.DataFrame:
    """Olson et al. (2013) annual budgets in both mass conventions."""
    records = []
    for year, (value, uncertainty) in sorted(OLSON_ANNUAL_C.items()):
        records.append(
            {
                "year": year,
                "olson_g_C_m2_yr": value,
                "olson_uncertainty_g_C": uncertainty,
                "olson_g_CH4_m2_yr": round(carbon_to_methane(value), 2),
                "olson_uncertainty_g_CH4": round(carbon_to_methane(uncertainty), 2),
            }
        )
    return pd.DataFrame.from_records(records)


def published_reconstruction_range() -> dict[str, float]:
    """The 1991-2011 reconstruction range in both mass conventions."""
    low, high, uncertainty = OLSON_RECONSTRUCTION_C
    return {
        "low_g_C": low,
        "high_g_C": high,
        "uncertainty_g_C": uncertainty,
        "low_g_CH4": round(carbon_to_methane(low), 2),
        "high_g_CH4": round(carbon_to_methane(high), 2),
        "uncertainty_g_CH4": round(carbon_to_methane(uncertainty), 2),
    }


def observed_against_published(annual: pd.DataFrame) -> pd.DataFrame:
    """Place the observed annual budgets beside the published ones, in both units.

    The observed column integrates measured half-hours only. It is not a budget
    for the year, because most of each year is unmeasured, and it is reported
    here to show the size of that shortfall rather than as a comparable figure.
    """
    published = published_annual_targets().set_index("year")
    rows = []
    for year in published.index:
        match = annual[annual["year"] == year]
        observed_ch4 = float(match["observed_only"].iloc[0]) if len(match) else float("nan")
        coverage = float(match["coverage_pct"].iloc[0]) if len(match) else float("nan")
        scaled_ch4 = float(match["coverage_scaled"].iloc[0]) if len(match) else float("nan")
        rows.append(
            {
                "year": year,
                "coverage_pct": coverage,
                "observed_g_CH4": round(observed_ch4, 2),
                "observed_g_C": round(methane_to_carbon(observed_ch4), 2),
                "coverage_scaled_g_CH4": round(scaled_ch4, 2),
                "coverage_scaled_g_C": round(methane_to_carbon(scaled_ch4), 2),
                "olson_g_CH4": published.loc[year, "olson_g_CH4_m2_yr"],
                "olson_g_C": published.loc[year, "olson_g_C_m2_yr"],
            }
        )
    return pd.DataFrame.from_records(rows)


def monthly_flux_to_annual(monthly_flux: pd.Series) -> pd.DataFrame:
    """Integrate monthly mean flux to annual budgets in both mass conventions.

    Each month contributes its mean flux held over that month's own length, so
    month lengths are not treated as equal. Years represented by only part of
    their months yield a partial total, and the month count is carried alongside
    so a partial year is not read as a whole one.
    """
    frame = pd.DataFrame({"flux": monthly_flux.astype(float)})
    frame["seconds"] = [p.days_in_month * 86400 for p in frame.index]
    frame["g_CH4"] = frame["flux"] * frame["seconds"] * 1e-9 * MOLAR_MASS_CH4
    frame["year"] = [p.year for p in frame.index]

    grouped = frame.groupby("year")
    out = pd.DataFrame({"n_months": grouped.size(), "g_CH4_m2": grouped["g_CH4"].sum()})
    out["g_C_m2"] = out["g_CH4_m2"] * C_PER_CH4
    return out.round(3)


def holdout_against_published(annual: pd.DataFrame) -> pd.DataFrame:
    """Place out-of-sample annual budgets beside the published ones.

    This is the comparison that carries weight, because the months being
    integrated were withheld from the fit that produced them.
    """
    published = published_annual_targets().set_index("year")
    rows = []
    for year in published.index:
        if year not in annual.index:
            continue
        row = annual.loc[year]
        rows.append(
            {
                "year": year,
                "n_months_integrated": int(row["n_months"]),
                "predicted_g_C_m2": round(float(row["g_C_m2"]), 2),
                "olson_g_C_m2": published.loc[year, "olson_g_C_m2_yr"],
                "olson_uncertainty_g_C": published.loc[year, "olson_uncertainty_g_C"],
                "difference_g_C": round(float(row["g_C_m2"]) - published.loc[year, "olson_g_C_m2_yr"], 2),
                "within_olson_interval": bool(
                    abs(float(row["g_C_m2"]) - published.loc[year, "olson_g_C_m2_yr"])
                    <= published.loc[year, "olson_uncertainty_g_C"]
                ),
            }
        )
    return pd.DataFrame.from_records(rows)


def independent_check_coverage(methane_months: pd.PeriodIndex) -> pd.DataFrame:
    """Observations this record holds for the seasons measured before it began."""
    records = []
    for year in SHURPALI_SEASONS:
        season = pd.period_range(f"{year}-05", f"{year}-10", freq="M")
        present = season.intersection(pd.PeriodIndex(methane_months, freq="M"))
        records.append(
            {
                "growing_season": f"{year}-05..{year}-10",
                "months_in_season": len(season),
                "months_observed_here": len(present),
            }
        )
    return pd.DataFrame.from_records(records)
