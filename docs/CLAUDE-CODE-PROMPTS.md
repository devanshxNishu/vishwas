# VISHWAS — Work Plan & Claude Code Prompts

**Written 26 Aug 2026.** Companion to `CLAUDE.md` (the project constitution) and
`data/VISHWAS-HANDOFF.md` (project state).

Each prompt below is self-contained — copy one into a fresh Claude Code session
on the Mac. Or point Claude Code at this file: *"Read
`docs/CLAUDE-CODE-PROMPTS.md` and do P1."*

---

## 0. The critical path — read before choosing what to work on

There are **two tracks and they are not the same track.** Conflating them is how
six days get spent on the wrong thing.

| Track | Deadline | Needs | Prompts |
|---|---|---|---|
| **DECK** | **31 Aug (5 days)** | one *defensible number* | **P1 → P3 → P4** |
| **MODEL** | after the deck | the full pipeline | P2 → P5 → P6 → P7 |

**The 850 hPa work (P2) and the bulk run (P6) are NOT on the deck critical
path.** They must happen before the *bulk* run, not before the *deck*. The deck
needs the four-season conditional number and nothing else from the pipeline.

So the order for this week is **P1, P3, P4 — then stop and write slides.**

### Why P1 unblocks the deck rather than delaying it

The four-season re-measure is ~40 minutes of compute *if the truth source is
IMD*. On ERA5 it is not 40 minutes. Each init date needs the ERA5 half-month
LSP+CP files spanning its 10 valid days — roughly 1–2 GB per date at ~4.5 MB/s.
Twelve dates across four seasons is **hours of transfer**, versus ~25 MB *per
year* for IMD.

