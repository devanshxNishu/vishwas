# VISHWAS — brief for the deck session

**Written 29 Aug 2026 by the technical session.** Hand this to whoever is
building the PPT. It assumes no prior context.

Deadlines: **internal college PPT 31 Aug** (tomorrow), SIH idea submission
**20 Sep** (6 slides).

> **Audited 30 Aug.** Phase 2 and Phase 3 are complete. §1's caveat 3 and §§6–7
> have been corrected; everything else stands as written. For calibration, SHAP,
> the demo date and the operational (POD/FAR/CSI/ETS) numbers, see
> `docs/DECK-TECHNICAL-PACK.md`, which is the current numbers document.

---

## 1. THE MODEL EXISTS. Results as of 29 Aug, 20:45

*(This section previously said there was no model. Out of date — the first
trained model and first honest evaluation completed tonight.)*

Trained on 2018, tested on **all 52 Wednesdays of 2019**, a year it never saw.
**651,040 test rows**, drawn from a labelled table of 1,302,080 gridpoint-days.
Truth from IMD rain gauges. (Keep those two apart — the score below is measured
on the 651,040, and conflating them is a defect a judge can check.)

| | ensemble spread (today's method) | VISHWAS |
|---|---|---|
| **Compared within like rainfall conditions** | **0.565** | **0.728** |

*(ROC-AUC: 0.5 is a coin flip, 1.0 is perfect.)*

> **The pooled row was removed from this table on 30 Aug.** The pooled pair is
> Q&A-only — it appears in no figure, slide or table. Both methods score near
> 0.9 there, which measures the wet/dry gradient rather than either method, and
> printing it in a results table is exactly the error this pitch accuses the
> incumbent of. If a judge asks for it, the numbers are in `CLAUDE.md`.

**THE HEADLINE, AND IT IS UNUSUAL.** Compared crudely, VISHWAS beats the
current method by a forgettable +0.023. Compared *fairly*, the gap widens to
**+0.163 — seven times larger**. Pooled scoring hands ensemble spread most of
its apparent skill for free by letting it track how hard it is raining. Strip
that away and it falls to **0.565, barely better than a coin flip**, while
VISHWAS holds **0.728**.

**The honest comparison is the one that favours us.** Most projects' numbers
get worse under scrutiny. Ours gets better, because the scrutiny removes an
advantage the incumbent never earned.

Safe to quote:
- 95% CI on the margin: **+0.108 to +0.193** (cluster bootstrap over 52
  forecast dates) — entirely above zero.
- **Ahead in every rainfall regime**, by +0.079 to +0.252.
- Largest edge in the driest conditions (0.835 vs 0.583) — the "ensemble is
  confident it won't rain, and it rains anyway" failure Phase 1 identified.
- Still ahead by +0.097 in the heaviest-rain bin, where 41% of forecasts bust.
- PR-AUC lift over base rate: **7.60x**, against the baseline's 6.29x.

**How to quote the margin: say +0.13 to +0.16, never +0.163 alone.** Those are
the variants conditioning only on the *forecast*. Disregard any figure from a
"forecast AND truth > X mm" filter — it conditions on the outcome, deleting
both classes of extreme bust, and understates the model for reasons unrelated
to quality.

**Three caveats, to state before a judge finds them:**
1. **One test year.** 2019 only. The interval is blind to year-to-year
   variation; treat it as a floor. The 5-year extension addresses it.
2. **Region-scope thresholds.** 52 training dates is too few for per-gridpoint
   thresholds (a 95th percentile would rest on 2.6 observations), so the bust
   threshold is per region and lead time.
3. ~~**The `month` ablation has not run.**~~ **RESOLVED 29 Aug — it ran and it
   passed.** Dropping `month` moves the score by **−0.0059**, far inside the
   0.02 tolerance fixed in advance. The model is not learning the calendar.
   **0.728 is final; print it.**

Nothing was tuned. No threshold, bin or definition was adjusted after seeing
results, and the decision rule was fixed in advance.

## 2. The theme changed, and it changes the pitch

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

### Two consequences that need action

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

## 3. The numbers — verified, and the only ones that may be quoted

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

## 4. What must NOT be claimed

- **Never quote the pooled ROC-AUC (0.885 baseline / 0.909 model).** It is the
  artefact, not the skill. Putting 0.909 on a slide would commit, in our own
  work, exactly the error our pitch accuses the incumbent of. The stratified
  pair (0.565 vs 0.728) is the result.
- **Never quote the model margin as +0.163 alone.** Say +0.13 to +0.16 — the
  range across variants that condition only on the forecast.
- **Never quote +0.663 as "the baseline we beat."** It is the artefact, not the
  signal. Quoting it would overstate the incumbent method.
- **Never quote +0.041 alone.** It rests heavily on one slice of the data;
  under other reasonable definitions it is nearer +0.09. Use the variance range
  (under 1%) instead, which is stable either way.
- **No seasonal slide.** Which season looks best reverses depending on analysis
  choices, and there are only three dates per season. There is no reliable
  seasonal story yet.
- **No accuracy figure of any kind.** The events are rare (~6% base rate), so
  accuracy is meaningless and quoting it signals the team does not understand
  imbalance. Use ROC-AUC and PR-AUC lift.
- **We detect busts, we do not correct forecasts.** Any "AI-adjusted forecast"
  wording is wrong and promises something not being built.
- **Do not call the regions "IMD official regions."** They are approximate
  latitude/longitude boxes.

---

## 5. The question a judge will ask first — have the answer ready

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

## 6. Assets ready to use

**Updated 30 Aug — this list previously named only the first three.** Eight
figures, 200 dpi, built from the real data, in `figures/`:

- `fig1_collapse.png` — 43.9% vs 0.90%, the headline. One bar towering over one
  almost invisible bar.
- `fig2_deciles.png` — the proof: within every rainfall regime, spread carries
  almost nothing. Includes the "confidently dry and wrong" failure mode.
- `fig3_map.png` — where India's forecasts go wrong, over the 1,252
  gauge-observed land gridpoints. Makes the product concrete.
- `fig4_inversion.png` — the +0.023 crude vs +0.163 fair inversion, with the
  confidence interval as an error bar. **Regenerated 30 Aug.**
- `fig6_confidence_map.png` — the demo: init 31 July 2019, Day 5, valid 5 Aug.
  **Three panels**, not two.
- `fig7_shap_global.png` — feature importance, median and mean side by side.
- `fig8_shap_cases_driest.png` — **the strongest single slide.** Three
  forecasts the incumbent cannot rank at all.
- `fig9_reliability.png` — calibration.

`fig5_confidence_map.png` was **deleted** on 30 Aug (its caption carried a date
that does not exist in the data). Do not look for it, and do not reuse the copy
still embedded in `deck/VISHWAS_SIH.pptx` — see `docs/DECK-VERIFICATION.md`.

Every figure already carries its truth source and sample size. Keep those
captions; they are what make the numbers credible.

---

## 7. One-liners that hold up

**Opening:** every forecast India issues arrives with no honesty label. VISHWAS
predicts when the forecast will be wrong.

**The differentiator:** most teams pitch a hypothesis. We pitch a measurement.

**Non-technical:** Google Maps says 25 minutes, and sometimes you sit in traffic
for an hour. Imagine it also said "I'm not confident about this one." That's
VISHWAS, for weather.

**If asked whether it works yet:** it works, and it is measured. We proved the
incumbent method is weak, then built the replacement and scored it on a year it
never saw: 0.728 against 0.565 on the fair comparison, ahead in every rainfall
regime. The rule we set before we saw results still stands — if it had failed to
beat the baseline we would have reported that instead.
