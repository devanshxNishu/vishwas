"""
VISHWAS step 05 — the 5 vs 11 member sensitivity check.

WHY THIS EXISTS. Our baseline is ensemble spread. The GEFSv12 reforecast
carries 5 members on most dates and 11 on Wednesdays; operational GEFS carries
31. A spread computed from 5 members is a NOISY estimate of the true ensemble
spread, and a noisy baseline is EASIER TO BEAT. If our margin over the baseline
shrinks as members increase, then part of our headline is an artefact of a weak
baseline rather than a real signal — and CLAUDE.md says we report that.

We sample Wednesdays, so every init date already carries 11 members. That lets
us hold the dates, the truth, and the metric fixed and vary ONLY the ensemble
size: 5 members (c00,p01-p04) against all 11.

  python src/05_ensemble_size.py --sample data/spread_skill_4season.parquet

Reads what 03 wrote. Computes nothing from the network and invents no data.
"""

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_conditional():
    """04_conditional.py starts with a digit, so it needs an explicit import.

    We reuse ITS binning and bootstrap rather than reimplementing them, so the
    5-member and 11-member numbers are produced by exactly the same code that
    produced the headline conditional number.
    """
    spec = importlib.util.spec_from_file_location(
        "cond04", os.path.join(HERE, "04_conditional.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(table, mean_column, spread_column, cond, bins, bootstrap):
    """Pooled and conditional r for one choice of ensemble size."""
    block = table.copy()
    block["mean"] = block[mean_column]
    block["spread"] = block[spread_column]
    block["error"] = np.abs(block["mean"] - block["truth"])

    # Same wet filter and same log offset as 03 and 04.
    block = block[(block["truth"] > cond.WET_THRESHOLD_MM)
                  | (block["mean"] > cond.WET_THRESHOLD_MM)].copy()
    block["log_spread"] = np.log(block["spread"] + cond.LOG_OFFSET)
    block["log_error"] = np.log(block["error"] + cond.LOG_OFFSET)

    pooled = cond.correlation(block)
    weighted, per_bin = cond.conditional_r(block, bins)
    interval = cond.cluster_bootstrap(block, bins, bootstrap)
    return {
        "n": len(block),
        "pooled": pooled,
        "conditional": weighted,
        "ci": interval,
        "per_bin": per_bin,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample",
                        default=os.path.join(ROOT, "data",
                                             "spread_skill_4season.parquet"))
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--bootstrap", type=int, default=2000)
    args = parser.parse_args()

    if not os.path.exists(args.sample):
        print("No sample at {}".format(args.sample))
        sys.exit(1)

    table = pd.read_parquet(args.sample)
    needed = {"mean", "spread", "mean_5", "spread_5", "truth"}
    missing = needed - set(table.columns)
    if missing:
        print("Sample is missing {}.".format(sorted(missing)))
        print("Re-run 03_spread_skill.py — the 5-member columns were added "
              "2026-08-27 and older samples do not carry them.")
        sys.exit(1)

    cond = load_conditional()
    truth_source = (table["truth_source"].iloc[0]
                    if "truth_source" in table.columns else "unknown")
    dates = table["init"].nunique()

    print("=" * 68)
    print("ENSEMBLE SIZE SENSITIVITY — 5 members vs 11, SAME dates")
    print("truth: {}   dates: {}".format(truth_source, dates))
    print("=" * 68)

    results = {}
    for label, mean_col, spread_col in [
            ("5-member  (c00,p01-p04)", "mean_5", "spread_5"),
            ("11-member (all)", "mean", "spread")]:
        results[label] = evaluate(table, mean_col, spread_col, cond,
                                  args.bins, args.bootstrap)

    print()
    print("  {:<26} {:>9} {:>13} {:>22}".format(
        "ensemble", "pooled r", "conditional r", "95% CI (cluster)"))
    for label, res in results.items():
        interval = res["ci"]
        ci_text = ("{:+.3f} to {:+.3f}".format(interval["low"], interval["high"])
                   if interval else "n/a")
        print("  {:<26} {:>+9.3f} {:>+13.3f} {:>22}".format(
            label, res["pooled"], res["conditional"], ci_text))

    five = results["5-member  (c00,p01-p04)"]
    eleven = results["11-member (all)"]
    d_pooled = eleven["pooled"] - five["pooled"]
    d_cond = eleven["conditional"] - five["conditional"]

    print()
    print("  CHANGE 5 -> 11:  pooled {:+.3f}   conditional {:+.3f}".format(
        d_pooled, d_cond))
    print()
    print("READING THIS:")
    print("  The baseline is what we must beat. If the conditional r RISES")
    print("  with more members, the 5-member baseline was artificially weak")
    print("  and our margin over it is partly an artefact.")
    if d_cond > 0.05:
        print("  -> conditional r rises materially ({:+.3f}). REPORT THIS. Our"
              .format(d_cond))
        print("     margin over the baseline is inflated by ensemble noise.")
    elif d_cond < -0.05:
        print("  -> conditional r FALLS ({:+.3f}) with more members. The"
              .format(d_cond))
        print("     11-member baseline is weaker, not stronger. Report it.")
    else:
        print("  -> conditional r barely moves ({:+.3f}). The baseline is not"
              .format(d_cond))
        print("     materially a small-ensemble artefact, at least from 5->11.")
    print()
    print("  CAVEAT THAT MUST GO IN THE REPORT: 5->11 is not 5->31.")
    print("  Operational GEFS carries 31 members. This check bounds the")
    print("  direction and rough size of the effect over the range the")
    print("  reforecast can actually show us; it does not extrapolate to 31.")

    print()
    print("PER-BIN DETAIL (conditional r by rainfall magnitude):")
    print("  {:<6} {:>12} {:>12}".format("bin", "5-member", "11-member"))
    five_bins = five["per_bin"].set_index("bin")
    eleven_bins = eleven["per_bin"].set_index("bin")
    for b in sorted(five_bins.index):
        a = five_bins.loc[b, "r"]
        c = eleven_bins.loc[b, "r"] if b in eleven_bins.index else np.nan
        fmt = lambda v: "  n/a " if pd.isna(v) else "{:+.3f}".format(v)
        print("  {:<6} {:>12} {:>12}".format(int(b), fmt(a), fmt(c)))


if __name__ == "__main__":
    main()
