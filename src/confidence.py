"""VISHWAS — the operating point, and the verdict rule, in one place.

Imported by src/15_dashboard_export.py (which writes these values into
site/dashboard-data.json) and by api/main.py (which reads them back out).
There is one definition of the threshold and one implementation of the
banding, and everything else derives from this file or from the JSON it fills.

WHY THE THRESHOLD IS A PINNED LITERAL AND NOT RECOMPUTED
--------------------------------------------------------
THRESHOLD is np.quantile(model_score, 0.90) over the 651,040-row 2019 test
set, computed ONCE and pinned here in full double precision. It is NOT
recomputed at import, and that is the entire point of this file.

A different test set has a different 90th percentile. The five-year extension
will have one. Adopting it is a legitimate decision, but it means republishing
every downstream count -- the confidence map, the met metrics, the demo panel,
the deck -- deliberately and all at once. A threshold that quietly re-derives
itself from whatever data happens to be loaded moves those numbers without
anyone deciding to, which is exactly the failure this pinning prevents.

Every published count was computed at this value: 547 flagged on 20190731
Day 5, being 395 hits, 152 false alarms and 59 misses. Those are the
acceptance test.

NEITHER 0.1535 NOR 0.153471 IS THIS CONSTANT. Both are display roundings and
neither may be used as a constant anywhere.
  - 0.1535 rounds UP past one cell scoring 0.1534840, giving 546 where the
    published figure is 547. That is where the 546/547 discrepancy came from,
    and scripts/check_docs.py forbids it as a bare constant.
  - 0.153471 truncates BELOW one cell scoring 0.15347109047316893 (20190731,
    Day 4, 25.5N 74.0E), flipping it from uncertain to high risk. No published
    count depends on Day 4, so nothing moved when this was corrected -- but the
    export disagreed with what had been computed, which is the same defect one
    decimal place further down.
Quote the threshold in prose as "p >= 0.153". Read this constant, or a cell's
stored verdict, for anything machine-readable.

WHY CONSUMERS GET A STORED VERDICT, NOT A COMPARISON
----------------------------------------------------
Probabilities are published at four decimals, and scores either side of the
threshold both display as 0.1535. Any consumer that re-derives a class from
the displayed number will disagree with the published counts on some cell, at
whatever precision is chosen. Storing the verdict removes the possibility
instead of making it less likely. This is the aug5.json boundary problem for
the third time, and it is meant to be the last.
"""

THRESHOLD = 0.1534712256035554
UNCERTAIN_FLOOR = 0.08

RELIABLE, UNCERTAIN, HIGH_RISK = 0, 1, 2

VERDICT_NAMES = {RELIABLE: "reliable",
                 UNCERTAIN: "uncertain",
                 HIGH_RISK: "high_risk"}


def verdict_of(score, floor=UNCERTAIN_FLOOR, threshold=THRESHOLD):
    """Band one RAW score. Never pass a rounded probability to this."""
    if score >= threshold:
        return HIGH_RISK
    if score >= floor:
        return UNCERTAIN
    return RELIABLE


def verdicts_of(scores, floor=UNCERTAIN_FLOOR, threshold=THRESHOLD):
    """Vectorised verdict_of, for a numpy array of raw scores."""
    import numpy as np
    return (np.asarray(scores) >= floor).astype(int) + \
           (np.asarray(scores) >= threshold).astype(int)
