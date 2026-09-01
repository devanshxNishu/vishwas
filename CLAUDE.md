# VISHWAS — Forecast Confidence Intelligence
### Team Hellfire Labs · SIH26079 · Smart India Hackathon 2026
विश्वास, "confidence" — knowing when not to trust the forecast.

CHECKER STATE, until team selection on 3 Sep 2026.
scripts/check_docs.py exits 1 by design. The Team ID guard fires on 7 hits
across 3 files because the ID is issued only after selection at the internal
hackathon. This is the rule working. DO NOT delete it, and do not "fix" the
placeholders by inventing an ID.

AFTER SELECTION: paste the real Team ID into the deck and the site footer, then
delete this block. From that point the guard must NOT fire, and a hit means a
build is carrying a placeholder — which is the failure it exists to catch.

PROBLEM-STATEMENT FIDELITY — FOUR OPEN ITEMS, RAISED 2026-08-27.

VERBATIM PS TEXT — RETRIEVED 2026-08-31 from https://www.sih.gov.in/sih2026PS
(official SIH portal, "Problem Statement Details" modal for SIH26079). This is
the authoritative text. Do not paraphrase it in any deck, doc or speaker note
without checking it against this block first.

  Problem Statement ID:    26079
  Problem Statement Title: AI-Based Forecast Bust Detection for Medium-Range
                           Weather Forecasts
  Organization:            Ministry of Earth Sciences (MoES)
  Department:              National Centre for Medium Range Weather
                           Forecasting (NCMRWF)
  Category:                Software
  Theme:                   Smart Automation
  Youtube Link:            (blank)
  Dataset Link:            (blank)
  Contact info:            (blank)
  Submitted Idea(s):       0/500
  Deadline for Idea Submission: 20 September 2026

  Description:
  • Problem Statement Medium-range weather forecasts sometimes show large
    errors during rapidly evolving systems such as monsoon depressions, heavy
    rainfall events, western disturbances, cyclones, heat waves and
    break/active monsoon phases. Such forecast failures, or 'forecast busts',
    can affect operational decision-making.
  • Challenge The challenge is to develop an AI/ML-based system that can
    identify regions and lead times where the forecast is likely to have high
    uncertainty or large error. The system should compare current NWP forecast
    patterns with historical forecast error behaviour and provide a forecast
    confidence indicator.

  Expected Outcome - Description Forecast confidence map - Region-wise
  confidence for Day 1 to Day 10 forecasts Forecast bust probability -
  Probability of large forecast error over different regions Error-prone area
  detection - Identification of areas where model forecast may be unreliable
  Explainable output - Key meteorological reasons for low confidence Prototype
  dashboard/API - Simple interface for operational use

WHAT THE VERBATIM TEXT SETTLES:
  • EXPLAINABILITY IS EXPLICIT. "Explainable output - Key meteorological
    reasons for low confidence" is a named deliverable. The SHAP work is
    required, not an embellishment.
  • CONFIDENCE MAP IS EXPLICIT, and the required range is DAY 1 TO DAY 10.
    Our evaluation is Day 5. State the lead-time scope honestly.
  • BUST PROBABILITY IS EXPLICIT — "Probability of large forecast error over
    different regions". Our calibrated probability output is on-spec.
  • A PROTOTYPE DASHBOARD/API IS A NAMED DELIVERABLE. Not optional polish.
  • "compare current NWP forecast patterns with historical forecast error
    behaviour" is the method the PS asks for, and is what we built.
  • THE PS DOES NOT NAME AN ENSEMBLE. It says "NWP forecast patterns", not
    NEPS/NCUM. The GEFS substitution in item 1 is therefore not a deviation
    from the letter of the PS — but NCMRWF is the department, so expect the
    question anyway.
  • THE PS DOES NOT NAME A VARIABLE, a region, a threshold, a metric or a
    dataset. Our rainfall/IMD-gauge/64.5mm/Brier choices are ours to justify.

1. WE USE GEFS; NCMRWF RUNS NEPS/NCUM. The problem owner operates India's own
   operational medium-range ensemble. We detect busts in an American one. This
   is defensible — NEPS reforecast archives are not publicly accessible, GEFS
   is the only publicly archived medium-range ensemble with a ~20-year
   reforecast, and the method is ensemble-agnostic — but it is a SUBSTITUTION,
   not a detail. State it before a judge asks, and say the pipeline points at
   NEPS the day access exists. This is the most likely first question.
2. THEME — RESOLVED 2026-08-27. SIH originally listed SIH26079 under
   DISASTER MANAGEMENT and later RE-LISTED it under SMART AUTOMATION. Both
   appear in our older docs because both were true at the time. SMART
   AUTOMATION IS CURRENT and governs the submission.
   This favours our actual result. The automation story is exact: forecasters
   assess confidence today by eyeballing ensemble spread, we measured that
   manual method against India's own gauge observations, and it explains under
   1% of forecast error. We automate a judgement that currently has no
   evidence behind it.
   TECHNICAL CONSEQUENCE, NOT JUST FRAMING: under an automation framing FALSE
   ALARMS COST MORE than missed events. An automated assistant that cries wolf
   gets switched off, and then it helps nobody. When P14 picks the operating
   point, weight FAR/precision more heavily than raw POD, and say why. Under a
   disaster-management framing the trade-off would have gone the other way.
3. DETECTION, NOT CORRECTION. The PS title says bust DETECTION. Paras's
   metrics guide sketches an "AI-adjusted forecast" map. We do not adjust
   forecasts and must not imply we do.
4. OPERATIONAL VIABILITY IS PROBABLY SCORED. This file calls real-time an
   "optional live dashboard". For an operational forecasting centre under a
   Smart Automation theme, "could this run at NCMRWF tomorrow" is likely a
   scoring question. The core claim still does not depend on it.

PROJECT: Ministry of Earth Sciences problem SIH26079, Smart India Hackathon
2026. We are NOT building a weather forecast. We build a model that predicts
WHEN the operational forecast will be badly wrong (a "forecast bust"). Output
is a forecast-confidence map over India, lead times Day 1-10.

SUCCESS CRITERION: Operational forecasters estimate confidence using ensemble
spread, but the spread-skill relationship is weak (r typically 0.3-0.6). That
weakness is our opening. Success = our learned confidence signal beats ensemble
spread, measured by ROC-AUC, PR-AUC, and precision within the top-10% flagged.

