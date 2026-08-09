"""Covariate transforms, chosen for how each behaves outside the fitted range.

Soil temperature enters as degrees Celsius against a logarithmic response, which
makes the fitted relationship a first-order exponential and its slope a Q10, the
factor by which flux multiplies per ten degrees of warming. Deventer et al.
(2019) measured that form at this site.

Water table enters clamped to the range seen in training. Beyond that range the
term holds at its edge value, so the model asserts no trend where it has no
observations, which matters because much of the period to be reconstructed lies
above the observed range.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SOIL_TEMP = "soil_temp_f"
WATER_TABLE = "wte_m"


def fahrenheit_to_celsius(values: pd.Series) -> pd.Series:
    """Convert Fahrenheit to Celsius, the scale on which a Q10 is defined."""
    return (values - 32.0) * 5.0 / 9.0


def clamp_bounds(covariates: pd.DataFrame, months: pd.PeriodIndex, column: str) -> tuple[float, float]:
    """Lowest and highest value of a covariate over the given months."""
    values = covariates.loc[months, column].dropna()
    return float(values.min()), float(values.max())


def clamp(values: pd.Series, bounds: tuple[float, float]) -> pd.Series:
    """Hold values at the edge of the range rather than letting them run past it."""
    return values.clip(lower=bounds[0], upper=bounds[1])


def warming_limb(covariates: pd.DataFrame, months: pd.PeriodIndex) -> pd.Series:
    """Whether soil temperature was rising into each month.

    Feng et al. (2020) report that the methane response to soil temperature at
    this site differs between the warming and cooling limbs of the annual cycle.
    The limb is taken from the sign of the change in soil temperature over the
    preceding month, computed on the full covariate record so that the first
    month of a subset is not left undefined.
    """
    full = covariates[SOIL_TEMP].sort_index()
    rising = full.diff() > 0
    return rising.reindex(pd.PeriodIndex(months, freq="M")).fillna(False)


def build_design(
    covariates: pd.DataFrame,
    months: pd.PeriodIndex,
    water_table_bounds: tuple[float, float] | None,
    include_water_table: bool = True,
    include_hysteresis: bool = False,
) -> pd.DataFrame:
    """Design matrix for the given months, with an intercept column first.

    ``water_table_bounds`` must come from the training months alone, so that a
    holdout or reconstruction month cannot widen the range the model treats as
    observed.
    """
    frame = pd.DataFrame(index=pd.PeriodIndex(months, freq="M"))
    frame["intercept"] = 1.0
    frame["soil_temp_c"] = fahrenheit_to_celsius(covariates.loc[months, SOIL_TEMP])
    if include_water_table:
        if water_table_bounds is None:
            raise ValueError("water table bounds are required when the term is included")
        frame["water_table_clamped"] = clamp(
            covariates.loc[months, WATER_TABLE], water_table_bounds
        )
    if include_hysteresis:
        # An interaction, so the warming limb carries its own temperature slope
        # while the cooling limb keeps the base slope.
        rising = warming_limb(covariates, months).astype(float)
        frame["warming_limb"] = rising
        frame["soil_temp_c_warming"] = frame["soil_temp_c"] * rising
    return frame


def log_target(monthly: pd.DataFrame, months: pd.PeriodIndex, column: str = "fch4_mean") -> pd.Series:
    """Natural logarithm of the monthly mean flux, the scale the model fits on."""
    values = monthly.loc[months, column]
    if (values <= 0).any():
        raise ValueError("log target requires strictly positive monthly means")
    return np.log(values)


def log_standard_error(
    monthly: pd.DataFrame,
    months: pd.PeriodIndex,
    mean_column: str = "fch4_mean",
    se_column: str = "fch4_se_across_days",
) -> pd.Series:
    """Standard error of each monthly mean carried onto the logarithmic scale.

    A first-order propagation, standard error divided by the mean, which is
    adequate while the relative error stays small.
    """
    return monthly.loc[months, se_column] / monthly.loc[months, mean_column]


def q10_from_slope(slope: float) -> float:
    """Q10 implied by a slope on log flux per degree Celsius."""
    return float(np.exp(10.0 * slope))


def slope_from_q10(q10: float) -> float:
    """Slope on log flux per degree Celsius implied by a Q10."""
    return float(np.log(q10) / 10.0)
