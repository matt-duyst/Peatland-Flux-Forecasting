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
import matplotlib.patheffects as pe

from study import plotstyle as ps

#: Extent of the imagery crop, degrees, matching the file stored under geodata/.
IMAGE_BOUNDS = (-93.500, 47.497, -93.478, 47.515)

#: Imagery provenance. The scene identifier is not drawn, but it is what makes
#: the stored crop reproducible, so it is recorded beside the credit that is.
IMAGE_SCENE = "mn_m_4709329_sw_15_060_20210831"
IMAGE_DATE = "2021-08-31"
IMAGE_CREDIT = "Imagery USDA NAIP 2021-08-31, 0.6 m, via Microsoft Planetary Computer"
WETLAND_CREDIT = "Wetlands US Fish and Wildlife Service, National Wetlands Inventory"
BOUNDARY_CREDIT = "State outlines US Census Bureau, 2022"

#: Homogeneous fetch around the tower, meters, from the product's own metadata.
SURFACE_HOMOGENEITY_M = 200.0

#: Room taken off the top of the drawing area. Panel a holds an equal aspect
#: and so sits lower than the rectangle it is given, which left panel b as the
#: only thing meeting the subtitle, 29 px below it against panel a's 79.
SUBTITLE_CLEARANCE_PX = 36

#: Wind sectors the site discards, degrees clockwise from north.
EXCLUDED_SECTOR = (30.0, 200.0)

#: The tower, drawn the same way on the map and in the legend.
#: White fill with a dark edge, so the tower reads the same over dark forest,
#: over light peat, and on the legend's white ground.
#: The tower: the one point a reader needs to find first on this panel, so it
#: takes the emphasis the boundary used to. Cased dark, because the ground beside
#: it runs from luminance 0.04 under the forest to 0.54 on the bare peat.
TOWER_MARKER = dict(marker="*", markersize=15, markerfacecolor=ps.SITE,
                    markeredgecolor=ps.INK, markeredgewidth=1.3, linestyle="none")

#: The same site among the network, in the panel beside it. Same color, same
#: meaning; cased dark because the states behind it are pale.
SITE_MARKER = dict(marker="*", markersize=15, markerfacecolor=ps.SITE,
                   markeredgecolor=ps.INK, markeredgewidth=1.1, linestyle="none")


