"""Diagnostics for negative methane fluxes. These functions report and never filter.

Deventer et al. (2019) give a flux detection limit of about 3 +/- 2 nmol m-2
s-1 and treat measured negative net fluxes as questionable: most exceeded the
detection limit, yet very few appeared in both analysers at the same timestamp,
which points to measurement error rather than genuine uptake.
"""

from __future__ import annotations

import pandas as pd

from . import site


def negative_summary(merged: pd.DataFrame, limit: float = site.DETECTION_LIMIT) -> dict[str, object]:
    """Counts of negative fluxes split by the detection limit."""
    values = merged["fch4"].dropna()
    negative = values[values < 0]
    below = negative[negative > -limit]
    exceeds = negative[negative <= -limit]
    return {
        "detection_limit": limit,
        "n_values": int(len(values)),
        "n_negative": int(len(negative)),
        "pct_negative": round(100 * len(negative) / len(values), 2),
        "n_negative_within_detection_limit": int(len(below)),
        "pct_of_negatives_within_limit": round(100 * len(below) / max(len(negative), 1), 1),
        "n_negative_exceeding_detection_limit": int(len(exceeds)),
        "pct_of_negatives_exceeding_limit": round(100 * len(exceeds) / max(len(negative), 1), 1),
        "most_negative": float(negative.min()) if len(negative) else float("nan"),
    }


def detection_limit_sensitivity(merged: pd.DataFrame) -> pd.DataFrame:
    """Repeat the negative-flux split across the published detection-limit range."""
    low = site.DETECTION_LIMIT - site.DETECTION_LIMIT_UNCERTAINTY
    high = site.DETECTION_LIMIT + site.DETECTION_LIMIT_UNCERTAINTY
    return pd.DataFrame.from_records(
        [negative_summary(merged, limit) for limit in (low, site.DETECTION_LIMIT, high)]
    )


def concurrent_negatives(frame: pd.DataFrame, limit: float = site.DETECTION_LIMIT) -> dict[str, object]:
    """Count timestamps where both analysers report a negative flux.

    Genuine uptake should register in both systems at once, whereas independent
    measurement error should rarely coincide, so concurrence discriminates
    between the two explanations.
    """
    both = frame[site.TGA_COLUMN].notna() & frame[site.LI7700_COLUMN].notna()
    pairs = frame.loc[both]
    tga_negative = pairs[site.TGA_COLUMN] < 0
    li_negative = pairs[site.LI7700_COLUMN] < 0
    either = tga_negative | li_negative
    concurrent = tga_negative & li_negative
    concurrent_beyond = (pairs[site.TGA_COLUMN] <= -limit) & (pairs[site.LI7700_COLUMN] <= -limit)
    return {
        "n_paired_timestamps": int(len(pairs)),
        "n_negative_tga": int(tga_negative.sum()),
        "n_negative_li7700": int(li_negative.sum()),
        "n_negative_in_either": int(either.sum()),
        "n_negative_in_both": int(concurrent.sum()),
        "pct_of_either_that_are_concurrent": round(
            100 * concurrent.sum() / max(either.sum(), 1), 1
        ),
        "n_beyond_limit_in_both": int(concurrent_beyond.sum()),
        "pct_of_either_beyond_limit_concurrent": round(
            100 * concurrent_beyond.sum() / max(either.sum(), 1), 2
        ),
    }


def negative_share_by_year(merged: pd.DataFrame) -> pd.DataFrame:
    """Negative-flux share per year, alongside the analysers active in that year."""
    reported = merged[merged["fch4"].notna()].copy()
    reported["year"] = reported["timestamp_start"].dt.year
    grouped = reported.groupby("year")
    out = pd.DataFrame(
        {
            "n": grouped.size(),
            "n_negative": grouped["fch4"].apply(lambda s: int((s < 0).sum())),
            "analyzer": grouped["analyzer"].agg(lambda s: "/".join(sorted(set(s)))),
        }
    )
    out["pct_negative"] = (100 * out["n_negative"] / out["n"]).round(1)
    return out.reset_index()
