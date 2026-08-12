"""PDF 3: Seminars taught per year, rendered as a polished 3D bar chart.

A department-specific page that mirrors the rank aggregation used by PDF 4
(Seminars Taught per Year by Rank) but presents it as a 3D graph. The chart is
rendered to a PNG with Matplotlib and embedded full-page into a landscape PDF so
it drops into the combined packet between PDF 2 and PDF 4.

Ported from the FYS Packet Creator Colab notebook (GRAPH3). Rank aggregation is
reused from pdf4_rank_aggregator so both pages always agree.

Dependencies: matplotlib, numpy (in addition to reportlab).
"""

import os
import math
import tempfile

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch, Rectangle, Polygon
from mpl_toolkits.mplot3d import proj3d
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage, SimpleDocTemplate

from .shared import ACRONYM_TO_FULL, sanitize_department_name
from .pdf4_rank_aggregator import aggregate_by_rank


GRAPH3_RANK_ORDER = [
    'Visiting (all levels)',
    'SL/SP/PoP/PiR',
    'Emeritus & Emerita',
    'Assistant Professor',
    'Associate Professor',
    'Lecturer',
    'Professor & University Professor',
]

# Legend order is reversed so it matches the visible graph rows from top to
# bottom in the rendered 3D view.
GRAPH3_LEGEND_ORDER = list(reversed(GRAPH3_RANK_ORDER))

GRAPH3_LABELS = {
    'Visiting (all levels)': 'Visiting',
    'SL/SP/PoP/PiR': 'SrLec/SrPrec/ProfPract',
    'Emeritus & Emerita': 'Emeritus',
    'Assistant Professor': 'Assistant Professor',
    'Associate Professor': 'Associate Professor',
    'Lecturer': 'Lecturer/Instructor',
    'Professor & University Professor': 'Prof/Univ Prof',
}

GRAPH3_COLORS = {
    'Visiting (all levels)': '#8064A2',
    'SL/SP/PoP/PiR': '#92D050',
    'Emeritus & Emerita': '#7F7F7F',
    'Assistant Professor': '#FFC000',
    'Associate Professor': '#2F5597',
    'Lecturer': '#00B0F0',
    'Professor & University Professor': '#C00000',
}

GRAPH3_SETTINGS = {
    # 4:3 landscape canvas, matching the attached sample PDF proportions.
    'figsize': (10.24, 7.68),
    'dpi': 240,

    # Orientation rotated so the perspective draws the eye toward 25-26
    # instead of emphasizing the 13-14 side of the year axis.
    'view_elev': 18,
    'view_azim': -65,
    'box_aspect': (17.2, 11.8, 7.2),

    # Extra spacing between years and rank rows so shorter bars remain visible.
    # These values intentionally use a larger gap, closer to the prior-year
    # 3D chart spacing, so foreground bars do not fully cover bars behind them.
    'year_step': 1.55,
    'rank_step': 2.25,

    # Smaller footprints plus larger spacing create visible padding.
    # dx and dy are kept close so the bars still read as square-ish columns.
    'bar_dx': 0.56,
    'bar_dy': 0.60,
    'tile_dx': 0.62,
    'tile_dy': 0.68,

    'chart_facecolor': 'white',
    'page_border_color': '#9E9E9E',

    # Enlarged plotting area, still leaving room for the legend on the right.
    'axes_rect': [-0.085, 0.040, 0.940, 0.825],
}


def _graph3_blend_with_white(hex_color, amount=0.66):
    """Lighten category colors for floor tiles."""
    r, g, b = to_rgb(hex_color)
    return (r + (1 - r) * amount,
            g + (1 - g) * amount,
            b + (1 - b) * amount)



def _graph3_blend_with_black(hex_color, amount=0.35):
    """Darken category colors for side faces of the 3D bars."""
    r, g, b = to_rgb(hex_color)
    return (r * (1 - amount),
            g * (1 - amount),
            b * (1 - amount))


