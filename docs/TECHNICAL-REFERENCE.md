# VISHWAS — Technical Reference

**For the session building the presentation.** Everything here is verified
against the live repository as of **30 Aug 2026** (consistency audit — see
`docs/CONSISTENCY-AUDIT.md`; the body was first written 29 Aug 17:52). Companion to
`docs/DECK-BRIEF.md`, which carries the framing, the safe claims and the
"do not claim" list. This document is the *engineering* picture: what the
system is, how it works, what is built, and what happens next.

Read `docs/DECK-BRIEF.md` first if you are writing slide copy. Read this one
if you are building an architecture slide, a methodology slide, a roadmap, or
answering a technical question from a judge.

---

## 1. What VISHWAS is, precisely

**VISHWAS does not forecast weather. It predicts when an existing forecast is
about to be badly wrong.**

Formally, it is a **supervised binary classifier over (gridpoint, lead day)**:

| | |
|---|---|
| **Input** | **23** features describing the state and the *disagreement* of a 11-member weather ensemble, for one gridpoint at one lead time |
| **Output** | calibrated probability that this forecast will "bust" |
| **Label** | `bust = |ensemble mean rainfall − observed rainfall| > 95th percentile` |
| **Domain** | India, 1,252 gauge-observed land gridpoints at 0.5° |
| **Horizon** | Day 1 to Day 10 (medium range) |

The product a forecaster would see is a **confidence map over India for each
lead day** — a companion layer to the forecast they already have, not a
replacement for it.

**Why this problem is not trivial:** a forecast can be wrong in a way the
forecast itself cannot know. The current professional practice is to read
*ensemble spread* — run the model 11 times from slightly different starting
conditions, and if the runs disagree, distrust the forecast. VISHWAS exists
because we measured that practice and found it carries almost no information
once you compare like with like.

---

## 2. Architecture — five stages

Draw this as a left-to-right pipeline. Each box is a real script in `src/`.

```
 ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
 │  1. FETCH       │   │  2. FEATURES    │   │  3. TRUTH       │
 │  01_fetch.py    │──▶│  02_features.py │──▶│  imd_truth.py   │
 │                 │   │                 │   │                 │
 │ NOAA GEFS v12   │   │ 11 members →    │   │ IMD gauge-      │
 │ reforecast,     │   │ mean + spread   │   │ gridded rain,   │
 │ public S3,      │   │ per field       │   │ 0.25°, exact    │
 │ byte-range      │   │ + derived       │   │ colocation to   │
 │ reads via .idx  │   │ physics         │   │ our 0.5° grid   │
 └─────────────────┘   └─────────────────┘   └─────────────────┘
                                                      │
        ┌─────────────────────────────────────────────┘
        ▼
 ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
 │  4. LABEL       │   │  5. MODEL       │   │  6. EVALUATE    │
 │  06_label.py    │──▶│  07_model.py    │──▶│  04_conditional │
 │                 │   │  (being written)│   │  08_met_metrics │
 │ error = |fcst − │   │                 │   │                 │
 │ obs|; bust =    │   │ HistGradient-   │   │ vs ensemble-    │
 │ >95th pct,      │   │ BoostingClass-  │   │ spread baseline │
 │ TRAIN-ONLY      │   │ ifier (CPU)     │   │ stratified +    │
 │ threshold       │   │ + calibration   │   │ SHAP + map      │
 └─────────────────┘   └─────────────────┘   └─────────────────┘
```

**The one-sentence version for a slide:** public ensemble forecast data in,
government gauge observations as ground truth, a learned confidence layer out.

---

## 3. The data — real numbers

### Forecast input: NOAA GEFS version 12 reforecast

| | |
|---|---|
| Source | `noaa-gefs-retrospective` public S3, anonymous, no credentials |
| Period available | 2000–2019 |
| Sampling | **Wednesdays only** — they carry 11 ensemble members; other days carry 5 |
| Members used | 11 (control + 10 perturbed) |
| Lead times | Day 1 to Day 10, daily |
| Per forecast date | 1,210 GRIB messages, **468 MB** |
| Currently downloading | 104 dates (2018–2019), **~51 GB**, ~3 h at 4.8 MB/s |

Only the needed bytes are fetched: each GRIB file ships an `.idx` sidecar
listing message offsets, so the pipeline issues HTTP range requests for exactly
the variables and lead times required, rather than downloading whole files.

