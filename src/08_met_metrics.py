"""VISHWAS — P14. Meteorological verification metrics and the operating point.

WHY THIS EXISTS
    ROC-AUC 0.728 against 0.565 is correct and threshold-free, and nobody
    operates a system at "AUC 0.728". This script turns the AUC difference into
    the sentence a forecaster actually understands:

        "Given the same number of alerts a forecaster would tolerate, VISHWAS
         catches X% of busts against the current method's Y%."

THE EVENT IS A BUST, NOT RAIN
    H  = we flagged it and the forecast busted
    M  = it busted and we did not flag it
    FA = we flagged it and the forecast was fine
    The arithmetic lives in src/met_metrics.py, which is imported, not
    reimplemented. Its self-test passes; this script never redefines a formula.

    Section 7 characterises the GEFS RAINFALL FORECAST ITSELF, where the event
    IS rain. That is a different application and it lives in its own table,
    clearly labelled. The two are never mixed.

THE OPERATING POINT IS CHOSEN ON VALIDATION, NEVER ON TEST
    The 13 interleaved 2018 dates carved out by 07_model.py exist for exactly
    this. Choosing a threshold on test and then reporting test metrics is
    reading the answer first.

TWO COMPARISONS, BOTH NEEDED, NEVER CONFLATED
    (A) FROZEN THRESHOLD — the operational number. The validation threshold is
        applied unchanged to 2019. The achieved alert rate is whatever it is,
        and it is printed every time.
    (B) MATCHED ALERT RATE — the fair head-to-head. Model and spread each flag
        exactly the same fraction of test cases, so the only remaining question
        is who catches more real busts. This uses test-set score QUANTILES, not
        test labels, and applies the identical rule to both methods.

    python src/08_met_metrics.py
    python src/08_met_metrics.py --bootstrap 2000
"""

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

# met_metrics.py is the arithmetic. It is imported, never reimplemented.
# compare_at_alert_rate() is deliberately NOT used: it selects by quantile, which
# is degenerate on ensemble spread (see flag_top below). Its components --
# contingency() and all_metrics() -- are used unchanged.
from met_metrics import all_metrics, contingency, threshold_at_alert_rate

# IMD's own daily rainfall classes, used only for the GEFS context table.
RAIN_THRESHOLDS = [(2.5, "light or more"), (15.6, "moderate or more"),
                   (64.5, "heavy or more")]

ALERT_RATES = [0.05, 0.10, 0.20]
PRIMARY_RATE = 0.10