SITEMAP_TEXT = ps.FigureText(
    title="The flux tower and the wind directions it measures at Marcell Bog Lake Peatland",
    subtitle=(
        "The tower stands in a poor fen in north-central Minnesota (47.5051\u00b0 N, "
        "93.4893\u00b0 W), measuring carbon dioxide since 2007 and methane since 2009. "
        "Because upland forest lies to the east and southeast, flux arriving from "
        "30\u00b0 to 200\u00b0 is discarded before publication, which removes 40% of "
        "the record."
    ),
    description=(
        "Panel a is the peatland around the tower. The white outline is the wetland "
        "the National Wetlands Inventory maps there, and the circle marks the 200 m "
        "within which the site reports its surface uniform, the assumption eddy "
        "covariance rests on. Panel b places the site among the FLUXNET-CH4 network: "
        "it is not one of them, so no community gap-filled product exists for it. "
        "Panel c is how often the wind blew from each direction over 2009 to 2019, "
        "the years the model was fitted on. The published product holds no retained "
        "flux from 30\u00b0 to 200\u00b0 at all, where the tower and the upland "
        "forest lie: the exclusion was applied before publication, so this study "
        "inherits it. It is 45% of the half-hours carrying a wind direction, "
        "which the rose plots."
    ),
    emphasize=("Panel a", "Panel b", "Panel c"),
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


#: The mapped wetland's boundary: cartography on this panel, not a study
#: encoding. It took the support orange once, beside a wind rose where orange
#: meant discarded. Heavy white over a dark casing separates it from the 48 thin
#: white outlines by weight rather than by hue, and holds against a scene whose
#: brightest tone is luminance 0.31. Yellow was measured as a fallback at 68.8
#: from its nearest scene tone and was not needed.
BOUNDARY_STYLE = {"edgecolor": "white", "linewidth": 2.4,
                  "path_effects": [pe.Stroke(linewidth=4.2, foreground=ps.INK),
                                   pe.Normal()]}


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
                                     facecolor="none", zorder=3,
                                     **BOUNDARY_STYLE))
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

    ps.scale_bar(ax, 400, corner=(0.05, 0.108))
    ps.north_arrow(ax, at=(0.05, 0.205), size=0.052)
    ps.credit(ax, f"{IMAGE_CREDIT}\n{WETLAND_CREDIT}")

    acres = tower_ring["acres"] if tower_ring else 0.0
    handles = [
        Line2D([], [], label="Flux tower",
               **{**TOWER_MARKER, "markersize": 12}),
        Line2D([], [], color=ps.INSIDE, linestyle=(0, (6, 3)), linewidth=1.6,
               label=f"{SURFACE_HOMOGENEITY_M:.0f} m uniform surface"),
        Line2D([], [], linestyle="-", color=BOUNDARY_STYLE["edgecolor"],
               linewidth=BOUNDARY_STYLE["linewidth"],
               path_effects=BOUNDARY_STYLE["path_effects"],
               label=f"Mapped wetland, {acres * 0.4047:.0f} ha"),
    ]
    key = ps.legend(ax, handles=handles, labels=[h.get_label() for h in handles],
                    loc="upper left", fontsize=7.6, borderpad=0.4, labelspacing=0.3,
                    handlelength=1.5, handletextpad=0.5, title="What is marked",
                    bbox_to_anchor=(0.03, 0.945))
    key.get_title().set_fontsize(7.8)
    key.get_title().set_fontweight("bold")


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
    ax.plot(inside.LON, inside.LAT, linestyle="none", marker="o", markersize=4.0,
            color=ps.MUTED, markeredgecolor="white", markeredgewidth=0.4, zorder=3)
    ax.plot(here[0], here[1], **SITE_MARKER, zorder=5)

    ax.set_xlim(-127, -66); ax.set_ylim(23.5, 50.5)
    ax.set_aspect(1 / math.cos(math.radians(38)))
    ax.set_xticks([]); ax.set_yticks([])
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_edgecolor(ps.BOUNDARY)

    handles = [
        Line2D([], [], **{**SITE_MARKER, "markersize": 12},
               label=f"{site.SITE_NAME} (not in FLUXNET-CH4)"),
        Line2D([], [], marker="o", color=ps.MUTED, linestyle="none", markersize=4,
               label=f"FLUXNET-CH4 sites in the lower 48 states ({len(inside)})"),
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

    ax.bar(theta[~excluded], values[~excluded], width=width, color=ps.INSIDE,
           edgecolor="white", linewidth=0.4, zorder=3)
    ax.bar(theta[excluded], values[excluded], width=width, color=ps.OUTSIDE,
           edgecolor="white", linewidth=0.4, hatch=ps.OUTSIDE_HATCH, zorder=3)

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    labels = [f"{d}\u00b0 N" if d == 0 else f"{d}\u00b0" for d in range(0, 360, 30)]
    ax.set_thetagrids(range(0, 360, 30), labels, fontsize=8.0)

    # Rings stop short of the outer edge, so no radial label sits on the frame.
    top = float(values.max())
    step = 3.0 if top <= 13 else 5.0
    rings = [r for r in np.arange(step, top + step, step) if r < top]
    ax.set_ylim(0, top * 1.20)
    ax.set_yticks(rings)
    ax.set_rlabel_position(112)
    ax.tick_params(axis="y", labelsize=7.4, colors=ps.MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")
    ax.annotate("rings: % of half-hours per 10\u00b0 sector", xy=(0.5, -0.105),
                xycoords="axes fraction", ha="center", va="top", fontsize=7.6,
                color=ps.MUTED)
    ax.grid(color=ps.GRID, linewidth=0.6)

    # The bounds are drawn, because a reader told the sector runs 30 to 200
    # degrees cannot otherwise find either one on the circle. 30 sits on a
    # gridline and is labeled there; 200 does not, so it is named on its ray.
    top = float(values.max())
    for bound in EXCLUDED_SECTOR:
        ax.plot([math.radians(bound)] * 2, [0, top * 1.20], color=ps.BOUNDARY,
                linewidth=1.1, linestyle=(0, (5, 3)), zorder=4)
    ax.annotate(f"{EXCLUDED_SECTOR[1]:.0f}\u00b0",
                xy=(math.radians(EXCLUDED_SECTOR[1]), top * 0.72),
                ha="center", va="center", fontsize=7.8, color=ps.BOUNDARY,
                zorder=5, path_effects=[ps._outline()])

    handles = [
        Patch(facecolor=ps.INSIDE, edgecolor="white", label="Flux retained"),
        Patch(facecolor=ps.OUTSIDE, edgecolor="white", hatch=ps.OUTSIDE_HATCH,
              label="Discarded, 30\u00b0 to 200\u00b0"),
    ]
    ps.legend(ax, handles=handles, labels=[h.get_label() for h in handles],
              loc="lower center", fontsize=7.8, borderpad=0.38, labelspacing=0.3,
              handlelength=1.4, handletextpad=0.5, columnspacing=1.4, ncols=2,
              bbox_to_anchor=(0.5, 1.09))


def site_overview(image, wetlands: dict, states: dict, sites: pd.DataFrame,
                  shares: pd.DataFrame) -> Figure:
    """The three panels together, sharing the set's title and description blocks."""
    fig, (left, bottom, width, height) = ps.canvas_area(SITEMAP_TEXT, size="tall")
    origin = (site.LONGITUDE, site.LATITUDE)
    # Panel a is aspect-constrained, so it sits lower than its allocation and
    # panel b meets the subtitle alone. Insetting the block clears it.
    height -= SUBTITLE_CLEARANCE_PX / ps.SIZES["tall"][1]

    gap = 0.035 * width
    left_w = 0.46 * width
    right_w = width - left_w - gap
    right_x = left + left_w + gap
    row_gap = 0.11 * height
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
