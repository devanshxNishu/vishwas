"""VISHWAS — fig2_deciles.png: why the 43.9% collapses.

Within every rainfall regime, ensemble spread carries almost nothing. The
apparent skill in fig1 is the wet/dry spatial gradient: wet places have big
spread AND big errors, dry places have small of both. That is climatology, not
a confidence signal.

WHY THIS SCRIPT EXISTS
    figures/fig2_deciles.png had NO GENERATOR. Written 30 Aug 2026 (P18).

THE SECOND FINDING IS IN HERE AND IT IS THE BETTER ONE
    Decile 0 does not merely fail to inform -- it correlates NEGATIVELY, near
    -0.47. When the ensemble is confidently dry and it rains anyway, spread
    points the WRONG WAY: narrow spread, huge error. That is a specific,
    operationally usable failure mode, and it is drawn in its own colour
    (categorical slot 2) so it reads as a finding rather than as noise.

    It is also why the headline +0.041 is fragile and must never be quoted
    alone -- this one bin drags the weighted mean down by roughly 0.058. The
    variance framing in fig1 is the robust claim; this figure is the mechanism.

DECILES HERE ARE CORRECT. This is the Phase 1 conditional analysis, which uses
    ten bins of ensemble mean (04_conditional.py --bins 10). Do not confuse it
    with the MODEL's rainfall stratification, which realises EIGHT bins because
    the zero-rainfall mass collapses three quantile edges. Different analysis,
    different sample, different bin count.

    python src/13_fig2_deciles.py
"""

import argparse
import importlib.util
import os

import numpy as np

import figstyle as fs

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SAMPLE = os.path.join(_ROOT, "data", "spread_skill_4season.parquet")


def load_conditional_module():
    path = os.path.join(_ROOT, "src", "04_conditional.py")
    spec = importlib.util.spec_from_file_location("conditional04", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sample", default=DEFAULT_SAMPLE)
    p.add_argument("--out", default=os.path.join(_ROOT, "figures", "fig2_deciles.png"))
    p.add_argument("--bins", type=int, default=10)
    a = p.parse_args()

    m04 = load_conditional_module()
    table = m04.load(a.sample)

    weighted, per_bin = m04.conditional_r(table, a.bins)
    per_bin = per_bin.dropna(subset=["r"]).reset_index(drop=True)
    pooled = m04.correlation(table)

    print("pooled r      {:+.3f}".format(pooled))
    print("weighted cond {:+.3f} over {} bins".format(weighted, len(per_bin)))
    for _, row in per_bin.iterrows():
        print("  bin {:>2}  median {:>7.2f} mm  n {:>6}  r {:+.3f}".format(
            int(row["bin"]), row["median_mm"], int(row["n"]), row["r"]))

    fig = fs.figure(15.2, 9.4)
    ax = fs.axes(fig, [0.085, 0.315, 0.885, 0.415])

    x = np.arange(len(per_bin))
    values = per_bin["r"].to_numpy()
    # The negative bin is the finding, not an outlier: give it its own colour.
    colours = [fs.CAT2 if v < 0 else fs.CAT1 for v in values]
    ax.bar(x, values, width=0.62, color=colours, zorder=3)

    ax.axhline(0, color=fs.INK, linewidth=1.4, zorder=4)
    ax.axhline(pooled, color=fs.INK2, linewidth=1.8, linestyle=(0, (5, 4)),
               zorder=4)
    ax.text(len(per_bin) - 0.42, pooled + 0.018,
            "pooled across all bins  {:+.3f}".format(pooled),
            ha="right", va="bottom", fontsize=14, color=fs.INK2)

    for xi, v in zip(x, values):
        ax.text(xi, v + (0.022 if v >= 0 else -0.022), "{:+.2f}".format(v),
                ha="center", va="bottom" if v >= 0 else "top",
                fontsize=13, color=fs.INK)

    ax.annotate("confidently dry,\nand it rained anyway",
                xy=(0.34, values[0] * 0.55), xytext=(1.65, values[0] * 0.72),
                fontsize=15, fontweight="bold", color=fs.CAT2, ha="left",
                va="center",
                arrowprops=dict(arrowstyle="-|>", color=fs.CAT2, linewidth=2.2,
                                connectionstyle="arc3,rad=0.25"))

    ax.set_xticks(x)
    ax.set_xticklabels(["{:.2g}".format(m) for m in per_bin["median_mm"]],
                       fontsize=13, color=fs.INK)
    ax.set_xlabel("Forecast rainfall for that gridpoint — decile median, mm/day",
                  fontsize=15, color=fs.INK, labelpad=10)
    ax.set_ylabel("Correlation between ensemble spread\nand forecast error",
                  fontsize=15, color=fs.INK)
    ax.set_ylim(min(values.min() * 1.35, -0.1), max(pooled * 1.18, 0.42))
    ax.grid(True, axis="y", color=fs.GRID, linewidth=0.9)

    fs.title(
        fig,
        "Within one rainfall regime, spread carries almost nothing",
        "The apparent skill is geography. Wet places have big spread and big errors; dry places have\n"
        "small of both. Compare like with like and the relationship all but disappears.",
        title_size=27)

    fs.footnote(fig, (
        "Each bar is the correlation between log ensemble spread and log absolute error among "
        "forecasts of SIMILAR predicted rainfall. Pooled across all deciles the correlation is "
        "{:+.3f}; recombined n-weighted within them it is {:+.3f}.\n"
        "THE DRIEST DECILE IS THE FINDING, not an outlier. At {:+.3f} it points the wrong way: when "
        "the ensemble agrees it will stay dry and rain arrives anyway, spread is narrow and the "
        "error is large, so spread is actively MISLEADING there rather than merely uninformative. "
        "That single bin drags the weighted mean down by about 0.058, which is why the weighted "
        "figure is never quoted on its own — the variance framing is the robust claim.\n"
        "Deciles are of the ENSEMBLE MEAN, never of truth. n = {:,} wet samples over {:,} "
        "gauge-observed land gridpoints, from {} GEFSv12 reforecasts spanning all four seasons and "
        "three years (2012 / 2015 / 2018), Day 1–10. Truth: IMD 0.25° gauge-gridded daily rainfall."
    ).format(pooled, weighted, values[0], len(table),
             table.groupby(["lat", "lon"]).ngroups, table["init"].nunique()),
        y=0.225, width=160, size=12)

    fs.save(fig, a.out)


if __name__ == "__main__":
    main()
