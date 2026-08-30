# VISHWAS — Phase 2 prompts: from measurement to model

> ⛔ **HISTORICAL PROMPT ARCHIVE — not a statement of current state.**
> Phase 2 prompts P8-P14, written 27 Aug 2026.
> All of this work is complete. For what is true now, read `CLAUDE.md` or
> `docs/DECK-TECHNICAL-PACK.md`. Forward-looking wording below ("next",
> "not yet", "no model exists") described the repository on the date this
> file was written and is preserved deliberately. Banner added 30 Aug 2026
> by the consistency audit (`docs/CONSISTENCY-AUDIT.md`).

**Written 27 Aug 2026.** Sequel to `docs/CLAUDE-CODE-PROMPTS.md` (P1–P7, all
done except the bulk run). Read `CLAUDE.md` first, always.

Phase 1 measured the incumbent. **Phase 2 builds the thing.** These prompts
close the gap that P1–P7 never covered: there is currently **no label, no
model, and no accuracy number of any kind** in this repo.

---

## 0. Order of work — read this first

**P8 is I/O-bound and P9–P10 are not. Start P8 first and write code while it
downloads.** Sequencing them wastes three hours.

```
P8  bulk run, 2 years        ~3 h, background   ─┐
P9  label construction        ~1 h, needs P8 done │ write P9 while P8 runs
P10 baseline + model + eval   ~1 h, needs P9      │
P11 ablations                 ~30 min             │
P12 calibration               ~1 h               │
P13 SHAP + confidence map     ~1 h               ─┘
P14 meteorological metrics    ~1 h, needs P10   — integrates Paras's guide
```

**P10 is the one that produces the number the deck needs.** P11–P13 make it
defensible and demonstrable. If time is short, P8→P9→P10 is the spine.

### The one design decision to make before P9

The bust label needs a **reference population** — "worse than the 95th
percentile *of what?*" Two defensible answers, and they say different things:

- **Per gridpoint, per lead time** (recommended). Every gridpoint then has
  exactly 5% busts in training, so local climatology is removed by
  construction and the model is forced to predict *when*, not *where*. This is
  the same logic that made you condition on rainfall magnitude — it is the
  strict, scientifically honest choice, and it is the harder one to beat.
- **Per region, per lead time.** Keeps the spatial signal, so "the Western
  Ghats are less predictable" becomes learnable. Operationally useful, but a
  model can score well on it by learning geography rather than meteorology.

Take per-gridpoint as primary and report per-region as a sensitivity. Document
whichever you choose — a judge will ask what the threshold was relative to.

---

## P8 — Bulk run, two years first

```
Read CLAUDE.md. Prerequisites P2 (850 hPa) and P5 (climatology fix) are done,
and the resume test passed under SIGKILL.

Run the bulk fetch for TWO years, not five:

    python src/02_features.py --years 2

Rationale: ~104 Wednesdays, ~49 GB, ~3 hours at the corrected 468 MB/date. That
is enough to train and evaluate a first model end to end. The manifest is
resumable and --years filters by cutoff date, so a later --years 5 ADDS
2015-2017 without refetching a single byte of 2018-2019. Starting small costs
nothing and de-risks the whole pipeline.

CONSTRAINTS:
- ONE process only. The manifest has no locking — two concurrent runs will
  duplicate dates and race on the same part file.
- Log throughput. If it is far off 4.5 MB/s, stop and report; this is
  bandwidth-bound, so more concurrency will not help.
- Do NOT run finalize() yet. P9 needs to decide the train window first, and
  finalize() now requires --train-end for exactly that reason.

Run it in the background and report when it lands. While it runs, move to P9.
```

---

## P9 — Label construction (`src/06_label.py`) — THE MISSING LINK

