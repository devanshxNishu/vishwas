"""VISHWAS — the confidence map (demo asset).

Renders one forecast date as three side-by-side maps over the 1,252
gauge-observed land gridpoints:

    A  VISHWAS predicted bust probability
    B  what actually happened (IMD gauge rainfall)
    C  hits, false alarms and misses at the operating point

The date is chosen EMPIRICALLY by src/08_pick_date.py, not assumed. The
operating point is the GLOBAL top-decile threshold fitted once on the whole
test set, never re-fitted per date -- re-fitting per date would guarantee a
flattering picture.

Visual language matches figures/fig3_map.png so the deck reads as one system.

    python src/08_demo_map.py --init 20190731 --lead 5
"""

import argparse
import textwrap

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D

# --- visual language, shared with fig3_map.png -----------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
RAMP = LinearSegmentedColormap.from_list("vishwas_blue", ["#cde2fb", "#0d366b"])
ASPECT = 1.0 / np.cos(np.radians(22.0))

# categorical slots 1-3 of the validated palette. All-pairs CVD dE 9.2,
# normal-vision 24.0 -- checked with the palette validator, not eyeballed.
C_HIT = "#2a78d6"     # slot 1, blue
C_FALSE = "#eb6834"   # slot 2, orange
C_MISS = "#1baf7a"    # slot 3, aqua
C_QUIET = "#dcdbd6"   # non-event, deliberately recessive

TRUTH_NOTE = ("Truth: IMD 0.25 deg gauge-gridded daily rainfall, colocated by exact "
              "float match onto the 0.5 deg GEFS grid.")

# IMD's own daily rainfall classes. Rainfall is far too skewed for a linear
# ramp -- one 390 mm cell would wash the whole map pale -- and these are the
# bins an Indian forecaster already reads.
RAIN_BINS = [0.0, 0.1, 2.5, 15.6, 64.5, 115.6, 204.5, 1000.0]
RAIN_LABELS = ["0", "0.1–2.4", "2.5–15.5", "15.6–64.4", "64.5–115.5",
               "115.6–204.4", "204.5+"]
RAIN_CLASSES = ["no rain", "very light", "light", "moderate", "heavy",
                "very heavy", "extremely heavy"]


def load(path, init, lead):
    d = pd.read_parquet(path)
    g = d[(d["init"] == init) & (d["lead_day"] == lead)].copy()
    if g.empty:
        raise SystemExit("no rows for init={} lead={}".format(init, lead))
    return d, g


def operating_threshold(d, flag_rate):
    """One global threshold, fitted on the entire test set."""
    return float(d["model_score"].quantile(1.0 - flag_rate))


def square_size(ax, fig, lon_span, cell=0.5):
    """Marker area in pt^2 so that marker='s' draws one grid cell."""
    width_pt = ax.get_window_extent().width / fig.dpi * 72.0
    side = cell * width_pt / lon_span
    return max(side * side * 0.86, 1.0)   # 0.86 leaves a hairline gap


def frame(ax, lon_lim, lat_lim, xlabel):
    ax.set_aspect(ASPECT)
    ax.set_xlim(*lon_lim)
    ax.set_ylim(*lat_lim)
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=13, length=4)
    ax.set_xlabel(xlabel, color=INK2, fontsize=14)


