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

CAP_SENTENCE = (
    "Risk is capped at 75%: that is the highest bust rate ever observed in "
    "held-out data, so the system does not display a confidence it has not "
    "earned.")

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
    args = ap.parse_args()

    check_cycle_hour(args.cycle_hour)

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

    # ---- JSON, in dashboard-data.json's shape, via 15's own writer -------
    ix = np.rint((rows["lon"].to_numpy() - EXPORT.LON0) / EXPORT.STEP).astype(int)
    iy = np.rint((rows["lat"].to_numpy() - EXPORT.LAT0) / EXPORT.STEP).astype(int)
    keep = (ix >= 0) & (ix < EXPORT.NX) & (iy >= 0) & (iy < EXPORT.NY)
    show = rows[keep].copy()
    show["ix"], show["iy"] = ix[keep], iy[keep]

    leads = {}
    for lead, part in show.groupby("lead_day"):
        leads[str(int(lead))] = [
            [int(r["ix"]), int(r["iy"]), round(float(r["p_display"]), 2),
             int(r["verdict"]), int(r["domain"])]
            for _, r in part.iterrows()]

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
            "cell_format": ["ix", "iy", "p_display", "verdict", "domain"],
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
    print("\n  TIMING plan {:.1f} s, transfer {:.1f} s, total {:.1f} s".format(
        planned, transfer, time.time() - clock + planned))


if __name__ == "__main__":
    main()
