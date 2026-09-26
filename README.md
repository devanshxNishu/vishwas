# VISHWAS

Forecast Confidence Intelligence for SIH26079.

VISHWAS does not generate a new weather forecast. It predicts when an existing medium-range ensemble forecast is likely to be badly wrong, so forecasters can see low-confidence regions before acting on the forecast.

## What a fresh clone can run

`data/` is 3.4 GB and gitignored, so a clone gets the code, the models, the
figure generators, the logs and the docs -- and no input data. Read the
**HANDOVER block at the top of `CLAUDE.md`** first; it is written for someone
who has never seen this project and it is not repeated here.

Runs with only the repo:

- `scripts/check_docs.py` -- the health check, below.
- `site/index.html` and `site/dashboard/index.html` -- open either in a
  browser. Both are self-contained; the dashboard's data is inlined.
- The tracked result tables in `data/*.csv`, and `logs/` and `ablations/`,
  which are the record behind every published number.
- `models/*.joblib` -- the published model, the five-year retest and the
  operational calibrator all load as they are.

Needs `data/` regenerated first, because each reads a gitignored parquet:

- `api/main.py` -- `data/model_predictions.parquet` and `data/labelled.parquet`,
  both at import, so the API does not start without them.
- `src/15_dashboard_export.py` -- the same two, plus the model.
- `src/20_operational.py` -- a live cycle needs network and
  `data/climatology.parquet`; `--from-parquet` needs a stored cycle parquet.
- `src/21_oper_calibrate.py` -- `data/labelled.parquet` and
  `data/features_oper.parquet`.

Regenerating means a fetch with `src/01_fetch.py`: **50.3 GB** for the published
study (104 dates, 2018-2019) and **124.5 GB** for the five-year window
(2015-2019). Refitting the model is a separate step, `src/07_model.py`, and the
tracked `.joblib` means you only need it if you are changing the model.

The one command that proves the clone is healthy:

```bash
python scripts/check_docs.py
```

It must exit **1**, reporting **7 findings in 3 files** -- all seven being the
Team ID guard, which fires by design until the ID is issued. A green run is the
failure, not the fix: it means the guard was deleted. Any other finding, or a
non-zero site-assertion count, is a real regression. `CLAUDE.md` explains why.

## Problem Statement

- SIH: SIH26079
- Title: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts
- Organization: Ministry of Earth Sciences / NCMRWF
- Current SIH theme: Smart Automation
- Track: Software

## Current Status

- Verified IMD gauge-gridded rainfall as the truth source.
- Built exact grid colocation and land-mask checks.
- Built four-season spread-skill analysis on 12 initialization dates across 2012, 2015, and 2018.
- Measured ensemble spread against forecast error using pooled and conditional correlations.
- Added true 500-850 hPa wind shear feature support.
- Added 5-member vs 11-member ensemble sensitivity analysis.
- Built the labelled dataset: 1,302,080 rows over 104 forecast dates, 2018-2019.
- Trained and evaluated the bust classifier on a time-based split (train 2018, test 2019).
- Ran five ablations, SHAP explanations, isotonic calibration, and the demo confidence map.
- Scored POD/FAR/CSI/ETS against ensemble spread at a matched alert budget.
- Persisted the fitted model to `models/vishwas_model.joblib`.

## Key Result For The PPT

Raw ensemble spread looks strong when pooled across wet and dry regimes, but after fair rainfall-regime comparison it explains less than 1% of forecast-error variance. That gap is the opportunity for VISHWAS: a learned confidence layer can target forecast busts instead of treating ensemble spread as enough.

Verified baseline numbers:

| Metric | Result |
| --- | --- |
| Truth source | IMD gauge-gridded rainfall, land only |
| Sample | 77,425 wet samples, 12 dates, all seasons, Day 1-10 |
| Pooled spread-error correlation | +0.663 |
| Fair conditional correlation | +0.041 |
| Variance explained after fair control | 0.17% to 0.90% |
| 5 to 11 ensemble sensitivity | Small positive effect; conclusion unchanged |

### The trained model

