# VISHWAS — Technical Pack for the Deck (v2)

**Team Hellfire Labs · SIH26079 · Ministry of Earth Sciences / NCMRWF**
**Theme: Smart Automation · Track: Software**

*Rewritten 30 Aug 2026 by the technical session. Supersedes every earlier
version. All work is complete; every number below is final and verified against
the live repository.*

**Deadlines:** internal college PPT **Mon 31 Aug** · SIH idea submission,
6 slides, **20 Sep**.

---

## ~~0. THREE FIXES NEEDED IN THE EXISTING DECK~~ — ✅ ALL THREE DONE

> **RESOLVED 30 Aug 15:59 (deck v17).** Re-verified by unzipping the shipping
> deck and hashing its media: slide 3 carries `fig6_confidence_map.png`, slide 4
> carries the regenerated `fig4_inversion.png`, both byte-identical to
> `figures/`, and slide 6 now reads *"the 651,040-row 2019 test set drawn from a
> 1,302,080-row labelled table"*. Zero orphaned media, no `fig5`.
> **Nothing in this section is outstanding.** Kept for provenance.

`deck/VISHWAS_SIH.pptx` embeds two outdated figures. Verified by unzipping the
file and byte-matching its media against `figures/`.

**Slide 3 — replace with `figures/fig6_confidence_map.png`.**
The embedded image has a **wrong date burned into it**: "initialised 26 July
2019, valid 31 July". The real forecast is init **31 July 2019, valid 5 August,
Day 5**. 26 July 2019 was a Friday; every forecast in this study is a Wednesday,
so the date does not exist in the data. A judge can check that in ten seconds.
**This is not a file swap** — fig6 has three panels where the old one had two,
and a different aspect ratio. The slide needs relaying out.

**Slide 4 — replace with the regenerated `figures/fig4_inversion.png`.**
The old version printed "+0.163" alone in 40pt type; the rule is to quote
**+0.13 to +0.16**. The new version shows the confidence interval as an error
bar and states the correct sample size.

**Slide 6 — reword.** "0.728 from 1,302,080 labelled gridpoint-days" conflates
two numbers. 0.728 is measured on the **651,040-row test set**, which is part of
a 1,302,080-row labelled table.

---

## 1. Status — everything is final

| | |
|---|---|
| Baseline measurement | ✅ final |
| Trained model | ✅ final — the `month` ablation passed, nothing is provisional |
| Ablations (5) | ✅ final |
| Calibration | ✅ final |
| Explainability (SHAP) | ✅ final |
| Confidence map | ✅ final |
| Operational metrics (POD/FAR/CSI/ETS) | ✅ final |
| Model artifact | ✅ `models/vishwas_model.joblib`, reproduces predictions exactly |

Nothing is pending. Nothing was tuned. Every decision rule was fixed before
results were seen.

---

## 2. The story — the spine of the deck

**One sentence:** every weather forecast India issues arrives with no honesty
label; VISHWAS predicts when the forecast is about to be badly wrong.

Four beats, in this order.

**Beat 1 — The method forecasters use today barely works.**
Professional forecasters judge confidence by *ensemble spread*: run the model 11
times from slightly different starting conditions, and if the runs disagree,
distrust the forecast. Measured against India's own rain gauges across all four
seasons: compared crudely it looks strong; compared fairly — within like
rainfall conditions — it explains **under 1% of forecast error**.

**Beat 2 — We built the replacement, and it works.**
Trained on 2018, tested on all of 2019. On the fair comparison, **0.728 against
the incumbent's 0.565**, ahead in every rainfall regime.

**Beat 3 — The comparison that favours us is the honest one.**
Compared crudely, our model beats the current method by a forgettable +0.023.
Compared *fairly*, the gap is **seven times larger**. Crude scoring hands
ensemble spread most of its apparent skill for free by letting it track how hard
it is raining. **Most projects' numbers shrink under scrutiny. Ours grows**,
because the scrutiny removes an advantage the incumbent never earned.

**Beat 4 — And in operational terms:**
> *Given the same number of alerts a forecaster would tolerate, VISHWAS catches
> **64% of busts against the current method's 55%**.*

**Why this differs from every other SIH project:** most pitch a hypothesis. This
pitches a *measurement* — of the incumbent, then of the replacement, both
against gauge observations, with confidence intervals and negative results
reported.

