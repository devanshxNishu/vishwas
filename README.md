# VISHWAS

Forecast Confidence Intelligence for SIH26079.

VISHWAS does not generate a new weather forecast. It predicts when an existing medium-range ensemble forecast is likely to be badly wrong, so forecasters can see low-confidence regions before acting on the forecast.

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

## Repository Layout

```text
src/
  01_fetch.py            Fetch GEFS reforecast files
  02_features.py         Build weather and ensemble features
  03_spread_skill.py     Measure spread-skill relationship
  04_conditional.py      Conditional baseline and bootstrap analysis
  05_ensemble_size.py    5 vs 11 ensemble sensitivity
  imd_truth.py           IMD rainfall truth loader
  verify_imd.py          IMD truth verification checks

docs/
  CLAUDE-CODE-PROMPTS.md Work plan and implementation prompts

data/
  VISHWAS-HANDOFF.md     Project handoff and current results
  raw/manifest.jsonl     Small fetch manifest
```

Generated datasets, IMD cache files, raw forecast files, virtual environments, models, and outputs are intentionally excluded from git.

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

