"""
Label construction — the bridge from the feature table to a trainable dataset.

02_features.py produces GEFS features and nothing else: no truth, no error, no
label. This script joins IMD gauge rainfall onto every (init, lead_day, lat,
lon) row, computes the forecast error, and turns that error into the binary
"bust" label the model is trained on.

WHY THE THRESHOLD IS THE DANGEROUS PART
---------------------------------------
bust = error > 95th percentile. The question a judge will ask is "95th
percentile of WHAT?", and the answer has to be "of the training window, and
only the training window".

If the percentile is computed over all data, every test row helps set the
threshold that later judges it. The metrics do not fail loudly when this
happens — they just come out too good. This project has already shipped one
leak of exactly that shape (the climatology leak, fixed in 02_features.py
finalize()), so --train-end is a REQUIRED argument here with no default. A
silent default is how the last one survived three sessions.

The proof that the split is honest is printed at the end: the train base rate
is ~5% by construction, and the test base rate is NOT. If the test base rate
comes out at exactly 5%, the threshold leaked.

REFERENCE POPULATION
--------------------
Primary is per (lat, lon, lead_day). Every gridpoint then carries exactly 5%
busts in training, so local climatology is removed by construction and the
model has to predict WHEN a forecast busts, not WHERE it rains hard. This is
the same logic that made 04_conditional.py condition on rainfall magnitude,
and it is the harder target to beat.

--by region is the sensitivity variant. It keeps the spatial signal, so "the
Western Ghats are less predictable" stays learnable, which is operationally
useful — but a model can score well on it by learning geography instead of
meteorology. Report it as a sensitivity, never as the headline.

TRUTH IS NOT A FEATURE
----------------------
IMD is truth only (CLAUDE.md, FEATURE SOURCE RULE). `truth`, `error` and
`bust` are labels. Nothing in this file may be fed to the model as an input.

Usage:
  python src/06_label.py --train-end 2018-12-31
  python src/06_label.py --train-end 2018-12-31 --by region
"""

import argparse
import datetime
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imd_truth

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FEATURES = os.path.join(_PROJECT_ROOT, "data", "features.parquet")
DEFAULT_OUT = os.path.join(_PROJECT_ROOT, "data", "labelled.parquet")
DEFAULT_THRESHOLDS = os.path.join(_PROJECT_ROOT, "data", "bust_thresholds.parquet")

# P1 verified the analysis grid lands exactly on IMD points: 65 of our 71
# latitudes and 68 of our 71 longitudes fall inside the IMD domain, with zero
# float error. We assert this rather than trust it — a silent drop to
# nearest-neighbour would shift the truth field by 0.25 deg and nothing else
# in the pipeline would notice.
EXPECTED_LATS_IN_DOMAIN = 65
EXPECTED_LONS_IN_DOMAIN = 68


def assert_exact_colocation():
    """Re-run the P1 colocation check. Hard failure, never a fallback."""
    sample = imd_truth.open_year(2015)
    lat_idx, lon_idx = imd_truth.colocation_index(
        np.asarray(sample.lat_array), np.asarray(sample.lon_array))

    lats_in = int((lat_idx >= 0).sum())
    lons_in = int((lon_idx >= 0).sum())
    if lats_in != EXPECTED_LATS_IN_DOMAIN or lons_in != EXPECTED_LONS_IN_DOMAIN:
        raise RuntimeError(
            "colocation changed: {} lats and {} lons inside the IMD domain, "
            "expected {} and {}. Do NOT switch to nearest-neighbour to make "
            "this pass — find out what moved.".format(
                lats_in, lons_in,
                EXPECTED_LATS_IN_DOMAIN, EXPECTED_LONS_IN_DOMAIN))

    print("colocation  : exact, {} lats and {} lons inside the IMD domain"
          .format(lats_in, lons_in))
    return lat_idx, lon_idx


def region_of(lat, lon):
    """Coarse homogeneous-region label for the sensitivity variant.

    APPROXIMATION, AND SAY SO IN THE REPORT. IMD's own homogeneous regions are
    defined by state boundaries, not by latitude/longitude boxes. These four
    boxes are a readable stand-in on a 0.5 deg grid: exhaustive, non
    overlapping, and close enough to the real division to be meaningful. They
    are not IMD's official regions and must not be labelled as such.
    """
    region = np.full(len(lat), "south_peninsula", dtype=object)
    northern = lat >= 20.0
    region[northern & (lon >= 85.0)] = "east_northeast"
    region[northern & (lon < 85.0) & (lat >= 26.0)] = "northwest"
    region[northern & (lon < 85.0) & (lat < 26.0)] = "central"
    return region


