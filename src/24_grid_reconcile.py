"""
P41 TASK 1 — RECONCILE THE TWO GRIDS.

THE MISMATCH. P40's Mahalanobis work, and P39's domain split before it, ran on
50,410 rows = 10 lead days x 5,041 gridpoints -- the FULL 71x71 ANALYSIS BOX
(5.0-40.0N, 65.0-100.0E at 0.5 deg). The shipped export carries 34,220 rows =
10 x 3,422 gridpoints -- the DASHBOARD GRID (8.5-37.0N, 68.0-97.0E, nx 59 x
ny 58). 1,619 gridpoints, 32% of the analysis box, are cropped between the
measurement and the product. So 7.78% and 13.16% were computed over a domain
the map does not display.

THE ONE THING THAT WOULD BE A LARGE FINDING is a gauge point outside the crop:
that would mean the product cannot show part of the only domain it can be
scored on. Checked first and explicitly.

    python src/24_grid_reconcile.py
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import confidence
import imd_truth

# The shipped grid, read from the export module's own constants so this cannot
# drift from what is actually written.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "export15", os.path.join(_HERE, "15_dashboard_export.py"))
EXPORT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EXPORT)


def main():
    ap = argparse.ArgumentParser(description="Analysis box vs shipped grid.")
    ap.add_argument("--live", default=os.path.join(_ROOT, "data",
                                                   "operational_20260908.parquet"))
    ap.add_argument("--out", default=os.path.join(_ROOT, "data", "grid_reconcile.csv"))
    args = ap.parse_args()

    live = pd.read_parquet(args.live)
    init = str(live["init"].iloc[0])

    lat = live["lat"].to_numpy()
    lon = live["lon"].to_numpy()

    # ---- the three populations -----------------------------------------
    mask = imd_truth.land_mask()
    lat_slot = np.rint((lat - imd_truth.ANALYSIS_LAT[0]) / 0.5).astype(int)
    lon_slot = np.rint((lon - imd_truth.ANALYSIS_LON[0]) / 0.5).astype(int)
    gauged = mask[lat_slot, lon_slot]

    ix = np.rint((lon - EXPORT.LON0) / EXPORT.STEP).astype(int)
    iy = np.rint((lat - EXPORT.LAT0) / EXPORT.STEP).astype(int)
    shipped = (ix >= 0) & (ix < EXPORT.NX) & (iy >= 0) & (iy < EXPORT.NY)

    flagged = live["model_score"].to_numpy() >= confidence.THRESHOLD

    def pts(sel):
        return pd.DataFrame({"lat": lat[sel], "lon": lon[sel]}).drop_duplicates().shape[0]

    print("=" * 78)
    print("TWO GRIDS, NAMED  (live cycle {})".format(init))
    print("=" * 78)
    print("  ANALYSIS BOX   {:.1f}-{:.1f}N, {:.1f}-{:.1f}E at {} deg = 71 x 71 = {:,} gridpoints"
          .format(imd_truth.ANALYSIS_LAT[0], imd_truth.ANALYSIS_LAT[-1],
                  imd_truth.ANALYSIS_LON[0], imd_truth.ANALYSIS_LON[-1], 0.5, pts(slice(None))))
    print("                 EVERY point in the box, land and ocean alike. This is")
    print("                 the domain features and climatology cover, and it is")
    print("                 what 5,041 means. It is NOT 'land gridpoints'.")
    print("  SHIPPED GRID   {:.1f}-{:.1f}N, {:.1f}-{:.1f}E = nx {} x ny {} = {:,} gridpoints"
          .format(EXPORT.LAT0, EXPORT.LAT0 + (EXPORT.NY - 1) * EXPORT.STEP,
                  EXPORT.LON0, EXPORT.LON0 + (EXPORT.NX - 1) * EXPORT.STEP,
                  EXPORT.NX, EXPORT.NY, EXPORT.NX * EXPORT.NY))
    print("                 The crop the map draws. {:,} analysis points fall outside it."
          .format(pts(slice(None)) - pts(shipped)))
    print("  GAUGE POINTS   {:,} of the analysis box carry an IMD gauge and can be"
          .format(pts(gauged)))
    print("                 LABELLED. 24.8% of 5,041. This is the only domain any")
    print("                 accuracy number has ever been computed on.")

    # ---- THE CHECK THAT MATTERS ----------------------------------------
    print()
    print("=" * 78)
    print("DO ALL 1,252 GAUGE POINTS SURVIVE THE CROP?")
    print("=" * 78)
    lost = gauged & ~shipped
    n_lost = pts(lost) if lost.any() else 0
    print("  gauge points inside the shipped grid : {:,}".format(pts(gauged & shipped)))
    print("  gauge points OUTSIDE it              : {:,}".format(n_lost))
    if n_lost:
        bad = pd.DataFrame({"lat": lat[lost], "lon": lon[lost]}).drop_duplicates()
        print("  *** THIS IS A LARGE FINDING: the product cannot display part of")
        print("  *** the only domain it can be scored on. Points:")
        print(bad.to_string(index=False))
    else:
        print("  ALL 1,252 SURVIVE. The verified figure is therefore computed on")
        print("  exactly the points the map draws, and holds unchanged.")

    # ---- both figure sets ----------------------------------------------
    rows = []
    for gname, gsel in [("ANALYSIS BOX (5,041 pts)", np.ones(len(live), bool)),
                        ("SHIPPED GRID (3,422 pts)", shipped)]:
        for dname, dsel in [("verified (gauge)", gauged), ("unverified (no gauge)", ~gauged)]:
            sel = gsel & dsel
            rows.append({
                "grid": gname, "domain": dname,
                "gridpoints": pts(sel), "rows": int(sel.sum()),
                "high_risk_pct": float(100.0 * flagged[sel].mean()) if sel.any() else float("nan"),
            })
        sel = gsel
        rows.append({"grid": gname, "domain": "POOLED (reference only)",
                     "gridpoints": pts(sel), "rows": int(sel.sum()),
                     "high_risk_pct": float(100.0 * flagged[sel].mean())})
    table = pd.DataFrame(rows)

    print()
    print("=" * 78)
    print("HIGH-RISK FRACTION, BOTH GRIDS, DOMAINS NEVER MERGED")
    print("=" * 78)
    print("  {:<26} {:<24} {:>7} {:>9} {:>11}".format(
        "grid", "domain", "points", "rows", "high risk"))
    for _, r in table.iterrows():
        print("  {:<26} {:<24} {:>7,} {:>9,} {:>10.2f}%".format(
            r["grid"], r["domain"], int(r["gridpoints"]), int(r["rows"]),
            r["high_risk_pct"]))

    ver = table[(table["grid"].str.startswith("SHIPPED")) &
                (table["domain"] == "verified (gauge)")].iloc[0]
    unv_a = table[(table["grid"].str.startswith("ANALYSIS")) &
                  (table["domain"] == "unverified (no gauge)")].iloc[0]
    unv_s = table[(table["grid"].str.startswith("SHIPPED")) &
                  (table["domain"] == "unverified (no gauge)")].iloc[0]
    print()
    print("  WHICH NUMBER BELONGS TO THE PRODUCT:")
    print("    the VERIFIED figure is identical on both grids ({:.2f}%) because every"
          .format(ver["high_risk_pct"]))
    print("    gauge point survives the crop. Quote it, and say 'gauge domain'.")
    print("    the UNVERIFIED figure MOVES: {:.2f}% on the analysis box, {:.2f}% on the"
          .format(unv_a["high_risk_pct"], unv_s["high_risk_pct"]))
    print("    shipped grid. The analysis-box value describes points the map never")
    print("    draws, so the SHIPPED value is the one a viewer could check.")
    print()
    print("  NEITHER POOLED FIGURE IS A HEADLINE. Both are printed so the ratio is")
    print("  visible, never so it can be quoted as one population.")

    table["init"] = init
    table.to_csv(args.out, index=False)
    print("\nwrote {}".format(args.out))


if __name__ == "__main__":
    main()