---

## 3. Suggested slide structure

### Internal PPT, Monday (~12 slides)

| # | Slide | Content |
|---|---|---|
| 1 | Title | VISHWAS — Forecast Confidence Intelligence. विश्वास = "confidence". |
| 2 | The problem | A forecast can be wrong in ways the forecast itself cannot know. |
| 3 | What forecasters do today | Ensemble spread, in plain terms. The incumbent. |
| 4 | **We measured it** | 43.9% → under 1%. `fig1_collapse.png` |
| 5 | Why it collapses | Geography, not confidence. `fig2_deciles.png` |
| 6 | What VISHWAS is | Pipeline diagram (§5) |
| 7 | **The result** | 0.565 vs 0.728, and the inversion. `fig4_inversion.png` |
| 8 | **What a forecaster gets** | `fig6_confidence_map.png` — three panels |
| 9 | **The case the old method cannot even rank** | `fig8_shap_cases_driest.png` — see §6, this is your strongest slide |
| 10 | Operational numbers | 64% vs 55% at matched alert budget; calibration |
| 11 | Rigour | §8 — the "why trust us" slide |
| 12 | Roadmap + team | §9 |

### SIH submission, 6 slides

(1) Problem · (2) **The measurement** — beats 1 and 3 · (3) Solution and
architecture · (4) Result, robustness and the driest-bin case ·
(5) Feasibility and impact · (6) Team and roadmap.

---

## 4. Every number

### The baseline measurement

| | value |
|---|---|
| Spread–error correlation, pooled | +0.663 |
| Within like rainfall conditions | +0.041 |
| Variance explained, pooled | **43.9%** |
| Variance explained, fair comparison | **0.17%–0.90%** |

> **Safest phrasing:** "Ensemble spread appears to explain 44% of the variance
> in forecast error. Once you control for how hard it is raining, it explains
> **under 1%**."

### The model

Trained on 2018 (39 dates fitted, 13 held as validation), tested on **all 52
Wednesdays of 2019**. 1,302,080 labelled gridpoint-days; **651,040 in the test
set**. Truth: IMD rain gauges.

| | ensemble spread | VISHWAS |
|---|---|---|
| **ROC-AUC, within like rainfall conditions** | **0.565** | **0.728** |
| PR-AUC lift over base rate | 6.29× | 7.60× |

> **The pooled ROC-AUC row was removed on 30 Aug.** It is Q&A-only and belongs
> in no results table — see §7. The crude margin is **+0.023**, which is all the
> deck needs in order to tell the inversion story.

- Margin **+0.163**, 95% CI **+0.108 to +0.193** — entirely above zero.
- **Quote the margin as +0.13 to +0.16**, never +0.163 alone.
- Ahead in **all 8 rainfall bins**, by +0.079 to +0.252.
  - *Why eight and not ten:* the code asks for deciles of forecast rainfall, but
    ~32% of test rows have a forecast of exactly 0.00 mm, so three quantile
    edges coincide and are dropped. The realised count is **8**, and bin 0
    absorbs the whole zero block — 208,065 rows at a 0.15% bust rate, against
    bin 7's 40.92%. **Say "eight bins", never "deciles" or "the wettest tenth",
    for the model result.** (Deciles *are* correct for the Phase 1 conditional
    correlation, which is a different analysis on a different sample.)
- Largest edge in the driest conditions (0.835 vs 0.583).
- Still +0.097 in the heaviest-rain bin, where 41% of forecasts bust.

### Operational metrics — at a matched alert budget

Both systems flag exactly the same fraction of forecasts. Operating point chosen
on the validation slice, never on test.

| budget | | POD | FAR | CSI | ETS |
|---|---|---|---|---|---|
| 5% | VISHWAS | **0.454** | 0.413 | 0.344 | 0.318 |
| | spread | 0.363 | 0.530 | 0.258 | 0.230 |
| **10%** | **VISHWAS** | **0.641** | **0.586** | **0.336** | **0.300** |
| | spread | 0.546 | 0.647 | 0.273 | 0.235 |
| 20% | VISHWAS | **0.791** | 0.744 | 0.240 | 0.191 |
| | spread | 0.748 | 0.758 | 0.224 | 0.174 |

