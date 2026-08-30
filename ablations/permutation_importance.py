"""
Permutation importance for the VISHWAS bust classifier — P11 Task 3.

MEASURED ON THE TEST SET, not on training data. Training importance is biased
toward high-cardinality continuous features, which here would flatter the
geopotential and wind fields simply because they take many distinct values.

MEASURED IN THE STRATIFIED METRIC, because that is the metric the project
reports. An importance ranking computed on pooled AUC would rank features by
how well they track rainfall amount, which is the artefact the whole evaluation
is built to remove.

THE BINS ARE FROZEN BEFORE PERMUTING. stratified_auc() bins on precip_mean, so
permuting precip_mean would also reshuffle the bin edges and the drop would
mix two different effects. The bins here are computed once from the ORIGINAL
precip_mean and held fixed across every permutation.
"""

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def load_model_module():
    """Import src/07_model.py, whose name starts with a digit."""
    path = os.path.join(_ROOT, "src", "07_model.py")
    spec = importlib.util.spec_from_file_location("model_seven", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["model_seven"] = module
    spec.loader.exec_module(module)
    return module


def frozen_stratified_auc(bust, score, bin_index, m):
    """n-weighted AUC within pre-computed rainfall bins."""
    rows = []
    for value in np.unique(bin_index):
        mask = bin_index == value
        auc = m.safe_auc(bust[mask], score[mask])
        if not np.isnan(auc):
            rows.append((auc, int(mask.sum())))
    if not rows:
        return float("nan")
    total = sum(n for _, n in rows)
    return sum(v * n for v, n in rows) / total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    m = load_model_module()

    table = m.load(m.DEFAULT_LABELS, m.STUDY_MIN, m.STUDY_MAX)
    table, _held = m.carve_validation(table, 4)
    features = m.feature_columns(table, False)

    fit = table[table["role"] == "train"]
    test = table[table["role"] == "test"].copy()
    print("train {} rows | test {} rows | {} features".format(
        len(fit), len(test), len(features)))

    model = HistGradientBoostingClassifier(random_state=args.seed)
    model.fit(fit[features], fit["bust"])

    # Bins frozen here, from the untouched precip_mean.
    bin_index = pd.qcut(test["precip_mean"], m.STRATIFY_BINS,
                        labels=False, duplicates="drop").to_numpy()
    bust = test["bust"].to_numpy().astype(bool)
    matrix = test[features].copy()

    base = frozen_stratified_auc(
        bust, model.predict_proba(matrix)[:, 1], bin_index, m)
    print("baseline stratified AUC (frozen bins): {:.4f}".format(base))
    print("bins: {}   repeats: {}".format(len(np.unique(bin_index)), args.repeats))
    print()

    rng = np.random.default_rng(args.seed)
    results = []
    for number, name in enumerate(features, 1):
        original = matrix[name].to_numpy().copy()
        drops = []
        for _ in range(args.repeats):
            shuffled = original.copy()
            rng.shuffle(shuffled)
            matrix[name] = shuffled
            score = model.predict_proba(matrix)[:, 1]
            drops.append(base - frozen_stratified_auc(bust, score, bin_index, m))
        matrix[name] = original
        results.append({"feature": name,
                        "mean_drop": float(np.mean(drops)),
                        "std": float(np.std(drops))})
        print("  [{}/{}] {:<22} {:+.4f}".format(
            number, len(features), name, np.mean(drops)), flush=True)

    frame = pd.DataFrame(results).sort_values("mean_drop", ascending=False)
    frame.to_csv(os.path.join(_HERE, "permutation_importance.csv"), index=False)

    print()
    print("=" * 60)
    print("PERMUTATION IMPORTANCE — test set, stratified AUC, top {}".format(args.top))
    print("=" * 60)
    print("  {:<24} {:>10} {:>8}".format("feature", "AUC drop", "sd"))
    for _, row in frame.head(args.top).iterrows():
        print("  {:<24} {:>+10.4f} {:>8.4f}".format(
            row["feature"], row["mean_drop"], row["std"]))
    print()
    print("A LARGER DROP MEANS THE MODEL RELIED ON IT MORE.")
    print("Negative means shuffling it HELPED — noise, not signal.")


if __name__ == "__main__":
    main()
