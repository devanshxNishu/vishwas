"""
VISHWAS P37 — can the published model score a LIVE operational GEFS cycle?

A PROBE, NOT A PIPELINE. No scheduler, no dashboard, no deployment. It answers
one question: does the operational bucket carry what the feature builder needs,
at the grid the model expects, and where does a live cycle sit relative to the
data the model was trained on.

    python src/20_oper_probe.py --cycle 20260906/00
    python src/20_oper_probe.py --latest

WHY THE OPERATIONAL PATH IS NOT JUST "A DIFFERENT PREFIX"
--------------------------------------------------------
The two archives are organised orthogonally.

  reforecast   ONE FILE PER (variable, member), all steps inside it.
               .../c00/Days:1-10/hgt_pres_abv700mb_2019073100_c00.grib2
  operational  ONE FILE PER (member, step), all variables inside it.
               .../atmos/pgrb2ap5/gep01.t00z.pgrb2a.0p50.f120

So the .idx lookup is by `variable:level:` INSIDE a combined file rather than
by filename, and a single lead day needs several step-files rather than several
variable-files.

FIELD PROVENANCE, CONFIRMED BY READING A REAL .idx (2026-09-07, f120):
  pgrb2ap5   HGT:500 mb, UGRD:500 mb, VGRD:500 mb, UGRD:850 mb, VGRD:850 mb,
             PWAT:entire atmosphere, APCP:surface
  pgrb2bp5   CAPE:surface                       <-- NOT in pgrb2ap5
CAPE IS THE TRAP. pgrb2ap5 carries `CAPE:180-0 mb above ground`, which is
mixed-layer CAPE over the lowest 180 mb — a DIFFERENT QUANTITY from the
reforecast's cape_sfc, which the reforecast .idx confirms is `CAPE:surface`.
Taking the pgrb2a record because the name starts with CAPE would silently feed
the model a different variable. Surface CAPE lives in the b family.

MEMBER COUNT — A DECISION, NOT A DETAIL.
Operational carries 31 members (gec00 + gep01..gep30). The model's spread
features were learned on 11 (c00 + p01..p10). A 31-member spread is a SHARPER
estimate than anything in training, so feeding it in unchanged is a domain
shift inside the model's most important feature family. We SUBSAMPLE to the
first 11 to match training. This project's own 5 -> 11 sensitivity moved the
conditional baseline about +0.015, which is the evidence that ensemble size
matters here; "more members is better" is exactly the wrong instinct.

THE FEATURES ARE BUILT BY 02_features.py's OWN build_rows(), UNCHANGED.
Operational fields are remapped onto the reforecast's variable and member names
and handed to the published function. Reimplementing the feature maths for the
operational path would mean two definitions of every feature and no guarantee
they agree; this way there is one.

THE CLIMATOLOGY IS LOADED, NEVER REFITTED.
CLIMATOLOGY_KEYS is [lat, lon, lead_day, season] — keyed on SEASON, not on
date — so data/climatology.parquet applies unchanged to any future init. Fitting
a climatology on operational data is the leak finalize() was rewritten to
prevent.

THERE IS NO TRUTH FOR A LIVE FORECAST, so this script computes NO accuracy of
any kind. IMD gauge-gridded rainfall lags far beyond this probe's horizon. The
output is a confidence FIELD. A forecaster at Day 5 has observed nothing yet.

THE OPERATING POINT IS FIXED at src/confidence.py's THRESHOLD. It is NOT
recomputed on operational scores. The flagged fraction on a live day will not
be 10%, and that is the signal, not a bug.
"""

import argparse
import concurrent.futures
import datetime
import importlib.util
import os
import sys
import time

import numpy as np
import pandas as pd

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


FETCH = _load("fetch01", "01_fetch.py")
FEAT = _load("feat02", "02_features.py")

OPER_ROOT = FETCH.GEFS_OPER_ROOT