def panel_title(ax, letter, title, sub):
    ax.text(0.0, 1.075, "{}  {}".format(letter, title), transform=ax.transAxes,
            fontsize=17, fontweight="bold", color=INK, ha="left", va="bottom")
    ax.text(0.0, 1.018, sub, transform=ax.transAxes,
            fontsize=13.5, color=INK2, ha="left", va="bottom")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pred", default="data/model_predictions.parquet")
    p.add_argument("--init", default="20190731")
    p.add_argument("--lead", type=int, default=5)
    p.add_argument("--flag-rate", type=float, default=0.10,
                   help="global alert budget; 0.10 matches the top-10% success criterion")
    p.add_argument("--out", default="figures/fig6_confidence_map.png")
    a = p.parse_args()

    d, g = load(a.pred, a.init, a.lead)
    thr = operating_threshold(d, a.flag_rate)

    init_dt = pd.to_datetime(a.init, format="%Y%m%d")
    valid_dt = init_dt + pd.Timedelta(days=a.lead)

    flagged = g["model_score"].to_numpy() >= thr
    bust = g["bust"].to_numpy()
    hit = flagged & bust
    false_alarm = flagged & ~bust
    miss = ~flagged & bust
    quiet = ~flagged & ~bust

    n_hit, n_false, n_miss = int(hit.sum()), int(false_alarm.sum()), int(miss.sum())
    precision = n_hit / max(n_hit + n_false, 1)
    recall = n_hit / max(n_hit + n_miss, 1)

    lon_lim = (g["lon"].min() - 0.9, g["lon"].max() + 0.9)
    lat_lim = (g["lat"].min() - 0.9, g["lat"].max() + 0.9)
    lon_span = lon_lim[1] - lon_lim[0]

    fig = plt.figure(figsize=(19.5, 10.1), dpi=200, facecolor=SURFACE)
    gs = fig.add_gridspec(1, 3, left=0.043, right=0.965, top=0.825, bottom=0.255,
                          wspace=0.44)
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]
    for i, ax in enumerate(axes):
        frame(ax, lon_lim, lat_lim, "longitude $\\degree$E")
    axes[0].set_ylabel("latitude $\\degree$N", color=INK2, fontsize=14)
    for ax in axes[1:]:
        ax.tick_params(labelleft=False)

    fig.canvas.draw()
    s = square_size(axes[0], fig, lon_span)

    lon, lat = g["lon"].to_numpy(), g["lat"].to_numpy()

    # --- A: predicted bust probability -------------------------------------
    m0 = axes[0].scatter(lon, lat, c=g["model_score"], cmap=RAMP, marker="s",
                         s=s, linewidths=0, vmin=0.0, zorder=2)
    cb0 = fig.colorbar(m0, ax=axes[0], fraction=0.040, pad=0.025)
    cb0.set_label("predicted bust probability", color=INK2, fontsize=13)
    panel_title(axes[0], "A", "What VISHWAS said, five days out",
                "issued {}".format(init_dt.strftime("%-d %B %Y")))

    # --- B: what actually happened -----------------------------------------
    rain_cmap = ListedColormap([RAMP(x) for x in np.linspace(0.02, 1.0, len(RAIN_BINS) - 1)])
    rain_norm = BoundaryNorm(RAIN_BINS, rain_cmap.N)
    m1 = axes[1].scatter(lon, lat, c=g["truth"], cmap=rain_cmap, norm=rain_norm,
                         marker="s", s=s, linewidths=0, zorder=2)
    mids = [0.5 * (RAIN_BINS[i] + RAIN_BINS[i + 1]) for i in range(len(RAIN_CLASSES))]
    cb1 = fig.colorbar(m1, ax=axes[1], fraction=0.040, pad=0.025,
                       ticks=mids, spacing="uniform")
    cb1.ax.set_yticklabels(
        ["{}  {}".format(n, RAIN_LABELS[i]) for i, n in enumerate(RAIN_CLASSES)])
    cb1.ax.tick_params(length=0, labelsize=12, colors=INK2)
    cb1.outline.set_visible(False)
    # no rotated colourbar label here -- the class names are already wide and a
    # ylabel would push into panel C. The unit lives in the panel subtitle.
    panel_title(axes[1], "B", "What actually happened",
                "IMD gauge rainfall, {} (mm)".format(valid_dt.strftime("%-d %B %Y")))

    # --- C: hits, false alarms, misses -------------------------------------
    order = [(quiet, C_QUIET, 2), (miss, C_MISS, 3),
             (false_alarm, C_FALSE, 4), (hit, C_HIT, 5)]
    for mask, colour, z in order:
        axes[2].scatter(lon[mask], lat[mask], c=colour, marker="s", s=s,
                        linewidths=0, zorder=z)
    panel_title(axes[2], "C", "Where the alert was right",
                "alert budget = top {:.0f}% of the test set".format(a.flag_rate * 100))

    handles = [
        Line2D([], [], marker="s", linestyle="none", markersize=14, color=C_HIT,
               label="flagged, and it busted  ({} pts)".format(n_hit)),
        Line2D([], [], marker="s", linestyle="none", markersize=14, color=C_FALSE,
               label="flagged, no bust  ({} pts)".format(n_false)),
        Line2D([], [], marker="s", linestyle="none", markersize=14, color=C_MISS,
               label="bust, not flagged  ({} pts)".format(n_miss)),
        Line2D([], [], marker="s", linestyle="none", markersize=14, color=C_QUIET,
               label="quiet, and it held  ({} pts)".format(int(quiet.sum()))),
    ]
    leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.043, 0.192),
                     ncol=4, frameon=False, fontsize=15, handletextpad=0.7,
                     columnspacing=3.2, borderpad=0.0)
    for t in leg.get_texts():
        t.set_color(INK)

    # --- figure-level titles (never ax.set_title -- it collides) ------------
    fig.text(0.043, 0.968, "VISHWAS flagged central India five days before the rain came",
             fontsize=29, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.043, 0.912,
             "One forecast date, Day 5. {} of 1,252 gauge-observed land gridpoints busted — "
             "the highest bust rate of the 52 test dates.".format(int(bust.sum())),
             fontsize=17, color=INK2, ha="left", va="top")

    foot = (
        "{} Bust = |ensemble mean − observed| above the 95th percentile for that region and "
        "lead time, fitted on 2018 training data only. "
        "Alert threshold p ≥ {:.3f}, fixed once on the whole 2019 test set (651,040 rows, 52 forecast "
        "dates) and applied here unchanged — not re-fitted for this date. On this date: precision "
        "{:.2f}, recall {:.2f}, n = 1,252 gridpoints."
    ).format(TRUTH_NOTE, thr, precision, recall)
    caveat = ("ONE DATE, CHOSEN AS AN ILLUSTRATION OF THE PRODUCT'S FORM — not evidence of general "
              "performance. The general result is a stratified ROC-AUC of 0.728 against 0.565 for "
              "ensemble spread, over all 52 test dates.")
    body = "\n".join(textwrap.wrap(foot, 185)) + "\n" + "\n".join(textwrap.wrap(caveat, 185))
    fig.text(0.043, 0.142, body, fontsize=12.5, color=INK2, ha="left", va="top",
             linespacing=1.65)

    fig.savefig(a.out, dpi=200, facecolor=SURFACE)
    print("wrote {}".format(a.out))
    print("init {}  valid {}  lead D{}".format(a.init, valid_dt.date(), a.lead))
    print("threshold {:.4f}  flagged {}  bust {}".format(thr, int(flagged.sum()), int(bust.sum())))
    print("hit {}  false {}  miss {}  precision {:.3f}  recall {:.3f}".format(
        n_hit, n_false, n_miss, precision, recall))


if __name__ == "__main__":
    main()
