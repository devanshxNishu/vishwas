"""
VISHWAS — score one live operational GEFS cycle, end to end, in one command.

    python src/20_operational.py --date 20260908
    python src/20_operational.py --latest

NOT A SCHEDULER. This runs once when invoked. Where it runs is the next
decision and a sleeping laptop is not an answer, so no cron, launchd job or
Action is written here.

FIVE THINGS ARE ENFORCED AS CONSTANTS AND GUARDS BELOW, NOT AS COMMENTS,
because each one is a way the run can look fine and be wrong:

  1. CYCLE_HOUR -- 00Z only. Every one of the 23 features is read at a VALID
     TIME derived from the cycle hour, so a 06Z cycle shifts the whole feature
     vector six hours against the climatology and against everything the model
     learned. The accumulation window is the most visible case, not the reason.
  2. CAPE_LEVEL / CAPE_FAMILY -- surface CAPE from pgrb2bp5, matched on the
     exact level string. pgrb2ap5 carries "CAPE:180-0 mb above ground", which
     is mixed-layer CAPE: a different physical quantity that would score
     silently.
  3. MEMBERS -- eleven, c00 + p01..p10, matching MEMBERS_WEEKLY. Operational
     offers 31; a 31-member spread is sharper than anything in training.
  4. THRESHOLD -- the fixed raw operating point from src/confidence.py, never
     recomputed. The flagged fraction on a day is the signal, not a target.
  5. EXPECTED_MESSAGES + the GRIB/7777 envelope check -- both BEFORE and
     during transfer, so a late or partial cycle fails fast instead of
     producing a short ensemble.

THE CALIBRATOR IS LOADED, NEVER FITTED. models/isotonic_oper.joblib comes from
src/21_oper_calibrate.py, fitted on the validation slice alone. Operational
data is scored by it and never seen by it.

WHAT IS DISPLAYED VS WHAT IS DECIDED -- these are deliberately different, and
the split is the whole point:
    DISPLAY   the isotonic-calibrated probability, rounded to DISPLAY_STEP.
              Measured on a live grid, the isotonic fit resolves 110 distinct
              values and its ten largest blocks cover half the grid, so a
              four-decimal calibrated number claims precision the fit does not
              have.
    DECIDE    the verdict, banded on the RAW score at THRESHOLD and STORED.
              No consumer re-derives a class from a displayed number. Under
              every display rule some cells print the same number and mean
              different things; storing the verdict removes the question.

DOMAIN. The model learned only where IMD has gauges: 1,252 of 5,041
gridpoints. Features and climatology cover all 5,041, and the ungauged 3,789
are NOT out of distribution (worst feature 0.158% outside the training range,
against 0.008% on the gauge grid -- src/22_domain_check.py). So they are
scored, and MARKED, and excluded from every headline count. In-range is not
verified: no gauge means no label ever existed there, so nothing about those
points has been or can be scored.
"""

import argparse
import datetime
import importlib.util
import json
import os
import sys
import time

import joblib
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import confidence
import imd_truth


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FETCH = _load("fetch01", "01_fetch.py")
PROBE = _load("probe20", "20_oper_probe.py")
EXPORT = _load("export15", "15_dashboard_export.py")
MAHAL = _load("mahal23", "23_mahalanobis.py")

# --- GUARD 1 -------------------------------------------------------------
CYCLE_HOUR = "00"

# --- GUARD 2 -------------------------------------------------------------
CAPE_LEVEL = "CAPE:surface"
CAPE_FAMILY = "b"
CAPE_WRONG_LEVEL = "CAPE:180-0 mb above ground"

# --- GUARD 3 -------------------------------------------------------------
MEMBERS = PROBE.MEMBERS
N_MEMBERS = 11

# --- GUARD 4 -------------------------------------------------------------
THRESHOLD = confidence.THRESHOLD

# --- GUARD 5 -------------------------------------------------------------
EXPECTED_MESSAGES = 1210

# TASK 2: the display resolution the isotonic fit actually supports.
DISPLAY_STEP = 0.01

# TASK 1: the two domain states. Never merged into one population.
VERIFIED, UNVERIFIED = 1, 0

