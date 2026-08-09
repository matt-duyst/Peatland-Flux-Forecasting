"""The site figure: where US-MBP is, what surrounds the tower, and what the
site's own protocol discards.

Kept apart from `figures` because its inputs are unlike everything else in the
set. Three come from outside this project and are stored under `geodata/`:
aerial imagery, wetland polygons and state outlines. The fourth, wind direction,
comes from the 2025 AmeriFlux product held under `CSVs/`.

The site panel is drawn on a local metric grid centered on the tower, so a
radius is a true circle and a scale bar needs no projection assumption. Over the
two kilometers shown, treating degrees as locally flat is accurate to well under
a meter.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Polygon

from ingest import paths, site
from study import plotstyle as ps

#: Extent of the imagery crop, degrees, matching the file stored under geodata/.
IMAGE_BOUNDS = (-93.500, 47.497, -93.478, 47.515)

#: Imagery provenance, stated inside the panel that uses it.
IMAGE_SCENE = "mn_m_4709329_sw_15_060_20210831"
IMAGE_DATE = "2021-08-31"
IMAGE_CREDIT = "Imagery USDA NAIP 2021-08-31, 0.6 m, via Microsoft Planetary Computer"
WETLAND_CREDIT = "Wetlands US Fish and Wildlife Service, National Wetlands Inventory"
BOUNDARY_CREDIT = "State outlines US Census Bureau, 2022"

#: Homogeneous fetch around the tower, meters, from the product's own metadata.
SURFACE_HOMOGENEITY_M = 200.0

#: Wind sectors the site discards, degrees clockwise from north.
EXCLUDED_SECTOR = (30.0, 200.0)

#: The tower, drawn the same way on the map and in the legend.
TOWER_MARKER = dict(marker="*", markersize=16, markerfacecolor=ps.INK,
                    markeredgecolor="white", markeredgewidth=0.9, linestyle="none")

#: The nearest network site of the same wetland class, named in the notes.
NEAREST_FEN = "US-Los"

SITEMAP_TEXT = ps.FigureText(
    title="Marcell Bog Lake Peatland: the site, its network, and the sector it discards",
    subtitle=(
        "This site sits alone in its network, and keeps flux from only part of the "
        "compass because the rest brings upland forest into the measurement"
    ),
    description=(
        "Panel a is the peatland around the tower, with the wetland polygon the "
        "National Wetlands Inventory maps there and a circle at the 200 m over which "
        "the site reports its surface uniform. Panel b places the site among the "
        "FLUXNET-CH4 network: it is not one of them, so no community gap-filled "
        "product exists for it, and the nearest fen in the network is 308 km away. "
        "Panel c is how often the wind blew from each direction over 2009 to 2019, "
        "the years the model was fitted on. Flux is discarded from 30 to 200 "
        "degrees, where the tower and the upland forest lie, and the published "
        "product holds no retained flux from that sector at all."
    ),
)


def geodata_dir() -> Path:
    """Directory holding the geospatial inputs stored with the repository."""
    return paths.repo_root() / "geodata"


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


def load_geojson(name: str) -> dict:
    """One stored layer, with its provenance block intact."""
    return json.loads((geodata_dir() / name).read_text())


def load_network_sites(path: Path | None = None) -> pd.DataFrame:
    """FLUXNET-CH4 sites and their coordinates, from the published appendix.

    The appendix carries two banner rows above its header, and its coordinates
    are read as numbers so a stray label cannot enter as a position.
    """
    source = path or (paths.csv_dir() / "Delwiche_2020_ESSD_Appendix_B.xlsx")
    frame = pd.read_excel(source, sheet_name="B3 - Metadata and Data", header=2)
    frame = frame[frame["SITE_ID"].notna()].copy()
    for column in ("LAT", "LON"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["LAT", "LON"])


def wind_shares(path: Path | None = None) -> pd.DataFrame:
    """Share of half-hours by wind direction, one row per ten-degree sector.

    Shares are of half-hours carrying a wind direction, which is the population
    the sector rule acts on and the one whose shares sum to a hundred. The header
    lines record that population and the whole record it came from, and are read
    back into the frame's attributes so a panel can state its own denominator.
    """
    source = path or (geodata_dir() / "wind_direction_shares.csv")
    frame = pd.read_csv(source, comment="#")
    counts = {}
    for line in Path(source).read_text().splitlines():
        if not line.startswith("#"):
            break
        for part in line.lstrip("# ").split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                counts[key.strip()] = int(value) if value.strip().isdigit() else value.strip()
    frame.attrs.update(counts)
    return frame


# --------------------------------------------------------------------------
# Local metric grid
# --------------------------------------------------------------------------


def to_meters(lon, lat, origin: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    """Degrees to meters east and north of an origin, on a local flat earth."""
    lon0, lat0 = origin
    scale = math.cos(math.radians(lat0))
    east = (np.asarray(lon, dtype=float) - lon0) * 111_320.0 * scale
    north = (np.asarray(lat, dtype=float) - lat0) * 110_570.0
    return east, north


# --------------------------------------------------------------------------
# Panels
# --------------------------------------------------------------------------


def draw_site(ax, image, wetlands: dict, origin: tuple[float, float]) -> None:
    """Imagery, the mapped wetland, the tower, and the homogeneity radius."""
    west, south, east, north = IMAGE_BOUNDS
    x0, y0 = to_meters(west, south, origin)
    x1, y1 = to_meters(east, north, origin)
    ax.imshow(image, extent=(float(x0), float(x1), float(y0), float(y1)),
              origin="upper", interpolation="bilinear", zorder=0)

    tower_ring = None
    for feature in wetlands["features"]:
        rings = feature["geometry"]["coordinates"]
        holds_tower = feature["properties"].get("contains_tower", False)
        for ring in rings:
            lon = [p[0] for p in ring]
            lat = [p[1] for p in ring]
            ex, ny = to_meters(lon, lat, origin)
            if holds_tower:
                tower_ring = feature["properties"]
                ax.add_patch(Polygon(np.column_stack([ex, ny]), closed=True,
                                     facecolor="none", edgecolor=ps.OUTSIDE,
                                     linewidth=1.8, zorder=3))
            else:
                ax.add_patch(Polygon(np.column_stack([ex, ny]), closed=True,
                                     facecolor="none", edgecolor="white",
                                     linewidth=0.7, alpha=0.55, zorder=2))

    ax.add_patch(Circle((0, 0), SURFACE_HOMOGENEITY_M, facecolor="none",
                        edgecolor=ps.INSIDE, linewidth=1.6, linestyle=(0, (6, 3)),
                        zorder=4))
    ax.plot([0], [0], **TOWER_MARKER, zorder=5)

    ax.set_xlim(float(x0), float(x1))
    ax.set_ylim(float(y0), float(y1))
    ax.set_aspect("equal")
    _coordinate_ticks(ax, origin)
    for spine in ax.spines.values():
        spine.set_edgecolor(ps.BOUNDARY)

    ps.scale_bar(ax, 400)
    ps.north_arrow(ax)
    ps.credit(ax, f"{IMAGE_CREDIT}\n{WETLAND_CREDIT}")

    acres = tower_ring["acres"] if tower_ring else 0.0
    handles = [
        Line2D([], [], label="Flux tower",
               **{**TOWER_MARKER, "markersize": 12}),
        Line2D([], [], color=ps.INSIDE, linestyle=(0, (6, 3)), linewidth=1.6,
               label=f"{SURFACE_HOMOGENEITY_M:.0f} m, reported uniform surface"),
        Patch(facecolor="none", edgecolor=ps.OUTSIDE, linewidth=1.8,
              label=f"Mapped wetland, {acres * 0.4047:.0f} ha"),
    ]
    ps.legend(ax, handles=handles, labels=[h.get_label() for h in handles],
              loc="upper left", fontsize=8.4, borderpad=0.42, labelspacing=0.34,
              bbox_to_anchor=(0.045, 0.985))


def _coordinate_ticks(ax, origin: tuple[float, float]) -> None:
    """A light set of ticks in degrees on a panel drawn in meters.

    Enough to place the panel on the earth without the clutter of a graticule
    over two kilometers of imagery.
    """
    lons = [-93.496, -93.489, -93.482]
    lats = [47.500, 47.505, 47.510]
    xs, _ = to_meters(lons, [origin[1]] * len(lons), origin)
    _, ys = to_meters([origin[0]] * len(lats), lats, origin)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{abs(v):.3f}\u00b0W" for v in lons], fontsize=7.4)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{v:.3f}\u00b0N" for v in lats], fontsize=7.4)
    ax.tick_params(length=3, colors=ps.MUTED, top=False, right=False)
    ax.grid(False)


def draw_network(ax, states: dict, sites: pd.DataFrame,
                 here: tuple[float, float]) -> None:
    """The lower states, the network's sites, and this one among them."""
    for feature in states["features"]:
        for ring in feature["geometry"]["coordinates"]:
            ax.add_patch(Polygon(ring, closed=True, facecolor="#F4F4F4",
                                 edgecolor=ps.GRID, linewidth=0.5, zorder=0))

    inside = sites[sites.LON.between(-128, -65) & sites.LAT.between(24, 50)]
    nearest = inside[inside.SITE_ID == NEAREST_FEN]
    others = inside[inside.SITE_ID != NEAREST_FEN]
    ax.plot(others.LON, others.LAT, linestyle="none", marker="o", markersize=4.0,
            color=ps.MUTED, markeredgecolor="white", markeredgewidth=0.4, zorder=3)
    ax.plot(nearest.LON, nearest.LAT, linestyle="none", marker="s", markersize=5.6,
            color=ps.INSIDE, markeredgecolor="white", markeredgewidth=0.6, zorder=4)
    ax.plot(here[0], here[1], marker="*", markersize=15, color=ps.OUTSIDE,
            markeredgecolor="white", markeredgewidth=1.2, zorder=5)
    if len(nearest):
        ax.annotate(f"{NEAREST_FEN}, 308 km", xy=(float(nearest.LON.iloc[0]),
                                                  float(nearest.LAT.iloc[0])),
                    xytext=(7, -9), textcoords="offset points", ha="left",
                    fontsize=7.8, color=ps.INK, zorder=6)

    ax.set_xlim(-127, -66); ax.set_ylim(23.5, 50.5)
    ax.set_aspect(1 / math.cos(math.radians(38)))
    ax.set_xticks([]); ax.set_yticks([])
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_edgecolor(ps.BOUNDARY)

    ps.credit(ax, BOUNDARY_CREDIT, xy=(0.985, 0.02), va="bottom", ha="right")
    handles = [
        Line2D([], [], marker="*", color=ps.OUTSIDE, linestyle="none", markersize=12,
               label="This site, absent from the network"),
        Line2D([], [], marker="s", color=ps.INSIDE, linestyle="none", markersize=5.6,
               label="Nearest network fen"),
        Line2D([], [], marker="o", color=ps.MUTED, linestyle="none", markersize=4,
               label=f"Other FLUXNET-CH4 sites here ({len(others)})"),
    ]
    ps.legend(ax, handles=handles, labels=[h.get_label() for h in handles],
              loc="lower left", fontsize=8.4, borderpad=0.42, labelspacing=0.34)


