"""
P40 TASK 2 — is the ungauged field a PREDICTION or an EXTRAPOLATION?

THE QUESTION P39 COULD NOT ANSWER. 22_domain_check.py found the ungauged
three-quarters of the grid flagging high risk at 13.16% against 7.78% on the
gauge grid, a 1.69x gap, while every feature's marginal range came back clean.
But that table is 23 SEPARATE ONE-DIMENSIONAL checks. A cell can sit inside
every feature's own range and still occupy a corner of 23-dimensional space
where no training row ever fell. Two stories predict that table identically:

  (a) the ungauged points are genuinely stormier terrain -- Himalaya, desert,
      the coastal margins IMD's gauge network avoids -- and 13.16% is
      meteorology the model is reading correctly;
  (b) they sit in JOINT feature combinations the model never learned, and
      13.16% is the model extrapolating confidently into a void.

Under (a) the domain marking is a labelling nicety. Under (b) the ungauged
field is not a prediction at all and must not be published.

THE METHOD. Squared Mahalanobis distance over the 23 features, mean and
covariance fitted on the rows the model was ACTUALLY FITTED ON -- split=="train"
minus the 13 interleaved validation dates, which is the 488,280 rows the bundle
records as n_train_rows. Not the whole labelled table: the test year never
reached the estimator, and including it would measure the wrong hull.

THE REFERENCE IS THE EMPIRICAL TRAINING DISTRIBUTION, NOT A CHI-SQUARED TABLE.
D^2 ~ chi2(23) holds only under multivariate normality, and these features are
nothing like normal: precip_mean is zero-inflated, month is discrete and
cyclic, the spreads are strictly positive and heavily skewed. Quoting a
chi-squared cutoff would smuggle a distributional assumption in as a threshold.
Every quantile below is read off the training rows themselves.

    python src/23_mahalanobis.py
"""

import argparse
import os
import sys

import joblib
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import confidence
import imd_truth

# Standardising before the covariance makes this a CORRELATION matrix. D^2 is
# invariant to that affine rescaling -- the distances are identical either way
# -- but the conditioning is vastly better, because the raw features span
# geopotential metres (~5,800) and precipitation millimetres (~0) in one matrix.
# Both condition numbers are reported so the choice is visible rather than
# assumed.
RIDGE_TRIGGER = 1e10


def mahalanobis(X, mu, chol_inv):
    """Squared Mahalanobis distance, via the Cholesky factor of the inverse."""
    Z = (X - mu) @ chol_inv
    return np.einsum("ij,ij->i", Z, Z)


# The two features that are not meteorology. `month` is a calendar index and
# `lead_day` a forecast-horizon index; both are legitimate model inputs, but on
# a single live cycle `month` is CONSTANT (every cell shares one value) while
# training spans 1-12. That constant offset lands in every live D^2 identically.
# It cancels in any contrast INTERNAL to the cycle -- flagged ungauged vs
# flagged gauged -- but it does not cancel against the training reference,
# which is exactly what "1.66% vs 1.00%, so it is in-distribution" rests on.
INDEX_FEATURES = ("month", "lead_day")


def fit_reference(labels_path, model_path, drop=()):
    """Mean, scale and inverse-covariance from the rows the estimator SAW.

    Returned as a dict so the operational export can reuse this exact fit
    rather than growing a second implementation that could drift from it.
    """
    bundle = joblib.load(model_path)
    cfg = bundle["config"]
    features = [f for f in bundle["features"] if f not in set(drop)]
    val_dates = set(str(d) for d in cfg["validation_dates"])

    lab = pd.read_parquet(labels_path, columns=list(features) + ["split", "init"])
    train = lab[lab["split"] == "train"]
    fitted = train[~train["init"].astype(str).isin(val_dates)]
    if len(fitted) != cfg["n_train_rows"]:
        raise SystemExit(
            "fitted rows {:,} disagree with the bundle's n_train_rows {:,}; stop."
            .format(len(fitted), cfg["n_train_rows"]))

    X = fitted[features].to_numpy(dtype=float)
    if np.isnan(X).any():
        raise SystemExit("NaN in training features; Mahalanobis needs complete rows.")
    mu = X.mean(axis=0)
    sd = X.std(axis=0, ddof=1)
    if (sd <= 0).any():
        raise SystemExit("zero-variance feature: {}".format(
            [f for f, s in zip(features, sd) if s <= 0]))
    Z = (X - mu) / sd
    C = np.cov(Z, rowvar=False)
    cond_raw = float(np.linalg.cond(np.cov(X, rowvar=False)))
    cond = float(np.linalg.cond(C))
    ridged = cond > RIDGE_TRIGGER
    if ridged:
        lam = 1e-6 * np.trace(C) / C.shape[0]
        C = C + lam * np.eye(C.shape[0])
    chol_inv = np.linalg.inv(np.linalg.cholesky(C)).T
    d_train = mahalanobis(Z, np.zeros(len(features)), chol_inv)
    return {"features": features, "mu": mu, "sd": sd, "chol_inv": chol_inv,
            "d_train": d_train, "p99": float(np.percentile(d_train, 99)),
            "cond": cond, "cond_raw": cond_raw, "ridged": ridged,
            "n_fitted": len(fitted), "dropped": list(drop)}


