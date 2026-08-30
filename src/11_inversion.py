"""VISHWAS — the pooled-to-stratified inversion, regenerated.

WHY THIS SCRIPT EXISTS
    figures/fig4_inversion.png was already in the deck with correct arithmetic
    (+0.0234 pooled, +0.1634 stratified, 6.98x) but two labelling faults, and
    no generating script anywhere in the repo:

    1. It printed "+0.163" alone in 40pt type. CLAUDE.md says, in capitals,
       QUOTE THE MARGIN AS +0.13 TO +0.16, NEVER +0.163 ALONE. The deck's most
       prominent number was breaking the project's own Q&A rule.
    2. Its footnote read "1,302,080 gridpoint-days". That is the whole labelled
       table -- train plus validation plus test. The margin is computed on the
       651,040 TEST rows. Stating a sample size 2x the real one under a chart
       about held-out performance is exactly what the label-every-figure rule
       exists to stop.

    Both are fixed here and the figure is reproducible from now on.

TWO RANGES, AND THEY ARE NOT THE SAME THING
    bootstrap CI      +0.1080 to +0.1926   uncertainty from resampling dates
    robustness range  +0.1322 to +0.1634   across rainfall-bin definitions
    The "+0.13 to +0.16" the deck quotes is the SECOND one. They are drawn and
    captioned separately so nobody merges them into one interval.

THE ROBUSTNESS RANGE SPANS TWO VARIANTS, NOT FIVE -- corrected 30 Aug (P18).
    07_model.py's panel prints five rows, but three are [truth-filtered]: they
    require BOTH forecast and truth above a threshold, which conditions on the
    OUTCOME and deletes every "said dry, it poured" and "said rain, nothing
    came" bust -- the two classes this system exists to catch. They are fair for
    the Phase 1 correlation and NOT fair for bust-prediction AUC, so they are
    excluded from the verdict range. The range is:
        all bins (headline)    +0.1634
        drop the driest bin    +0.1322
    An earlier caption said "five wet-point definitions". That was wrong here.
    It IS right for Phase 1's 0.17-0.90% variance range, which does span five.

THIS SCRIPT IS THE ONLY GENERATOR FOR figures/fig4_inversion.png.
    Before 30 Aug it was not: the shipped PNG had been made by an ad hoc script
    that hardcoded its literals and was never committed, and this file rendered
    a DIFFERENT footnote -- one that printed the pooled pair (0.909 vs 0.885)
    under CLAUDE.md's then-standing sanctioned exception. The project owner
    removed the pooled pair from the figure on 30 Aug. That decision is now
    reflected here and in CLAUDE.md, and this script reproduces the shipped
    figure. Everything in the caption is computed from the data or read from
    the fitted artifact; nothing is pasted in.

    python src/11_inversion.py
"""

import argparse
import os
import textwrap

import matplotlib
matplotlib.use("Agg")

import importlib.util
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
C_CRUDE = "#9cc2ea"   # the same blue, stepped light -- this bar is the foil
C_FAIR = "#2a78d6"    # categorical slot 1