DATA (all public, anonymous S3, no credentials, no paid access):
- GEFSv12 reforecast (ensemble): s3://noaa-gefs-retrospective/
- GEFS operational (ensemble):   s3://noaa-gefs-pds/
- ERA5 truth:                    s3://nsf-ncar-era5/   (no registration needed)
- IMD gridded rainfall (historical): imdlib.get_data() — the truth source.
  VERIFIED 2026-08-27, all four VERIFY-IMD conditions pass. See TRUTH
  SOURCE below.
- DO NOT plan around IMD AWS/ARG station data — IMD closed public portal
  access around May 2025. Unavailable to us.

TRUTH SOURCE — CORRECTED 2026-08-26. READ ALL OF THIS BEFORE TOUCHING TRUTH.

There are TWO IMD endpoints and the earlier session tested only ONE of them.

  WRONG ENDPOINT (correctly found unusable, tested 2026-08-25):
    imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain_ind0.25_%y_%m_%d.grd
    Rolling REAL-TIME archive. Probed: 2015/2019/2020/2021 -> HTTP 404;
    2022-2026 -> HTTP 200, 69660 bytes. Coverage starts ~2022, so it does
    NOT overlap the 2000-2019 reforecast. imdlib.get_real_data() hits this.

  RIGHT ENDPOINT (the truth source — VERIFIED 2026-08-27):
    imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html
    0.25 deg daily gridded rainfall, 1901-2024, yearly .grd files
    (float32, ~25 MB/yr), 135 lon x 129 lat, first point 6.5N/66.5E,
    last 38.5N/100.0E, units mm. imdlib.get_data() hits this one.

WHY THE SWITCH IS WORTH MAKING:
  - Full overlap with the reforecast (2000-2019).
  - ~500 MB total instead of ~60 GB of ERA5.
  - Gauge-based OBSERVATION, not reanalysis. Removes the "ERA5 assimilated
    model physics that partly overlaps GEFS" weakness we would otherwise
    have to disclose on every single number we report.
  - It is MoES's own product, and MoES owns this problem statement.

STATUS: VERIFIED IN CODE 2026-08-27. src/imd_truth.py is the loader,
src/verify_imd.py re-runs the checks below on demand.

VERIFY-IMD — all four passed 2026-08-27:
  1. PASS. imdlib 0.1.21 installs clean on the venv (Python 3.9.6) from pure
     wheels, no GDAL. (The older imddaily package needed GDAL and failed to
     build; imdlib is a DIFFERENT package. requirements.txt now lists imdlib.)
  2. PASS. imdlib.get_data("rain", 2015, 2015) returns a real 2015 grid,
     25,425,900 bytes = 135 x 129 x 365 x 4, so the float32 decode divides
     exactly. Values 0.00 to 679.22 mm. 2012 and 2018 also verified, and
     2012 correctly reports 366 days.
  3. PASS. Colocation is EXACT float equality, zero interpolation, asserted
     in colocation_index(). BUT THE DOMAIN SHRINKS TWICE OVER:
       - Geometry: IMD spans 6.5-38.5N / 66.5-100.0E, so our 5.0/5.5/6.0N
         AND our 39.0/39.5/40.0N rows, plus 65.0/65.5/66.0E, fall outside.
         NOTE THE NORTHERN EDGE — it is easy to remember only the south and
         west. 621 of 5041 points drop on geometry alone (12.3%).
       - Land mask: 1252 points survive, 24.8% of the full box, 28.3% of
         the in-domain box.
     WE STATE THE 24.8% OURSELVES. A judge must not be the one to find it.
  4. PASS. Ocean/no-gauge points are undef -999 and become NaN in
     imd_truth.daily_rain(). NEVER 0.0 — a -999 read as zero rainfall would
     silently dry out the whole ocean half of the box. The undef footprint
     is identical across sampled days, so the mask is time-invariant.
  PHYSICS CHECK (beyond the four): July 2015 all-India mean 9.18 mm/day vs
  January 0.27 mm/day, a factor of 35. The monsoon is present in the decode.