# TASK 4: the cell layout is DECLARED, never inferred from array length.
# Bump the version whenever the field list or the required count changes.
CELL_SCHEMA = {
    "version": "vishwas.oper.cells/2",
    "fields": ["ix", "iy", "p_display", "verdict", "domain", "hull", "drivers"],
    "required": 6,
    "optional_tail": "drivers",
    "domain_values": {"0": "outside the verified domain (no IMD gauge, never "
                           "scoreable)", "1": "verified domain (IMD gauge)"},
    "hull_values": {"0": "inside the training distribution",
                    "1": "squared Mahalanobis distance above the TRAINING 99th "
                         "percentile -- unusual against what the model learned"},
    "hull_note": "domain and hull are INDEPENDENT and answer different "
                 "questions. domain=0 means UNVERIFIABLE: no gauge ever existed "
                 "there, so nothing can be scored. hull=1 means UNUSUAL: this "
                 "cell sits far from anything in training, and it happens "
                 "INSIDE the gauge grid too. A cell can be verified and "
                 "unusual, or unverifiable and perfectly ordinary.",
    "drivers": "top three SHAP drivers as [feature_index, shap_log_odds, "
               "percentile], present exactly when verdict >= 1 (not reliable). "
               "feature_index indexes meta.features. SHAP is computed on the "
               "RAW log-odds, never on the calibrated display value.",
    "note": "A cell carries the first 5 fields always, and all 6 when the "
            "optional tail is present. Read meta.schema; never branch on "
            "cell.length.",
}

# "ever observed" invites the question of whether nothing anywhere busted more
# often. The cap is the top isotonic block's rate on the validation slice, so
# it is the highest rate for any COMPARABLE GROUP, which is what this now says.
CAP_SENTENCE = (
    "Risk is capped at 75%: that is the highest rate observed for any "
    "comparable group of forecasts in held-out data, so the system does not "
    "display a confidence it has not earned.")

DOMAIN_SENTENCE = (
    "The model was trained only where IMD has rain gauges: 1,252 of 5,041 "
    "gridpoints. The remaining 3,789 are scored and shown, but no observation "
    "has ever existed there, so they are marked outside the verified domain "
    "and excluded from every headline count.")


def check_cycle_hour(hour):
    """GUARD 1. Refuse anything but 00Z."""
    if hour != CYCLE_HOUR:
        sys.exit(
            "REFUSING cycle hour {}Z. This model accepts {}Z only.\n"
            "  Every one of the 23 features is read at a VALID TIME derived "
            "from the cycle hour, so a {}Z cycle shifts the ENTIRE feature "
            "vector {} hours against the climatology and against the "
            "reforecast the model learned on -- 500 hPa heights, winds, "
            "shear, CAPE and precipitable water alike, not only the "
            "accumulation window. The reforecast is 00Z throughout, so there "
            "is no {}Z training data to compare against."
            .format(hour, CYCLE_HOUR, hour, int(hour), hour))


def check_cape_provenance(wanted):
    """GUARD 2. Every CAPE range must be surface CAPE, from the b family."""
    cape = [w for w in wanted if w[3] == "cape_sfc"]
    if not cape:
        sys.exit("no CAPE messages planned at all.")
    for path, _, _, _, _, _ in cape:
        if "pgrb2bp5" not in path:
            sys.exit("CAPE planned from {} -- surface CAPE lives in pgrb2bp5. "
                     "pgrb2ap5's CAPE is {}, a different quantity."
                     .format(path, CAPE_WRONG_LEVEL))
    expected = N_MEMBERS * len(PROBE.DAILY_STEPS)
    if len(cape) != expected:
        sys.exit("planned {} CAPE messages, expected {}".format(
            len(cape), expected))
    print("  guard 2  CAPE: {} messages, all pgrb2bp5, exact level '{}'"
          .format(len(cape), CAPE_LEVEL))


def check_members():
    """GUARD 3. Eleven, and the same eleven the reforecast carries."""
    ref = FETCH.MEMBERS_WEEKLY
    ours = [r for _, r in MEMBERS]
    if len(ours) != N_MEMBERS or ours != ref[:N_MEMBERS]:
        sys.exit("member set {} does not match MEMBERS_WEEKLY {}".format(
            ours, ref[:N_MEMBERS]))
    print("  guard 3  members: {} of 31 available -- {}".format(
        N_MEMBERS, ", ".join(ours)))
    print("           SUBSAMPLED because a 31-member spread is a sharper")
    print("           estimate than anything in training, and spread is the")
    print("           model's most important feature family.")