def load_model_module():
    path = os.path.join(_ROOT, "src", "07_model.py")
    spec = importlib.util.spec_from_file_location("model07", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def drop_driest_bin_margin(m07, frame):
    """Stratified margin with the driest rainfall bin removed.

    Reproduces the "drop the driest bin" row of 07_model.py's robustness panel,
    using that module's own binning and AUC so the two cannot diverge. This is
    the LOW end of the +0.13 to +0.16 range the deck quotes.
    """
    block = frame.copy()
    block["_bin"] = pd.qcut(block["precip_mean"], m07.STRATIFY_BINS,
                            labels=False, duplicates="drop")
    kept = block[block["_bin"] > block["_bin"].min()]
    return (m07.stratified_auc(kept, "model_score")
            - m07.stratified_auc(kept, "baseline_score"))


def train_facts(test_frame):
    """(n_train_rows, n_train_dates) from the fitted artifact.

    Falls back to deriving the date count from the row count when the artifact
    is absent (models/ is gitignored), using this study's fixed grid: 1,252
    gauge-observed gridpoints x 10 lead days = 12,520 rows per forecast date.
    """
    rows_per_date = len(test_frame) // test_frame["init"].nunique()
    path = os.path.join(_ROOT, "models", "vishwas_model.joblib")
    n_rows = None
    if os.path.exists(path):
        try:
            import joblib
            n_rows = int(joblib.load(path)["config"]["n_train_rows"])
        except Exception:
            n_rows = None
    if n_rows is None:
        raise SystemExit(
            "models/vishwas_model.joblib not found and no train row count "
            "available. Re-run src/07_model.py first — this caption states the "
            "training sample size and must not guess it.")
    return n_rows, n_rows // rows_per_date


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pred", default=os.path.join(_ROOT, "data", "model_predictions.parquet"))
    p.add_argument("--out", default=os.path.join(_ROOT, "figures", "fig4_inversion.png"))
    p.add_argument("--bootstrap", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()

    m07 = load_model_module()
    d = pd.read_parquet(a.pred)

    pooled_b = m07.safe_auc(d["bust"], d["baseline_score"])
    pooled_m = m07.safe_auc(d["bust"], d["model_score"])
    strat_b = m07.stratified_auc(d, "baseline_score")
    strat_m = m07.stratified_auc(d, "model_score")
    crude = pooled_m - pooled_b
    fair = strat_m - strat_b

    boot = m07.cluster_bootstrap_margin(d, "model_score", "baseline_score",
                                        a.bootstrap, a.seed)

    # The low end of the ROBUSTNESS range, computed here rather than pasted in.
    # It is the "drop the driest bin" variant from 07_model.py's panel: bin 0
    # holds the collapsed zero-rainfall mass, where ensemble spread is
    # degenerate (0.00 mm on 91% of the bin), so a reviewer will ask what the
    # margin looks like without it. Answer: it survives.
    robust_low = drop_driest_bin_margin(m07, d)

    # Train-side facts, read from the fitted artifact so the caption cannot
    # drift from the model it describes.
    n_train_rows, n_train_dates = train_facts(d)

    print("pooled     {:.4f} vs {:.4f}   margin {:+.4f}".format(pooled_m, pooled_b, crude))
    print("stratified {:.4f} vs {:.4f}   margin {:+.4f}".format(strat_m, strat_b, fair))
    print("ratio {:.2f}x".format(fair / crude))
    print("robustness {:+.4f} (drop driest bin) to {:+.4f} (all bins)".format(
        robust_low, fair))
    print("train {} dates / {:,} rows   test {} dates / {:,} rows".format(
        n_train_dates, n_train_rows, d["init"].nunique(), len(d)))
    if boot:
        print("bootstrap CI {:+.4f} to {:+.4f} over {} dates".format(
            boot["low"], boot["high"], boot["n_dates"]))

    fig = plt.figure(figsize=(15.2, 9.4), dpi=200, facecolor=SURFACE)
    ax = fig.add_axes([0.105, 0.285, 0.855, 0.455])
    ax.set_facecolor(SURFACE)

    x = [0, 1]
    ax.bar(x, [crude, fair], width=0.52, color=[C_CRUDE, C_FAIR], zorder=3)

    if boot:
        ax.errorbar([1], [fair], yerr=[[fair - boot["low"]], [boot["high"] - fair]],
                    fmt="none", ecolor=INK, elinewidth=2.4, capsize=13,
                    capthick=2.4, zorder=5)

    ax.text(0, crude + 0.006, "+{:.3f}".format(crude), ha="center", va="bottom",
            fontsize=30, fontweight="bold", color=INK)
    ax.text(1, boot["high"] + 0.008 if boot else fair + 0.008,
            "+{:.3f}".format(fair), ha="center", va="bottom",
            fontsize=30, fontweight="bold", color=INK)
    if boot:
        ax.text(1.31, fair, "95% CI\n{:+.3f} to\n{:+.3f}".format(boot["low"], boot["high"]),
                ha="left", va="center", fontsize=14, color=INK2, linespacing=1.5)

    ax.annotate("{:.0f} times larger".format(fair / crude),
                xy=(0.72, fair * 0.92), xytext=(0.24, fair * 0.40),
                fontsize=20, fontweight="bold", color=C_FAIR, ha="center",
                arrowprops=dict(arrowstyle="-|>", color=C_FAIR, linewidth=2.4,
                                connectionstyle="arc3,rad=-0.32"))

    ax.set_xlim(-0.55, 1.68)
    ax.set_xticks(x)
    ax.set_xticklabels(["Compared crudely\n(pooled across all of India)",
                        "Compared fairly\n(within the same rainfall regime)"],
                       fontsize=17, color=INK)
    ax.set_ylabel("VISHWAS's margin over\nensemble spread  (ROC-AUC)",
                  fontsize=15, color=INK)
    ax.set_ylim(0, max(boot["high"] if boot else fair, fair) * 1.22)
    ax.tick_params(colors=INK2, labelsize=14, length=4)
    ax.tick_params(axis="x", length=0, colors=INK)
    ax.grid(True, axis="y", color=GRID, linewidth=0.9)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)

    fig.text(0.045, 0.955, "The honest comparison is the one that favours us",
             fontsize=31, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.045, 0.888,
             "Pooled scoring hands ensemble spread most of its apparent skill for free, "
             "by letting it track how hard it is raining.\nRemove that and it collapses to "
             "0.565 — barely above chance.",
             fontsize=17, color=INK2, ha="left", va="top", linespacing=1.5)

    # FOOTNOTE — this is the SHIPPED text (deck v17, slide 4). Two things about
    # it are deliberate and must not be "tidied" back:
    #
    # 1. IT DOES NOT PRINT THE POOLED PAIR. An earlier version of this script
    #    printed "0.909 vs 0.885" here under CLAUDE.md's sanctioned-exception
    #    clause. The project owner decided on 30 Aug to take them out, and the
    #    shipped PNG has no pooled pair anywhere. That decision stands and
    #    CLAUDE.md has been amended to match. Do not reinstate them.
    # 2. "TWO BIN DEFINITIONS", NOT FIVE. The robustness panel in
    #    ablations/a_full.log has five rows, but three are [truth-filtered] and
    #    are excluded from the verdict range because they condition on the
    #    outcome. The +0.132-to-+0.163 range spans exactly two variants:
    #    "all bins (headline)" +0.1634 and "drop the driest bin" +0.1322.
    #    The shipped PNG says "five" here and that is an error, corrected below.
    #    (Phase 1's 0.17-0.90% variance range DOES span five wet-point
    #    definitions -- different quantity, correct as printed on slide 6.)
    foot = (
        "Left bar: VISHWAS's margin when every forecast is pooled together. Right bar: the same "
        "margin when forecasts are compared only against others of similar rainfall magnitude — "
        "stratified ROC-AUC {:.3f} against ensemble spread's {:.3f}. The error bar is a cluster "
        "bootstrap over the {} forecast dates, because the forecast is the independent unit and "
        "the gridpoint is not.\n"
        "The margin is quoted as +0.13 to +0.16: across the two rainfall-bin definitions tested it "
        "ranges +{:.3f} to +{:.3f} — the headline, and the same comparison with the driest bin "
        "dropped, where ensemble spread is degenerate. That is a different quantity from the "
        "bootstrap interval above and should not be conflated with it.\n"
        "Trained on 2018 ({} dates, {:,} rows), tested on all 52 Wednesdays of 2019 — a year the "
        "model never saw. n = {:,} test rows over 1,252 gauge-observed land gridpoints, Day 1–10. "
        "Truth: IMD 0.25° gauge-gridded daily rainfall."
    ).format(strat_m, strat_b,
             boot["n_dates"] if boot else d["init"].nunique(),
             robust_low, fair,
             n_train_dates, n_train_rows, len(d))
    wrapped = "\n".join("\n".join(textwrap.wrap(par, 148)) for par in foot.split("\n"))
    fig.text(0.045, 0.185, wrapped, fontsize=12.5, color=INK2, ha="left", va="top",
             linespacing=1.6)

    fig.savefig(a.out, dpi=200, facecolor=SURFACE)
    print("wrote {}".format(a.out))


if __name__ == "__main__":
    main()