### Ground truth: IMD gauge-gridded rainfall

| | |
|---|---|
| Source | India Meteorological Department, via `imdlib` |
| Resolution | 0.25°, daily, 1901–2024 |
| Size | ~25 MB per year — the entire truth archive is smaller than one forecast date |
| Coverage | land only; ocean and no-gauge cells stored as −999 |

**This is a deliberate and defensible choice.** The obvious alternative, ERA5
reanalysis, is a *model* product whose physics partly overlaps GEFS — scoring a
forecast against a reanalysis that assimilated similar physics flatters it. IMD
is **gauge observation**: actual rain gauges, from the Ministry that owns this
problem statement. It is the harder and more honest target.

### The analysis grid

- India box: **5°–40°N, 65°–100°E**, at 0.5° → **71 × 71 = 5,041 gridpoints**
- After the IMD land mask: **1,252 gridpoints (24.8%)** — this is the gauge
  domain, and the shrinkage is stated openly rather than hidden
- Rows per forecast date: 1,252 points × 10 lead days = **12,520**
- Two-year dataset: ~**1.3 million labelled rows**

---

## 4. The features — what the model sees

**23 features**, all derived from GEFS. **No feature is derived from the truth** —
that separation is enforced and is what makes the evaluation meaningful.

> **Corrected 30 Aug.** This section previously said "24 columns". The feature
> table `data/features.parquet` has 27 columns: 3 keys (`init`, `lat`, `lon`),
> plus 24 others — but `season` is built and never fed to the model, because
> `month` already carries the annual cycle. **The model sees 23**, and that is
> the number to quote. Verified against `models/vishwas_model.joblib`, which
> stores the 23 feature names in order.

| Feature | Meteorological meaning |
|---|---|
| `gh500_mean`, `gh500_spread` | 500 hPa geopotential height — the mid-atmosphere pressure pattern, ridges and troughs that steer weather systems |
| `u500_mean/spread`, `v500_mean/spread` | mid-level wind components |
| `wind500_speed` | mid-level wind strength |
| `gh500_gradient` | how sharply the pressure pattern changes per 100 km — strong gradients mean strong, fast-moving systems |
| `flow500_deformation` | stretching and shearing of the mid-level flow — where air masses are being pulled apart, a classic front-formation signal |
| `u850_mean`, `v850_mean` | low-level winds — the monsoon flow |
| `shear_500_850` | **true vertical wind shear** between 850 and 500 hPa — controls whether convection organises into large storms or stays scattered |
| `pwat_mean`, `pwat_spread` | precipitable water: total moisture in the air column — the fuel |
| `cape_mean`, `cape_spread` | convective available potential energy — atmospheric instability, thunderstorm potential |
| `precip_mean`, `precip_spread` | the ensemble's own rainfall forecast and its disagreement |
| `pwat_anomaly`, `cape_anomaly`, `precip_anomaly` | departures from climatology, fitted on the **training period only** |
| `month` | annual cycle. (`season` is also built into the feature table but is **not** a model input — it is redundant with `month`.) |
| `lead_day` | how far ahead the forecast reaches — a model input, not just an index |

**Every `_spread` column is the disagreement among the 11 ensemble members.**
That is the heart of the idea: the model does not only see what the atmosphere
is doing, it sees *where the ensemble cannot agree with itself*, and learns
which disagreements actually matter.

> **Slide-worthy detail:** the feature list says "wind shear", and an earlier
> version of the pipeline could only compute horizontal deformation at one
> level — which is a real predictor but is *not* vertical shear. Rather than
> mislabel it, the team fetched a second pressure level (850 hPa) at a 60%
> increase in data transfer, and kept both features under honest names. That
> is the standard of care throughout.

---

## 5. The label — what counts as a "bust"

```
error = | ensemble mean rainfall − IMD observed rainfall |     (mm)
bust  = error > 95th percentile of error
```

Everything hard is in "95th percentile **of what**".

- Computed **per gridpoint (or region) and per lead day** — a 30 mm error in
  Cherrapunji is routine; in Rajasthan it is a catastrophic failure. A single
  global threshold would simply relabel "wet places" as "bust-prone".
- Computed on the **training window only**, then frozen and applied to the test
  window. If the threshold saw the test data, every test row would help set the
  standard it is judged against.
- Base rate is therefore ~5% in training by construction. **The test base rate
  is deliberately not 5%** — that difference is the proof the split is honest.