IMD OPERATIONAL NOTE: imdpune.gov.in is flaky. The first get_data() call of
a session may die with a TLS connection reset; an immediate retry works.
The host also resets any client that offers HTTP/2 in ALPN (curl fails,
Python's ssl does not). Wrap bulk downloads in a retry. One reset is NOT
evidence that IMD is down. Transfer is ~25.4 MB/year at 1.2-3.0 MB/s, so a
year lands in 9-21 seconds and the whole 2000-2019 record in about 8
minutes.

DOMAIN CHANGE IS A CONFOUND WHEN COMPARING TO OLD NUMBERS. The provisional
conditional +0.076 was measured on ERA5, which carries values over ocean.
IMD is land-only. Any IMD number therefore differs from +0.076 on TWO axes
at once — truth source/domain AND whatever else changed. To attribute a
move to seasonality, hold the domain fixed: run the ERA5 path restricted to
the IMD land mask as the controlled comparison.

ERA5 IS NOW OPTIONAL — KEEP IT WORKING, DO NOT DELETE IT. It stays the
fallback if VERIFY-IMD fails, and it is the only route if we ever verify a
non-rainfall variable. ERA5 facts, still true: total precipitation is
LSP + CP (there is no single `tp` in e5.oper.fc.sfc.accumu); it is a
REANALYSIS product carrying known biases over India, so any number built on
it must say so; files are chunked (1, 12, 721, 1440) — one chunk is a whole
global field, so India-box subsetting saves NO transfer. Pull whole files,
use, delete. Budget ~510 MB per half-month per variable pair.

NEVER MIX TRUTH SOURCES IN ONE COMPARISON. The baseline and the model must
be scored against the SAME truth. A baseline measured on ERA5 against a
model scored on IMD is not a comparison, and a meteorologist judge will
say so out loud.

REAL-TIME IS NOT NEEDED FOR THE CORE CLAIM. We train AND test entirely inside
the 2000-2019 reforecast using a time-based split. Operational GEFS is for an
OPTIONAL live dashboard only. If real-time access breaks, the result still
stands. Do not let dashboard work block the evaluation.
Its real layout is NOT gefs.YYYYMMDD/{HH}/pgrb2a/ — probed 2026-08-25: the
2017-era files sit directly under {HH}/ with pgrb2a in the FILENAME
(gec00.t00z.pgrb2af000), and the current era uses {HH}/atmos/pgrb2ap5/.
Coverage starts 2017-01-01 and carries 31 members, so it neither overlaps nor
is comparable to the 5-member 2000-2019 reforecast.
ARCHIVE RANGE IS 2000-2019. reforecast/2020/ holds one misfiled 2010
date. Never write range(2000, 2021).

ENSEMBLE SIZE — WAS A KNOWN WEAKNESS, CHECKED 2026-08-27. See result below.
The reforecast carries only 5 members (c00 + p01-p04), rising to 11 once
weekly. Operational GEFS carries 31. A 5-member spread is therefore a NOISY
estimate of true ensemble spread, and our baseline is built on it. That cuts
both ways: a noisy baseline is easier to beat, and a judge will spot it.
SENSITIVITY CHECK — DONE 2026-08-27, src/05_ensemble_size.py. Same 12 dates,
same IMD truth, same metric, only the ensemble size varies:
    5-member  (c00,p01-p04)   pooled +0.619   conditional +0.040
                              95% CI +0.019 to +0.060
    11-member (all)           pooled +0.663   conditional +0.041
                              95% CI +0.016 to +0.065
    CHANGE 5 -> 11:           pooled +0.044   conditional +0.001

RESULT AS FIRST REPORTED: the conditional baseline moves +0.001, i.e. not a
small-ensemble artefact.

BUT THAT +0.001 IS THE SAME WET-FILTER ARTEFACT — CHECKED 2026-08-27.
Re-run under the robust filters, 5 -> 11 does move the baseline:
    OR filter, all bins (as reported)   5: +0.040   11: +0.041   d +0.001
    OR filter, drop driest decile       5: +0.087   11: +0.099   d +0.012
    both forecast AND truth > 0.5 mm    5: +0.079   11: +0.095   d +0.016
    both forecast AND truth > 1.0 mm    5: +0.076   11: +0.089   d +0.013
CORRECTED READING: more members DO make the baseline modestly better —
about +0.015 on a base near +0.09, so roughly a 15-20% relative improvement
from 5 to 11. That is small and does NOT threaten the conclusion (even a
baseline at +0.12 is ~1.4% of variance), but it is NOT zero. Say "a small
positive effect that does not change the conclusion", NOT "no effect" — the
second version is refutable in one command and the first is not.

STILL WORTH A SLIDE, because the shape of the story survives the correction:
the POOLED number rises sharply with more members (+0.044) while the
CONDITIONAL number rises only slightly (+0.001 to +0.016 depending on
filter). More members clean up the estimate of the wet/dry gradient —
which is what the pooled number mostly measures — but they add nothing to the
within-regime information, which is what a confidence signal actually needs.

CAVEAT THAT MUST BE STATED: 5 -> 11 is not 5 -> 31. Operational GEFS carries
31 members. This bounds the direction and rough size of the effect over the
range the reforecast can actually show us; it does not extrapolate to 31, and
we must not claim it does.

CONSTRAINTS: Subset aggressively — India domain only (lat 5-40N, lon 65-100E),
5 ensemble members, few variables, START WITH 5 YEARS NOT 20 (the archive is
terabytes). No GPU. Team is Semester 3 CSE/AI-ML + ECE — readable code, not
clever code.

FEATURE SOURCE RULE — HARD, NO EXCEPTIONS. ALL predictive features come from
GEFS reforecast fields. ERA5 and IMD are TRUTH ONLY and must never appear as
features. A feature drawn from the truth dataset is leakage: ERA5 is an
analysis that assimilated the observations we are scoring against, so any
ERA5-derived predictor lets the model peek at the answer. Precipitable water
therefore comes from GEFS pwat_eatm, NOT ERA5 TCWV. The ERA5 TCWV plan is
DROPPED.

LEAKAGE — TWO LIVE RISKS, ONE ALREADY IN THE CODE. FIX BEFORE TRAINING.

1. CLIMATOLOGY LEAK — PRESENT IN THE CODE NOW (02_features.py, finalize()).
   finalize() builds the pwat/cape/precip anomalies against a climatology
   taken over the ENTIRE concatenated table — training period AND test
   period together. Every test row's anomaly therefore encodes the test
   period's own mean. This is precisely what our time-based-split rule
   exists to prevent, and it is INVISIBLE in the metrics: it inflates them
   silently rather than failing loudly.
   FIX: compute the climatology on the TRAIN window only, persist it, and
   apply that stored climatology to the test window. A climatology is a
   fitted parameter, not a description of the data you are scoring.

2. ERROR-CLIMATOLOGY LEAK — PLANNED, NOT YET WRITTEN.
   "regional error climatology" sits in the FEATURES list. It is derived
   from |forecast - truth|, so it is a TRUTH-DERIVED feature and collides
   head-on with the FEATURE SOURCE RULE above. It is defensible ONLY in one
   form: "the error record we already had before the test period began" —
   computed strictly on the training window and then frozen. Computed over
   the whole record it is a direct read of the answer.
   If it ships, it is train-only, frozen, and the report says so plainly.

VARIABLE LIST — CORRECTED, PROBED 2026-08-25:
  hgt_pres_abv700mb   500 hPa geopotential -> gradient feature
  ugrd_pres_abv700mb  500 hPa u wind -> shear
  vgrd_pres_abv700mb  500 hPa v wind -> shear
  pwat_eatm           precipitable water (entire atmosphere)
  cape_sfc            surface
  apcp_sfc            surface, truth-adjacent — accumulated precipitation
WARNING: the plain *_pres files (hgt_pres, ugrd_pres, vgrd_pres) stop at
800 mb and contain NO 500 hPa data. Their .idx lists only 1000/975/950/925/
900/850/800 mb. Everything at and above 700 mb is in the *_abv700mb files.
Using the plain files would download terabytes and yield none of the 500 hPa
fields the gradient and shear features are built on.

FEATURES: ensemble spread (both a feature AND the baseline to beat), lead time,
season, region, 500hPa geopotential gradient, precipitable water anomaly, wind
shear, CAPE, regional error climatology.

STORAGE — WE NEVER HOLD THE FULL ARCHIVE. The pipeline STREAMS each init
date: fetch the thinned GRIB messages, compute features, append one row per
(gridpoint, lead time) to the feature table, then DISCARD the raw GRIB.
Peak disk is one init date (~310 MB), not the whole download. Persistent
storage is the FEATURE TABLE ONLY — a few hundred MB. Nobody should plan
around 87 GB or 323 GB of disk; those are TRANSFER volumes, not disk needs.

WIND SHEAR — DECIDED 2026-08-26, IMPLEMENTED AND VERIFIED 2026-08-27.
The feature list says "wind shear", and vertical shear needs TWO levels,
so 500 hPa alone was never enough. flow500_deformation is horizontal
deformation of the 500 hPa flow. That is a real predictor, it is correctly
named in the code, and it must NEVER be relabelled "wind shear" in the
report or on a slide — shear_500_850 is now the column that means shear.
DECISION: add 850 hPa u/v from the PLAIN ugrd_pres/vgrd_pres files (850 mb
sits below the 800 mb cutoff, so it IS in the plain files). True 500-850
shear is meteorologically meaningful for convective organisation and for
monsoon depression structure.
STATUS: IMPLEMENTED 2026-08-27. 01_fetch.py fetches 850 mb via wanted_850mb();
02_features.py emits u850_mean, v850_mean and shear_500_850. Verified on
20000105: shear mean 11.1 m/s, and it has the right LATITUDE STRUCTURE for
January — 5.0 m/s at 5-15N versus 15.5 m/s at 25-35N, which is the
subtropical jet. Row count and grid alignment unchanged.

COST — THE 1.6% ESTIMATE WAS WRONG BY A FACTOR OF ~35. MEASURED 2026-08-27:
the addition costs +176 MB per date on a 292 MB baseline, i.e. +60%, not
+5 MB / +1.6%. Per date: 292 MB -> 468 MB.
  WHY: the two file families are on DIFFERENT GRIDS. Decoded and confirmed —
  *_abv700mb messages are 0.5 deg (361 x 720, ~0.15-0.21 MB each), the plain
  *_pres messages are 0.25 deg (721 x 1440, ~0.79-0.84 MB each). So every
  850 hPa message is ~4-5x the bytes of the 500 hPa message beside it.
  WE THEN THROW 3/4 OF IT AWAY, because to_india_grid() colocates onto the
  0.5 analysis grid. There is no way around this: a GRIB message is atomic,
  so byte-range requests cannot subset inside one.
  BULK RUN CONSEQUENCE: 5 years of Wednesdays (~261 dates) goes from ~76 GB
  to ~122 GB, and at 4.5 MB/s from ~4.7 h to ~7.6 h. Re-plan P6 around the
  larger number, and re-confirm the shear is worth 3 extra hours before
  starting a 20-year run.
THIS HAD TO LAND BEFORE THE BULK RUN. Adding it afterwards means refetching
every date.

LEAD-TIME RESOLUTION: the deliverable is a Day 1-10 confidence map, so DAILY
steps (24h, 48h ... 240h) are enough. Do not pull the 3-hourly steps.

MIXED-SCHEMA TRAP IN features_parts/ — FOUND 2026-08-29, NOT YET TRIGGERED.
If the 5-year run fetches new dates WITHOUT the 850 hPa columns while the
existing 104 parts have them, finalize() will NOT catch it: its guard checks
only ANOMALY_COLUMNS + CLIMATOLOGY_KEYS, so the 850 columns fall outside it,
pd.concat silently fills them with NaN for the new dates, and
HistGradientBoostingClassifier handles NaN natively. Result: a feature that is
real for 104 dates and NaN for 156, with no error anywhere.
EITHER keep 850 hPa for every date (recommended — the parts are only 486 MB;
the 27.4 GB is transfer time, ~1.7 h overnight, and skipping it destroys data
already fetched) OR strip the three columns from the existing parts first so
the schema stays uniform. NEVER mix.

P11 ABLATIONS — 2026-08-29. All five, same split/labels/seed.
  FULL 0.728 | drop month 0.722 (-0.006) | drop precip 0.731 (+0.003)
  drop 850hPa 0.726 (-0.002) | spread only 0.562 (baseline 0.565)
  MONTH PASSES: -0.0059, far under the 0.02 line fixed in advance. The model is
  NOT learning the calendar; 0.728 is final, not provisional.
  Two results worth quoting. Dropping the rainfall forecast entirely makes it
  slightly BETTER — so the model does not ride the magnitude artefact. And a
  learned model given ONLY spread scores 0.562 vs 0.565 for spread as a plain
  ranking: none of our edge is gradient boosting being clever, all of it is
  having more information.
  Permutation importance: pwat_mean +0.086, precip_spread +0.066,
  precip_mean +0.061 — moisture plus ensemble disagreement.

FIRST TRAINED MODEL — 2026-08-29, 20:45. THE PROJECT NOW HAS A RESULT.
Train 2018 (39 dates fitted, 13 held as validation) / test all 52 Wednesdays of
2019. Labelled table 1,302,080 rows; the TEST SET is 651,040 of them over 1,252
gauge-observed land gridpoints, Day 1-10. IMD gauge truth, region-scope bust
thresholds, HistGradientBoostingClassifier, nothing tuned.

                          baseline (spread)   model
  ROC-AUC pooled                0.885         0.909   <- ARTEFACT, DO NOT QUOTE

  "DO NOT QUOTE" REFINED 2026-08-30 — the absolute form was wrong. The rule
  bars quoting the pooled pair AS A MEASURE OF PERFORMANCE; that is what would
  commit, in our own work, the error this project accuses the incumbent of.

  THE SANCTIONED EXCEPTION IS WITHDRAWN — 2026-08-30, P18. THE RULE IS AGAIN
  ABSOLUTE: the pooled pair appears in NO figure, slide, table, abstract or
  spoken line. It survives only in this file and in the audit trail, as the
  thing being ruled against.
    Earlier on 30 Aug this file granted fig4_inversion.png a licence to print
    0.909 vs 0.885 in provenance text, on the argument that "+0.023" is
    meaningless without them. THE PROJECT OWNER DECIDED OTHERWISE and the
    shipped figure does not print them: it names only the stratified pair and
    describes the left bar in words. Verified by opening the PNG and by
    unzipping deck v17 — the pooled pair appears nowhere in the deck.
    THIS PARAGRAPH IS WHY THE AMENDMENT MATTERS. A rule permitting what the
    project has since decided against WILL be acted on by a future session,
    which would quietly reintroduce the number into the figure. src/11_inversion.py
    now renders the shipped footnote and carries the same warning at the call
    site. If a future figure wants this licence, it does not have it.
  ROC-AUC stratified            0.565         0.728   <- THE RESULT
  PR-AUC lift over base rate    6.29x         7.60x

  stratified margin +0.1634, 95% CI +0.1080 to +0.1926 (cluster bootstrap,
  52 forecast dates). Entire interval above zero.

THE FINDING IS THE INVERSION. Pooled, the model beats spread by only +0.023.
Stratified, by +0.163 — seven times larger. Pooled scoring gives spread 0.885
for free by letting it track rainfall amount; remove that and it collapses to
0.565, barely above chance. The fair comparison FAVOURS us, which is rare and
worth saying out loud.

ROBUSTNESS. Ahead in all 8 rainfall bins (+0.079 to +0.252), largest edge in
the driest conditions (0.835 vs 0.583 — the "confidently dry and it rained"
failure), still +0.097 in the heaviest bin where 41% of forecasts bust.
QUOTE +0.13 TO +0.16, not +0.163 alone. The "forecast AND truth > X mm"
variants in the panel condition on the OUTCOME — they delete every
forecast-said-dry-it-poured bust and every forecast-said-rain-nothing-came
bust, so they understate the model for reasons unrelated to quality. Fair for
the Phase-1 correlation, NOT fair for bust-prediction AUC.

THE BIN-WEIGHTING QUESTION, AND ITS ONE-SENTENCE ANSWER — SETTLED 2026-08-30.
A sharp judge will work this out and it deserves an answer that is ready, not
derived on the spot. THE QUESTION: stratified_auc() is n-weighted, and bin 0
holds 208,065 of 651,040 test rows because qcut collapsed the zero-rainfall
mass into it. So roughly a THIRD of the headline 0.728 comes from the one bin
where the incumbent is degenerate — ensemble spread is exactly 0.00 mm on 91%
of that bin, only 64 distinct values across it. Is the margin an artefact of
weighting a bin where the baseline cannot rank at all?
  THE ANSWER, already computed — it is the "drop the driest bin" row of the
  robustness panel (ablations/a_full.log), and it is where the published low
  end of +0.132 comes from:
      all bins (headline)   baseline 0.565   model 0.728   margin +0.1634
      drop the driest bin   baseline 0.539   model 0.671   margin +0.1322
  SAY THIS: "Drop the bin where spread is degenerate and the margin goes from
  +0.163 to +0.132 — still an edge, and still ahead in every remaining bin."
  THE RANGE SPANS TWO VARIANTS, NOT FIVE — CORRECTED 2026-08-30, P18. The panel
  prints five rows but three are [truth-filtered] and excluded from the verdict
  range for the reason stated just above. +0.13 to +0.16 is exactly these two:
  "all bins" and "drop the driest bin". fig4's footnote said "five wet-point
  definitions" and was wrong; it is corrected in src/11_inversion.py. NOTE THE
  ASYMMETRY: Phase 1's 0.17-0.90% variance range DOES span five wet-point
  definitions, because for a spread-error CORRELATION the truth-filtered
  variants are a fair sensitivity check. Five is right on slide 6 and wrong on
  fig4. Do not "fix" slide 6.
  Note the baseline FALLS to 0.539 when that bin is removed, so the driest bin
  was helping the incumbent's score, not ours. And it is not a hidden variant:
  it is one of the two definitions the +0.13-to-+0.16 range is built from.
  DO NOT concede the premise that bin 0 should be dropped. It is a third of
  real forecasts, the busts in it are the confidently-dry failures this system
  exists to catch, and the incumbent's inability to rank them is a finding
  about the incumbent — not a reason to delete the cases from the evaluation.

CLOSED 2026-08-29: the `month` ablation ran and PASSED (-0.0059, tolerance
0.02). See P11 ABLATIONS above. 0.728 is final. Any document still calling it
provisional or listing the month ablation as outstanding is stale.

================================================================================
PHASE 3 — COMPLETE 2026-08-30. Explainability, calibration, demo, metrics.
================================================================================

MODEL ARTIFACT — models/vishwas_model.joblib (07_model.py now persists it).
Holds the fitted estimator, the 23 feature names IN ORDER, and the config
(study window, validation dates, seed, sklearn version, row counts, timestamp).
A fitted estimator without its column order is not reloadable, so they travel
together. VERIFIED: it reloads and reproduces model_predictions.parquet to a
max score difference of 0.00e+00 across all 651,040 test rows. models/ is
gitignored. Nothing downstream needs to retrain; 09/10 load this file.

DEMO DATE — CHOSEN EMPIRICALLY, NOT ASSUMED. src/08_pick_date.py ranks all 52
test dates on TRUTH ALONE: observed bust rate, plus a spatial-coherence score
(share of bust cells touching another bust cell — a real synoptic event is
contiguous, scatter is not). Model AUC is printed as context and deliberately
EXCLUDED from the ranking; ranking dates by our own skill and showing the
winner is cherry-picking and a judge will ask.
  PICK: init 20190731 (issued Wed 31 July 2019), Day 5, valid 5 Aug 2019.
  Bust rate 36.3% (454/1252) at Day 5 — highest of the 52 dates, and highest
  across all leads too (27.5%). Spatial coherence 0.99. Runner-up 20190724 at
  28.0%. Monthly means confirm the Jul-Sep prior: Jul 23.9%, Sep 15.2%,
  Aug 12.4%, against 0.2-1.0% in DJF.
  OPERATING POINT ON THE MAP: p >= 0.1535, the global top-10% threshold fitted
  ONCE on the whole test set and applied unchanged. NOT re-fitted per date —
  that would manufacture a flattering picture. 547 flags, 395 hits, 152 false
  alarms, 59 misses; precision 0.72, recall 0.87 ON THIS DATE ONLY.
  CAVEAT TO HAVE READY: at Day 3 on this date the model is marginally BEHIND
  spread (0.826 vs 0.831). Single-date per-lead numbers are noisy. Never
  defend the date on its metrics — it was chosen on observed busts.
  figures/fig6_confidence_map.png. Panel B uses IMD's own daily rainfall
  classes, not a linear ramp: one 390 mm cell washes the map pale otherwise.

SHAP — WORKED CLEANLY, NO SUBSTITUTION. shap 0.49.1 TreeExplainer supports
HistGradientBoostingClassifier natively. Additivity verified against the raw
log-odds to 4e-13. Sample 6,000 random test rows. src/09_shap.py.
  GLOBAL, ranked by MEDIAN |SHAP|: precip_spread, precip_mean, pwat_mean —
  the same top three as permutation importance, Spearman +0.775.
  RANKED BY MEAN |SHAP| THEY DISAGREE, AND THE REASON IS THE POINT.
  Mean promotes v850_mean to #2 and cape_anomaly to #4; permutation ranks them
  #16 and #17 (+0.0022, +0.0015). For those features the top 1% of rows carry
  71-83% of all |SHAP| mass, with single-row contributions up to 610 log-odds —
  saturated tree leaves. For pwat_mean and precip_mean the top 1% carry 5-8%.
  The mean ranks a feature by its rarest rows; the median by the typical
  forecast. Spearman drops to +0.670 on the mean. fig7 plots both.
  Permutation importance was RECOMPUTED here over all 23 features (CLAUDE.md
  had only three recorded, not enough to answer "do they agree"). It
  reproduces P11: pwat_mean +0.094 vs +0.086, precip_mean +0.067 vs +0.061,
  precip_spread +0.065 vs +0.066.

DRIEST-BIN SHAP CASES — THE BEST EXPLAINABILITY SLIDE WE HAVE.
figures/fig8_shap_cases_driest.png, via `09_shap.py --case-driest-bin`.
The driest precip_mean decile is 208,065 of 651,040 test cases, forecast
rainfall 0.000-0.009 mm, bust base rate 0.15%. The three highest-confidence
correct bust calls in it:
    12 Jun 2019 D1  0.0 mm forecast -> 13.2 mm fell   p=0.17  (109x bin rate)
     5 Jun 2019 D4  0.0 mm forecast -> 16.1 mm fell   p=0.14  ( 95x)
    22 May 2019 D10 0.0 mm forecast -> 22.5 mm fell   p=0.12  ( 82x)
  Ensemble spread is EXACTLY 0.00 mm on all three, tied with 189,758 other
  test rows, so the incumbent cannot rank them at all.
  THE SHAP STRUCTURE CARRIES THE ARGUMENT: in all three, pwat_mean is the
  largest POSITIVE contributor (+2.80, +1.95, +2.47) and precip_spread = 0 is
  the largest NEGATIVE one (-1.35, -1.28, -1.28). The model correctly learned
  that zero spread argues against a bust, and flagged anyway because the
  moisture signal overwhelmed it. That is the system overruling the incumbent
  using information the incumbent does not have.
  SAY p = 0.17 WITH ITS CONTEXT. In absolute terms it looks weak; against a
  0.15% base rate it is ~109x. The caption states this so nobody has to
  discover it.
  The generic highest-confidence cases (fig8_shap_cases.png) are all the
  "forecast said rain, less fell" mode. Prefer the driest-bin figure.

CALIBRATION (P12) — src/10_calibration.py, figures/fig9_reliability.png.
Isotonic and Platt fitted on the VALIDATION slice only (13 interleaved 2018
dates, 162,760 rows, base rate 5.43%). Never on test.
  Brier decomposed, 10 equal-width bins, 651,040 test rows:
    uncalibrated   Brier 0.04218  REL 0.00014  RES 0.01777  BSS +0.3028
    + ISOTONIC     Brier 0.04217  REL 0.00006  RES 0.01758  BSS +0.3029
    + Platt        Brier 0.04218  REL 0.00015  RES 0.01778  BSS +0.3027
    spread+isotonic Brier 0.04749 REL 0.00012  RES 0.01225  BSS +0.2148
    climatology     Brier 0.06060 REL 0.00011  RES 0.00000  BSS -0.0018
  THE BASELINE GETS THE IDENTICAL ISOTONIC FIT. Spread is in millimetres;
  scoring a rainfall amount against a Brier score would hand us the win free.
  WAS THE RAW MODEL ALREADY CALIBRATED? TWO-SIDED, BOTH HALVES MATTER.
  In aggregate YES: REL 0.00014 against UNC 0.06049 is 0.23% of the total, and
  Brier barely moves. Between p=0.0 and 0.8 the raw curve tracks the diagonal.
  AT THE TAIL, NO. The raw model says p >= 0.9 on 72 test cases and only 5.6%
  of them bust. Typical rows there have forecast 0.00 mm, spread 0.00 mm and
  0.00 mm observed — maximally certain of a bust where nothing happened. These
  are the SAME saturated leaves the SHAP tail diagnostic found; two independent
  analyses landed on one defect. It is invisible in an average over 651,040
  rows and it is the end of the scale a forecaster acts on hardest.
  ISOTONIC WINS AND PLATT CANNOT. Isotonic caps output at 0.75 because PAVA
  pools the violating region downward; Platt (slope 0.946, intercept -0.119,
  near-identity) can rescale a monotone region but not flatten it, and still
  emits p >= 0.9 on 67 cases of which 1.5% bust.
  THE EMPTY 0.8-1.0 BINS ARE DELIBERATE, NOT MISSING DATA: the calibrated
  system declines to claim a confidence it never earned on held-out data.
  RESOLUTION is the informativeness term: 0.01758 vs 0.01225 for calibrated
  spread, 1.4x. Calibration does NOT change the ranking, so 0.728 vs 0.565 is
  untouched — what changes is whether the number can be believed.
  The three-term identity BS = REL - RES + UNC is exact only for a discretised
  forecast; the within-bin variance residual (~7e-04, five times REL) is
  computed and labelled, not swept up as rounding.

MET METRICS (P14) — src/08_met_metrics.py, imports src/met_metrics.py unchanged.
Event = BUST, never rain. Operating point chosen on VALIDATION: top 10% is
p >= 0.1271. Frozen onto test it fires at 11.62% (2019 is wetter: 6.47% vs
5.43%), POD 0.673, FAR 0.625, CSI 0.317, ETS 0.278.
  HEAD-TO-HEAD AT A MATCHED ALERT BUDGET, top 10% of test cases:
    VISHWAS          POD 0.641  FAR 0.586  CSI 0.336  ETS 0.300
    ensemble spread  POD 0.546  FAR 0.647  CSI 0.273  ETS 0.235
  THE SENTENCE: "Given the same number of alerts a forecaster would tolerate,
  VISHWAS catches 64% of busts against the current method's 55%." Stratified
  within rainfall magnitude: 19% against 15%.
  TIES ARE THE TRAP. Ensemble spread is exactly 0.00 mm on 189,758 test rows —
  a third of the set is one tie, and in the driest decile it is 91.2% of the
  bin with only 64 distinct values across 208,065 cases. A quantile cut of 0.00
  flags the whole bin: the first run of this script reported the baseline
  spending 38.78% of cases against a 10% budget, which silently voided the
  comparison. Ties are now broken by RANDOM within-tie order on a fixed seed —
  the only neutral choice, and the honest model of a score that cannot rank.
  Pooled, no alert comes from the tied block (those rows sit at the BOTTOM of
  the ranking); the tie only bites inside the driest bin.
  PRECISION IS WEIGHTED OVER RECALL and the script says why: Smart Automation
  theme, an assistant that cries wolf gets switched off. 5% budget buys +0.173
  precision for -0.187 POD; 20% costs -0.158 precision for +0.151 POD.
  cluster_bootstrap_margin() in 07_model.py is hardcoded to stratified_auc, so
  it CANNOT compute a POD or CSI difference. 08 uses a metric-agnostic bootstrap
  copying its design, AND imports the original unchanged for the AUC margin.
  ETS IS computable from the four counts: H_rand = (H+FA)(H+M)/N. Paras's guide
  says otherwise and is wrong on that point.

TEAM ROLES AND CREDIT — CORRECTION PENDING THE 20 SEP REBUILD, P23 2026-08-31.

Slide 6's B.Tech line in the PRESENTED deck reads:
    Devansh (model and evaluation) · Ankit (data pipeline)
Ankit did not build the fetch and feature pipeline; Devansh did. A rebuild
carrying the fix was produced on 31 Aug and DELIBERATELY DISCARDED, because its
only change was to move "data pipeline" to Devansh and leave Ankit with a bare
name and no role at all. The presented deck is left unchanged as the record of
what was actually in the room.

THE NEXT BUILD MUST READ:
    Devansh (data pipeline, model and evaluation) ·
    Ankit (problem-statement tracking, option analysis)

ANKIT'S ACTUAL CONTRIBUTIONS, which is what the corrected line is naming:
  • Caught that SIH had re-listed SIH26079 from DISASTER MANAGEMENT to SMART
    AUTOMATION — the save that stopped a deck built on flood framing from
    going out. It changed the primary user, the framing, and the direction the
    operating point is tuned (see item 2 of the PS fidelity block: under an
    automation framing FALSE ALARMS COST MORE, which is why P14 weights
    precision over POD).
  • Ran the comparison against the secondary problem statement, which is how
    the team knew what it was choosing against when it committed to this one.

NEVER SHIP A ROSTER LINE WITH A NAME AND NO ROLE. Removing a wrong credit is
only half the correction; the other half is naming what the person actually did.

ALREADY APPLIED ELSEWHERE: site/index.html carries the corrected roster (Ankit
= "scope & problem tracking"), and data/VISHWAS-HANDOFF.md's team table was
fixed in the same commit. scripts/check_docs.py now forbids the stale string so
it cannot come back, with deck/VISHWAS_SIH.pptx and .pdf EXEMPT — that file is
a historical record and must keep its original text.


FIGURES — CURRENT SET. fig1_collapse, fig2_deciles, fig3_map (reference visual
language), fig4_inversion (REGENERATED 30 Aug, src/11_inversion.py),
fig6_confidence_map, fig7_shap_global, fig8_shap_cases{,_driest,_20190731},
fig9_reliability.
  fig5_confidence_map.png DELETED 30 Aug — its caption read "initialised 26
  July, valid 31 July" while carrying the numbers for init 31 July / valid
  5 Aug. Both dates were five days early and 26 July 2019 was a Friday, not
  one of the 52 Wednesday inits. Superseded by fig6.
  fig4 was regenerated because it printed "+0.163" alone in 40pt type against
  this file's own rule, and its footnote called the sample 1,302,080 when the
  margin is computed on 651,040 test rows. Numbers were always correct.

ONE GENERATOR PER FIGURE — ESTABLISHED 2026-08-30, P18. EVERY figure in
figures/ is now reproducible from a committed script. It was not: fig1, fig2
and fig3 had NO generator at all — the image carrying the project's headline
finding could not be remade — and fig4's shipped PNG had been produced by an
ad hoc script that was never committed and hardcoded its literals, while
src/11_inversion.py rendered a DIFFERENT footnote. That divergence is closed:
11_inversion.py now renders the shipped text and computes every number in it.
  fig1  src/12_fig1_collapse.py   fig2  src/13_fig2_deciles.py
  fig3  src/14_fig3_map.py        fig4  src/11_inversion.py
  fig6  src/08_demo_map.py        fig7/fig8  src/09_shap.py
  fig9  src/10_calibration.py
  src/figstyle.py holds the shared palette and layout helpers. 11_inversion.py
  predates it and keeps its own copy of the constants, deliberately, because it
  is verified against the shipped deck image; migrate it when it next changes.
  IF YOU ADD A FIGURE, ADD ITS SCRIPT IN THE SAME COMMIT. An uncommitted
  generator is how fig4 ended up with two different captions and no way to tell
  which one shipped.

CAPTION TEXT IS NOT COVERED BY scripts/check_docs.py. The checker walks .md
files; a wrong number or a stale claim baked into a PNG is invisible to it and
always will be. Figure captions are checked by READING THE FIGURE. That is how
the "five wet-point definitions" error in fig4's footnote was found (it is two;
see below), and it is why every figure's numbers must come from its script
rather than from a person retyping them.

