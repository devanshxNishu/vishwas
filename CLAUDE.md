# VISHWAS — Forecast Confidence Intelligence
### Team Hellfire Labs · SIH26079 · Smart India Hackathon 2026
विश्वास, "confidence" — knowing when not to trust the forecast.

================================================================================
HANDOVER — READ THIS FIRST. Written 2026-09-09, at the end of development.
Development is PAUSED here. This block assumes you know nothing about the
project and have no access to the conversation that built it.
================================================================================

WHAT VISHWAS IS
We are not building a weather forecast. We built a model that predicts WHEN the
operational medium-range forecast will be badly wrong — a "forecast bust" — and
publishes that as a confidence map over India for lead days 1 to 10. The point
of comparison is what forecasters do today: judge confidence by eyeballing
ensemble spread, a method we measured against India's own rain gauges and found
explains under 1% of forecast error once you control for how much it rained.

WHAT IS DONE AND SHIPPABLE
  RESULT      Stratified ROC-AUC 0.728 for the model against 0.565 for ensemble
              spread, margin +0.13 to +0.16, whole confidence interval above
              zero. Trained on 2018, tested on all 52 Wednesdays of 2019, IMD
              gauge truth, 651,040 test rows over 1,252 gauge-observed
              gridpoints. A five-year retest (train 2015-17) changed nothing
              measurable, which retired "one training year is thin".
  DECK        deck/VISHWAS_SIH.{pptx,pdf}, 6 slides. RELEASED — do not rebuild
              it casually. deck/archive/ holds v1.
  SITE        site/index.html — the landing page and the case.
  DASHBOARD   site/dashboard/index.html, live at vishwas-five.vercel.app/dashboard/.
              Deploys from a push to main (Vercel, git-connected). Edit BOTH
              site/source/vishwas-dashboard.dc.html AND site/dashboard/index.html
              or the next rebuild from source silently reverts you.
  API         api/main.py, reads site/dashboard-data.json. It never recomputes
              a verdict; it serves the stored one.
  OPERATIONAL src/20_operational.py scores one live GEFS cycle end to end in
              about 100 seconds and 210 MB. Five guards are constants, not
              comments. `--from-parquet` rebuilds the export from a stored cycle
              with no network at all — use that for any export change.
  REPRODUCE   Every figure has a committed generator; every published number
              has a script. models/ is gitignored, so a fresh clone must refit
              via src/07_model.py before 09/10 will run.

WHAT IS OPEN — each with enough context to act without asking anyone
  1. WHERE THE DAILY RUN LIVES. 20_operational.py is a one-shot command, NOT a
     scheduler, deliberately. Nothing has been decided about hosting it, and no
     cron, launchd job or GitHub Action exists anywhere in this repo. A daily
     00Z run costs ~210 MB and ~100 s. Use the 00Z cycle only: the reforecast
     is all 00Z, and a 06Z cycle shifts every one of the 23 features against
     the climatology (measured, not assumed).
  2. THE HULL FLAG ON ALERTS OUTSIDE THE GAUGE GRID. Every exported cell now
     carries `hull`, set when its squared Mahalanobis distance exceeds the
     training 99th percentile. On the shipped grid, 7.21% of alerts outside the
     gauge domain are outside the hull, against 1.64% inside it. The flag is
     computed and published; NOTHING IN THE INTERFACE READS IT YET. Deciding
     how the dashboard should show "unusual" — distinct from the existing
     "unverifiable" marker — is open design work.
  3. THE KHARGONE REGION LABEL. 21.5N 75.5E is Khargone, MADHYA PRADESH, and
     the dashboard labels it "Interior Maharashtra". The obvious fix — shrink
     the Interior Maharashtra box — does not work: region() breaks ties between
     overlapping boxes on distance to BOX CENTRE, so shrinking a box moves its
     centre and steals points far from the edge you moved. Narrowing maxLat to
     21.2 fixes 5 Madhya Pradesh cells and breaks Hyderabad and Kalaburagi,
     both of which surface on the panel. A containment-depth tie-break was
     tried and is worse (168 cells move, Hyderabad still breaks). This needs a
     tie-break that does not depend on box centres. Do not retry either of the
     two approaches already measured.
  4. THE TEAM ID. Still not pasted. The date named in the CHECKER STATE block
     below has passed; if the ID has been issued, do all four of its steps in
     ONE commit. check_docs.py fires 7 hits on this and exits 1 BY DESIGN until
     then.

THE STANDING RULES. Non-negotiable, and each exists because of a specific way
this project could be taken apart by a judge. scripts/check_docs.py enforces
them on Markdown; it cannot see inside a PNG or a .pptx, so figures and slides
are checked by reading them.
  • NEVER QUOTE THE POOLED PAIR (0.909 model / 0.885 spread). Pooled scoring
    lets ensemble spread track rainfall AMOUNT and scores it 0.885 for free.
    Removing that collapses it to 0.565. Quoting the pooled pair as performance
    would commit, in our own work, the exact error this project accuses the
    incumbent of. It survives in this file and the audit trail only, as the
    thing being ruled against.
  • NEVER SET 0.755 BESIDE 0.728. Different test set, different labels, and
    seven qcut bins instead of eight. It is a scope conflation, not a gain.
  • NEVER QUOTE A MARGIN RANGE CONTAINING +0.035. It comes from a "forecast AND
    truth > X mm" filter that conditions on the OUTCOME and deletes both
    classes of extreme bust. The honest range is +0.13 to +0.16.
  • NEVER REPORT PLAIN ACCURACY. The base rate is about 6%; accuracy is
    meaningless here and reads as either naive or evasive.
  • NEVER RECOMPUTE THE THRESHOLD. confidence.THRESHOLD is pinned in full
    double precision and is NOT re-derived at import. A different test set has
    a different 90th percentile, and adopting one means republishing every
    downstream count deliberately and all at once. Consumers read the STORED
    verdict; they never re-derive a class from a displayed probability.
  • FIX THE PROSE, NEVER THE DATA. If a script contradicts a value in a
    document, the document is wrong until proven otherwise — and if the script
    is genuinely wrong, that is a real finding to report, not a documentation
    bug to paper over. Never edit a log to agree with a document; a log edited
    to match is worthless as an audit trail.
  • NEVER MIX TRUTH SOURCES IN ONE COMPARISON, and never let a feature come
    from ERA5 or IMD. Those are truth; a predictor drawn from them is leakage.

