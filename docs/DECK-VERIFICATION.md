# VISHWAS deck — claim-by-claim verification

Every factual statement on `deck/VISHWAS_SIH.pptx`, traced to a source.
Checked 29 Aug 2026 against `CLAUDE.md`, `README.md`, `data/VISHWAS-HANDOFF.md`,
`docs/DECK-BRIEF.md`, Devansh's `TECHNICAL-REFERENCE.md`, Arnav's model-error
report, Mahika's research evidence brief, `DECK-TECHNICAL-PACK.md` (29 Aug, 21:10),
and named government and peer-reviewed sources.

Status key — **OK** verified · **CHECK** needs a human · **CTX** framing, not a
measurement.

## Slide 1 — Title

| Claim | Source | Status |
|---|---|---|
| PS ID SIH26079 | README.md, CLAUDE.md | OK |
| Title "AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts" | README.md "Problem Statement" | **CHECK** — confirm against portal; CLAUDE.md notes verbatim PS text is not in repo |
| Theme — Smart Automation | README.md; CLAUDE.md item 2; HANDOFF header | OK |
| PS Category — Software | README.md "Track: Software" | OK |
| Team ID | **blank, red placeholder** | **CHECK** |
| Ministry of Earth Sciences / NCMRWF | README.md, HANDOFF header | OK |
| Interdisciplinary team block: B.Tech (Devansh, Ankit) / BCA (Arnav, Paras) / BBA-BA (Mahika, Dhruv) | Stated by Devansh, 29 Aug 2026 | **CHECK** — confirm whether Mahika and Dhruv are both BBA, or one BBA and one BA |

## Slide 2 — Idea title

| Claim | Source | Status |
|---|---|---|
| Day 1–10 confidence output | CLAUDE.md PROJECT | OK |
| RELIABLE / UNCERTAIN / HIGH-RISK | Mahika's deck framing | CTX |
| "flags busts; does not adjust the forecast" | CLAUDE.md item 3 (detection, not correction) | OK |
| Forecasters judge confidence by ensemble spread | CLAUDE.md SUCCESS CRITERION | OK |
| 43.9% of forecast error, pooled | CLAUDE.md "pooled explains 43.9% of the variance in log error" | OK |
| under 1% within rainfall regime | CLAUDE.md "conditional explains 0.17% to 0.90%" | OK |
| four seasons, three years | CLAUDE.md SPREAD-SKILL RE-MEASURED | OK |

## Slide 3 — Technical approach

| Claim | Source | Status |
|---|---|---|
| GEFSv12 reforecast, 2000–2019 | CLAUDE.md ARCHIVE RANGE | OK |
| IMD 0.25° gauge-gridded rainfall, 1901–2024 | CLAUDE.md TRUTH SOURCE (right endpoint) | OK |
| Gauge observation, not reanalysis | CLAUDE.md WHY THE SWITCH IS WORTH MAKING | OK |
| **23** features, all from GEFS, none from truth | `models/vishwas_model.joblib` carries 23 feature names; `ablations/permutation_importance.csv` has 23 rows; CLAUDE.md FEATURE SOURCE RULE | **OK (corrected 30 Aug — this row said 24)**. The feature table has 24 non-key columns; `season` is built but never fed to the model. The model sees 23. See the corrections table below, which already recorded this. |
| Feature list | CLAUDE.md FEATURES + VARIABLE LIST | OK |
| "true 500–850 hPa wind shear" *and* "500 hPa flow deformation" named separately | CLAUDE.md WIND SHEAR — the two must never be conflated | OK |
| Bust = \|forecast − observed\| above 95th pct, per region and lead time | CLAUDE.md MODEL PLAN 1 | OK |
| HistGradientBoostingClassifier | CLAUDE.md MODEL PLAN 3 | OK |
| SHAP, reliability diagram, Brier | CLAUDE.md MODEL PLAN 4–5 | OK |
| ROC-AUC / PR-AUC / precision@top-10% | CLAUDE.md SUCCESS CRITERION — named as protocol, **no values quoted** | OK |
| POD, FAR, CSI, ETS, FSS | Paras, metrics guide | OK |
| Split by time, never randomly | CLAUDE.md HONESTY RULES | OK |
| Santacruz 944 mm vs Colaba 73 mm, 27 km apart, 26 Jul 2005 | Kumar et al. (2008) QJRMS 134, 1897–1910 — verified independently. **Arnav's chart says 70 mm; the peer-reviewed figure is 73** | OK (corrected) |

