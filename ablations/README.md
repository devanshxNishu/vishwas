# Ablations — what each log is, and one thing to read before the numbers

Printed output of `src/07_model.py`, one file per variant. These are **evidence
of what a run printed** and are never edited. If a log and a document disagree,
the document is what gets fixed.

| log | variant | `--drop` | ran |
|---|---|---|---|
| `a_full.log` | full model, all 23 features — the published headline | *(none)* | 2026-08-29 21:14 |
| `b_no_month.log` | month ablation: is the model learning the calendar? | `month` | 2026-08-29 21:16 |
| `c_no_precip.log` | drop the rainfall forecast entirely | `precip_mean,precip_spread` | 2026-08-29 21:18 |
| `d_no_850.log` | drop the 850 hPa trio | `shear_500_850,u850_mean,v850_mean` | 2026-08-29 21:20 |
| `e_spread_only.log` | learned model given ONLY ensemble spread | everything else | 2026-08-29 21:21 |
| `permutation.log` | permutation importance over all 23 features | — | 2026-08-29 21:15 |
| `a_full_5yr.log` | P34 five-year run, train 2015-17 / test 2018+19 | *(none)* | 2026-09-06 22:41 |

The five 2026-08-29 logs were produced by `run.sh`. `a_full_5yr.log` was not —
it is a separate study with its own study window and its own `--out` path.

## Read this before quoting a confidence interval from these logs

`a_full.log` line 30 prints

```
95% CI, cluster bootstrap over 52 forecast dates: +0.1026 to +0.1910
```

**The published canonical CI is `+0.1080 to +0.1926`.** Both are correct. They
differ only in the number of bootstrap replicates:

- `run.sh` line 11 passes `--bootstrap 500`, chosen so five variants would
  finish in reasonable time.
- The headline run used `--bootstrap 2000`.

Same seed (0), same data, same code. `cluster_bootstrap_margin()` resamples
forecast dates and reads the 2.5/97.5 percentiles off the resulting draws, so
**the point estimate is deterministic and the interval is not**: the margin
`+0.1634` and every per-bin figure in this log agree with the publication
exactly. Only the interval moves, and it moves because 500 draws estimate a tail
percentile less precisely than 2000 do.

**The log is correct as printed.** Do not edit it to match the publication, and
do not quote `+0.1026 to +0.1910` as the project's confidence interval.
`scripts/check_docs.py` forbids that pair in Markdown for exactly this reason.

Both values were reproduced from the stored predictions on **2026-09-07** —
evaluation only, no retraining, nothing regenerated:

```python
import importlib.util, pandas as pd
# `import 07_model` is a SyntaxError: the module name starts with a digit.
spec = importlib.util.spec_from_file_location("m", "src/07_model.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
test = pd.read_parquet("data/pred_a_full.parquet")
for reps in (500, 2000):
    r = m.cluster_bootstrap_margin(test, "model_score", "baseline_score", reps, 0)
    print(reps, "%+.4f to %+.4f" % (r["low"], r["high"]))
```

```
rows 651040, dates 52
500 +0.1026 to +0.1910
2000 +0.1080 to +0.1926
```

That both reproduce to four decimals also confirms `data/pred_a_full.parquet`
holds the same predictions the log and the publication were built from.

## Do not re-run `run.sh` to refresh these

It writes `ablations/*.log` and `data/pred_*.parquet` in place. Running it
overwrites the audit trail — including the file three documents cite — and the
new logs would carry a fresh timestamp with nothing to show for it.
