"""
VISHWAS step 04 — the number that goes on the slide.

03_spread_skill.py reports the POOLED spread-skill correlation. Pooled is the
number we must NOT quote (see CLAUDE.md): nearly all of it is the wet/dry
spatial gradient, not a confidence signal. This script produces the number the
pitch actually rests on — the correlation AFTER conditioning on rainfall
magnitude — and, just as importantly, an honest uncertainty band around it.

  python src/04_conditional.py
  python src/04_conditional.py --sample data/spread_skill_4season.parquet
  python src/04_conditional.py --bins 10 --bootstrap 2000

WHY THIS SCRIPT EXISTS
The 0.076 figure in the handoff was computed ad hoc in a chat session and was
never committed. That means it could not be reproduced, and the four-season
re-measurement had nothing to re-run. Now it does. Point this at any sample
parquet produced by 03 and it prints the same table every time.

THE UNCERTAINTY BAND IS THE POINT
The headline claim rests on 3 init dates from one season of one year. Rows
within a single date are massively spatially autocorrelated, so a row-level
bootstrap would report a fake-tight interval (n=136,513 "independent" points
when the real independent unit is the date). This script therefore does a
CLUSTER bootstrap over init dates: each replicate resamples whole dates with
replacement. With 3 dates that interval is very wide — and that width IS the
finding. It is the quantitative argument for the 12-date re-measurement.

READ THE SIGN CONVENTION
A POSITIVE correlation means spread is informative (big spread -> big error).
Near zero, or negative, means spread tells you little or is actively
misleading. We are trying to show the incumbent method is WEAK, so numbers
near zero support the project. Do not "fix" a low number.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_SAMPLE = os.path.join(ROOT, "data", "spread_skill_sample.parquet")

# Matches 03_spread_skill.py, so the two scripts agree on what "wet" means.
WET_THRESHOLD_MM = 0.1
LOG_OFFSET = 0.1


def load(path):
    """
    Load a sample parquet and rebuild any derived column that is missing.

    03 has been edited across sessions, so older sample files carry a
    different column set than newer ones (the 2015 JJAS sample, for instance,
    has no lat/lon). Rebuild what we can and say plainly what is absent.
    """
    if not os.path.exists(path):
        print("No sample at {}".format(path))
        print("Run 03_spread_skill.py first — this script only re-analyses "
              "what 03 produced. It never invents data.")
        sys.exit(1)

    table = pd.read_parquet(path)

    required = {"init", "lead_day", "mean", "spread", "truth"}
    missing = required - set(table.columns)
    if missing:
        print("Sample is missing required columns: {}".format(sorted(missing)))
        sys.exit(1)

    if "error" not in table.columns:
        table["error"] = np.abs(table["mean"] - table["truth"])

    # Restrict to wet points. A dry-point zero has no meaningful log, and
    # including the dry mask manufactures correlation out of the wet/dry
    # boundary — the very artefact this script exists to strip out.
    before = len(table)
    table = table[(table["truth"] > WET_THRESHOLD_MM)
                  | (table["mean"] > WET_THRESHOLD_MM)].copy()
    if len(table) != before:
        print("wet filter: {} -> {} rows".format(before, len(table)))

    table["log_spread"] = np.log(table["spread"] + LOG_OFFSET)
    table["log_error"] = np.log(table["error"] + LOG_OFFSET)

    if "season" not in table.columns:
        month = table["init"].astype(str).str[4:6].astype(int)
        table["season"] = np.select(
            [month.isin([12, 1, 2]), month.isin([3, 4, 5]),
             month.isin([6, 7, 8, 9])],
            ["DJF", "MAM", "JJAS"], default="ON")

    return table


def correlation(block):
    """Spearman-free plain Pearson on the logs, matching 03's convention."""
    if len(block) < 100:
        return np.nan
    return block["log_spread"].corr(block["log_error"])


