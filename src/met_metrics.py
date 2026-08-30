"""
Meteorological verification metrics — pure functions, no data dependencies.

Library for 08_met_metrics.py (P14). Kept separate and dependency-free so the
arithmetic can be tested on its own, the way imd_truth.py is a library for the
numbered pipeline scripts.

THE EVENT IS A BUST, NOT RAIN
-----------------------------
Paras's metrics guide frames every metric around rainfall detection ("when rain
really happened, did our model notice it?"). VISHWAS does not forecast rain, it
forecasts BUSTS. For our scores:

    HIT             we flagged it AND the forecast busted
    MISS            it busted and we did not flag it
    FALSE ALARM     we flagged it and the forecast was fine
    CORRECT NEG     neither

The same functions serve the other application — characterising the GEFS
rainfall forecast itself, where the event IS heavy rain — but the two must
never share a results table. Pass a `label` through and keep them apart.

CORRECTIONS TO THE GUIDE, verified 27 Aug 2026
----------------------------------------------
- ETS IS fully computable from the four counts. The guide says it is not.
  H_rand = (H + FA) * (H + M) / N, which needs nothing beyond H, M, FA, CN.
  Only FSS needs the spatial fields.
- The guide's section 11 example (H=60, M=20, FA=10, CN=10) states accuracy is
  90%. It is 70%. That example also has an 80% event base rate, so it cannot
  illustrate the rare-event problem it is being used to make; section 2's
  example (H=20, M=5, FA=10, CN=65) does. Both are in the self-test below.

Run the self-test:
    python src/met_metrics.py
"""

import numpy as np

__all__ = ["contingency", "pod", "far", "csi", "ets", "frequency_bias",
           "all_metrics", "threshold_at_alert_rate", "compare_at_alert_rate"]


def _safe(numerator, denominator):
    """Division that returns NaN rather than raising or silently giving inf.

    An undefined metric is a real state — POD is undefined when nothing was
    observed — and it must stay visible as NaN rather than becoming 0.0 and
    quietly dragging a mean down.
    """
    denominator = float(denominator)
    if denominator == 0.0:
        return float("nan")
    return float(numerator) / denominator


def contingency(observed, predicted):
    """Four counts from two boolean arrays.

    observed[i]  — did the event actually occur (for us: did it bust)
    predicted[i] — did we flag it

    Returns (H, M, FA, CN) as ints.
    """
    observed = np.asarray(observed).astype(bool)
    predicted = np.asarray(predicted).astype(bool)
    if observed.shape != predicted.shape:
        raise ValueError("observed {} and predicted {} differ in shape".format(
            observed.shape, predicted.shape))
    hit = int(np.sum(observed & predicted))
    miss = int(np.sum(observed & ~predicted))
    false_alarm = int(np.sum(~observed & predicted))
    correct_neg = int(np.sum(~observed & ~predicted))
    return hit, miss, false_alarm, correct_neg


def pod(hit, miss, false_alarm=None, correct_neg=None):
    """Probability of detection. Of the busts that happened, how many did we
    catch? Higher is better, max 1."""
    return _safe(hit, hit + miss)


def far(hit, miss, false_alarm, correct_neg=None):
    """False alarm ratio. Of the cases we flagged, how many were wrong?
    LOWER is better, min 0. Note this is conditional on us flagging — it says
    nothing about how many real busts we missed."""
    return _safe(false_alarm, hit + false_alarm)


def csi(hit, miss, false_alarm, correct_neg=None):
    """Critical success index. Hits over everything that was either flagged or
    observed. Ignores correct negatives, which is why it beats accuracy for a
    rare event. Higher is better, max 1."""
    return _safe(hit, hit + miss + false_alarm)


def ets(hit, miss, false_alarm, correct_neg):
    """Equitable threat score — CSI with chance hits removed.

    H_rand = (H + FA) * (H + M) / N is the number of hits you would expect from
    a random forecast with the same number of alarms and the same event
    frequency. Subtracting it is what makes scores comparable across regions
    and seasons with different base rates.

    Ranges from -1/3 to 1; 0 means no skill beyond chance.
    """
    total = hit + miss + false_alarm + correct_neg
    if total == 0:
        return float("nan")
    hits_by_chance = (hit + false_alarm) * (hit + miss) / float(total)
    return _safe(hit - hits_by_chance,
                 hit + miss + false_alarm - hits_by_chance)


def frequency_bias(hit, miss, false_alarm, correct_neg=None):
    """Alarms raised divided by events observed. 1 is unbiased.

    Worth reporting beside POD: it is the direct detector of the "flag
    everything" failure the guide warns about. A POD of 0.95 with a bias of 6
    means the model is crying wolf, not detecting well.
    """
    return _safe(hit + false_alarm, hit + miss)


def all_metrics(hit, miss, false_alarm, correct_neg):
    """Every count-based metric at once, as a dict."""
    total = hit + miss + false_alarm + correct_neg
    return {
        "H": hit, "M": miss, "FA": false_alarm, "CN": correct_neg, "N": total,
        "base_rate": _safe(hit + miss, total),
        "alert_rate": _safe(hit + false_alarm, total),
        "POD": pod(hit, miss),
        "FAR": far(hit, miss, false_alarm),
        "CSI": csi(hit, miss, false_alarm),
        "ETS": ets(hit, miss, false_alarm, correct_neg),
        "bias": frequency_bias(hit, miss, false_alarm),
        # Reported ONLY so a reader can see how misleading it is on a rare
        # event. Never quote it on its own — CLAUDE.md forbids it.
        "accuracy_do_not_quote": _safe(hit + correct_neg, total),
    }