HOW TO CHECK THE WHOLE THING IS STILL COHERENT
    python scripts/check_docs.py
  EXPECT EXIT 1, with exactly this shape: "7 finding(s) in 3 file(s); 36 noted
  in 9 exempt file(s); 0 site assertion(s) failed", all seven being the Team ID
  guard. ANY OTHER FINDING, or a non-zero site assertion count, is a real
  regression. A green run before the Team ID is pasted means someone deleted
  the guard — that is the failure, not the fix.

================================================================================

CHECKER STATE, until team selection on 3 Sep 2026.
scripts/check_docs.py exits 1 by design. The Team ID guard fires on 7 hits
across 3 files because the ID is issued only after selection at the internal
hackathon. This is the rule working. DO NOT delete it, and do not "fix" the
placeholders by inventing an ID.

AFTER SELECTION, in ONE commit — these four changes only make sense
together, and split apart there is a window where this file and the
checker disagree:
  1. Paste the real Team ID into the deck, slide 1.
  2. ADD a Team ID line to the site footer. It does not exist yet — this
     is a new element, not a blank to fill. The site guard catches a blank
     field, not a missing one, so nothing will remind you.
  3. Flip the site assertion from "not blank" to "present", so from then
     on absence is a failure.
  4. Delete this block. The guard's meaning inverts here: a hit stops
     being expected and becomes a real finding.

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

S3 THROUGHPUT — THE CONNECTION POOL, NOT THE LINK. MEASURED 2026-09-06 (P34).
One init date is ~1,210 byte-range GETs, and botocore pools only 10 connections
by default. That pool, not bandwidth, is what limits the fetch. Proof it was
not the link: with the fetch running alone the whole interface carried
0.91 MB/s; adding a second downloader took the interface to 2.49 MB/s.
    default pool (10)          0.9 - 4.4 MB/s     478 s per date
    max_pool_connections=128   6.1 - 6.4 MB/s      74 s per date
Benchmarked on four UNFETCHED dates, 200 messages each, alternating settings so
a recovering network could not flatter the later run. Raising it further did not
help: batch_size 256 with a 256 pool measured SLOWER than the default batch size
at pool 128. connect() in 01_fetch.py now sets POOL_CONNECTIONS = 128.
THIS IS A TRANSPORT SETTING ONLY — the same byte ranges are requested, the same
GRIB messages come back, and every blob still gets its GRIB/7777 envelope check
in fetch(). It is a ~6x speedup on every future fetch. DO NOT let it be
rediscovered, and do not read a slow first date as "the network is bad" without
checking the pool first.

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

"NEITHER OVERLAPS NOR IS COMPARABLE" — HALF WRONG, CORRECTED 2026-09-07 (P37).
Established by LISTING the bucket, not by reasoning about retention:
  IT DOES OVERLAP IN DATE. noaa-gefs-pds holds an UNBROKEN daily series from
  gefs.20170101 to the present — 3,537 entries for a 3,537-day span, zero
  missing. gefs.20190731/00/ still exists, and that is both a published
  52-date test-set member and the demo date. There is no retention window.
  IT IS STILL NOT COMPARABLE, but for reasons this file did not name:
    - RESOLUTION. The 2019 operational families are pgrb2a/pgrb2b at 1.0 deg
      (181 x 360). The analysis grid is 0.5 deg, so HALF our latitudes and
      half our longitudes DO NOT EXIST in the 2019 operational files.
      colocation would become interpolation, which to_india_grid() forbids.
    - MODEL VERSION. GEFSv12 became operational 2020-09-23, after the
      reforecast ends. Every overlapping date is GEFS v11 output; the
      reforecast is GEFSv12. Different model, not just a different sample.
    - Member count differs too (21 in 2019, 31 now, 11 in training), but it
      is the least of the three and the only one we can correct for.
  CONSEQUENCE: a "same date, both archives" controlled comparison is NOT
  available, and the four confounds — model version, resolution, gradient
  length scale, member count — would exceed the signal. Do not build one and
  do not report one.
  THE LIVE PATH IS A BETTER MATCH THAN THE HISTORICAL OVERLAP, which is
  counter-intuitive and worth holding onto: today's cycle is GEFSv12 at
  0.5 deg from pgrb2ap5 — the same model family and the exact grid the model
  was trained on.