## The model result — FINAL (ablation passed 29 Aug)

Added to the deck 29 Aug from `DECK-TECHNICAL-PACK.md` §3. Trained on 2018,
tested on all 52 Wednesdays of 2019 — a year the model never saw. 651,040 test
rows, drawn from a labelled table of 1,302,080 gridpoint-days. IMD rain gauges
as truth.

| Claim on the deck | Source | Status |
|---|---|---|
| Ensemble spread 0.565 vs VISHWAS 0.728, stratified ROC-AUC | Technical pack §3; confirmed by `ablations/a_full.log` | **OK** |
| Ahead under every wet-point definition tested | `ablations/a_full.log` robustness table — model ahead in all 5 variants | OK |
| Confidence map, **31 Jul 2019 init, Day 5, valid 5 Aug**, 454 of 1,252 busts, AUC 0.886 on that date | Computed from `data/model_predictions.parquet` — real out-of-sample predictions | **CORRECTED 30 Aug.** v12 said "26 Jul init, valid 31 Jul" — both dates five days early, and 26 Jul 2019 was a Friday, not one of the 52 Wednesday inits. The counts and the AUC were always right; only the date label was wrong. **The deck itself still carries the wrong date on slide 3 — fix before Monday.** |
| Permutation importance ranks pwat, precip_spread, precip_mean | `ablations/permutation_importance.csv` | OK |
| Margin quoted as **+0.13 to +0.16** | Pack: "quote the margin as +0.13 to +0.16, never +0.163 alone" | OK — fig4 regenerated 30 Aug; the old version printed +0.163 alone in 40pt |
| 95% interval entirely above zero | Pack §3 (+0.108 to +0.193) | OK |
| Ahead in all eight rainfall bins | Pack §3 (+0.079 to +0.252) | OK |
| Driest conditions 0.835 vs 0.583 | Pack §3 | OK |
| Crude margin +0.023 vs fair +0.163, "seven times larger" | Pack §1, beat 3 | OK |
| 50.3 GB, 104 forecast dates, 1.3M gridpoint-days | Pack §3 scale table | OK (FINAL) |
| Base rate ~6% | Pack §7 | OK — corrected from ~5% |

**The `month` ablation has run and passed.** Dropping `month` moves the model
from 0.728 to 0.722 — a fall of **0.006**, well inside the 0.02 tolerance the
technical pack set. The figures stand as written and the claim is no longer
provisional.

**One nuance to hold for Q&A.** The robustness table also reports truth-filtered
wet-point variants (`both > 0.5 / 1.0 / 2.0 mm`). Those numbers are real, but
they are **not a margin range and must never be quoted as one.** They condition
on the OUTCOME: requiring truth to be wet deletes every "forecast said dry, it
poured" bust, and requiring the forecast to be wet deletes every "forecast said
rain, nothing came" bust. Both extreme classes vanish and only middling busts
remain, so the margin shrinks for reasons unrelated to model quality. The
robustness panel in `07_model.py` labels them `[truth-filtered]` and excludes
them from the verdict range for exactly this reason.

**The honest robustness range is +0.132 to +0.163**, from the
forecast-conditioned variants (all bins, and drop-the-driest-bin), which
condition only on information available at forecast time. That is the range
behind the deck's "+0.13 to +0.16". The correct answer to "what if I define a
wet point differently?" is that **the model is ahead under every definition
tested** — quoting the truth-filtered numbers as a margin range instead would
understate the model and invite a fair challenge.

