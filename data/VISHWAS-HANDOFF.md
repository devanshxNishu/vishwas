# VISHWAS — Project Handoff

**Team Hellfire Labs · SIH26079 · Ministry of Earth Sciences / NCMRWF**
**Theme: Smart Automation** (SIH re-listed this PS from Disaster Management to
Smart Automation partway through; older notes saying Disaster Management are
stale, not wrong-at-the-time). Track: Software.

विश्वास, "confidence" — knowing when not to trust the forecast.

> Read this file first. State of the project as of **30 August 2026**.
> Supersedes the 26 August version, which described a truth source and a
> headline number we have since replaced.
>
> **Updated 30 Aug (consistency audit).** Sections 1, 3, 5 and 8 are unchanged
> and were always correct. Sections 2, 4, 6 and 7 described the bulk run and the
> model as future work; **both are done**, and those sections have been
> rewritten. §4a below is new.
>
> Companions: `CLAUDE.md` (the technical constitution — read before any code),
> `docs/DECK-TECHNICAL-PACK.md` (every current number, for the deck) and
> `docs/CLAUDE-CODE-PROMPTS.md` (the Phase 1 work plan, P1–P7).

---

## 1. What the project is

We are **not** building a weather forecast. We are building a system that
predicts **when the operational forecast will be badly wrong** (a "forecast
bust"). Output: a forecast-confidence map over India, Day 1 to Day 10.

**The scientific claim:** our learned confidence signal beats **ensemble
spread**, which is what forecasters use today.

---

## 2. Deadlines

| Date | What |
|---|---|
| **31 Aug 2026** | College internal PPT — **tomorrow, this is the live deadline** |
| ~~29 Aug~~ | ~~Internal cutoff — all team inputs to Mahika~~ — passed |
| **20 Sep 2026** | SIH idea submission via SPOC (6 slides) |
| Dec 2026 | Grand Finale (if selected) |

The model did not *need* to be finished for either deadline — but **it is
finished**, trained, ablated, calibrated and explained. Both submissions are
slides, and every number they rest on is measured.

---

## 3. Team

| Person | Role | Feeds into |
|---|---|---|
| **Devansh** (lead) | data pipeline, model + evaluation, runs the agent sessions | everything |
| **Ankit** | problem-statement tracking, option analysis | Devansh, Mahika |
| **Arnav** | hunting a real Indian forecast-failure case study | Mahika (demo) |
| **Paras** | metrics (ETS/CSI/POD/FAR/FSS) + evaluation integrity | Devansh, Mahika |
| **Mahika** | slides, pitch, interview with a real official | the submission |
| **Dhruv** | users + cost-of-forecast-failure figures | Mahika (Impact slide) |

---

## 4. What changed since 26 August

All planned work items are **done and verified**, the bulk download included.

| Item | Outcome |
|---|---|
| Truth source | Switched **ERA5 → IMD gauge-gridded rainfall**, verified end to end |
| 850 hPa / true wind shear | Implemented; cost estimate corrected (it is **+60%**, not +1.6%) |
| Four-season re-measurement | Done — this is the deck's Phase 1 number |
| Climatology leak | Found and fixed; the leak was real and is proven fixed |
| Ensemble-size sensitivity | Done — small effect, does not threaten the conclusion |
| Bulk run | ✅ **Complete 29 Aug** — 104 forecast dates, 2018–2019, 50.3 GB |

**New code:** `src/imd_truth.py`, `src/verify_imd.py`, `src/04_conditional.py`,
`src/05_ensemble_size.py`, `src/06_label.py`, `src/07_model.py`,
`src/08_demo_map.py`, `src/08_met_metrics.py`, `src/08_pick_date.py`,
`src/09_shap.py`, `src/10_calibration.py`, `src/11_inversion.py`,
`src/met_metrics.py`.

---

## 4a. The model — added 30 August

Trained on 2018 (39 dates fitted, 13 held back as validation), tested on **all
52 Wednesdays of 2019**, a year it never saw. **651,040 test rows** out of a
1,302,080-row labelled table, over the same 1,252 gauge-observed land
gridpoints, Day 1–10. Truth: IMD gauge-gridded rainfall.

| | ensemble spread | VISHWAS |
|---|---|---|
| ROC-AUC, within like rainfall conditions | **0.565** | **0.728** |
| PR-AUC lift over base rate | 6.29× | 7.60× |

Margin **+0.1634**, 95% CI **+0.1080 to +0.1926** (cluster bootstrap over the 52
dates). **Quote it as +0.13 to +0.16, never +0.163 alone.** Ahead in all **8**
rainfall bins, by +0.079 to +0.252.

**Do not quote the pooled ROC-AUC pair as the result** — it is the artefact this
project exists to expose. See `docs/DECK-TECHNICAL-PACK.md` §7.

**In operational terms:** given the same number of alerts a forecaster would
tolerate, VISHWAS catches **64% of busts against the current method's 55%**.

Also done: five ablations (`month` passed at −0.006, so the model is not
learning the calendar), isotonic calibration, SHAP explanations, and a demo
confidence map for init 31 July 2019, Day 5, valid 5 Aug. Every number is in
`docs/DECK-TECHNICAL-PACK.md`, which is the current numbers document.

---

## 5. The measurement the whole pitch rests on

Truth = **IMD gauge-gridded rainfall** (MoES's own product, land only), 12 init
dates across **all four seasons and three years** (2012/2015/2018), 11 members.

|  | value |
|---|---|
| Pooled across gridpoints | **r = +0.663** |
| Conditioned on rainfall magnitude | **r = +0.041** |
| 95% CI (cluster bootstrap over 12 dates) | +0.016 to +0.065 |

**Interpretation:** almost all of the apparent +0.663 is the wet/dry spatial
gradient — wet places have big spread and big errors. That is climatology, not
a confidence signal. **Within a comparable rain regime, ensemble spread tells
you almost nothing.**

### Read this before anyone quotes a number

**+0.041 is fragile on its own.** It rests almost entirely on the driest
decile, where the correlation is −0.474. Under other reasonable definitions of
a "wet point" the figure is roughly **+0.09**:

| variant | conditional r |
|---|---|
| OR filter, all bins (the headline) | +0.041 |
| drop the driest decile | +0.093 |
| require **both** forecast and truth > 0.5 mm | +0.095 |
| …> 1.0 mm / > 2.0 mm | +0.089 / +0.084 |

So **quote the variance framing, which is robust to that choice:**

> Ensemble spread appears to explain **43.9%** of the variance in forecast
> error. Once you control for how hard it is raining, it explains **under 1%**
> — between 0.17% and 0.90% depending on how you define a wet point.

That sentence survives a hostile question. A single correlation coefficient
does not.

### A second, better finding

The driest-bin behaviour is not a wart, it is a result. When the ensemble is
**confidently dry and it rains anyway**, spread is **actively misleading** —
narrow spread, huge error. That names a specific, operationally usable failure
mode. Report it as its own finding rather than burying it in the headline.

### What NOT to claim

- **Do not** quote the pooled number as "the baseline we beat."
- **Do not** build a seasonal slide. The seasonal ordering is not stable: under
  the OR filter JJAS is highest and DJF negative; under the robust filter ON is
  highest and DJF flips positive. Three dates per season is too thin.
- **Do not** put the old +0.076 figure in the deck. It was a different truth
  source, a different domain, and one season. Report one number measured one
  way, and the "why did it change?" question never arises.

---

## 6. Open risks

| Risk | Status |
|---|---|
| Headline sensitive to the wet-filter definition | **Identified; report the robust range and the variance framing** |
| Ensemble size (5→11 improves baseline ~+0.015) | Small, stated honestly; 5→31 remains unmeasurable from the reforecast |
| Land-only domain (1252 of 5041 gridpoints, 24.8%) | Defensible — it is the gauge domain — but **state it before a judge finds it** |
| Rare-event precision will look low in absolute terms | Report honestly; the comparison is what matters |
| ~~Bulk transfer now ~122 GB / ~7.6 h~~ | **Closed.** The 2-year run completed 29 Aug at 50.3 GB over 104 dates. The ~122 GB figure was the 5-year estimate; that extension is now a mid-Sep item |
| One test year (2019 only) | Stated openly. The interval is blind to year-to-year variation — treat it as a floor. The 5-year extension addresses it |

---

## 7. Immediate next actions — rewritten 30 Aug

**Before the PPT tomorrow:**

Items 1–3 (slide 3's figure, slide 4's figure, slide 6's wording) were **all
done in deck v17, built 30 Aug 15:59** — re-verified by hashing the deck's
embedded media. Two remain:

1. Paste the **Team ID** (slide 1, still a red placeholder).
2. Confirm the **PS title** against the portal wording.

**Present from `deck/VISHWAS_SIH.pdf`.** The superseded 29 Aug build has been
moved to `deck/archive/` so there is only one presentable deck in `deck/`.

**Technical (Devansh + Ankit) — after 31 Aug:**
1. Extend the run from 2 years to 5. The resumable manifest refetches nothing.
   **One process only — the manifest has no locking.**
2. Decide the open `fig4` question in `docs/DECK-VERIFICATION.md` (the figure on
   disk and `src/11_inversion.py` disagree about the footnote).

**Still outstanding from the team:** Dhruv's cost figures re-angled for Smart
Automation (forecaster time and decision quality, not flood damage), and Arnav's
verified case study.

---

## 8. Framing for the pitch

**One-liner:** every forecast India issues arrives with no honesty label.
VISHWAS predicts when the forecast will be wrong.

**The strongest line available to us:** we measured the method forecasters use
today, against India's own gauge observations, across all four seasons — and
once you compare fairly it explains under 1% of forecast error. Most teams
pitch a hypothesis; we pitch a measurement.

**Non-technical version:** Google Maps says 25 minutes, and sometimes you sit
in traffic for an hour. Imagine it also said "I'm not confident about this one."
That's VISHWAS, for weather.

**Honesty rules that stay in force:** split train/test by time, never randomly;
never report plain accuracy on a ~5% base rate; never label the 500 hPa
deformation feature as wind shear; if we cannot beat spread, say so — an honest
negative result scores better with meteorologist judges than an inflated claim.
