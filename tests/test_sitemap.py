"""The site figure, on synthetic layers rather than the stored geospatial inputs."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study import plotstyle as ps, sitemap


def wetlands():
    """One polygon holding the tower and one that does not."""
    return {
        "features": [
            {"properties": {"code": "PSS3Dg", "acres": 88.22, "contains_tower": True},
             "geometry": {"coordinates": [[[-93.495, 47.500], [-93.483, 47.500],
                                           [-93.483, 47.510], [-93.495, 47.510],
                                           [-93.495, 47.500]]]}},
            {"properties": {"code": "PUBH", "acres": 3.0},
             "geometry": {"coordinates": [[[-93.499, 47.498], [-93.497, 47.498],
                                           [-93.497, 47.499], [-93.499, 47.498]]]}},
        ]
    }


def states():
    return {"features": [{"properties": {"state": "MN"},
                          "geometry": {"coordinates": [[[-97.0, 43.5], [-89.5, 43.5],
                                                        [-89.5, 49.4], [-97.0, 49.4],
                                                        [-97.0, 43.5]]]}}]}


def sites():
    return pd.DataFrame({"SITE_ID": ["US-Los", "SE-Deg"], "LAT": [46.08, 64.18],
                         "LON": [-89.98, 19.55]})


def shares():
    start = np.arange(0, 360, 10)
    return pd.DataFrame({"sector_start": start,
                         "pct_of_half_hours_with_wind_direction": np.full(36, 100 / 36),
                         "excluded": (start >= 30) & (start < 200)})


def image():
    return np.full((40, 33, 3), 128, dtype=np.uint8)


def test_meters_are_zero_at_the_origin_and_grow_the_right_way():
    origin = (-93.489, 47.505)
    e, n = sitemap.to_meters([-93.489], [47.505], origin)
    assert abs(float(e[0])) < 1e-6 and abs(float(n[0])) < 1e-6
    e, n = sitemap.to_meters([-93.479], [47.515], origin)
    assert float(e[0]) > 0 and float(n[0]) > 0
    # One degree of latitude is longer than one of longitude at this latitude.
    assert float(n[0]) > float(e[0])


def test_a_two_hundred_meter_radius_is_a_circle_on_the_metric_grid():
    """The panel is drawn in meters so the reported fetch is a true circle."""
    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    ax = fig.axes[0]
    circles = [p for p in ax.patches if type(p).__name__ == "Circle"]
    assert len(circles) == 1
    assert circles[0].get_radius() == pytest.approx(sitemap.SURFACE_HOMOGENEITY_M)
    assert ax.get_aspect() == 1.0
    ps.plt.close(fig)


def test_the_tower_polygon_is_distinguished_from_its_neighbors():
    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    ax = fig.axes[0]
    edges = [p.get_edgecolor() for p in ax.patches if type(p).__name__ == "Polygon"]
    from matplotlib.colors import to_rgba
    assert to_rgba(ps.OUTSIDE) in edges
    ps.plt.close(fig)


def test_only_sites_in_the_mapped_states_are_plotted():
    """A site in Sweden must not be drawn on a map of the lower states."""
    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    network = fig.axes[1]
    drawn = [len(l.get_xdata()) for l in network.lines]
    assert 1 in drawn                       # this site, marked alone
    assert all(n <= 1 for n in drawn)       # US-Los only; SE-Deg dropped


def test_the_excluded_sector_is_marked_and_keyed():
    """The panels carry no titles, so the sector needs a key of its own."""
    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    rose = fig.axes[2]
    hatched = [b for b in rose.patches if b.get_hatch()]
    assert len(hatched) == 17               # 30 to 200 degrees in ten-degree steps
    keyed = " ".join(t.get_text() for t in rose.get_legend().get_texts())
    assert "Discarded" in keyed and "retained" in keyed
    assert "%" in rose.get_ylabel()
    ps.plt.close(fig)


def test_no_panel_carries_a_title():
    """Titles on one panel and not the others read as unbalanced."""
    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    assert not any(ax.get_title() for ax in fig.axes[:3])
    ps.plt.close(fig)


def test_every_panel_carries_its_letter():
    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    letters = {t.get_text() for ax in fig.axes[:3] for t in ax.texts}
    assert {"(a)", "(b)", "(c)"} <= letters
    ps.plt.close(fig)


def test_imagery_and_layers_are_credited_inside_the_figure():
    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    said = " ".join(t.get_text() for ax in fig.axes[:3] for t in ax.texts)
    assert "NAIP" in said and "National Wetlands Inventory" in said
    assert "Census" in said
    ps.plt.close(fig)