## ~~⛔ TWO STALE IMAGES ARE EMBEDDED IN `deck/VISHWAS_SIH.pptx`~~ — ✅ FIXED, SECTION STALE

> **RESOLVED 30 Aug 15:59 — this whole section is now historical.** The deck was
> rebuilt (v17) and re-verified by unzipping it and hashing its media:
> `image5.png` is `figures/fig6_confidence_map.png` and `image6.png` is the
> regenerated `figures/fig4_inversion.png`, both byte-identical. Six media
> files, all referenced, **zero orphans, no `fig5`**. Slide 6's wording is
> fixed too. Nothing below is outstanding.
>
> The stale v1 build that *did* carry these faults has been moved to
> `deck/archive/`. See `docs/CONSISTENCY-AUDIT.md` F3 and F5.

Found 30 Aug by unzipping the deck and matching embedded media by byte size.
The `.pptx` was built 29 Aug 16:10 and still carries figures that have since
been deleted or regenerated.

| Slide | Embedded | Byte size | What it actually is | Action |
|---|---|---|---|---|
| 3 | `ppt/media/image5.png` | 132,935 | the **deleted** `fig5_confidence_map.png` | replace with `figures/fig6_confidence_map.png` |
| 4 | `ppt/media/image6.png` | 164,852 | the **superseded** `fig4_inversion.png` | replace with the regenerated `figures/fig4_inversion.png` |

**Slide 3 is the urgent one.** The embedded image has the wrong date burned
into its caption — "initialised 26 July 2019, valid 31 July" when the numbers
on it (454 busts, AUC 0.886) belong to init **31 July**, valid **5 August**.
26 July 2019 was a Friday and is not one of the 52 Wednesday inits, so the
claim is checkable and wrong. A meteorologist judge who checks the calendar
finds it in seconds.

**This cannot be hot-swapped in the zip.** `fig6` has three panels where `fig5`
had two, and a different aspect ratio, so dropping it into the existing picture
frame would distort it. Slide 3 needs a layout change, not a file substitution.

**One more wording fix on slide 6.** It reads "scores 0.728 ... from 1,302,080
labelled gridpoint-days". 1,302,080 is the whole labelled table; the model was
**tested on 651,040** of those rows. Same defect the regenerated `fig4` fixed.

---

## Slide 4 — Feasibility and viability

| Claim | Source | Status |
|---|---|---|
| Truth source verified end to end | CLAUDE.md VERIFY-IMD, all four pass | OK |
| Baseline measured, four seasons / three years | CLAUDE.md SPREAD-SKILL RE-MEASURED | OK |
| "trained model, evaluated on a held-out 2019, artifact persisted" | TECHNICAL-REFERENCE §8 status table; `models/vishwas_model.joblib`; CLAUDE.md PHASE 3 | OK — **superseded 30 Aug. v2 said no model existed; the model is now trained, ablated, calibrated and explained.** |
| Two data-leakage bugs found and fixed | TECHNICAL-REFERENCE §7.1; CLAUDE.md LEAKAGE | OK |
| "we will report what it does, including if it fails" | CLAUDE.md HONESTY RULES | OK |
| Runs on CPU, no GPU | CLAUDE.md CONSTRAINTS | OK |
| Pipeline streams each date, no archive held | CLAUDE.md STORAGE | OK |
| NEPS archives not publicly accessible; GEFS only public ~20-yr reforecast; method ensemble-agnostic | CLAUDE.md item 1 | OK |
| 1,252 of 5,041 gridpoints (24.8%) | CLAUDE.md VERIFY-IMD 3 | OK |
| 5 → 11 members: small positive effect, conclusion unchanged | CLAUDE.md CORRECTED READING — wording chosen deliberately over "no effect" | OK |
| 5 → 31 beyond what the reforecast can show | CLAUDE.md CAVEAT THAT MUST BE STATED | OK |
| ~5% base rate; PR-AUC not accuracy | CLAUDE.md HONESTY RULES | OK |
| Weight FAR/precision above raw POD | CLAUDE.md item 2, TECHNICAL CONSEQUENCE | OK |
| Cry-wolf effect is documented | LeClerc & Joslyn (2015), Risk Analysis 35(3), DOI 10.1111/risa.12336 — verified via PubMed 25627345 | OK |
| NDRF constable mobilised for rain that never came | Mahika's field research, interview 3 | OK — qualitative, reported as a single observation |
| Confidently-dry failure mode | CLAUDE.md CAUSE / second finding | OK |

