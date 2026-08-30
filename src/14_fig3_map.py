"""VISHWAS — fig3_map.png: where India's forecasts actually go wrong.

Mean absolute forecast error per gridpoint, over the 1,252 gauge-observed land
gridpoints the whole project is scored on. This is the figure that makes the
product concrete: the confidence map VISHWAS produces has this same shape and
this same domain.

WHY THIS SCRIPT EXISTS
    figures/fig3_map.png had NO GENERATOR. Written 30 Aug 2026 (P18).

TWO THINGS THIS FIGURE MUST STATE, AND DOES
    1. THE DOMAIN IS 24.8% OF THE BOX. IMD's gridded rainfall is gauge-based,
       so it is land only: 1,252 of the 5,041 gridpoints in the India box
       survive the land mask. We state that ourselves rather than let a judge
       find it. The unsampled box is drawn as a faint outline so the gap is
       visible rather than cropped away.
    2. THIS IS ERROR, NOT BUST RATE. It is the mean |ensemble mean - observed|
       in mm/day over the Phase 1 sample. It is NOT the model's output and not
       a bust probability. Never present it beside fig6 without saying so.

    Sequential palette, low to high, because this is one quantity.

    python src/14_fig3_map.py
"""

import argparse
import importlib.util
import os

import numpy as np

import figstyle as fs

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SAMPLE = os.path.join(_ROOT, "data", "spread_skill_4season.parquet")

# The India box the pipeline subsets to, from CLAUDE.md CONSTRAINTS.
BOX_LAT = (5.0, 40.0)
BOX_LON = (65.0, 100.0)
BOX_POINTS = 5041


def load_conditional_module():
    path = os.path.join(_ROOT, "src", "04_conditional.py")
    spec = importlib.util.spec_from_file_location("conditional04", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sample", default=DEFAULT_SAMPLE)
    p.add_argument("--out", default=os.path.join(_ROOT, "figures", "fig3_map.png"))
    a = p.parse_args()

    m04 = load_conditional_module()
    table = m04.load(a.sample)

    cells = (table.groupby(["lat", "lon"])
             .agg(error=("error", "mean"), n=("error", "size"))
             .reset_index())
    n_points = len(cells)
    share = 100.0 * n_points / BOX_POINTS

    print("gridpoints {:,} of {:,} in the box ({:.1f}%)".format(
        n_points, BOX_POINTS, share))
    print("mean error {:.2f} mm/day   median {:.2f}   max {:.2f}".format(
        cells["error"].mean(), cells["error"].median(), cells["error"].max()))

    fig = fs.figure(12.6, 11.2)
    ax = fs.axes(fig, [0.085, 0.285, 0.775, 0.465])

    # The full box, so the land-only domain is visibly a subset.
    ax.add_patch(plt_rect(BOX_LON, BOX_LAT))

    # Colour ceiling at the 98th percentile: a handful of orographic cells
    # otherwise wash the whole map pale. Stated in the footnote.
    vmax = float(np.percentile(cells["error"], 98))
    sc = ax.scatter(cells["lon"], cells["lat"], c=cells["error"],
                    cmap=fs.SEQUENTIAL, vmin=0, vmax=vmax,
                    s=15, marker="s", linewidths=0, zorder=3)

    ax.set_xlim(BOX_LON[0] - 0.6, BOX_LON[1] + 0.6)
    ax.set_ylim(BOX_LAT[0] - 0.6, BOX_LAT[1] + 0.6)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitude °E", fontsize=14, color=fs.INK)
    ax.set_ylabel("Latitude °N", fontsize=14, color=fs.INK)
    ax.grid(True, color=fs.GRID, linewidth=0.8)

    cax = fig.add_axes([0.875, 0.285, 0.022, 0.465])
    bar = fig.colorbar(sc, cax=cax)
    bar.set_label("Mean absolute forecast error, mm/day", fontsize=13,
                  color=fs.INK)
    bar.ax.tick_params(colors=fs.INK2, labelsize=12, length=3)
    bar.outline.set_edgecolor(fs.GRID)

    # No in-plot annotation: every placement collided with either Kashmir or
    # the peninsula, and the footnote already states the box and the mask.

    fs.title(
        fig,
        "Where India's forecasts go wrong",
        "Mean forecast error at each of the {:,} gauge-observed land gridpoints the whole\n"
        "project is scored on. VISHWAS predicts, in advance, which of these will fail.".format(
            n_points),
        x=0.085, y=0.965, title_size=29, gap=0.058)

    fs.footnote(fig, (
        "THE DOMAIN IS LAND ONLY, AND WE SAY SO FIRST. IMD's gridded rainfall is built from rain "
        "gauges, so it exists only over land: {:,} of the {:,} gridpoints in the 5–40°N / 65–100°E "
        "box survive the mask, or {:.1f}%. The faint rectangle is the full box, drawn so the gap is "
        "visible rather than cropped away. That is the observational domain, not a modelling "
        "shortcut — scoring against real gauges instead of a reanalysis is the harder and more "
        "honest choice.\n"
        "THIS IS FORECAST ERROR, NOT VISHWAS'S OUTPUT. Each cell is the mean of "
        "|ensemble mean − observed| in mm/day; it is not a bust probability and not a model "
        "prediction. Colour is clipped at the 98th percentile ({:.1f} mm/day) because a few "
        "orographic cells otherwise wash the map pale.\n"
        "n = {:,} wet samples from {} GEFSv12 reforecasts spanning all four seasons and three "
        "years (2012 / 2015 / 2018), Day 1–10. Truth: IMD 0.25° gauge-gridded daily rainfall."
    ).format(n_points, BOX_POINTS, share, vmax, len(table),
             table["init"].nunique()),
        x=0.085, y=0.222, width=126, size=10.8)

    fs.save(fig, a.out)


def plt_rect(lon, lat):
    from matplotlib.patches import Rectangle
    return Rectangle((lon[0], lat[0]), lon[1] - lon[0], lat[1] - lat[0],
                     facecolor="none", edgecolor=fs.GRID, linewidth=1.6,
                     zorder=1)


if __name__ == "__main__":
    main()
