"""
The model, the baseline, and the honest comparison between them.

This is the script that produces the number the project is judged on. Getting
the EVALUATION right matters more than getting the model right, so most of the
code below is about measurement, not fitting.

    python src/07_model.py --labels data/labelled.parquet
    python src/07_model.py --with-location        # sensitivity, see FEATURES
    python src/07_model.py --bootstrap 2000

WHAT WE ARE PREDICTING
----------------------
bust = the ensemble mean rainfall missed the IMD gauge observation by more than
the 95th percentile for that place and lead time. Base rate ~5% in training by
construction. 06_label.py built the labels; it fitted every threshold on the
training window alone.

THE BASELINE IS ENSEMBLE SPREAD, AND IT IS NOT A STRAW MAN
----------------------------------------------------------
Ranking forecasts by ensemble spread is what operational forecasters do today.
We rank the identical test rows by precip_spread and score it with the identical
metrics. If we cannot beat it, CLAUDE.md is explicit: say so.

THE POOLED NUMBER WILL FLATTER US. DO NOT QUOTE IT.
---------------------------------------------------
Pooled across all of India the model will likely score 0.75-0.85 ROC-AUC,
because precip_mean predicts large absolute errors almost trivially — wet places
have big errors. That is the SAME artefact this project exists to expose in
ensemble spread (pooled +0.663 collapsing to +0.041 once conditioned on rainfall
magnitude). Quoting our own pooled number would repeat, in our own work, the
error our pitch accuses the incumbent method of.

THE HEADLINE IS THE STRATIFIED NUMBER: AUC computed inside rainfall-magnitude
bins and recombined. Expect it to be much lower. That is honesty, not failure.

FEATURES
--------
Everything comes from GEFS. truth, error, bust and threshold are LABELS and are
never inputs (CLAUDE.md, FEATURE SOURCE RULE).

lat/lon/region are EXCLUDED by default. Under region-scope thresholds a model
that knows the exact gridpoint can learn "this cell busts more often than its
region average" — real signal, but climatology rather than meteorology, and
precisely the geography shortcut the stratified evaluation exists to strip out.
--with-location turns them on as a documented sensitivity.
"""

import argparse
import datetime
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LABELS = os.path.join(_ROOT, "data", "labelled.parquet")
DEFAULT_OUT = os.path.join(_ROOT, "data", "model_predictions.parquet")
DEFAULT_MODEL = os.path.join(_ROOT, "models", "vishwas_model.joblib")

# Study window. features_parts/ still holds four smoke dates from January 2000;
# any train_end inside 2018-2019 would silently make them training rows and feed
# eighteen-year-old weather into the fit. Filtered, not deleted, so the exclusion
# stays visible.
STUDY_MIN = "2018-01-01"
STUDY_MAX = "2019-12-31"

# Columns that are labels, bookkeeping, or geography — never model inputs.
NEVER_FEATURES = {
    "truth", "error", "bust", "threshold", "threshold_source",
    "split", "init", "init_date", "valid_date", "season",
}
LOCATION_FEATURES = {"lat", "lon", "region"}

STRATIFY_BINS = 10


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def load(path, date_min, date_max):
    if not os.path.exists(path):
        print("No labelled dataset at {}".format(path))
        print("Run: python src/06_label.py --train-end 2018-12-31")
        sys.exit(1)

    table = pd.read_parquet(path)
    if "init" not in table.columns:
        print("labelled.parquet has no `init` column — cannot split by time.")
        sys.exit(1)

    table["init_date"] = pd.to_datetime(table["init"], format="%Y%m%d")
    before = len(table)
    table = table[(table["init_date"] >= pd.Timestamp(date_min))
                  & (table["init_date"] <= pd.Timestamp(date_max))].copy()
    dropped = before - len(table)
    if dropped:
        print("study window {} to {}: dropped {} rows outside it".format(
            date_min, date_max, dropped))
    if table.empty:
        print("No rows inside the study window.")
        sys.exit(1)

    month = table["init_date"].dt.month
    table["season_name"] = np.select(
        [month.isin([12, 1, 2]), month.isin([3, 4, 5]), month.isin([6, 7, 8, 9])],
        ["DJF", "MAM", "JJAS"], default="ON")
    return table