## Slide 5 — Impact and benefits

| Claim | Source | Status |
|---|---|---|
| Primary user = duty forecaster at an operational centre | DECK-BRIEF §2 (Smart Automation re-angle) | CTX |
| Confidence assessed by hand each cycle | CLAUDE.md item 2 | OK |
| **85% → 58%** IMD heavy-rainfall warning accuracy, Day 1 → Day 5 | **MoES, Lok Sabha Q. 2953, 17 Dec 2025** — verified directly at moes.gov.in: "85%, 73%, 67%, 63% and 58% for lead times ranging from one to five days" | OK |
| ~~0.34–0.37 multi-model false-alarm ratio, Day 1–5~~ | ~~IMD Monsoon Report 2024, via Dhruv~~ | **REMOVED 30 Aug.** The number could not be traced to any table in that report. The report may be cited for *containing* FAR/POD/threat-score verification; it may **not** be cited as the source of 0.34–0.37. Do not put this figure on a slide. |
| Farmer, Assam — shifted sowing for rain that did not arrive | Mahika's field research, interview 1 | OK — qualitative |
| Krishi Vibhag, Unnao UP — "very, very beneficial" | Mahika's field research, interview 2 | OK — direct quote |
| NDRF constable, Guwahati — mobilised for rain that never came | Mahika's field research, interview 3 | OK — qualitative |
| Downstream users (district, agriculture, power, aviation) | DECK-BRIEF §2a | CTX |

**Field-research integrity.** Three exploratory conversations, not a survey.
Mahika's brief states this explicitly and the deck follows it: no percentages,
no "N% of users said", each observation attributed to one named role. Keep it
that way.

## Slide 6 — Research and references

| Claim | Source | Status |
|---|---|---|
| 12 reforecasts, 77,425 wet samples, 1,252 gridpoints, Day 1–10 | README.md results table | OK |
| 43.9% / 0.17–0.90% | CLAUDE.md | OK |
| Range spans five wet-point definitions | CLAUDE.md lists exactly five variants | OK |
| Cluster bootstrap over forecast dates | CLAUDE.md REPRODUCIBILITY 5 | OK |
| All government sources | Dhruv's reference sheet, each with a live URL | OK |
| Ashrit et al. (2020), NCMRWF, Met. Apps 27(2) | Crossref DOI 10.1002/met.1906 — authors and affiliation confirmed | OK |
| Kumar et al. (2008), QJRMS 134 | Full text verified at mmm.ucar.edu | OK |
| MoES Lok Sabha Q. 2953, 17 Dec 2025 | Verified at moes.gov.in — includes the ~40% improvement on 2014 | OK |
| LeClerc & Joslyn (2015), Risk Analysis 35(3) | Verified via PubMed / Wiley | OK |
| Kusunose & Mahmood (2016), Agricultural Systems 146 | From Mahika's brief; DOI 10.1016/j.agsy.2016.04.006 | **CHECK** — cited but not independently opened |

## Deliberately NOT on the deck

Each of these was available and was left off for a stated reason.

