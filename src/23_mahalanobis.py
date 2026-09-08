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
    args = ap.parse_args()

    bundle = joblib.load(args.model)
    features = bundle["features"]
    cfg = bundle["config"]
    val_dates = set(str(d) for d in cfg["validation_dates"])

    # ---- the reference: the rows the estimator actually saw ----
    lab = pd.read_parquet(args.labels, columns=features + ["split", "init"])
    train = lab[lab["split"] == "train"]
    fitted = train[~train["init"].astype(str).isin(val_dates)]
    print("labelled table            {:,} rows".format(len(lab)))
    print("  split == train          {:,} rows over {} dates".format(
        len(train), train["init"].nunique()))
    print("  minus 13 validation     {:,} rows over {} dates  <- the fitted set".format(
        len(fitted), fitted["init"].nunique()))
    print("  bundle n_train_rows     {:,}{}".format(
        cfg["n_train_rows"],
        "   MATCH" if len(fitted) == cfg["n_train_rows"] else "   *** MISMATCH ***"))
    if len(fitted) != cfg["n_train_rows"]:
        raise SystemExit("fitted row count disagrees with the model bundle; stop.")

    Xtr = fitted[features].to_numpy(dtype=float)
    if np.isnan(Xtr).any():
        raise SystemExit("NaN in training features; Mahalanobis needs complete rows.")

    # ---- mean, scale, covariance ----
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0, ddof=1)
    if (sd <= 0).any():
        raise SystemExit("zero-variance feature: {}".format(
            [f for f, s in zip(features, sd) if s <= 0]))
    Ztr = (Xtr - mu) / sd
    C = np.cov(Ztr, rowvar=False)                      # correlation matrix
    C_raw = np.cov(Xtr, rowvar=False)                  # reported for contrast only

    cond = float(np.linalg.cond(C))
    cond_raw = float(np.linalg.cond(C_raw))
    print()
    print("condition number, raw covariance          {:.3e}".format(cond_raw))
    print("condition number, standardised (used)     {:.3e}".format(cond))

    ridged = cond > RIDGE_TRIGGER
    if ridged:
        lam = 1e-6 * np.trace(C) / C.shape[0]
        C = C + lam * np.eye(C.shape[0])
        print("  ill-conditioned above {:.0e} -> ridge {:.3e} added to the diagonal"
              .format(RIDGE_TRIGGER, lam))
        print("  condition number after ridge            {:.3e}".format(np.linalg.cond(C)))
    else:
        print("  below the {:.0e} trigger -> NO regularisation applied".format(RIDGE_TRIGGER))

    # Cholesky of the inverse: D^2 = || (x-mu) L^-T ||^2, numerically safer
    # than forming the inverse and sandwiching it.
    L = np.linalg.cholesky(C)
    chol_inv = np.linalg.inv(L).T

    d_train = mahalanobis(Ztr, np.zeros(len(features)), chol_inv)
    ref_p99 = float(np.percentile(d_train, 99))

    # ---- the live cycle ----
    live = pd.read_parquet(args.live)
    init = str(live["init"].iloc[0])
    mask = imd_truth.land_mask()
    lat_slot = np.rint((live["lat"].to_numpy() - imd_truth.ANALYSIS_LAT[0]) / 0.5).astype(int)
    lon_slot = np.rint((live["lon"].to_numpy() - imd_truth.ANALYSIS_LON[0]) / 0.5).astype(int)
    gauged = mask[lat_slot, lon_slot]
    flagged = live["model_score"].to_numpy() >= confidence.THRESHOLD

    Zlive = (live[features].to_numpy(dtype=float) - mu) / sd
    d_live = mahalanobis(Zlive, np.zeros(len(features)), chol_inv)

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
    print("SQUARED MAHALANOBIS DISTANCE, 23 features, live cycle {}".format(init))
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

    table["cond_standardised"] = cond
    table["cond_raw"] = cond_raw
    table["ridged"] = ridged
    table["train_p99"] = ref_p99
    table["init"] = init
    table.to_csv(args.out, index=False)
    print("\nwrote {}".format(args.out))


if __name__ == "__main__":
    main()