def _graph3_bar_facecolors(hex_color):
    """
    Return per-face colors for Matplotlib bar3d.

    Matplotlib uses this face order for each cuboid:
    -Z bottom, +Z top, -Y front-facing face, +Y back face, -X side, +X side.
    The chart view exposes the -Y face as the broad/front face, so make that
    face lighter and keep the side faces darker, per the requested look.
    """
    front_light = _graph3_blend_with_white(hex_color, amount=0.16)
    top_light = _graph3_blend_with_white(hex_color, amount=0.28)
    side_dark = _graph3_blend_with_black(hex_color, amount=0.32)
    side_darker = _graph3_blend_with_black(hex_color, amount=0.42)
    bottom_dark = _graph3_blend_with_black(hex_color, amount=0.50)
    return [
        bottom_dark,   # -Z bottom
        top_light,     # +Z top
        front_light,   # -Y broad/front face visible to the viewer
        side_darker,   # +Y back face
        side_dark,     # -X side face
        side_darker,   # +X side face
    ]

def _display_year_label(year):
    """Make year labels look like the reference PDF: '13-14, '14-15, etc."""
    year = str(year).strip()
    return year if year.startswith("'") else f"'{year}"


def _nice_z_ticks(zmax):
    """Use a 0-8 scale by default; expand only if a department would clip."""
    if zmax <= 8:
        return np.arange(0, 9, 1)
    step = 2 if zmax <= 20 else 5
    top = int(math.ceil(zmax / step) * step)
    return np.arange(0, top + step, step)


def _project_graph3_point_to_figure(fig, ax, x, y, z):
    """Project a 3D data coordinate into figure coordinates for clean custom labels."""
    x2, y2, _ = proj3d.proj_transform(x, y, z, ax.get_proj())
    display_xy = ax.transData.transform((x2, y2))
    return fig.transFigure.inverted().transform(display_xy)


def prepare_graph3_data(saved_data):
    """Use the notebook's existing aggregation logic and reorder rows for Graph 3."""
    rank_data, years = aggregate_by_rank(saved_data)
    matrix = np.array([
        [rank_data.get(rank, {}).get(year, 0) for year in years]
        for rank in GRAPH3_RANK_ORDER
    ], dtype=float)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    return years, matrix


def _add_graph3_projected_floor_tiles(fig, ax, matrix, x_positions, y_positions, dx, dy, tile_dx, tile_dy):
    """
    Add the colored floor grid as 2D projected polygons behind the 3D axes.

    This avoids the Matplotlib 3D painter-order problem where a floor tile from
    one row can appear on top of a neighboring raised bar. Because these tiles
    sit behind the transparent axes pane, bars always render above them.
    """
    for yi, rank in enumerate(GRAPH3_RANK_ORDER):
        y_base = y_positions[yi]
        for xi, x_base in enumerate(x_positions):
            x0 = x_base + (dx - tile_dx) / 2
            y0 = y_base + (dy - tile_dy) / 2
            x1 = x0 + tile_dx
            y1 = y0 + tile_dy
            projected_points = [
                _project_graph3_point_to_figure(fig, ax, x0, y0, 0),
                _project_graph3_point_to_figure(fig, ax, x1, y0, 0),
                _project_graph3_point_to_figure(fig, ax, x1, y1, 0),
                _project_graph3_point_to_figure(fig, ax, x0, y1, 0),
            ]
            fig.patches.append(Polygon(
                projected_points,
                closed=True,
                transform=fig.transFigure,
                facecolor=_graph3_blend_with_white(GRAPH3_COLORS[rank]),
                edgecolor='#D4D4D4',
                linewidth=0.22,
                zorder=0.60,
            ))