SPREAD-SKILL RE-MEASURED 2026-08-27 — THIS IS THE DECK NUMBER.
Sample: 12 init dates, ALL FOUR SEASONS, 3 years (2012/2015/2018), 11 members,
daily precip, truth = IMD gauge-gridded rainfall, LAND ONLY, wet points only
(>0.1 mm). 77,425 wet points. Produced by:
  python src/03_spread_skill.py --truth imd --seasons JJAS,DJF,MAM,ON \
      --years 2012,2015,2018 --dates-per-season 1 \
      --out data/spread_skill_4season.parquet
  python src/04_conditional.py --sample data/spread_skill_4season.parquet \
      --bootstrap 2000

  POOLED r                = +0.663   <- STILL NOT THE BASELINE. DO NOT QUOTE.
  WEIGHTED CONDITIONAL r  = +0.041   <- the honest baseline
  95% CI (cluster bootstrap, 12 dates, 2000 reps) = +0.016 to +0.065
  per season: DJF -0.015 | MAM +0.041 | ON +0.062 | JJAS +0.069

+0.041 IS FRAGILE — DO NOT QUOTE IT ALONE. CHECKED 2026-08-27.
The headline rests almost entirely on ONE decile. Bin 0 (the driest) has
r = -0.474 and drags the weighted mean down by 0.058 on its own:
    OR filter, all bins (the headline)      +0.041
    OR filter, drop the driest decile       +0.093
    both forecast AND truth > 0.5 mm        +0.095
    both forecast AND truth > 1.0 mm        +0.089
    both forecast AND truth > 2.0 mm        +0.084
