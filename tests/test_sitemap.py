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


def test_the_tower_polygon_is_distinguished_by_weight_not_by_a_study_hue():
    """The boundary is cartography, so it must not borrow the support encoding.

    It took the support orange once, beside a wind rose where orange meant
    discarded, which is the collision the palette convention exists to prevent.
    Emphasis now comes from line weight against the other mapped polygons.
    """
    from matplotlib.colors import to_rgba

    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    ax = fig.axes[0]
    polygons = [p for p in ax.patches if type(p).__name__ == "Polygon"]
    widths = sorted(p.get_linewidth() for p in polygons)
    assert widths[-1] >= 2 * widths[0], "the mapped wetland is not heavier than its neighbors"
    for polygon in polygons:
        assert polygon.get_edgecolor() != to_rgba(ps.OUTSIDE)
        assert polygon.get_edgecolor() != to_rgba(ps.INSIDE)
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
    # A polar plot has no y axis, so the bar unit is stated as a line beneath it.
    assert not rose.get_ylabel()
    said = " ".join(a.get_text() for a in rose.texts)
    assert "%" in said and "sector" in said
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


def test_the_substantive_layers_are_credited_inside_the_figure():
    """Imagery and the wetland mapping carry their sources on the panel.

    The state outlines do not: they are a generic base map rather than a layer
    the figure makes a claim from, and their provenance is in notes/study.md.
    """
    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    said = " ".join(t.get_text() for ax in fig.axes[:3] for t in ax.texts)
    assert "NAIP" in said and "National Wetlands Inventory" in said
    assert "Census" not in said
    ps.plt.close(fig)


def test_the_stated_shares_match_the_stored_wind_record():
    """The figure's percentages must agree with the file panel c plots.

    This is the one test here that reads a stored layer rather than a synthetic
    one, because that is the thing being checked: the shares are written into
    the title and description as text, so regenerating the file over a different
    period would otherwise leave the words behind without any failure.
    """
    shares = sitemap.wind_shares()
    counts = shares.attrs
    column = "pct_of_half_hours_with_wind_direction"
    assert shares[column].sum() == pytest.approx(100.0, abs=0.01)

    of_directions = shares.loc[shares.excluded, column].sum()
    of_record = of_directions * counts["with_wind_direction"] / counts["half_hours"]

    said = sitemap.SITEMAP_TEXT.subtitle + " " + sitemap.SITEMAP_TEXT.description
    assert f"{round(of_directions)}%" in said
    assert f"{round(of_record)}%" in said


def test_the_wind_record_is_restricted_to_the_study_window():
    """Panel c covers the fitted years, not the full product.

    Every other quantity in the study is computed on the fit window, and the
    shares quoted in the figure are computed on the same months the rose plots.
    """
    counts = sitemap.wind_shares().attrs
    assert counts["half_hours"] == 192816       # 2009-01 to 2019-12
    assert counts["with_wind_direction"] == 172639


def test_the_site_is_yellow_in_both_panels_so_the_star_means_one_thing():
    """A reader meeting a star in both panels assumes it means the same thing."""
    from matplotlib.colors import to_rgba

    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    site_panel, network = fig.axes[0], fig.axes[1]
    stars = [l for ax in (site_panel, network) for l in ax.lines if l.get_marker() == "*"]
    assert len(stars) >= 2
    for star in stars:
        assert to_rgba(star.get_markerfacecolor()) == to_rgba(ps.SITE)
        assert to_rgba(star.get_markeredgecolor()) == to_rgba(ps.INK), "needs a dark casing"
    ps.plt.close(fig)


def test_orange_now_means_only_discarded_on_this_figure():
    """It marked the wetland boundary and the site star as well, which it no longer does."""
    from matplotlib.colors import to_rgba

    fig = sitemap.site_overview(image(), wetlands(), states(), sites(), shares())
    orange = to_rgba(ps.OUTSIDE)
    for ax in (fig.axes[0], fig.axes[1]):
        for line in ax.lines:
            assert to_rgba(line.get_markerfacecolor()) != orange
            assert to_rgba(line.get_markeredgecolor()) != orange
        for patch in ax.patches:
            assert to_rgba(patch.get_facecolor()) != orange
            assert to_rgba(patch.get_edgecolor()) != orange
    # The wind rose is the one place it survives, where it does mean discarded.
    rose = fig.axes[2]
    assert any(to_rgba(p.get_facecolor()) == orange for p in rose.patches)
    ps.plt.close(fig)


def test_a_white_casing_would_vanish_on_the_network_panel():
    """Why the star is cased dark: the states behind it are near-white."""
    def luminance(value: str) -> float:
        rgb = np.array([int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)])
        linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
        return float(np.dot(linear, [0.2126, 0.7152, 0.0722]))

    # A white casing is a tenth of the scale from the ground it would sit on; the
    # dark one is nine tenths of it away.
    assert abs(luminance("#FFFFFF") - luminance("#F4F4F4")) < 0.10
    assert abs(luminance(ps.INK) - luminance("#F4F4F4")) > 0.85
