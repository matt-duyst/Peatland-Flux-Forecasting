"""Carbon dioxide aggregation: the same rule as methane, on synthetic half-hours."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ingest import daily, site


def halfhourly(days: int = 3, per_day: int = 48, start: str = "2015-06-01"):
    stamps = pd.date_range(start, periods=days * per_day, freq="30min")
    rng = np.random.default_rng(0)
    return pd.DataFrame({"timestamp_start": stamps,
                         "FC": rng.normal(-2.0, 0.5, len(stamps)),
                         "fch4": rng.normal(40.0, 5.0, len(stamps))})


def test_the_column_generic_path_reproduces_the_methane_path_exactly():
    """One coverage rule for both gases, pinned by equivalence rather than by hope."""
    frame = halfhourly()
    frame["analyzer"] = "site_aggregated"
    reference = daily.daily_stats(frame)
    generic = daily.daily_stats_column(frame, "fch4")

    assert len(reference) == len(generic)
    for stat in ("mean", "n", "sd", "se"):
        np.testing.assert_allclose(reference[f"fch4_{stat}"].to_numpy(),
                                   generic[f"fch4_{stat}"].to_numpy())


def test_days_below_the_coverage_threshold_are_dropped():
    frame = halfhourly(days=2)
    keep = frame["timestamp_start"].dt.day == frame["timestamp_start"].dt.day.min()
    thin = frame[keep].head(site.MIN_HALFHOURS_PER_DAY - 1)
    out = daily.daily_stats_column(pd.concat([thin, frame[~keep]]), "FC")
    assert len(out) == 1, "a day under the threshold must not produce a daily mean"


def test_monthly_means_average_days_not_half_hours():
    """A month with one heavily sampled day must not be dominated by it."""
    dense = halfhourly(days=1, start="2015-06-01")
    dense["FC"] = -10.0
    sparse = halfhourly(days=1, start="2015-06-02").head(8)
    sparse["FC"] = 0.0
    monthly = daily.daily_to_monthly_column(
        daily.daily_stats_column(pd.concat([dense, sparse]), "FC"), "FC")
    assert monthly["FC_mean"].iloc[0] == pytest.approx(-5.0)
    assert monthly["FC_days"].iloc[0] == 2
    assert monthly["FC_halfhours"].iloc[0] == 56


def test_diurnal_balancing_removes_a_daylight_skew():
    """Daylight-heavy sampling must not tilt the balanced mean."""
    stamps = pd.date_range("2015-06-01", periods=48 * 10, freq="30min")
    day = (stamps.hour >= 6) & (stamps.hour < 18)
    value = np.where(day, -6.0, 2.0)
    frame = pd.DataFrame({"timestamp_start": stamps, "FC": value})
    # Thin the night by dropping whole days, not whole slots: balancing can only
    # correct a skew where every half-hour of the day is represented somewhere.
    keep = day | (stamps.dayofyear % 4 == 0)
    skewed = frame[keep]

    plain = skewed["FC"].mean()
    balanced = daily.monthly_diurnally_balanced(skewed, "FC")["FC_mean"].iloc[0]
    assert plain < -3.0, "the skewed sample should read too negative"
    assert balanced == pytest.approx(-2.0), "balancing should recover the true daily mean"


def test_balanced_output_carries_its_cell_count():
    frame = halfhourly(days=5)
    out = daily.monthly_diurnally_balanced(frame, "FC")
    assert out["FC_cells"].iloc[0] == 48
    assert out["FC_halfhours"].iloc[0] == 5 * 48