CAUSE: the wet filter is an OR — keep a point if EITHER side is wet. In the
driest bin the median TRUTH is 0.00 mm and 38.6% of points got in only
because it rained while the ensemble said nothing. Those are confidently-dry
busts: narrow spread, huge error, hence a strong negative correlation.
CONSEQUENCE: a reviewer who asks "what if both sides must be wet?" gets
+0.095, more than double the headline. Quoting +0.041 alone looks like
cherry-picking once that is found.
WHAT TO QUOTE INSTEAD — the variance framing, which is robust to the filter:
    pooled explains 43.9% of the variance in log error
    conditional explains 0.17% to 0.90%, depending on the wet filter
  i.e. UNDER 1% HOWEVER YOU SLICE IT. That claim survives the question.
The confidently-dry failure mode is a SEPARATE and better finding: when the
ensemble is confidently dry and it rains, spread is actively MISLEADING, not
merely uninformative. That is operationally usable — report it as its own
result, not buried inside the headline.
src/04_conditional.py now prints this panel on every run.

VERDICT: the pitch stands as written. Conditional r is far below the ~0.15
level that would have forced a rewording, and the WHOLE interval sits below
+0.07. The pooled -> conditional collapse (+0.663 -> +0.041) is larger than
in the provisional measurement, so the structural finding got stronger.