def draw_sector(ax, shares: pd.DataFrame) -> None:
    """Wind direction, with the sector the site discards marked.

    Bars are the share of half-hours blowing from each direction. The excluded
    share is what the rule removes before any flux is kept, not a share of
    retained flux: the published product holds no retained flux from the sector
    at all, so that quantity is zero by construction and is not plotted.
    """
    width = math.radians(10)
    theta = np.radians(shares["sector_start"].to_numpy() + 5)
    values = shares["pct_of_half_hours_with_wind_direction"].to_numpy()
    excluded = shares["excluded"].to_numpy()

    lo, hi = (math.radians(a) for a in EXCLUDED_SECTOR)
    ax.bar(theta[~excluded], values[~excluded], width=width, color=ps.INSIDE,
           edgecolor="white", linewidth=0.4, zorder=3)
    ax.bar(theta[excluded], values[excluded], width=width, color=ps.OUTSIDE,
           edgecolor="white", linewidth=0.4, hatch=ps.OUTSIDE_HATCH, zorder=3)

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetagrids(range(0, 360, 45), ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
                      fontsize=8.4)
    ax.set_rlabel_position(112)
    ax.tick_params(axis="y", labelsize=7.6, colors=ps.MUTED)
    ax.grid(color=ps.GRID, linewidth=0.6)
    ax.set_rlabel_position(112)
    ax.tick_params(axis="y", labelsize=7.6, colors=ps.MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")
    removed = float(values[excluded].sum())
    recorded = shares.attrs.get("with_wind_direction")
    total = shares.attrs.get("half_hours")
    caption = f"{removed:.0f}% of half-hours with a wind direction, 30 to 200 degrees"
    if recorded and total:
        caption += f"\n{removed * recorded / total:.0f}% of the whole record"
    caption += "\nbars are % of half-hours per 10\u00b0 sector"
    ax.set_title(caption, fontsize=ps.LEGEND_SIZE, fontweight="bold",
                 color=ps.BOUNDARY, pad=16)


# --------------------------------------------------------------------------
# The figure
# --------------------------------------------------------------------------


def site_overview(image, wetlands: dict, states: dict, sites: pd.DataFrame,
                  shares: pd.DataFrame) -> Figure:
    """The three panels together, sharing the set's title and description blocks."""
    fig, (left, bottom, width, height) = ps.canvas_area(SITEMAP_TEXT, size="tall")
    origin = (site.LONGITUDE, site.LATITUDE)

    gap = 0.035 * width
    left_w = 0.46 * width
    right_w = width - left_w - gap
    right_x = left + left_w + gap
    row_gap = 0.17 * height
    row_h = (height - row_gap) / 2

    ax_site = fig.add_axes((left, bottom, left_w, height))
    ax_net = fig.add_axes((right_x, bottom + row_h + row_gap, right_w, row_h))
    ax_rose = fig.add_axes((right_x, bottom, right_w, row_h), projection="polar")

    draw_site(ax_site, image, wetlands, origin)
    draw_network(ax_net, states, sites, origin)
    draw_sector(ax_rose, shares)
    for ax, letter in ((ax_site, "a"), (ax_net, "b"), (ax_rose, "c")):
        ps.panel_letter(ax, letter)
    return fig