def conditional_r(table, bins):
    """
    The headline number: correlation within rainfall-magnitude bins, then
    recombined as an n-weighted mean across bins.

    Binning is on the ENSEMBLE MEAN, not on truth. Binning on truth would
    condition on the answer and is not something we could reproduce
    operationally — at forecast time the ensemble mean is known and the truth
    is not.

    Returns (weighted_r, per_bin_dataframe).
    """
    # duplicates="drop" because a dry-heavy sample can put identical edges on
    # several low bins; that collapses them rather than crashing.
    table = table.copy()
    table["bin"] = pd.qcut(table["mean"], bins, labels=False,
                           duplicates="drop")

    rows = []
    for index, block in table.groupby("bin"):
        rows.append({
            "bin": int(index),
            "median_mm": block["mean"].median(),
            "r": correlation(block),
            "n": len(block),
        })
    per_bin = pd.DataFrame(rows)

    usable = per_bin.dropna(subset=["r"])
    if usable["n"].sum() == 0:
        return np.nan, per_bin
    weighted = float((usable["r"] * usable["n"]).sum() / usable["n"].sum())
    return weighted, per_bin


def cluster_bootstrap(table, bins, replicates, seed=0):
    """
    Confidence interval for the conditional correlation, resampling whole
    INIT DATES with replacement.

    The independent unit here is the forecast, not the gridpoint. Two
    gridpoints 50 km apart on the same day are nearly the same observation;
    treating them as independent is what would produce a falsely narrow
    interval. So we resample dates.

    The bins are recomputed inside every replicate, because the binning is
    itself estimated from the data.
    """
    dates = sorted(table["init"].unique())
    if len(dates) < 2:
        return None

    rng = np.random.default_rng(seed)
    by_date = {d: block for d, block in table.groupby("init")}

    estimates = []
    for _ in range(replicates):
        picked = rng.choice(dates, size=len(dates), replace=True)
        replicate = pd.concat([by_date[d] for d in picked], ignore_index=True)
        value, _ = conditional_r(replicate, bins)
        if not np.isnan(value):
            estimates.append(value)

    if not estimates:
        return None
    estimates = np.array(estimates)
    return {
        "low": float(np.percentile(estimates, 2.5)),
        "high": float(np.percentile(estimates, 97.5)),
        "n_dates": len(dates),
        "n_replicates": len(estimates),
    }


def robustness(table, bins):
    """
    How much of the headline rests on the wet filter?

    The wet filter in 03/04 is an OR: keep a point if EITHER the forecast or
    the truth is wet. That admits a whole class of points into the driest
    magnitude bin where the ensemble was confidently dry and it rained anyway
    — narrow spread, large error — which produces a strongly NEGATIVE
    correlation in bin 0 and drags the weighted mean down.

    That is a real and interesting failure mode, but it is not the same claim
    as "spread carries little information within a rain regime". Report both,
    so nobody is surprised by the question in a review.
    """
    variants = []

    weighted, _ = conditional_r(table, bins)
    variants.append(("OR filter, all bins (headline)", weighted, len(table)))

    binned = table.copy()
    binned["bin"] = pd.qcut(binned["mean"], bins, labels=False,
                            duplicates="drop")
    dropped = binned[binned["bin"] > 0]
    value, _ = conditional_r(dropped, bins)
    variants.append(("OR filter, drop driest decile", value, len(dropped)))

    for threshold in (0.5, 1.0, 2.0):
        strict = table[(table["truth"] > threshold)
                       & (table["mean"] > threshold)]
        if len(strict) < 1000:
            continue
        value, _ = conditional_r(strict, bins)
        variants.append(("both forecast AND truth > {} mm".format(threshold),
                         value, len(strict)))

    print("ROBUSTNESS TO THE WET FILTER — read this before quoting a number:")
    for label, value, count in variants:
        print("  {:<34} r = {:+.3f}   n = {:>7}".format(label, value, count))

    values = [v for _, v, _ in variants[1:]]
    if values:
        print()
        print("  The headline is {:+.3f}; excluding the driest bin or requiring".format(
            variants[0][1]))
        print("  both sides wet gives {:+.3f} to {:+.3f}. If those differ a lot,".format(
            min(values), max(values)))
        print("  QUOTE THE ROBUST RANGE, not the headline alone — the headline")
        print("  is then resting on one decile and will not survive review.")
        print()
        print("  Variance explained (r squared), which is the clearest framing:")
        allv = [variants[0][1]] + values
        print("    conditional: {:.2f}% to {:.2f}% of variance in log error".format(
            100 * min(allv) ** 2, 100 * max(allv) ** 2))
        pooled = correlation(table)
        print("    pooled     : {:.1f}%  <- the apparent skill, same data".format(
            100 * pooled ** 2))
    print()


