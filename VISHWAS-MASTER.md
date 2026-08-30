# VISHWAS — Master Document

**Team Hellfire Labs · SIH26079 · Ministry of Earth Sciences / NCMRWF**
**Theme: Smart Automation · Track: Software**

*Consolidated snapshot, 29 August 2026, 18:45 IST.*

---

> ## ⚠️ SUPERSEDED IN PART — read this before quoting anything below
>
> **This file is a snapshot taken BEFORE the model was trained.** It was
> accurate at 18:45 on 29 August and large parts of it are no longer true. It
> has deliberately NOT been patched line by line: more than half the document
> describes a pre-model state, and a half-corrected file where the reader
> cannot tell which half is current is more dangerous than a clearly labelled
> stale one.
>
> **`CLAUDE.md` is the authority for anything from Phase 2 onward.**
>
> Specifically superseded, do not quote from these:
> - **Part 0** in full — "where things stand", the live state, "the one
>   blocker", the landing sequence. The bulk download finished; there is no
>   blocker.
> - **Part 1 §8** status table — the model is trained, not "being written".
> - **Part 2 §1**, "Read this first: there is no model yet" — **wrong as of
>   29 August ~20:45.** The model is trained, ablated, calibrated and
>   explained. Its heading and every claim under it are false now.
> - **Part 2 §3** — still correct for the Phase 1 baseline numbers, but it
>   predates every model number. Add nothing from it about the classifier.
> - **Part 2 §4**, the bullet "no accuracy figure — for the model (none
>   exists)": the *metric* rule still stands (never report plain accuracy at a
>   ~6% base rate); the parenthetical "(none exists)" is stale.
> - **Part 2 §6** assets list — predates fig4 (regenerated), fig6, fig7, fig8,
>   fig9, and the deletion of fig5.
> - **Part 3** in full — a work plan for P8-P15, all of which have been done.
>
> Still reliable: Part 1 §§1-7 and §§9-11 (what the system is, architecture,
> data, features, label, evaluation design, glossary), and the Phase 1
> measurement numbers in Part 2 §3.
>
> **Recommendation: regenerate this file from `CLAUDE.md` rather than editing
> it.** Flagged 30 August 2026.

---

## How to use this document

This is everything in one file: what the system is, what has been measured,
what is running, what to do next, and every prompt still to be executed.

The individual files in the repository remain the **working copies** and will
drift ahead of this snapshot. If they disagree, they win:

| File | What it is |
|---|---|
| `CLAUDE.md` | The project constitution. Read before touching any code. Authoritative on data, honesty rules and leakage. |
| `data/VISHWAS-HANDOFF.md` | Team-facing state and deadlines. |
| `docs/TECHNICAL-REFERENCE.md` | The engineering picture, for building technical slides. |
| `docs/DECK-BRIEF.md` | Framing, safe claims, and the "do not claim" list. |
| `docs/CLAUDE-CODE-PROMPTS.md` | Phase 1 prompts, P1–P7 (complete). |
| `docs/PROMPTS-PHASE2-MODEL.md` | Phase 2 prompts, P8–P15 (in progress). |

**Reading paths:** just landed on the project → Part 0, then Part 1.
Building slides → Part 2, then Part 1 §2–6 for the technical slides.
Writing code → Part 0's landing sequence, then Part 3.
Answering a judge → Part 2 §4–5 and Part 1 §10.

---

## Part 0 — Where things stand right now

### Deadlines

| Date | What | Days away |
|---|---|---|
| **31 Aug 2026 (Mon)** | College internal PPT | **2** |
| 20 Sep 2026 | SIH idea submission, 6 slides | 22 |
| Dec 2026 | Grand Finale, if selected | — |

### The one-line status

**The measurement is complete and verified. The model does not exist yet.**
Data for it is downloading now and lands around 20:13 tonight; the code to
train it is written, tested, and waiting.

### Live state, 18:45 IST

```
P8 bulk fetch   [##################................] 56/104  (54%)
                27.3 GB of ~51 GB · 4.45 MB/s · ETA 20:13
```

| Component | State |
|---|---|
| Data fetch `01_fetch.py` | ✅ working, resumable, survives SIGKILL mid-download |
| Feature build `02_features.py` | ✅ 24 features, verified physically sane |
| IMD truth `imd_truth.py` | ✅ independently verified against raw `.grd` bytes |
| Baseline measurement `03/04/05` | ✅ complete — **this is the headline result** |
| Metrics library `met_metrics.py` | ✅ written, self-test passes |
| Label construction `06_label.py` | ✅ written, leak-audited, hardened |
| Model `07_model.py` | ✅ **written and tested — not yet run on real data** |
| **Bulk data** | 🔄 **downloading, ETA 20:13** |
| Trained model | ⬜ **none yet — no accuracy figure exists** |
| Calibration, SHAP, confidence map | ⬜ next, after the model |