def carve_validation(table, every):
    """Hold out every Nth training forecast date as validation.

    P12 (calibration) and P14 (operating point) both need data that is neither
    train nor test, and both are invalidated by touching test. Taking the tail
    of the training year instead would give an ON/DJF-only validation set, and a
    calibration fitted on post-monsoon need not transfer to monsoon — so the
    holdout is interleaved to stay seasonally representative. It sits inside the
    training window, so the test year is never touched.
    """
    train_dates = sorted(table.loc[table["split"] == "train", "init"].unique())
    held = set(train_dates[::every])
    table["role"] = np.where(
        table["split"] == "test", "test",
        np.where(table["init"].isin(held), "validation", "train"))
    return table, held


def report_splits(table):
    print()
    print("SPLITS — seasonal composition is printed so an unbalanced test set")
    print("cannot slip through unnoticed (a test block missing a season would")
    print("invalidate any four-season claim).")
    print("  {:<11} {:>7} {:>9} {:>8}   {}".format(
        "role", "dates", "rows", "bust%", "seasons"))
    for role in ["train", "validation", "test"]:
        block = table[table["role"] == role]
        if block.empty:
            print("  {:<11} {:>7}".format(role, 0))
            continue
        counts = block.groupby("season_name")["init"].nunique()
        seasons = " ".join("{}={}".format(s, counts.get(s, 0))
                           for s in ("DJF", "MAM", "JJAS", "ON"))
        missing = [s for s in ("DJF", "MAM", "JJAS", "ON") if counts.get(s, 0) == 0]
        print("  {:<11} {:>7} {:>9} {:>7.2f}%   {}{}".format(
            role, block["init"].nunique(), len(block),
            100.0 * block["bust"].mean(), seasons,
            "   <-- MISSING {}".format(",".join(missing)) if missing else ""))
    print()


def feature_columns(table, with_location, drop_extra=()):
    """Model inputs, minus anything excluded by policy or by --drop.

    drop_extra is the ablation hook (P11). A name in it that is NOT actually a
    feature raises: a typo'd --drop would otherwise silently fit the FULL model
    and the ablation would report "no effect" for a variant that never ran.
    """
    drop = set(NEVER_FEATURES)
    if not with_location:
        drop |= LOCATION_FEATURES
    drop.add("role")
    drop.add("season_name")
    columns = []
    for name in table.columns:
        if name in drop:
            continue
        if not pd.api.types.is_numeric_dtype(table[name]):
            continue
        columns.append(name)

    drop_extra = [name for name in drop_extra if name]
    unknown = [name for name in drop_extra if name not in columns]
    if unknown:
        raise ValueError(
            "--drop names {} which are not in the feature set. Available: {}. "
            "Refusing to run: a silently ignored --drop would fit the FULL "
            "model and the ablation would look like 'no effect'."
            .format(unknown, columns))

    return [name for name in columns if name not in set(drop_extra)]


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------

def safe_auc(truth, score):
    """ROC-AUC, or NaN when the metric is undefined (one class only)."""
    truth = np.asarray(truth).astype(bool)
    if truth.all() or not truth.any() or len(truth) < 50:
        return float("nan")
    return float(roc_auc_score(truth, score))


def safe_ap(truth, score):
    truth = np.asarray(truth).astype(bool)
    if truth.all() or not truth.any() or len(truth) < 50:
        return float("nan")
    return float(average_precision_score(truth, score))


def stratified_auc(frame, score_column, bins=STRATIFY_BINS):
    """AUC inside rainfall-magnitude bins, recombined n-weighted.

    Binning is on precip_mean — the forecast amount, known at forecast time —
    never on truth, which would condition on the answer.
    """
    block = frame.copy()
    block["bin"] = pd.qcut(block["precip_mean"], bins,
                           labels=False, duplicates="drop")
    rows = []
    for index, part in block.groupby("bin"):
        value = safe_auc(part["bust"], part[score_column])
        if not np.isnan(value):
            rows.append((value, len(part)))
    if not rows:
        return float("nan")
    total = sum(n for _, n in rows)
    return sum(v * n for v, n in rows) / total


def per_bin_table(frame, columns, bins=STRATIFY_BINS):
    block = frame.copy()
    block["bin"] = pd.qcut(block["precip_mean"], bins,
                           labels=False, duplicates="drop")
    out = []
    for index, part in block.groupby("bin"):
        row = {"bin": int(index),
               "median_mm": float(part["precip_mean"].median()),
               "n": len(part),
               "bust_rate": float(part["bust"].mean())}
        for label, column in columns.items():
            row[label] = safe_auc(part["bust"], part[column])
        out.append(row)
    return pd.DataFrame(out)


