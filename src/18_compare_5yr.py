"""
P34 step 5 — the three-way comparison, on one metric implementation.

    (a) published   train 2018 only,        test 2019
    (b) new model   train 2015-2017,        test 2019        <- controlled
    (c) new model   train 2015-2017,        test 2018+2019   <- multi-year

(a) vs (b) isolates the effect of more training data on an UNCHANGED question:
same test year, same model class, same features, same metric, same seed. (c)
adds the second test year, which is what retires "one test year is thin".

EVERY NUMBER HERE COMES FROM 07_model.py's OWN FUNCTIONS. They are imported,
not reimplemented, so (a) cannot differ from (b) because of a metric rewrite.
That matters more than it sounds: stratified_auc() re-derives its qcut bin
edges from whatever frame it is handed, so a second implementation with a
different binning convention would produce a difference that looks like a
result and is not.

CONSEQUENCE OF THAT RE-DERIVATION, STATED SO NOBODY HAS TO REDISCOVER IT:
(b)'s bins are cut on the 2019 rows alone, exactly as the published run's were.
(c)'s are cut on 2018+2019 together. So (a) vs (b) is like for like, and (c) is
a different question rather than a bigger version of the same one.

    python src/18_compare_5yr.py \
        --published data/model_predictions.parquet \
        --new data/model_predictions_5yr.parquet
"""

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def load_model_module():
    """07_model.py starts with a digit, so it needs an explicit import."""
    spec = importlib.util.spec_from_file_location(
        "model07", os.path.join(_HERE, "07_model.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load_model_module()


def evaluate(frame, label, bootstrap, seed):
    """Every headline figure for one test frame, using 07_model's metrics."""
    base_rate = float(frame["bust"].mean())
    result = {
        "label": label,
        "n_rows": len(frame),
        "n_dates": int(frame["init"].nunique()),
        "base_rate": base_rate,
        "pooled_base": M.safe_auc(frame["bust"], frame["baseline_score"]),
        "pooled_model": M.safe_auc(frame["bust"], frame["model_score"]),
        "strat_base": M.stratified_auc(frame, "baseline_score"),
        "strat_model": M.stratified_auc(frame, "model_score"),
        "ap_base": M.safe_ap(frame["bust"], frame["baseline_score"]),
        "ap_model": M.safe_ap(frame["bust"], frame["model_score"]),
    }
    result["margin"] = result["strat_model"] - result["strat_base"]
    result["lift_base"] = result["ap_base"] / base_rate
    result["lift_model"] = result["ap_model"] / base_rate
    result["ci"] = M.cluster_bootstrap_margin(
        frame, "model_score", "baseline_score", bootstrap, seed)

    # The one robustness variant that conditions on the FORECAST rather than
    # the outcome. The truth-filtered variants are deliberately not computed
    # here: CLAUDE.md excludes them from the verdict range for bust-prediction
    # AUC, because they delete both extreme bust classes.
    binned = frame.copy()
    binned["_bin"] = pd.qcut(binned["precip_mean"], M.STRATIFY_BINS,
                             labels=False, duplicates="drop")
    result["n_bins"] = int(binned["_bin"].nunique())
    kept = binned[binned["_bin"] > binned["_bin"].min()]
    result["drop_driest_base"] = M.stratified_auc(kept, "baseline_score")
    result["drop_driest_model"] = M.stratified_auc(kept, "model_score")
    result["drop_driest_margin"] = (result["drop_driest_model"]
                                    - result["drop_driest_base"])
    return result


def print_headline(rows):
    print("=" * 78)
    print("THE COMPARISON")
    print("=" * 78)
    print()
    print("  {:<38} {:>8} {:>8} {:>9}".format(
        "", "baseline", "model", "margin"))
    print("  " + "-" * 66)
    for row in rows:
        print("  {:<38} {:>8.3f} {:>8.3f} {:>+9.4f}".format(
            row["label"], row["strat_base"], row["strat_model"], row["margin"]))
    print()
    print("  Stratified ROC-AUC. The pooled pair is computed but NOT printed as")
    print("  a measure of performance — CLAUDE.md bars it from every figure,")
    print("  slide, table and spoken line. It is written to the machine-readable")
    print("  CSV only, as the thing being ruled against.")
    print()

    print("  95% CI on the margin, cluster bootstrap over forecast dates:")
    for row in rows:
        if row["ci"]:
            print("    {:<36} {:+.4f} to {:+.4f}   ({} dates)".format(
                row["label"], row["ci"]["low"], row["ci"]["high"],
                row["ci"]["n_dates"]))
        else:
            print("    {:<36} not computed".format(row["label"]))
    print()

    print("  Supporting detail:")
    print("  {:<38} {:>9} {:>8} {:>9} {:>9}".format(
        "", "rows", "dates", "bust%", "bins"))
    for row in rows:
        print("  {:<38} {:>9,} {:>8} {:>8.2f}% {:>9}".format(
            row["label"], row["n_rows"], row["n_dates"],
            100 * row["base_rate"], row["n_bins"]))
    print()
    print("  {:<38} {:>10} {:>10}".format("PR-AUC lift over base rate",
                                          "baseline", "model"))
    for row in rows:
        print("  {:<38} {:>9.2f}x {:>9.2f}x".format(
            row["label"], row["lift_base"], row["lift_model"]))
    print()
    print("  {:<38} {:>8} {:>8} {:>9}".format(
        "Drop the driest bin", "baseline", "model", "margin"))
    for row in rows:
        print("  {:<38} {:>8.3f} {:>8.3f} {:>+9.4f}".format(
            row["label"], row["drop_driest_base"], row["drop_driest_model"],
            row["drop_driest_margin"]))
    print()


def print_verdict(published, controlled):
    """(a) vs (b) is the only pair where a difference means one thing."""
    delta = controlled["margin"] - published["margin"]
    print("=" * 78)
    print("(a) vs (b) — WHAT MORE TRAINING DATA DID")
    print("=" * 78)
    print()
    print("  Same test year, same features, same estimator, same seed, same")
    print("  metric — but NOT the same labels. The bust threshold is the 95th")
    print("  percentile of the TRAINING window, so retraining on 2015-2017")
    print("  relabels the 2019 test set. The target moved as well as the")
    print("  training data. src/19_paired_ab.py measures how much: it prices")
    print("  the relabelling on a FIXED ranker (ensemble spread, whose scores")
    print("  are bit-identical between the runs) and pairs the bootstrap over")
    print("  the shared 52 dates. Read its verdict before this one.")
    print()
    print("  stratified margin  (a) {:+.4f}   (b) {:+.4f}   change {:+.4f}"
          .format(published["margin"], controlled["margin"], delta))
    print("  model AUC          (a) {:.4f}    (b) {:.4f}    change {:+.4f}"
          .format(published["strat_model"], controlled["strat_model"],
                  controlled["strat_model"] - published["strat_model"]))
    print("  baseline AUC       (a) {:.4f}    (b) {:.4f}    change {:+.4f}"
          .format(published["strat_base"], controlled["strat_base"],
                  controlled["strat_base"] - published["strat_base"]))
    print()
    print("  The baseline is ensemble spread on identical rows, so it SHOULD be")
    print("  unchanged between (a) and (b) — it does not depend on training")
    print("  data at all. A non-zero change there is a bug, not a finding.")
    if abs(controlled["strat_base"] - published["strat_base"]) > 1e-9:
        print("  -> IT MOVED. Investigate before reading anything else here.")
    else:
        print("  -> Identical, as required. The comparison is clean.")
    print()


def per_lead(frame, label):
    print("PER LEAD DAY — {}".format(label))
    print("  {:>4} {:>9} {:>8} {:>10} {:>10} {:>10}".format(
        "day", "n", "bust%", "baseline", "model", "margin"))
    for day, part in frame.groupby("lead_day"):
        base = M.stratified_auc(part, "baseline_score")
        model = M.stratified_auc(part, "model_score")
        print("  {:>4} {:>9,} {:>7.2f}% {:>10.3f} {:>10.3f} {:>+10.4f}".format(
            int(day), len(part), 100 * part["bust"].mean(),
            base, model, model - base))
    print()


def per_bin(frame, label):
    print("PER RAINFALL BIN — {}".format(label))
    table = M.per_bin_table(frame, {"baseline": "baseline_score",
                                    "model": "model_score"})
    print("  {:>4} {:>11} {:>9} {:>8} {:>10} {:>10} {:>10}".format(
        "bin", "median mm", "n", "bust%", "baseline", "model", "margin"))
    for _, row in table.iterrows():
        print("  {:>4} {:>11.2f} {:>9,} {:>7.2f}% {:>10.3f} {:>10.3f} {:>+10.4f}"
              .format(int(row["bin"]), row["median_mm"], int(row["n"]),
                      100 * row["bust_rate"], row["baseline"], row["model"],
                      row["model"] - row["baseline"]))
    print()
    return table


def main():
    parser = argparse.ArgumentParser(description="P34 three-way comparison.")
    parser.add_argument("--published",
                        default=os.path.join(_ROOT, "data",
                                             "model_predictions.parquet"))
    parser.add_argument("--new",
                        default=os.path.join(_ROOT, "data",
                                             "model_predictions_5yr.parquet"))
    parser.add_argument("--controlled-year", default="2019",
                        help="the test year (a) and (b) share")
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-csv",
                        default=os.path.join(_ROOT, "data",
                                             "comparison_5yr.csv"))
    args = parser.parse_args()

    published = pd.read_parquet(args.published)
    new = pd.read_parquet(args.new)

    year = args.controlled_year
    pub_year = published[published["init"].astype(str).str[:4] == year]
    new_year = new[new["init"].astype(str).str[:4] == year]

    if pub_year.empty or new_year.empty:
        sys.exit("no {} rows in one of the prediction sets".format(year))
    if len(pub_year) != len(new_year):
        print("WARNING: {} test rows differ — published {:,}, new {:,}. The "
              "controlled comparison assumes identical rows."
              .format(year, len(pub_year), len(new_year)))

    rows = [
        evaluate(pub_year, "(a) published   train 2018,   test 2019",
                 args.bootstrap, args.seed),
        evaluate(new_year, "(b) new model   train 15-17,  test 2019",
                 args.bootstrap, args.seed),
        evaluate(new, "(c) new model   train 15-17,  test 18+19",
                 args.bootstrap, args.seed),
    ]

    print()
    print_headline(rows)
    print_verdict(rows[0], rows[1])
    per_bin(new_year, "(b) new model, test 2019")
    per_bin(new, "(c) new model, test 2018+2019")
    per_lead(new_year, "(b) new model, test 2019")
    per_lead(new, "(c) new model, test 2018+2019")

    frame = pd.DataFrame([{k: v for k, v in row.items() if k != "ci"}
                          for row in rows])
    for i, row in enumerate(rows):
        frame.loc[i, "ci_low"] = row["ci"]["low"] if row["ci"] else np.nan
        frame.loc[i, "ci_high"] = row["ci"]["high"] if row["ci"] else np.nan
    frame.to_csv(args.out_csv, index=False)
    print("wrote {}".format(args.out_csv))


if __name__ == "__main__":
    main()