> ⛔ **EVERY ROW OF THIS TABLE FROM `07_model.py` DOWN IS STALE.** As of
> 29–30 Aug: the bulk download finished (104 dates, 50.3 GB), the model is
> trained and evaluated, and calibration, SHAP and the confidence map are all
> done. See `CLAUDE.md` or `docs/DECK-TECHNICAL-PACK.md`. The table is left
> unedited because this whole file is a pre-model snapshot — see the banner at
> the top. The feature count "24" is also wrong; the model uses **23**.

### ⚠️ The one blocker

**`scikit-learn` is not installed in `.venv`.** `07_model.py` imports it on
line one and will fail instantly. `shap` and `properscoring` are missing too.
All three are in `requirements.txt`, so the original install predates those
lines or partly failed.

```bash
source .venv/bin/activate
pip install scikit-learn shap properscoring
```

Everything else is ready: `imdlib`, pandas, numpy, pyarrow, xarray, cfgrib and
s3fs are all present, and there is 123 GB of disk headroom against ~25 GB still
to download.

### The landing sequence

Once all 104 dates are down:

```bash
python src/02_features.py --finalize --train-end 2018-12-31
python src/06_label.py    --train-end 2018-12-31 --by region
python src/07_model.py    --bootstrap 2000
```

About two minutes of compute. Measured at full scale: the climatology transform
takes 4.0 s over 5.24M rows, and the truth join 12.2 s.

### Decisions already made, so nobody relitigates them

| Decision | Why |
|---|---|
| **Truth = IMD gauge rainfall**, not ERA5 | ERA5 is a model product whose physics partly overlaps GEFS. IMD is real gauges, from the Ministry that owns the problem statement. |
| **Train 2018 / test 2019** (`--train-end 2018-12-31`) | Both blocks then carry an identical, complete seasonal composition (DJF 13, MAM 13, JJAS 17, ON 9). A 60/20/24 split by index would have produced a test set with **zero MAM dates**. |
| **Region-scope bust thresholds** for this run | A 95th percentile from 52 training dates rests on 2.6 exceedances. Gridpoint scope becomes primary once 5 years of data exist. |
| **Validation = every 4th Wednesday of 2018** | Seasonally spread, inside the training window, so the test year is never touched. The tail of 2018 would give an ON/DJF-only validation set. |
| **lat/lon/region excluded from features** by default | Under region-scope labels the model could learn "this cell busts more than its region average" — climatology, not meteorology. `--with-location` is the documented sensitivity. |
| **2 years first, not 5** | The manifest is resumable and `--years` filters by cutoff, so extending later refetches nothing. |
| **No GPU, ever** | `HistGradientBoostingClassifier` has no GPU code path. The full archive bins to ~1.15 GB. |

---

## Part 1 — The system, technically

*Architecture, data, features, label, evaluation design, and the rigour that
differentiates this project. Source: `docs/TECHNICAL-REFERENCE.md`.*

---

### 1. What VISHWAS is, precisely

**VISHWAS does not forecast weather. It predicts when an existing forecast is
about to be badly wrong.**

Formally, it is a **supervised binary classifier over (gridpoint, lead day)**:

| | |
|---|---|
| **Input** | ~24 features describing the state and the *disagreement* of a 11-member weather ensemble, for one gridpoint at one lead time |
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

### 2. Architecture — five stages

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

### 3. The data — real numbers

#### Forecast input: NOAA GEFS version 12 reforecast

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

#### Ground truth: IMD gauge-gridded rainfall

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

#### The analysis grid

- India box: **5°–40°N, 65°–100°E**, at 0.5° → **71 × 71 = 5,041 gridpoints**
- After the IMD land mask: **1,252 gridpoints (24.8%)** — this is the gauge
  domain, and the shrinkage is stated openly rather than hidden
- Rows per forecast date: 1,252 points × 10 lead days = **12,520**
- Two-year dataset: ~**1.3 million labelled rows**

---

### 4. The features — what the model sees

24 columns, all derived from GEFS. **No feature is derived from the truth** —
that separation is enforced and is what makes the evaluation meaningful.

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
| `month`, `season` | annual cycle |

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