def report(table, bins, replicates):
    dates = sorted(table["init"].unique())
    seasons = sorted(table["season"].unique())

    print()
    print("=" * 68)
    print("VISHWAS — spread-skill, pooled vs conditioned on rainfall magnitude")
    print("=" * 68)
    print("sample      : {} wet points".format(len(table)))
    print("init dates  : {}  ({})".format(len(dates), ", ".join(dates)))
    print("seasons     : {}".format(", ".join(seasons)))
    if "lat" not in table.columns:
        print("note        : no lat/lon in this sample — no regional or "
              "land-mask breakdown possible")
    print()

    pooled = correlation(table)
    print("POOLED r = {:+.3f}     <- DO NOT QUOTE THIS AS 'THE BASELINE'".format(pooled))
    print("  Pooled across gridpoints, this is mostly the wet/dry spatial")
    print("  gradient: wet places have big spread AND big error. That is")
    print("  climatology, not a confidence signal.")
    print()

    print("per lead day (pooled, for reference):")
    for day in sorted(table["lead_day"].unique()):
        block = table[table["lead_day"] == day]
        print("  Day {:<3} {:+.3f}   n={}".format(
            int(day), correlation(block), len(block)))
    print()

    weighted, per_bin = conditional_r(table, bins)
    print("CONDITIONED ON RAINFALL MAGNITUDE ({} bins of ensemble mean):".format(bins))
    print("  bin   median rain      r         n")
    for _, row in per_bin.iterrows():
        r_text = "  n/a " if np.isnan(row["r"]) else "{:+.3f}".format(row["r"])
        print("  {:<5} {:>8.2f} mm     {}   {:>7}".format(
            int(row["bin"]), row["median_mm"], r_text, int(row["n"])))
    print()
    print("  WEIGHTED CONDITIONAL r = {:+.3f}   <- THIS is the honest baseline".format(weighted))
    print()

    interval = cluster_bootstrap(table, bins, replicates)
    if interval is None:
        print("  (too few init dates for a bootstrap interval)")
    else:
        print("  95% CI (cluster bootstrap over {} init dates, {} replicates):"
              .format(interval["n_dates"], interval["n_replicates"]))
        print("      {:+.3f}  to  {:+.3f}".format(
            interval["low"], interval["high"]))
        if interval["n_dates"] < 8:
            print()
            print("  WARNING: {} init dates is too few to pin this number, and".format(
                interval["n_dates"]))
            print("  this interval is NARROWER than the real uncertainty.")
            print("  A cluster bootstrap can only resample the dates it was")
            print("  given. If those dates are consecutive Wednesdays in one")
            print("  season of one year, the interval measures within-season")
            print("  sampling error and is BLIND to season-to-season and")
            print("  year-to-year variation — which is exactly what could move")
            print("  the headline. Treat it as a floor on the uncertainty,")
            print("  never as the error bar. Do not put a single hero number")
            print("  on a slide until the four-season re-measurement is in.")
    print()

    if len(seasons) > 1:
        print("BY SEASON (conditional r — this is what the re-measure is for):")
        for season in seasons:
            block = table[table["season"] == season]
            value, _ = conditional_r(block, bins)
            print("  {:<5} {:+.3f}   n={:>7}   dates={}".format(
                season, value, len(block), block["init"].nunique()))
        print()
    else:
        print("BY SEASON: only {} present. The four-season re-measurement is".format(seasons[0]))
        print("what turns this from provisional into defensible.")
        print()

    robustness(table, bins)

    print("-" * 68)
    print("READING THIS: pooled {:+.3f} -> conditional {:+.3f}.".format(
        pooled, weighted))
    print("The collapse between those two numbers IS the finding. The exact")
    print("conditional value can move with more data; that it collapses is")
    print("the structural result the pitch should rest on.")
    print("-" * 68)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Conditional spread-skill analysis for VISHWAS.")
    parser.add_argument("--sample", default=DEFAULT_SAMPLE,
                        help="sample parquet written by 03_spread_skill.py")
    parser.add_argument("--bins", type=int, default=10,
                        help="rainfall-magnitude bins (default 10 = deciles)")
    parser.add_argument("--bootstrap", type=int, default=1000,
                        help="cluster bootstrap replicates (0 to skip)")
    args = parser.parse_args()

    table = load(args.sample)
    report(table, args.bins, args.bootstrap)


if __name__ == "__main__":
    main()