```
Read CLAUDE.md, especially the LEAKAGE section and the FEATURE SOURCE RULE.

There is currently no way to get from the feature table to a trainable dataset.
features.parquet has 27 columns and NO truth, NO error, NO label. Build that
bridge.

Write src/06_label.py:

1. JOIN. For each feature row (init, lead_day, lat, lon), the valid date is
   init + lead_day days. Join IMD truth for that valid date at that gridpoint,
   using src/imd_truth.py from P1.
   - Colocation is exact (P1 proved 65/65 lats, 68/68 lons, zero float error).
     ASSERT it; never fall back to nearest-neighbour.
   - IMD ocean/missing is -999 -> NaN. DROP those rows. Never let -999 become
     0 mm. Report how many rows survive (expect roughly 1252 of 5041 points).

2. ERROR. error = |precip_mean - truth|, in mm. precip_mean is the ensemble
   mean already in the feature table.

3. LABEL — AND THIS IS WHERE THE PROJECT'S THIRD LEAKAGE BUG WOULD LIVE.
   bust = error > 95th percentile.
   The percentile MUST be computed on the TRAINING WINDOW ONLY, then applied
   unchanged to the test window. If you compute it over all data, every test
   row helps set the threshold that judges it. This is the identical mistake
   the climatology leak was (P5) — do not repeat it in a new place.
   - Take --train-end as a REQUIRED argument. No default. A silent default is
     how the last leak survived three sessions.
   - Primary: threshold per (lat, lon, lead_day), train rows only.
   - FLOOR ON EXPECTED EXCEEDANCES, NOT SAMPLE COUNT (corrected 29 Aug).
     A 95th percentile from n samples rests on n*(1-p) exceedances. At 52 train
     dates that is 2.6 — far too few, though it passes a naive n>=30 check.
     Require n_train*(1-percentile) >= 8 before using a gridpoint threshold;
     otherwise fall back to regional and RECORD which rows used the fallback.
     Consequence for the 2-year run: region scope is PRIMARY, gridpoint is the
     sensitivity. That reverses when 5 years lands (156 train -> 7.8, adequate).
     Do NOT lower the percentile to 90 to rescue gridpoint scope — that changes
     the scientific definition of a bust to work around a data limitation.
     STATUS: implemented in src/06_label.py as --min-exceedances (default 8).
   - Persist the threshold table to data/bust_thresholds.parquet so it is
     auditable and reusable.
   - Also emit a --by region variant for the sensitivity check.

4. OUTPUT: data/labelled.parquet — features + truth + error + bust + a
   `split` column ("train"/"test") derived from --train-end.

ACCEPTANCE CRITERIA — print all of these:
- rows in, rows dropped for missing truth, rows out
- bust base rate in train (should be ~5% by construction) AND in test (will
  NOT be exactly 5% — if it is, your threshold leaked)
- that base-rate difference is the proof the split is honest. Report it.
- confirm no row has bust computed from a threshold that saw it

CONSTRAINTS:
- ERA5/IMD are TRUTH ONLY. Nothing derived from truth may become a feature.
  error and bust are labels, not inputs. If you later add "regional error
  climatology", it is train-only and frozen — see CLAUDE.md.
- Readable code. The team is Semester 3.
```

---

## P9 hardening — independent review, 29 Aug — ALL FOUR APPLIED

`06_label.py` was reviewed by a second session and verified against the raw
`.grd` bytes (no `imdlib` in the loop). **Verified correct:** -999 -> NaN is
complete (-999.0 is the ONLY negative value in 2012/2015/2018); year files are
cached; file sizes fit exactly including 2012's 366 days; the 28.5% valid-cell
fraction independently reproduces the 1252-gridpoint land count; and the
gridpoint -> region -> global fallback chain is fitted on train rows throughout.

Four changes were made and unit-tested:

1. **Exceedance gate** — `--min-exceedances` (default 8) replaces the raw
   `n_train >= 30` check. At the 95th pct this needs >= 160 train samples, so
   the 2-year run correctly falls back to region scope.
2. **`truth >= 0` assertion** after the NaN filter. -999 is handled and
   verified, but rainfall cannot be negative, so one comparison also catches a
   changed IMD sentinel, an unseen year's undef, and any sign error.
