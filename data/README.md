# Data Policy

This repository does not commit generated weather data.

Excluded from git:

- GEFS GRIB files
- IMD `.grd` cache files
- Generated parquet feature tables
- Model checkpoints and large outputs

Tracked:

- `VISHWAS-HANDOFF.md`
- `raw/manifest.jsonl`

Regenerate datasets locally using the scripts in `src/`.