DO NOT OVERCLAIM THE SEASONAL RESULT. Every season is near zero and DJF is
indistinguishable from zero. The honest reading is "spread carries almost no
within-regime information in ANY season", which is a cleaner and more
defensible claim than "it works in some regimes and not others". Do not build
a regime slide on a 0.08 spread of near-zero numbers.

THE MOVE FROM +0.076 TO +0.041 IS CONFOUNDED — SAY SO IF ASKED. It changed on
two axes at once: seasons/years AND truth source/domain (ERA5 with ocean ->
IMD land-only). It cannot be attributed to seasonality. The controlled
comparison is implemented but NOT RUN: 03 --truth era5 --restrict-to-imd-land
holds the domain fixed. The conclusion does not depend on it — both numbers
are low — so this is a completeness item, not a blocker.

DATE SELECTION MATTERS AND IS EASY TO GET WRONG. pick_inits() takes the CENTRE
of each (year, season) block, not the first date in it. Taking the first would
have sampled 6 June for JJAS in all three years — monsoon ONSET, wearing a
JJAS label — and repeated that identical bias in every year.

--- superseded, kept for provenance ---
SPREAD-SKILL MEASURED 2026-08-25 (PROVISIONAL, SUPERSEDED BY THE ABOVE).
Sample: 3 Wednesdays, JJAS 2015, 11 members, daily precip, truth = ERA5
LSP+CP, wet points only (>0.1 mm). 136,513 points.
  corr(log spread, log |ens_mean - truth|) POOLED = +0.588
  (flat across leads: Day 1 +0.533 ... Day 10 +0.617)