def check_message_count(wanted):
    """GUARD 5, first half. A partial cycle is caught before any transfer."""
    if len(wanted) != EXPECTED_MESSAGES:
        sys.exit(
            "planned {} messages, expected {}. A late or partial cycle is the "
            "usual cause. Refusing to transfer: a short ensemble would score "
            "without failing.".format(len(wanted), EXPECTED_MESSAGES))
    print("  guard 5  {} messages planned, matching EXPECTED_MESSAGES"
          .format(len(wanted)))


def explain(rows, model, features, labels_path):
    """TASK 3: the top three SHAP drivers, on the archive export's own rule.

    THE SELECTION RULE IS COPIED, NOT INVENTED. 15_dashboard_export.py explains
    every cell whose STORED VERDICT is not "reliable", and so does this. A
    second rule would mean the deck's "why this gridpoint" panel answers a
    different question on the live product than on the archive it was captured
    from -- and that panel is the image on slide 3.

    PERCENTILES ARE AGAINST THE 2019 TEST SET, the same reference the archive
    uses. Ranking a live value against the live cycle's own distribution would
    be refitting on operational data, which is the leak the stored climatology
    exists to avoid, and it would make "94th percentile" mean two different
    things in two files a single page reads.

    SHAP IS COMPUTED ON THE RAW LOG-ODDS. The calibrated display value is a
    monotone relabelling; attributions do not survive it, and summing them
    against it would not reconstruct anything.
    """
    uncertain = rows["verdict"].to_numpy() >= confidence.UNCERTAIN
    block = rows[uncertain]
    print()
    print("  SHAP: {:,} of {:,} cells are not reliable and get explained "
          "({:.1%})".format(len(block), len(rows), uncertain.mean()))
    if not len(block):
        return {}

    if not os.path.exists(labels_path):
        sys.exit("no labelled table at {} -- percentiles are ranked against "
                 "the 2019 test set and cannot be built without it. Refusing "
                 "to publish explanations on a live-only reference."
                 .format(labels_path))
    ref = pd.read_parquet(labels_path, columns=list(features) + ["split"])
    ref = ref[ref["split"] == "test"]
    print("  percentile reference: {:,} test rows (2019), NOT the live cycle"
          .format(len(ref)))
    lookups = {f: EXPORT.percentile_lookup(ref[f].to_numpy()) for f in features}

    # GUARD: the same additivity assertion the archive makes. If sum(SHAP) plus
    # the base value does not reconstruct the model's own log-odds, the
    # explanations describe some other function and must not ship.
    values = EXPORT.shap_for(model, features, block)

    order = np.argsort(-np.abs(values), axis=1)[:, :3]
    pct = np.empty_like(order)
    for slot in range(3):
        fi = order[:, slot]
        for j, feature in enumerate(features):
            hit = fi == j
            if hit.any():
                pct[hit, slot] = lookups[feature](block[feature].to_numpy()[hit])

    drivers = {}
    for row, idx in enumerate(block.index):
        drivers[idx] = [
            [int(order[row, s]),
             round(float(values[row, order[row, s]]), 4),
             int(pct[row, s])]
            for s in range(3)]
    return drivers


