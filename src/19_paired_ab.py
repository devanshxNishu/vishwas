"""
Is (b) actually different from (a), or is the gap inside the noise?

The two runs score the SAME 52 forecast dates, so comparing their separate
confidence intervals wastes that pairing — two heavily overlapping intervals
can still hide a consistent per-date difference, and two disjoint ones can be
manufactured by a single wild date. Resample the dates ONCE per replicate and
recompute both margins on the same resample, then take the difference.

IT ALSO SEPARATES TWO EFFECTS THE HEADLINE CONFOUNDS. The bust label is the
95th percentile of the TRAINING window, so retraining on 2015-2017 relabels the
2019 test set: 4,576 of 651,040 rows (0.70%) change class. The target moved as
well as the training data. Ensemble spread gives a free control for that,
because its scores are bit-identical between the two runs — so any change in
the BASELINE's AUC is caused by relabelling alone, with the ranker held fixed.

    python src/19_paired_ab.py
"""

import argparse
import importlib.util
import os

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

spec = importlib.util.spec_from_file_location(
    "model07", os.path.join(_HERE, "07_model.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

KEY = ["init", "lead_day", "lat", "lon"]


def main():
    parser = argparse.ArgumentParser(description="Paired (a) vs (b) bootstrap.")
    parser.add_argument("--published",
                        default=os.path.join(_ROOT, "data",
                                             "model_predictions.parquet"))
    parser.add_argument("--new",
                        default=os.path.join(_ROOT, "data",
                                             "model_predictions_5yr.parquet"))
    parser.add_argument("--year", default="2019")
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    a = pd.read_parquet(args.published)
    b = pd.read_parquet(args.new)
    b = b[b["init"].astype(str).str[:4] == args.year]
    a = a.sort_values(KEY).reset_index(drop=True)
    b = b.sort_values(KEY).reset_index(drop=True)
    assert a[KEY].equals(b[KEY]), "row keys differ; the pairing is not valid"
    assert np.array_equal(a["baseline_score"].values, b["baseline_score"].values), \
        "baseline scores differ; spread is a raw GEFS field and must be identical"

    changed = int((a["bust"].values != b["bust"].values).sum())
    print("paired on {:,} rows over {} forecast dates".format(
        len(a), a["init"].nunique()))
    print("bust labels changed by the retrain: {:,} rows ({:.2f}%)".format(
        changed, 100.0 * changed / len(a)))
    print()

    # Point estimates.
    a_model = M.stratified_auc(a, "model_score")
    a_base = M.stratified_auc(a, "baseline_score")
    b_model = M.stratified_auc(b, "model_score")
    b_base = M.stratified_auc(b, "baseline_score")

    print("  {:<28} {:>9} {:>9} {:>10}".format("", "(a)", "(b)", "change"))
    print("  {:<28} {:>9.4f} {:>9.4f} {:>+10.4f}".format(
        "model AUC", a_model, b_model, b_model - a_model))
    print("  {:<28} {:>9.4f} {:>9.4f} {:>+10.4f}".format(
        "baseline AUC", a_base, b_base, b_base - a_base))
    print("  {:<28} {:>9.4f} {:>9.4f} {:>+10.4f}".format(
        "margin", a_model - a_base, b_model - b_base,
        (b_model - b_base) - (a_model - a_base)))
    print()
    print("  THE BASELINE ROW IS THE RELABELLING CONTROL. Ensemble spread's")
    print("  scores are bit-identical across the two runs, so its {:+.4f} is".format(
        b_base - a_base))
    print("  caused by the changed labels alone. That is the scale of the")
    print("  relabelling effect on a FIXED ranker.")
    print()

    dates = sorted(a["init"].unique())
    rng = np.random.default_rng(args.seed)
    a_by = {d: part for d, part in a.groupby("init")}
    b_by = {d: part for d, part in b.groupby("init")}

    d_margin, d_model, d_base = [], [], []
    for _ in range(args.replicates):
        picked = rng.choice(dates, size=len(dates), replace=True)
        sa = pd.concat([a_by[d] for d in picked], ignore_index=True)
        sb = pd.concat([b_by[d] for d in picked], ignore_index=True)
        am, ab = M.stratified_auc(sa, "model_score"), M.stratified_auc(sa, "baseline_score")
        bm, bb = M.stratified_auc(sb, "model_score"), M.stratified_auc(sb, "baseline_score")
        if any(np.isnan(v) for v in (am, ab, bm, bb)):
            continue
        d_model.append(bm - am)
        d_base.append(bb - ab)
        d_margin.append((bm - bb) - (am - ab))

    def report(name, values):
        values = np.array(values)
        low, high = np.percentile(values, [2.5, 97.5])
        crosses = low <= 0.0 <= high
        print("  {:<28} {:+.4f}   95% CI {:+.4f} to {:+.4f}   {}".format(
            name, float(np.median(values)), low, high,
            "includes zero" if crosses else "excludes zero"))
        return crosses

    print("PAIRED BOOTSTRAP, {} replicates over the same {} dates".format(
        len(d_margin), len(dates)))
    crosses_model = report("(b) - (a) model AUC", d_model)
    report("(b) - (a) baseline AUC", d_base)
    crosses_margin = report("(b) - (a) margin", d_margin)
    print()
    print("  VERDICT")
    if crosses_margin:
        print("  -> The change in margin is NOT separable from zero on these 52")
        print("     dates. More training data did not measurably change the")
        print("     result on the question (a) asked. Report it as unchanged,")
        print("     not as a decline.")
    else:
        print("  -> The change in margin is separable from zero. More training")
        print("     data moved the result on an unchanged question, in the")
        print("     direction shown above.")
    if crosses_model:
        print("  -> The change in model AUC alone is also inside the noise.")


if __name__ == "__main__":
    main()