3. **Dead colocation return removed.**
4. **Length guards on both fallback merges**, so a future duplicate key fails
   loudly instead of silently shifting every threshold.

---

## P10 — Baseline, model, and the honest evaluation (`src/07_model.py`)

```
Read CLAUDE.md HONESTY RULES before writing a line of this.

This prompt produces the number that goes in the deck. Getting the EVALUATION
right matters more than getting the model right.

1. SPLIT BY TIME, never randomly. Use the `split` column from P9. Weather is
   autocorrelated; a random split inflates every metric.

2. BASELINE FIRST, and make it strong. Rank test rows by ensemble spread
   (precip_spread) alone. Compute ROC-AUC and PR-AUC. This is what forecasters
   have today and it is what we must beat. Do not handicap it.

3. MODEL: HistGradientBoostingClassifier. CPU only, no GPU anywhere in this
   project. Start with defaults; do not tune before you have a first number.

4. EVALUATE TWICE, AND SAY WHICH ONE IS HONEST:
   a. POOLED over all test rows.
   b. STRATIFIED WITHIN RAINFALL-MAGNITUDE BINS (deciles of precip_mean),
      reported per bin and as an n-weighted mean.

   PREDICTION, so you are not fooled: the pooled ROC-AUC will probably look
   great (0.75-0.85) because precip_mean predicts large absolute errors
   trivially. That is the SAME wet/dry artefact this project exists to expose.
   The stratified number will be much lower (perhaps 0.55-0.65).
   THE STRATIFIED NUMBER IS THE HEADLINE. Putting the pooled number on a slide
   would repeat, in our own work, precisely the error our pitch accuses the
   incumbent method of.

5. THE DECISION RULE, fixed BEFORE you see results so nobody moves goalposts:
   - stratified model AUC clearly above stratified baseline AUC -> we beat it,
     report the margin with a bootstrap interval over init dates
   - roughly equal -> we did NOT beat it. Say so plainly.
   - Either way it goes in the report. CLAUDE.md: "If we cannot beat ensemble
     spread, SAY SO."

6. NEVER report plain accuracy. Base rate is ~5%; accuracy is meaningless and
   quoting it signals we do not understand imbalance.

7. Bootstrap the model-minus-baseline margin by CLUSTERING ON INIT DATE, not on
   rows. Gridpoints within one forecast are not independent — this is the same
   correction 04_conditional.py already makes. Reuse its cluster_bootstrap.

REPORT: a table of baseline vs model, pooled and stratified, ROC-AUC and
PR-AUC, with the margin and its interval. State the verdict against rule 5.
```

### P10 amendments A-D — all implemented in `src/07_model.py`

**A. THE SPLIT IS train = 2018, test = 2019.** An earlier 60/20/24 split by
index was WRONG and is withdrawn: the last 24 dates are 2019-07-17 onward,
containing **zero MAM dates**, and testing a four-season claim on a test set
missing a season is indefensible. Use `--train-end 2018-12-31`. Both blocks
then carry identical, complete seasonal composition:

    train 2018   52 dates   DJF 13  MAM 13  JJAS 17  ON 9
    test  2019   52 dates   DJF 13  MAM 13  JJAS 17  ON 9

VALIDATION comes from inside 2018: **every 4th Wednesday** (13 dates,
seasonally spread). The tail of 2018 would give an ON/DJF-only validation set,
and a calibration fitted on post-monsoon need not transfer to monsoon.

**B. Filter to the study window.** The four January-2000 smoke parts have been
moved to `data/features_parts/_smoke_jan2000/` so `finalize()`'s `os.listdir`
glob cannot sweep them into the 2018 training window. `07_model.py` also
filters by date as a second line of defence.

**C. PR-AUC is not comparable across base rates.** Its no-skill floor IS the
base rate, and train/test rates differ. Print PR-AUC next to the test base rate
and report the lift. Comparing bare PR-AUC across seasons or regions with
different base rates is invalid.