That looks like a strong baseline. IT IS MOSTLY AN ARTIFACT.
Conditioning on precipitation magnitude (deciles of ensemble mean) collapses
it to +0.076 weighted:
  decile 0 (0.09 mm) -0.153 | decile 5 (4.9 mm) +0.053 | decile 9 (31 mm) +0.260
So nearly all of the 0.588 is the wet/dry spatial gradient — wet places have
big spread AND big error, dry places have small of both. Within a comparable
rain regime, spread carries almost no information about error.

CONSEQUENCES, ALL OF THEM IMPORTANT:
1. Do NOT quote 0.588 as "the spread-skill correlation". It is not comparable
   to the published 0.3-0.6 figures, which are not pooled across space this
   way. Quoting it would overstate the baseline we claim to beat.
2. Our headroom is LARGER than the simulation assumed, not smaller. Raw
   spread is a weak discriminator once magnitude is controlled.
3. THE TRAP: our model gets precip_mean as a feature, so it also earns credit
   from the same wet/dry gradient. Comparing model-vs-raw-spread on pooled
   data flatters BOTH. The fair baseline is spread conditioned on magnitude
   (or stratified evaluation within magnitude bins). Build it that way or a
   meteorologist judge will take the result apart.
4. Caveats on this measurement: only 3 dates, one season, one year, and ERA5
   truth is reanalysis whose model physics partly overlaps GEFS. RESOLVED
   2026-08-27 by the four-season IMD re-measurement at the top of this
   section, which supersedes these numbers as the deck figure.
