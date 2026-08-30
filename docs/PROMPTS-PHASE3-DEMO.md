# VISHWAS — Phase 3: make it demonstrable

> ⛔ **HISTORICAL PROMPT ARCHIVE — not a statement of current state.**
> Phase 3 prompts P12-P14, written 29 Aug 2026.
> All of this work is complete. For what is true now, read `CLAUDE.md` or
> `docs/DECK-TECHNICAL-PACK.md`. Forward-looking wording below ("next",
> "not yet", "no model exists") described the repository on the date this
> file was written and is preserved deliberately. Banner added 30 Aug 2026
> by the consistency audit (`docs/CONSISTENCY-AUDIT.md`).

**Written 29 Aug 2026, 21:40 IST.** Sequel to `docs/PROMPTS-PHASE2-MODEL.md`
(P8–P11, all complete). Read `CLAUDE.md` first, always.

**Phase 2 proved the model works. Phase 3 makes it something you can show
someone.** The headline number will not change from here.

---

## Where things stand — do not redo any of this

| | |
|---|---|
| Data | 104 forecast dates, 2018–2019, 50.3 GB fetched |
| Labels | 1,302,080 rows, region-scope thresholds, leak-audited |
| Model | Trained. **Stratified ROC-AUC 0.728 vs baseline 0.565**, margin +0.163 (CI +0.108 to +0.193) |
| Ablations | All five done. `month` −0.006 (passes), dropping rainfall features +0.003, spread-only 0.562 |
| Figures | `figures/fig1_collapse.png`, `fig2_deciles.png`, `fig3_map.png` |
| Metrics library | `src/met_metrics.py` — POD/FAR/CSI/ETS, self-test passes |
| Validation slice | 13 dates (every 4th Wednesday of 2018), **untouched, reserved for P12/P14** |

**Order is by deck value, not by dependency.** The internal PPT is Monday
31 Aug. If only one of these gets done, make it P13.

---

## P13 — The confidence map and SHAP (DO THIS FIRST, ~1 h)

```
Read CLAUDE.md. The model is trained and validated; nothing here changes the
headline. This produces the missing SLIDE: right now we can tell a panel the
system works, but we cannot show them what it looks like.

PART A — THE CONFIDENCE MAP. This is the deliverable, and the priority.

1. Pick the demo date EMPIRICALLY, do not assume one. From
   data/model_predictions.parquet, find test dates with a high observed bust
   rate and a clear spatial signature. 2019's monsoon was late and heavy, so
   expect something in Jul-Sep. Report which date you picked and why.

2. For that single forecast date, render a figure showing, side by side:
     - VISHWAS predicted bust probability across the 1,252 land gridpoints
     - what actually happened: observed IMD rainfall
     - hits and misses: where the model flagged and was right, flagged and was
       wrong, and missed a real bust
   Pick one lead day (Day 5 is a good default — far enough out to matter,
   close enough that a forecaster would act on it) and say which you used.

3. MATCH THE EXISTING VISUAL LANGUAGE so the deck looks like one system.
   figures/fig3_map.png is the reference: 0.5 degree squares (marker="s"),
   sequential blue ramp #cde2fb -> #0d366b, surface #fcfcfb, ink #0b0b0b,
   secondary ink #52514e, grid #e6e5e1, aspect 1/cos(22 deg), 200 dpi, title
   and subtitle as figure text (not ax.set_title, which collides), and a
   footnote carrying truth source and sample size.
   For the probability panel a sequential ramp is right. For hits/misses use
   CATEGORICAL colours, not a ramp — #2a78d6 (blue) and #eb6834 (orange) are
   the validated first two slots.

4. Save to figures/. These are demo assets: they must survive being projected
   in a room, so no thin grey text and no 8pt labels.

PART B — SHAP.

The problem statement explicitly requires EXPLAINABLE output, so this is a
scored requirement, not polish.

5. shap 0.49.1 is installed. Use TreeExplainer on a SAMPLE of test rows (a few
   thousand — TreeSHAP is slow and you do not need millions).
   If shap does not support HistGradientBoostingClassifier cleanly, SAY SO and
   report it rather than silently substituting a worse explainer. We already
   have permutation importance from P11 as a fallback, so a clean failure here
   costs us little; a silent substitution would cost us credibility.

6. Produce:
     - global feature importance (compare it against P11's permutation
       importance — pwat_mean +0.086, precip_spread +0.066, precip_mean +0.061.
       If SHAP disagrees materially, that is interesting, report it)
     - a per-prediction breakdown for 2-3 of the highest-confidence bust
       predictions: WHY did the model flag this particular forecast?
   That second one is the actual explainability deliverable. "The model
   flagged this because moisture was high and the ensemble disagreed sharply"
   is what a forecaster needs; a bar chart of global importances is not.

REPORT: which date and lead day you chose and why, what the map shows, whether
SHAP worked, and whether its ranking agrees with permutation importance.

CONSTRAINT: label every figure with its truth source and sample size. Do not
present a single date as evidence of general performance — it is an
illustration, and the caption must say so.
```