# Operational member -> the reforecast member name build_rows() expects.
# Eleven, deliberately: see MEMBER COUNT in the docstring.
MEMBERS = [("gec00", "c00")] + [("gep%02d" % i, "p%02d" % i) for i in range(1, 11)]

# (idx search key, family, reforecast variable name build_rows() looks up).
# The family column is the whole reason this table exists — see FIELD
# PROVENANCE above.
INSTANT_FIELDS = [
    (":HGT:500 mb:",                 "a", "hgt_pres_abv700mb"),
    (":UGRD:500 mb:",                "a", "ugrd_pres_abv700mb"),
    (":VGRD:500 mb:",                "a", "vgrd_pres_abv700mb"),
    (":UGRD:850 mb:",                "a", "ugrd_pres"),
    (":VGRD:850 mb:",                "a", "vgrd_pres"),
    (":PWAT:entire atmosphere",      "a", "pwat_eatm"),
    (":CAPE:surface:",               "b", "cape_sfc"),
]
APCP_KEY = ":APCP:surface:"

DAILY_STEPS = [24 * d for d in range(1, 11)]
# A daily total is the sum of four disjoint 6-hour buckets, so every multiple
# of 6 is needed for APCP. Confirmed from the index: f102 is 96-102, f108 is
# 102-108, f114 108-114, f120 114-120 — disjoint and tiling, never running
# totals, so they are SUMMED and never differenced.
APCP_STEPS = [6 * k for k in range(1, 41)]


def family_path(cycle_date, cycle_hour, family, member, step):
    return "{}/gefs.{}/{}/atmos/pgrb2{}p5/{}.t{}z.pgrb2{}.0p50.f{:03d}".format(
        OPER_ROOT, cycle_date, cycle_hour, family, member, cycle_hour,
        family, step)


def plan(fs, cycle_date, cycle_hour):
    """Byte ranges for one cycle. Reads indexes only; moves no field data."""
    keys = []
    for oper_member, _ in MEMBERS:
        for step in sorted(set(DAILY_STEPS) | set(APCP_STEPS)):
            keys.append(family_path(cycle_date, cycle_hour, "a", oper_member, step))
        for step in DAILY_STEPS:
            keys.append(family_path(cycle_date, cycle_hour, "b", oper_member, step))

    idx_blobs = fs.cat([k + ".idx" for k in keys])
    sizes = {}
    with concurrent.futures.ThreadPoolExecutor(32) as pool:
        for key, info in zip(keys, pool.map(lambda k: fs.info(k), keys)):
            sizes[key] = info["size"]

    wanted = []          # (path, start, end, variable, member, step)
    for oper_member, ref_member in MEMBERS:
        for step in sorted(set(DAILY_STEPS) | set(APCP_STEPS)):
            key = family_path(cycle_date, cycle_hour, "a", oper_member, step)
            records = FETCH.parse_idx(idx_blobs[key + ".idx"].decode(), sizes[key])
            for search, family, variable in INSTANT_FIELDS:
                if family != "a" or step not in DAILY_STEPS:
                    continue
                hit = [r for r in records if search in r[2]]
                if len(hit) != 1:
                    raise ValueError("{} f{:03d}: {} matched {} records"
                                     .format(oper_member, step, search, len(hit)))
                s, e, _ = hit[0]
                wanted.append((key, s, e, variable, ref_member, step))
            hit = [r for r in records if APCP_KEY in r[2]]
            if len(hit) != 1:
                raise ValueError("{} f{:03d}: APCP matched {} records"
                                 .format(oper_member, step, len(hit)))
            s, e, _ = hit[0]
            wanted.append((key, s, e, "apcp_sfc", ref_member, step))

        for step in DAILY_STEPS:
            key = family_path(cycle_date, cycle_hour, "b", oper_member, step)
            records = FETCH.parse_idx(idx_blobs[key + ".idx"].decode(), sizes[key])
            hit = [r for r in records if ":CAPE:surface:" in r[2]]
            if len(hit) != 1:
                raise ValueError("{} f{:03d}: CAPE:surface matched {} records"
                                 .format(oper_member, step, len(hit)))
            s, e, _ = hit[0]
            wanted.append((key, s, e, "cape_sfc", ref_member, step))
    return wanted