### 5. The label — what counts as a "bust"

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

### 6. The evaluation — the hard part, and the differentiator

This is where the project's real intellectual content sits, and it is what a
meteorologist judge will probe.

#### The trap

Rank every gridpoint in India by ensemble spread and compare against error, and
spread looks excellent — correlation **+0.663**, explaining **43.9%** of the
variance. But most of that is geography, not skill: wet regions have both large
spread *and* large errors. A method that only knows "it rains a lot in Kerala"
would score similarly. That is climatology, not a confidence signal.

#### The fix

Compare **within like rainfall conditions**. Split the data into ten bins by
forecast rainfall amount, measure the relationship inside each bin, and
recombine. The correlation collapses to **+0.041**, explaining **0.17%–0.90%**
of the variance depending on how a "wet point" is defined.

**Under 1%, however the data is sliced. That is the finding the project rests
on.** The same discipline is applied to the model itself: the headline model
score will be the stratified one, never the flattering pooled one.

#### Baseline comparison at a matched alert budget

The clearest comparison, and the one to put on a slide once the model exists:
let the model and ensemble spread each flag the **same fraction** of forecasts —
say the riskiest 10% — and ask which catches more real busts.

> *"Given the same number of alerts a forecaster would tolerate, VISHWAS catches
> X% of busts against the current method's Y%."*

Because the theme is **Smart Automation**, false alarms are weighted more
heavily than missed events: an automated assistant that cries wolf gets
switched off, and then it helps nobody.

---

### 7. Methodological rigour — four things most teams get wrong

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

### 8. Status — what is built, running, and next

| Component | State |
|---|---|
| Data fetch (`01_fetch.py`) | ✅ working, resumable, survives being killed mid-download |
| Feature build (`02_features.py`) | ✅ working, 24 features verified physically sane |
| IMD truth (`imd_truth.py`) | ✅ verified independently, exact colocation proven |
| Baseline measurement (`03`, `04`, `05`) | ✅ complete — this is the headline result |
| Metrics library (`met_metrics.py`) | ✅ written and unit-tested |
| Label construction (`06_label.py`) | ✅ written, leak-audited |
| **Bulk data download** | 🔄 **running now — 27 of 104 dates, ETA 20:06 today** |
| **Model (`07_model.py`)** | ⬜ **being written — no trained model yet** |
| Calibration, SHAP, confidence map | ⬜ next, after the model |

**Be precise about this on slides: there is no accuracy number yet.** The
measurement is complete and verified; the model is in progress. Claiming
otherwise would violate the project's own honesty rules and is exactly the
thing a technical judge catches.

---

### 9. Milestones

#### Delivered

| Date | Milestone |
|---|---|
| 25 Aug | Data pipeline working end to end; GEFS layout mapped; first features built |
| 26 Aug | Truth source corrected from ERA5 reanalysis to IMD gauge observations |
| 27 Aug | Four-season baseline measured; leakage fixed; 850 hPa shear added; ensemble-size check done; labelling built |

#### Immediate

| Date | Milestone |
|---|---|
| **27 Aug, ~20:00** | 2-year dataset complete (~1.3M labelled rows) |
| **28 Aug** | First trained model; first honest comparison against the baseline |
| **29 Aug** | Team inputs due for the internal deck |
| **31 Aug** | **College internal PPT** |

#### Toward submission

| Date | Milestone |
|---|---|
| Early Sep | Calibration, explainability (SHAP), meteorological metrics at matched alert budget |
| Mid Sep | Extend to 5 years of training data (incremental — no re-downloading) |
| **20 Sep** | **SIH idea submission (6 slides)** |

#### If selected

| Period | Milestone |
|---|---|
| Oct–Nov | Operational path on live forecasts; forecaster-facing confidence map; real Indian bust case study |
| Dec | **Grand Finale** |

---

### 10. Answers to the technical questions a judge will ask

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
headline number is the within-rainfall-regime one rather than the pooled one
that would look four times better.

**"What if the model does not beat the baseline?"**
Then we report that. The measurement of the incumbent method stands on its own
and is a contribution regardless of what the model does.

---

### 11. Glossary for non-meteorologist slides