5. REPRODUCIBILITY: 03_spread_skill.py reports the POOLED number ONLY. The
   conditional number is produced by src/04_conditional.py, which also
   reports a CLUSTER-BOOTSTRAP confidence interval over init dates (the
   independent unit is the forecast date, not the gridpoint — a row-level
   bootstrap would report a falsely tight interval). Never quote a
   conditional number that did not come out of 04.

MODEL PLAN:
1. Label: bust = |forecast - ERA5 truth| > 95th percentile, computed PER region
   and PER lead time (a Day 10 error is not comparable to a Day 1 error).
2. Baseline: rank by ensemble spread alone. Record ROC-AUC + PR-AUC.
3. Model: HistGradientBoostingClassifier first. ConvLSTM only if time remains.
4. Calibration matters — deliverable is a confidence indicator, so probabilities
   must be calibrated. Reliability diagram + Brier decomposition.
5. SHAP explanations (the PS explicitly requires explainable output).

HONESTY RULES:
- Split train/test BY TIME, never randomly. Weather is autocorrelated and a
  random split inflates every metric.
- Never report plain accuracy — base rate is ~5%, accuracy is meaningless.
- PR-AUC will look low in absolute terms (~0.2-0.3). Report it anyway.
- If we cannot beat ensemble spread, SAY SO. An honest negative result scores
  better with meteorologist judges than an inflated claim.
- Never write a fallback that silently generates synthetic data. If the real
  data path breaks, I need to know.