**D. Threshold-scope sensitivity is required.** Evaluate under both `--by
region` and `--by gridpoint` and report whether the rule-5 verdict changes. For
this 2-year run region scope is the headline; gridpoint is a known-noisy
sensitivity.

---

## P11 — Ablations: what is the model actually using?

```
A single AUC does not tell you whether the model learned meteorology or just
learned that heavy rain has big errors. This prompt finds out. It is short and
it is the most likely source of a genuinely interesting slide.

Retrain and re-evaluate (stratified, always) under these variants:

  a. FULL model — all features
  b. WITHOUT precip_mean and precip_spread — can it predict busts at all when
     you take away "how hard it is raining"? If performance collapses to
     baseline, the model is riding the magnitude artefact and we must say so.
  c. SPREAD-ONLY — one feature, the baseline as a learned model rather than a
     ranking. Isolates how much comes from a better functional form versus
     from more information.
  d. WITHOUT `month` — ADDED 29 Aug after the rehearsal. Bust thresholds are
     fitted per (region, lead_day) and NOT per season, so monsoon days carry
     systematically more busts than winter ones: the rehearsal's Jan-Mar test
     window showed a 1.47% bust rate against 5.00% in training. That makes
     `month` a powerful predictor for exactly the "climatology, not
     meteorology" reason that made pooled ensemble spread look skilful. If
     dropping `month` barely moves the stratified score, the model is learning
     weather; if it collapses, the model is largely learning what season it is,
     and we must say so.
  e. WITHOUT the 850 hPa shear features — did P2's +60% transfer cost buy
     anything? This is a real question with a real budget attached, and the
     answer changes whether the full 5-year run should include them.

Also report permutation importance on the test set (not training importance,
which is biased toward high-cardinality features).

REPORT: one table, four rows, stratified AUC each. Then a plain-English
paragraph on what the model is actually keying on. If the answer is
unflattering, that is still the answer.
```

---

## P12 — Calibration (this is what makes it a *confidence* product)

```
Read the MODEL PLAN in CLAUDE.md, item 4.

The deliverable is a confidence indicator. An uncalibrated confidence
indicator is worse than useless — if the system says "20% chance of a bust"
it must be wrong about one time in five, or a forecaster cannot act on it.
Judges on a meteorology panel will know this. Most hackathon teams skip it,
which is exactly why doing it well is worth points.

1. Carve a VALIDATION slice out of the TRAINING window by time. Never touch
   test. Calibrating on test invalidates the test.
2. Fit isotonic regression (and Platt as a comparison) on validation.
3. Reliability diagram on the test set: predicted probability vs observed
   frequency, with counts per bin so sparse bins are visible.
4. Brier score, decomposed into reliability / resolution / uncertainty.
   Report all three. Resolution is the part that says the model is informative;
   reliability is the part that says it is honest.
5. Compare calibrated vs uncalibrated, and the baseline too.

ACCEPTANCE: a reliability curve close to the diagonal, and a Brier
decomposition table. Save the diagram to figures/ at 200 dpi, light
background, ready to paste into slides.
```

---

## P13 — SHAP and the confidence map (the demo)

```
The problem statement explicitly requires EXPLAINABLE output. This is not
optional polish; it is a stated requirement we can be marked against.

1. SHAP. Use TreeExplainer on a SAMPLE of test rows (a few thousand — TreeSHAP
   is slow and you do not need millions). Produce:
   - global feature importance
   - a breakdown for the highest-confidence bust predictions: WHY did the model
     flag this forecast?
   If shap does not support HistGradientBoostingClassifier cleanly, say so and
   switch to LightGBM rather than silently using a worse explainer. Report the
   substitution if you make it.

2. THE CONFIDENCE MAP — the actual deliverable, at last. Pick one held-out
   test date with a real forecast bust and render, for Day 1 to Day 10:
   - predicted bust probability over the 1252 land gridpoints
   - the observed rainfall and the ensemble forecast for the same day
   - where the model flagged and was right; where it flagged and was wrong
   Use the same visual language as figures/fig3_map.png (0.5 deg squares,
   sequential blue, light background, 200 dpi).

3. Save everything to figures/. These are demo assets — they need to survive
   being projected in a room.

CONSTRAINT: label every figure with its truth source and sample size. Every
number we show states that truth is IMD gauge observation.
```