---

## P14 — Metrics at a matched alert budget (~1 h)

```
Read CLAUDE.md and the corrections to Paras's metrics guide recorded in
docs/PROMPTS-PHASE2-MODEL.md (P14 section). src/met_metrics.py is written and
its self-test passes — do not rewrite it, import it.

This turns an AUC difference into the sentence a forecaster actually
understands. AUC is threshold-free and correct, but nobody operates a system
at "AUC 0.728".

Write src/08_met_metrics.py:

1. EVENT = BUST, not rain. H = we flagged it and it busted. M = it busted and
   we missed it. FA = we flagged it and the forecast was fine.

2. OPERATING POINT chosen on the VALIDATION slice (the 13 held-out dates from
   2018), NEVER on test. Primary: flag the top 10% of cases by predicted
   probability. Print the threshold and the resulting alert rate every time.

3. THE HEAD-TO-HEAD. Compare model vs ensemble spread AT THE SAME ALERT RATE.
   Both flag exactly 10% of cases; the only question left is who catches more
   real busts. Report POD, FAR, CSI, ETS for both, side by side. Sweep the
   alert rate at 5%, 10% and 20% so the trade-off is visible.

   The output we want is this sentence, with real numbers in it:
     "Given the same number of alerts a forecaster would tolerate, VISHWAS
      catches X% of busts against the current method's Y%."

4. WEIGHT PRECISION OVER RECALL when choosing the operating point, and say why:
   the theme is Smart Automation, and an automated assistant that cries wolf
   gets switched off. Under a disaster-management framing the trade-off would
   go the other way. That is a defensible engineering choice, not a default —
   make it visible.

5. STRATIFY within rainfall-magnitude bins as well as pooled. Same discipline
   as everywhere else in this project.

6. Cluster-bootstrap the difference by INIT DATE (reuse cluster_bootstrap from
   07_model.py — it was optimised to subset columns first, so it is fast now).

7. Also compute POD/FAR/CSI/ETS for the GEFS rainfall forecast itself (event =
   rain above a stated threshold) as CONTEXT ONLY, in a clearly separate table
   labelled "the underlying forecast, not our model". Never mix the two.

CONSTRAINTS:
- Never report plain accuracy. Base rate is ~6%.
- ETS IS computable from the four counts: H_rand = (H+FA)(H+M)/N. Paras's guide
  says otherwise; the guide is wrong on that point.
```

---

## P12 — Calibration, and finally save the model (~1 h)

```
Read CLAUDE.md.

An automated confidence indicator that is not calibrated is decoration. If the
system says "20% chance of a bust" it must be wrong about one time in five, or
a forecaster cannot act on the number. Most hackathon teams skip this, which is
exactly why doing it properly is worth points — and under a Smart Automation
theme, trust in the magnitude is the whole product.

1. SAVE THE TRAINED MODEL. It is currently never persisted — 07_model.py trains
   in memory and writes only predictions, so there is no model artifact at all.
   Add joblib.dump to models/vishwas_model.joblib, together with the feature
   list and the training configuration, so a demo does not have to retrain on
   launch. Two lines, long overdue.

2. Fit calibration on the VALIDATION slice — the 13 dates from 2018 that
   07_model.py deliberately held back. NEVER on test; calibrating on test
   invalidates the test.
   Fit isotonic regression, and Platt scaling for comparison.

3. Reliability diagram on the TEST set: predicted probability against observed
   frequency, WITH counts per bin so sparse bins are visibly sparse. Save to
   figures/ in the same visual language as the others (see P13 part A step 3).

4. Brier score, DECOMPOSED into reliability / resolution / uncertainty. Report
   all three, not just the total — resolution is the part that says the model
   is informative, reliability is the part that says it is honest.

5. Compare calibrated vs uncalibrated vs the ensemble-spread baseline.

ACCEPTANCE: a reliability curve close to the diagonal, a Brier decomposition
table, and a saved model file that loads and reproduces the same predictions.

REPORT: whether the raw model was already well calibrated (gradient boosting
often is not), which calibrator won, and by how much.
```

---

## After Monday, not before

**The 5-year extension** is the single strongest thing you can add before the
20 Sep submission: `--years 5` adds 156 dates (~1.7 h more if 850 hPa is kept)
and refetches nothing. It would give per-gridpoint bust thresholds instead of
region scope, and a genuinely multi-year test instead of one year.

**Read the mixed-schema warning in `CLAUDE.md` first** — if the new dates are
fetched without the 850 hPa columns while the existing 104 have them,
`finalize()` will not catch it and the column becomes silently NaN for 60% of
the data.
