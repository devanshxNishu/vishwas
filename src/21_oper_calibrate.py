"""
P37 follow-up — what does the isotonic map do to a LIVE cycle's tail?

WHY THIS EXISTS. The live probe produced a displayed bust probability of
1.0000 at Day 3. An operational product must never show certainty about a
forecast bust five days before anything can be observed, and P12 already
established why that number is not to be believed: the raw model's p >= 0.9
leaves are saturated, and only 5.6% of the test cells in them actually busted.
This script measures what the published isotonic calibrator does to that tail,
and whether adopting it would move the flagged-cell count.

NOTHING IS REFITTED ON OPERATIONAL DATA. The calibrator is rebuilt on the SAME
validation slice 10_calibration.py uses -- driven by the model bundle's own
stored config (study window, validation_every), so this reproduces the
published fit rather than choosing a new one. Operational data is scored by it
and never seen by it.

THE THRESHOLD QUESTION IS NOT TRIVIALLY "MONOTONE, SO UNCHANGED".
src/confidence.py's THRESHOLD lives in RAW score space. Publishing calibrated
scores means mapping it: high risk becomes p_cal >= iso(THRESHOLD). Isotonic is
monotone NON-DECREASING, not strictly increasing -- PAVA pools violating
regions into flat runs. If a flat run straddles THRESHOLD, cells below the raw
threshold share the same calibrated value as cells above it and the >= test
admits them, so the count can GROW. That is checked here rather than assumed.

    python src/21_oper_calibrate.py
"""

import argparse
import importlib.util
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import confidence


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def quantisation(iso, raw, label):
    """How many DISTINCT numbers can a calibrated display actually show?

    PAVA fits a step function: every raw score inside one pooled block maps to
    the same calibrated value. So the calibrated field is not a continuous
    probability, it is a small set of levels, and cells printing an identical
    number can carry different verdicts anywhere a block spans the threshold --
    not only at 0.126283. This measures how coarse the steps really are before
    a calibrated number goes on a map.
    """
    cal = iso.predict(raw)
    values, counts = np.unique(cal, return_counts=True)
    order = np.argsort(counts)[::-1]
    top10 = counts[order][:10].sum()

    print()
    print("=" * 74)
    print("QUANTISATION — {} ({:,} cells)".format(label, len(raw)))
    print("=" * 74)
    print("  distinct calibrated values      {:>10,}".format(len(values)))
    print("  distinct raw values             {:>10,}".format(len(np.unique(raw))))
    print("  largest block                   {:>10,} cells ({:.2f}% of grid)"
          .format(int(counts.max()), 100.0 * counts.max() / len(raw)))
    print("  median block                    {:>10,} cells".format(int(np.median(counts))))
    print("  cells in blocks of 100+         {:>10,} ({:.2f}%)".format(
        int(counts[counts >= 100].sum()),
        100.0 * counts[counts >= 100].sum() / len(raw)))
    print("  ten largest blocks cover        {:>10,} ({:.2f}%)".format(
        int(top10), 100.0 * top10 / len(raw)))
    print()
    print("  the ten largest, value -> cells:")
    for v, c in zip(values[order][:10], counts[order][:10]):
        print("    {:.6f} {:>10,}  ({:.2f}%)".format(v, int(c), 100.0 * c / len(raw)))
    return len(values), counts