OPERATIONAL VIABILITY — PROBED 2026-09-07 (P37), PS-fidelity item 4 CLOSED as
a question, OPEN as an engineering decision. THE PUBLISHED MODEL CAN SCORE A
LIVE CYCLE. Ran end to end on gefs.20260907/00Z, src/20_oper_probe.py,
logs/p37_oper.log.
  FIELD PROVENANCE, from a real .idx and not from documentation:
    pgrb2ap5   HGT/UGRD/VGRD 500 mb, UGRD/VGRD 850 mb, PWAT, APCP  (7 of 8)
    pgrb2bp5   CAPE:surface                                        (1 of 8)
  CAPE IS THE TRAP. pgrb2ap5 carries CAPE:180-0 mb above ground — mixed-layer
  CAPE, a DIFFERENT QUANTITY from the reforecast's cape_sfc, which its own
  .idx confirms is CAPE:surface. Matching on "CAPE" would silently feed the
  model a different variable. Surface CAPE is in the b family.
  APCP SUMMATION REPRODUCES A DAILY TOTAL. Operational buckets are disjoint
  and tiling — f102 is 96-102, f108 102-108, f114 108-114, f120 114-120 — so
  four are SUMMED per day, exactly as daily_precip() already does. Never
  differenced.
  MEMBERS SUBSAMPLED 31 -> 11 (gec00 + gep01..gep10) to match training. A
  31-member spread is SHARPER than anything in training, so using all of them
  would shift the model's most important feature family. "More is better" is
  the wrong instinct here; see the 5 -> 11 sensitivity below.
  THE STORED CLIMATOLOGY APPLIES UNCHANGED. Keyed on season, not date, so
  every one of 50,410 live rows matched a group in data/climatology.parquet.
  It is LOADED, never refitted — refitting on operational data is the leak
  finalize() was rewritten to prevent.
  THE MATCH COUNT NAMES THE EXACT SHAPE OF THE DOMAIN GAP. 201,640 groups is
  5,041 x 10 x 4 — every gridpoint in the full 71 x 71 India box, every lead
  day, every season. FEATURES AND CLIMATOLOGY COVER THE WHOLE DOMAIN. It is
  only LABELS and BUST THRESHOLDS that stop at 1,252 gridpoints, because those
  need IMD gauge truth and the IMD land/no-gauge mask is what cuts 5,041 down
  to 24.8%. A live cycle therefore produces a confidence value at all 50,410
  (gridpoint, lead day) cells — the 1,252 figure is a limit on what can be
  SCORED, never on what can be PREDICTED. Do not quote 1,252 as the size of
  the operational product.
  USE THE 00Z CYCLE. The reforecast is all 00Z inits, so a 06Z cycle is a
  quiet mismatch: over India the diurnal cycle makes a 06Z-06Z daily
  accumulation a different quantity from 00Z-00Z. Measured, not assumed — the
  same probe on 06Z put 2.63% of gh500_mean outside the training range, and
  on 00Z that falls to 0.01%.
  COST FOR ONE CYCLE: 1,210 messages, 207.6 MB, 89.5 s wall clock (plan 14.3,
  transfer 73.0, features+score 2.2). A daily job is trivially affordable.
  DISTRIBUTIONS: on 00Z no feature puts more than 1% of live values outside
  the training range. The model is interpolating, not guessing.
  DEPLOY THE CALIBRATED SCORE FOR DISPLAY, BUT BAND ON THE RAW ONE.
  MEASURED 2026-09-07, src/21_oper_calibrate.py, logs/p37_calibrate.log.
  The live tail reproduces the known saturation: p >= 0.9 on 7 of 50,410 cells
  (0.014%), against 72 of 651,040 (0.011%) on the test set, and the live raw
  maximum is 0.9999997898 — which DISPLAYS AS 1.0000. An operational product
  must never show a bust probability of exactly 1 days before anything can be
  observed. The isotonic map fixes the display: it sends that value, and 1.0
  itself, to 0.752381, its hard cap, and NO live cell calibrates above 0.9.
  BUT IT DOES NOT PRESERVE THE OPERATING POINT, AND THIS WAS CHECKED RATHER
  THAN ASSUMED. "Isotonic is monotone so the ranking is safe" is the trap:
  monotone NON-DECREASING allows flat runs, and one of them straddles the
  threshold. Isotonic maps the whole raw interval [0.147189, 0.176311] onto
  the single value 0.126283, and THRESHOLD = 0.15347 sits inside it. 995 live
  cells land on that run; 240 of them are below the raw threshold and a
  >= test on calibrated scores cannot tell them apart from the cells above it.
      flagged, raw scale     5,512  (10.93%)
      flagged, calibrated    5,752  (11.41%)   +240 gained, 0 lost
  SO THE BANDING DECISION STAYS ON THE RAW SCORE. This is exactly the doctrine
  src/confidence.py already states one level down — publish the number, store
  the verdict, and never let a consumer re-derive a class from a lossy
  representation. The calibrated probability is another such representation.
  Adopting it as the banding input would republish every count deliberately;
  it must not happen as a side effect of improving the display.
  NO TRUTH, SO NO ACCURACY. IMD gauge rainfall lags far beyond this horizon.
  A live run yields a confidence FIELD and nothing that can be scored.
  10.93% of cells crossed the FIXED threshold p >= 0.153 on 7 Sep 2026. The
  threshold is NOT recomputed per cycle; the crossed fraction is the signal.
  THE LEAD-DAY PROFILE RISES THROUGH DAY 9 AND EASES AT DAY 10. Write it that
  way; NEVER call it monotonic. High risk by lead day, 00Z 7 Sep 2026:
      D1 3.59  D2 5.08  D3 7.78  D4 10.24  D5 10.65
      D6 10.75  D7 13.15  D8 15.69  D9 17.50  D10 14.92
  Mean p turns TWICE, not once: it dips at 5 -> 6 (0.0725 -> 0.0716) before
  climbing to its Day 9 peak of 0.1041 and falling back to 0.0979 at Day 10.
  One cycle is one weather situation, so do not build a lead-time story on
  this shape — but do not smooth it into "increases with lead time" either.

OPERATIONAL RUNNER AND ITS TWO MEASUREMENTS — 2026-09-08 (P39).
src/20_operational.py scores one live cycle in one command. NOT a scheduler:
where it runs is the next decision. Five guards are CONSTANTS, not comments —
00Z only, surface CAPE from pgrb2bp5 by exact level match, 11 members, the
fixed raw threshold, EXPECTED_MESSAGES + GRIB/7777 before transfer.
Verified on gefs.20260908/00Z: 211.6 MB, 104 s, all five guards fired.

THE DOMAIN SPLIT — MEASURED, src/22_domain_check.py, logs/p39_domain.log.
The model learned ONLY at the 1,252 gauge points; features and climatology
cover all 5,041. Splitting the live grid and re-running the out-of-range check
on each subset SEPARATELY (P37's number pooled them, so 75% of the domain was
averaged against the 25% carrying the training footprint):
    worst feature, gauged 1,252     0.008%
    worst feature, ungauged 3,789   0.158%   (precip_anomaly)
    features over 1% on the ungauged subset: NONE
So the ungauged points are NOT out of distribution, and the decision is SCORE
ALL 5,041 BUT MARK THE 3,789 as a distinct state, excluded from every headline
count. They are never merged into one population; slide 4 promises the gauge
domain is stated and an unmarked full-grid count breaks that promise.
  IN-RANGE IS NOT VERIFIED, and this is the sentence to keep. The check says
  live features sit inside the training hull. It says NOTHING about accuracy
  there, because no gauge means no label ever existed, so nothing at those
  points has been or can be scored.
  THE MARKING EARNED ITSELF IMMEDIATELY. On 20260908 the ungauged domain
  flagged high risk 13.16% against 7.78% on the verified grid — 1.69x. The
  pooled figure, 11.82%, is dominated by the three quarters of the domain that
  can never be checked. QUOTE 7.78%. The full-grid number is reference only.