def threshold_at_alert_rate(scores, rate):
    """Score threshold that flags exactly `rate` of cases (the top `rate`).

    POD/FAR/CSI/ETS need a binary decision but the model emits a probability,
    so an operating point must be chosen. Choosing it by alert rate — rather
    than by a fixed probability — is what makes the model and the baseline
    comparable: both spend the same alert budget.

    Pick `rate` on VALIDATION, never on test.
    """
    if not 0.0 < rate < 1.0:
        raise ValueError("alert rate must be strictly between 0 and 1")
    scores = np.asarray(scores, dtype=float)
    finite = scores[np.isfinite(scores)]
    if finite.size == 0:
        raise ValueError("no finite scores")
    return float(np.quantile(finite, 1.0 - rate))


def compare_at_alert_rate(observed, model_scores, baseline_scores, rate):
    """Head-to-head at a matched alert budget.

    Both rankings flag the same fraction of cases, so the only question left is
    which one catches more real busts. This is the fairest comparison available
    and it states directly: "given the same number of alerts a forecaster would
    tolerate, we catch X% of busts against the incumbent's Y%."

    Returns {"model": {...}, "baseline": {...}, "rate": rate}.
    """
    out = {"rate": rate}
    for name, scores in (("model", model_scores), ("baseline", baseline_scores)):
        cut = threshold_at_alert_rate(scores, rate)
        flagged = np.asarray(scores, dtype=float) >= cut
        out[name] = all_metrics(*contingency(observed, flagged))
        out[name]["threshold"] = cut
    return out


def _self_test():
    """Known values, including the two examples from Paras's guide."""
    cases = [
        # (label, H, M, FA, CN, expected POD, FAR, CSI, ETS)
        ("guide S2  (25% base rate)", 20, 5, 10, 65,
         0.800, 0.3333, 0.5714, 0.4545),
        ("guide S11 (80% base rate)", 60, 20, 10, 10,
         0.750, 0.1429, 0.6667, 0.1176),
        ("perfect forecast", 10, 0, 0, 90, 1.0, 0.0, 1.0, 1.0),
        ("flags everything", 10, 0, 90, 0, 1.0, 0.9, 0.1, 0.0),
        ("flags nothing", 0, 10, 0, 90, 0.0, float("nan"), 0.0, 0.0),
    ]
    print("met_metrics self-test")
    print("=" * 74)
    print("%-28s %7s %7s %7s %7s %8s" % ("case", "POD", "FAR", "CSI", "ETS", "acc"))
    failures = 0
    for label, h, m, fa, cn, e_pod, e_far, e_csi, e_ets in cases:
        got = all_metrics(h, m, fa, cn)
        print("%-28s %7.3f %7.3f %7.3f %7.3f %7.0f%%" % (
            label, got["POD"], got["FAR"], got["CSI"], got["ETS"],
            100 * got["accuracy_do_not_quote"]))
        for name, expected in (("POD", e_pod), ("FAR", e_far),
                               ("CSI", e_csi), ("ETS", e_ets)):
            actual = got[name]
            ok = (np.isnan(expected) and np.isnan(actual)) or \
                 (not np.isnan(expected) and abs(actual - expected) < 5e-4)
            if not ok:
                print("    FAIL %s: got %.6f, expected %.6f" % (
                    name, actual, expected))
                failures += 1
    print()

    # The point the guide missed: CSI 0.667 looks respectable until chance
    # hits are removed, and then almost all of it disappears.
    s11 = all_metrics(60, 20, 10, 10)
    print("Why ETS matters — guide section 11's own numbers:")
    print("  CSI %.3f  ->  ETS %.3f. Events occur 80%% of the time there, so"
          % (s11["CSI"], s11["ETS"]))
    print("  most of that CSI is hits anyone would get by guessing.")
    print("  Accuracy is %.0f%%, not the 90%% the guide states."
          % (100 * s11["accuracy_do_not_quote"]))
    print()

    # Operating point / matched alert rate.
    rng = np.random.default_rng(0)
    observed = rng.random(20000) < 0.05
    informative = rng.random(20000) + observed * 0.55
    noise = rng.random(20000)
    result = compare_at_alert_rate(observed, informative, noise, 0.10)
    print("Matched alert rate (both flag 10%), synthetic check:")
    for who in ("model", "baseline"):
        block = result[who]
        print("  %-9s alert %.1f%%  POD %.3f  FAR %.3f  CSI %.3f  ETS %.3f" % (
            who, 100 * block["alert_rate"], block["POD"], block["FAR"],
            block["CSI"], block["ETS"]))
    if not result["model"]["POD"] > result["baseline"]["POD"]:
        print("    FAIL: informative scores should beat noise")
        failures += 1
    if abs(result["model"]["alert_rate"] - result["baseline"]["alert_rate"]) > 0.01:
        print("    FAIL: alert rates are not matched")
        failures += 1
    print()
    print("FAILURES: %d" % failures)
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if _self_test() else 0)