def main():
    ap = argparse.ArgumentParser(description="Score one live GEFS cycle.")
    ap.add_argument("--date", default=None, help="YYYYMMDD (00Z assumed)")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--cycle-hour", default=CYCLE_HOUR,
                    help="present only so a wrong value fails loudly")
    ap.add_argument("--model", default=os.path.join(_ROOT, "models", "vishwas_model.joblib"))
    ap.add_argument("--calibrator", default=os.path.join(_ROOT, "models", "isotonic_oper.joblib"))
    ap.add_argument("--climatology", default=os.path.join(_ROOT, "data", "climatology.parquet"))
    ap.add_argument("--out-dir", default=os.path.join(_ROOT, "data"))
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--labels", default=os.path.join(_ROOT, "data", "labelled.parquet"),
                    help="percentile reference for SHAP drivers (2019 test split)")
    ap.add_argument("--from-parquet", default=None,
                    help="rebuild the export from a stored cycle parquet, with "
                         "no fetch. Scores, verdicts and the domain flag are "
                         "read back exactly as written; nothing is re-scored.")
    args = ap.parse_args()

    check_cycle_hour(args.cycle_hour)

    if args.from_parquet:
        rows = pd.read_parquet(args.from_parquet)
        date = str(rows["init"].iloc[0])
        bundle = joblib.load(args.model)
        model, features = bundle["model"], bundle["features"]
        cal_bundle = joblib.load(args.calibrator)
        print("=" * 78)
        print("VISHWAS OPERATIONAL — REBUILD from {}".format(
            os.path.basename(args.from_parquet)))
        print("=" * 78)
        print("  cycle gefs.{}/{}Z, {:,} rows read back unchanged".format(
            date, CYCLE_HOUR, len(rows)))
        print("  NOT re-scored: model_score, verdict, p_calibrated, p_display")
        print("  and domain are the stored values. The five transfer-time")
        print("  guards do not apply to a rebuild and are not claimed.")
        for col in ("model_score", "verdict", "p_display", "domain"):
            if col not in rows.columns:
                sys.exit("stored parquet lacks {} -- not a scored cycle".format(col))
        # The stored verdict must still reproduce from the stored raw score,
        # or the parquet and confidence.py have drifted apart.
        want = confidence.verdicts_of(rows["model_score"].to_numpy())
        if not (want == rows["verdict"].to_numpy()).all():
            sys.exit("stored verdicts do not reproduce from stored raw scores.")
        print("  stored verdicts reproduce from stored raw scores.")
        planned = transfer = 0.0
        clock = time.time()
        write_export(rows, date, model, features, cal_bundle, args,
                     planned, transfer, clock)
        return

    fs = FETCH.connect()
    if args.latest or not args.date:
        stamp = datetime.datetime.utcnow()
        date = None
        for back in range(8):
            day = (stamp - datetime.timedelta(days=back)).strftime("%Y%m%d")
            probe = PROBE.family_path(day, CYCLE_HOUR, "b", MEMBERS[-1][0], 240) + ".idx"
            if fs.exists(probe):
                date = day
                break
        if date is None:
            sys.exit("no complete 00Z cycle in the last 8 days")
    else:
        date = args.date

    print("=" * 78)
    print("VISHWAS OPERATIONAL — gefs.{}/{}Z".format(date, CYCLE_HOUR))
    print("=" * 78)
    print("  guard 1  cycle hour {}Z accepted".format(CYCLE_HOUR))
    check_members()

    clock = time.time()
    wanted = PROBE.plan(fs, date, CYCLE_HOUR)
    check_message_count(wanted)
    check_cape_provenance(wanted)
    planned = time.time() - clock

    clock = time.time()
    # GUARD 5, second half: fetch_fields raises on any message whose envelope
    # is not GRIB...7777.
    fields, n_bytes = PROBE.fetch_fields(fs, wanted)
    transfer = time.time() - clock
    print("  fetched {:.1f} MB in {:.1f} s".format(n_bytes / 1e6, transfer))

    rows = PROBE.FEAT.build_rows(fields, date)
    rows = PROBE.apply_stored_climatology(rows, args.climatology)

    bundle = joblib.load(args.model)
    model, features = bundle["model"], bundle["features"]
    rows["model_score"] = model.predict_proba(rows[features])[:, 1]

    # GUARD 4: banded on the RAW score at the fixed threshold, and stored.
    rows["verdict"] = confidence.verdicts_of(rows["model_score"].to_numpy())

    cal_bundle = joblib.load(args.calibrator)
    iso = cal_bundle["isotonic"]
    rows["p_calibrated"] = iso.predict(rows["model_score"].to_numpy())
    rows["p_display"] = np.round(rows["p_calibrated"] / DISPLAY_STEP) * DISPLAY_STEP
    print("  calibrator loaded from {} (cap {:.6f}), NOT refitted".format(
        os.path.basename(args.calibrator), cal_bundle["cap"]))

    # TASK 1: mark the domain. Never merge the two populations.
    mask = imd_truth.land_mask()
    lat_slot = np.rint((rows["lat"].to_numpy() - imd_truth.ANALYSIS_LAT[0]) / 0.5).astype(int)
    lon_slot = np.rint((rows["lon"].to_numpy() - imd_truth.ANALYSIS_LON[0]) / 0.5).astype(int)
    rows["domain"] = np.where(mask[lat_slot, lon_slot], VERIFIED, UNVERIFIED)

    verified = rows[rows["domain"] == VERIFIED]
    print()
    print("  DOMAIN: {:,} verified rows ({:,} gridpoints), {:,} outside "
          "({:,} gridpoints)".format(
              len(verified), verified.groupby(["lat", "lon"]).ngroups,
              int((rows["domain"] == UNVERIFIED).sum()),
              rows[rows["domain"] == UNVERIFIED].groupby(["lat", "lon"]).ngroups))
    print()
    print("  HEADLINE COUNT IS THE VERIFIED DOMAIN ONLY:")
    print("    high risk {:,} of {:,} = {:.2f}%  (p >= {:.3f}, fixed)".format(
        int((verified["verdict"] == confidence.HIGH_RISK).sum()), len(verified),
        100 * (verified["verdict"] == confidence.HIGH_RISK).mean(), THRESHOLD))
    print("    full grid, for reference only: {:.2f}%".format(
        100 * (rows["verdict"] == confidence.HIGH_RISK).mean()))
    print()
    print("  NO TRUTH EXISTS for this cycle. Nothing above is an accuracy.")

    out_parquet = os.path.join(args.out_dir, "operational_{}.parquet".format(date))
    rows.to_parquet(out_parquet, index=False, compression="zstd")
    print("\n  wrote {}".format(out_parquet))

    write_export(rows, date, model, features, cal_bundle, args,
                 planned, transfer, clock)