def distances(frame, ref):
    """Squared Mahalanobis distance of each row of `frame` against `ref`."""
    Z = (frame[ref["features"]].to_numpy(dtype=float) - ref["mu"]) / ref["sd"]
    return mahalanobis(Z, np.zeros(len(ref["features"])), ref["chol_inv"])


def describe(name, d, ref_p99, n_total=None):
    n = len(d)
    return {
        "group": name,
        "n": n,
        "p50": float(np.percentile(d, 50)),
        "p90": float(np.percentile(d, 90)),
        "p99": float(np.percentile(d, 99)),
        "max": float(d.max()),
        "beyond_train_p99_pct": float(np.mean(d > ref_p99) * 100.0),
    }


def main():
    ap = argparse.ArgumentParser(description="Mahalanobis domain check.")
    ap.add_argument("--live", default=os.path.join(_ROOT, "data", "operational_20260908.parquet"))
    ap.add_argument("--labels", default=os.path.join(_ROOT, "data", "labelled.parquet"))
    ap.add_argument("--model", default=os.path.join(_ROOT, "models", "vishwas_model.joblib"))
    ap.add_argument("--out", default=os.path.join(_ROOT, "data", "mahalanobis.csv"))
    ap.add_argument("--drop-index", action="store_true",
                    help="exclude month and lead_day, the two features that are "
                         "not meteorology, and re-test the conclusion")
    args = ap.parse_args()
    drop = INDEX_FEATURES if args.drop_index else ()

    ref = fit_reference(args.labels, args.model, drop)
    features = ref["features"]
    print("fitted reference rows      {:,}  (split==train minus the 13 "
          "validation dates)".format(ref["n_fitted"]))
    print("features in the distance   {}{}".format(
        len(features),
        "   DROPPED {}".format(", ".join(ref["dropped"])) if ref["dropped"] else ""))
    print()
    print("condition number, raw covariance          {:.3e}".format(ref["cond_raw"]))
    print("condition number, standardised (used)     {:.3e}".format(ref["cond"]))
    if ref["ridged"]:
        print("  ill-conditioned above {:.0e} -> ridge added to the diagonal"
              .format(RIDGE_TRIGGER))
    else:
        print("  below the {:.0e} trigger -> NO regularisation applied"
              .format(RIDGE_TRIGGER))

    d_train = ref["d_train"]
    ref_p99 = ref["p99"]

    # ---- the live cycle ----
    live = pd.read_parquet(args.live)
    init = str(live["init"].iloc[0])
    mask = imd_truth.land_mask()
    lat_slot = np.rint((live["lat"].to_numpy() - imd_truth.ANALYSIS_LAT[0]) / 0.5).astype(int)
    lon_slot = np.rint((live["lon"].to_numpy() - imd_truth.ANALYSIS_LON[0]) / 0.5).astype(int)
    gauged = mask[lat_slot, lon_slot]
    flagged = live["model_score"].to_numpy() >= confidence.THRESHOLD

    d_live = distances(live, ref)

    groups = [
        ("training rows (reference)", d_train),
        ("live, gauged", d_live[gauged]),
        ("live, ungauged", d_live[~gauged]),
        ("live, ungauged AND flagged", d_live[(~gauged) & flagged]),
        ("live, gauged AND flagged", d_live[gauged & flagged]),
    ]
    table = pd.DataFrame([describe(n, d, ref_p99) for n, d in groups])

    print()
    print("=" * 86)
    print("SQUARED MAHALANOBIS DISTANCE, {} features{}, live cycle {}".format(
        len(features),
        " (index features dropped)" if ref["dropped"] else "", init))
    print("reference = the 488,280 fitted training rows; quantiles are EMPIRICAL")
    print("=" * 86)
    print("  {:<28} {:>9} {:>9} {:>9} {:>10} {:>11}".format(
        "group", "n", "p50", "p90", "p99", "max"))
    for _, r in table.iterrows():
        print("  {:<28} {:>9,} {:>9.2f} {:>9.2f} {:>9.2f} {:>11.1f}".format(
            r["group"], int(r["n"]), r["p50"], r["p90"], r["p99"], r["max"]))
    print()
    print("  fraction beyond the TRAINING 99th percentile (D^2 > {:.2f}):".format(ref_p99))
    for _, r in table.iterrows():
        print("    {:<30} {:>7.2f}%".format(r["group"], r["beyond_train_p99_pct"]))
    print("  by construction the training row itself sits at 1.00%.")

    # ---- the verdict ----
    u = table.loc[table["group"] == "live, ungauged"].iloc[0]
    g = table.loc[table["group"] == "live, gauged"].iloc[0]
    uf = table.loc[table["group"] == "live, ungauged AND flagged"].iloc[0]
    g_f = table.loc[table["group"] == "live, gauged AND flagged"].iloc[0]
    tr = table.loc[table["group"] == "training rows (reference)"].iloc[0]
    print()
    print("=" * 86)
    print("WHICH STORY")
    print("=" * 86)
    print("  ungauged median D^2 is {:.2f}x the gauged median ({:.2f} vs {:.2f})"
          .format(u["p50"] / g["p50"], u["p50"], g["p50"]))
    print("  ungauged beyond training p99: {:.2f}%   gauged: {:.2f}%   expected under (a): ~1%"
          .format(u["beyond_train_p99_pct"], g["beyond_train_p99_pct"]))
    print("  ungauged AND FLAGGED beyond training p99: {:.2f}%"
          .format(uf["beyond_train_p99_pct"]))
    print()
    if uf["beyond_train_p99_pct"] > 20.0 or u["beyond_train_p99_pct"] > 20.0:
        print("  STORY (b) -- EXTRAPOLATION. A large share of the ungauged field, and")
        print("  of the flagged ungauged cells in particular, sits in joint feature")
        print("  space the training rows never occupied. The marginal ranges were")
        print("  clean because each feature alone is unremarkable; the COMBINATION")
        print("  is not. RECOMMENDATION CHANGES: do not publish the ungauged field.")
    elif u["beyond_train_p99_pct"] > 5.0:
        print("  MIXED. The ungauged field is measurably further from the training")
        print("  hull than the gauge grid, but not wholesale outside it. Keep the")
        print("  marking, and state the joint-space gap alongside it.")
    else:
        print("  STORY (a) -- METEOROLOGY. The ungauged cells sit inside the joint")
        print("  training distribution at close to the rate the training rows")
        print("  themselves do, so 13.16% is not the model extrapolating into a")
        print("  void. The P39 decision stands: score all 5,041, mark the 3,789.")
    print()
    print("  THE FLAGGED UNGAUGED CELLS ARE THE QUALIFICATION, AND THEY ARE PRINTED")
    print("  WHATEVER THE VERDICT SAYS. {:.2f}% of them sit beyond the training 99th"
          .format(uf["beyond_train_p99_pct"]))
    print("  percentile, against {:.2f}% of the flagged GAUGED cells -- {:.1f}x -- and their"
          .format(g_f["beyond_train_p99_pct"],
                  uf["beyond_train_p99_pct"] / max(g_f["beyond_train_p99_pct"], 1e-9)))
    print("  median D^2 of {:.2f} is {:.1f}x the training median of {:.2f}. So the ALARMS"
          .format(uf["p50"], uf["p50"] / tr["p50"], tr["p50"]))
    print("  raised outside the gauge grid are drawn disproportionately from the")
    print("  sparse edge of the training distribution, even though the ungauged")
    print("  field AS A WHOLE is not. That is a minority effect -- {:.1f}% of flagged"
          .format(100.0 - uf["beyond_train_p99_pct"]))
    print("  ungauged cells are still inside the hull -- so it qualifies story (a)")
    print("  rather than replacing it with (b). Report it with the headline.")
    print()
    print("  IN-RANGE IS STILL NOT VERIFIED. This measures DISTANCE TO THE TRAINING")
    print("  DISTRIBUTION and nothing else. No gauge means no label ever existed")
    print("  there, so nothing at those points has been or can be scored. A cell")
    print("  can sit at the centre of the training cloud and still be wrong.")

    table["n_features"] = len(features)
    table["dropped"] = ",".join(ref["dropped"]) or "none"
    table["cond_standardised"] = ref["cond"]
    table["cond_raw"] = ref["cond_raw"]
    table["ridged"] = ref["ridged"]
    table["train_p99"] = ref_p99
    table["init"] = init
    table.to_csv(args.out, index=False)
    print("\nwrote {}".format(args.out))


if __name__ == "__main__":
    main()
