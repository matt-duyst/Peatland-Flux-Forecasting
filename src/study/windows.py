"""Fit and reconstruction windows, and the covariate coverage that bounds them.

A month can enter the fit window only if methane and every covariate are present
for it, so the window is bounded by whichever covariate ends earliest, not by
the methane record. Carbon dioxide flux is excluded from the reconstruction
covariates: it begins in 2009 alongside the methane record and so offers no
values over the period being reconstructed.
"""

from __future__ import annotations

import pandas as pd

#: Covariates available both during and before the methane record.
RECONSTRUCTION_COVARIATES = ("soil_temp_f", "atm_temp_f", "precip_in", "wte_m")

#: Present only from 2009 onward, and therefore unusable for reconstruction.
CONTEMPORANEOUS_ONLY = ("fco2",)

#: Months whose water table is not credible as a measurement. Both sit about
#: 0.8 m below their neighbors and recover within one month, and both are the
#: lowest value on record for their calendar month by a wide margin. Fitting on
#: values established as instrument error is fitting on instrument error, so the
#: study excludes them and the fit window is 115 months rather than 117.
#:
#: This is the single source for that exclusion. It lived in `study.figures` for
#: a time, which meant the figures described the adopted window while every table
#: described the nominal one; `notes/study.md` records that defect and its fix.
WATER_TABLE_ARTIFACTS = (pd.Period("2019-06", freq="M"), pd.Period("2019-09", freq="M"))


def covariate_coverage(covariates: pd.DataFrame) -> pd.DataFrame:
    """First and last month, count, and interior gaps for each covariate."""
    records = []
    for column in covariates.columns:
        if column.endswith("_n"):
            continue
        series = covariates[column].dropna()
        span = pd.period_range(series.index.min(), series.index.max(), freq="M")
        gaps = span.difference(series.index)
        records.append(
            {
                "covariate": column,
                "first": str(series.index.min()),
                "last": str(series.index.max()),
                "n_months": len(series),
                "span_months": len(span),
                "n_interior_gaps": len(gaps),
                "interior_gaps": ", ".join(str(g) for g in gaps),
                "reconstruction_capable": column in RECONSTRUCTION_COVARIATES,
            }
        )
    return pd.DataFrame.from_records(records)


def complete_covariate_months(
    covariates: pd.DataFrame, columns: tuple[str, ...] = RECONSTRUCTION_COVARIATES
) -> pd.PeriodIndex:
    """Months holding a value for every named covariate."""
    return pd.PeriodIndex(covariates[list(columns)].dropna().index, freq="M")


def build_windows(
    covariates: pd.DataFrame,
    methane_months: pd.PeriodIndex,
    columns: tuple[str, ...] = RECONSTRUCTION_COVARIATES,
    exclude: tuple[pd.Period, ...] = WATER_TABLE_ARTIFACTS,
) -> dict[str, pd.PeriodIndex]:
    """Split the complete-covariate months into fit and reconstruction sets.

    The fit window is every month carrying both methane and a complete covariate
    set, less any month named in `exclude`. The reconstruction window is every
    complete-covariate month before the methane record begins. Months after the
    methane record starts but lacking methane are held separately, since they are
    interpolation rather than reconstruction.

    `fit` is the adopted window and `fit_nominal` is the same window before the
    exclusion, so a caller can report both configurations without rebuilding.
    Passing `exclude=()` recovers the nominal window as the primary one.
    """
    complete = complete_covariate_months(covariates, columns)
    observed = pd.PeriodIndex(methane_months, freq="M")
    first_methane = observed.min()

    removed = pd.PeriodIndex(exclude, freq="M")
    fit_nominal = complete.intersection(observed).sort_values()
    fit = fit_nominal.difference(removed).sort_values()
    without_methane = complete.difference(observed)
    reconstruction = without_methane[without_methane < first_methane].sort_values()
    interior = without_methane[without_methane >= first_methane].sort_values()

    return {
        "fit": fit,
        "fit_nominal": fit_nominal,
        "excluded": fit_nominal.intersection(removed).sort_values(),
        "reconstruction": reconstruction,
        "interior_gaps": interior,
        "methane_excluded": observed.difference(complete).sort_values(),
    }


#: Windows that occupy a contiguous span, for which absent months are meaningful.
_CONTIGUOUS = ("fit", "fit_nominal", "reconstruction")


def window_accounting(windows: dict[str, pd.PeriodIndex]) -> pd.DataFrame:
    """Month counts for each window, against the span it occupies.

    Span and absent-month counts are reported only for the two windows meant to
    be contiguous. The others are sets of months scattered through the record,
    where the difference between a span and its contents carries no meaning.
    """
    records = []
    for name in ("fit", "fit_nominal", "excluded", "reconstruction",
                 "interior_gaps", "methane_excluded"):
        index = windows[name]
        record = {"window": name, "n_months": len(index)}
        if len(index) == 0:
            records.append({**record, "first": "", "last": "", "span_months": "", "n_absent": ""})
            continue
        record |= {"first": str(index.min()), "last": str(index.max())}
        if name in _CONTIGUOUS:
            span = pd.period_range(index.min(), index.max(), freq="M")
            record |= {"span_months": len(span), "n_absent": len(span.difference(index))}
        else:
            record |= {"span_months": "", "n_absent": ""}
        records.append(record)
    return pd.DataFrame.from_records(records)


def absent_months(windows: dict[str, pd.PeriodIndex], name: str) -> list[str]:
    """Months inside a window's span that the window does not contain."""
    index = windows[name]
    if len(index) == 0:
        return []
    span = pd.period_range(index.min(), index.max(), freq="M")
    return [str(m) for m in span.difference(index)]


def binding_constraint(coverage: pd.DataFrame) -> pd.DataFrame:
    """Which reconstruction-capable covariate ends earliest, and which starts latest.

    These two bound the fit and reconstruction windows respectively.
    """
    capable = coverage[coverage["reconstruction_capable"]].copy()
    return pd.DataFrame(
        [
            {
                "bound": "fit window ends at",
                "covariate": capable.loc[capable["last"].idxmin(), "covariate"],
                "month": capable["last"].min(),
            },
            {
                "bound": "reconstruction window starts at",
                "covariate": capable.loc[capable["first"].idxmax(), "covariate"],
                "month": capable["first"].max(),
            },
        ]
    )