The IMD switch is therefore not only the scientifically stronger choice
(gauge observation, not reanalysis; MoES's own product). **It is what makes the
re-measurement fit inside this week at all.**

### Division of labour

| Where | What | Why |
|---|---|---|
| **Claude Code (Mac)** | anything touching the network — S3, IMD, bulk runs | Only the Mac can reach `imdpune.gov.in` and `noaa-gefs-retrospective`. The Cowork VM and cloud container reach pypi and nothing else. |
| **Cowork session** | analysis on saved parquet, docs, code review, leakage audits | No network needed; already has the sample staged. |

---

## 1. Current status

| Item | State |
|---|---|
| `01_fetch.py` | Works. 500 hPa only. **No 850 hPa yet.** |
| `02_features.py` | Works, 1 date verified. **`finalize()` has a climatology leak — see P5.** |
| `03_spread_skill.py` | Works, **ERA5 truth**. Docstring still says IMD is impossible — stale, see P3. Sample it wrote has **no lat/lon**. |
| `04_conditional.py` | **New.** Reproduces pooled +0.588 → conditional +0.076 exactly, plus a cluster-bootstrap CI. |
| `CLAUDE.md` | **Updated 26 Aug** — truth source corrected, wind-shear decision recorded, leakage section added, 2000-2019 range fixed. |
| `requirements.txt` | **Fixed 26 Aug**: `imddaily` -> `imdlib`. |
| `imdlib` | **Pre-verified 26 Aug**: pure-Python wheel (`py3-none-any`), no GDAL, installs on 3.9. Colocation proven exact. |
| Data on disk | 1 features part (`20150107`), 1 manifest row, 1 spread-skill sample (3 dates, JJAS 2015). |
| Bulk run | **Not started.** Correct — do not start it before P2. |

**Verified this session:** `04_conditional.py` reproduces the handoff's numbers
exactly (pooled +0.588; deciles −0.153 / +0.053 / +0.260; weighted +0.076).
Cluster-bootstrap 95% CI over the 3 dates: **+0.056 to +0.107** — but that
interval is a *floor*, not the error bar. It resamples three consecutive
Wednesdays in June 2015, so it measures within-season sampling error and is
blind to exactly the season-to-season variation that could move the headline.

---

## P1 — Verify the IMD truth path (BLOCKING — do this first)

```
Read CLAUDE.md first, especially the TRUTH SOURCE section and the four
VERIFY-IMD conditions.

Goal: find out whether IMD historical gridded rainfall actually works. Do NOT
switch any existing script to it yet. This prompt is verification only.

Work in the project venv (.venv, Python 3.9.6).

1. ALREADY DONE — requirements.txt now lists `imdlib` instead of `imddaily`.
   PRE-VERIFIED 26 Aug from the published wheel: imdlib 0.1.21 ships as
   imdlib-0.1.21-py3-none-any.whl — a PURE-PYTHON wheel. No GDAL, no compiled
   extensions, Requires-Python >=3.0. Its only deps are matplotlib, numpy,
   pandas, six, python-dateutil, pytz, urllib3, scipy, xarray, requests — all
   pure Python and mostly already installed. It will install on the 3.9 venv.
   Just install it and confirm the import works. Do not re-litigate this.

2. Write a new file src/imd_truth.py — a small, readable, reusable loader.
   It must expose roughly:
       download_year(year, cache_dir) -> path to the .grd
       daily_rain(year, day) -> 2-D numpy array on OUR 0.5 deg analysis grid
   Use imdlib.get_data() (the HISTORICAL yearwise function), NOT
   get_real_data() (the rolling real-time archive, ~2022 onward, which does
   not overlap our reforecast).
   CONFIRMED at source level 26 Aug — these are genuinely two endpoints:
       get_data()      core.py -> https://imdpune.gov.in/cmpg/Griddata/rainfall.php
       get_real_data() real.py -> https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php
   Both are HTTP POST (requests.post), not GET. The handoff's correction is
   right: the earlier session tested only the real-time one.

3. Verify all four VERIFY-IMD conditions from CLAUDE.md and print the evidence:
   a. imdlib imports and get_data("rain", 2015, 2015) returns real data.
   b. Grid geometry matches what CLAUDE.md records: 0.25 deg, 135 lon x 129
      lat, first point 6.5N/66.5E, last 38.5N/100.0E, units mm.
   c. COLOCATION — PRE-VERIFIED 26 Aug. Assert it in code, then move on.
      Computed from imdlib's own grid definition (core.py: lat =
      linspace(6.5, 38.5, 129), lon = linspace(66.5, 100.0, 135), both
      exactly 0.25 deg) against our 0.5 deg analysis grid:
        - 65 of our 71 latitudes and 68 of our 71 longitudes fall inside the
          IMD domain, and EVERY ONE matches to exactly 0.0 float error.
          Colocation is exact. Sample, never interpolate.
        - Outside the IMD domain: lats 5.0, 5.5, 6.0, 39.0, 39.5, 40.0 and
          lons 65.0, 65.5, 66.0.
        - Domain shrinks 5041 -> 4420 gridpoints (12.3% lost) from the
          bounding box ALONE, before any land mask.
      Still assert the exact match in code so a future imdlib version cannot
      change the grid under us.
      WARNING: imdlib imports scipy.interpolate.griddata and exposes a
      remap() method. Do NOT let any code path silently interpolate.
   d. LAND MASK. IMD is gauge-based over land; ocean is undef (-999). Report
      the fraction of our India-box 0.5 gridpoints that carry real data, and
      produce a quick count of surviving points per lead-independent grid.
      Treat -999 as missing, never as zero rainfall.
      NOTE: imdlib masks -999 to NaN inside its xarray path (core.py does
      xr_da.where(xr_da.values != -999.)). If you read the raw .grd yourself
      instead, YOU must handle -999 — a -999 that becomes 0 mm is a silent
      catastrophe in every downstream number.
      Report the surviving fraction as a share of BOTH 5041 (our full grid)
      and 4420 (the IMD box), so the two shrinkages are not conflated.

4. Sanity-check the physics, do not just check the plumbing: print the all-India
   mean daily rainfall for a few days in July 2015 and a few days in January
   2015. Monsoon July should be several mm/day and dramatically wetter than
   January. If it is not, something is wrong with the decoding — say so.

CONSTRAINTS:
- Never write a fallback that fabricates or synthesises data. If IMD fails,
  report the failure plainly. An honest "this does not work" is the useful
  outcome here.
- Do not modify 03_spread_skill.py in this prompt.
- Readable code, not clever code (Semester 3 team).

REPORT BACK: a clear PASS/FAIL on each of the four conditions, the land-point
fraction, the domain shrinkage from the 6.5N/66.5E origin, and a recommendation
on whether to proceed with the switch.
```

---

## P2 — Add 850 hPa u/v (before the bulk run, NOT before the deck)

```
Read CLAUDE.md, the WIND SHEAR section. The decision is already made: add
850 hPa. This prompt implements it.

Goal: fetch 850 hPa u/v and compute TRUE 500-850 vertical wind shear.

1. In 01_fetch.py, add the PLAIN files ugrd_pres and vgrd_pres to the variable
   list. Critical: 850 mb lives in the PLAIN *_pres files (they cover
   1000-800 mb). It is NOT in the *_abv700mb files. Add a selector that keeps
   only :850 mb: at the daily lead steps, exactly mirroring wanted_500mb().

2. In 02_features.py, add two columns:
       shear_500_850   magnitude of the (u500-u850, v500-v850) vector
       u850_mean / v850_mean if useful
   KEEP flow500_deformation exactly as it is. It is a real predictor, it is
   correctly named, and it is not shear. Do not rename it, do not remove it.

3. Verify on ONE date before anything else:
       python src/02_features.py --limit 1
   Check: the new column exists, is physically plausible (500-850 shear over
   India in the monsoon is typically ~5-20 m/s, often strongly negative zonal
   shear during JJAS), and the row count and grid alignment are unchanged.

4. Report the actual per-date transfer cost increase. CLAUDE.md estimates about
   5 MB on 309 MB (~1.6%). Confirm or correct that with the real number.

CONSTRAINTS:
- The existing 20150107 features part was built WITHOUT this column. Either
  delete it and its manifest row so it gets rebuilt, or make the schema change
  explicit. Do NOT end up with a parts directory of mixed schemas — that will
  fail or silently produce NaNs at finalize() time.
- Never label the deformation feature as wind shear anywhere.
```

---

## P3 — Rewire 03 to IMD truth, and keep lat/lon this time

```
Prerequisite: P1 passed. If P1 failed, stop and say so — do not proceed.

Read CLAUDE.md TRUTH SOURCE section.

Goal: 03_spread_skill.py measures against IMD, with ERA5 retained as a fallback.

1. Add a --truth flag: --truth imd (new default) or --truth era5 (keep the
   existing ERA5 code path working; do NOT delete it — it is the fallback and
   the only route for non-rainfall variables later).

2. Use src/imd_truth.py from P1 for the IMD path.

3. FIX A REAL GAP: the current sample parquet has NO lat/lon columns, so no
   regional or land-mask analysis is possible on it. The new sample MUST carry
   lat, lon, init, lead_day, mean, spread, truth, and season. We need lat/lon
   for the land mask and for regional stratification.

4. Handle the land mask properly: IMD ocean points are -999. Drop them as
   MISSING. Never let -999 become a rainfall value, and never let it become 0.
   Print how many points were dropped.

5. Update the module docstring. It currently states that IMD "CANNOT be used" —
   that referred to the real-time endpoint and is now misleading. Replace it
   with the corrected two-endpoint explanation from CLAUDE.md.

6. Allow multiple seasons and years in one run:
       --seasons JJAS,DJF,MAM,ON  --years 2012,2015,2018  --dates-per-season 3

CONSTRAINTS:
- NEVER mix truth sources within one comparison. Whatever truth the baseline is
  measured on is the truth the model must later be scored on.
- Every printed number must state its truth source.
- Do not touch 04_conditional.py; it reads whatever 03 writes.
```

---

## P4 — The four-season re-measurement (this is the deck's number)

```
Prerequisite: P3 done.

Goal: replace a 3-date, one-season, one-year provisional number with a
defensible one.

1. Run 03_spread_skill.py with IMD truth across roughly 12 init dates spanning
   all four seasons (JJAS, DJF, MAM, ON) and spread across at least three
   different years — do not take all 12 from one year. Consecutive Wednesdays
   from one month are nearly the same synoptic situation and will understate
   the uncertainty.

   Write the output to data/spread_skill_4season.parquet.

2. Then run:
       python src/04_conditional.py --sample data/spread_skill_4season.parquet --bootstrap 2000

3. Report, as a table:
   - pooled r and conditional r, overall
   - conditional r per season
   - the cluster-bootstrap 95% CI
   - how much the conditional number moved from the provisional +0.076

4. INTERPRET IT HONESTLY. Three cases:
   - conditional r stays low (<~0.15): the pitch stands as written.
   - conditional r rises materially (>~0.25): the claim needs REWORDING before
     it goes in the deck. Say so explicitly and loudly.
   - it varies a lot by season: that is itself a finding worth a slide —
     ensemble spread works in some regimes and not others.

CONSTRAINT: report what you find. Do not tune bins, thresholds, or date
selection to keep the number low. If the incumbent method turns out to be
better than we thought, that is the result, and CLAUDE.md's honesty rules say
we report it.
```

---

## P5 — Fix the climatology leak in `finalize()`

```
Read the LEAKAGE section in CLAUDE.md.

02_features.py finalize() computes the pwat/cape/precip anomalies against a
climatology taken over the ENTIRE concatenated table — train AND test together.
Every test row's anomaly therefore encodes the test period's own mean. This
silently inflates every metric and is invisible in the results.

Fix:
1. finalize() takes a --train-end date (e.g. 2015-12-31).
2. Climatology (grouped by lat, lon, lead_day, season) is computed ONLY on rows
   at or before --train-end.
3. That stored climatology is applied to ALL rows, train and test alike.
4. Persist the climatology table to disk so it is auditable and reusable.
5. If any test group has no training counterpart, emit NaN and report the count.
   Do not silently fall back to the test period's own mean.

Also: "regional error climatology" appears in the planned FEATURES list. It is
derived from |forecast - truth| and therefore truth-derived. If it is ever
implemented, it must be computed on the training window only and frozen. Add a
comment to that effect where the feature list lives.
```

---

## P6 — Bulk run (do NOT start before P2)

```
Prerequisites: P2 (850 hPa) and P5 (climatology fix) both done. Starting the
bulk run before P2 means refetching everything.

1. Confirm the resume manifest works: kill a run mid-date and restart it.
   Verify the interrupted date is retried and not falsely marked done.
2. Start with 5 years, not 20. ~80 GB, ~5 hours at 4.5 MB/s.
3. Log throughput. If it is far off 4.5 MB/s, stop and report — CLAUDE.md says
   this is bandwidth-bound, so more concurrency will not help.
4. Run finalize() with the train-only climatology from P5.
```

---

## P7 — The 5 vs 11 member sensitivity check

```
CLAUDE.md flags this as PRIORITY, not nice-to-have, and it is not implemented.

Our baseline is built on ensemble spread from a 5-member ensemble (11 on
Wednesdays). Operational GEFS carries 31. A small ensemble gives a NOISY spread
estimate, which makes the baseline easier to beat — and a judge will spot that.

On the Wednesday dates (which carry 11 members), compute spread from 5 members
and from all 11 on the SAME dates, then measure how the conditional spread-skill
correlation and our margin over the baseline change.

If the margin shrinks materially as members increase, our headline is partly an
artifact of a weak baseline, and CLAUDE.md says we report that honestly.

Deliverable: a small table, 5-member vs 11-member, same dates, same metric.
```

---

## Guardrails — worth pasting into any session

```
- Split train/test BY TIME, never randomly.
- Never report plain accuracy; the base rate is ~5%.
- Never write a fallback that silently generates synthetic data. If the real
  data path breaks, say so.
- ALL predictive features come from GEFS. ERA5 and IMD are TRUTH ONLY.
- Do not quote the POOLED spread-skill correlation as "the baseline".
- Never relabel flow500_deformation as wind shear.
- If we cannot beat ensemble spread, say so. An honest negative result scores
  better with meteorologist judges than an inflated claim.
```