def render_graph3_png(dept, saved_data, output_png):
    """Render the 3D chart as a PNG that can be embedded into the PDF packet."""
    # Close prior figures so repeated packet generation cannot stack charts.
    plt.close('all')

    years, matrix = prepare_graph3_data(saved_data)
    department_full_name = ACRONYM_TO_FULL.get(dept, dept)

    fig = plt.figure(figsize=GRAPH3_SETTINGS['figsize'], dpi=GRAPH3_SETTINGS['dpi'])
    fig.patch.set_facecolor(GRAPH3_SETTINGS['chart_facecolor'])

    # Outer chart box to mimic the reference PDF.
    fig.add_artist(Rectangle(
        (0.018, 0.075), 0.965, 0.770,
        transform=fig.transFigure,
        fill=False,
        linewidth=0.8,
        edgecolor=GRAPH3_SETTINGS['page_border_color'],
        zorder=5,
    ))

    # Title stack: "FYSP's Evolution" kicker on top (black), then the department
    # (red, the primary title), then the report subtitle inside the framed chart.
    fig.text(0.5, 0.972, "FYSP's Evolution", ha='center', va='top',
             fontsize=15, fontfamily='serif', fontstyle='italic',
             fontweight='bold', color='black', zorder=6)
    fig.text(0.5, 0.912, department_full_name, ha='center', va='top',
             fontsize=22, fontfamily='sans-serif', fontweight='bold',
             color='#8B0000', zorder=6)
    fig.text(0.5, 0.833, 'Seminars taught per year', ha='center', va='top',
             fontsize=21, fontfamily='serif', fontstyle='italic', color='black', zorder=6)

    try:
        ax = fig.add_axes(GRAPH3_SETTINGS['axes_rect'], projection='3d', computed_zorder=False)
    except TypeError:
        # Older Matplotlib fallback.
        ax = fig.add_axes(GRAPH3_SETTINGS['axes_rect'], projection='3d')
        ax.computed_zorder = False

    ax.set_zorder(2)
    ax.patch.set_alpha(0)
    ax.set_facecolor((1, 1, 1, 0))

    n_years = len(years)
    n_ranks = len(GRAPH3_RANK_ORDER)
    year_step = GRAPH3_SETTINGS['year_step']
    rank_step = GRAPH3_SETTINGS['rank_step']
    dx = GRAPH3_SETTINGS['bar_dx']
    dy = GRAPH3_SETTINGS['bar_dy']
    tile_dx = GRAPH3_SETTINGS['tile_dx']
    tile_dy = GRAPH3_SETTINGS['tile_dy']
    x_positions = np.arange(n_years, dtype=float) * year_step
    y_positions = np.arange(n_ranks, dtype=float) * rank_step

    raw_max = int(np.ceil(matrix.max())) if matrix.size and matrix.max() > 0 else 8
    zmax = max(8, raw_max)
    zticks = _nice_z_ticks(zmax)
    ax.set_zlim(0, int(zticks[-1]))
    ax.set_zticks(zticks)
    ax.zaxis.set_tick_params(labelsize=9, pad=1)

    ax.set_xlim(-0.20 * year_step, x_positions[-1] + dx + 0.08 * year_step)
    ax.set_ylim(-0.30 * rank_step, y_positions[-1] + dy + 0.14 * rank_step)

    # Keep ticks for geometry but hide axis labels. Year labels are custom figure text.
    ax.set_xticks(x_positions + dx / 2)
    ax.set_xticklabels([''] * n_years)
    ax.set_yticks(y_positions + dy / 2)
    ax.set_yticklabels([''] * n_ranks)
    ax.xaxis.set_tick_params(length=0, pad=0)
    ax.yaxis.set_tick_params(length=0, pad=0)

    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_zlabel('')

    ax.view_init(elev=GRAPH3_SETTINGS['view_elev'], azim=GRAPH3_SETTINGS['view_azim'])
    ax.set_proj_type('persp')
    try:
        ax.set_box_aspect(GRAPH3_SETTINGS['box_aspect'])
    except Exception:
        pass

    # Stable grid styling: keep the horizontal z-grid, suppress clutter elsewhere.
    try:
        for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
            axis.pane.fill = False
            axis.pane.set_edgecolor((1, 1, 1, 0))
        ax.xaxis._axinfo['grid']['linewidth'] = 0
        ax.yaxis._axinfo['grid']['linewidth'] = 0
        ax.zaxis._axinfo['grid']['linewidth'] = 0.9
        ax.zaxis._axinfo['grid']['color'] = (0.62, 0.62, 0.62, 1)
        ax.zaxis._axinfo['grid']['linestyle'] = '-'
        ax.xaxis.line.set_color('#9A9A9A')
        ax.yaxis.line.set_color('#9A9A9A')
        ax.zaxis.line.set_color('#9A9A9A')
    except Exception:
        pass

    ax.tick_params(axis='z', colors='#202020')

    # Force projection to be computed before adding custom floor tiles/labels.
    fig.canvas.draw()

    # The colored floor grid is drawn behind the axes, not as 3D cuboids, so it
    # cannot appear on top of any bar.
    _add_graph3_projected_floor_tiles(fig, ax, matrix, x_positions, y_positions, dx, dy, tile_dx, tile_dy)

    # Raised bars are drawn after the floor and inside the transparent 3D axes.
    # Matplotlib 3D uses a painter-style renderer, so draw order matters. We
    # project each bar's base center to the page, draw the visually higher/back
    # bars first, and draw the visually lower/front bars last. This keeps front
    # bars on top when rows overlap in perspective. Bar face colors are set
    # manually instead of relying on Matplotlib's default light source so the
    # front face stays lighter while the side faces stay darker.
    bar_items = []
    for yi, rank in enumerate(GRAPH3_RANK_ORDER):
        y_base = y_positions[yi]
        for xi, value in enumerate(matrix[yi]):
            if value > 0:
                x_base = x_positions[xi]
                _, screen_y = _project_graph3_point_to_figure(
                    fig, ax, x_base + dx / 2, y_base + dy / 2, 0
                )
                bar_items.append((screen_y, y_base, x_base, yi, xi, float(value), rank))

    # Larger screen_y is visually higher/farther back on the page; smaller
    # screen_y is visually lower/closer to the viewer. Draw back-to-front.
    # y_base is included as a tie-breaker so farther rows draw before nearer rows.
    bar_items.sort(key=lambda item: (item[0], item[1]), reverse=True)

    for draw_order, (_, _, _, yi, xi, value, rank) in enumerate(bar_items):
        bars = ax.bar3d(
            x_positions[xi], y_positions[yi], 0,
            dx, dy, value,
            color=_graph3_bar_facecolors(GRAPH3_COLORS[rank]),
            shade=False,
            edgecolor='#4A4A4A',
            linewidth=0.18,
            zsort='average'
        )
        bars.set_zorder(50 + draw_order)

    # Recompute projection after bars are added, then add custom year labels.
    fig.canvas.draw()

    # Custom year labels: diagonal, non-overlapping, placed at the front edge.
    year_fontsize = max(6.7, min(8.5, 9.1 - max(0, n_years - 13) * 0.20))
    for xi, year in enumerate(years):
        x_fig, y_fig = _project_graph3_point_to_figure(
            fig, ax, x_positions[xi] + dx / 2, -0.50 * rank_step, 0
        )
        fig.text(
            x_fig,
            y_fig - 0.004,
            _display_year_label(year),
            ha='right',
            va='top',
            rotation=43,
            fontsize=year_fontsize,
            fontfamily='sans-serif',
            fontweight='bold',
            color='black',
            zorder=6,
        )

    # Rank/professor axis labels intentionally removed per request. The legend is
    # the only place where the full rank/title names appear.
    handles = [
        Patch(facecolor=GRAPH3_COLORS[r], edgecolor='none', label=GRAPH3_LABELS[r])
        for r in GRAPH3_LEGEND_ORDER
    ]
    fig.legend(
        handles=handles,
        loc='center left',
        bbox_to_anchor=(0.805, 0.455),
        frameon=False,
        fontsize=9.5,
        handlelength=0.62,
        handleheight=0.70,
        handletextpad=0.35,
        borderaxespad=0.0,
        labelspacing=0.78
    )

    # Do not use bbox_inches='tight': it changes geometry between departments and
    # can make the embedded PDF page appear shifted or scaled unpredictably.
    fig.savefig(output_png, dpi=GRAPH3_SETTINGS['dpi'], facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return output_png


def create_pdf3(dept, output_path, saved_data, headers=None):
    """Create PDF 3 as a full-page 3D graph image."""
    chart_dir = os.path.join(tempfile.gettempdir(), 'fys_graph3_cache')
    os.makedirs(chart_dir, exist_ok=True)

    png_name = f"{sanitize_department_name(dept)}_graph3.png"
    png_path = os.path.join(chart_dir, png_name)
    render_graph3_png(dept, saved_data, png_path)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        leftMargin=0,
        rightMargin=0,
        topMargin=0,
        bottomMargin=0,
    )
    # Match the landscape-letter page. The PNG already contains all titles/margins.
    story = [RLImage(png_path, width=11.0 * inch, height=8.25 * inch)]
    doc.build(story)