def fetch_fields(fs, wanted):
    """Download the planned ranges and group as fields[var][member][step].

    THE STEP KEY COMES FROM THE INDEX, NOT FROM cfgrib. An accumulation message
    can decode with a step coordinate describing the period rather than its end
    hour, and daily_precip() matches on the end hour. Taking the step from the
    index we already parsed removes that whole class of ambiguity.
    """
    paths = [w[0] for w in wanted]
    starts = [w[1] for w in wanted]
    ends = [w[2] for w in wanted]
    blobs = fs.cat_ranges(paths, starts, ends)

    bad = [i for i, b in enumerate(blobs)
           if not (b[:4] == b"GRIB" and b[-4:] == b"7777")]
    if bad:
        raise ValueError("{} malformed messages, e.g. {}".format(
            len(bad), paths[bad[0]]))

    n_bytes = sum(len(b) for b in blobs)
    fields = {}
    for blob, (_, _, _, variable, member, step) in zip(blobs, wanted):
        array = FEAT.decode(blob)
        fields.setdefault(variable, {}).setdefault(member, {})[step] = array
    return fields, n_bytes


def apply_stored_climatology(rows, climatology_path):
    """Attach anomalies from the STORED climatology. Never refit — see docstring."""
    climatology = pd.read_parquet(climatology_path)
    renamed = {c: c.replace("_mean", "_clim") for c in FEAT.ANOMALY_COLUMNS}
    merged = rows.merge(climatology, on=FEAT.CLIMATOLOGY_KEYS, how="left")
    for column in FEAT.ANOMALY_COLUMNS:
        rows[column.replace("_mean", "_anomaly")] = (
            merged[column].values - merged[renamed[column]].values)

    unmatched = int(merged[renamed[FEAT.ANOMALY_COLUMNS[0]]].isna().sum())
    if unmatched:
        print("  WARNING: {} rows ({:.2f}%) matched no climatology group -> "
              "anomaly NaN".format(unmatched, 100.0 * unmatched / len(rows)))
    else:
        print("  every row matched a stored climatology group "
              "({} groups, keyed on {})".format(
                  len(climatology), ", ".join(FEAT.CLIMATOLOGY_KEYS)))
    return rows


def distribution_report(live, training, features):
    """Where does the live cycle sit relative to what the model was trained on?

    With no truth available this is the only honest check there is. A model
    extrapolating on precip_spread or pwat_mean is not predicting, it is
    guessing, and that has to be visible.
    """
    print()
    print("=" * 78)
    print("FEATURE DISTRIBUTIONS — live cycle vs the model's TRAINING rows")
    print("=" * 78)
    print("  {:<22} {:>9} {:>9} {:>9} {:>9} {:>7}".format(
        "feature", "train p1", "train p99", "live p1", "live p99", "outside"))
    flagged = []
    for name in features:
        if name not in live.columns or name not in training.columns:
            continue
        t = training[name].to_numpy()
        l = live[name].to_numpy()
        t_lo, t_hi = np.nanpercentile(t, [1, 99])
        l_lo, l_hi = np.nanpercentile(l, [1, 99])
        t_min, t_max = np.nanmin(t), np.nanmax(t)
        outside = float(np.mean((l < t_min) | (l > t_max)) * 100.0)
        mark = ""
        if outside > 1.0:
            mark = "  <-- EXTRAPOLATING"
            flagged.append((name, outside, t_min, t_max, np.nanmin(l), np.nanmax(l)))
        print("  {:<22} {:>9.3f} {:>9.3f} {:>9.3f} {:>9.3f} {:>6.2f}%{}".format(
            name, t_lo, t_hi, l_lo, l_hi, outside, mark))

    print()
    if flagged:
        print("  {} feature(s) put more than 1% of live values OUTSIDE the "
              "training range:".format(len(flagged)))
        for name, pct, tmin, tmax, lmin, lmax in flagged:
            print("    {:<22} {:.2f}% outside; train [{:.3f}, {:.3f}] "
                  "live [{:.3f}, {:.3f}]".format(name, pct, tmin, tmax, lmin, lmax))
    else:
        print("  No feature puts more than 1% of live values outside the "
              "training range.")
    return flagged