def write_export(rows, date, model, features, cal_bundle, args,
                 planned, transfer, clock):
    """Assemble and write the operational JSON. Shared by a live run and a
    --from-parquet rebuild so both emit byte-identical structure."""
    # ---- JSON, in dashboard-data.json's shape, via 15's own writer -------
    ix = np.rint((rows["lon"].to_numpy() - EXPORT.LON0) / EXPORT.STEP).astype(int)
    iy = np.rint((rows["lat"].to_numpy() - EXPORT.LAT0) / EXPORT.STEP).astype(int)
    keep = (ix >= 0) & (ix < EXPORT.NX) & (iy >= 0) & (iy < EXPORT.NY)
    show = rows[keep].copy()
    show["ix"], show["iy"] = ix[keep], iy[keep]

    # TASK 3 (P41): the hull flag. Separates UNVERIFIABLE from UNUSUAL.
    #
    # WHY THE INDEX FEATURES ARE DROPPED HERE. The flag is a statement about
    # METEOROLOGY -- "this cell is far from anything the model learned" -- and
    # `month` and `lead_day` are indices, not weather. On a single cycle `month`
    # is CONSTANT, so including it adds the same offset to every cell's D^2 and
    # shifts the whole field against a fixed training threshold without saying
    # anything about any individual cell. Measured both ways in P41: the verdict
    # is unchanged, so this is the more defensible of two answers, not a rescue.
    ref = MAHAL.fit_reference(args.labels, args.model, MAHAL.INDEX_FEATURES)
    d2 = MAHAL.distances(show, ref)
    show["hull"] = (d2 > ref["p99"]).astype(int)
    print()
    print("  HULL: D^2 over {} features (dropped {}), reference = the {:,} fitted "
          "training rows".format(len(ref["features"]), ", ".join(ref["dropped"]),
                                 ref["n_fitted"]))
    print("    training 99th percentile D^2 = {:.2f}  (empirical, never chi-squared)"
          .format(ref["p99"]))
    for dom, label in ((VERIFIED, "verified  "), (UNVERIFIED, "unverified")):
        sub = show[show["domain"] == dom]
        if not len(sub):
            continue
        alerts = sub[sub["verdict"] == confidence.HIGH_RISK]
        print("    {} {:,} cells, {:.2f}% outside the hull; of its {:,} alerts, "
              "{:.2f}% outside".format(
                  label, len(sub), 100 * sub["hull"].mean(), len(alerts),
                  100 * alerts["hull"].mean() if len(alerts) else float("nan")))
    print("    domain and hull are INDEPENDENT: unverifiable is not unusual, and")
    print("    an alert inside the gauge grid can still be far from training.")

    # TASK 3 (P40): SHAP, on the archive's own selection rule and its own code path.
    drivers = explain(show, model, features, args.labels)

    leads = {}
    for lead, part in show.groupby("lead_day"):
        cells = []
        for idx, r in part.iterrows():
            cell = [int(r["ix"]), int(r["iy"]), round(float(r["p_display"]), 2),
                    int(r["verdict"]), int(r["domain"]), int(r["hull"])]
            if idx in drivers:
                cell.append(drivers[idx])
            cells.append(cell)
        leads[str(int(lead))] = cells

    stamp = datetime.datetime.strptime(date, "%Y%m%d")
    payload = {
        "meta": {
            "grid": {"lon0": EXPORT.LON0, "lat0": EXPORT.LAT0,
                     "step": EXPORT.STEP, "nx": EXPORT.NX, "ny": EXPORT.NY},
            "n_points": int(show[["lat", "lon"]].drop_duplicates().shape[0]),
            "threshold": THRESHOLD,
            "uncertain_floor": confidence.UNCERTAIN_FLOOR,
            "cycle": "{}{}".format(date, CYCLE_HOUR),
            "display": {
                "value": "isotonic-calibrated probability",
                "step": DISPLAY_STEP,
                "cap": float(cal_bundle["cap"]),
                "cap_note": CAP_SENTENCE,
                "note": "The displayed number is rounded to the resolution the "
                        "calibration supports. The VERDICT is banded on the raw "
                        "score and stored; never re-derive a class from the "
                        "displayed value.",
            },
            "domain": {
                "verified": int((rows["domain"] == VERIFIED).sum()),
                "unverified": int((rows["domain"] == UNVERIFIED).sum()),
                "note": DOMAIN_SENTENCE,
            },
            "hull": {
                "features": list(ref["features"]),
                "dropped": list(ref["dropped"]),
                "train_p99": round(float(ref["p99"]), 4),
                "outside": int(show["hull"].sum()),
                "note": "Squared Mahalanobis distance against the 488,280 rows "
                        "the model was fitted on, thresholded at their own 99th "
                        "percentile. It marks cells that are UNUSUAL, which is a "
                        "different question from the domain marker's "
                        "UNVERIFIABLE, and it fires inside the gauge grid too.",
            },
            "schema": CELL_SCHEMA,
            "cell_format": CELL_SCHEMA["fields"],
            "features": list(features),
            "labels": {f: EXPORT.LABELS[f] for f in features},
            "truth": None,
            "truth_note": "No truth exists for a live cycle. Nothing here is "
                          "an accuracy claim.",
            "provenance": "Operational GEFS {}{}Z, 11 of 31 members, 0.5 deg "
                          "pgrb2ap5/pgrb2bp5. Model and calibrator both fitted "
                          "on the 2000-2019 reforecast and unchanged here."
                          .format(date, CYCLE_HOUR),
        },
        "dates": [{"init": date,
                   "label": stamp.strftime("%-d %B %Y"),
                   "season": PROBE.FEAT.__dict__.get("_season", None) or
                             ("JJAS" if stamp.month in (6, 7, 8, 9) else
                              "DJF" if stamp.month in (12, 1, 2) else
                              "MAM" if stamp.month in (3, 4, 5) else "ON"),
                   "leads": leads}],
    }

    out_json = args.out_json or os.path.join(
        args.out_dir, "operational_{}.json".format(date))
    size = EXPORT.write_payload(out_json, payload)
    print("  wrote {}  ({:,} bytes)".format(out_json, size))

    # ---- the explain rule, checked in BOTH directions -------------------
    # Same assertion the archive makes: a cell carries drivers exactly when its
    # STORED verdict is not "reliable". Keyed off the stored verdict, never off
    # the displayed number.
    cells = [c for d in payload["dates"] for cs in d["leads"].values() for c in cs]
    full = len(CELL_SCHEMA["fields"])
    broken = [c for c in cells
              if (len(c) == full) != (c[3] >= confidence.UNCERTAIN)]
    with_shap = sum(1 for c in cells if len(c) == full)
    print("  cells with a SHAP array: {:,} of {:,}".format(with_shap, len(cells)))
    print("  explain-rule violations (not-reliable without SHAP, or reliable "
          "with): {}".format(len(broken)))
    if broken:
        sys.exit("EXPLAIN RULE VIOLATED — not shipping this to an interface.")

    # Every driver triple must index a real feature and carry a real percentile.
    for c in cells:
        if len(c) != full:
            continue
        for fi, _, pc in c[-1]:
            if not 0 <= fi < len(features) or not 0 <= pc <= 100:
                sys.exit("driver triple out of range: {}".format(c[-1]))
    print("  every driver indexes meta.features and carries a 0-100 percentile.")

    print("\n  TIMING plan {:.1f} s, transfer {:.1f} s, total {:.1f} s".format(
        planned, transfer, time.time() - clock + planned))


if __name__ == "__main__":
    main()