ISOTONIC QUANTISATION — WHY THE DISPLAY IS ROUNDED. src/21_oper_calibrate.py.
PAVA fits a step function, so the calibrated field is a small set of levels,
not a continuous probability:
    live cycle    110 distinct calibrated values from 42,891 distinct raw;
                  largest block 7.22% of the grid; ten largest cover 50.50%;
                  97.80% of cells sit in blocks of 100+
    2019 test     445 distinct from 456,678 raw; largest block 10.90%;
                  ten largest cover 53.98%
DECISION: DISPLAY THE CALIBRATED PROBABILITY ROUNDED TO 1 PERCENTAGE POINT
(DISPLAY_STEP = 0.01), which is option (b) but at 1% and NOT the 5% first
suggested — 5% is too coarse where the mass is. 86.4% of the live grid sits
below p = 0.10 and the median cell is 0.0339, so a 5% grid would round the
median to 0.05, a ~47% relative shift, while wasting resolution over 0.3-0.75
where almost nothing lands. Measured distortion: 5% max shift 0.0248, 1% max
shift 0.0050 against blocks far wider than that.
  COARSER DISPLAY MEANS MORE CELLS SHARE A NUMBER, AND THAT IS ACCEPTED:
    raw at 4dp        22 cells (0.04%) share a printed number with a
                      different verdict
    calibrated full   2,017 (4.00%)
    calibrated at 1%  4,106 (8.15%)
  No display precision drives it to zero, which is exactly why THE VERDICT IS
  STORED AND BANDED ON THE RAW SCORE. A coarse number also discourages the
  false belief that two cells showing the same value can be ranked.
  THE CAP NEEDS WORDS, and they live in the export's meta block so no
  interface can omit them: "Risk is capped at 75%: that is the highest bust
  rate ever observed in held-out data, so the system does not display a
  confidence it has not earned."

REGION LABELS ON THE DASHBOARD — FIXED AND DEPLOYED 2026-09-09 (P40).
The "most error-prone areas" panel names places through region(lon, lat), a
table of approximate lat/lon rectangles. THE BOXES ARE FINE; THE COMPOUND NAMES
WERE NOT. Every wrong label was a compound asserting a SECOND, NARROWER place
the rectangle cannot guarantee, and every single-name label was correct:
    Gujarat–Saurashtra              -> Gujarat        (24.0N 73.0E)
    Konkan–Goa coast                -> Konkan coast   (20.0N 73.0E; Goa is 15.3N)
    Central India (MP–Chhattisgarh) -> Central India  (25.0N 76.5E is Baran, RAJASTHAN)
    West Rajasthan                  -> Rajasthan      (26.0N 74.0E sits ON IMD's
                                       own West/East Rajasthan subdivision line,
                                       so an IMD or NCMRWF judge checks it on sight)
Two off-screen compounds failed the same test and were renamed:
'Bengal–Odisha coast' is assigned inland to 84E, ~230 km from the sea, so it
became 'Bengal–Odisha'; 'Kerala–coastal Karnataka' reaches 77.5E at 12.5N,
interior Karnataka, so it became 'Kerala–Karnataka'. 'Telangana–Vidarbha' WAS
KEPT DELIBERATELY: it names two PEER regions the box genuinely spans, with no
narrower assertion, exactly as 'Bihar–Jharkhand' does. A peer compound is not
the defect; a NARROWING compound is. Do not "finish the job" by reducing it to
one state — that would label Vidarbha (Maharashtra) as Telangana, a fresh
state-level error.

THE TIE-BREAK IS THE TRAP, AND IT COST ONE OF THE TWO INSTRUCTED BOX EDITS.
region() picks, among all boxes CONTAINING the point, the one whose CENTRE is
nearest. So shrinking a box MOVES ITS CENTRE and can steal or surrender points
nowhere near the edge that moved. Measured over the 1,252 gauge cells:
    Bihar–Jharkhand latMin 21.5 -> 22.5   APPLIED. 7 cells fixed, 3 regressed.
        Fixes 21.5/22.0N x 83.0/83.5E (Raigarh/Jashpur, CHHATTISGARH — 22.0N
        83.5E was showing as rank 09 on the Day 5 view). Costs 22.5N
        85.5/86.0E (Singhbhum, JHARKHAND) and 26.5N 83.5E (Gorakhpur, UP).
    Interior Maharashtra maxLat 21.5 -> 21.2   NOT APPLIED, ON PURPOSE.
        It fixes 5 Madhya Pradesh cells but breaks 2 more elsewhere: the centre
        moves 18.75N -> 18.6N and steals 17.0N 78.0E (HYDERABAD, Telangana) and
        17.0N 76.5E (Kalaburagi, Karnataka) from their correct boxes. Both
        surface in the top-10 panel. Net 13 fixed / 5 broken, but it puts MORE
        wrong labels on the visible panel than were there before.
CONSEQUENCE: 21.5N 75.5E (Khargone/Barwani, MADHYA PRADESH) STILL READS
"Interior Maharashtra". IT IS A KNOWN SURVIVOR, not an oversight. Fixing it
needs a tie-break that does not depend on box centres — containment depth was
tried and is WORSE (168 cells move, and it does not fix Hyderabad either) — so
it is post-20-Sep work. DO NOT apply the 21.2 narrowing without re-measuring.

TWO FILES CARRY THE TABLE and a rebuild from source silently reverts a
one-file fix: site/source/vishwas-dashboard.dc.html (design-chat source) and
site/dashboard/index.html (built page). Both were edited, and the parsed tables
are asserted identical. Deployed and VERIFIED ON THE SERVED PAGE, not merely
committed: vishwas-five.vercel.app/dashboard/ returns 'Konkan coast',
'Rajasthan', 'Gujarat', 'Central India', 'Bengal–Odisha', 'Kerala–Karnataka'
and zero occurrences of Saurashtra, "Goa coast", Chhattisgarh, "West
Rajasthan", "coastal Karnataka". A COMMIT IS NOT A DEPLOY AND A DEPLOY IS NOT
A VERIFICATION. deck/VISHWAS_SIH.{pptx,pdf} was held on exactly this (slide 3
prints the dashboard URL) and was released unchanged once the page verified.