def newest_complete_cycle(fs, hours_back=4):
    """Walk back from now until a cycle serves the f240 index for every member.

    Completeness is checked on the LAST step of the LAST member, which is what
    a cycle finishes writing. A cycle that is mid-upload will fail here rather
    than produce a short ensemble downstream.
    """
    now = datetime.datetime.utcnow()
    for back in range(hours_back * 6):
        stamp = now - datetime.timedelta(hours=6 * back)
        date = stamp.strftime("%Y%m%d")
        hour = "%02d" % (stamp.hour // 6 * 6)
        probes = [family_path(date, hour, "a", MEMBERS[-1][0], 240) + ".idx",
                  family_path(date, hour, "b", MEMBERS[-1][0], 240) + ".idx"]
        if all(fs.exists(p) for p in probes):
            return date, hour
    raise RuntimeError("no complete cycle found in the last %d hours" % (hours_back * 6))


def main():
    parser = argparse.ArgumentParser(description="P37 operational probe.")
    parser.add_argument("--cycle", default=None,
                        help="YYYYMMDD/HH, e.g. 20260906/00")
    parser.add_argument("--latest", action="store_true",
                        help="use the newest cycle complete out to f240")
    parser.add_argument("--model", default=os.path.join(_ROOT, "models",
                                                        "vishwas_model.joblib"))
    parser.add_argument("--climatology", default=os.path.join(
        _ROOT, "data", "climatology.parquet"))
    parser.add_argument("--training", default=os.path.join(
        _ROOT, "data", "labelled.parquet"),
        help="the model's own training rows, for the distribution check")
    parser.add_argument("--out-features", default=os.path.join(
        _ROOT, "data", "features_oper.parquet"))
    parser.add_argument("--out-pred", default=os.path.join(
        _ROOT, "data", "predictions_oper.parquet"))
    args = parser.parse_args()

    import joblib

    fs = FETCH.connect()
    if args.latest or not args.cycle:
        date, hour = newest_complete_cycle(fs)
        print("newest complete cycle: gefs.{}/{}".format(date, hour))
    else:
        date, hour = args.cycle.split("/")

    print()
    print("=" * 78)
    print("VISHWAS P37 — operational probe, cycle gefs.{}/{}Z".format(date, hour))
    print("=" * 78)
    print("members : {} of 31 available — {} .. {}".format(
        len(MEMBERS), MEMBERS[0][0], MEMBERS[-1][0]))
    print("          SUBSAMPLED to match the 11 the model was trained on. A")
    print("          31-member spread is sharper than anything in training, so")
    print("          using all of them would shift the model's most important")
    print("          feature family. See MEMBER COUNT in the docstring.")
    print("grid    : 0.50 deg (pgrb2ap5/pgrb2bp5) — the analysis grid exactly")
    print("truth   : NONE. No accuracy of any kind is computed below.")
    print()

    clock = time.time()
    wanted = plan(fs, date, hour)
    planned = time.time() - clock
    print("planned {} messages in {:.1f} s".format(len(wanted), planned))

    clock = time.time()
    fields, n_bytes = fetch_fields(fs, wanted)
    transfer = time.time() - clock
    print("fetched {:.1f} MB in {:.1f} s ({:.2f} MB/s)".format(
        n_bytes / 1e6, transfer, n_bytes / 1e6 / transfer))

    for variable, members in sorted(fields.items()):
        print("   {:<22} {} members x {} steps".format(
            variable, len(members), len(members[MEMBERS[0][1]])))

    clock = time.time()
    init = "{}".format(date)
    rows = FEAT.build_rows(fields, init)
    print("\nbuilt {} rows x {} columns via 02_features.build_rows(), unchanged"
          .format(len(rows), rows.shape[1]))

    rows = apply_stored_climatology(rows, args.climatology)
    build = time.time() - clock

    bundle = joblib.load(args.model)
    model, features = bundle["model"], bundle["features"]
    cfg = bundle["config"]
    # NOT "trained <study_window>". The bundle's study_window is the date span
    # of the SOURCE TABLE handed to 07_model.load() -- 2018-2019 for the
    # published model, because the table holds both the training year and the
    # held-out test year. Printing it under the word "trained" made the log
    # read as though the model had seen its own test year, which is the one
    # thing it must not have done. The split itself comes from the `split`
    # column that 06_label.py fitted at --train-end 2018-12-31.
    print("\nmodel   : {} ({} features, seed {}, sklearn {})".format(
        os.path.basename(args.model), len(features), cfg["seed"], cfg["sklearn"]))
    print("          source table spans {} .. {}  <- DATA span, not the "
          "training period".format(*cfg["study_window"]))
    print("          fitted on {:,} rows (bust rate {:.2f}%); {:,} test rows "
          "held out".format(cfg["n_train_rows"], 100 * cfg["train_bust_rate"],
                            cfg["n_test_rows"]))
    print("          {} validation dates also held out".format(
        len(cfg["validation_dates"])))

    missing = [f for f in features if f not in rows.columns]
    if missing:
        sys.exit("operational features are missing {} — the probe cannot "
                 "score this cycle.".format(missing))

    rows["model_score"] = model.predict_proba(rows[features])[:, 1]
    rows["verdict"] = confidence.verdicts_of(rows["model_score"].to_numpy())

    print()
    print("=" * 78)
    print("CONFIDENCE FIELD — no truth, no accuracy, no score of correctness")
    print("=" * 78)
    print("operating point: p >= {:.3f}, the FIXED published threshold, NOT "
          "recomputed here".format(confidence.THRESHOLD))
    flagged = float((rows["model_score"] >= confidence.THRESHOLD).mean())
    print("flagged high risk: {:,} of {:,} cells = {:.2f}%".format(
        int((rows["verdict"] == confidence.HIGH_RISK).sum()), len(rows),
        100 * flagged))
    print("  This is NOT 10%, and that is correct. The threshold is a fixed")
    print("  operating point; how much of the grid crosses it on a given day")
    print("  is the signal.")
    print()
    print("  {:>4} {:>10} {:>10} {:>12} {:>12}".format(
        "day", "mean p", "max p", "high risk %", "uncertain %"))
    for day, part in rows.groupby("lead_day"):
        print("  {:>4} {:>10.4f} {:>10.4f} {:>11.2f}% {:>11.2f}%".format(
            int(day), part["model_score"].mean(), part["model_score"].max(),
            100 * (part["verdict"] == confidence.HIGH_RISK).mean(),
            100 * (part["verdict"] == confidence.UNCERTAIN).mean()))

    training = pd.read_parquet(args.training)
    training = training[training["split"] == "train"]
    print("\ntraining rows for the comparison: {:,} ({} dates)".format(
        len(training), training["init"].nunique()))
    distribution_report(rows, training, features)

    rows.to_parquet(args.out_features, index=False, compression="zstd")
    keep = ["init", "lead_day", "lat", "lon", "precip_mean", "precip_spread",
            "pwat_mean", "model_score", "verdict"]
    rows[[c for c in keep if c in rows.columns]].to_parquet(
        args.out_pred, index=False, compression="zstd")
    print("\nwrote {}".format(args.out_features))
    print("wrote {}".format(args.out_pred))
    print("\nTIMING for one cycle: plan {:.1f} s, transfer {:.1f} s, "
          "features+score {:.1f} s, total {:.1f} s; {:.1f} MB".format(
              planned, transfer, build, planned + transfer + build, n_bytes / 1e6))


if __name__ == "__main__":
    main()