| Term | Plain English |
|---|---|
| **Ensemble** | Running the weather model ~11 times from slightly different starting conditions, because the atmosphere is chaotic and the starting state is never known exactly |
| **Ensemble spread** | How much those runs disagree. Today's confidence signal, and the thing we measured |
| **Forecast bust** | A forecast that is badly wrong — here, in the worst 5% of errors for that place and lead time |
| **Lead time** | How far ahead the forecast reaches. Day 1 is tomorrow; Day 10 is ten days out |
| **Medium range** | Roughly 3–10 days ahead — long enough to plan, short enough to be actionable |
| **Reforecast** | The same modern model re-run over past decades, so the historical record is consistent |
| **Calibration** | If the system says "20% chance of a bust", it should be wrong about one time in five. Without this, a confidence number is decoration |
| **Gauge-gridded** | Built from real rain gauges on the ground, not from another computer model |


---

## Part 2 — Results, framing, and what must not be claimed

*Read this before writing a single slide. Source: `docs/DECK-BRIEF.md`.*

---

### 1. ~~Read this first: there is no model yet~~ — ⛔ FALSE SINCE 29 AUG

> **DO NOT QUOTE THIS SECTION.** The model was trained on 29 August at ~20:45
> and every claim below it is now wrong. Stratified ROC-AUC **0.728 against
> ensemble spread's 0.565**, margin +0.1634 (95% CI +0.1080 to +0.1926), ahead
> in all 8 rainfall bins. Ablations, calibration, SHAP and the confidence map
> are all complete. Go to `CLAUDE.md` or `docs/DECK-TECHNICAL-PACK.md`.
> The original text is preserved below only as a record of what was true on
> 29 August at 18:45.

The project has **no trained model, no accuracy figure, no ROC-AUC, no PR-AUC.**
Do not put one on a slide, and do not let anyone assume one exists.

What exists is something rarer and, for this deck, stronger: **a measurement.**
Most SIH teams pitch a plan. This team measured the method that professional
forecasters use today and found it barely works. That is the spine of the deck.

The model is in progress — data is downloading now, first results expected in
the next few days. If a slide must mention it, "in progress, results by
[date]" is the honest form.

---

### 2. The theme changed, and it changes the pitch

SIH originally listed **SIH26079** under **Disaster Management**, then re-listed
it under **Smart Automation**. Smart Automation is current and governs the
submission. Any older material framed around floods and lives saved is now
off-theme.

**This is good news.** The result is an automation argument almost word for
word:

> Forecasters judge confidence today by eyeballing ensemble spread. We measured
> that manual judgement against India's own gauge observations, across all four
> seasons, and it explains under 1% of forecast error. We are not automating a
> task that already works — we are automating a judgement that currently has no
> evidence behind it.

That is a better story than the disaster-management version, which would have
required lives-saved estimates the team cannot substantiate.

#### Two consequences that need action

**a) Dhruv's cost-of-failure figures need re-angling.** They were gathered for a
disaster-impact framing (damage, lives, flood losses). Under Smart Automation
the relevant cost is **forecaster time and operational decision quality** — how
long a duty forecaster spends assessing confidence manually, how often a
low-confidence forecast is acted on as if it were reliable, what a wrong
operational call costs a user (power scheduling, agriculture advisories,
aviation). Ask him for that, with citations, not for disaster damage totals.

**b) Operational viability now needs a slide.** Automation implies something
that runs inside a workflow. The problem owner is **NCMRWF**, an operational
forecasting centre. "Could this run at NCMRWF tomorrow?" is likely scored.
The technical work has a live-forecast path; it needs to be shown, not called
optional.

---

### 3. The numbers — verified, and the only ones that may be quoted

Truth is **IMD gauge-gridded rainfall** (the Ministry's own product, land
only), 12 forecast dates spanning **all four seasons and three years**
(2012/2015/2018), 77,425 wet samples, Day 1–10.

| | value |
|---|---|
| Spread–error correlation, pooled across India | **+0.663** |
| Same, compared within like rainfall conditions | **+0.041** |
| Variance in forecast error explained, pooled | **43.9%** |
| Variance explained, fair comparison | **0.17% – 0.90%** |

**The safest headline, robust to every analyst choice:**

> Ensemble spread appears to explain 44% of the variance in forecast error.
> Once you control for how hard it is raining, it explains **under 1%**.

Use the variance framing, not a bare correlation. It survives hostile
questioning because it holds however the analysis is sliced.

**A second, stronger finding worth its own beat:** when the ensemble is
confidently dry and it rains anyway, spread points the *wrong* way — it is
actively misleading, not merely uninformative. That names a specific failure
mode a forecaster could act on.

---

### 4. What must NOT be claimed

- **Never quote +0.663 as "the baseline we beat."** It is the artefact, not the
  signal. Quoting it would overstate the incumbent method.