def join_truth(features, lat_index, lon_index):
    """Attach IMD rainfall for each row's VALID date (init + lead_day).

    Loads one truth field per distinct valid date and indexes into it, rather
    than looking up row by row — at five million rows the difference is hours.
    """
    valid = features["valid_date"]
    truth = np.full(len(features), np.nan)

    dates = sorted(valid.unique())
    print("truth join  : {} distinct valid dates".format(len(dates)))

    failures = []
    for number, day in enumerate(dates, 1):
        day = pd.Timestamp(day).date()
        try:
            field = imd_truth.daily_rain(day.year, day.isoformat())
        except Exception as exc:
            # Never invent truth. Record the gap and report it.
            failures.append((day.isoformat(), str(exc)))
            continue

        rows = np.nonzero((valid == np.datetime64(day)).to_numpy())[0]
        truth[rows] = field[lat_index[rows], lon_index[rows]]

        if number % 100 == 0:
            print("              {}/{} dates".format(number, len(dates)),
                  flush=True)

    if failures:
        print()
        print("WARNING: IMD truth failed for {} valid dates. Those rows carry "
              "no truth and are dropped below.".format(len(failures)))
        for day, message in failures[:10]:
            print("   {}  {}".format(day, message))
        if len(failures) > 10:
            print("   ... and {} more".format(len(failures) - 10))
        print()

    return truth


def fit_thresholds(train, keys, percentile):
    """Percentile of |error| per group, computed on TRAINING ROWS ONLY."""
    grouped = train.groupby(keys, observed=True)["error"]
    # Merged rather than assigned side by side: two groupby results are only
    # positionally aligned by convention, and a silent misalignment here would
    # attach the wrong sample count to the wrong threshold.
    table = grouped.quantile(percentile / 100.0).rename("threshold").reset_index()
    counts = grouped.size().rename("n_train").reset_index()
    return table.merge(counts, on=keys, how="left")


def build_labels(table, train_end, by, percentile, min_exceedances):
    """Attach `bust`, `split`, and the threshold that produced each label.

    Returns (labelled, thresholds, fallback_counts).
    """
    table = table.copy()
    table["split"] = np.where(table["init_date"] <= train_end, "train", "test")

    train = table[table["split"] == "train"]
    if train.empty:
        raise RuntimeError(
            "no training rows at or before {}. The threshold cannot be fitted, "
            "and fitting it on test rows is the leak this script exists to "
            "prevent.".format(train_end))

    # Primary grouping, plus the two fallbacks, all fitted on train only.
    if by == "gridpoint":
        primary_keys = ["lat", "lon", "lead_day"]
    else:
        primary_keys = ["region", "lead_day"]

    primary = fit_thresholds(train, primary_keys, percentile)
    regional = fit_thresholds(train, ["region", "lead_day"], percentile)
    globally = fit_thresholds(train, ["lead_day"], percentile)

    # A group with too few training samples has a percentile estimate that is
    # mostly noise — one unlucky day sets the threshold for that gridpoint
    # forever. Fall back, and record it, so the report can say how much of the
    # label set rests on borrowed thresholds.
    # FLOOR ON EXPECTED EXCEEDANCES, NOT SAMPLE COUNT.
    # A pth percentile from n samples rests on n*(1-p/100) observations above
    # the threshold. With 52 training dates a 95th percentile rests on 2.6 of
    # them — which sails past a naive "n >= 30" check while being mostly noise.
    # Gate on the exceedances instead, so the rule scales with the percentile.
    min_needed = min_exceedances / (1.0 - percentile / 100.0)
    usable = primary[primary["n_train"] >= min_needed]
    print("threshold gate: need >= {:.0f} train samples per group "
          "({} exceedances at the {}th pct); {} of {} groups qualify"
          .format(min_needed, min_exceedances, percentile,
                  len(usable), len(primary)))

    labelled = table.merge(
        usable[primary_keys + ["threshold"]], on=primary_keys, how="left")
    labelled["threshold_source"] = np.where(
        labelled["threshold"].notna(), by, None)

    missing = labelled["threshold"].isna()
    if missing.any():
        filled = labelled[missing].drop(columns=["threshold"]).merge(
            regional[["region", "lead_day", "threshold"]],
            on=["region", "lead_day"], how="left")
        assert len(filled) == int(missing.sum()), (
            "fallback merge changed row count ({} -> {}); a duplicate key "
            "would silently shift every threshold".format(
                int(missing.sum()), len(filled)))
        labelled.loc[missing, "threshold"] = filled["threshold"].to_numpy()
        labelled.loc[missing & labelled["threshold"].notna(),
                     "threshold_source"] = "region"

    missing = labelled["threshold"].isna()
    if missing.any():
        filled = labelled[missing].drop(columns=["threshold"]).merge(
            globally[["lead_day", "threshold"]], on=["lead_day"], how="left")
        assert len(filled) == int(missing.sum()), (
            "fallback merge changed row count ({} -> {}); a duplicate key "
            "would silently shift every threshold".format(
                int(missing.sum()), len(filled)))
        labelled.loc[missing, "threshold"] = filled["threshold"].to_numpy()
        labelled.loc[missing & labelled["threshold"].notna(),
                     "threshold_source"] = "global"

    still_missing = int(labelled["threshold"].isna().sum())
    if still_missing:
        raise RuntimeError(
            "{} rows have no threshold even after the global fallback. That "
            "means a lead_day appears in test and never in train — check the "
            "--train-end split.".format(still_missing))

    labelled["bust"] = labelled["error"] > labelled["threshold"]

    primary["scope"] = by
    regional["scope"] = "region"
    globally["scope"] = "global"
    globally["region"] = None
    thresholds = pd.concat([primary, regional, globally], ignore_index=True)
    thresholds["percentile"] = percentile
    thresholds["train_end"] = str(train_end)
    thresholds["min_exceedances"] = min_exceedances
    thresholds["min_train_samples"] = min_needed

    return labelled, thresholds