def main():
    ap = argparse.ArgumentParser(description="Isotonic on the live cycle tail.")
    ap.add_argument("--model", default=os.path.join(_ROOT, "models", "vishwas_model.joblib"))
    ap.add_argument("--labels", default=os.path.join(_ROOT, "data", "labelled.parquet"))
    ap.add_argument("--live", default=os.path.join(_ROOT, "data", "features_oper.parquet"))
    ap.add_argument("--save", default=os.path.join(_ROOT, "models", "isotonic_oper.joblib"),
                    help="persist the fitted calibrator so the operational "
                         "runner LOADS it instead of refitting")
    args = ap.parse_args()

    m07 = _load("model07", "07_model.py")
    bundle = joblib.load(args.model)
    model, features, config = bundle["model"], bundle["features"], bundle["config"]

    table = m07.load(args.labels, *config["study_window"])
    table, _ = m07.carve_validation(table, config["validation_every"])
    validation = table[table["role"] == "validation"].copy()
    print("validation slice: {:,} rows / {} dates, base rate {:.3f}%".format(
        len(validation), validation["init"].nunique(), 100 * validation["bust"].mean()))

    p_val = model.predict_proba(validation[features])[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(p_val, validation["bust"].to_numpy().astype(int))
    print("isotonic: {} distinct output levels, max output {:.6f}".format(
        len(np.unique(iso.y_thresholds_)), float(iso.predict([1.0])[0])))

    # Persist it. The operational runner must never refit -- a calibrator
    # refitted per cycle would move the display under the reader, and one
    # refitted on operational data would have no labels to fit against at all.
    os.makedirs(os.path.dirname(args.save), exist_ok=True)
    joblib.dump({
        "isotonic": iso,
        "fitted_on": {
            "labels": args.labels,
            "study_window": config["study_window"],
            "validation_every": config["validation_every"],
            "validation_dates": config["validation_dates"],
            "n_rows": int(len(validation)),
            "base_rate": float(validation["bust"].mean()),
        },
        "cap": float(iso.predict([1.0])[0]),
        "note": "Fitted on the VALIDATION slice only, reproducing "
                "10_calibration.py. Never refit on operational data.",
    }, args.save)
    print("wrote {}".format(args.save))

    live = pd.read_parquet(args.live)
    raw = live["model_score"].to_numpy()
    cal = iso.predict(raw)

    print()
    print("=" * 74)
    print("THE TAIL — what the isotonic map does to a displayed certainty")
    print("=" * 74)
    print("  live raw maximum      {:.10f}  (displays as {:.4f})".format(
        raw.max(), raw.max()))
    print("  isotonic sends it to  {:.6f}".format(float(iso.predict([raw.max()])[0])))
    print("  isotonic(1.0)       = {:.6f}   <- the hard cap; PAVA pools the".format(
        float(iso.predict([1.0])[0])))
    print("                                     violating top region downward,")
    print("                                     so nothing can be published above it")
    print()
    print("  raw cells >= 0.9      {:>6}".format(int((raw >= 0.9).sum())))
    print("  calibrated >= 0.9     {:>6}".format(int((cal >= 0.9).sum())))
    print("  highest calibrated    {:.6f}".format(cal.max()))

    print()
    print("=" * 74)
    print("FLAGGED-CELL COUNT — does adopting the calibrated score move it?")
    print("=" * 74)
    t_raw = confidence.THRESHOLD
    t_cal = float(iso.predict([t_raw])[0])
    flag_raw = raw >= t_raw
    flag_cal = cal >= t_cal
    print("  raw threshold        p >= {:.16f}".format(t_raw))
    print("  maps to calibrated   p >= {:.16f}".format(t_cal))
    print("  flagged, raw scale    {:>6,} of {:,}  ({:.2f}%)".format(
        int(flag_raw.sum()), len(raw), 100 * flag_raw.mean()))
    print("  flagged, calibrated   {:>6,} of {:,}  ({:.2f}%)".format(
        int(flag_cal.sum()), len(cal), 100 * flag_cal.mean()))
    gained = int((flag_cal & ~flag_raw).sum())
    lost = int((flag_raw & ~flag_cal).sum())
    print("  cells gained {}, lost {}".format(gained, lost))
    if gained == 0 and lost == 0:
        print("  IDENTICAL SET. The flat run of the isotonic map does not straddle")
        print("  the threshold, so the transform is rank-preserving here and the")
        print("  published count is untouched by adopting it.")
    else:
        print("  THE SET MOVES. A flat run straddles the threshold; adopting the")
        print("  calibrated score would republish the count. Decide deliberately.")

    print()
    print("VERDICT BANDS, raw vs calibrated-with-mapped-thresholds:")
    f_cal = float(iso.predict([confidence.UNCERTAIN_FLOOR])[0])
    v_raw = confidence.verdicts_of(raw)
    v_cal = (cal >= f_cal).astype(int) + (cal >= t_cal).astype(int)
    for code, name in confidence.VERDICT_NAMES.items():
        print("  {:<10} raw {:>6,}   calibrated {:>6,}".format(
            name, int((v_raw == code).sum()), int((v_cal == code).sum())))
    print("  bands identical: {}".format(bool((v_raw == v_cal).all())))

    quantisation(iso, raw, "live cycle")
    test = pd.read_parquet(os.path.join(_ROOT, "data", "model_predictions.parquet"))
    quantisation(iso, test["model_score"].to_numpy(), "2019 test set")


if __name__ == "__main__":
    main()