def cluster_bootstrap_margin(frame, model_column, baseline_column,
                             replicates, seed=0):
    """Interval on (model - baseline) stratified AUC, resampling INIT DATES.

    Gridpoints inside one forecast are nearly the same observation, so a
    row-level bootstrap would report a falsely tight interval. The independent
    unit is the forecast date. Predictions are fixed, so only the evaluation is
    resampled — no refitting.
    """
    dates = sorted(frame["init"].unique())
    if len(dates) < 3 or replicates <= 0:
        return None
    rng = np.random.default_rng(seed)

    # Only five columns are ever read below, but the caller hands us the whole
    # test frame (~35 columns). Concatenating 52 date-groups 2000 times then
    # copies ~180 MB per replicate instead of ~26 MB. Subsetting first is
    # numerically identical and roughly 7x less memory traffic — which matters
    # because P11 pays this cost once per ablation variant.
    needed = ["init", "bust", "precip_mean", model_column, baseline_column]
    frame = frame[[c for c in dict.fromkeys(needed) if c in frame.columns]]

    by_date = {d: part for d, part in frame.groupby("init")}
    margins = []
    for _ in range(replicates):
        picked = rng.choice(dates, size=len(dates), replace=True)
        sample = pd.concat([by_date[d] for d in picked], ignore_index=True)
        model = stratified_auc(sample, model_column)
        base = stratified_auc(sample, baseline_column)
        if not (np.isnan(model) or np.isnan(base)):
            margins.append(model - base)
    if not margins:
        return None
    margins = np.array(margins)
    return {"low": float(np.percentile(margins, 2.5)),
            "high": float(np.percentile(margins, 97.5)),
            "median": float(np.median(margins)),
            "n_dates": len(dates), "n": len(margins)}


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def robustness_panel(test):
    """Does the verdict survive the wet-point definition?

    WHY THIS EXISTS. 04_conditional.py already reports this panel for the
    BASELINE, because the headline spread-skill number turned out to rest
    almost entirely on the driest bin: +0.041 across all bins, but +0.095 once
    the driest decile is dropped or both sides are required to be wet.

    If we hold the incumbent method to that standard and not ourselves, we are
    grading on a curve in our own favour — the exact criticism this project
    levels at pooled spread-skill. So the model gets the identical treatment.

    A further reason it matters here: a large share of rows have precip_mean of
    exactly 0.00, so qcut collapses several decile edges (duplicates="drop")
    and the intended ten bins can silently become five. The real bin count is
    printed, never assumed.
    """
    print("ROBUSTNESS TO THE WET-POINT DEFINITION")
    print("  The baseline is reported this way (04_conditional.py), so the model")
    print("  is too. If the verdict flips between rows, quote the range.")
    print()
    print("  {:<34} {:>9} {:>9} {:>9} {:>6}".format(
        "variant", "baseline", "model", "margin", "bins"))

    variants = []
    binned = test.copy()
    binned["_bin"] = pd.qcut(binned["precip_mean"], STRATIFY_BINS,
                             labels=False, duplicates="drop")
    n_bins = binned["_bin"].nunique()
    variants.append(("all bins (headline)", test, n_bins))

    driest = binned["_bin"].min()
    variants.append(("drop the driest bin",
                     binned[binned["_bin"] > driest], n_bins - 1))

    # CAVEAT, added 29 Aug after the first real run. The variants below filter
    # on TRUTH, which is the outcome. For the spread-vs-error CORRELATION in
    # 04_conditional.py that was a fair check — it removed the dry-mask
    # artefact. For BUST-PREDICTION AUC it is not neutral: requiring truth to
    # be wet deletes every "forecast said dry, it poured" bust, and requiring
    # the forecast to be wet deletes every "forecast said rain, nothing came"
    # bust. Both extreme classes vanish and only middling busts remain, so the
    # margin shrinks for reasons that have nothing to do with model quality.
    # Report them as context; the honest robustness check for THIS metric is
    # "drop the driest bin", which conditions only on the forecast.
    if "truth" in test.columns:
        for threshold in (0.5, 1.0, 2.0):
            strict = test[(test["truth"] > threshold)
                          & (test["precip_mean"] > threshold)]
            if len(strict) >= 1000:
                variants.append(
                    ("[truth-filtered] both > {} mm".format(threshold), strict, None))

    # Only the forecast-conditioned variants count toward the verdict range.
    margins = []
    for label, frame, bins in variants:
        base = stratified_auc(frame, "baseline_score")
        model = stratified_auc(frame, "model_score")
        if np.isnan(base) or np.isnan(model):
            continue
        margins.append(model - base)
        shown = bins if bins is not None else pd.qcut(
            frame["precip_mean"], STRATIFY_BINS, labels=False,
            duplicates="drop").nunique()
        print("  {:<34} {:>9.3f} {:>9.3f} {:>+9.4f} {:>6}".format(
            label, base, model, model - base, shown))

    print()
    honest = margins[:2] if len(margins) >= 2 else margins
    if len(honest) > 1:
        low, high = min(honest), max(honest)
        print("  margin ranges {:+.4f} to {:+.4f} across these definitions.".format(
            low, high))
        if low > 0:
            print("  The model is ahead under EVERY definition — that is the")
            print("  robust form of the claim, and the one to quote.")
        elif high <= 0:
            print("  The model is behind under every definition. Report that.")
        else:
            print("  THE VERDICT FLIPS depending on the wet-point definition.")
            print("  Do NOT quote the favourable one. Report the range and say")
            print("  the result is not yet separable from the baseline.")
    print()