| Excluded | Why |
|---|---|
| Pooled r = +0.663 as "the baseline we beat" | CLAUDE.md: it is the artefact, not the signal |
| Conditional r = +0.041 quoted alone | CLAUDE.md: fragile, rests on one decile; variance framing used instead |
| The old +0.076 figure | CLAUDE.md: different truth source, domain and season |
| A seasonal slide | CLAUDE.md: ordering is not stable, three dates per season |
| Any accuracy figure | Base rate ~6% makes accuracy meaningless, and quoting it signals a team that does not understand imbalance. (This row previously read "no model exists yet" — stale since 29 Aug; the reason was always the base rate, not the absence of a model.) |
| "AI-adjusted forecast" map | CLAUDE.md item 3 — appears in Paras's metrics guide p.12 and must not reach a slide |
| "IMD official regions" | DECK-BRIEF §4 — they are approximate lat/lon boxes |
| Flood damage / lives lost / cropped-area figures | Off-theme under Smart Automation (DECK-BRIEF §2a) |
| "IMD forecast +13% vs observed +96%" for Kerala Aug 2018 | Arnav's report. IMD's own extreme-rainfall report gives August 2018 Kerala at **+94%** (821.0 mm), and states **no advance 13% forecast figure**. Attributing a specific number to an IMD forecast, in front of a judge from the same ministry, needs a hard citation we do not yet have |
| IMD AWS/ARG station data | CLAUDE.md: public portal access closed ~May 2025 |
| Real-time IMD APIs as the data foundation | CLAUDE.md: training is entirely inside the 2000–2019 reforecast |
| 98%→46%, 0.89 POD / 0.38 FAR, ₹13,331 cr, "50% faster", "~30% improvement", "evacuation costs down to one-third" | Present in earlier team drafts; still not traceable to a verified source |
| Pooled ROC-AUC 0.885 / 0.909 | **Never as a headline.** ⚠️ **Row corrected 30 Aug, and it opens a discrepancy — see the flag below.** It previously stated that the regenerated `fig4_inversion.png` prints the pooled pair in its provenance footnote. **It does not.** The rendered PNG on disk was inspected directly: its footnote reads "Left bar: VISHWAS's margin when every forecast is pooled together…" and prints only the stratified pair (0.728 / 0.565). The pooled pair appears nowhere in the deck. |
| ⚠️ **FLAG — `fig4` cannot be reproduced from `src/`** | **Do not resolve this by editing either side.** `figures/fig4_inversion.png` (written 30 Aug 04:29) carries footnote text that exists in no script in this repository. `src/11_inversion.py` (last modified 30 Aug 03:35) would render a *different* footnote — one that **does** print "0.909 vs 0.885", matching the "one sanctioned exception" paragraph in `CLAUDE.md` and pack §7. So the figure and the code that is supposed to produce it disagree, and re-running `11_inversion.py` today would produce a figure that contradicts this table. The numbers are not in question — they reproduce exactly from `data/model_predictions.parquet`. What is in question is which footnote is intended. **A human must decide before the figure is regenerated.** |
| ~~Pooled ROC-AUC as a claim~~ | **Never on a slide.** The pack: quoting 0.909 would commit, in our own work, exactly the error the pitch accuses the incumbent of. The stratified pair is the result. Swept for on every build. |
| ~~Calibration, SHAP, the confidence map as delivered~~ | **NO LONGER EXCLUDED — all three were delivered 30 Aug** and are in `docs/DECK-TECHNICAL-PACK.md` §4 and §6. Slide 3's "next build step" wording is stale and must come off. |
| ~~85%→58%~~ | **REINSTATED.** Rejected on 29 Aug as unsourced. Mahika then sourced it to MoES Lok Sabha Q. 2953 (17 Dec 2025), which was verified directly. It is now on slide 5. |
| "Multiple forecast sources / forecast-observation divergence / real-time observations" as VISHWAS inputs | Appears in Mahika's §5 framework. VISHWAS uses a single ensemble (GEFS) and takes no real-time observations; features come from GEFS only |