---

## 6. The evaluation — the hard part, and the differentiator

This is where the project's real intellectual content sits, and it is what a
meteorologist judge will probe.

### The trap

Rank every gridpoint in India by ensemble spread and compare against error, and
spread looks excellent — correlation **+0.663**, explaining **43.9%** of the
variance. But most of that is geography, not skill: wet regions have both large
spread *and* large errors. A method that only knows "it rains a lot in Kerala"
would score similarly. That is climatology, not a confidence signal.

### The fix

Compare **within like rainfall conditions**. Split the data into ten bins by
forecast rainfall amount, measure the relationship inside each bin, and
recombine. The correlation collapses to **+0.041**, explaining **0.17%–0.90%**
of the variance depending on how a "wet point" is defined.

**Under 1%, however the data is sliced. That is the finding the project rests
on.** The same discipline is applied to the model itself: the headline model
score will be the stratified one, never the flattering pooled one.

### Baseline comparison at a matched alert budget

The clearest comparison, and it is now measured (P14, 30 Aug): let the model and
ensemble spread each flag the **same fraction** of forecasts — the riskiest 10% —
and ask which catches more real busts.

> *"Given the same number of alerts a forecaster would tolerate, VISHWAS catches
> **64%** of busts against the current method's **55%**."*

At that matched 10% budget: VISHWAS POD 0.641 / FAR 0.586 / CSI 0.336 /
ETS 0.300, against ensemble spread's POD 0.546 / FAR 0.647 / CSI 0.273 /
ETS 0.235. Stratified within rainfall magnitude, 19% against 15%. The operating
point was chosen on the **validation** slice, never on test. Full sweep at 5%,
10% and 20% in `docs/DECK-TECHNICAL-PACK.md` §4.

Because the theme is **Smart Automation**, false alarms are weighted more
heavily than missed events: an automated assistant that cries wolf gets
switched off, and then it helps nobody.

---

## 7. Methodological rigour — four things most teams get wrong

This is "why us" material. Each of these is a real defect that was found and
fixed in this project, not a generic best practice.

1. **Two data-leakage bugs found and fixed.** The climatology used for anomaly
   features was originally computed over training *and* test data together, so
   every test row's features encoded the test period's own average. It was
   caught, fixed, and *proven* fixed — the old code's signature was that every
   group's anomalies summed to exactly zero. A second leak of the same shape was
   pre-empted in the label threshold before it could be written.
2. **Uncertainty is measured by forecast date, not by row.** Two gridpoints
   50 km apart on the same day are nearly the same observation. Treating 77,425
   gridpoints as independent would produce a confidence interval far too narrow.
   The project resamples whole forecast dates instead.
3. **Statistical honesty about small samples.** A 95th percentile estimated from
   52 training dates rests on ~2.6 observations above the threshold. The
   pipeline gates on *expected exceedances*, not on a naive sample count, and
   falls back to a coarser reference population when the estimate would be noise.
4. **The negative results are reported.** An ensemble-size sensitivity test
   showed the baseline improves slightly with more members — which makes the
   project's own claim marginally weaker, and it is written down anyway. The
   governing rule in the project's constitution: *"If we cannot beat ensemble
   spread, say so."*

---

## 8. Status — what is built, running, and next

| Component | State |
|---|---|
| Data fetch (`01_fetch.py`) | ✅ working, resumable, survives being killed mid-download |
| Feature build (`02_features.py`) | ✅ working, features verified physically sane — 24 non-key columns built, **23 fed to the model** (`season` is not) |
| IMD truth (`imd_truth.py`) | ✅ verified independently, exact colocation proven |
| Baseline measurement (`03`, `04`, `05`) | ✅ complete — this is the headline result |
| Metrics library (`met_metrics.py`) | ✅ written and unit-tested |
| Label construction (`06_label.py`) | ✅ written, leak-audited |
| Bulk data download | ✅ complete — 104 forecast dates, 2018-2019, 50.3 GB fetched |
| **Model (`07_model.py`)** | ✅ **trained and evaluated; artifact at `models/vishwas_model.joblib`** |
| Ablations (`P11`) | ✅ five variants, `month` passed at -0.006 |
| Calibration (`10_calibration.py`) | ✅ isotonic on validation; reliability diagram `fig9` |
| SHAP (`09_shap.py`) | ✅ TreeSHAP, global + per-prediction; `fig7`, `fig8` |
| Confidence map (`08_demo_map.py`) | ✅ `fig6_confidence_map.png` |
| Meteorological metrics (`08_met_metrics.py`) | ✅ POD/FAR/CSI/ETS at a matched alert budget |