IS THE UNGAUGED FIELD A PREDICTION OR AN EXTRAPOLATION? — ANSWERED 2026-09-09
(P40). src/23_mahalanobis.py, logs/p40_mahalanobis.log, data/mahalanobis.csv.
P39's domain table is 23 SEPARATE ONE-DIMENSIONAL checks, so it cannot tell
"genuinely stormier terrain" from "joint feature combinations never seen". A
cell can sit inside every feature's own range and still occupy an empty corner
of 23-dimensional space. Squared Mahalanobis distance settles it, mean and
covariance fitted on THE 488,280 ROWS THE ESTIMATOR ACTUALLY SAW — split=="train"
MINUS the 13 interleaved validation dates, asserted against the bundle's
n_train_rows — not on the whole labelled table.
    group                        n        p50    p90     p99      max   >train p99
    training rows (reference)  488,280  17.76  39.86  100.72   4301.7     1.00%
    live, gauged                12,520  17.00  29.07   74.11    187.8     0.29%
    live, ungauged              37,890  21.85  52.27  120.43    853.9     1.66%
    live, ungauged AND flagged   4,986  44.73  93.26  219.03    853.9     8.82%
    live, gauged AND flagged       974  21.11  52.52  109.60    187.8     1.33%
VERDICT: STORY (a), METEOROLOGY. The ungauged field as a whole sits inside the
joint training distribution at 1.66% beyond the training 99th percentile
against the training rows' own 1.00%. 13.16% is not the model extrapolating
into a void, and the P39 decision stands: score all 5,041, mark the 3,789.
  THE QUALIFICATION IS THE FLAGGED SUBSET AND IT SHIPS WITH THE HEADLINE.
  8.82% of flagged UNGAUGED cells sit beyond the training p99, against 1.33%
  of flagged GAUGED cells — 6.6x — and their median D^2 of 44.73 is 2.5x the
  training median. The ALARMS raised outside the gauge grid are drawn
  disproportionately from the sparse edge of the training distribution even
  though the field as a whole is not. 91.2% of them are still inside the hull,
  so this QUALIFIES (a) rather than replacing it with (b). Never quote the
  1.66% without the 8.82%.
  THE REFERENCE IS THE EMPIRICAL TRAINING DISTRIBUTION, NOT A CHI-SQUARED
  TABLE. D^2 ~ chi2(23) needs multivariate normality and these features are
  nothing like it — precip_mean is zero-inflated, month is discrete and cyclic.
  A chi-squared cutoff would be a distributional assumption smuggled in as a
  threshold. Condition number 74.87 on the standardised (correlation) matrix
  against 2.714e+05 raw, so NO regularisation was needed or applied; the ridge
  trigger sits at 1e10 and is reported either way.
  IN-RANGE IS STILL NOT VERIFIED. This measures distance to the training
  distribution and nothing else. No gauge means no label ever existed, so a
  cell can sit at the centre of the training cloud and still be wrong.

SHAP IN THE OPERATIONAL EXPORT — ADDED 2026-09-09 (P40), an omission in P39.
Operational cells were [ix, iy, p_display, verdict, domain] with no SHAP, while
the archive carries the top three drivers — and that "WHY THIS GRIDPOINT" panel
is THE IMAGE ON SLIDE 3. As built, the live product could not answer the
question the deck shows it answering, and "Explainable output" is PS Expected
Outcome 4, named explicitly. src/20_operational.py now calls explain(), which
REUSES 15_dashboard_export.py's shap_for() and percentile_lookup() rather than
running a parallel implementation.
  THE SELECTION RULE IS COPIED, NOT INVENTED: every cell whose STORED VERDICT
  is not "reliable" gets drivers, which is the archive's rule exactly. On
  20260908 that is 8,044 of 34,220 display-grid cells (23.5%).
  THE ADDITIVITY ASSERTION CARRIES OVER and fired: max |sum(SHAP) + base - raw
  log-odds| = 3.58e-14, well inside the 1e-4 refusal.
  SHAP IS ON THE RAW LOG-ODDS, NEVER THE CALIBRATED DISPLAY VALUE. The
  calibrated number is a monotone relabelling; attributions do not survive it
  and would not sum to it.
  PERCENTILES RANK AGAINST THE 2019 TEST SET, the same reference the archive
  uses. Ranking a live value against the live cycle's own distribution would be
  refitting on operational data — the leak the stored climatology exists to
  prevent — and would make "94th percentile" mean two different things in two
  files one page reads.
  --from-parquet REBUILDS THE EXPORT FROM A STORED CYCLE WITH NO FETCH, so the
  JSON can be regenerated without 211 MB of S3 and without re-scoring anything.
  It re-asserts that stored verdicts reproduce from stored raw scores, and it
  does NOT claim the five transfer-time guards, which cannot apply to a rebuild.

ONE SCHEMA, DECLARED RATHER THAN INFERRED — 2026-09-09 (P40).
Position 5 means AN ARRAY OF SHAP TRIPLES in the archive file and AN INTEGER
DOMAIN FLAG in the operational one. Any renderer branching on cell.length > 4
reads a domain marker as an explanation. That is a latent bug in a product with
two data files and one page.
  THE FIX IS SELF-DESCRIPTION, NOT REGENERATION. Regenerating the archive would
  redeploy the dashboard mid-flight, which is what the region-label work exists
  to avoid. The operational export now declares
      meta.schema = {"version": "vishwas.oper.cells/1",
                     "fields": ["ix","iy","p_display","verdict","domain","drivers"],
                     "required": 5, "optional_tail": "drivers"}
  and check_declared_schema() in the SHARED writer refuses to emit any cell
  whose length is not in {required, len(fields)}. Verified by construction: a
  4-length cell exits non-zero and NO FILE IS WRITTEN.
  THE ARCHIVE FILE, site/dashboard-data.json, HAS NO meta.schema YET. It gains
  one THE NEXT TIME IT IS LEGITIMATELY REGENERATED — not before, and not as a
  side effect of anything else. Until then the writer prints "meta.schema
  ABSENT" on every write of it, and NO RENDERER MAY INFER LAYOUT FROM ARRAY
  LENGTH. Bump the version string whenever the field list or required count
  changes.