def headline(test, bootstrap_result):
    base_rate = float(test["bust"].mean())

    pooled_model = safe_auc(test["bust"], test["model_score"])
    pooled_base = safe_auc(test["bust"], test["baseline_score"])
    strat_model = stratified_auc(test, "model_score")
    strat_base = stratified_auc(test, "baseline_score")

    ap_model = safe_ap(test["bust"], test["model_score"])
    ap_base = safe_ap(test["bust"], test["baseline_score"])

    print("=" * 70)
    print("RESULTS — test period, {} rows, bust base rate {:.2f}%".format(
        len(test), 100 * base_rate))
    print("=" * 70)
    print()
    print("  {:<34} {:>10} {:>10}".format("", "baseline", "model"))
    print("  {:<34} {:>10} {:>10}".format("", "(spread)", "(VISHWAS)"))
    print("  " + "-" * 56)
    print("  {:<34} {:>10.3f} {:>10.3f}   <- DO NOT QUOTE".format(
        "ROC-AUC, pooled", pooled_base, pooled_model))
    print("  {:<34} {:>10.3f} {:>10.3f}   <- THE HEADLINE".format(
        "ROC-AUC, stratified", strat_base, strat_model))
    print("  {:<34} {:>10.3f} {:>10.3f}".format(
        "PR-AUC, pooled", ap_base, ap_model))
    print("  {:<34} {:>10.2f}x{:>10.2f}x".format(
        "PR-AUC lift over base rate", ap_base / base_rate, ap_model / base_rate))
    print()
    print("  PR-AUC's no-skill floor IS the base rate ({:.3f}), so the lift is".format(
        base_rate))
    print("  the comparable figure. Never compare bare PR-AUC across seasons or")
    print("  regions whose base rates differ.")
    print()

    margin = strat_model - strat_base
    print("  STRATIFIED MARGIN (model - baseline): {:+.4f}".format(margin))
    if bootstrap_result:
        print("  95% CI, cluster bootstrap over {} forecast dates: {:+.4f} to {:+.4f}".format(
            bootstrap_result["n_dates"], bootstrap_result["low"],
            bootstrap_result["high"]))
    print()

    # The decision rule is fixed in the prompt BEFORE results are seen, so that
    # a disappointing number cannot quietly become a different question.
    print("  VERDICT")
    beats = bootstrap_result and bootstrap_result["low"] > 0
    if beats and margin >= 0.02:
        print("  -> The model beats ensemble spread on the honest metric, and the")
        print("     whole confidence interval is above zero.")
    elif margin > 0 and not beats:
        print("  -> The model is ahead ({:+.4f}) but the interval INCLUDES ZERO.".format(margin))
        print("     That is not yet a result. Report it as suggestive and get more")
        print("     data before claiming it.")
    else:
        print("  -> The model does NOT beat ensemble spread on the honest metric.")
        print("     Say so plainly. CLAUDE.md: 'If we cannot beat ensemble spread,")
        print("     SAY SO.' The measurement of the incumbent method stands on its")
        print("     own and remains the project's contribution.")
    print()
    print("  NOTE: accuracy is deliberately not reported anywhere. At a ~5% base")
    print("  rate, predicting 'never a bust' scores 95% and is useless.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Train the bust classifier and compare it honestly to spread.")
    parser.add_argument("--labels", default=DEFAULT_LABELS)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--model-out", default=DEFAULT_MODEL,
                        help="where to persist the fitted model + feature list + config")
    parser.add_argument("--date-min", default=STUDY_MIN)
    parser.add_argument("--date-max", default=STUDY_MAX)
    parser.add_argument("--validation-every", type=int, default=4,
                        help="hold out every Nth training date as validation")
    parser.add_argument("--with-location", action="store_true",
                        help="include lat/lon/region as features (sensitivity)")
    parser.add_argument("--drop", default="",
                        help="comma-separated features to exclude before "
                             "fitting, e.g. --drop month. Ablation hook (P11); "
                             "an unknown name is an error, never a no-op.")
    parser.add_argument("--bootstrap", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    table = load(args.labels, args.date_min, args.date_max)
    table, held = carve_validation(table, args.validation_every)
    report_splits(table)

    dropped_by_flag = [name.strip() for name in args.drop.split(",")]
    features = feature_columns(table, args.with_location, dropped_by_flag)
    print("features ({}): {}".format(len(features), ", ".join(features)))
    if not args.with_location:
        print("  lat/lon/region excluded — see the FEATURES note in the docstring.")
    if args.drop.strip():
        print("  ABLATION, --drop: {}".format(
            ", ".join(n for n in dropped_by_flag if n)))
    print()

    fit = table[table["role"] == "train"]
    test = table[table["role"] == "test"].copy()
    if fit.empty or test.empty:
        print("Need both training and test rows. Check --train-end in 06_label.py.")
        sys.exit(1)

    model = HistGradientBoostingClassifier(random_state=args.seed)
    model.fit(fit[features], fit["bust"].astype(int))
    test["model_score"] = model.predict_proba(test[features])[:, 1]

    # The incumbent method, scored on identical rows with identical metrics.
    test["baseline_score"] = test["precip_spread"]

    bootstrap_result = cluster_bootstrap_margin(
        test, "model_score", "baseline_score", args.bootstrap, args.seed)

    headline(test, bootstrap_result)
    robustness_panel(test)

    print("PER RAINFALL BIN (stratified detail)")
    bins = per_bin_table(test, {"baseline": "baseline_score",
                                "model": "model_score"})
    print("  {:>4} {:>11} {:>9} {:>8} {:>10} {:>10}".format(
        "bin", "median mm", "n", "bust%", "baseline", "model"))
    for _, row in bins.iterrows():
        print("  {:>4} {:>11.2f} {:>9} {:>7.2f}% {:>10.3f} {:>10.3f}".format(
            int(row["bin"]), row["median_mm"], int(row["n"]),
            100 * row["bust_rate"], row["baseline"], row["model"]))
    print()

    keep = ["init", "lead_day", "lat", "lon", "bust", "truth", "error",
            "precip_mean", "precip_spread", "model_score", "baseline_score"]
    keep = [c for c in keep if c in test.columns]
    test[keep].to_parquet(args.out, index=False)
    print("wrote {}".format(args.out))

    # Persist the fitted model. Until now nothing was saved, so a demo had to
    # refit on launch and P12/P14 had to reconstruct the model from scratch to
    # get at it. The feature list and config travel WITH the model: a fitted
    # estimator without its column order is not reloadable, it is a guess.
    os.makedirs(os.path.dirname(args.model_out), exist_ok=True)
    joblib.dump({
        "model": model,
        "features": features,
        "config": {
            "labels": args.labels,
            "study_window": [args.date_min, args.date_max],
            "validation_every": args.validation_every,
            "validation_dates": sorted(held),
            "with_location": args.with_location,
            "dropped": [n for n in dropped_by_flag if n],
            "seed": args.seed,
            "estimator": "HistGradientBoostingClassifier(random_state={})".format(args.seed),
            "n_train_rows": int(len(fit)),
            "n_test_rows": int(len(test)),
            "train_bust_rate": float(fit["bust"].mean()),
            "sklearn": __import__("sklearn").__version__,
            "written": datetime.datetime.now().isoformat(timespec="seconds"),
        },
    }, args.model_out)
    print("wrote {}".format(args.model_out))
    print("  validation dates held out and untouched: {} — reserved for".format(len(held)))
    print("  calibration (P12) and the operating point (P14).")


if __name__ == "__main__":
    main()