ΔPOD **+0.093** (CI +0.071 to +0.110). Every interval excludes zero.
Stratified within rainfall magnitude: **19% against 15%**.

### Ablations — what the model is really using

| variant | stratified AUC |
|---|---|
| Full model | 0.728 |
| Without `month` | 0.722 |
| **Without the rainfall forecast** | **0.731** — *slightly better* |
| Without 850 hPa shear | 0.726 |
| Ensemble spread only | 0.562 |

Two of these are slide-worthy on their own:
- **Removing the rainfall forecast entirely makes it slightly better.** The
  "you're just predicting heavy rain" objection is dead on evidence.
- **A model given only ensemble spread scores 0.562, against 0.565 for spread
  as a plain ranking.** None of the edge comes from the algorithm being clever;
  all of it comes from having more information.

### Calibration

| | Brier | reliability ↓ | resolution ↑ | skill score |
|---|---|---|---|---|
| VISHWAS + isotonic | 0.04217 | 0.00006 | **0.01758** | **+0.303** |
| ensemble spread + isotonic | 0.04749 | 0.00012 | 0.01225 | +0.215 |

**Resolution 1.4× the incumbent's** — that is the component measuring
informativeness. Calibration does not change the ranking, so the AUC is
unaffected; what changes is whether the number attached to it can be believed.

### The underlying forecast — context, NOT our model

| event | POD | FAR | CSI | ETS |
|---|---|---|---|---|
| rain ≥ 2.5 mm | 0.822 | 0.526 | 0.429 | 0.308 |
| rain ≥ 15.6 mm | 0.393 | 0.615 | 0.241 | 0.208 |
| **rain ≥ 64.5 mm (heavy)** | **0.060** | 0.677 | 0.053 | 0.052 |

> **Highly quotable:** GEFS detects **23% of heavy-rain events at Day 1, and
> 0.2% at Day 10**. That is the problem VISHWAS exists to flag.

Keep this in its own table, clearly labelled "the underlying forecast, not our
model". Never mix it with our scores.

### Scale

| | |
|---|---|
| Forecast data processed | **50.3 GB**, 104 forecast dates |
| Labelled dataset | **1,302,080** gridpoint-days (**651,040** test) |
| Domain | **1,252** gauge-observed land gridpoints |
| Horizon | Day 1 to Day 10 · **11 ensemble members** |

---

## 5. Architecture — for the technical slide

```
  GEFS ensemble          Feature build           IMD gauge truth
  forecast archive  ──▶  11 members become  ──▶  exact colocation
  (public, 50 GB)        mean + disagreement      onto our grid
                         per weather field
                                │
        ┌───────────────────────┘
        ▼
  Label: was this      Model: learned          Evaluate against
  forecast a bust? ──▶ confidence layer   ──▶  ensemble spread,
  (worst 5%)           (gradient boosting)     within like conditions
```

**One sentence:** public ensemble forecast data in, government rain gauges as
ground truth, a learned confidence layer out.

**What the model sees:** 23 features per gridpoint per lead day — mid-level
pressure patterns, moisture, instability, wind shear, and crucially **where the
11 ensemble members disagree with each other**. It learns which disagreements
matter.

**What a bust is:** the forecast missed observed gauge rainfall by more than the
95th percentile *for that region and lead time*. A 30 mm error in Cherrapunji is
routine; in Rajasthan it is catastrophic — so the threshold is local.

---

## 6. Figures, and the notes that must go with them

All in `figures/`, 200 dpi, one visual language, each carrying truth source and
sample size.

| file | what it is |
|---|---|
| `fig1_collapse.png` | 43.9% vs 0.90%. **The most persuasive image in the set.** |
| `fig2_deciles.png` | Within every rainfall regime, spread carries almost nothing |
| `fig3_map.png` | Where India's forecasts go wrong, 1,252 gridpoints |
| `fig4_inversion.png` | The +0.023 → +0.163 inversion. **Second best.** |
| `fig6_confidence_map.png` | **The demo slide** — three panels |
| `fig7_shap_global.png` | Feature importance (median and mean, they disagree) |
| `fig8_shap_cases_driest.png` | **The strongest single slide — see below** |
| `fig9_reliability.png` | Calibration |

