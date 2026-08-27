# VISHWAS — Project Handoff

**Team Hellfire Labs · SIH26079 · Ministry of Earth Sciences · Disaster Management**

विश्वास, "confidence" — knowing when not to trust the forecast.

> Read this file first. State of the project as of **27 August 2026**.
> Supersedes the 26 August version, which described a truth source and a
> headline number we have since replaced.
>
> Companions: `CLAUDE.md` (the technical constitution — read before any code)
> and `docs/CLAUDE-CODE-PROMPTS.md` (the work plan, P1–P7).

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
| **31 Aug 2026** | College internal PPT — **4 days away, this is the live deadline** |
| 29 Aug | Internal cutoff — all team inputs to Mahika |
| **20 Sep 2026** | SIH idea submission via SPOC (6 slides) |
| Dec 2026 | Grand Finale (if selected) |

The model does **not** need to be finished for either deadline. Both
submissions are slides, and **the number they rest on is already measured.**

---

## 3. Team

| Person | Role | Feeds into |
|---|---|---|
| **Devansh** (lead) | model + evaluation, runs the agent sessions | everything |
| **Ankit** | data pipeline, features | Devansh |
| **Arnav** | hunting a real Indian forecast-failure case study | Mahika (demo) |
| **Paras** | metrics (ETS/CSI/POD/FAR/FSS) + evaluation integrity | Devansh, Mahika |
| **Mahika** | slides, pitch, interview with a real official | the submission |
| **Dhruv** | users + cost-of-forecast-failure figures | Mahika (Impact slide) |

---

## 4. What changed since 26 August

All seven planned work items except the bulk download are **done and verified.**

| Item | Outcome |
|---|---|
| Truth source | Switched **ERA5 → IMD gauge-gridded rainfall**, verified end to end |
| 850 hPa / true wind shear | Implemented; cost estimate corrected (it is **+60%**, not +1.6%) |
| Four-season re-measurement | Done — this is the deck's number |
| Climatology leak | Found and fixed; the leak was real and is proven fixed |
| Ensemble-size sensitivity | Done — small effect, does not threaten the conclusion |
| Bulk run | **Not started, deliberately.** Not needed for either deadline. |

**New code:** `src/imd_truth.py`, `src/verify_imd.py`, `src/04_conditional.py`,
`src/05_ensemble_size.py`.

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
| Bulk transfer now ~122 GB / ~7.6 h (was ~80 GB / ~5 h) | Not on the deadline path; run it after 31 Aug |

---

## 7. Immediate next actions

**Submission (everyone, by 29 Aug):**
- Arnav — shortlist of documented Indian forecast failures
- Dhruv — primary user + cost figures with citations
- Paras — one-page plain-English metrics explainer, and own the stratified
  (within-magnitude-bin) evaluation when the model is scored
- Mahika — slide skeleton; **the headline number is ready, build against it**

**Technical (Devansh + Ankit) — after 31 Aug, not before:**
1. Bulk run. Start with `--years 2` (~3 h) to validate the pipeline end to end;
   the resumable manifest means extending to `--years 5` later refetches
   nothing. **One process only — the manifest has no locking.**
2. Train the bust classifier; evaluate stratified within magnitude bins.

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