## Arnav's case studies — status

| Case | Figures | Verdict |
|---|---|---|
| **Mumbai, 26 Jul 2005** | Santacruz 944 mm vs Colaba 73 mm in 24 h, 27 km apart | **Verified and used** on slide 3 — the cleanest justification for per-gridpoint confidence. Correct Colaba to 73 mm in his chart. |
| **Kerala, Aug 2018** | "IMD forecast 13%" vs "observed 96%" | **Not used.** Observed is +94% per IMD's own report, not 96%. The 13% forecast figure is not in that report. Needs a hard citation before it is spoken aloud. Ashrit et al. (2020) from NCMRWF studies exactly this event and is the right source to check. |
| **Uttarakhand, 17 Jun 2013** | Dehradun >340 mm vs normal 65.9 mm | **Not used and not verified** — it shows an extreme event, not a documented forecast failure, so it does not illustrate a bust. |

## Open items

1. **Team ID** — blank on slide 1.
2. **PS title** — from README; confirm the exact portal wording.
3. **Dhruv's re-angled cost figures** — DECK-BRIEF §2a asks for forecaster time
   and operational decision quality with citations, replacing disaster-damage
   totals. Not yet supplied, so slide 5 currently carries no cost figure.
4. **Arnav's case study** — not yet supplied.

## Checked against DECK-TECHNICAL-PACK v2 (30 Aug) — corrections applied

| Item | Was on the deck | Now | Source |
|---|---|---|---|
| Feature count | 24 | **23** | `ablations/permutation_importance.csv` has 23 rows; CLAUDE.md "all 23 features" |
| SHAP vs permutation | "agree on the drivers: precipitable water, ensemble precipitation spread, then forecast rainfall" | claim removed from the slide; notes now say they pick the **same top three in different order** | `figures/shap_vs_permutation.csv` — permutation ranks pwat/precip_mean/precip_spread 1-2-3, SHAP median ranks precip_spread/precip_mean/pwat 1-2-3 |
| Calibration & SHAP | "the next build step" | removed — both are **done** | pack v2 §1 |
| Wet-point robustness range | notes quoted "+0.035 to +0.050" | removed | pack v2 §7: *never quote a margin range containing +0.035* — it came from a filter conditioning on the outcome |
| Rigour | lost in the 29 Aug slide-4 rewrite | restored as **three defects**, not two | pack v2 §8 |

## Added from pack v2

| Claim | Source | Status |
|---|---|---|
| Matched alert budget: VISHWAS catches **64% of busts against 55%** | pack v2 §4 operational table, 10% budget: POD 0.641 vs 0.546 | OK |
| Removing the rainfall forecast **raises** the score, 0.728 → 0.731 | pack v2 ablation table | OK — this is the evidence answer to "you're just predicting heavy rain" |
| Ensemble spread is exactly 0.00 mm on **189,758** test rows — a third of the set, one tie it cannot rank | pack v2 §6, CLAUDE.md MET METRICS | OK — now the fig4 caption |
| Three defects found and fixed in our own work | pack v2 §8 | OK |

## Still not on the deck, deliberately

Six slides is the binding constraint. These are strong and have no room:

- **`fig8_shap_cases_driest.png`** — pack v2 calls it "the strongest single slide". Three forecasts where the ensemble said 0.0 mm, VISHWAS flagged anyway, and 13-22 mm fell. Its core fact (the 189,758-row tie) **is** on the deck, as the fig4 caption. The figure itself is the first thing to add to the 12-slide internal deck.
- **`fig9_reliability.png`** and the calibration table — resolution 1.4x the incumbent's. In the speaker notes only.
- **Spread-only ablation** (0.562 vs 0.565 for plain spread) — "the algorithm adds nothing; the information does". Excellent Q&A answer, no slide room.
- **fig7_shap_global**, fig2_deciles, fig3_map.