### `fig8_shap_cases_driest.png` — build a slide around this

Three forecasts where the ensemble predicted **0.0 mm**, VISHWAS flagged them
anyway, and **13–22 mm fell**. Probabilities 0.12–0.17 — small in absolute
terms, but **82–109× the base rate of that group**.

> **The killer fact: ensemble spread is exactly 0.00 mm on all three — tied with
> 189,758 other cases.** The incumbent does not rank these badly. **It cannot
> rank them at all.** A third of the test set collapses into one indistinguishable
> tie, and VISHWAS pulls real busts out of it.

The SHAP breakdown seals it: `precip_spread = 0` is the largest **negative**
contributor, so the model correctly learned that zero spread argues against a
bust — and flagged anyway because the moisture signal overwhelmed it. Not luck:
a system overruling the incumbent using information the incumbent lacks.

### SPEAKER NOTE for the confidence map — do not present it without this

Panels A and B look alike: high predicted probability over central India, heavy
rain over central India. A judge will say *"your model just predicts where it
rains."* The answer:

> Bust probability tracks rainfall because busts happen where it rains — 41%
> bust rate in the wettest of the eight rainfall bins against 0.15% in the
> driest. The question is
> whether we beat "it's raining" alone. Within each rainfall band we score 0.728
> against spread's 0.565. And removing the rainfall forecast from the model
> entirely did not hurt it — performance went slightly **up**.

### Calibration, stated honestly

The raw model was **already well calibrated in aggregate** — say that rather
than claiming a rescue. What isotonic fixes is the tail: the raw model said
p ≥ 0.9 on 72 cases of which only 5.6% busted. Isotonic caps output at 0.75, so
**the calibrated system declines to claim a confidence it has never earned on
held-out data.**

---

## 7. What must NOT be claimed

- **Never quote the pooled ROC-AUC pair. THE RULE IS ABSOLUTE AGAIN — amended
  30 Aug, and the earlier "one sanctioned exception" is WITHDRAWN.**
  The pooled pair appears in **no figure, no slide, no results table, no
  abstract and no spoken headline**. It is a **Q&A-only** answer: if a judge
  asks what the crude comparison gives, the numbers are in `CLAUDE.md`.
  Verified 30 Aug by opening `fig4_inversion.png` and by unzipping deck v17 —
  the pair is in neither, and `src/11_inversion.py` no longer renders it.
  What the deck says instead: **the crude margin is +0.023, the fair margin is
  +0.163, seven times larger.** That tells the whole inversion story without
  printing a number that would commit, in our own work, exactly the error the
  pitch accuses the incumbent of. It is the artefact, not the skill.
  *(A figure that printed the pair "to discredit it" was permitted for part of
  30 Aug. That licence is gone: a rule allowing what the project has decided
  against will be acted on by whoever reads it next.)*
- **Never quote the margin as +0.163 alone.** Say **+0.13 to +0.16**.
- **Never quote +0.663 as "the baseline we beat."**
- **Never quote +0.041 alone** — use the variance range (under 1%).
- **Never quote a margin range containing +0.035.** That came from a filter
  conditioning on the outcome; it is not a fair robustness check.
- **No accuracy figure of any kind.** Base rate is ~6%; accuracy is meaningless
  and quoting it signals a team that does not understand imbalance.
- **No seasonal slide.** Season rankings reverse with analysis choices.
- **We detect busts; we do not correct forecasts.** No "AI-adjusted forecast".
- **Do not call the regions "IMD official regions"** — approximate lat/lon boxes.
- **Do not present one date as evidence of general performance.** The confidence
  map is an illustration; the general result is 0.728 vs 0.565 over 52 dates.

---

## 8. Rigour — the "why trust us" slide

Each of these is a real defect found *in this project*, not a generic practice.

1. **Two data-leakage bugs found and fixed.** The climatology behind our
   features was originally computed over training *and* test data together.
   Caught, fixed, and *proven* fixed. A second leak of identical shape was
   pre-empted in the bust threshold before it could be written.
2. **A third defect caught in our own evaluation.** Our first operational
   comparison had the baseline flagging 38.78% of cases against a 10% alert
   budget — silently voiding the matched-budget premise. Cause: ensemble spread
   is 0.00 mm across 91% of dry cases, so a percentile cut flags everything.
   Fixed with rank-based selection and random tie-breaking.
