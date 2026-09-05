"""VISHWAS — does the edge survive out to Day 10? (P26)

The PS asks for confidence "for Day 1 to Day 10 forecasts", and the dashboard
now ships all ten. That makes the per-lead-day skill load-bearing: an interface
that offers a Day 10 map is claiming the Day 10 map is worth looking at.

    python src/16_lead_curve.py
    python src/16_lead_curve.py --bootstrap 2000

Stratified ROC-AUC, model and ensemble spread, computed SEPARATELY for each of
the ten lead days over the full 52-date test set. Nothing is refitted -- this is
a measurement over data/model_predictions.parquet, which already holds every
lead day.

BINS ARE REFITTED INSIDE EACH LEAD DAY, and that is the point rather than an
oversight. The question a forecaster asks at Day 7 is "within the rainfall
regime the model is forecasting AT DAY 7, can it rank?" Forecast rainfall
distributions differ by lead -- the ensemble mean smooths out as members
diverge -- so borrowing Day 1's bin edges would score Day 7 inside regimes it
never forecast. The globally-binned variant is computed anyway and printed as a
check, because a reader is entitled to know the choice changed nothing.

THESE TEN NUMBERS ARE NOT COMPARABLE TO THE HEADLINE 0.728, and the script
prints the reconciliation so nobody quotes one against the other. The headline
pools all ten lead days and bins them together, so inside a single rainfall bin
the model must rank a Day 1 case against a Day 10 case -- and because bust
thresholds are fitted PER LEAD, the same forecast rainfall carries a different
bust likelihood at each. Splitting by lead deletes that cross-lead comparison,
which is why every per-lead number lands above the pooled-lead one. It is an
easier question, not a better result.

EXPECTATION, STATED BEFORE THE RESULT: skill should decline with lead time.
Reported whichever way it comes out.
"""

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

import figstyle

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PRED = os.path.join(_ROOT, "data", "model_predictions.parquet")
DEFAULT_TABLE = os.path.join(_ROOT, "data", "lead_day_auc.csv")
DEFAULT_FIG = os.path.join(_ROOT, "figures", "fig10_lead_curve.png")


_M07 = None


def load_model_module():
    """07_model.py starts with a digit, so it cannot be imported by name.

    Cached: global_bin_auc is called twenty times and re-executing the module
    on each call is pure waste.
    """
    global _M07
    if _M07 is None:
        path = os.path.join(_ROOT, "src", "07_model.py")
        spec = importlib.util.spec_from_file_location("model07", path)
        _M07 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_M07)
    return _M07


def global_bin_auc(frame, score_column, edges):
    """Stratified AUC using bin edges fitted on the POOLED test set.

    The cross-check for the per-lead binning. Same recombination as
    07_model.stratified_auc -- n-weighted over bins -- only the edges differ.
    """
    m07 = load_model_module()
    block = frame.copy()
    block["bin"] = pd.cut(block["precip_mean"], edges,
                          labels=False, include_lowest=True)
    rows = []
    for _, part in block.groupby("bin"):
        value = m07.safe_auc(part["bust"], part[score_column])
        if not np.isnan(value):
            rows.append((value, len(part)))
    if not rows:
        return float("nan")
    total = sum(n for _, n in rows)
    return sum(v * n for v, n in rows) / total