**The result, stated precisely.** Stratified ROC-AUC 0.728 against 0.565 for
ensemble spread, margin +0.1634 (95% CI +0.1080 to +0.1926). Quote the margin
as **+0.13 to +0.16**, never +0.163 alone. Never quote the pooled pair
(0.909 vs 0.885) as the result — it is the artefact this project exists to
expose. Never report plain accuracy: the base rate is ~6%.

---

## 9. Milestones

### Delivered

| Date | Milestone |
|---|---|
| 25 Aug | Data pipeline working end to end; GEFS layout mapped; first features built |
| 26 Aug | Truth source corrected from ERA5 reanalysis to IMD gauge observations |
| 27 Aug | Four-season baseline measured; leakage fixed; 850 hPa shear added; ensemble-size check done; labelling built |
| **29 Aug** | Bulk run complete — 104 dates, 50.3 GB, 1,302,080 labelled rows. **First trained model**, first honest comparison against the baseline, five ablations (`month` passed at −0.006) |
| **30 Aug** | Calibration (isotonic), explainability (SHAP), confidence map, operational metrics at a matched alert budget, model artifact persisted |

### Immediate

| Date | Milestone |
|---|---|
| **31 Aug** | **College internal PPT** |

### Toward submission

| Date | Milestone |
|---|---|
| Mid Sep | Extend to 5 years of training data (incremental — no re-downloading) |
| **20 Sep** | **SIH idea submission (6 slides)** |

### If selected

| Period | Milestone |
|---|---|
| Oct–Nov | Operational path on live forecasts; forecaster-facing confidence map; real Indian bust case study |
| Dec | **Grand Finale** |

---

## 10. Answers to the technical questions a judge will ask

**"Why NOAA GEFS and not NCMRWF's own NEPS?"**
NEPS reforecast archives are not publicly accessible. GEFS is the only publicly
archived medium-range ensemble with a ~20-year reforecast, which is what makes a
four-season, multi-year measurement possible at all. The method is
ensemble-agnostic and points at NEPS the day access exists.

**"Why is your domain smaller than India?"**
IMD's gridded rainfall is gauge-based, so it covers land only — 1,252 of 5,041
gridpoints. That is the observational domain, not a modelling shortcut, and
scoring against real gauges rather than a model reanalysis is the stronger
choice.

**"Only 11 ensemble members? Operational systems run more."**
Tested directly. Going from 5 to 11 members improves the baseline slightly and
does not change the conclusion. The effect is reported honestly rather than
assumed away, though 11 → 31 cannot be measured from this archive.

**"How do you know you are not just predicting heavy rain?"**
That is exactly what the stratified evaluation controls for, and it is why the
headline number is the within-rainfall-regime one (0.728 vs 0.565) rather than
the flattering pooled one. We also tested it directly: removing
the rainfall forecast from the model entirely did not hurt it — the score rose
slightly, 0.728 to 0.731.

**"What if the model does not beat the baseline?"**
It did, and the rule was fixed before we saw results — had it failed we would
have reported that instead. The measurement of the incumbent method stands on
its own and is a contribution regardless of what the model does.

---

## 11. Glossary for non-meteorologist slides

| Term | Plain English |
|---|---|
| **Ensemble** | Running the weather model ~11 times from slightly different starting conditions, because the atmosphere is chaotic and the starting state is never known exactly |
| **Ensemble spread** | How much those runs disagree. Today's confidence signal, and the thing we measured |
| **Forecast bust** | A forecast that is badly wrong — here, in the worst 5% of errors for that place and lead time |
| **Lead time** | How far ahead the forecast reaches. Day 1 is tomorrow; Day 10 is ten days out |
| **Medium range** | Roughly 3–10 days ahead — long enough to plan, short enough to be actionable |
| **Reforecast** | The same modern model re-run over past decades, so the historical record is consistent |
| **Calibration** | If the system says "20% chance of a bust", a bust should actually follow about one time in five. Without this, a confidence number is decoration |
| **Gauge-gridded** | Built from real rain gauges on the ground, not from another computer model |