3. **Uncertainty measured by forecast date, not by row.** Two gridpoints 50 km
   apart on the same day are nearly the same observation.
4. **Negative results reported.** An ensemble-size test showed the baseline
   improves slightly with more members — weakening our own claim — and it is
   written down anyway. Governing rule: *"If we cannot beat ensemble spread,
   say so."*

---

## 9. Milestones

| Date | Milestone |
|---|---|
| 25 Aug | Data pipeline working end to end |
| 26 Aug | Truth corrected from ERA5 reanalysis to IMD gauge observations |
| 27 Aug | Four-season baseline measured; two leakage bugs fixed; wind shear added |
| **29 Aug** | **50 GB fetched, 1.3M rows labelled, model trained — beats the incumbent** |
| **30 Aug** | **Ablations, calibration, explainability, confidence map, operational metrics** |
| **31 Aug** | **College internal PPT** |
| Mid Sep | Extend 2 years → 5 years (incremental, no refetching) |
| **20 Sep** | **SIH idea submission** |
| Oct–Nov | Operational path on live forecasts; real bust case study |
| Dec | Grand Finale |

---

## 10. Questions a judge will ask

**"You used NOAA GEFS. NCMRWF runs its own ensemble. Why?"**
NEPS reforecast archives are not publicly accessible. GEFS is the only publicly
archived medium-range ensemble with a ~20-year reforecast, which is what makes a
four-season, multi-year measurement possible. The method is ensemble-agnostic
and points at NEPS the day access exists. **Put this in the appendix.**

**"Why is your domain smaller than India?"**
IMD's gridded rainfall is gauge-based, so land only — 1,252 of 5,041 gridpoints.
That is the observational domain, and scoring against real gauges rather than a
model reanalysis is the harder, more honest choice.

**"How do you know you are not just predicting heavy rain?"**
We removed the rainfall forecast from the model entirely and performance did not
drop — it rose slightly, 0.728 to 0.731.

**"Isn't this just gradient boosting doing gradient boosting things?"**
A model given only ensemble spread scores 0.562, against 0.565 for spread as a
plain ranking. The algorithm adds nothing; the information does.

**"Only 11 ensemble members? Operational systems run 31."**
Tested. 5 → 11 improves the baseline slightly and does not change the
conclusion. 11 → 31 cannot be measured from this archive, and we say so.

**"One test year is thin."**
Agreed, and stated. The interval resamples 52 dates of a single year, so treat
it as a floor. Extending to 5 years needs no new code.

**"What if the model had not beaten the baseline?"**
We would have reported it. The decision rule was fixed before results were seen,
and the measurement of the incumbent stands on its own.

---

## 11. Glossary

| Term | Plain English |
|---|---|
| **Ensemble** | Running the weather model ~11 times from slightly different starting conditions, because the atmosphere is chaotic |
| **Ensemble spread** | How much those runs disagree. Today's confidence signal |
| **Forecast bust** | A forecast badly wrong — the worst 5% of errors for that place and lead time |
| **Lead time** | How far ahead. Day 1 is tomorrow; Day 10 is ten days out |
| **ROC-AUC** | How well a score separates two groups. 0.5 is a coin flip, 1.0 perfect |
| **POD / FAR** | Of real busts, how many we caught / of our alerts, how many were wrong |
| **Calibration** | If it says "20% chance", it should be wrong four times in five |
| **Gauge-gridded** | Built from real rain gauges, not another computer model |

---

## 12. One-liners that hold up

**Opening:** every forecast India issues arrives with no honesty label. VISHWAS
predicts when the forecast will be wrong.

**The differentiator:** most teams pitch a hypothesis. We pitch a measurement.

**Operational:** given the same number of alerts a forecaster would tolerate, we
catch 64% of busts against the current method's 55%.

**The one that lands hardest:** on a third of the country's forecasts, the
current method returns exactly the same score — zero — and cannot tell them
apart at all. We can.

**Non-technical:** Google Maps says 25 minutes, and sometimes you sit in traffic
for an hour. Imagine it also said "I'm not confident about this one."

**On rigour:** we found three defects in our own pipeline and fixed them. We
report the results that weaken our case alongside the ones that help it.