def report(labelled, rows_in, dropped_truth, by, percentile, train_end):
    print()
    print("=" * 68)
    print("VISHWAS — bust labels  (reference population: per {})".format(by))
    print("=" * 68)
    print("train window: init <= {}".format(train_end))
    print("threshold   : {}th percentile of |ensemble mean - IMD|, TRAIN ONLY"
          .format(percentile))
    print()

    print("rows in                 : {:>9}".format(rows_in))
    print("dropped, no IMD truth   : {:>9}  ({:.1f}%)".format(
        dropped_truth, 100.0 * dropped_truth / max(rows_in, 1)))
    print("rows out                : {:>9}".format(len(labelled)))

    points = labelled.groupby(["lat", "lon"], observed=True).ngroups
    print("gridpoints surviving    : {:>9}  of 5041 ({:.1f}%)".format(
        points, 100.0 * points / 5041))
    print("   P1 expects ~1252: 621 points fall outside the IMD domain and the")
    print("   rest are ocean or no-gauge, stored as -999 and dropped as NaN.")
    print()

    sources = labelled["threshold_source"].value_counts()
    print("threshold provenance:")
    for name, count in sources.items():
        print("   {:<12} {:>9} rows  ({:.1f}%)".format(
            name, count, 100.0 * count / len(labelled)))
    print()

    print("BASE RATES — THIS IS THE HONESTY CHECK")
    for split in ["train", "test"]:
        block = labelled[labelled["split"] == split]
        if block.empty:
            print("   {:<6} no rows".format(split))
            continue
        print("   {:<6} {:>9} rows   bust rate {:.3f}%".format(
            split, len(block), 100.0 * block["bust"].mean()))

    train_block = labelled[labelled["split"] == "train"]
    test_block = labelled[labelled["split"] == "test"]
    print()
    if test_block.empty:
        print("   No test rows for this --train-end, so the base-rate check")
        print("   cannot run. Do not train on this split.")
    else:
        train_rate = 100.0 * train_block["bust"].mean()
        test_rate = 100.0 * test_block["bust"].mean()
        gap = abs(test_rate - train_rate)
        print("   Train sits at ~{:.1f}% by construction. Test is {:.3f}%, a".format(
            100.0 - percentile, test_rate))
        print("   gap of {:.3f} points. THAT GAP IS THE PROOF THE SPLIT IS".format(gap))
        print("   HONEST: the test window never touched its own threshold.")
        if gap < 0.05:
            print()
            print("   WARNING: the test base rate is suspiciously close to the")
            print("   train base rate. Check that --train-end actually split")
            print("   the data and that no test row reached fit_thresholds().")

    print()
    print("no test row contributed to any threshold: enforced in build_labels(),")
    print("which fits every threshold table on split == 'train' only.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Join IMD truth onto the feature table and build bust labels.")
    parser.add_argument("--features", default=DEFAULT_FEATURES)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--thresholds", default=DEFAULT_THRESHOLDS)
    parser.add_argument("--train-end", required=True,
                        help="last init date in the TRAINING window, e.g. "
                             "2018-12-31. REQUIRED and deliberately has no "
                             "default — see the leakage note at the top.")
    parser.add_argument("--by", choices=["gridpoint", "region"],
                        default="gridpoint",
                        help="reference population for the percentile. "
                             "gridpoint is the headline; region is the "
                             "sensitivity variant.")
    parser.add_argument("--percentile", type=float, default=95.0)
    parser.add_argument("--min-exceedances", type=float, default=8.0,
                        help="a group needs this many expected observations "
                             "ABOVE the percentile before its own threshold is "
                             "trusted; otherwise it borrows the regional one. "
                             "At the 95th pct this means >= 160 train samples, "
                             "so a 2-year run correctly falls back to region "
                             "scope and a 5-year run does not.")
    args = parser.parse_args()

    try:
        train_end = datetime.date.fromisoformat(args.train_end)
    except ValueError:
        parser.error("--train-end must be ISO format, e.g. 2018-12-31")

    if not os.path.exists(args.features):
        print("No feature table at {}.".format(args.features))
        print("Run: python src/02_features.py --years 2")
        sys.exit(1)

    features = pd.read_parquet(args.features)
    rows_in = len(features)
    print("features    : {} rows, {} columns".format(rows_in, features.shape[1]))

    features["init_date"] = pd.to_datetime(
        features["init"], format="%Y%m%d").dt.date
    features["valid_date"] = pd.to_datetime(features["init"], format="%Y%m%d") \
        + pd.to_timedelta(features["lead_day"], unit="D")

    assert_exact_colocation()   # hard check; main() builds its own slots below

    # Row -> position on the 71x71 analysis grid. Both grids are built by the
    # same np.arange, so this is an exact lookup, not a search.
    lat_slot = np.rint(
        (features["lat"].to_numpy() - imd_truth.ANALYSIS_LAT[0]) / 0.5).astype(int)
    lon_slot = np.rint(
        (features["lon"].to_numpy() - imd_truth.ANALYSIS_LON[0]) / 0.5).astype(int)
    if lat_slot.min() < 0 or lat_slot.max() >= len(imd_truth.ANALYSIS_LAT) \
            or lon_slot.min() < 0 or lon_slot.max() >= len(imd_truth.ANALYSIS_LON):
        raise RuntimeError("feature grid does not match the analysis grid")

    features["truth"] = join_truth(features, lat_slot, lon_slot)

    # IMD ocean / no-gauge is -999, already NaN by imd_truth.daily_rain(). It
    # is MISSING, never zero rainfall — dropping is the only correct move.
    before = len(features)
    features = features[np.isfinite(features["truth"])].copy()
    dropped_truth = before - len(features)

    if features.empty:
        print("Every row lost its truth. Nothing to label.")
        sys.exit(1)

    # Rainfall cannot be negative. -999 is already handled above, but this one
    # line also catches a changed IMD sentinel, a different undef in a year we
    # have not opened before, and any sign error — the whole class of silent
    # truth corruption, for the cost of a comparison.
    if not bool((features["truth"] >= 0).all()):
        worst = float(features["truth"].min())
        raise RuntimeError(
            "negative rainfall in truth (min {:.1f}). -999 handling or the IMD "
            "undef value has changed. Do NOT clip to zero — find out why."
            .format(worst))

    features["error"] = np.abs(features["precip_mean"] - features["truth"])
    features["region"] = region_of(features["lat"].to_numpy(),
                                   features["lon"].to_numpy())

    labelled, thresholds = build_labels(
        features, train_end, args.by, args.percentile, args.min_exceedances)

    labelled = labelled.drop(columns=["valid_date"])
    labelled.to_parquet(args.out, index=False)
    thresholds.to_parquet(args.thresholds, index=False)

    report(labelled, rows_in, dropped_truth, args.by, args.percentile, train_end)
    print("wrote {}".format(args.out))
    print("wrote {}   <- auditable, reusable, and the record of what the".format(
        args.thresholds))
    print("      label meant. Keep it with any result you report.")


if __name__ == "__main__":
    main()