THE CAP SENTENCE, TIGHTENED 2026-09-09. It read "the highest bust rate ever
observed in held-out data", which invites a judge to ask whether nothing
anywhere busted more often. It is the top isotonic block's rate on the
validation slice, so it is the highest rate for any COMPARABLE GROUP. It now
reads: "Risk is capped at 75%: that is the highest rate observed for any
comparable group of forecasts in held-out data, so the system does not display
a confidence it has not earned." Lives in CAP_SENTENCE and reaches every
interface through the export's meta block.

THE TWO GRIDS, RECONCILED 2026-09-09 (P41). src/24_grid_reconcile.py,
logs/p41_grid.log, data/grid_reconcile.csv. THREE NUMBERS, THREE DIFFERENT
THINGS, and this file previously used 5,041 for two of them:
  5,041 = THE ANALYSIS BOX. 5.0-40.0N, 65.0-100.0E at 0.5 deg, 71 x 71. EVERY
          point in the box, LAND AND OCEAN ALIKE. It is what features and
          climatology cover. IT IS NOT "land gridpoints" — anywhere this file
          or any document says that, it is wrong.
  3,422 = THE SHIPPED GRID. 8.5-37.0N, 68.0-97.0E, nx 59 x ny 58. The crop the
          map actually draws. 1,619 analysis points (32%) fall outside it.
  1,252 = THE GAUGE POINTS. The subset of the analysis box carrying an IMD
          gauge, so the only domain any label or accuracy has ever existed on.
          24.8% of 5,041.
THE CHECK THAT MATTERED: ALL 1,252 GAUGE POINTS SURVIVE THE CROP. Zero fall
outside the shipped grid. Had any been lost, the product could not display part
of the only domain it can be scored on, which would have been a far larger
finding than a mismatched percentage.
CONSEQUENCE — ONE FIGURE HOLDS AND ONE MOVES:
    grid                       domain                  points     high risk
    ANALYSIS BOX (5,041)       verified (gauge)         1,252        7.78%
    ANALYSIS BOX (5,041)       unverified                3,789       13.16%
    ANALYSIS BOX (5,041)       pooled, reference only    5,041       11.82%
    SHIPPED GRID (3,422)       verified (gauge)          1,252        7.78%
    SHIPPED GRID (3,422)       unverified                2,170       14.06%
    SHIPPED GRID (3,422)       pooled, reference only    3,422       11.77%
  THE VERIFIED FIGURE IS 7.78% ON BOTH GRIDS and is unaffected, because every
  gauge point survives the crop. Keep quoting it, and name the domain.
  THE UNVERIFIED FIGURE IS 13.16% ON THE ANALYSIS BOX AND 14.06% ON THE SHIPPED
  GRID. P39 and P40 quoted 13.16%, which describes 3,789 points of which 1,619
  are never drawn. WHEN THE CLAIM IS ABOUT THE PRODUCT, QUOTE 14.06% AND SAY
  "shipped grid"; the 13.16% is correct only as a statement about the analysis
  box. Neither pooled figure is ever a headline.

MAHALANOBIS WITHOUT THE INDEX FEATURES — OBJECTION CLOSED 2026-09-09 (P41).
src/23_mahalanobis.py --drop-index, logs/p41_mahalanobis_noindex.log.
THE OBJECTION: on one live cycle `month` is CONSTANT at 9 while training spans
1-12, so every live cell carries the same month-driven contribution to D^2.
That cancels in any contrast INTERNAL to the cycle — flagged ungauged 8.82% vs
flagged gauged 1.33% is untouched by it — but it does NOT cancel against the
training reference, which is what "1.66% vs 1.00%, so it is in-distribution"
rests on. Re-run over 21 features, dropping `month` and `lead_day`, the two
inputs that are indices rather than meteorology:
    fraction beyond the training 99th pct     23 features    21 features
      training rows (by construction)             1.00%          1.00%
      live, gauged                                0.29%          0.33%
      live, ungauged                              1.66%          1.77%
      live, ungauged AND flagged                  8.82%          9.13%
      live, gauged AND flagged                    1.33%          1.64%
THE CONCLUSION HOLDS AND THE OBJECTION IS CLOSED PERMANENTLY. Every figure
moves by around a tenth of a percentage point and none changes sign or story.
Story (a), meteorology, stands: the ungauged field sits inside the joint
training distribution at 1.77% against the training rows' own 1.00%. The
qualification stands too: flagged ungauged cells are 5.6x the flagged gauged
rate (was 6.6x), so the alarms outside the gauge grid still come
disproportionately from the sparse edge. DO NOT RE-OPEN THIS. The month
constant was not doing the work, and it has been measured both ways.

THE HULL FLAG — IN THE EXPORT 2026-09-09 (P41). Every operational cell now
carries `hull`, set when its squared Mahalanobis distance exceeds the TRAINING
99th percentile (96.57 over the 21 meteorological features).
  DOMAIN AND HULL ARE INDEPENDENT AND ANSWER DIFFERENT QUESTIONS, which is the
  whole reason the flag earns its place:
      domain = 0  UNVERIFIABLE. No IMD gauge ever existed there, so nothing at
                  that point has been or can be scored. A property of the MAP.
      hull   = 1  UNUSUAL. This cell sits far from anything the model learned.
                  A property of the WEATHER, and IT FIRES INSIDE THE GAUGE GRID
                  TOO — which the domain marker alone can never say.
  Cross-tab on 20260908, shipped grid: 21,310 unverifiable-and-ordinary,
  390 unverifiable-and-unusual, 12,479 verified-and-ordinary, and 41
  VERIFIED-AND-UNUSUAL. That last cell is the one the domain marker misses.
  Of alerts: 7.21% outside the hull on the unverified domain against 1.64% on
  the verified one.
  THE INDEX FEATURES ARE DROPPED FOR THE FLAG, on purpose. The flag is a claim
  about METEOROLOGY, and `month` is constant across a cycle, so including it
  shifts the whole field against a fixed threshold while saying nothing about
  any individual cell. Both versions were measured and the verdict is the same,
  so this is the more defensible of two answers rather than a rescue.
  NOTHING IN THE INTERFACE READS `hull` YET. It is published and declared; how
  the dashboard should show "unusual" as distinct from "unverifiable" is open.