---

## P14 — Meteorological metrics layer (integrates Paras's guide)

**Context:** Paras delivered `AI_Based_Forecast_Bust_Detection_Meteorological_Metrics_Guide`
(14 pp, 27 Aug). The five formulas are correct and the pedagogy is good, but
before implementing anything from it, read these corrections.

### Corrections to the guide — verified 27 Aug

| # | Issue | Correct version |
|---|---|---|
| 1 | §11 says "90% of all cases were correct" for H=60, M=20, FA=10, CN=10 | Accuracy is **70%** — (60+10)/100 |
| 2 | §11's example has an 80% event base rate | It therefore **cannot** illustrate the rare-event problem it is making. §2's example (H=20, M=5, FA=10, CN=65) has a 25% base rate, 85% accuracy, CSI 0.571, ETS 0.455 — use that one |
| 3 | §11 says ETS "should not be fabricated from only the four confusion-matrix counts" | **ETS is fully computable from the four counts.** `H_rand = (H+FA)(H+M)/N`. Only FSS needs the spatial fields |
| 4 | §6 never states the `H_rand` formula | State it, as above, so it is implementable |

**A gift hidden in correction 3:** compute ETS on the guide's own §11 example and
you get **0.118** against a CSI of **0.667**. That gap — a compact-looking score
collapsing once chance hits are removed — is the single best illustration of why
ETS exists, and it is sitting unused in the document.

### The structural issue to fix before coding