def load_model_module():
    """07_model.py starts with a digit, so it cannot be imported by name."""
    path = os.path.join(_ROOT, "src", "07_model.py")
    spec = importlib.util.spec_from_file_location("model07", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rebuild(m07, labels_path, seed, validation_every):
    """Refit exactly as 07_model.py does, and keep the validation slice.

    07_model.py writes only test rows to model_predictions.parquet, so the
    validation scores this script needs do not exist on disk. The refit is
    checked against that file before any threshold is taken from it.
    """
    table = m07.load(labels_path, m07.STUDY_MIN, m07.STUDY_MAX)
    table, held = m07.carve_validation(table, validation_every)
    features = m07.feature_columns(table, with_location=False)

    fit = table[table["role"] == "train"]
    model = HistGradientBoostingClassifier(random_state=seed)
    model.fit(fit[features], fit["bust"].astype(int))

    out = {}
    for role in ("validation", "test"):
        block = table[table["role"] == role].copy()
        block["model_score"] = model.predict_proba(block[features])[:, 1]
        block["baseline_score"] = block["precip_spread"]
        out[role] = block
    return out["validation"], out["test"], held, features, model


def check_refit(test, pred_path):
    if not os.path.exists(pred_path):
        print("  (no {} to check against — skipping)".format(pred_path))
        return
    ref = pd.read_parquet(pred_path)
    got = test[["init", "lead_day", "lat", "lon", "model_score"]].rename(
        columns={"model_score": "refit_score"})
    joined = ref.merge(got, on=["init", "lead_day", "lat", "lon"], how="inner")
    if joined.empty:
        print("  REFIT CHECK FAILED: no rows joined.")
        sys.exit(1)
    delta = float(np.abs(joined["model_score"] - joined["refit_score"]).max())
    print("  refit check: {:,} rows joined, max |score difference| = {:.2e}".format(
        len(joined), delta))
    if delta > 1e-9:
        print("  REFIT CHECK FAILED: this is not the model the deck reports.")
        sys.exit(1)
    print("  refit reproduces data/model_predictions.parquet exactly.")


# --------------------------------------------------------------------------
# reporting helpers
# --------------------------------------------------------------------------

def flag_top(scores, rate, rng):
    """Flag exactly `rate` of cases, breaking ties at random.

    WHY THIS EXISTS, AND WHY IT IS NOT A REWRITE OF met_metrics. That module's
    threshold_at_alert_rate() takes a quantile and flags score >= cut, which is
    correct for a continuous score and DEGENERATE for ensemble spread. In the
    driest rainfall decile 91.2% of the 208,065 cases have spread of exactly
    0.00 mm -- 64 distinct values in the whole bin -- so the 90th-percentile cut
    is 0.00 and `>= 0.00` flags the entire bin. The first run of this script
    reported the baseline flagging 38.78% of cases against a 10% budget, which
    silently destroys the matched-budget premise the comparison rests on.

    Random tie-breaking is the honest model of what the incumbent actually
    faces: inside a tied group it has no information, so it picks arbitrarily,
    and a forecaster spending a fixed alert budget picks arbitrarily with it.
    The seed is fixed, so the result is reproducible.

    met_metrics.py is still the source of every metric; only the choice of
    WHICH cases to flag is made here.
    """
    scores = np.asarray(scores, dtype=float)
    n = len(scores)
    k = int(round(rate * n))
    if k <= 0:
        return np.zeros(n, dtype=bool)
    if k >= n:
        return np.ones(n, dtype=bool)
    order = np.lexsort((rng.random(n), -scores))
    flagged = np.zeros(n, dtype=bool)
    flagged[order[:k]] = True
    return flagged


def tie_share(scores, flagged):
    """Share of the flagged set that sits inside a tied score group.

    A high number means the budget was spent partly at random, which is a
    property of the SCORE, not of the alert rule -- and it is the strongest
    single statement about why ensemble spread cannot be operated in dry
    conditions.
    """
    scores = np.asarray(scores, dtype=float)
    if not flagged.any():
        return float("nan")
    cut = scores[flagged].min()
    tied = scores == cut
    return float((tied & flagged).sum()) / float(flagged.sum())


def metrics_header():
    return "  {:<26} {:>7} {:>7} {:>7} {:>7} {:>7} {:>7} {:>7}".format(
        "", "alert%", "POD", "FAR", "prec", "CSI", "ETS", "bias")


def metrics_row(label, m):
    return "  {:<26} {:>6.2f}% {:>7.3f} {:>7.3f} {:>7.3f} {:>7.3f} {:>7.3f} {:>7.2f}".format(
        label, 100 * m["alert_rate"], m["POD"], m["FAR"], 1.0 - m["FAR"],
        m["CSI"], m["ETS"], m["bias"])


def counts_row(label, m):
    return "  {:<26} H {:>6}   M {:>6}   FA {:>6}   CN {:>7}   N {:>7}".format(
        label, m["H"], m["M"], m["FA"], m["CN"], m["N"])


# --------------------------------------------------------------------------
# stratified variant
# --------------------------------------------------------------------------

def bin_codes(frame, m07):
    """Rainfall-magnitude deciles on precip_mean — the FORECAST amount, known at
    forecast time. Binning on truth would condition on the answer."""
    return pd.qcut(frame["precip_mean"], m07.STRATIFY_BINS,
                   labels=False, duplicates="drop").to_numpy()


def stratified_counts(observed, scores, codes, rate, rng):
    """Flag the top `rate` WITHIN each rainfall bin, then pool the four counts.

    Same discipline as the stratified AUC that produces the 0.728 headline:
    it removes the credit both methods get for free from the wet/dry spatial
    gradient. Counts are summed across bins and the metrics computed once from
    the pooled table -- averaging ratios across bins would weight a bin with
    three busts the same as a bin with three hundred.
    """
    h = m = fa = cn = 0
    for code in np.unique(codes[~pd.isna(codes)]):
        sel = codes == code
        flagged = flag_top(scores[sel], rate, rng)
        counts = contingency(observed[sel], flagged)
        h += counts[0]; m += counts[1]; fa += counts[2]; cn += counts[3]
    return h, m, fa, cn


# --------------------------------------------------------------------------
# cluster bootstrap
# --------------------------------------------------------------------------

def cluster_bootstrap_metrics(test, rate, replicates, seed, stratified, m07):
    """Interval on the model-minus-spread difference in POD, FAR and CSI.

    Resamples INIT DATES, not rows. Gridpoints inside one forecast are nearly
    the same observation, so a row-level bootstrap reports a falsely tight
    interval -- the same reasoning, and the same independent unit, as
    cluster_bootstrap_margin() in 07_model.py.

    That function could not be called directly: it is hardcoded to
    stratified_auc and returns an AUC margin. It IS reused unchanged, in
    section 5, for the AUC margin it does compute. Only the metric differs
    here; the resampling design is copied from it deliberately, including
    subsetting the columns before grouping (~26 MB per replicate instead of
    ~180 MB).
    """
    columns = ["init", "bust", "model_score", "baseline_score", "precip_mean"]
    frame = test[columns].reset_index(drop=True)
    observed = frame["bust"].to_numpy().astype(bool)
    model = frame["model_score"].to_numpy(dtype=float)
    base = frame["baseline_score"].to_numpy(dtype=float)
    codes = bin_codes(frame, m07) if stratified else None

    dates = sorted(frame["init"].unique())
    index_of = {d: np.nonzero((frame["init"] == d).to_numpy())[0] for d in dates}
    if len(dates) < 3 or replicates <= 0:
        return None

    rng = np.random.default_rng(seed)
    diffs = {"POD": [], "FAR": [], "CSI": []}
    for _ in range(replicates):
        picked = rng.choice(dates, size=len(dates), replace=True)
        rows = np.concatenate([index_of[d] for d in picked])
        obs = observed[rows]
        if not obs.any() or obs.all():
            continue
        if stratified:
            c = codes[rows]
            mm = all_metrics(*stratified_counts(obs, model[rows], c, rate, rng))
            bb = all_metrics(*stratified_counts(obs, base[rows], c, rate, rng))
        else:
            mm = all_metrics(*contingency(obs, flag_top(model[rows], rate, rng)))
            bb = all_metrics(*contingency(obs, flag_top(base[rows], rate, rng)))
        for key in diffs:
            diffs[key].append(mm[key] - bb[key])

    out = {}
    for key, values in diffs.items():
        values = np.array([v for v in values if np.isfinite(v)])
        if values.size == 0:
            continue
        out[key] = {"median": float(np.median(values)),
                    "low": float(np.percentile(values, 2.5)),
                    "high": float(np.percentile(values, 97.5)),
                    "n": int(values.size)}
    out["n_dates"] = len(dates)
    return out


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="P14 — meteorological metrics and the operating point.")
    p.add_argument("--labels", default=os.path.join(_ROOT, "data", "labelled.parquet"))
    p.add_argument("--pred", default=os.path.join(_ROOT, "data", "model_predictions.parquet"))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--validation-every", type=int, default=4)
    p.add_argument("--bootstrap", type=int, default=500)
    p.add_argument("--rate", type=float, default=PRIMARY_RATE,
                   help="primary alert rate, chosen on validation")
    a = p.parse_args()

    m07 = load_model_module()

    print("=" * 78)
    print("VISHWAS — P14. METEOROLOGICAL METRICS. EVENT = A FORECAST BUST.")
    print("=" * 78)
    print()
    print("Plain accuracy is never reported. The base rate is ~6%, so a model that")
    print("flags nothing scores 94% and detects nothing.")
    print()

    print("REBUILDING THE DECK MODEL")
    validation, test, held, features, model = rebuild(
        m07, a.labels, a.seed, a.validation_every)
    print("  {} features; validation {:,} rows over {} dates; "
          "test {:,} rows over {} dates".format(
              len(features), len(validation), validation["init"].nunique(),
              len(test), test["init"].nunique()))
    print("  bust base rate — validation {:.2f}%, test {:.2f}%".format(
        100 * validation["bust"].mean(), 100 * test["bust"].mean()))
    check_refit(test, a.pred)

    # ---- 1. operating point, chosen on validation -----------------------
    print()
    print("-" * 78)
    print("1. OPERATING POINT — CHOSEN ON VALIDATION, NEVER ON TEST")
    print("-" * 78)
    print("  The 13 interleaved 2018 dates 07_model.py held back exist for this.")
    print()
    thresholds = {}
    for rate in ALERT_RATES:
        t_model = threshold_at_alert_rate(validation["model_score"], rate)
        t_base = threshold_at_alert_rate(validation["baseline_score"], rate)
        thresholds[rate] = (t_model, t_base)
        got_m = float((validation["model_score"] >= t_model).mean())
        got_b = float((validation["baseline_score"] >= t_base).mean())
        mark = "  <- PRIMARY" if abs(rate - a.rate) < 1e-9 else ""
        print("  target top {:>4.0%}   VISHWAS p >= {:.4f} (validation alert rate {:.2f}%)"
              "   spread >= {:.3f} mm (alert rate {:.2f}%){}".format(
                  rate, t_model, 100 * got_m, t_base, 100 * got_b, mark))

    # ---- 2. frozen threshold on test ------------------------------------
    t_model, t_base = thresholds[a.rate]
    print()
    print("-" * 78)
    print("2. THE OPERATIONAL NUMBER — VALIDATION THRESHOLD FROZEN, APPLIED TO 2019")
    print("-" * 78)
    print("  Nothing is re-fitted here. The achieved test alert rate is whatever the")
    print("  frozen threshold produces, and it is printed rather than forced to 10%.")
    print()
    frozen = {}
    for name, column, cut in (("VISHWAS", "model_score", t_model),
                              ("ensemble spread", "baseline_score", t_base)):
        flagged = test[column].to_numpy(dtype=float) >= cut
        frozen[name] = all_metrics(*contingency(test["bust"].to_numpy(), flagged))
    print(metrics_header())
    for name in ("VISHWAS", "ensemble spread"):
        print(metrics_row(name, frozen[name]))
    print()
    for name in ("VISHWAS", "ensemble spread"):
        print(counts_row(name, frozen[name]))
    drift = 100 * (frozen["VISHWAS"]["alert_rate"] - a.rate)
    print()
    print("  Alert-rate drift from validation to test: {:+.2f} points. The 2019 test".format(drift))
    print("  year is wetter than the 2018 training year (bust base rate {:.2f}% vs {:.2f}%),".format(
        100 * test["bust"].mean(), 100 * validation["bust"].mean()))
    print("  so a frozen threshold fires somewhat more often. That is the honest")
    print("  operational behaviour and it is why section 3 exists.")

    # ---- 3. head to head at matched alert rate ---------------------------
    print()
    print("-" * 78)
    print("3. HEAD TO HEAD AT A MATCHED ALERT RATE — THE FAIR COMPARISON")
    print("-" * 78)
    print("  Both methods flag exactly the same fraction of 2019 cases, so the only")
    print("  question left is who catches more real busts. Cases are ranked by score")
    print("  and the top k flagged, ties broken at random with a fixed seed. No labels")
    print("  are used and the identical rule is applied to both methods.")
    print()
    obs = test["bust"].to_numpy()
    ms = test["model_score"].to_numpy(dtype=float)
    bs = test["baseline_score"].to_numpy(dtype=float)
    pooled = {}
    for rate in ALERT_RATES:
        rng = np.random.default_rng(a.seed)
        mf = flag_top(ms, rate, rng)
        bf = flag_top(bs, rate, rng)
        result = {"rate": rate,
                  "model": all_metrics(*contingency(obs, mf)),
                  "baseline": all_metrics(*contingency(obs, bf)),
                  "model_ties": tie_share(ms, mf),
                  "baseline_ties": tie_share(bs, bf)}
        pooled[rate] = result
        print("  alert budget = top {:.0%} of cases".format(rate))
        print(metrics_header())
        print(metrics_row("VISHWAS", result["model"]))
        print(metrics_row("ensemble spread", result["baseline"]))
        print("  {:<26} POD {:+.3f}   FAR {:+.3f}   CSI {:+.3f}   ETS {:+.3f}".format(
            "difference", result["model"]["POD"] - result["baseline"]["POD"],
            result["model"]["FAR"] - result["baseline"]["FAR"],
            result["model"]["CSI"] - result["baseline"]["CSI"],
            result["model"]["ETS"] - result["baseline"]["ETS"]))
        zero = bs == 0.0
        print("  ties: {:.1%} of VISHWAS's budget and {:.1%} of spread's fell inside a tied "
              "score group;".format(result["model_ties"], result["baseline_ties"]))
        print("        {:,} of spread's {:,} alerts ({:.1%}) were drawn from the "
              "zero-spread block".format(
                  int((bf & zero).sum()), int(bf.sum()),
                  float((bf & zero).sum()) / max(int(bf.sum()), 1)))
        print()

    # ---- 4. stratified ---------------------------------------------------
    print("-" * 78)
    print("4. THE SAME COMPARISON, STRATIFIED BY RAINFALL MAGNITUDE")
    print("-" * 78)
    print("  Each method flags the top {:.0%} WITHIN every precip_mean decile, and the".format(a.rate))
    print("  four counts are pooled across deciles. This removes the wet/dry gradient")
    print("  both methods get for free — the same correction that turns the pooled")
    print("  AUC of 0.885 vs 0.909 into the stratified 0.565 vs 0.728.")
    print()
    codes = bin_codes(test, m07)
    n_bins = len(np.unique(codes[~pd.isna(codes)]))
    print("  rainfall bins actually formed: {} (qcut collapses edges where "
          "precip_mean is exactly 0)".format(n_bins))
    print()
    print("  WHY THE ALERT RULE HAD TO BE RANK-BASED. Ensemble spread is DEGENERATE in")
    print("  dry conditions: a quantile cut of 0.00 mm flags a whole bin at once. The")
    print("  first version of this script reported the baseline spending 38.8% of cases")
    print("  against a 10% budget, which quietly voided the comparison. Ties are now")
    print("  broken at random, which is the honest model of a score that cannot rank.")
    print()
    print("  {:>4} {:>10} {:>11} {:>13} {:>13} {:>11}".format(
        "bin", "n", "median mm", "bust rate", "spread == 0", "distinct spread"))
    for code in np.unique(codes[~pd.isna(codes)]):
        sel = codes == code
        blk = test[sel]
        print("  {:>4} {:>10,} {:>11.2f} {:>12.2f}% {:>12.1%} {:>11,}".format(
            int(code), int(sel.sum()), float(blk["precip_mean"].median()),
            100 * float(blk["bust"].mean()),
            float((blk["precip_spread"] == 0).mean()),
            int(blk["precip_spread"].nunique())))
    print()
    print("  In the driest decile the incumbent has 64 distinct values to rank 208,065")
    print("  cases with, and 91% of them are the same value. It is not weakly")
    print("  informative there — it is unable to express a preference at all.")
    print()
    zero_all = int((test["precip_spread"] == 0.0).sum())
    print("  Across the whole test set ensemble spread is exactly 0.00 mm on {:,} of".format(zero_all))
    print("  {:,} rows ({:.1%}) — one tie covering close to a third of the data. Ties are".format(
        len(test), zero_all / len(test)))
    print("  broken by random within-tie order on a fixed seed. That is the only neutral")
    print("  choice: ordering the block by any other column would smuggle information")
    print("  into the baseline, and leaving it in input order would hand it whatever")
    print("  structure the file happens to carry.")
    print()
    strat = {}
    for rate in ALERT_RATES:
        strat[rate] = {
            "model": all_metrics(*stratified_counts(
                obs, ms, codes, rate, np.random.default_rng(a.seed))),
            "baseline": all_metrics(*stratified_counts(
                obs, bs, codes, rate, np.random.default_rng(a.seed))),
        }
        print("  alert budget = top {:.0%} within each bin".format(rate))
        print(metrics_header())
        print(metrics_row("VISHWAS", strat[rate]["model"]))
        print(metrics_row("ensemble spread", strat[rate]["baseline"]))
        print("  {:<26} POD {:+.3f}   FAR {:+.3f}   CSI {:+.3f}   ETS {:+.3f}".format(
            "difference",
            strat[rate]["model"]["POD"] - strat[rate]["baseline"]["POD"],
            strat[rate]["model"]["FAR"] - strat[rate]["baseline"]["FAR"],
            strat[rate]["model"]["CSI"] - strat[rate]["baseline"]["CSI"],
            strat[rate]["model"]["ETS"] - strat[rate]["baseline"]["ETS"]))
        print()

    # ---- 5. cluster bootstrap -------------------------------------------
    print("-" * 78)
    print("5. CLUSTER BOOTSTRAP BY INIT DATE — {} replicates".format(a.bootstrap))
    print("-" * 78)
    print("  The independent unit is the forecast date, not the gridpoint. 1,252")
    print("  gridpoints inside one forecast are nearly the same observation.")
    print()
    for label, stratify in (("pooled", False), ("stratified by rainfall bin", True)):
        boot = cluster_bootstrap_metrics(test, a.rate, a.bootstrap, a.seed,
                                         stratify, m07)
        if boot is None:
            continue
        print("  {} — model minus spread at a matched top-{:.0%} alert rate, "
              "{} dates resampled".format(label, a.rate, boot["n_dates"]))
        for key in ("POD", "FAR", "CSI"):
            if key not in boot:
                continue
            b = boot[key]
            crosses = "" if (b["low"] > 0) == (b["high"] > 0) else "   <- CROSSES ZERO"
            print("    d{:<4} median {:+.3f}   95% CI {:+.3f} to {:+.3f}{}".format(
                key, b["median"], b["low"], b["high"], crosses))
        print()

    # reuse 07_model.py's own bootstrap, unchanged, for the AUC margin
    auc_boot = m07.cluster_bootstrap_margin(test, "model_score", "baseline_score",
                                            a.bootstrap, a.seed)
    if auc_boot:
        print("  for reference, the stratified ROC-AUC margin from")
        print("  07_model.cluster_bootstrap_margin() (imported unchanged):")
        print("    median {:+.4f}   95% CI {:+.4f} to {:+.4f}   over {} dates".format(
            auc_boot["median"], auc_boot["low"], auc_boot["high"], auc_boot["n_dates"]))

    # ---- 6. the choice ---------------------------------------------------
    prim = pooled[a.rate]
    print()
    print("-" * 78)
    print("6. WHY THIS OPERATING POINT — PRECISION IS WEIGHTED OVER RECALL")
    print("-" * 78)
    print("  SIH26079 is filed under SMART AUTOMATION, not disaster management. An")
    print("  automated assistant that cries wolf gets switched off, and a switched-off")
    print("  assistant helps nobody. So a false alarm costs more than a missed bust")
    print("  here, and the operating point is chosen on precision (1 - FAR) rather")
    print("  than on raw POD. Under a disaster-management framing — where a missed")
    print("  event is the expensive error — this trade-off would go the other way.")
    print("  It is an engineering choice, made deliberately, not a default.")
    print()
    print("  {:>8}  {:>9}  {:>7}  {:>7}  {:>7}   {}".format(
        "budget", "precision", "POD", "CSI", "ETS", "alerts per forecast date"))
    for rate in ALERT_RATES:
        m = pooled[rate]["model"]
        per_date = m["N"] * m["alert_rate"] / test["init"].nunique()
        mark = "   <- PRIMARY" if abs(rate - a.rate) < 1e-9 else ""
        print("  {:>7.0%}  {:>9.3f}  {:>7.3f}  {:>7.3f}  {:>7.3f}   {:>10,.0f}{}".format(
            rate, 1 - m["FAR"], m["POD"], m["CSI"], m["ETS"], per_date, mark))
    print()
    print("  Tightening to 5% buys {:+.3f} precision and costs {:+.3f} POD.".format(
        (1 - pooled[0.05]["model"]["FAR"]) - (1 - prim["model"]["FAR"]),
        pooled[0.05]["model"]["POD"] - prim["model"]["POD"]))
    print("  Loosening to 20% costs {:+.3f} precision and buys {:+.3f} POD.".format(
        (1 - pooled[0.20]["model"]["FAR"]) - (1 - prim["model"]["FAR"]),
        pooled[0.20]["model"]["POD"] - prim["model"]["POD"]))
    print()
    print("  THE SENTENCE:")
    per_date = prim["model"]["N"] * prim["model"]["alert_rate"] / test["init"].nunique()
    cases_per_date = prim["model"]["N"] / test["init"].nunique()
    print("    Given the same number of alerts a forecaster would tolerate")
    print("    ({:,.0f} of the {:,.0f} gridpoint-lead-day cases on each forecast date —".format(
        per_date, cases_per_date))
    print("    that it equals the gridpoint count is arithmetic coincidence, the alerts")
    print("    are spread across all ten lead days),")
    print("    VISHWAS catches {:.0f}% of busts against the current method's {:.0f}%.".format(
        100 * prim["model"]["POD"], 100 * prim["baseline"]["POD"]))
    sm, sb = strat[a.rate]["model"], strat[a.rate]["baseline"]
    print()
    print("    Stratified within rainfall magnitude, where neither method gets")
    print("    credit for the wet/dry gradient: {:.0f}% against {:.0f}%.".format(
        100 * sm["POD"], 100 * sb["POD"]))

    # ---- 7. GEFS context, kept separate ---------------------------------
    print()
    print("=" * 78)
    print("7. THE UNDERLYING FORECAST, NOT OUR MODEL")
    print("=" * 78)
    print("  EVENT = RAIN, not a bust. This table scores the GEFS rainfall forecast")
    print("  itself against IMD gauges — how good is the forecast India relies on.")
    print("  It is CONTEXT FOR THE PITCH and it is NOT a VISHWAS score. Never quote a")
    print("  number from this table beside one from sections 2-6.")
    print()
    print("  Forecast event: GEFS ensemble-mean rainfall >= threshold.")
    print("  Observed event: IMD gauge-gridded rainfall >= the same threshold.")
    print()
    truth = test["truth"].to_numpy(dtype=float)
    fcst = test["precip_mean"].to_numpy(dtype=float)
    for threshold, name in RAIN_THRESHOLDS:
        print("  rain >= {:.1f} mm/day ({})".format(threshold, name))
        print("  {:<26} {:>7} {:>7} {:>7} {:>7} {:>7} {:>7}".format(
            "", "obs%", "POD", "FAR", "CSI", "ETS", "bias"))
        for lead in (1, 5, 10, None):
            sel = (np.ones(len(test), dtype=bool) if lead is None
                   else (test["lead_day"].to_numpy() == lead))
            m = all_metrics(*contingency(truth[sel] >= threshold,
                                         fcst[sel] >= threshold))
            label = "all leads (Day 1-10)" if lead is None else "Day {}".format(lead)
            print("  {:<26} {:>6.2f}% {:>7.3f} {:>7.3f} {:>7.3f} {:>7.3f} {:>7.2f}".format(
                label, 100 * m["base_rate"], m["POD"], m["FAR"], m["CSI"],
                m["ETS"], m["bias"]))
        print()
    print("  Truth: IMD 0.25 deg gauge-gridded daily rainfall, 1,252 land gridpoints,")
    print("  52 forecast dates of 2019, Day 1-10. n = {:,} forecast-gridpoint cases.".format(len(test)))


if __name__ == "__main__":
    main()