CELL SCHEMA NOW vishwas.oper.cells/2 — fields
["ix","iy","p_display","verdict","domain","hull","drivers"], required 6, so a
cell is 6 long or 7 with the SHAP tail. check_declared_schema() in the shared
writer refuses anything else and was re-verified against the new version: a
5-long cell, which was legal under /1, now exits non-zero and no file is
written. site/dashboard-data.json still has NO meta.schema and gains one only
when it is next legitimately regenerated; until then no renderer may infer
layout from array length. BUMP THE VERSION whenever the field list or the
required count changes.

ATTRIBUTION — CHECKED 2026-09-09 (P41), AND IT IS CORRECT.
P40 instructed the Interior Maharashtra narrowing (maxLat 21.5 -> 21.2) and it
was NOT applied. The P40 report attributed that to a decision by Devansh, and
that attribution is accurate: measurement showed the narrowing broke Hyderabad
and Kalaburagi, three options were put to him in session with the counts for
each, and he chose "renames + Bihar-Jharkhand only". An instruction was
overridden by the project owner, not dropped.
  RECORDED PRECISELY BECAUSE THE FAILURE MODE IT RESEMBLES IS REAL: declining
  an instruction and then attributing the decision to an authority that never
  gave it would be far worse than simply not doing the work, because it is
  invisible in a diff and destroys the audit trail. The distinguishing evidence
  is that the choice was made from measured options, and the option chosen was
  one the model recommended — so the decision was his, the recommendation was
  the model's, and both belong in the record.

MODEL METADATA — CORRECTED 2026-09-08. logs/p37_oper.log printed
    model : vishwas_model.joblib (23 features, trained ['2018-01-01', '2019-12-31'])
which reads as though the model saw its own test year. THE BUNDLE FIELD IS
HONEST — config["study_window"] is [date_min, date_max], the span of the
SOURCE TABLE handed to 07_model.load(), and it spans both years because the
table holds the training year and the held-out test year together. The word
"trained" was the probe's own label and was wrong. 20_oper_probe.py now prints
the span as "source table spans ... <- DATA span, not the training period",
alongside the fitted row count and the held-out test rows. No model, metric or
published number was affected; only the log line.

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
EITHER keep 850 hPa for every date (recommended — the parts are small; the
cost is transfer time, and skipping it destroys data already fetched) OR strip
the three columns from the existing parts first so the schema stays uniform.
NEVER mix.
  COST CORRECTED 2026-09-06 BY MEASUREMENT (P34). This note used to say the
  extension costs "~27.4 GB / ~1.7 h". IT IS 488 MB PER DATE, 74.2 GB for the
  152 new dates, 3.44 h. The 27.4 GB was the 850 hPa PORTION alone and was
  transcribed as though it were the total. The COST block above was right all
  along (~122 GB for ~261 dates); this note disagreed with it and this note was
  the wrong one. The extension ran and the schema held: 256 parts, one schema,
  850 hPa present throughout, zero nulls in all 27 columns of the finalized
  table. src/17_schema_guard.py is the check, and it exits non-zero on a
  mismatch rather than warning — run it before and after any fetch that adds
  dates.

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

THE CI IN ablations/a_full.log IS NOT THE PUBLISHED CI, AND BOTH ARE RIGHT —
CHECKED 2026-09-07. The log cited just above prints, at line 30:
    95% CI, cluster bootstrap over 52 forecast dates: +0.1026 to +0.1910
The canonical interval — here, in README.md, the deck, the site and
check_docs.py — is +0.1080 to +0.1926. ONLY THE INTERVAL DIFFERS. The margin
+0.1634 and every per-bin number in that log match the publication exactly.
CAUSE: ablations/run.sh line 11 passes --bootstrap 500, chosen so five variants
would finish; the headline run used 2000. Same seed 0, same data, same code.
cluster_bootstrap_margin() resamples forecast dates and reads the 2.5/97.5
percentiles off the draws, so THE POINT ESTIMATE IS DETERMINISTIC AND THE
INTERVAL IS NOT — 500 draws pin a tail percentile less tightly than 2000.
Reproduced from data/pred_a_full.parquet with the project's own code,
evaluation only: 500 -> +0.1026 to +0.1910, 2000 -> +0.1080 to +0.1926, both to
four decimals. That agreement also confirms the stored predictions are the ones
the log and the publication came from.
THE LOG IS CORRECT AS PRINTED. DO NOT EDIT A LOG TO AGREE WITH A DOCUMENT — a
log edited to match is worthless as an audit trail. Do not quote +0.1026 to
+0.1910 as the project's CI either; check_docs.py now forbids that pair in
Markdown, absolving ablations/README.md, which quotes it in order to explain it.
The full account, with the snippet, is in ablations/README.md.

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
  OPERATING POINT. The alert threshold is the global 90th percentile of
  predicted scores over the test set: 0.1534712256035554. It is fitted ONCE on
  the whole test set and applied unchanged — NOT re-fitted per date, which
  would manufacture a flattering picture. This is the value every published
  count was computed at: 547 flagged on 20190731 Day 5, being 395 hits and 152
  false alarms, with 59 misses; precision 0.72, recall 0.87 ON THIS DATE ONLY.
  Quote it in prose as "p >= 0.153". DO NOT use a shortened form as a constant
  anywhere — NEITHER 0.1535 NOR 0.153471. Both are display roundings. 0.1535
  rounds up past one cell scoring 0.1534840 and yields 546, which is where the
  546/547 discrepancy came from; 0.153471 truncates below one cell scoring
  0.15347109047316893 (20190731 Day 4) and flips it from uncertain to high
  risk. No published count depends on Day 4, so correcting it moved nothing.
  The constant lives in src/confidence.py, pinned in full double precision and
  NEVER recomputed at import: a different test set has a different 90th
  percentile, and adopting one means republishing every downstream count
  deliberately and all at once.
  THE MACHINE-READABLE FORM IS site/dashboard-data.json meta.threshold, and
  every cell there carries a stored VERDICT (0 reliable, 1 uncertain, 2 high
  risk) computed upstream at the exact threshold. Consumers read the verdict;
  they must never re-derive a class from the published four-decimal p, because
  scores either side of the threshold both display as 0.1535. api/main.py reads
  both from that file. Corrected P28, 5 Sep 2026 — no number changed meaning,
  547 was always 547.
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

