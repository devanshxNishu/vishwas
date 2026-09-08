"""
P39 TASK 1 — is the model in a regime it has SEEN, outside the gauge grid?

THE QUESTION. Labels and bust thresholds need IMD gauge truth, so the model
learned only at the 1,252 gauge-observed gridpoints. Features and climatology
cover all 5,041. A live cycle therefore scores 3,789 points the model was never
trained anywhere near -- the Thar desert, the high Himalaya, the ocean margins.

WHY P37's NUMBER CANNOT ANSWER IT. That check pooled all 50,410 rows, so its
0.12% worst case averages 75% of the domain against the 25% that carries the
training footprint. A badly out-of-regime minority hides inside a pooled mean
by construction. This splits the two subsets and reports them side by side.

THE DECISION THIS FEEDS, fixed before the numbers are seen:
  materially out-of-distribution  -> restrict the live product to the 1,252
  not                            -> score all 5,041, but mark the 3,789 as a
                                    DISTINCT STATE and keep them out of every
                                    headline count
Either way 5,041 is never counted as one population. Slide 4 promises the
gauge domain is stated, and an unmarked full-grid count breaks that promise.

    python src/22_domain_check.py
"""

import argparse
import importlib.util
import os
import sys

import joblib
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import imd_truth


def main():
    ap = argparse.ArgumentParser(description="Gauge vs ungauged domain check.")
    ap.add_argument("--live", default=os.path.join(_ROOT, "data", "features_oper.parquet"))
    ap.add_argument("--labels", default=os.path.join(_ROOT, "data", "labelled.parquet"))
    ap.add_argument("--model", default=os.path.join(_ROOT, "models", "vishwas_model.joblib"))
    ap.add_argument("--out", default=os.path.join(_ROOT, "data", "domain_check.csv"))
    args = ap.parse_args()

    features = joblib.load(args.model)["features"]
    live = pd.read_parquet(args.live)

    # The gauge footprint, from the same mask 06_label.py labels with.
    mask = imd_truth.land_mask()
    lat_slot = np.rint((live["lat"].to_numpy() - imd_truth.ANALYSIS_LAT[0]) / 0.5).astype(int)
    lon_slot = np.rint((live["lon"].to_numpy() - imd_truth.ANALYSIS_LON[0]) / 0.5).astype(int)
    gauged = mask[lat_slot, lon_slot]

    n_pts = live.groupby(["lat", "lon"]).ngroups
    n_gauged_pts = live.loc[gauged].groupby(["lat", "lon"]).ngroups
    print("live rows {:,} over {:,} gridpoints".format(len(live), n_pts))
    print("  gauge-observed  {:,} points -> {:,} rows".format(
        n_gauged_pts, int(gauged.sum())))
    print("  unobserved      {:,} points -> {:,} rows".format(
        n_pts - n_gauged_pts, int((~gauged).sum())))

    train = pd.read_parquet(args.labels)
    train = train[train["split"] == "train"]
    print("training rows {:,} over {} dates".format(len(train), train["init"].nunique()))
    print()

    rows = []
    for name in features:
        t = train[name].to_numpy()
        lo, hi = np.nanmin(t), np.nanmax(t)
        g = live.loc[gauged, name].to_numpy()
        u = live.loc[~gauged, name].to_numpy()
        rows.append({
            "feature": name,
            "train_min": lo, "train_max": hi,
            "gauged_out_pct": float(np.mean((g < lo) | (g > hi)) * 100.0),
            "ungauged_out_pct": float(np.mean((u < lo) | (u > hi)) * 100.0),
            "ungauged_min": float(np.nanmin(u)), "ungauged_max": float(np.nanmax(u)),
        })
    table = pd.DataFrame(rows)
    table["ratio"] = table["ungauged_out_pct"] / table["gauged_out_pct"].replace(0, np.nan)

    print("=" * 78)
    print("OUT-OF-TRAINING-RANGE, BY SUBSET  (the pooled P37 number hid this)")
    print("=" * 78)
    print("  {:<22} {:>14} {:>16} {:>10}".format(
        "feature", "gauged 1,252", "ungauged 3,789", "ratio"))
    for _, r in table.iterrows():
        ratio = "" if np.isnan(r["ratio"]) else "{:>10.1f}x".format(r["ratio"])
        flag = "  <--" if r["ungauged_out_pct"] > 1.0 else ""
        print("  {:<22} {:>13.3f}% {:>15.3f}% {}{}".format(
            r["feature"], r["gauged_out_pct"], r["ungauged_out_pct"], ratio, flag))

    worst_g = table["gauged_out_pct"].max()
    worst_u = table["ungauged_out_pct"].max()
    bad = table[table["ungauged_out_pct"] > 1.0]
    print()
    print("  worst feature, gauged subset   : {:.3f}%".format(worst_g))
    print("  worst feature, ungauged subset : {:.3f}%".format(worst_u))
    print("  features over 1% on the ungauged subset: {}".format(len(bad)))
    for _, r in bad.iterrows():
        print("    {:<22} {:.2f}%  train [{:.2f}, {:.2f}]  ungauged [{:.2f}, {:.2f}]"
              .format(r["feature"], r["ungauged_out_pct"], r["train_min"],
                      r["train_max"], r["ungauged_min"], r["ungauged_max"]))

    print()
    print("=" * 78)
    print("DECISION")
    print("=" * 78)
    if worst_u > 5.0:
        print("  RESTRICT to the 1,252. The ungauged subset is materially")
        print("  out-of-distribution: {:.2f}% of values on its worst feature sit".format(worst_u))
        print("  outside anything the model was trained on.")
        decision = "restrict"
    else:
        print("  SCORE ALL 5,041, MARK THE 3,789. The ungauged subset is not")
        print("  materially out-of-distribution -- worst feature {:.3f}%, against".format(worst_u))
        print("  {:.3f}% on the gauge grid itself. But it is still unverifiable:".format(worst_g))
        print("  no IMD gauge means no label ever existed there, so nothing about")
        print("  those points has been or can be scored. They get a DISTINCT")
        print("  STATE, 'outside the verified domain', and are excluded from")
        print("  every headline count.")
        decision = "mark"
    print()
    print("  IN-RANGE IS NOT VERIFIED. This check says the live features sit")
    print("  inside the training hull; it says NOTHING about whether the model")
    print("  is accurate there, because no truth has ever existed at those")
    print("  points. Do not let 'in distribution' be read as 'validated'.")

    table.to_csv(args.out, index=False)
    print("\nwrote {}".format(args.out))
    return decision


if __name__ == "__main__":
    main()