- **Never quote +0.041 alone.** It rests heavily on one slice of the data;
  under other reasonable definitions it is nearer +0.09. Use the variance range
  (under 1%) instead, which is stable either way.
- **No seasonal slide.** Which season looks best reverses depending on analysis
  choices, and there are only three dates per season. There is no reliable
  seasonal story yet.
- **No accuracy figure of any kind** — for the model (none exists) or as a
  metric (the events are rare, so accuracy is meaningless and quoting it signals
  the team does not understand imbalance).
- **We detect busts, we do not correct forecasts.** Any "AI-adjusted forecast"
  wording is wrong and promises something not being built.
- **Do not call the regions "IMD official regions."** They are approximate
  latitude/longitude boxes.

---

### 5. The question a judge will ask first — have the answer ready

**"You used NOAA GEFS. NCMRWF runs its own ensemble. Why?"**

The problem owner operates India's operational medium-range system (NCUM/NEPS).
This project detects busts in an American ensemble instead. The answer is good,
but it must be given proactively rather than extracted:

> NEPS reforecast archives are not publicly accessible. GEFS is the only
> publicly archived medium-range ensemble with a ~20-year reforecast, which is
> what makes a four-season, multi-year measurement possible at all. The method
> is ensemble-agnostic — it points at NEPS the day we have access.

Put this on a slide or in the appendix. Being seen to have anticipated it is
worth more than the answer itself.

---

### 6. Assets ready to use

Three figures, 200 dpi, built from the real data, in `figures/`:

- `fig1_collapse.png` — 43.9% vs 0.90%, the headline. One bar towering over one
  almost invisible bar.
- `fig2_deciles.png` — the proof: within every rainfall regime, spread carries
  almost nothing. Includes the "confidently dry and wrong" failure mode.
- `fig3_map.png` — where India's forecasts go wrong, over the 1,252
  gauge-observed land gridpoints. Makes the product concrete.

Every figure already carries its truth source and sample size. Keep those
captions; they are what make the numbers credible.

---

### 7. One-liners that hold up

**Opening:** every forecast India issues arrives with no honesty label. VISHWAS
predicts when the forecast will be wrong.

**The differentiator:** most teams pitch a hypothesis. We pitch a measurement.

**Non-technical:** Google Maps says 25 minutes, and sometimes you sit in traffic
for an hour. Imagine it also said "I'm not confident about this one." That's
VISHWAS, for weather.

**If asked whether it works yet:** we have proven the problem is real and the
incumbent method is weak. The model is being trained now, and we will report
what it does — including if it fails to beat the baseline.


---

## Part 3 — The work plan and every remaining prompt

*Phase 1 (P1–P7) is complete: data pipeline, IMD truth verification, 850 hPa
wind shear, the four-season baseline measurement, the climatology-leak fix, and
the ensemble-size sensitivity check. What follows is Phase 2 — turning the
measurement into a model. Source: `docs/PROMPTS-PHASE2-MODEL.md`.*

---

### 0. Order of work — read this first

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

#### The one design decision to make before P9

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

### P8 — Bulk run, two years first

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

### P9 — Label construction (`src/06_label.py`) — THE MISSING LINK

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

### P9 hardening — independent review, 29 Aug — ALL FOUR APPLIED

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

### P10 — Baseline, model, and the honest evaluation (`src/07_model.py`)

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

#### P10 amendments A-D — all implemented in `src/07_model.py`

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

### P11 — Ablations: what is the model actually using?

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
  d. WITHOUT the 850 hPa shear features — did P2's +60% transfer cost buy
     anything? This is a real question with a real budget attached, and the
     answer changes whether the full 5-year run should include them.

Also report permutation importance on the test set (not training importance,
which is biased toward high-cardinality features).

REPORT: one table, four rows, stratified AUC each. Then a plain-English
paragraph on what the model is actually keying on. If the answer is
unflattering, that is still the answer.
```

---

### P12 — Calibration (this is what makes it a *confidence* product)

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

### P13 — SHAP and the confidence map (the demo)

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

### P14 — Meteorological metrics layer (integrates Paras's guide)

**Context:** Paras delivered `AI_Based_Forecast_Bust_Detection_Meteorological_Metrics_Guide`
(14 pp, 27 Aug). The five formulas are correct and the pedagogy is good, but
before implementing anything from it, read these corrections.

#### Corrections to the guide — verified 27 Aug

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

#### The structural issue to fix before coding

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

### Guardrails — paste into any Phase 2 session

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
### P15 — Get the machine ready for P8 landing (do this NOW, while it downloads)

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