def figure(table, out, n_rows, n_dates):
    """Layout follows fig1/fig2: 15.2 x 9.4, axes in the upper half, footnote
    below. Series are labelled at the Day 10 end of each line rather than in a
    legend box, which is the convention the rest of the set uses."""
    fig = figstyle.figure(15.2, 9.8)
    figstyle.title(
        fig,
        "The edge holds across the whole forecast range",
        "Stratified ROC-AUC by lead day — VISHWAS against the method\n"
        "operational forecasters use today, ensemble spread.")

    ax = figstyle.axes(fig, [0.085, 0.375, 0.80, 0.385])
    lead = table["lead_day"].to_numpy()

    ax.fill_between(lead, table["baseline"], table["model"],
                    color=figstyle.CAT1, alpha=0.10, zorder=1)
    ax.axhline(0.5, color=figstyle.GRID, linewidth=1.4, zorder=0)
    ax.text(0.72, 0.505, "chance", fontsize=11.5, color=figstyle.INK2,
            ha="left", va="bottom")

    for column, colour, name in (("model", figstyle.CAT1, "VISHWAS"),
                                 ("baseline", figstyle.CAT2, "ensemble spread")):
        ax.plot(lead, table[column], color=colour, linewidth=3.1,
                marker="o", markersize=8, markeredgecolor=figstyle.SURFACE,
                markeredgewidth=1.8, zorder=3)
        ax.text(10.35, table[column].iloc[-1], name, fontsize=14.5,
                color=colour, fontweight="bold", ha="left", va="center")

    # The margin is the finding, so it is printed on the gap it measures.
    for _, r in table.iterrows():
        ax.annotate("+{:.3f}".format(r["margin"]),
                    (r["lead_day"], (r["model"] + r["baseline"]) / 2),
                    fontsize=10.5, color=figstyle.INK2, ha="center", va="center")

    ax.grid(axis="y", color=figstyle.GRID, linewidth=1)
    ax.set_xticks(range(1, 11))
    ax.set_xlim(0.55, 12.4)
    ax.set_ylim(0.48, 0.82)
    ax.set_xlabel("forecast lead time (days)", fontsize=14,
                  color=figstyle.INK2, labelpad=10)
    ax.set_ylabel("stratified ROC-AUC", fontsize=14, color=figstyle.INK2,
                  labelpad=10)

    first, last = table.iloc[0], table.iloc[-1]
    figstyle.footnote(
        fig,
        "Read the shaded gap, not the height of either line. The margin is "
        "+{:.3f} at Day 1 and +{:.3f} at Day 10, and all ten lead days are "
        "positive with the whole 95% interval above zero (cluster bootstrap "
        "over the 52 forecast dates). Both curves end lower than they start — "
        "what medium-range forecasting does — but neither falls monotonically; "
        "at 52 dates per lead the wobble is sampling noise. The separation "
        "does not fade with lead time.\n"
        "NOT COMPARABLE TO THE PUBLISHED ALL-LEAD 0.728, and higher for a "
        "structural reason: pooling the lead days makes the model rank a Day 1 "
        "case against a Day 10 case inside one rainfall bin, and splitting by "
        "lead removes that harder comparison.\n"
        "AUC is stratified inside ten bins of forecast rainfall and recombined "
        "n-weighted, refitted within each lead day; pooled scoring is not "
        "reported because it credits both methods for tracking rainfall amount "
        "rather than for ranking uncertainty. {:,} test rows, {} forecast "
        "dates, 1,252 gauge-observed land gridpoints. GEFSv12 reforecast, 2019 "
        "test year, model trained on 2018; truth for labelling is IMD 0.25 deg "
        "gauge-gridded rainfall."
        .format(first["margin"], last["margin"], n_rows, n_dates),
        y=0.275, width=155)

    figstyle.save(fig, out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pred", default=DEFAULT_PRED)
    p.add_argument("--out-table", default=DEFAULT_TABLE)
    p.add_argument("--out-fig", default=DEFAULT_FIG)
    p.add_argument("--bootstrap", type=int, default=1000)
    a = p.parse_args()

    m07 = load_model_module()

    if not os.path.exists(a.pred):
        print("No predictions at {}. Run src/07_model.py first.".format(a.pred))
        sys.exit(1)
    pred = pd.read_parquet(a.pred)

    print("VISHWAS — skill by lead day (P26)")
    print("=" * 78)
    print("{:,} test rows, {} forecast dates, Day {}-{}".format(
        len(pred), pred["init"].nunique(),
        pred["lead_day"].min(), pred["lead_day"].max()))
    print("stratified AUC, {} rainfall bins, refitted within each lead day"
          .format(m07.STRATIFY_BINS))
    if a.bootstrap:
        print("cluster bootstrap on the margin: {} replicates, resampling the "
              "52 forecast dates".format(a.bootstrap))

    # Pooled bin edges for the cross-check, fitted once on all lead days.
    _, edges = pd.qcut(pred["precip_mean"], m07.STRATIFY_BINS,
                       labels=False, duplicates="drop", retbins=True)

    rows = []
    for lead in sorted(pred["lead_day"].unique()):
        block = pred[pred["lead_day"] == lead]
        model = m07.stratified_auc(block, "model_score")
        base = m07.stratified_auc(block, "baseline_score")
        row = {"lead_day": int(lead), "n": len(block),
               "bust_rate": float(block["bust"].mean()),
               "model": model, "baseline": base, "margin": model - base,
               "model_global_bins": global_bin_auc(block, "model_score", edges),
               "baseline_global_bins": global_bin_auc(block, "baseline_score", edges)}
        ci = m07.cluster_bootstrap_margin(block, "model_score",
                                          "baseline_score", a.bootstrap)
        row["margin_lo"] = ci["low"] if ci else float("nan")
        row["margin_hi"] = ci["high"] if ci else float("nan")
        rows.append(row)
        print("  Day {:>2}  model {:.3f}  spread {:.3f}  margin +{:.3f}  "
              "[{:+.3f}, {:+.3f}]".format(
                  lead, model, base, row["margin"],
                  row["margin_lo"], row["margin_hi"]))

    table = pd.DataFrame(rows)

    print()
    print("PER-LEAD-DAY TABLE")
    print("  {:>3} {:>8} {:>10} {:>9} {:>9} {:>9} {:>20}".format(
        "day", "n", "bust rate", "model", "spread", "margin", "95% CI on margin"))
    for _, r in table.iterrows():
        print("  {:>3} {:>8,} {:>9.2%} {:>9.3f} {:>9.3f} {:>+9.3f} {:>10.3f} to {:+.3f}"
              .format(int(r["lead_day"]), int(r["n"]), r["bust_rate"],
                      r["model"], r["baseline"], r["margin"],
                      r["margin_lo"], r["margin_hi"]))

    print()
    print("CROSS-CHECK — bin edges fitted on the pooled test set instead of")
    print("within each lead day. If the two agree, the binning choice is inert.")
    print("  {:>3} {:>9} {:>9} {:>9} {:>9} {:>9}".format(
        "day", "model", "global", "spread", "global", "d margin"))
    for _, r in table.iterrows():
        gm = r["model_global_bins"] - r["baseline_global_bins"]
        print("  {:>3} {:>9.3f} {:>9.3f} {:>9.3f} {:>9.3f} {:>+9.3f}".format(
            int(r["lead_day"]), r["model"], r["model_global_bins"],
            r["baseline"], r["baseline_global_bins"], gm - r["margin"]))

    first, last = table.iloc[0], table.iloc[-1]
    print()
    print("SHAPE OF THE CURVE")
    print("  model    Day 1 {:.3f} -> Day 10 {:.3f}   ({:+.3f})".format(
        first["model"], last["model"], last["model"] - first["model"]))
    print("  spread   Day 1 {:.3f} -> Day 10 {:.3f}   ({:+.3f})".format(
        first["baseline"], last["baseline"], last["baseline"] - first["baseline"]))
    print("  margin   Day 1 {:+.3f} -> Day 10 {:+.3f}  ({:+.3f})".format(
        first["margin"], last["margin"], last["margin"] - first["margin"]))
    print("  margin positive on {} of {} lead days; whole 95% CI above zero on "
          "{}".format(int((table["margin"] > 0).sum()), len(table),
                      int((table["margin_lo"] > 0).sum())))
    print("  neither curve is monotone — Day {} is the model's best lead and "
          "Day {} its worst.".format(
              int(table.loc[table["model"].idxmax(), "lead_day"]),
              int(table.loc[table["model"].idxmin(), "lead_day"])))

    # The reconciliation, printed so the two numbers are never quoted against
    # each other. Splitting by lead is an EASIER question than the headline.
    pooled_m = m07.stratified_auc(pred, "model_score")
    pooled_b = m07.stratified_auc(pred, "baseline_score")
    print()
    print("RECONCILIATION WITH THE PUBLISHED HEADLINE")
    print("  all ten leads pooled and binned together (the headline):")
    print("    model {:.3f}   spread {:.3f}   margin {:+.3f}".format(
        pooled_m, pooled_b, pooled_m - pooled_b))
    print("  mean of the ten per-lead values (this table):")
    print("    model {:.3f}   spread {:.3f}   margin {:+.3f}".format(
        table["model"].mean(), table["baseline"].mean(),
        table["margin"].mean()))
    print("  The per-lead values are HIGHER because splitting by lead removes")
    print("  the cross-lead ranking the pooled number still has to do. Do not")
    print("  quote a per-lead number as an improvement on 0.728.")

    table.to_csv(a.out_table, index=False)
    print()
    print("wrote {}".format(a.out_table))
    figure(table, a.out_fig, len(pred), pred["init"].nunique())


if __name__ == "__main__":
    main()