Train 2018 (39 dates fitted, 13 held back as validation), test all 52 Wednesdays
of 2019 - a year the model never saw. 651,040 test rows over 1,252
gauge-observed land gridpoints, Day 1-10. Truth: IMD gauge-gridded rainfall.

| Metric | Ensemble spread | VISHWAS |
| --- | --- | --- |
| ROC-AUC, pooled (do not quote - see below) | 0.885 | 0.909 |
| ROC-AUC, within like rainfall conditions | 0.565 | 0.728 |
| PR-AUC lift over base rate | 6.29x | 7.60x |

The margin is +0.1634, 95% CI +0.1080 to +0.1926 by cluster bootstrap over the
52 forecast dates. Quote it as **+0.13 to +0.16**, never +0.163 alone. The
pooled row is an artefact of letting ensemble spread track rainfall amount and
must not be quoted as the result.

Ahead in all **eight** rainfall bins, by +0.079 to +0.252. In operational terms,
at a matched alert budget VISHWAS catches **64% of busts against ensemble
spread's 55%**.

## Repository Layout

```text
src/
  01_fetch.py            Fetch GEFS reforecast files
  02_features.py         Build weather and ensemble features
  03_spread_skill.py     Measure spread-skill relationship
  04_conditional.py      Conditional baseline and bootstrap analysis
  05_ensemble_size.py    5 vs 11 ensemble sensitivity
  06_label.py            Bust labels, per region and lead time
  07_model.py            Train and evaluate the bust classifier
  08_demo_map.py         Demo confidence map (fig6)
  08_met_metrics.py      POD/FAR/CSI/ETS at a matched alert budget
  08_pick_date.py        Choose the demo date on observed busts alone
  09_shap.py             SHAP explanations (fig7, fig8)
  10_calibration.py      Isotonic/Platt calibration, reliability (fig9)
  11_inversion.py        The pooled-to-stratified inversion (fig4)
  met_metrics.py         Metrics library used by 08_met_metrics.py
  imd_truth.py           IMD rainfall truth loader
  verify_imd.py          IMD truth verification checks
  watch_fetch.py         Progress monitor for a running fetch

scripts/
  check_docs.py          Documentation consistency check (see below)

docs/
  DECK-TECHNICAL-PACK.md Every current number, for the deck
  DECK-BRIEF.md          Framing, safe claims, the "do not claim" list
  DECK-VERIFICATION.md   Claim-by-claim verification of the deck
  DECK-BENCHMARK.md      What the selected SIH decks actually do
  TECHNICAL-REFERENCE.md The engineering picture
  CONSISTENCY-AUDIT.md   Documentation audit, 30 Aug 2026
  SIH-COMPLIANCE.md      Template rule compliance
  P11-ablations.md, P16-wrapup.md, CLAUDE-CODE-PROMPTS.md,
  PROMPTS-PHASE2-MODEL.md, PROMPTS-PHASE3-DEMO.md   Prompt archives

figures/                 Generated figures, fig1-fig9 (gitignored)
ablations/               Ablation logs and permutation importance
data/
  VISHWAS-HANDOFF.md     Project handoff and current results
  raw/manifest.jsonl     Small fetch manifest
```

## Checking the documentation

Numbers appear in many documents and drift silently. `scripts/check_docs.py`
holds the canonical values and the known-stale claims as two literal tables and
walks every `.md` in the repo:

```bash
python scripts/check_docs.py     # exits 0 if clean, 1 if anything is found
```

It reports and never rewrites. See `docs/CONSISTENCY-AUDIT.md`.

Generated datasets, IMD cache files, raw forecast files, virtual environments,
and outputs are intentionally excluded from git. The fitted models in `models/`
are the exception and **are** tracked -- they are the artefact this project
produces, they total under 600 KB, and without them a clone cannot score
anything without re-running the fetch. See "What a fresh clone can run" above.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Useful Commands

```bash
python src/verify_imd.py
python src/04_conditional.py --sample data/spread_skill_4season.parquet --bootstrap 500
python src/05_ensemble_size.py --sample data/spread_skill_4season.parquet --bootstrap 500
```

The parquet files referenced above are generated/local artifacts and are not committed to GitHub.

