"""VISHWAS — fig1_collapse.png: the headline Phase 1 finding.

Ensemble spread appears to explain 43.9% of the variance in forecast error.
Control for how hard it is raining and it explains under 1%.

WHY THIS SCRIPT EXISTS
    figures/fig1_collapse.png is the most persuasive image in the set and it
    had NO GENERATOR. The figure carrying the project's headline finding could
    not be remade. Written 30 Aug 2026 (P18).

WHAT IT SHOWS, AND WHY THAT NUMBER
    Left bar   43.9%   pooled r^2, the apparent skill
    Right bar   0.90%  conditional r^2, the honest one

    The right bar uses the LARGEST of the conditional variants -- the one most
    favourable to the incumbent -- because the claim is "under 1% HOWEVER you
    slice it". Quoting the smallest (0.17%) would be picking the number that
    flatters us, which is the exact error this project accuses pooled scoring
    of committing. The footnote states the full range.

    Every number is computed here from data/spread_skill_4season.parquet using
    04_conditional.py's own functions, so this figure cannot drift from the
    script that produces the reported baseline.

    python src/12_fig1_collapse.py
"""

import argparse
import importlib.util
import os

import figstyle as fs

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SAMPLE = os.path.join(_ROOT, "data", "spread_skill_4season.parquet")


def load_conditional_module():
    """Import 04_conditional.py — its numeric leading name blocks a plain import."""
    path = os.path.join(_ROOT, "src", "04_conditional.py")
    spec = importlib.util.spec_from_file_location("conditional04", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def variance_terms(m04, table, bins):
    """(pooled_pct, conditional_low_pct, conditional_high_pct).

    Conditional variants are exactly 04_conditional.robustness()'s list: the
    headline, the drop-driest-decile variant, and the three both-sides-wet
    thresholds. All five are legitimate HERE -- unlike the model's AUC range,
    where the truth-filtered variants condition on the outcome. For a
    correlation between spread and error they are a fair sensitivity check,
    which is why the Phase 1 range spans five definitions and the model's
    spans two.
    """
    pooled = m04.correlation(table)

    values = [m04.conditional_r(table, bins)[0]]

    binned = table.copy()
    import pandas as pd
    binned["bin"] = pd.qcut(binned["mean"], bins, labels=False,
                            duplicates="drop")
    values.append(m04.conditional_r(binned[binned["bin"] > 0], bins)[0])

    for threshold in (0.5, 1.0, 2.0):
        strict = table[(table["truth"] > threshold) & (table["mean"] > threshold)]
        if len(strict) >= 1000:
            values.append(m04.conditional_r(strict, bins)[0])

    squares = [100 * v ** 2 for v in values]
    return 100 * pooled ** 2, min(squares), max(squares), len(values)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sample", default=DEFAULT_SAMPLE)
    p.add_argument("--out", default=os.path.join(_ROOT, "figures", "fig1_collapse.png"))
    p.add_argument("--bins", type=int, default=10)
    a = p.parse_args()

    m04 = load_conditional_module()
    table = m04.load(a.sample)

    pooled_pct, cond_low, cond_high, n_variants = variance_terms(
        m04, table, a.bins)

    print("pooled       {:.1f}% of variance".format(pooled_pct))
    print("conditional  {:.2f}% to {:.2f}% across {} wet-point definitions".format(
        cond_low, cond_high, n_variants))
    print("n = {:,} wet samples, {} init dates".format(
        len(table), table["init"].nunique()))

    fig = fs.figure(15.2, 9.4)
    ax = fs.axes(fig, [0.105, 0.325, 0.855, 0.405])

    bars = ax.bar([0, 1], [pooled_pct, cond_high], width=0.52,
                  color=[fs.SEQ_LOW, fs.CAT1], zorder=3)
    bars[0].set_edgecolor(fs.CAT1)
    bars[0].set_linewidth(1.2)

    ax.text(0, pooled_pct + 1.1, "{:.1f}%".format(pooled_pct), ha="center",
            va="bottom", fontsize=40, fontweight="bold", color=fs.INK)
    ax.text(1, cond_high + 1.1, "{:.2f}%".format(cond_high), ha="center",
            va="bottom", fontsize=40, fontweight="bold", color=fs.CAT1)

    ax.annotate("", xy=(0.78, cond_high + 0.6), xytext=(0.22, pooled_pct * 0.55),
                arrowprops=dict(arrowstyle="-|>", color=fs.CAT1, linewidth=2.4,
                                connectionstyle="arc3,rad=-0.28"))
    ax.text(0.5, pooled_pct * 0.62, "compare fairly", ha="center", va="bottom",
            fontsize=20, fontweight="bold", color=fs.CAT1)

    ax.set_xlim(-0.55, 1.55)
    ax.set_ylim(0, pooled_pct * 1.28)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Compared crudely\n(pooled across all of India)",
                        "Compared fairly\n(within the same rainfall regime)"],
                       fontsize=17, color=fs.INK)
    ax.tick_params(axis="x", length=0, colors=fs.INK)
    ax.set_ylabel("Variance in forecast error\nexplained by ensemble spread",
                  fontsize=15, color=fs.INK)
    ax.grid(True, axis="y", color=fs.GRID, linewidth=0.9)

    fs.title(
        fig,
        "The signal forecasters trust today explains under 1%",
        "Ensemble spread appears to explain {:.1f}% of the variance in forecast error.\n"
        "Once you control for how hard it is raining, it explains under 1%.".format(
            pooled_pct))

    fs.footnote(fig, (
        "The right-hand bar is the LARGEST of the {} conditional variants — the reading most "
        "favourable to ensemble spread. Across all {} the figure is {:.2f}% to {:.2f}%, i.e. under "
        "1% however the data is sliced, which is why the claim is made in that form rather than as "
        "a single correlation.\n"
        "Correlation is between log ensemble spread and log absolute error, computed within "
        "deciles of forecast rainfall and recombined n-weighted; variance explained is r squared. "
        "Binning is on the ENSEMBLE MEAN, never on truth — at forecast time the truth is not "
        "known.\n"
        "n = {:,} wet samples over {} gauge-observed land gridpoints, from {} GEFSv12 reforecasts "
        "spanning all four seasons and three years (2012 / 2015 / 2018), Day 1–10. "
        "Truth: IMD 0.25° gauge-gridded daily rainfall."
    ).format(n_variants, n_variants, cond_low, cond_high, len(table),
             "{:,}".format(table.groupby(["lat", "lon"]).ngroups),
             table["init"].nunique()), y=0.225, width=160, size=12)

    fs.save(fig, a.out)


if __name__ == "__main__":
    main()