The guide frames every metric around **rainfall detection** ("when rain really
happened, did our model notice it?"). VISHWAS does not forecast rain. **It
forecasts busts.** There are two legitimate applications and they must never be
mixed in one table:

- **(A) Characterising GEFS.** Event = heavy rain. Answers "how good is the
  forecast India relies on?" Good context for the pitch; not our model's score.
- **(B) Evaluating our bust classifier.** Event = **a forecast bust**. H = we
  flagged it and it busted. M = it busted and we missed it. FA = we flagged it
  and the forecast was fine. This is the one that scores VISHWAS.

Also note §9 describes a *rule-based* system — watch the metrics degrade, declare
a bust — which is a different architecture from the supervised classifier in
CLAUDE.md. Do not let it redirect the implementation.

```
Read CLAUDE.md and the corrections above. Prerequisite: P10 done.

Write src/08_met_metrics.py — the meteorological verification layer.

1. APPLICATION (B) IS PRIMARY. Event = bust, as labelled by 06_label.py.
   Build H / M / FA / CN for the bust event on the TEST split.

2. OPERATING POINT. POD, FAR, CSI and ETS all need a binary decision, but our
   model emits a probability. This is the gap in the guide and it matters.
   - Choose the threshold on the VALIDATION slice, never on test.
   - Primary operating point: a FIXED ALERT RATE — flag the top 10% of cases by
     predicted probability. CLAUDE.md already asks for "precision within the
     top-10% flagged", so this is consistent with the stated success criterion.
   - Always print the threshold and the resulting alert rate next to the scores.

3. THE HEAD-TO-HEAD THAT MATTERS. Compare model vs the ensemble-spread baseline
   AT THE SAME ALERT RATE. Both flag exactly 10% of cases; the question is who
   catches more real busts. This is the cleanest, fairest comparison available
   and it is directly presentable:
       "Given the same alert budget a forecaster would tolerate, VISHWAS catches
        X% of busts against the incumbent method's Y%."
   Report POD, FAR, CSI, ETS for both, side by side, at matched alert rates.
   Also sweep the alert rate (5%, 10%, 20%) so the trade-off is visible.

4. STRATIFY WITHIN RAINFALL-MAGNITUDE BINS. The guide's §10 covers thresholds,
   lead time, region, season and leakage, but omits the one that has actually
   bitten this project: pooled evaluation flatters BOTH model and baseline
   through the wet/dry artefact. Report every metric pooled AND stratified, and
   mark the stratified table as the honest one.

5. UNCERTAINTY BY INIT DATE. The guide asks for confidence intervals but not for
   the right resampling unit. Gridpoints within one forecast are not independent.
   Cluster-bootstrap on init date — reuse cond.cluster_bootstrap from
   04_conditional.py rather than reimplementing.

6. KEEP ROC-AUC AND PR-AUC. They are threshold-free and CLAUDE.md names them as
   the success criterion; POD/FAR/CSI/ETS are threshold-dependent and describe
   one operating point. Report both families. They answer different questions
   and a judge will want both.

7. APPLICATION (A) AS A SEPARATE, CLEARLY LABELLED OUTPUT. Compute POD/FAR/CSI/
   ETS for GEFS rainfall itself (event = rain above a stated threshold) purely as
   context. Label it unmistakably as "the underlying forecast, not our model".
   Never place it in the same table as our scores.

8. FSS is OPTIONAL and last. It applies to the bust-probability field spatially,
   but our domain is land-only and irregular (1252 points), so neighbourhood
   sizes need care. Only attempt it after 1-7 are done, and if you do, always
   report grid resolution, threshold and neighbourhood size together.

ACCEPTANCE: one table, model vs baseline, matched alert rate, pooled and
stratified, with cluster-bootstrap intervals on the difference. State plainly
whether we beat the baseline.

CONSTRAINT: never report plain accuracy. The guide is right about this and it is
the first item in its own "Common Mistakes" list.
```

---

## Guardrails — paste into any Phase 2 session

```
- Split train/test BY TIME, never randomly.
- Any threshold, climatology, or calibration is fit on TRAIN ONLY and applied
  frozen to test. This project has already had two leaks of exactly this shape.
- Never report plain accuracy; the base rate is ~5%.
- Evaluate stratified within rainfall-magnitude bins. Pooled numbers flatter
  the model through the same artefact we accuse ensemble spread of.
- Bootstrap by init date, never by row.
- ALL features come from GEFS. IMD is truth only. error and bust are labels.
- No GPU. HistGradientBoostingClassifier is CPU-only by design.
- Never write a fallback that silently generates synthetic data.
- If the model does not beat spread, say so. An honest negative result scores
  better with meteorologist judges than an inflated claim.
```
## P15 — Get the machine ready for P8 landing (do this NOW, while it downloads)

```
Read CLAUDE.md first. P8 (the 2-year bulk fetch) is still running and lands
around 20:18 IST. This prompt makes sure the moment it lands, the whole chain
runs without a single surprise.

ALREADY DONE BY THE OTHER SESSION — DO NOT REDO ANY OF THIS:
  - src/06_label.py has been hardened (4 items) and unit-tested:
      * the fallback gate is now on EXPECTED EXCEEDANCES, not sample count
        (--min-exceedances, default 8; at the 95th pct that means >= 160 train
        samples, so this 2-year run correctly falls back to REGION scope)
      * a truth >= 0 assertion after the NaN filter
      * the dead colocation return removed
      * length guards on both fallback merges
  - src/07_model.py has been written and tested end to end on synthetic data.
    It implements P10 plus amendments A-D: train=2018 / test=2019, validation
    carved as every 4th Wednesday of 2018 and left untouched, study-window
    filter, PR-AUC reported as lift over base rate, both label scopes, and a
    verdict rule fixed before results are seen.
  - The four January-2000 smoke parts have been MOVED to
    data/features_parts/_smoke_jan2000/ so finalize()'s os.listdir glob cannot
    sweep them into the 2018 training window. Leave them there.

TASK 1 — FIX THE VENV. THIS IS THE BLOCKER.
scikit-learn is NOT installed in .venv, and src/07_model.py imports it on line
one. shap and properscoring are also missing. All three are in
requirements.txt, so the original install evidently predates those lines or
partly failed.

    source .venv/bin/activate
    pip install scikit-learn shap properscoring

Then PROVE the environment is complete, do not assume:

    python -c "import sklearn, shap, properscoring, imdlib, pandas, numpy, \
        pyarrow, xarray, cfgrib, s3fs; print('all imports OK')"
    python -c "import ast; [ast.parse(open(f).read()) for f in \
        ['src/06_label.py','src/07_model.py']]; print('syntax OK')"

If shap fails to build on Python 3.9, report it and move on — shap is only
needed for P13, not tonight. scikit-learn is non-negotiable.

TASK 2 — REHEARSE THE FULL CHAIN ON THE DATA ALREADY DOWNLOADED.
~54 of 104 dates are on disk right now. That is enough to exercise every code
path end to end. Do this BEFORE P8 finishes, so any integration bug surfaces
now rather than at 20:20 with everyone watching.

    python src/02_features.py --finalize --train-end 2018-12-31
    python src/06_label.py --train-end 2018-12-31 --by region
    python src/07_model.py --bootstrap 200

THE NUMBERS FROM THIS REHEARSAL ARE MEANINGLESS — the test period is whatever
sliver of 2019 has arrived, likely two dates. Do not record them, quote them,
or put them anywhere near the deck. You are testing PLUMBING. What you are
checking is:
  - finalize() reports only 2018/2019 dates, never 2000
  - 06_label.py's threshold gate prints "region" as the source for ~all rows
    (52 train samples is far below the 160 the 95th percentile needs)
  - the train bust rate is ~5% and the test rate is NOT ~5%
  - 07_model.py runs to completion and prints the splits table, the results
    table, the per-bin detail, and a verdict
  - no assertion trips anywhere

Fix anything that breaks. Report exactly what broke and what you changed.

TASK 3 — WHEN P8 LANDS (all 104 dates), RE-RUN FOR REAL.
The rehearsal overwrites data/features.parquet and data/labelled.parquet with
partial versions, so every step must be re-run once the fetch completes.
Confirm 104 dates first:

    wc -l < data/raw/manifest.jsonl        # includes 4 old smoke entries
    ls data/features_parts/*.parquet | wc -l   # must be 104

Then:

    python src/02_features.py --finalize --train-end 2018-12-31
    python src/06_label.py --train-end 2018-12-31 --by region
    python src/07_model.py --bootstrap 2000

REPORT, in this order:
  1. splits table — dates, rows, bust rate and seasonal composition for train /
     validation / test. Both train and test must carry all four seasons; say so
     explicitly, because a test set missing a season would invalidate every
     four-season claim we make.
  2. the results table — baseline vs model, pooled and stratified, PR-AUC and
     lift.
  3. the stratified margin with its cluster-bootstrap interval, and the verdict.
  4. the per-rainfall-bin detail.

INTERPRET IT HONESTLY. The pooled number will look far better than the
stratified one — that is expected and is the artefact this whole project
exists to expose. THE STRATIFIED NUMBER IS THE RESULT. If the model does not
beat ensemble spread, say so plainly; CLAUDE.md is explicit about this and the
measurement of the incumbent method stands on its own regardless.

CONSTRAINTS:
  - Do NOT run two 02_features.py processes at once. The manifest has no
    locking. P8 is still running until it is not — check before you finalize.
  - Do NOT tune the model, change the threshold percentile, adjust the bins, or
    alter the wet-point definition to improve a number. The decision rule was
    fixed before results were seen precisely so this cannot happen.
  - Do NOT report plain accuracy anywhere. The base rate is ~5%.
  - Never delete the _smoke_jan2000/ parts; they are excluded, not discarded.
```

