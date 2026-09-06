"""
Schema guard for data/features_parts/ — the mixed-schema trap, made loud.

CLAUDE.md, MIXED-SCHEMA TRAP: if a later run appends dates WITHOUT the 850 hPa
columns while the existing parts have them, nothing downstream complains.
finalize()'s own guard checks only ANOMALY_COLUMNS + CLIMATOLOGY_KEYS, so the
850 columns fall outside it; pd.concat fills the gap with NaN, and
HistGradientBoostingClassifier consumes NaN natively. The result is a feature
that is real for some dates and absent for the rest, with no error anywhere.

This script refuses to let that happen silently. It compares the column SET of
every part against the first one, requires the 850 hPa trio to be present in
all of them, and exits non-zero on any mismatch.

  python src/17_schema_guard.py                     # audit the parts
  python src/17_schema_guard.py --table data/x.parquet   # also audit a table

Exit codes: 0 clean, 1 mismatch. Run it BEFORE the fetch (to record the
reference schema) and AFTER it (to prove the new dates match).
"""

import argparse
import os
import sys

import pyarrow.parquet as pq

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(_ROOT, "data", "features_parts")

# The columns the trap is about. Named explicitly rather than inferred, so that
# a run where EVERY part lost them still fails instead of agreeing with itself.
REQUIRED_850 = ["u850_mean", "v850_mean", "shear_500_850"]


def audit_parts(parts_dir):
    files = sorted(f for f in os.listdir(parts_dir) if f.endswith(".parquet"))
    if not files:
        print("no parts in {}".format(parts_dir))
        return 1

    groups = {}
    for name in files:
        columns = tuple(pq.ParquetFile(os.path.join(parts_dir, name)).schema.names)
        groups.setdefault(columns, []).append(name)

    print("parts directory : {}".format(parts_dir))
    print("parts           : {}  ({} ... {})".format(
        len(files), files[0], files[-1]))
    print("distinct schemas: {}".format(len(groups)))

    failed = False
    if len(groups) != 1:
        failed = True
        print()
        print("MIXED SCHEMAS — this is the trap. The groups are:")
        reference = None
        for columns, names in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            print("  {} parts ({} ... {}), {} columns".format(
                len(names), names[0], names[-1], len(columns)))
            if reference is None:
                reference = set(columns)
                continue
            print("     missing vs the largest group: {}".format(
                sorted(reference - set(columns)) or "none"))
            print("     extra   vs the largest group: {}".format(
                sorted(set(columns) - reference) or "none"))

    columns = sorted(groups, key=lambda c: -len(groups[c]))[0]
    print()
    print("reference schema ({} columns):".format(len(columns)))
    for name in columns:
        mark = "  <- 850 hPa" if name in REQUIRED_850 else ""
        print("    {}{}".format(name, mark))

    print()
    for name in REQUIRED_850:
        missing = [f for f, cols in
                   ((f, cols) for cols, names in groups.items() for f in names)
                   if name not in cols]
        if missing:
            failed = True
            print("MISSING {} in {} parts, e.g. {}".format(
                name, len(missing), missing[:3]))
        else:
            print("present in every part: {}".format(name))

    return 1 if failed else 0


def audit_table(path):
    """A finalized table cannot show mixed schemas — it shows their aftermath.

    A column NaN for a round fraction of rows is the trap having sprung, so the
    null count is the diagnostic here, not the column list.
    """
    import pandas as pd

    print()
    print("finalized table : {}".format(path))
    table = pd.read_parquet(path)
    print("rows            : {:,}   columns: {}   dates: {}".format(
        len(table), len(table.columns), table["init"].nunique()))
    print()
    print("  {:<24} {:>12} {:>9}".format("column", "nulls", "pct"))
    failed = False
    for name in table.columns:
        nulls = int(table[name].isna().sum())
        pct = 100.0 * nulls / len(table)
        flag = ""
        # 55-65% is the shape of the trap: 156 of 260 dates NaN is exactly 60%.
        if 55.0 <= pct <= 65.0:
            flag = "   <-- SUSPICIOUS, looks like a per-date schema gap"
            failed = True
        elif nulls:
            flag = "   (non-zero)"
        print("  {:<24} {:>12,} {:>8.2f}%{}".format(name, nulls, pct, flag))

    for name in REQUIRED_850:
        if name not in table.columns:
            print("MISSING COLUMN in the finalized table: {}".format(name))
            failed = True
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description="Feature schema guard.")
    parser.add_argument("--parts", default=PARTS)
    parser.add_argument("--table", default=None,
                        help="also audit a finalized feature table's null counts")
    args = parser.parse_args()

    status = audit_parts(args.parts)
    if args.table:
        status = max(status, audit_table(args.table))

    print()
    if status:
        print("SCHEMA GUARD: FAILED. Do not run anything downstream of this.")
    else:
        print("SCHEMA GUARD: PASS. One schema, 850 hPa present throughout.")
    sys.exit(status)


if __name__ == "__main__":
    main()