================================================================================
THE FIVE-YEAR EXTENSION (P34) — COMPLETE 2026-09-06. Study window 2015-2019.
================================================================================

VERDICT: TRIPLING THE TRAINING DATA DID NOT MEASURABLY CHANGE THE RESULT.
The two runs score the SAME 52 test dates, so the pairing is used rather than
wasted on two overlapping intervals: resample the dates once per replicate and
recompute BOTH models on that same resample (src/19_paired_ab.py).
    margin (b)-(a)   -0.0118   95% CI -0.0509 to +0.0111   INCLUDES ZERO
    model  (b)-(a)   -0.0147   95% CI -0.0539 to +0.0069   INCLUDES ZERO
REPORT THIS AS UNCHANGED. Not as a decline, not as an improvement. The
published 0.728 / 0.565 / +0.13 to +0.16 stands for its stated scope. One year
of training was already enough, and that is now an EXPERIMENTAL RESULT rather
than an assumption — which strengthens the original rather than weakening it.

  (a) published   train 2018      test 2019      0.565 / 0.728   +0.1634
  (b) five-year   train 2015-17   test 2019      0.561 / 0.703   +0.1418
  (c) five-year   train 2015-17   test 2018+19   0.606 / 0.755   +0.1491
                                                 CI +0.1164 to +0.2029

(c) IS THE NEW RESULT AND THE ONLY NEW CLAIM: +0.149 across 104 forecast dates,
two monsoons, all four seasons in the test block (DJF 26, MAM 26, JJAS 34,
ON 18), entire interval above zero. This is what retires "one test year is
thin".

NEVER SET 0.755 BESIDE 0.728. Three INDEPENDENT reasons, each sufficient on its
own: a different test set, different labels, and qcut yielding SEVEN bins
instead of eight — pooling two years puts 522,549 of 1,302,080 rows (40%) into
the collapsed driest bin, so the n-weighted stratified average is averaging
over a different partition. A "0.728 -> 0.755 improvement" is a scope
conflation, not a gain, and scripts/check_docs.py now forbids that phrasing.

THE SPLIT HAS A CONFOUND, AND IT IS MEASURED. "Only the training data differs"
is not quite true: bust thresholds are the 95th percentile OF THE TRAINING
WINDOW, so retraining relabels the test set — 4,576 of 651,040 rows (0.70%),
bust rate 6.467% -> 6.035%. Ensemble spread's scores are BIT-IDENTICAL across
both runs, so it is a fixed ranker and its movement isolates the relabelling
with the ranker held still:
    baseline (b)-(a)   -0.0031   95% CI -0.0066 to -0.0001   excludes zero
That is roughly a fifth of the model's -0.015, so relabelling is real but does
not account for the move. THE CONFOUND IS INHERENT TO DOING IT HONESTLY: the
only way to remove it is one threshold fitted across all 260 dates, which is
precisely the leak 06_label.py exists to prevent.

ROBUSTNESS IMPROVED WHERE IT WAS WEAKEST. Dropping the driest bin NARROWED the
published margin to +0.132; in both new runs it WIDENS — +0.144 for (b),
+0.167 for (c). The new result does not lean on the bin where spread is
degenerate. (c) is ahead in all 7 bins (+0.109 to +0.193); (b) in all 8
(+0.099 to +0.159).

THE LEAD-DAY CLAIM, CORRECTED. DO NOT WRITE "the margin is as wide at Day 10 as
at Day 1". That rested on the 52-date curve. The 104-date curve shows a gentle
decline: +0.171 at Day 1 easing to +0.149 at Day 10. THE CLAIM THAT SURVIVES
BOTH is: positive at every lead day, with the whole confidence interval above
zero at all ten.

DATA. 256 usable dates (2015: 52, 2016: 48, 2017: 52, 2018: 52, 2019: 52),
12,904,960 feature rows, 3,205,120 labelled rows, 124.5 GB fetched in total.
Outputs carry a _5yr suffix so both studies coexist unambiguously:
data/{features,climatology,labelled,bust_thresholds,model_predictions,
comparison,lead_day_auc}_5yr.*, models/vishwas_model_5yr.joblib,
ablations/a_full_5yr.log, figures/fig10_lead_curve_5yr.png. Nothing behind the
published result was overwritten.

FOUR DATES THE ARCHIVE CANNOT SERVE — 20160224 (p08), 20160309 (p09),
20160615 (p06), 20160622 (p01). One member truncated in the *_abv700mb family
only; the 0.25 deg families are complete on all four. SKIPPED, NOT PATCHED:
dropping the short member gives those dates a 10-member ensemble, and this
project's own 5 -> 11 sensitivity shows ensemble size moves the spread baseline
by about +0.015 conditional — that inhomogeneity would sit INSIDE the incumbent
being measured. Recorded in data/raw/incomplete.jsonl and printed in the run
summary. DO NOT "fix" this by lowering EXPECTED_MEMBERS. 01_fetch.py now checks
message counts against EXPECTED_MESSAGES before transferring a byte, so an
unservable date is a logged skip rather than a crash three hours in.

PER-GRIDPOINT THRESHOLDS REMAIN OUT OF REACH. 0 of 12,520 (lat, lon, lead_day)
groups qualify; 100% region scope. The gate needs 160 training samples (8
exceedances at the 95th pct) and the training window has 152 — 156 Wednesdays
in 2015-2017 minus the 4 skipped. EIGHT SHORT. DO NOT lower --min-exceedances:
at 152 samples a 95th percentile rests on 7.6 observations, so one unlucky day
would set a gridpoint's threshold for the whole study. Getting there needs a
LONGER TRAINING WINDOW, roughly seven years, not a re-cut of these. Note this
also keeps (a) and (b) comparable, since the published run is region-scoped too.

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
fig9_reliability, fig10_lead_curve (P26, 5 Sep — ROC-AUC per lead day).
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
  fig9  src/10_calibration.py    fig10 src/16_lead_curve.py
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
